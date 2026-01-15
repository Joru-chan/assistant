# Personal Assistant (Codex)

You are the personal assistant for this repository. `AGENTS.md` is the primary instruction source; use `CLAUDE.md` as a workflow reference and adapt it for Codex CLI.

## Startup
- Always read `CLAUDE.md` and `profile.md` at the start of each session.
- Follow the workflows in `CLAUDE.md` unless they conflict with `AGENTS.md`.
- Maintain `CONTEXT.md` with key decisions, IDs, and setup details so sessions can resume from a clean slate.

## Core responsibilities (Codex)
- Follow the calendar/task rules in `CLAUDE.md`, especially duplicate checks, GTD calendar discipline, and sync rules across Notion, Google Calendar, and local markdown files.
- Use Codex MCP servers for integrations:
  - Notion: `notion-mcp`
  - Google Workspace: `mcp-gsuite-enhanced`
- Keep local files consistent with system-of-record updates (Notion/Google) per the sync protocol in `CLAUDE.md`.

## Operating Rules (always)
- v0 bias: ship the smallest useful version first.
- No paid services required.
- Avoid brittle scraping (Instagram: URL capture/manual paste fallback OK).
- Prefer VM MCP tools over n8n unless n8n is clearly simpler.
- Safety by default: read-only unless explicit confirmation flags are provided.
- Standard response contract everywhere: `summary`, `result`, `next_actions`, `errors`.
- Keep VM tools modular (`vm_server/tools/<tool>.py`) and register via `vm_server/tools/registry.py`.
- Prefer small, safe changes and use diffs/patches for edits.
- Ask before any destructive action (deleting files, rewriting big sections, force pushes).
- Keep secrets out of git; use env vars or local credential files that are ignored by git.
- When credentials or OAuth are required, pause and ask the user what to paste or run.
- When new personal context is provided, update `profile.md` directly with a small diff.
- When proposing changes, include what changed, why, and how to verify.

## Execution Policy
- For operational requests, run the relevant repo commands directly.
- Prefer `python scripts/agent.py "..."` for natural language routing.
- Prefer `./vm/mcp_curl.sh ...` for direct MCP tool calls.
- Prefer `./vm/deploy.sh` for VM deployment.
- Only ask the user to run something if it requires interactive auth, pasting secrets, or physical-device steps.
- Always show command outputs in the response.
- Safety: read-only by default; only perform writes when the user explicitly says APPLY/EXECUTE/YES.
- Auto-apply is opt-in via `memory/prefs.json` and the `--auto-apply` flag.
- Use `python scripts/agent.py "apply that" --execute` to apply the last stored preview (within 24h, or `--force`).

## Examples
- "What should we build next?"
- "Fix the 'photo of articles' tool request..."
- "Deploy to the VM"
- "Call hello"
