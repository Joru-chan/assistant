from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

import httpx
from fastmcp import FastMCP

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


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


def _title_property_name(properties: Dict[str, Any]) -> str | None:
    for name, prop in properties.items():
        if prop.get("type") == "title":
            return name
    return None


def _extract_plain_text(items: List[Dict[str, Any]]) -> str:
    return "".join(item.get("plain_text", "") for item in items).strip()


def _summarize_property(prop: Dict[str, Any]) -> Dict[str, Any]:
    prop_type = prop.get("type")
    if prop_type == "title":
        return {"type": "title", "value": _extract_plain_text(prop.get("title", []))}
    if prop_type == "rich_text":
        return {"type": "rich_text", "value": _extract_plain_text(prop.get("rich_text", []))}
    if prop_type == "select":
        select = prop.get("select") or {}
        return {"type": "select", "value": select.get("name")}
    if prop_type == "multi_select":
        multi = prop.get("multi_select") or []
        return {"type": "multi_select", "value": [item.get("name") for item in multi]}
    if prop_type == "checkbox":
        return {"type": "checkbox", "value": prop.get("checkbox")}
    if prop_type == "number":
        return {"type": "number", "value": prop.get("number")}
    if prop_type == "url":
        return {"type": "url", "value": prop.get("url")}
    if prop_type == "date":
        date = prop.get("date") or {}
        return {"type": "date", "value": date}
    return {"type": prop_type, "value": None}


def _summarize_page(page: Dict[str, Any]) -> Dict[str, Any]:
    props = page.get("properties", {})
    title_name = _title_property_name(props)
    title = ""
    if title_name:
        title_prop = props.get(title_name, {})
        title = _summarize_property(title_prop).get("value") or ""
    summary = {name: _summarize_property(prop) for name, prop in props.items()}
    return {
        "id": page.get("id"),
        "title": title,
        "url": page.get("url"),
        "last_edited_time": page.get("last_edited_time"),
        "properties": summary,
    }


def _build_property_update(
    prop_name: str,
    prop: Dict[str, Any],
    value: Any,
    errors: List[str],
) -> Dict[str, Any] | None:
    prop_type = prop.get("type")
    if prop_type == "title":
        if not isinstance(value, str):
            errors.append(f"Title property '{prop_name}' expects a string.")
            return None
        return {"title": [{"text": {"content": value}}]}
    if prop_type == "rich_text":
        if not isinstance(value, str):
            errors.append(f"Rich text property '{prop_name}' expects a string.")
            return None
        return {"rich_text": [{"text": {"content": value}}]}
    if prop_type == "select":
        if not isinstance(value, str):
            errors.append(f"Select property '{prop_name}' expects a string.")
            return None
        return {"select": {"name": value}}
    if prop_type == "multi_select":
        if isinstance(value, dict) and "replace" in value:
            replace_value = value.get("replace")
            if not isinstance(replace_value, list):
                errors.append(f"Multi-select property '{prop_name}' expects a list for replace.")
                return None
            cleaned = [str(item) for item in replace_value if item]
            return {"multi_select": [{"name": name} for name in cleaned]}
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            errors.append(f"Multi-select property '{prop_name}' expects a list of strings.")
            return None
        existing = prop.get("multi_select") or []
        existing_names = {item.get("name") for item in existing if item.get("name")}
        merged = list(existing_names.union({str(item) for item in value if item}))
        return {"multi_select": [{"name": name} for name in merged]}
    if prop_type == "checkbox":
        if not isinstance(value, bool):
            errors.append(f"Checkbox property '{prop_name}' expects true/false.")
            return None
        return {"checkbox": value}
    if prop_type == "number":
        if not isinstance(value, (int, float)):
            errors.append(f"Number property '{prop_name}' expects a number.")
            return None
        return {"number": value}
    if prop_type == "url":
        if not isinstance(value, str):
            errors.append(f"URL property '{prop_name}' expects a string.")
            return None
        return {"url": value}
    if prop_type == "date":
        if isinstance(value, str):
            return {"date": {"start": value}}
        if isinstance(value, dict):
            return {"date": value}
        errors.append(f"Date property '{prop_name}' expects a date string or object.")
        return None
    errors.append(f"Property '{prop_name}' type '{prop_type}' not supported for updates.")
    return None


