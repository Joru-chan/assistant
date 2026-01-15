#!/usr/bin/env python3
"""
Poke-friendly MCP wrapper for Calendar Hygiene.

Exposes two stable entrypoints:
  - plan(days=7, calendar_id=None, verbose=False)
  - apply(plan_id, action_ids, dry_run=True, confirm=False)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.calendar_hygiene import calendar_hygiene as ch  # noqa: E402


def _preview_actions(actions: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    preview = []
    for action in actions[:limit]:
        preview.append(
            {
                "action_id": action.get("action_id"),
                "type": action.get("type"),
                "title": action.get("title"),
                "start": action.get("start"),
                "end": action.get("end"),
                "reason": action.get("reason"),
                "confidence": action.get("confidence"),
            }
        )
    return preview


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def plan(days: int = 7, calendar_id: str | None = None, verbose: bool = False) -> Dict[str, Any]:
    ch._load_env()
    calendar_id = calendar_id or "primary"
    now = datetime.now(timezone.utc)
    start = now
    end = now + timedelta(days=days)
    start_iso = start.isoformat()
    end_iso = end.isoformat()

    events, errors, raw_count = ch._fetch_events(start_iso, end_iso, calendar_id)
    data_source = "mcp"
    if errors:
        events = ch._mock_events(start)
        data_source = "mock"
        raw_count = len(events)

    events, stats = ch._filter_events(events)
    actions, debug_lines = ch._build_actions(events)
    time_window = {"start": start_iso, "end": end_iso}
    plan_data = ch.build_plan(
        events, time_window, calendar_id, data_source, errors, actions
    )
    plan_path = ch._write_plan(plan_data)

    if verbose:
        print("Debug:")
        print(f"- Calendar(s): {calendar_id}")
        print(f"- Time window: {start_iso} -> {end_iso}")
        print(f"- Events fetched: {raw_count}")
        print(f"- Events analyzed: {len(events)}")
        print(f"- All-day excluded: {stats['all_day_excluded']}")
        print(f"- Private events (kept for timing): {stats['private_count']}")
        print("- Declined events: not available in MCP data.")
        print("- Private events: keyword heuristics skipped; timing heuristics allowed.")
        print("- Heuristic traces:")
        for line in debug_lines:
            print(f"  - {line}")

    summary = (
        f"Plan {plan_data['plan_id']} saved. "
        f"{len(events)} events scanned, {len(actions)} actions proposed."
    )
    if data_source == "mock":
        summary += " MCP unavailable; using mock events."

    return {
        "summary": summary,
        "result": {
            "plan_id": plan_data["plan_id"],
            "time_window": plan_data["time_window"],
            "events_scanned": len(events),
            "actions_proposed": len(actions),
            "proposed_actions_preview": _preview_actions(actions),
            "plan_path": str(plan_path),
        },
        "next_actions": [
            "Review the plan file and proposed actions.",
            "Call calendar_hygiene_apply with selected action IDs when ready.",
        ],
        "errors": errors,
    }


def apply(
    plan_id: str,
    action_ids: List[str],
    dry_run: bool = True,
    confirm: bool = False,
) -> Dict[str, Any]:
    ch._load_env()

    if not dry_run and not confirm:
        return {
            "summary": "Confirmation required before applying changes.",
            "result": {
                "created_count": 0,
                "created_event_ids": [],
                "skipped_action_ids": action_ids,
                "dry_run": dry_run,
            },
            "next_actions": [
                "Re-run with confirm=True once you approve the selected actions."
            ],
            "errors": ["confirm=True is required when dry_run is False."],
        }

    if not action_ids:
        return {
            "summary": "No action IDs provided.",
            "result": {
                "created_count": 0,
                "created_event_ids": [],
                "skipped_action_ids": [],
                "dry_run": dry_run,
            },
            "next_actions": ["Provide action IDs to apply."],
            "errors": ["action_ids is required."],
        }

    try:
        plan_data = ch._load_plan(plan_id)
    except FileNotFoundError as exc:
        return {
            "summary": "Plan file not found.",
            "result": {
                "created_count": 0,
                "created_event_ids": [],
                "skipped_action_ids": action_ids,
                "dry_run": dry_run,
            },
            "next_actions": ["Generate a plan before applying."],
            "errors": [str(exc)],
        }

    if plan_data.get("data_source") != "mcp":
        return {
            "summary": "Plan generated without MCP data; apply blocked.",
            "result": {
                "created_count": 0,
                "created_event_ids": [],
                "skipped_action_ids": action_ids,
                "dry_run": dry_run,
            },
            "next_actions": ["Regenerate the plan with MCP available."],
            "errors": ["Plan data_source is not mcp."],
        }

    window = plan_data.get("time_window", {})
    window_start = _parse_iso(window.get("start", ""))
    window_end = _parse_iso(window.get("end", ""))
    if not window_start or not window_end:
        return {
            "summary": "Plan time window is invalid.",
            "result": {
                "created_count": 0,
                "created_event_ids": [],
                "skipped_action_ids": action_ids,
                "dry_run": dry_run,
            },
            "next_actions": ["Regenerate the plan."],
            "errors": ["Missing or invalid time_window in plan."],
        }

    actions = plan_data.get("proposed_actions", [])
    action_map = {action.get("action_id"): action for action in actions}

    created_ids: List[str] = []
    skipped: List[str] = []
    errors: List[str] = []

    for action_id in action_ids:
        action = action_map.get(action_id)
        if not action:
            skipped.append(action_id)
            errors.append(f"Action {action_id} not found in plan.")
            continue
        if action.get("type") != "create_block":
            skipped.append(action_id)
            errors.append(f"Action {action_id} is not create_block.")
            continue
        start = _parse_iso(action.get("start", ""))
        end = _parse_iso(action.get("end", ""))
        if not start or not end:
            skipped.append(action_id)
            errors.append(f"Action {action_id} missing start/end.")
            continue
        if start < window_start or end > window_end:
            skipped.append(action_id)
            errors.append(f"Action {action_id} outside plan time window.")
            continue

        if dry_run:
            created_ids.append(f"dry-run:{action_id}")
            continue

        try:
            result = ch._apply_create_block(action, plan_data.get("calendar_id") or "primary")
            created_ids.append(result)
        except Exception as exc:  # noqa: BLE001
            skipped.append(action_id)
            errors.append(f"Action {action_id} failed: {exc}")

    summary = (
        f"{'Dry-run' if dry_run else 'Applied'} "
        f"{len(created_ids)} action(s); {len(skipped)} skipped."
    )

    return {
        "summary": summary,
        "result": {
            "created_count": len(created_ids),
            "created_event_ids": created_ids,
            "skipped_action_ids": skipped,
            "dry_run": dry_run,
        },
        "next_actions": (
            ["Run apply with confirm=True to execute writes."]
            if dry_run
            else ["Review created blocks in calendar."]
        ),
        "errors": errors,
    }


def _print_response(response: Dict[str, Any]) -> None:
    print(json.dumps(response, indent=2, ensure_ascii=True))


def _parse_action_ids(value: str | None) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Calendar Hygiene MCP wrapper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Generate a plan.")
    plan_parser.add_argument("--days", type=int, default=7)
    plan_parser.add_argument("--calendar-id")
    plan_parser.add_argument("--verbose", action="store_true")

    apply_parser = subparsers.add_parser("apply", help="Apply selected actions.")
    apply_parser.add_argument("--plan-id", required=True)
    apply_parser.add_argument("--actions", required=True)
    apply_parser.add_argument(
        "--dry-run", action="store_true", help="Show actions without writing."
    )
    apply_parser.add_argument(
        "--execute", action="store_true", help="Apply changes (requires --confirm)."
    )
    apply_parser.add_argument("--confirm", action="store_true", default=False)

    args = parser.parse_args()

    if args.command == "plan":
        response = plan(args.days, args.calendar_id, args.verbose)
        _print_response(response)
        return 0

    if args.execute and args.dry_run:
        print("Choose either --execute or --dry-run, not both.", file=sys.stderr)
        return 2

    dry_run = True
    if args.execute:
        dry_run = False
    elif args.dry_run:
        dry_run = True

    action_ids = _parse_action_ids(args.actions)
    response = apply(args.plan_id, action_ids, dry_run, args.confirm)
    _print_response(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
