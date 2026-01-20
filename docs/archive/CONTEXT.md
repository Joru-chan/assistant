# Project Context (Codex)

Last updated: 2026-01-20

## Purpose
- Personal assistant for Jordane Frechet using Codex CLI.
- Personal-life focus; work/career is treated as a personal category, not a separate system.
- `AGENTS.md` is the primary instruction source; `CLAUDE.md` is a workflow reference.

## Identity
- Name: Jordane Frechet
- Primary email: jordane.frechet@gmail.com

## Notion
- Life Atlas database: `1f85ae60-7903-80ef-8503-fa3497160404`
- Assistant HQ page (inside Life Atlas): `2e85ae60-7903-81b9-8fbc-c719c3b9c46a`

### Assistant HQ Databases
- Personal Tasks: `2e85ae60-7903-8103-a2b5-f3961e369cfb`
- Projects: `2e85ae60-7903-81c4-9798-f583477ca854`
- Habits & Routines: `2e85ae60-7903-814b-b893-d43c809845b3`
- Health & Medical: `2e85ae60-7903-8102-98e4-d5575108a601`
- Finance & Bills: `2e85ae60-7903-81a7-bc63-e7516f555620`
- Daily Log: `2e85ae60-7903-813a-9a32-ecd7ed4f3507`
- Tool Requests / Friction Log DB ID: `2e85ae60-7903-8040-809e-ed82409e73d0`
- Tool Requests / Friction Log DB URL: `https://www.notion.so/2e85ae6079038040809eed82409e73d0?v=2e85ae60790380708681000c66e3c423`

## MCP Integrations
- Notion MCP: `notion-mcp` configured via `codex mcp add`.
  - If using nvm, set PATH to Node 20+ in the MCP command.
- Google Workspace MCP: `mcp-gsuite-enhanced` configured via `codex mcp add`.
  - Uses local venv executable at `mcp-gsuite-enhanced/.venv/bin/mcp-gsuite-enhanced`.
  - OAuth files live locally in `mcp-gsuite-enhanced/` and are gitignored.

## VM Deployment
- VM Host: 134.98.141.19 (mcp-lina.duckdns.org)
- Deployment: Auto-deploys on `git push origin main` via post-push hook
- Configuration: `vm/config.sh` (gitignored, copy from `vm/config.example.sh`)
- Manual deployment: `./vm/deploy.sh`
- Service: `mcp-server.service` on Ubuntu VM
- Health check: `./vm/health_check.sh` or `https://mcp-lina.duckdns.org/health`

## Scripts
- `scripts/personal_task_analyzer.py` (Personal Tasks)
- `scripts/personal_project_analyzer.py` (Projects)
- `scripts/work_task_analyzer.py` is deprecated (legacy work flow).

## Templates
- `templates/weekly_planning_template.md` (personal weekly planning)
- `templates/sprint_planning_template.md` (legacy work template)

## Notes
- Keep secrets out of git; credentials are stored locally via env vars and ignored files.
