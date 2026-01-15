#!/usr/bin/env python3
"""
Calendar Hygiene Assistant.

Commands:
  plan  - analyze next 7 days and propose actions (read-only)
  apply - apply selected actions from a plan (explicit only)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

PLAN_DIR = Path("memory/plans/calendar_hygiene")
SCHEMA_VERSION = 1
MEDICAL_KEYWORDS = [
    "doctor",
    "hospital",
    "appointment",
    "mri",
    "clinic",
    "physio",
    "physiotherapy",
    "neurologist",
    "infusion",
    "dentist",
    "therapy",
    "scan",
    "surgery",
    "lab",
    "bloodwork",
]
PRIVATE_TITLES = {"busy", "private", "unavailable"}


@dataclass
class Event:
    event_id: str
    title: str
    start: datetime
    end: datetime
    description: str = ""
    location: str = ""
    is_all_day: bool = False
    is_private: bool = False


def _load_env() -> None:
    if load_dotenv:
        load_dotenv()


def _run_codex(prompt: str, *, verbose: bool, progress: bool, label: str) -> str:
    from utils.progress import run_command

    try:
        returncode, output = run_command(
            ["codex", "exec", prompt],
            label=label,
            verbose=verbose,
            progress=progress,
        )
    except FileNotFoundError:
        raise RuntimeError("codex CLI not found on PATH.")

    if returncode != 0:
        raise RuntimeError(output or "codex exec failed.")

    return output.strip()


def _extract_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(1))


def _parse_iso(dt_value: str) -> datetime | None:
    if not dt_value:
        return None
    try:
        parsed = datetime.fromisoformat(dt_value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _event_from_raw(raw: Dict[str, Any]) -> Event | None:
    title = (raw.get("title") or raw.get("summary") or "Untitled").strip()
    event_id = str(raw.get("id") or "").strip()
    start_val = raw.get("start")
    end_val = raw.get("end")
    is_all_day = False

    if isinstance(start_val, dict):
        is_all_day = "date" in start_val and "dateTime" not in start_val
        start_val = start_val.get("dateTime") or start_val.get("date")
    if isinstance(end_val, dict):
        end_val = end_val.get("dateTime") or end_val.get("date")

    if isinstance(start_val, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", start_val):
        is_all_day = True
    if isinstance(end_val, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", end_val):
        is_all_day = True

    start = _parse_iso(str(start_val or ""))
    end = _parse_iso(str(end_val or ""))
    if not start or not end:
        return None

    visibility = str(raw.get("visibility") or "").lower()
    is_private = title.lower() in PRIVATE_TITLES or visibility == "private"

    return Event(
        event_id=event_id,
        title=title,
        start=start,
        end=end,
        description=str(raw.get("description") or ""),
        location=str(raw.get("location") or ""),
        is_all_day=is_all_day,
        is_private=is_private,
    )


def _fetch_events(
    start_iso: str,
    end_iso: str,
    calendar_id: str,
    verbose: bool,
    progress: bool,
) -> Tuple[List[Event], List[str], int]:
    prompt = (
        "Using mcp-gsuite-enhanced, list calendar events between "
        f"{start_iso} and {end_iso} for calendar_id '{calendar_id}'. "
        "Return JSON only as an array of objects with fields: "
        "id, title, start, end, description, location."
    )
    try:
        output = _run_codex(
            prompt,
            verbose=verbose,
            progress=progress,
            label="Google Calendar MCP: list events",
        )
        data = _extract_json(output)
        raw_events = data if isinstance(data, list) else data.get("results", [])
        events = [event for raw in raw_events if (event := _event_from_raw(raw))]
        return events, [], len(raw_events)
    except Exception as exc:  # noqa: BLE001 - single fallback
        return [], [str(exc)], 0


def _mock_events(start: datetime) -> List[Event]:
    base = start.replace(hour=9, minute=0, second=0, microsecond=0)
    return [
        Event(
            event_id="mock-1",
            title="Medical appointment",
            start=base + timedelta(days=1, hours=2),
            end=base + timedelta(days=1, hours=3),
            description="",
        ),
        Event(
            event_id="mock-2",
            title="Team sync meeting",
            start=base + timedelta(days=2, hours=1),
            end=base + timedelta(days=2, hours=2),
            description="",
        ),
    ]


def _filter_events(events: List[Event]) -> Tuple[List[Event], Dict[str, int]]:
    stats = {
        "total": len(events),
        "all_day_excluded": 0,
        "private_count": 0,
    }
    filtered = []
    for event in events:
        if event.is_private:
            stats["private_count"] += 1
        if event.is_all_day:
            stats["all_day_excluded"] += 1
            continue
        filtered.append(event)
    return filtered, stats


def _overlaps(
    start: datetime, end: datetime, events: List[Event], exclude_id: str | None = None
) -> bool:
    for event in events:
        if exclude_id and event.event_id == exclude_id:
            continue
        if start < event.end and end > event.start:
            return True
    return False


def _event_duration_minutes(event: Event) -> float:
    return (event.end - event.start).total_seconds() / 60


def _find_free_slot(
    events: List[Event],
    window_start: datetime,
    window_end: datetime,
    duration_minutes: int,
    blocked_intervals: List[Tuple[datetime, datetime]] | None = None,
) -> datetime | None:
    if window_end <= window_start:
        return None
    duration = timedelta(minutes=duration_minutes)
    intervals: List[Tuple[datetime, datetime]] = [
        (event.start, event.end)
        for event in events
        if event.end > window_start and event.start < window_end
    ]
    if blocked_intervals:
        intervals.extend(blocked_intervals)
    intervals.sort(key=lambda item: item[0])

    cursor = window_start
    for start, end in intervals:
        if cursor + duration <= start:
            return cursor
        if end > cursor:
            cursor = end
    if cursor + duration <= window_end:
        return cursor
    return None

def _action_id(seed: str) -> str:
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]
    return f"act-{digest}"


def _medical_keywords(title: str) -> List[str]:
    title_lower = title.lower()
    return [keyword for keyword in MEDICAL_KEYWORDS if keyword in title_lower]


def _build_actions(
    events: List[Event],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    actions: List[Dict[str, Any]] = []
    debug_lines: List[str] = []
    events_sorted = sorted(events, key=lambda event: event.start)
    blocked_intervals: List[Tuple[datetime, datetime]] = []

    def slot_free(start: datetime, end: datetime, exclude_event_id: str | None = None) -> bool:
        if _overlaps(start, end, events, exclude_id=exclude_event_id):
            return False
        for block_start, block_end in blocked_intervals:
            if start < block_end and end > block_start:
                return False
        return True

    def reserve_slot(start: datetime, end: datetime) -> None:
        blocked_intervals.append((start, end))

    # Heuristic A: back-to-back buffer or shorten suggestion.
    for current, next_event in zip(events_sorted, events_sorted[1:]):
        gap_minutes = (next_event.start - current.end).total_seconds() / 60
        if gap_minutes < 0:
            debug_lines.append(
                f"[Back-to-back] {current.title} -> {next_event.title}: overlap ({gap_minutes:.1f}m); no action."
            )
            continue
        if gap_minutes <= 5:
            seed = f"suggest_shorten:{current.event_id}:{next_event.event_id}:{current.end.isoformat()}"
            actions.append(
                {
                    "action_id": _action_id(seed),
                    "type": "suggest_shorten",
                    "target_event_id": current.event_id,
                    "minutes": 5,
                    "reason": "Back-to-back events with no buffer.",
                    "reasoning": (
                        f"Gap is {gap_minutes:.1f} minutes between "
                        f"'{current.title}' and '{next_event.title}'."
                    ),
                    "confidence": 0.4,
                    "risk": "low",
                }
            )
            debug_lines.append(
                f"[Back-to-back] {current.title} -> {next_event.title}: gap {gap_minutes:.1f}m; suggest shorten."
            )
        else:
            debug_lines.append(
                f"[Back-to-back] {current.title} -> {next_event.title}: gap {gap_minutes:.1f}m; no action."
            )

    # Heuristic B: medical prep + travel blocks.
    for event in events_sorted:
        if event.is_private:
            debug_lines.append(
                f"[Medical] {event.title}: private event; keyword heuristics skipped."
            )
            continue

        keywords = _medical_keywords(event.title)
        if not keywords:
            debug_lines.append(
                f"[Medical] {event.title}: no medical keywords matched."
            )
            continue

        prep_start = event.start - timedelta(minutes=15)
        prep_end = event.start
        if slot_free(prep_start, prep_end, exclude_event_id=event.event_id):
            seed = f"create_block:prep:{event.event_id}:{event.start.isoformat()}"
            prep_title = (
                f"Prep/Travel to {event.location}"
                if event.location
                else f"Prep: {event.title}"
            )
            prep_reason = (
                "Prep/travel buffer before appointment."
                if event.location
                else "Medical prep buffer before appointment."
            )
            actions.append(
                {
                    "action_id": _action_id(seed),
                    "type": "create_block",
                    "start": prep_start.isoformat(),
                    "end": prep_end.isoformat(),
                    "title": prep_title,
                    "reason": prep_reason,
                    "reasoning": f"Keyword match: {', '.join(keywords)}.",
                    "confidence": 0.7,
                    "risk": "low",
                    "related_event_id": event.event_id,
                }
            )
            reserve_slot(prep_start, prep_end)
            debug_lines.append(
                f"[Medical] {event.title}: prep block proposed."
            )
        else:
            debug_lines.append(
                f"[Medical] {event.title}: prep block skipped (slot overlaps)."
            )

        if event.location:
            travel_after_start = event.end
            travel_after_end = event.end + timedelta(minutes=15)
            if slot_free(
                travel_after_start, travel_after_end, exclude_event_id=event.event_id
            ):
                seed = (
                    f"create_block:travel_from:{event.event_id}:{event.end.isoformat()}"
                )
                actions.append(
                    {
                        "action_id": _action_id(seed),
                        "type": "create_block",
                        "start": travel_after_start.isoformat(),
                        "end": travel_after_end.isoformat(),
                        "title": f"Travel from {event.location}",
                        "reason": "Travel buffer after medical appointment.",
                        "reasoning": "Location present; add travel buffer.",
                        "confidence": 0.7,
                        "risk": "low",
                        "related_event_id": event.event_id,
                    }
                )
                reserve_slot(travel_after_start, travel_after_end)
                debug_lines.append(
                    f"[Medical] {event.title}: travel-from block proposed."
                )
            else:
                debug_lines.append(
                    f"[Medical] {event.title}: travel-from block skipped (slot overlaps)."
                )

    # Heuristic C: daily planning/admin anchor.
    events_by_day: Dict[str, List[Event]] = {}
    for event in events_sorted:
        day_key = event.start.date().isoformat()
        events_by_day.setdefault(day_key, []).append(event)

    for day_key, day_events in sorted(events_by_day.items()):
        total_minutes = sum(_event_duration_minutes(event) for event in day_events)
        qualifies = len(day_events) >= 3 or total_minutes >= 120
        if not qualifies:
            debug_lines.append(
                f"[Daily anchor] {day_key}: {len(day_events)} events, {total_minutes:.0f}m; no action."
            )
            continue

        if any("daily planning" in event.title.lower() for event in day_events):
            debug_lines.append(
                f"[Daily anchor] {day_key}: planning block already exists; no action."
            )
            continue

        tz = day_events[0].start.tzinfo or timezone.utc
        morning_start = datetime.fromisoformat(day_key).replace(
            hour=8, minute=30, tzinfo=tz
        )
        morning_end = datetime.fromisoformat(day_key).replace(
            hour=11, minute=30, tzinfo=tz
        )
        slot = _find_free_slot(
            day_events, morning_start, morning_end, 20, blocked_intervals
        )
        if slot is None:
            afternoon_start = datetime.fromisoformat(day_key).replace(
                hour=13, minute=0, tzinfo=tz
            )
            afternoon_end = datetime.fromisoformat(day_key).replace(
                hour=17, minute=30, tzinfo=tz
            )
            slot = _find_free_slot(
                day_events, afternoon_start, afternoon_end, 20, blocked_intervals
            )

        if slot is None:
            debug_lines.append(
                f"[Daily anchor] {day_key}: qualified but no free 20m slot found."
            )
            continue

        seed = f"create_block:daily_admin:{day_key}:{slot.isoformat()}"
        actions.append(
            {
                "action_id": _action_id(seed),
                "type": "create_block",
                "start": slot.isoformat(),
                "end": (slot + timedelta(minutes=20)).isoformat(),
                "title": "Daily planning/admin",
                "reason": "High-activity day needs a planning anchor.",
                "reasoning": (
                    f"{len(day_events)} events totaling {total_minutes:.0f} minutes."
                ),
                "confidence": 0.5,
                "risk": "low",
            }
        )
        reserve_slot(slot, slot + timedelta(minutes=20))
        debug_lines.append(
            f"[Daily anchor] {day_key}: planning block proposed at {slot.time()}."
        )

    return actions, debug_lines


def build_plan(
    events: List[Event],
    time_window: Dict[str, str],
    calendar_id: str,
    data_source: str,
    errors: List[str],
    actions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    date_str = time_window["start"].split("T")[0]
    plan_id = date_str
    summary = (
        f"Proposed {len(actions)} action(s) from {len(events)} event(s)."
        if actions
        else f"No actions proposed from {len(events)} event(s)."
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "plan_id": plan_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "time_window": time_window,
        "calendar_id": calendar_id,
        "data_source": data_source,
        "summary": summary,
        "result": {
            "events_analyzed": len(events),
            "proposed_actions": len(actions),
            "action_types": list({action["type"] for action in actions}),
        },
        "next_actions": [
            "Review proposed actions in the plan file.",
            "Apply selected actions with --plan-id and --actions.",
        ],
        "errors": errors,
        "events": [
            {
                "id": event.event_id,
                "title": event.title,
                "start": event.start.isoformat(),
                "end": event.end.isoformat(),
                "description": event.description,
                "location": event.location,
            }
            for event in events
        ],
        "proposed_actions": actions,
    }


def _write_plan(plan: Dict[str, Any]) -> Path:
    PLAN_DIR.mkdir(parents=True, exist_ok=True)
    date_str = plan["plan_id"]
    path = PLAN_DIR / f"{date_str}.json"
    path.write_text(json.dumps(plan, indent=2, ensure_ascii=True), encoding="utf-8")
    return path


def _load_plan(plan_id: str) -> Dict[str, Any]:
    path = PLAN_DIR / f"{plan_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Plan file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _apply_create_block(
    action: Dict[str, Any],
    calendar_id: str,
    verbose: bool,
    progress: bool,
) -> str:
    prompt = (
        "Using mcp-gsuite-enhanced, create a calendar event "
        f"on calendar_id '{calendar_id}' with title '{action['title']}', "
        f"start '{action['start']}', end '{action['end']}', "
        "and description 'Buffer block created by Calendar Hygiene Assistant.' "
        "Return the created event id."
    )
    return _run_codex(
        prompt,
        verbose=verbose,
        progress=progress,
        label="Google Calendar MCP: create block",
    )


def _apply_actions(
    plan: Dict[str, Any],
    action_ids: List[str],
    verbose: bool,
    progress: bool,
) -> Dict[str, Any]:
    if plan.get("data_source") != "mcp":
        raise RuntimeError("Plan was generated without MCP data; apply aborted.")

    calendar_id = plan.get("calendar_id") or "primary"
    actions = plan.get("proposed_actions", [])
    action_map = {action["action_id"]: action for action in actions}

    results = {"applied": [], "failed": []}
    for action_id in action_ids:
        action = action_map.get(action_id)
        if not action:
            results["failed"].append(
                {"action_id": action_id, "error": "Action not found in plan."}
            )
            continue
        try:
            if action["type"] != "create_block":
                raise RuntimeError(
                    f"Unsupported action type for apply: {action['type']}"
                )
            result = _apply_create_block(action, calendar_id, verbose, progress)
            results["applied"].append({"action_id": action_id, "result": result})
        except Exception as exc:  # noqa: BLE001
            results["failed"].append({"action_id": action_id, "error": str(exc)})
    return results


def _format_action_list(actions: List[Dict[str, Any]]) -> str:
    lines = []
    for action in actions:
        reason = action.get("reason", "")
        lines.append(f"- {action['action_id']}: {action['type']} ({reason})")
    return "\n".join(lines) if lines else "No actions proposed."


def _plan_command(args: argparse.Namespace) -> int:
    now = datetime.now(timezone.utc)
    start = now
    end = now + timedelta(days=args.days)
    start_iso = start.isoformat()
    end_iso = end.isoformat()

    events, errors, raw_count = _fetch_events(
        start_iso,
        end_iso,
        args.calendar_id,
        verbose=args.verbose,
        progress=args.progress,
    )
    data_source = "mcp"
    if errors:
        events = _mock_events(start)
        data_source = "mock"
        raw_count = len(events)

    events, stats = _filter_events(events)
    actions, debug_lines = _build_actions(events)
    time_window = {"start": start_iso, "end": end_iso}
    plan = build_plan(
        events, time_window, args.calendar_id, data_source, errors, actions
    )
    path = _write_plan(plan)

    print(
        f"Plan saved to {path}. Events scanned: {len(events)}. "
        f"Actions proposed: {len(plan['proposed_actions'])}. Data source: {data_source}."
    )
    if errors:
        print("MCP unavailable; plan generated from mock inputs.")
    if args.verbose:
        print("")
        print("Debug:")
        print(f"- Calendar(s): {args.calendar_id}")
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
    return 0


def _apply_command(args: argparse.Namespace) -> int:
    try:
        plan = _load_plan(args.plan_id)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    actions = plan.get("proposed_actions", [])
    if args.dry_run and not args.actions:
        print("Dry-run: proposed create_block actions:")
        print(_format_action_list([a for a in actions if a.get("type") == "create_block"]))
        return 0

    if not args.actions:
        print("No actions selected. Available actions:")
        print(_format_action_list(actions))
        return 2

    action_ids = [item.strip() for item in args.actions.split(",") if item.strip()]
    if args.dry_run:
        print("Dry-run: would apply actions:")
        print(_format_action_list([a for a in actions if a.get("action_id") in action_ids]))
        return 0

    try:
        results = _apply_actions(
            plan, action_ids, verbose=args.verbose, progress=args.progress
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(
        f"Applied: {len(results['applied'])}, Failed: {len(results['failed'])}."
    )
    if results["failed"]:
        print(json.dumps(results["failed"], indent=2))
        return 1
    return 0


def main() -> int:
    _load_env()
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        "--verbose", action="store_true", help="Show verbose output."
    )
    common_parser.add_argument(
        "--progress",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable progress spinners.",
    )

    parser = argparse.ArgumentParser(description="Calendar Hygiene Assistant.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser(
        "plan", help="Generate a plan (read-only).", parents=[common_parser]
    )
    plan_parser.add_argument("--days", type=int, default=7)
    plan_parser.add_argument("--calendar-id", default="primary")
    plan_parser.set_defaults(func=_plan_command)

    apply_parser = subparsers.add_parser(
        "apply", help="Apply selected actions.", parents=[common_parser]
    )
    apply_parser.add_argument("--plan-id", required=True)
    apply_parser.add_argument("--actions", help="Comma-separated action IDs to apply.")
    apply_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without writing.",
    )
    apply_parser.set_defaults(func=_apply_command)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
