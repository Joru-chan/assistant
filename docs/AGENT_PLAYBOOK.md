# Agent Playbook (Codex)

Hard rules for fulfilment and planning.

## Always-on rules
- Default read-only/dry-run. Writes require explicit confirm flags.
- If the user says “plan” or “start with the plan”, do **not** implement.
- Tools must include “How to use” (inputs + 2-3 example calls).
- Scripts fetch/apply; the agent decides and asks questions before implementing.

## Fulfilment flow (build/fulfil requests)
When the user asks to build/fulfil:
1) Fetch Tool Requests candidates (latest + search).
2) Present top 5 with brief rationale.
3) Ask for confirmation of the selection.
4) Ask for constraints/requirements.
5) Produce a plan (include Inputs/UX/Capture workflow).
6) Stop unless explicitly told to implement.

## Plan-first behavior
If the user asks to plan (or says “start with the plan”), do not implement. Provide plan only.

## Plan-only guard (enforced)
- Any request containing plan/outline phrasing triggers a hard guard.
- The agent stops after showing candidates, selected suggestion, questions, and the plan outline.
- The guard sets `plan_only=true` and blocks writes, scaffold, Notion updates, deploys, and shell commands—even if `--execute` is supplied.

## Tool design requirements
- Include a “How to use” section in tool specs.
- Provide inputs + 2-3 example calls.
- Keep v0 minimal.
- Read-only by default; apply requires explicit confirmation.
