# VM Deployment Toolkit

Use these scripts to deploy the local repo to the Ubuntu VM over SSH and
restart the MCP server service.

## Setup
1) Copy the config file and edit values as needed:
   - `cp vm/config.example.sh vm/config.sh`
2) Ensure the SSH key path is correct and readable.
3) Set `VM_LOCAL_SRC` to the local folder that contains the MCP server code
   you want to deploy (defaults to `vm_server/`).

## Scripts
- `vm/ssh.sh`    : open an SSH session to the VM
- `vm/status.sh` : show systemd status + last 50 logs
- `vm/logs.sh`   : tail service logs (journalctl -f)
- `vm/deploy.sh` : rsync code to VM + restart service + health check
- `vm/pull_server_from_vm.sh` : pull the live server code from the VM
- `vm/diagnose_caddy_mcp.sh` : diagnose 502s and proxy config on the VM
- `vm/fix_caddy_mcp.sh` : patch Caddy to proxy /mcp correctly (with backup)

## Deploy behavior
- Uses `rsync` to copy `VM_LOCAL_SRC/` to `VM_DEST_DIR/`.
- Excludes: `venv/`, `__pycache__/`, `*.pyc`, `.env`, `memory/`, `.git`.
- No destructive remote commands (no `rm -rf`, no `--delete`).

## Recommended layout
Keep a dedicated server-only folder for deployment. Default:
- `vm_server/` (contains the MCP server code + requirements for the VM)

Use `vm/pull_server_from_vm.sh` to bootstrap `vm_server/` from the live VM
so it matches `/home/ubuntu/mcp-server-template/src`.

## Pull from VM
Use this to bootstrap or recover the server code from the live VM:
```bash
./vm/pull_server_from_vm.sh
```

## Server environment
The current server expects these env vars (set on the VM, not in git):
- `MOOD_MEMORY_WEBHOOK_URL`
- `SERENDIPITY_EVENT_WEBHOOK_URL`
- `PORT` (default `8000`)
- `MCP_SYSTEM_OVERVIEW.md` at `/home/ubuntu/MCP_SYSTEM_OVERVIEW.md`

## Health check
- Primary: `GET /health` (returns 200 with `{\"ok\": true}`).
- Fallback (if /health is unavailable): call the `health_check` tool via `/mcp`.

## Notes
- `vm/config.sh` is local-only and gitignored.
- Recommended health check URL: `https://mcp-lina.duckdns.org/health`.
- The health check URL is read from `VM_HEALTH_URL` (defaults to `/health`).
- Set `VM_HEALTH_URL` in `vm/config.sh` if your deployment uses a different URL.
- Deploy verifies health by calling the MCP `health_check` tool via `VM_MCP_URL`.
  If that fails, it falls back to the HTTP `/health` endpoint.
- Deploy retries the MCP health check for a few seconds; initial 502s during restart can be normal.
- Deploy runs a dependency sync if `requirements.txt` exists in `VM_DEST_DIR`
  using `VM_VENV_PY` (defaults to `/home/ubuntu/mcp-server-template/src/venv/bin/python`).
- FastMCP streamable HTTP requires `Accept: application/json, text/event-stream`.

## MCP curl helper
Use the wrapper to hit MCP tools with the correct headers:
```bash
./vm/mcp_curl.sh health_check
./vm/mcp_curl.sh tool_requests_latest '{"limit":5}'
```

## Set service env vars
Use the helper script to set Notion env vars on the VM via a systemd drop-in:
```bash
./vm/set_service_env.sh
```
Security note: the token is only written on the VM and never stored in git.

## 502 on /mcp
This usually means Caddy is not proxying `/mcp` to the FastMCP server port
or the service is down. Run:
```bash
./vm/diagnose_caddy_mcp.sh
```
If needed, apply the minimal fix (creates a backup first):
```bash
./vm/fix_caddy_mcp.sh
```
