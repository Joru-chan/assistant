#!/usr/bin/env python3
"""
Tool Requests / Friction Log entry helper.

Usage:
  python scripts/tool_requests_log.py --title "Annoyed by X" \
    --description "What happened..." \
    --desired "What good looks like..." \
    --frequency weekly \
    --impact medium \
    --domain "email,planning" \
    --source terminal \
    --link "https://example.com" \
    --notes "Any constraints"
"""

import argparse
import os
from typing import List

from dotenv import load_dotenv
from notion_client import Client

load_dotenv()


def _split_multi(value: str | None) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def build_properties(args: argparse.Namespace) -> dict:
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
    domains = _split_multi(args.domain)
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a Tool Requests / Friction Log entry in Notion."
    )
    parser.add_argument("--db-id", default=os.getenv("TOOL_REQUESTS_DB_ID"))
    parser.add_argument("--title", required=True)
    parser.add_argument("--description")
    parser.add_argument("--desired")
    parser.add_argument(
        "--frequency",
        default="once",
        choices=["once", "weekly", "daily", "many-times-per-day"],
    )
    parser.add_argument("--impact", default="low", choices=["low", "medium", "high"])
    parser.add_argument("--domain", help="Comma-separated list (e.g., email,planning)")
    parser.add_argument(
        "--status",
        default="new",
        choices=["new", "triaging", "spec-ready", "building", "shipped", "won't-do"],
    )
    parser.add_argument(
        "--source", default="terminal", choices=["poke", "terminal", "other"]
    )
    parser.add_argument("--link")
    parser.add_argument("--notes")

    args = parser.parse_args()
    db_id = args.db_id
    if not db_id:
        raise SystemExit(
            "Missing database ID. Set TOOL_REQUESTS_DB_ID or pass --db-id."
        )

    notion_token = os.getenv("NOTION_TOKEN")
    if not notion_token:
        raise SystemExit("NOTION_TOKEN environment variable is required.")

    notion = Client(auth=notion_token)
    properties = build_properties(args)
    response = notion.pages.create(parent={"database_id": db_id}, properties=properties)
    print(response.get("url", "Created entry."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
