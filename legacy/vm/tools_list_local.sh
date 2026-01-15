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

LOCAL_URL="${VM_MCP_LOCAL_URL:-http://127.0.0.1:8000/mcp}"
PAYLOAD='{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

ssh -i "$VM_SSH_KEY" "$VM_USER@$VM_HOST" \
  "curl -s '$LOCAL_URL' -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -d '$PAYLOAD'"