def _build_blocks(append_blocks: List[Dict[str, Any]], errors: List[str]) -> List[Dict[str, Any]]:
    blocks = []
    for block in append_blocks:
        if block.get("type") != "paragraph":
            errors.append("Only paragraph blocks are supported.")
            continue
        text = block.get("text")
        if not isinstance(text, str):
            errors.append("Paragraph block requires text.")
            continue
        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": text}}]},
            }
        )
    return blocks


async def _fetch_page(
    client: httpx.AsyncClient, token: str, page_id: str
) -> Dict[str, Any]:
    url = f"{NOTION_API_BASE}/pages/{page_id}"
    resp = await client.get(url, headers=_headers(token))
    if resp.status_code >= 400:
        raise RuntimeError(_notion_error_message(resp))
    return resp.json()


def register(mcp: FastMCP) -> None:
    @mcp.tool
    async def notion_search(query: str, limit: int = 10) -> dict:
        errors: List[str] = []
        token = os.getenv("NOTION_TOKEN")
        if not token:
            errors.append("NOTION_TOKEN is not set on the server.")
        if not query:
            errors.append("Query is required.")
        if errors:
            return {
                "summary": "Missing configuration for Notion search.",
                "result": {"items": []},
                "next_actions": ["Set NOTION_TOKEN and provide a query."],
                "errors": errors,
            }

        payload = {
            "query": query,
            "page_size": max(1, min(limit, 50)),
            "filter": {"property": "object", "value": "page"},
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{NOTION_API_BASE}/search",
                headers=_headers(token),
                json=payload,
            )

        if resp.status_code >= 400:
            errors.append(_notion_error_message(resp))
            return {
                "summary": "Failed to search Notion.",
                "result": {"items": []},
                "next_actions": ["Check Notion token and permissions."],
                "errors": errors,
            }

        data = resp.json()
        results = data.get("results", [])
        items = []
        for page in results:
            props = page.get("properties", {})
            title_name = _title_property_name(props)
            title = ""
            if title_name:
                title_prop = props.get(title_name, {})
                title = _summarize_property(title_prop).get("value") or ""
            items.append(
                {
                    "id": page.get("id"),
                    "title": title,
                    "last_edited_time": page.get("last_edited_time"),
                    "url": page.get("url"),
                }
            )

        summary = f"Found {len(items)} Notion page(s) for query '{query}'."
        return {
            "summary": summary,
            "result": {"items": items},
            "next_actions": [],
            "errors": errors,
        }

    @mcp.tool
    async def notion_get_page(page_id: str) -> dict:
        errors: List[str] = []
        token = os.getenv("NOTION_TOKEN")
        if not token:
            errors.append("NOTION_TOKEN is not set on the server.")
        if not page_id:
            errors.append("page_id is required.")
        if errors:
            return {
                "summary": "Missing configuration for Notion page fetch.",
                "result": {"page": None},
                "next_actions": ["Set NOTION_TOKEN and provide page_id."],
                "errors": errors,
            }

        async with httpx.AsyncClient(timeout=10) as client:
            try:
                page = await _fetch_page(client, token, page_id)
            except RuntimeError as exc:
                errors.append(str(exc))
                return {
                    "summary": "Failed to fetch Notion page.",
                    "result": {"page": None},
                    "next_actions": ["Check Notion token, DB ID, and permissions."],
                    "errors": errors,
                }

        summary = _summarize_page(page)
        return {
            "summary": f"Fetched Notion page '{summary.get('title')}'.",
            "result": {"page": summary},
            "next_actions": [],
            "errors": errors,
        }

    @mcp.tool
    async def notion_update_page(
        page_id: str,
        updates: Dict[str, Any],
        dry_run: bool = True,
    ) -> dict:
        errors: List[str] = []
        token = os.getenv("NOTION_TOKEN")
        if not token:
            errors.append("NOTION_TOKEN is not set on the server.")
        if not page_id:
            errors.append("page_id is required.")
        if not isinstance(updates, dict):
            errors.append("updates must be an object.")
        if errors:
            return {
                "summary": "Missing configuration for Notion update.",
                "result": {},
                "next_actions": ["Set NOTION_TOKEN and provide page_id/updates."],
                "errors": errors,
            }

        async with httpx.AsyncClient(timeout=10) as client:
            try:
                page = await _fetch_page(client, token, page_id)
            except RuntimeError as exc:
                errors.append(str(exc))
                return {
                    "summary": "Failed to fetch Notion page.",
                    "result": {},
                    "next_actions": ["Check Notion token, page ID, and permissions."],
                    "errors": errors,
                }

            before = _summarize_page(page)
            props = page.get("properties", {})
            title_prop_name = _title_property_name(props)
            updates_payload: Dict[str, Any] = {}

            title_value = updates.get("title")
            if title_value is not None:
                if not title_prop_name:
                    errors.append("No title property found on page.")
                else:
                    title_prop = props.get(title_prop_name, {})
                    patch = _build_property_update(
                        title_prop_name, title_prop, title_value, errors
                    )
                    if patch:
                        updates_payload[title_prop_name] = patch

            prop_updates = updates.get("properties") or {}
            if isinstance(prop_updates, dict):
                for prop_name, value in prop_updates.items():
                    if prop_name not in props:
                        errors.append(f"Property '{prop_name}' does not exist on this page.")
                        continue
                    patch = _build_property_update(
                        prop_name, props[prop_name], value, errors
                    )
                    if patch:
                        updates_payload[prop_name] = patch

            append_blocks = updates.get("append_blocks") or []
            blocks = _build_blocks(append_blocks, errors)

            if dry_run:
                preview = dict(before)
                if updates_payload:
                    for name, value in updates_payload.items():
                        preview["properties"][name] = {
                            "type": props[name].get("type"),
                            "value": value.get(
                                props[name].get("type"),
                                value.get("select")
                                or value.get("multi_select")
                                or value.get("checkbox")
                                or value.get("number")
                                or value.get("url")
                                or value.get("date"),
                            ),
                        }
                if title_prop_name and title_value is not None:
                    preview["title"] = title_value

                return {
                    "summary": "Dry-run: Notion update preview generated.",
                    "result": {
                        "page_id": page_id,
                        "url": page.get("url"),
                        "dry_run": True,
                        "before": before,
                        "after": preview,
                        "proposed_updates": updates,
                        "append_blocks_count": len(blocks),
                    },
                    "next_actions": ["Re-run with dry_run=false to apply updates."],
                    "errors": errors,
                }

            if updates_payload:
                resp = await client.patch(
                    f"{NOTION_API_BASE}/pages/{page_id}",
                    headers=_headers(token),
                    json={"properties": updates_payload},
                )
                if resp.status_code >= 400:
                    errors.append(_notion_error_message(resp))
                else:
                    page = resp.json()

            if blocks:
                blocks_resp = await client.patch(
                    f"{NOTION_API_BASE}/blocks/{page_id}/children",
                    headers=_headers(token),
                    json={"children": blocks},
                )
                if blocks_resp.status_code >= 400:
                    errors.append(_notion_error_message(blocks_resp))

            after = _summarize_page(page) if page else before
            summary = "Updated Notion page." if not errors else "Update completed with warnings."

            return {
                "summary": summary,
                "result": {
                    "page_id": page_id,
                    "url": page.get("url") if page else None,
                    "dry_run": False,
                    "before": before,
                    "after": after,
                    "updated_properties": list(updates_payload.keys()),
                    "append_blocks_count": len(blocks),
                },
                "next_actions": [],
                "errors": errors,
            }
