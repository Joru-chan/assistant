#!/usr/bin/env python3
"""
Triage Tool Requests via the VM MCP endpoint.

Usage:
  python scripts/triage.py
  python scripts/triage.py --dry-run
  python scripts/triage.py --execute
  python scripts/triage.py --write
  python scripts/triage.py --limit 20
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


THEME_MAP = {
    "calendar": "calendar hygiene",
    "email": "email triage",
    "notion": "notion hygiene",
    "health": "health admin",
    "errands": "errands",
    "planning": "planning",
    "admin": "admin",
    "relationships": "relationships",
    "home": "home operations",
    "finance": "finance admin",
    "other": "other",
}

DOMAIN_THEME_PRIORITY = [
    ({"recipes", "instagram"}, "recipe capture"),
    ({"groceries", "inventory"}, "pantry inventory"),
    ({"pantry", "reading", "knowledge", "ocr", "capture"}, "knowledge capture"),
]

KEYWORD_MAP = {
    "calendar": "calendar hygiene",
    "meeting": "calendar hygiene",
    "invite": "calendar hygiene",
    "email": "email triage",
    "notion": "notion hygiene",
    "note": "notion hygiene",
    "health": "health admin",
    "doctor": "health admin",
    "appointment": "health admin",
    "plan": "planning",
    "schedule": "planning",
    "bill": "finance admin",
    "finance": "finance admin",
    "home": "home operations",
    "relationship": "relationships",
    "recipe": "home operations",
    "pantry": "knowledge capture",
    "reading": "knowledge capture",
    "knowledge": "knowledge capture",
    "ocr": "knowledge capture",
    "capture": "knowledge capture",
    "article": "knowledge capture",
    "articles": "knowledge capture",
    "inventory": "pantry inventory",
    "groceries": "pantry inventory",
    "instagram": "recipe capture",
}


@dataclass
class TriageItem:
    page_id: str
    url: str
    title: str
    desired_outcome: str
    domain: List[str]
    status: str
    created_time: str
    score: float = 0.0
    theme: str = "other"


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


def _recency_score(value: str) -> int:
    dt = _parse_time(value)
    if not dt:
        return 0
    now = datetime.now(timezone.utc)
    delta_days = (now - dt).days
    if delta_days <= 7:
        return 2
    if delta_days <= 30:
        return 1
    return 0


def _theme_from_domain(domains: List[str]) -> str | None:
    if not domains:
        return None
    domain_set = {domain.strip().lower() for domain in domains if domain.strip()}
    if not domain_set:
        return None
    for candidates, theme in DOMAIN_THEME_PRIORITY:
        if domain_set.intersection(candidates):
            return theme
    return None


def _theme_for_item(item: TriageItem) -> str:
    domain_theme = _theme_from_domain(item.domain)
    if domain_theme:
        return domain_theme
    text = f"{item.title} {item.desired_outcome}"
    lower = text.lower()
    for key, theme in KEYWORD_MAP.items():
        if key in lower:
            return theme
    return THEME_MAP["other"]


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "tool-request"


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_spec(item: TriageItem) -> str:
    desired = item.desired_outcome or "TBD"
    return (
        f"# Tool Spec: {item.title}\n\n"
        f"- Source: Tool Requests / Friction Log\n"
        f"- Item URL: {item.url}\n"
        f"- Theme: {item.theme}\n"
        f"- Score: {item.score:.1f}\n\n"
        "## Problem\n"
        f"{item.title}\n\n"
        "## Desired outcome\n"
        f"{desired}\n\n"
        "## v0 proposal\n"
        "- Deliver the smallest useful workflow.\n"
        "- Read-only by default; apply only with explicit confirmation.\n"
    )


def _build_plan(item: TriageItem) -> str:
    return (
        f"# Plan: {item.title}\n\n"
        f"- Selected item: {item.title}\n"
        f"- Theme: {item.theme}\n"
        f"- Score: {item.score:.1f}\n"
        f"- Source URL: {item.url}\n\n"
        "## Next steps (v0)\n"
        "1) Draft a minimal tool spec.\n"
        "2) Implement a read-only path first.\n"
        "3) Add an explicit apply/confirm step for writes.\n"
    )


def _normalize(raw: Dict[str, Any]) -> TriageItem:
    domain = raw.get("domain") or []
    if isinstance(domain, str):
        domain = [part.strip() for part in domain.split(",") if part.strip()]
    if not isinstance(domain, list):
        domain = []
    return TriageItem(
        page_id=str(raw.get("id", "")).strip(),
        url=str(raw.get("url", "")).strip(),
        title=str(raw.get("title", "")).strip(),
        desired_outcome=str(raw.get("desired_outcome", "") or "").strip(),
        domain=domain,
        status=str(raw.get("status", "") or "").strip(),
        created_time=str(raw.get("created_time", "") or "").strip(),
    )


def triage(limit: int, dry_run: bool) -> Dict[str, Any]:
    payload = _run_mcp(
        "tool_requests_latest",
        {"limit": limit, "statuses": ["new", "triaging"]},
    )
    structured = _extract_structured(payload)
    errors = structured.get("errors") or []
    items = structured.get("result", {}).get("items", [])

    normalized: List[TriageItem] = []
    for item in items:
        triage_item = _normalize(item)
        triage_item.theme = _theme_for_item(triage_item)
        triage_item.score = 2 + 2 + _recency_score(triage_item.created_time)
        normalized.append(triage_item)

    normalized.sort(key=lambda item: item.score, reverse=True)
    selected = normalized[0] if normalized else None

    spec_path = None
    plan_path = None
    if selected and not dry_run:
        today = datetime.now().strftime("%Y-%m-%d")
        slug = _slugify(selected.title)
        spec_path = Path("memory/specs") / f"{today}_{slug}.md"
        plan_path = Path("memory/plans") / f"{today}_{slug}.md"
        _write_file(spec_path, _build_spec(selected))
        _write_file(plan_path, _build_plan(selected))

    result = {
        "items_considered": len(normalized),
        "selected": (
            {
                "id": selected.page_id,
                "title": selected.title,
                "url": selected.url,
                "created_time": selected.created_time,
                "theme": selected.theme,
                "score": selected.score,
                "desired_outcome": selected.desired_outcome,
            }
            if selected
            else None
        ),
        "spec_path": str(spec_path) if spec_path else None,
        "plan_path": str(plan_path) if plan_path else None,
    }

    summary = (
        f"Selected top request: {selected.title}." if selected else "No tool requests found."
    )
    next_actions = []
    if dry_run and selected:
        next_actions.append("Re-run with --execute to write spec and plan files.")
    if selected and spec_path and plan_path:
        next_actions.append(f"Review spec: {spec_path}")
        next_actions.append(f"Review plan: {plan_path}")

    return {
        "summary": summary,
        "result": result,
        "next_actions": next_actions,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Triage tool requests via MCP.")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    dry_run = True
    if args.execute or args.write:
        dry_run = False
    if args.dry_run:
        dry_run = True

    output = triage(limit=args.limit, dry_run=dry_run)
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
