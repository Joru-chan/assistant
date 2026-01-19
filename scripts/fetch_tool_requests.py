#!/usr/bin/env python3
"""
Fetch Tool Requests candidates via the VM MCP endpoint.

Usage:
  python scripts/fetch_tool_requests.py --limit 10
  python scripts/fetch_tool_requests.py --query "photo of receipt" --limit 10
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List

from tool_request_scoring import tokenize


def _run_mcp(tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
    cmd = ["./vm/mcp_curl.sh", tool, json.dumps(args)]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "vm/mcp_curl.sh failed")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from MCP: {exc}") from exc


def _extract_structured(payload: Dict[str, Any]) -> Dict[str, Any]:
    result = payload.get("result") or {}
    structured = result.get("structuredContent")
    if structured:
        return structured
    content = result.get("content") or []
    for block in content:
        text = block.get("text")
        if isinstance(text, str):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                continue
    raise RuntimeError("Missing structuredContent in MCP response")


def _parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _recency_days(value: str) -> int | None:
    dt = _parse_time(value)
    if not dt:
        return None
    now = datetime.now(timezone.utc)
    return max((now - dt).days, 0)


def _normalize_domain(domain: Any) -> List[str]:
    if isinstance(domain, list):
        return [str(item).strip() for item in domain if str(item).strip()]
    if isinstance(domain, str):
        return [part.strip() for part in domain.split(",") if part.strip()]
    return []


def _normalize_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    domain = _normalize_domain(raw.get("domain"))
    created_time = str(raw.get("created_time", "") or "").strip()
    description = str(raw.get("description", "") or "").strip()
    desired_outcome = str(raw.get("desired_outcome", "") or "").strip()
    title = str(raw.get("title", "") or "").strip()
    return {
        "id": str(raw.get("id", "")).strip(),
        "url": str(raw.get("url", "")).strip(),
        "title": title,
        "description": description,
        "desired_outcome": desired_outcome,
        "domain": domain,
        "status": str(raw.get("status", "") or "").strip(),
        "impact": str(raw.get("impact", "") or "").strip(),
        "frequency": str(raw.get("frequency", "") or "").strip(),
        "created_time": created_time,
        "recency_days": _recency_days(created_time),
        "tokens": {
            "title": tokenize(title),
            "description": tokenize(description),
            "desired_outcome": tokenize(desired_outcome),
            "domain": tokenize(" ".join(domain)),
        },
    }


def _dedupe(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    deduped: List[Dict[str, Any]] = []
    for item in items:
        page_id = item.get("id")
        if not page_id or page_id in seen:
            continue
        seen.add(page_id)
        deduped.append(item)
    return deduped


def fetch_candidates(limit: int, query: str | None) -> Dict[str, Any]:
    errors: List[str] = []
    items: List[Dict[str, Any]] = []

    latest_payload = _run_mcp(
        "tool_requests_latest",
        {"limit": limit, "statuses": ["new", "triaging"]},
    )
    latest_structured = _extract_structured(latest_payload)
    errors.extend(latest_structured.get("errors") or [])
    latest_items = latest_structured.get("result", {}).get("items", []) or []
    items.extend([_normalize_item(item) for item in latest_items])

    if query:
        search_payload = _run_mcp(
            "tool_requests_search",
            {"query": query, "limit": limit},
        )
        search_structured = _extract_structured(search_payload)
        errors.extend(search_structured.get("errors") or [])
        search_items = search_structured.get("result", {}).get("items", []) or []
        items.extend([_normalize_item(item) for item in search_items])

    candidates = _dedupe(items)
    return {
        "summary": f"Fetched {len(candidates)} candidate(s).",
        "result": {"candidates": candidates},
        "next_actions": [],
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch tool request candidates via MCP.")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--query", type=str, default=None)
    args = parser.parse_args()

    output = fetch_candidates(limit=args.limit, query=args.query)
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
