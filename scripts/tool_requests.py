#!/usr/bin/env python3
"""
Unified Tool Requests / Friction Log management.

Quick capture (MCP + queue fallback):
  python scripts/tool_requests.py capture "Annoyed by X"
  python scripts/tool_requests.py capture "Annoyed by X" --desired-outcome "Y"

Detailed entry (direct Notion API):
  python scripts/tool_requests.py log --title "Annoyed by X" \
    --description "..." --desired "..." --frequency weekly

Fetch entries:
  python scripts/tool_requests.py fetch --limit 10
  python scripts/tool_requests.py fetch --query "photo" --limit 5

Flush offline queue:
  python scripts/tool_requests.py flush
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from notion_client import Client
    HAS_NOTION_CLIENT = True
except ImportError:
    HAS_NOTION_CLIENT = False

from common.progress import print_ok, print_warn, run_command

QUEUE_PATH = Path("memory/tool_requests_queue.jsonl")
CONTEXT_PATH = Path("PERSONAL_CONTEXT.md")


# ============================================================================
# CAPTURE (MCP + queue fallback)
# ============================================================================

def _load_env() -> None:
    if load_dotenv:
        load_dotenv()


def _read_db_id() -> str | None:
    db_id = os.getenv("TOOL_REQUESTS_DB_ID")
    if db_id:
        return db_id
    if not CONTEXT_PATH.exists():
        return None
    content = CONTEXT_PATH.read_text(encoding="utf-8")
    match = re.search(r"Tool Requests / Friction Log.*?Database ID.*?`([^`]+)`", content, re.DOTALL)
    return match.group(1) if match else None


def _split_domains(value: str | None) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _short_title(text: str, limit: int = 80) -> str:
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3].rstrip() + "..."


def _normalize_text(text: str | None) -> str | None:
    if text is None:
        return None
    return " ".join(text.replace('"', "'").split())


def _infer_desired_outcome(complaint: str) -> str:
    title = _short_title(complaint)
    return f"Resolve: {title}"


def _queue_entry(entry: Dict[str, Any]) -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with QUEUE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=True) + "\n")


def _build_prompt(db_id: str, entry: Dict[str, Any]) -> str:
    parts = [
        f"Title='{entry['title']}'",
        f"Description='{entry['description']}'",
        f"Desired outcome='{entry['desired_outcome']}'",
        f"Frequency='{entry['frequency']}'",
        f"Impact='{entry['impact']}'",
        f"Source='{entry['source']}'",
    ]
    domains = entry.get("domain") or []
    if domains:
        parts.append(f"Domain=[{', '.join(domains)}]")
    if entry.get("link"):
        parts.append(f"Link(s)='{entry['link']}'")
    if entry.get("notes"):
        parts.append(f"Notes / constraints='{entry['notes']}'")
    properties = ", ".join(parts)
    return (
        "Create a new entry in the Notion database "
        f"{db_id} with properties: {properties}. "
        "Return the created page URL."
    )


def _send_to_notion(prompt: str, verbose: bool, progress: bool) -> tuple[int, str]:
    return run_command(
        ["codex", "exec", prompt],
        label="Notion MCP: create tool request",
        verbose=verbose,
        progress=progress,
    )


def cmd_capture(args: argparse.Namespace) -> int:
    """Quick capture via MCP with queue fallback"""
    _load_env()
    db_id = _read_db_id()
    if not db_id:
        print_warn("Missing TOOL_REQUESTS_DB_ID. Queueing locally.")
        return _queue_and_exit(args)

    entry = {
        "title": _short_title(args.complaint),
        "description": _normalize_text(args.complaint),
        "desired_outcome": _normalize_text(args.desired_outcome or _infer_desired_outcome(args.complaint)),
        "frequency": args.frequency,
        "impact": args.impact,
        "domain": _split_domains(args.domain),
        "source": args.source,
        "link": args.link,
        "notes": _normalize_text(args.notes),
    }

    prompt = _build_prompt(db_id, entry)
    exit_code, output = _send_to_notion(prompt, args.verbose, not args.no_progress)

    if exit_code != 0:
        print_warn(f"MCP failed (exit {exit_code}). Queueing entry.")
        _queue_entry(entry)
        print_ok(f"Queued to {QUEUE_PATH}")
        return 1

    url_match = re.search(r"https://[^\s]+", output)
    url = url_match.group(0) if url_match else "Created"
    print_ok(f"Created: {url}")
    return 0


def _queue_and_exit(args: argparse.Namespace) -> int:
    entry = {
        "title": _short_title(args.complaint),
        "description": _normalize_text(args.complaint),
        "desired_outcome": _normalize_text(args.desired_outcome or _infer_desired_outcome(args.complaint)),
        "frequency": args.frequency,
        "impact": args.impact,
        "domain": _split_domains(args.domain),
        "source": args.source,
        "link": args.link,
        "notes": _normalize_text(args.notes),
    }
    _queue_entry(entry)
    print_ok(f"Queued to {QUEUE_PATH}")
    return 0


# ============================================================================
# LOG (Direct Notion API)
# ============================================================================

def build_notion_properties(args: argparse.Namespace) -> dict:
    """Build Notion properties dict from args"""
    props = {
        "Title": {
            "title": [{"type": "text", "text": {"content": args.title}}],
        }
    }
    if args.description:
        props["Description"] = {
            "rich_text": [{"type": "text", "text": {"content": args.description}}]
        }
    if args.desired:
        props["Desired outcome"] = {
            "rich_text": [{"type": "text", "text": {"content": args.desired}}]
        }
    if args.frequency:
        props["Frequency"] = {"select": {"name": args.frequency}}
    if args.impact:
        props["Impact"] = {"select": {"name": args.impact}}
    domains = _split_domains(args.domain)
    if domains:
        props["Domain"] = {"multi_select": [{"name": name} for name in domains]}
    if args.status:
        props["Status"] = {"select": {"name": args.status}}
    if args.source:
        props["Source"] = {"select": {"name": args.source}}
    if args.link:
        props["Link(s)"] = {"url": args.link}
    if args.notes:
        props["Notes / constraints"] = {
            "rich_text": [{"type": "text", "text": {"content": args.notes}}]
        }
    return props


def cmd_log(args: argparse.Namespace) -> int:
    """Detailed entry via direct Notion API"""
    if not HAS_NOTION_CLIENT:
        print_warn("notion-client not installed. Use 'capture' command instead.")
        return 1

    _load_env()
    db_id = args.db_id or _read_db_id()
    if not db_id:
        raise SystemExit("Missing database ID. Set TOOL_REQUESTS_DB_ID or pass --db-id.")

    notion_token = os.getenv("NOTION_TOKEN")
    if not notion_token:
        raise SystemExit("NOTION_TOKEN environment variable is required.")

    notion = Client(auth=notion_token)
    properties = build_notion_properties(args)
    response = notion.pages.create(parent={"database_id": db_id}, properties=properties)
    print_ok(response.get("url", "Created entry."))
    return 0


# ============================================================================
# FETCH
# ============================================================================

def _run_mcp(tool: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    cmd = ["./vm/mcp_curl.sh", tool, json.dumps(tool_args)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
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


def cmd_fetch(args: argparse.Namespace) -> int:
    """Fetch tool requests from MCP"""
    mcp_args = {"limit": args.limit}
    if args.query:
        mcp_args["query"] = args.query

    try:
        payload = _run_mcp("tool_requests_latest", mcp_args)
        data = _extract_structured(payload)
        candidates = data.get("result", [])
        
        if not candidates:
            print("No tool requests found.")
            return 0

        print(f"Found {len(candidates)} tool request(s):\n")
        for item in candidates:
            print(f"  • {item.get('title', 'Untitled')}")
            print(f"    Status: {item.get('status', 'N/A')}, Impact: {item.get('impact', 'N/A')}, Frequency: {item.get('frequency', 'N/A')}")
            if item.get("page_id"):
                print(f"    ID: {item['page_id']}")
            print()
        return 0

    except Exception as exc:
        print_warn(f"Failed to fetch: {exc}")
        return 1


# ============================================================================
# FLUSH QUEUE
# ============================================================================

def cmd_flush(args: argparse.Namespace) -> int:
    """Flush offline queue to Notion"""
    if not QUEUE_PATH.exists():
        print_ok("Queue is empty.")
        return 0

    _load_env()
    db_id = _read_db_id()
    if not db_id:
        print_warn("Missing TOOL_REQUESTS_DB_ID. Cannot flush.")
        return 1

    entries = []
    with QUEUE_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    if not entries:
        print_ok("Queue is empty.")
        QUEUE_PATH.unlink(missing_ok=True)
        return 0

    print(f"Flushing {len(entries)} queued entries...")
    succeeded = 0
    failed = []

    for idx, entry in enumerate(entries, 1):
        prompt = _build_prompt(db_id, entry)
        exit_code, output = _send_to_notion(prompt, args.verbose, not args.no_progress)
        if exit_code == 0:
            succeeded += 1
            print_ok(f"  [{idx}/{len(entries)}] Created: {entry['title']}")
        else:
            failed.append(entry)
            print_warn(f"  [{idx}/{len(entries)}] Failed: {entry['title']}")

    if failed:
        with QUEUE_PATH.open("w", encoding="utf-8") as handle:
            for entry in failed:
                handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
        print_warn(f"Flushed {succeeded}/{len(entries)}. {len(failed)} remain queued.")
        return 1
    else:
        QUEUE_PATH.unlink(missing_ok=True)
        print_ok(f"Flushed all {succeeded} entries.")
        return 0


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="Tool Requests management")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # CAPTURE
    capture_parser = subparsers.add_parser("capture", help="Quick capture via MCP")
    capture_parser.add_argument("complaint", help="Short complaint or friction note")
    capture_parser.add_argument("--desired-outcome")
    capture_parser.add_argument("--frequency", default="once", choices=["once", "weekly", "daily", "many-times-per-day"])
    capture_parser.add_argument("--impact", default="low", choices=["low", "medium", "high"])
    capture_parser.add_argument("--domain", help="Comma-separated (e.g., email,planning)")
    capture_parser.add_argument("--source", default="terminal", choices=["poke", "terminal", "other"])
    capture_parser.add_argument("--link")
    capture_parser.add_argument("--notes")
    capture_parser.add_argument("--verbose", action="store_true")
    capture_parser.add_argument("--no-progress", action="store_true")

    # LOG
    log_parser = subparsers.add_parser("log", help="Detailed entry via Notion API")
    log_parser.add_argument("--db-id")
    log_parser.add_argument("--title", required=True)
    log_parser.add_argument("--description")
    log_parser.add_argument("--desired")
    log_parser.add_argument("--frequency", default="once", choices=["once", "weekly", "daily", "many-times-per-day"])
    log_parser.add_argument("--impact", default="low", choices=["low", "medium", "high"])
    log_parser.add_argument("--domain")
    log_parser.add_argument("--status", default="new", choices=["new", "triaging", "spec-ready", "building", "shipped", "won't-do"])
    log_parser.add_argument("--source", default="terminal", choices=["poke", "terminal", "other"])
    log_parser.add_argument("--link")
    log_parser.add_argument("--notes")

    # FETCH
    fetch_parser = subparsers.add_parser("fetch", help="Fetch tool requests from MCP")
    fetch_parser.add_argument("--limit", type=int, default=10)
    fetch_parser.add_argument("--query")

    # FLUSH
    flush_parser = subparsers.add_parser("flush", help="Flush offline queue to Notion")
    flush_parser.add_argument("--verbose", action="store_true")
    flush_parser.add_argument("--no-progress", action="store_true")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "capture":
        return cmd_capture(args)
    elif args.command == "log":
        return cmd_log(args)
    elif args.command == "fetch":
        return cmd_fetch(args)
    elif args.command == "flush":
        return cmd_flush(args)
    else:
        print_warn(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
