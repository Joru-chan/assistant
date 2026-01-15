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

if [[ -z "${VM_HOST:-}" || -z "${VM_USER:-}" || -z "${VM_SSH_KEY:-}" || -z "${VM_DEST_DIR:-}" ]]; then
  echo "Missing VM_HOST, VM_USER, VM_SSH_KEY, or VM_DEST_DIR in vm/config.sh." >&2
  exit 1
fi

DOC_FILE="${VM_DOC_FILE:-/home/ubuntu/MCP_SYSTEM_OVERVIEW.md}"
ROADMAP_FILE="${VM_ROADMAP_FILE:-/home/ubuntu/MCP_ROADMAP.md}"
SERVICE_NAME="${VM_SERVICE:-mcp-server.service}"
PROJECT_DIR="$VM_DEST_DIR"
MCP_HTTPS_URL="${VM_MCP_URL:-https://mcp-lina.duckdns.org/mcp}"
MCP_LOCAL_URL="${VM_MCP_LOCAL_URL:-http://127.0.0.1:8000/mcp}"

ssh -i "$VM_SSH_KEY" "$VM_USER@$VM_HOST" \
  "DOC_FILE='$DOC_FILE' ROADMAP_FILE='$ROADMAP_FILE' SERVICE_NAME='$SERVICE_NAME' PROJECT_DIR='$PROJECT_DIR' MCP_HTTPS_URL='$MCP_HTTPS_URL' MCP_LOCAL_URL='$MCP_LOCAL_URL' bash -lc 'set -euo pipefail;\
    cat << DOC > "$DOC_FILE"\
# Lina Serendipity MCP System Overview\
\
_Last generated: $(date -Iseconds)_\
\
## 1. High-Level Architecture\
\
- **Client**: Poke (Interaction app via iMessage), with MCP support.\
- **MCP Server**: FastMCP-based HTTP server on this VM.\
  - Local: $MCP_LOCAL_URL\
  - Public via Caddy: $MCP_HTTPS_URL\
- **Automations / Memory**: n8n running on this VM.\
- **Storage**: Google Sheets (mood + serendipity logs).\
\
## 2. MCP Service Details\
\
- **Systemd service**: $SERVICE_NAME\
- **Project directory**: $PROJECT_DIR\
- **ExecStart**: $PROJECT_DIR/venv/bin/python server.py\
- **Transport**: streamable HTTP over /mcp\
\
## 3. Environment Variables (current)\
\
```\
$(systemctl show "$SERVICE_NAME" | grep '^Environment=' || true)\
```\
\
## 4. Roadmap\
\
```\
$(if [[ -f "$ROADMAP_FILE" ]]; then cat "$ROADMAP_FILE"; else echo "(no roadmap yet)"; fi)\
```\
DOC\
    echo "✅ Documentation written to $DOC_FILE"'"
