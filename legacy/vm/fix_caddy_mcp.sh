#!/usr/bin/env bash
# DEPRECATED: moved to legacy/vm during cleanup. Use canonical vm/ scripts instead.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config.sh"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Missing vm/config.sh. Copy vm/config.example.sh first." >&2
  exit 1
fi

# shellcheck source=/dev/null
source "$CONFIG_FILE"

if [[ -z "${VM_HOST:-}" || -z "${VM_USER:-}" || -z "${VM_SSH_KEY:-}" ]]; then
  echo "Missing VM_HOST, VM_USER, or VM_SSH_KEY in vm/config.sh." >&2
  exit 1
fi

MCP_HOST="mcp-lina.duckdns.org"
MCP_URL="${VM_MCP_URL:-https://mcp-lina.duckdns.org/mcp}"
MCP_PORT="${VM_MCP_PORT:-}"

ssh -i "$VM_SSH_KEY" "$VM_USER@$VM_HOST" <<EOSSH
set -euo pipefail

CADDYFILE="/etc/caddy/Caddyfile"
HOST="$MCP_HOST"
PORT="$MCP_PORT"

if [ -z "${PORT}" ]; then
  if sudo ss -lntp | grep -q ':8000'; then
    PORT="8000"
  elif sudo ss -lntp | grep -q ':8001'; then
    PORT="8001"
  else
    PORT="8000"
    echo "WARN: Could not detect MCP port, defaulting to 8000." >&2
  fi
fi

echo "Using MCP port: $PORT"

if [ ! -f "$CADDYFILE" ]; then
  echo "Missing $CADDYFILE" >&2
  exit 1
fi

STAMP=$(date +%Y%m%d-%H%M%S)
sudo cp -a "$CADDYFILE" "$CADDYFILE.bak.$STAMP"

echo "Patching Caddyfile for /mcp proxy..."

sudo python3 - <<PY
import re
from pathlib import Path

path = Path("$CADDYFILE")
text = path.read_text(encoding="utf-8")
host = "$MCP_HOST"
port = "$PORT"

if re.search(r"handle_path?\s+/mcp", text):
    print("Found existing /mcp handler; no changes made.")
else:
    lines = text.splitlines()
    block = None
    host_line = None
    for i, line in enumerate(lines):
        if host in line:
            host_line = i
            break

    def insert_snippet(start_idx: int) -> None:
        indent = "  "
        snippet = [
            f"{indent}handle /mcp* {{",
            f"{indent}  reverse_proxy 127.0.0.1:{port}",
            f"{indent}}}",
            "",
        ]
        for offset, entry in enumerate(snippet):
            lines.insert(start_idx + 1 + offset, entry)

    if host_line is None:
        lines.append("")
        lines.append(f"{host} {{")
        lines.append(f"  handle /mcp* {{")
        lines.append(f"    reverse_proxy 127.0.0.1:{port}")
        lines.append("  }")
        lines.append("}")
    else:
        # find opening brace
        open_idx = host_line
        if "{" not in lines[open_idx]:
            while open_idx < len(lines) and "{" not in lines[open_idx]:
                open_idx += 1
        if open_idx >= len(lines):
            raise SystemExit("Could not find opening brace for host block.")

        depth = lines[open_idx].count("{") - lines[open_idx].count("}")
        close_idx = None
        for j in range(open_idx + 1, len(lines)):
            depth += lines[j].count("{") - lines[j].count("}")
            if depth == 0:
                close_idx = j
                break
        if close_idx is None:
            raise SystemExit("Could not find closing brace for host block.")

        insert_snippet(open_idx)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

sudo caddy validate --config "$CADDYFILE"

if sudo systemctl reload caddy; then
  echo "Caddy reloaded."
else
  echo "Reload failed; restarting Caddy." >&2
  sudo systemctl restart caddy
fi

echo "Post-check MCP health_check via $MCP_URL"
curl -sS -w "\nHTTP_STATUS:%{http_code}\n" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"health_check","arguments":{}}}' \
  "$MCP_URL" || true
EOSSH
