from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple

import httpx
from fastmcp import FastMCP

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

DEFAULT_PROPERTY_MAP = {
    "name": "Name",
    "quantity": "Quantity",
    "unit": "Unit",
    "category": "Category",
    "purchase_date": "Purchase Date",
    "store": "Store",
}

SKIP_KEYWORDS = {
    "total",
    "subtotal",
    "tax",
    "change",
    "cash",
    "visa",
    "mastercard",
    "amex",
    "balance",
    "payment",
    "discount",
}


def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _notion_error_message(response: httpx.Response) -> str:
    retry_after = response.headers.get("retry-after")
    if response.status_code == 429:
        return f"Notion rate limited (HTTP 429). Retry after {retry_after or 'later'}."
    try:
        payload = response.json()
        return payload.get("message") or payload.get("code") or response.text
    except Exception:  # noqa: BLE001
        return response.text


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _extract_price(line: str) -> str:
    match = re.search(r"\$?\d+(?:\.\d{2})?$", line.strip())
    return match.group(0) if match else ""


def _parse_receipt_text(text: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if any(keyword in lowered for keyword in SKIP_KEYWORDS):
            continue
        qty = None
        name_part = line
        qty_match = re.match(r"^\s*(\d+)\s*[xX]\s*(.+)", line)
        if qty_match:
            qty = int(qty_match.group(1))
            name_part = qty_match.group(2).strip()
        price = _extract_price(name_part)
        if price:
            name_part = name_part[: -len(price)].strip()
        name_part = re.sub(r"\s{2,}", " ", name_part).strip()
        if len(name_part) < 2:
            continue
        items.append(
            {
                "name": name_part,
                "quantity": qty,
                "unit": None,
                "category": None,
                "store": None,
                "purchase_date": None,
                "source_line": line,
                "confidence": 0.35 if qty is None else 0.45,
                "reason": "parsed_from_receipt_text",
            }
        )
    return items


def _normalize_items(items: List[Dict[str, Any]], errors: List[str]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"Item {idx + 1} is not an object.")
            continue
        name = item.get("name") or item.get("title")
        if not name or not isinstance(name, str):
            errors.append(f"Item {idx + 1} missing name/title.")
            continue
        normalized.append(
            {
                "name": name.strip(),
                "quantity": item.get("quantity"),
                "unit": item.get("unit"),
                "category": item.get("category"),
                "store": item.get("store"),
                "purchase_date": item.get("purchase_date"),
                "source_line": item.get("source_line"),
                "confidence": item.get("confidence", 0.75),
                "reason": "provided_items_input",
            }
        )
    return normalized


def _dedupe_items(items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    deduped: List[Dict[str, Any]] = []
    duplicates: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = _normalize_name(item.get("name", ""))
        if not key:
            duplicates.append(item)
            continue
        if key in seen:
            duplicates.append(item)
            continue
        seen.add(key)
        deduped.append(item)
    return deduped, duplicates


def _title_property_name(properties: Dict[str, Any]) -> str | None:
    for name, prop in properties.items():
        if prop.get("type") == "title":
            return name
    return None


def _build_property_payload(
    prop_type: str, value: Any, errors: List[str], prop_name: str
) -> Dict[str, Any] | None:
    if value is None:
        return None
    if prop_type == "title":
        return {"title": [{"text": {"content": str(value)}}]}
    if prop_type == "rich_text":
        return {"rich_text": [{"text": {"content": str(value)}}]}
    if prop_type == "select":
        return {"select": {"name": str(value)}}
    if prop_type == "multi_select":
        values = value if isinstance(value, list) else [value]
        return {"multi_select": [{"name": str(v)} for v in values if v]}
    if prop_type == "number":
        if isinstance(value, (int, float)):
            return {"number": value}
        try:
            return {"number": float(value)}
        except (TypeError, ValueError):
            errors.append(f"Property '{prop_name}' expects a number.")
            return None
    if prop_type == "date":
        if isinstance(value, dict):
            return {"date": value}
        return {"date": {"start": str(value)}}
    if prop_type == "url":
        return {"url": str(value)}
    if prop_type == "checkbox":
        if isinstance(value, bool):
            return {"checkbox": value}
        errors.append(f"Property '{prop_name}' expects a boolean.")
        return None
    errors.append(f"Property '{prop_name}' type '{prop_type}' not supported.")
    return None


async def _fetch_database(
    client: httpx.AsyncClient, token: str, db_id: str
) -> Dict[str, Any]:
    resp = await client.get(f"{NOTION_API_BASE}/databases/{db_id}", headers=_headers(token))
    if resp.status_code >= 400:
        raise RuntimeError(_notion_error_message(resp))
    return resp.json()


async def _query_by_title(
    client: httpx.AsyncClient, token: str, db_id: str, title_prop: str, name: str
) -> List[Dict[str, Any]]:
    payload = {"filter": {"property": title_prop, "title": {"equals": name}}}
    resp = await client.post(
        f"{NOTION_API_BASE}/databases/{db_id}/query",
        headers=_headers(token),
        json=payload,
    )
    if resp.status_code >= 400:
        return []
    return resp.json().get("results", [])


def _preview_payloads(
    items: List[Dict[str, Any]],
    property_map: Dict[str, str],
    properties: Dict[str, Any],
    errors: List[str],
) -> List[Dict[str, Any]]:
    preview: List[Dict[str, Any]] = []
    title_prop = _title_property_name(properties) or property_map.get("name")
    for item in items:
        props_payload: Dict[str, Any] = {}
        if title_prop in properties:
            prop_type = properties[title_prop].get("type")
            payload = _build_property_payload(prop_type, item.get("name"), errors, title_prop)
            if payload:
                props_payload[title_prop] = payload
        for key, prop_name in property_map.items():
            if key == "name":
                continue
            if prop_name not in properties:
                continue
            prop_type = properties[prop_name].get("type")
            payload = _build_property_payload(prop_type, item.get(key), errors, prop_name)
            if payload:
                props_payload[prop_name] = payload
        preview.append({"item": item, "properties": props_payload})
    return preview


def register(mcp: FastMCP) -> None:
    @mcp.tool
    async def receipt_photo_pantry_inventory(
        receipt_text: str | None = None,
        items: List[Dict[str, Any]] | None = None,
        store: str | None = None,
        purchase_date: str | None = None,
        dry_run: bool = True,
        confirm: bool = False,
        pantry_db_id: str | None = None,
        property_map: Dict[str, str] | None = None,
        check_existing: bool = True,
    ) -> dict:
        """
        Parse a receipt text (or structured items) into pantry inventory entries.
        Read-only by default; set dry_run=false and confirm=true to write.
        """
        errors: List[str] = []
        if not receipt_text and not items:
            errors.append("Provide receipt_text or items.")
        if not dry_run and not confirm:
            errors.append("Writes require confirm=true.")
        if errors:
            return {
                "summary": "Missing required inputs.",
                "result": {"items": []},
                "next_actions": ["Provide receipt_text or items."],
                "errors": errors,
            }

        parsed_items: List[Dict[str, Any]] = []
        if items:
            parsed_items.extend(_normalize_items(items, errors))
        if receipt_text:
            parsed_items.extend(_parse_receipt_text(receipt_text))

        for item in parsed_items:
            if store and not item.get("store"):
                item["store"] = store
            if purchase_date and not item.get("purchase_date"):
                item["purchase_date"] = purchase_date

        deduped, duplicates = _dedupe_items(parsed_items)
        summary_parts = [f"Parsed {len(parsed_items)} item(s)."]
        if duplicates:
            summary_parts.append(f"Skipped {len(duplicates)} duplicate line(s).")

        token = os.getenv("NOTION_TOKEN")
        db_id = pantry_db_id or os.getenv("PANTRY_DB_ID")
        property_map = property_map or {
            key: os.getenv(f"PANTRY_PROP_{key.upper()}", default)
            for key, default in DEFAULT_PROPERTY_MAP.items()
        }

        if dry_run or not db_id or not token:
            if not token:
                errors.append("NOTION_TOKEN not set; cannot write to Notion.")
            if not db_id:
                errors.append("PANTRY_DB_ID not set; cannot write to Notion.")
            return {
                "summary": " ".join(summary_parts) + " Dry-run preview.",
                "result": {
                    "items": deduped,
                    "duplicates": duplicates,
                    "apply_ready": False,
                    "property_map": property_map,
                },
                "next_actions": [
                    "Set PANTRY_DB_ID and NOTION_TOKEN to enable apply.",
                    "Re-run with dry_run=false and confirm=true to create items.",
                ],
                "errors": errors,
            }

        created: List[Dict[str, Any]] = []
        skipped_existing: List[Dict[str, Any]] = []
        missing_properties: List[str] = []
        preview_errors: List[str] = []
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                database = await _fetch_database(client, token, db_id)
            except RuntimeError as exc:
                return {
                    "summary": "Failed to load pantry database.",
                    "result": {"items": deduped},
                    "next_actions": ["Verify PANTRY_DB_ID and permissions."],
                    "errors": [str(exc)],
                }

            properties = database.get("properties", {})
            title_prop = _title_property_name(properties)
            if not title_prop:
                return {
                    "summary": "Pantry database missing title property.",
                    "result": {"items": deduped},
                    "next_actions": ["Ensure the pantry database has a title property."],
                    "errors": ["No title property found."],
                }

            for key, prop_name in property_map.items():
                if prop_name and prop_name not in properties:
                    missing_properties.append(prop_name)

            preview = _preview_payloads(deduped, property_map, properties, preview_errors)
            if preview_errors:
                errors.extend(preview_errors)

            for entry in preview:
                item = entry["item"]
                name = item.get("name", "")
                if check_existing:
                    existing = await _query_by_title(client, token, db_id, title_prop, name)
                    if existing:
                        skipped_existing.append(item)
                        continue

                payload = {
                    "parent": {"database_id": db_id},
                    "properties": entry["properties"],
                }
                resp = await client.post(
                    f"{NOTION_API_BASE}/pages",
                    headers=_headers(token),
                    json=payload,
                )
                if resp.status_code >= 400:
                    errors.append(_notion_error_message(resp))
                    continue
                page = resp.json()
                created.append(
                    {"id": page.get("id"), "url": page.get("url"), "name": name}
                )

        summary_parts.append(f"Created {len(created)} item(s) in Notion.")
        if skipped_existing:
            summary_parts.append(
                f"Skipped {len(skipped_existing)} existing item(s) by title."
            )
        if missing_properties:
            errors.append(
                "Missing pantry properties: " + ", ".join(sorted(set(missing_properties)))
            )

        return {
            "summary": " ".join(summary_parts),
            "result": {
                "items": deduped,
                "duplicates": duplicates,
                "created": created,
                "skipped_existing": skipped_existing,
                "property_map": property_map,
                "apply_ready": True,
                "checked_existing": check_existing,
                "ran_at": datetime.utcnow().isoformat() + "Z",
            },
            "next_actions": [
                "Review created items in Notion.",
                "Adjust property map via PANTRY_PROP_* env vars if needed.",
            ],
            "errors": errors,
        }
