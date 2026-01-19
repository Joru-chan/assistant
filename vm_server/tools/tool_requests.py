from __future__ import annotations

import os
from typing import Any, Dict, List

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


def _extract_title(properties: Dict[str, Any]) -> str:
    for value in properties.values():
        if value.get("type") == "title":
            title_items = value.get("title", [])
            return "".join(item.get("plain_text", "") for item in title_items).strip()
    title_prop = properties.get("Title")
    if title_prop and title_prop.get("type") == "title":
        title_items = title_prop.get("title", [])
        return "".join(item.get("plain_text", "") for item in title_items).strip()
    return ""


def _extract_rich_text(properties: Dict[str, Any], name: str) -> str:
    prop = properties.get(name)
    if not prop or prop.get("type") != "rich_text":
        return ""
    items = prop.get("rich_text", [])
    return "".join(item.get("plain_text", "") for item in items).strip()


def _extract_select(properties: Dict[str, Any], name: str) -> str:
    prop = properties.get(name)
    if not prop or prop.get("type") != "select":
        return ""
    select = prop.get("select") or {}
    return str(select.get("name") or "").strip()


def _extract_multi_select(properties: Dict[str, Any], name: str) -> List[str]:
    prop = properties.get(name)
    if not prop or prop.get("type") != "multi_select":
        return []
    items = prop.get("multi_select", [])
    return [item.get("name", "").strip() for item in items if item.get("name")]


def _build_status_filter(statuses: List[str]) -> Dict[str, Any] | None:
    cleaned = [status.strip() for status in statuses if status.strip()]
    if not cleaned:
        return None
    if len(cleaned) == 1:
        return {
            "property": "Status",
            "select": {"equals": cleaned[0]},
        }
    return {
        "or": [
            {
                "property": "Status",
                "select": {"equals": status},
            }
            for status in cleaned
        ]
    }


def _build_search_filter(query: str) -> Dict[str, Any]:
    return {
        "or": [
            {"property": "Title", "title": {"contains": query}},
            {"property": "Description", "rich_text": {"contains": query}},
            {"property": "Desired outcome", "rich_text": {"contains": query}},
        ]
    }


def _extract_items(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for page in results:
        properties = page.get("properties", {})
        items.append(
            {
                "id": page.get("id"),
                "title": _extract_title(properties),
                "description": _extract_rich_text(properties, "Description"),
                "created_time": page.get("created_time"),
                "status": _extract_select(properties, "Status"),
                "source": _extract_select(properties, "Source"),
                "desired_outcome": _extract_rich_text(properties, "Desired outcome"),
                "domain": _extract_multi_select(properties, "Domain"),
                "impact": _extract_select(properties, "Impact"),
                "frequency": _extract_select(properties, "Frequency"),
                "url": page.get("url"),
            }
        )
    return items


def _summarize(items: List[Dict[str, Any]], label: str) -> str:
    titles = [item.get("title") or "Untitled" for item in items]
    head = "; ".join(titles[:3])
    suffix = f" Top: {head}." if head else ""
    return f"{label}: {len(items)} item(s).{suffix}"


def _notion_error_message(response: httpx.Response) -> str:
    retry_after = response.headers.get("retry-after")
    if response.status_code == 429:
        return f"Notion rate limited (HTTP 429). Retry after {retry_after or 'later'}."
    try:
        payload = response.json()
        return payload.get("message") or payload.get("code") or response.text
    except Exception:  # noqa: BLE001
        return response.text


def register(mcp: FastMCP) -> None:
    @mcp.tool
    async def tool_requests_latest(
        limit: int = 10,
        statuses: List[str] | None = None,
    ) -> dict:
        """
        Return the latest Tool Requests entries filtered by status.
        """
        errors: List[str] = []
        notion_token = os.getenv("NOTION_TOKEN")
        db_id = os.getenv("TOOL_REQUESTS_DB_ID")
        if not notion_token:
            errors.append("NOTION_TOKEN is not set on the server.")
        if not db_id:
            errors.append("TOOL_REQUESTS_DB_ID is not set on the server.")
        if errors:
            return {
                "summary": "Missing configuration for Notion access.",
                "result": {"items": []},
                "next_actions": ["Set NOTION_TOKEN and TOOL_REQUESTS_DB_ID."],
                "errors": errors,
            }

        statuses = statuses or ["new", "triaging"]
        filter_payload = _build_status_filter(statuses)
        payload: Dict[str, Any] = {
            "page_size": max(1, min(limit, 50)),
            "sorts": [{"timestamp": "created_time", "direction": "descending"}],
        }
        if filter_payload:
            payload["filter"] = filter_payload

        url = f"{NOTION_API_BASE}/databases/{db_id}/query"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, headers=_headers(notion_token), json=payload)

        if resp.status_code >= 400:
            errors.append(_notion_error_message(resp))
            return {
                "summary": "Failed to fetch Tool Requests.",
                "result": {"items": []},
                "next_actions": ["Check Notion token, DB ID, and permissions."],
                "errors": errors,
            }

        data = resp.json()
        results = data.get("results", [])
        items = _extract_items(results)
        summary = _summarize(items, "Latest tool requests")

        return {
            "summary": summary,
            "result": {"items": items},
            "next_actions": [],
            "errors": errors,
        }

    @mcp.tool
    async def tool_requests_search(query: str, limit: int = 10) -> dict:
        """
        Search Tool Requests by keyword across title and description.
        """
        errors: List[str] = []
        notion_token = os.getenv("NOTION_TOKEN")
        db_id = os.getenv("TOOL_REQUESTS_DB_ID")
        if not notion_token:
            errors.append("NOTION_TOKEN is not set on the server.")
        if not db_id:
            errors.append("TOOL_REQUESTS_DB_ID is not set on the server.")
        if not query:
            errors.append("Query is required.")
        if errors:
            return {
                "summary": "Missing configuration for Notion search.",
                "result": {"items": []},
                "next_actions": ["Set NOTION_TOKEN and TOOL_REQUESTS_DB_ID."],
                "errors": errors,
            }

        payload = {
            "page_size": max(1, min(limit, 50)),
            "filter": _build_search_filter(query),
            "sorts": [{"timestamp": "created_time", "direction": "descending"}],
        }

        url = f"{NOTION_API_BASE}/databases/{db_id}/query"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, headers=_headers(notion_token), json=payload)

        if resp.status_code >= 400:
            errors.append(_notion_error_message(resp))
            return {
                "summary": "Failed to search Tool Requests.",
                "result": {"items": []},
                "next_actions": ["Check Notion token, DB ID, and permissions."],
                "errors": errors,
            }

        data = resp.json()
        results = data.get("results", [])
        items = _extract_items(results)
        summary = _summarize(items, "Search results")

        return {
            "summary": summary,
            "result": {"items": items},
            "next_actions": [],
            "errors": errors,
        }
