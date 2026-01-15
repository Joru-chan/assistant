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

if [[ -z "${VM_HOST:-}" || -z "${VM_USER:-}" || -z "${VM_SSH_KEY:-}" || -z "${VM_SERVICE:-}" ]]; then
  echo "Missing VM_HOST, VM_USER, VM_SSH_KEY, or VM_SERVICE in vm/config.sh." >&2
  exit 1
fi

ssh -i "$VM_SSH_KEY" "$VM_USER@$VM_HOST" <<'REMOTE'
set -euo pipefail
SERVICE_NAME="mcp-server.service"
MOOD_URL=$(systemctl show "$SERVICE_NAME" | sed -n 's/^Environment=MOOD_MEMORY_WEBHOOK_URL=\(.*\)$/\1/p' | head -n 1)
if [[ -z "$MOOD_URL" ]]; then
  echo "❌ MOOD_MEMORY_WEBHOOK_URL not set in service."
  exit 1
fi

echo "Using MOOD_MEMORY_WEBHOOK_URL: $MOOD_URL"
curl -s "$MOOD_URL" \
  -H "Content-Type: application/json" \
  -d '{"mood":"test_mood_from_ui","source":"toolbox-ui"}'
REMOTE
