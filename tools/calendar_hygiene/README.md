# Calendar Hygiene Assistant

## Purpose
Reduce calendar chaos by generating safe, reviewable cleanup recommendations for
the next 7 days (buffer blocks, annotations, and context reminders).

## Non-goals
- Rescheduling events or deleting anything.
- Sending emails, messages, or RSVP updates.
- Modifying calendars without explicit approval.

## Inputs
- `--days` (default: 7) number of days to analyze.
- `--calendar-id` (default: `primary`) which calendar to read/write.
- `--verbose` (plan mode) print fetch details and heuristic traces.
- `--plan-id` (apply mode) date identifier in `YYYY-MM-DD` format.
- `--actions` (apply mode) comma-separated action IDs to apply.
- `--dry-run` (apply mode) show what would be created without writing.

## Output contract
Both the CLI stdout and the plan JSON follow:
- `summary`: short human-readable overview.
- `result`: structured plan metadata and counts.
- `next_actions`: explicit manual steps or approvals.
- `errors`: any failures, including MCP connectivity.
- Each proposed action includes `reasoning` and `confidence` (0-1).

## Safety rules
- Read-only by default (`plan`).
- `apply` requires an explicit `--plan-id` and `--actions` list.
- Only allowed writes:
  - create buffer blocks
- Never edit existing events (for now).
- Never delete events.
- Never send emails/messages.

## Heuristics
- Back-to-back buffer: if two events have <=5 minutes gap, propose a
  `suggest_shorten` action for the earlier event (plan-only).
- Medical prep/travel: if title matches medical keywords, propose prep/travel
  blocks (15 min) when slots are free.
- Daily admin/planning anchor: if a day has >=3 events or >=2 hours total,
  propose a 20-minute "Daily planning/admin" block in a free slot (morning
  preferred).

## Test plan
- Smoke:
  1) `python tools/calendar_hygiene/calendar_hygiene.py plan`
  2) Verify `memory/plans/calendar_hygiene/YYYY-MM-DD.json` exists.
- Apply dry review:
  1) `python tools/calendar_hygiene/calendar_hygiene.py apply --plan-id YYYY-MM-DD`
  2) Ensure it lists actions and exits without changes.
- Apply selected actions:
  1) `python tools/calendar_hygiene/calendar_hygiene.py apply --plan-id YYYY-MM-DD --actions action-id`

## Edge cases
- No events in the window.
- Events without descriptions.
- MCP unavailable (mock plan should still be produced).
- Invalid plan ID or action ID.

## Poke/MCP usage
Use the wrapper so Poke receives structured responses without reading local files.

### Plan
Inputs:
- `days` (int, default 7)
- `calendar_id` (string, optional)
- `verbose` (bool, optional)

Output contract:
- `summary`: human-readable result.
- `result`: includes `plan_id`, `time_window`, `events_scanned`, `actions_proposed`,
  and `proposed_actions_preview` (first 5).
- `next_actions`: explicit steps for user approval.
- `errors`: list of errors (if any).

### Apply
Inputs:
- `plan_id` (required)
- `action_ids` (required list)
- `dry_run` (default true)
- `confirm` (required if `dry_run` is false)

Safety wording for Poke:
- Always ask for confirmation before calling apply with `confirm=true`.
- Never apply without explicit user-selected action IDs.
