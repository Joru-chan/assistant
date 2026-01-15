#!/usr/bin/env bash
# DEPRECATED: moved to legacy/vm during cleanup. Use canonical vm/ scripts instead.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config.sh"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Missing vm/config.sh. Copy vm/config.example.sh first." >&2
  exit 1
fi

# shellcheck source=/dev/null
source "$CONFIG_FILE"

if [[ -z "${VM_HOST:-}" || -z "${VM_USER:-}" || -z "${VM_SSH_KEY:-}" || -z "${VM_SERVICE:-}" ]]; then
  echo "Missing required VM_* variables in vm/config.sh." >&2
  exit 1
fi

read -r -s -p "NOTION_TOKEN: " notion_token_input || true
if [[ -n "${NOTION_TOKEN:-}" ]]; then
  NOTION_TOKEN="$NOTION_TOKEN"
elif [[ -n "$notion_token_input" ]]; then
  NOTION_TOKEN="$notion_token_input"
else
  echo >&2
  echo "NOTION_TOKEN is required." >&2
  exit 1
fi
echo

if [[ -n "${TOOL_REQUESTS_DB_ID:-}" ]]; then
  TOOL_REQUESTS_DB_ID="$TOOL_REQUESTS_DB_ID"
else
  read -r -p "TOOL_REQUESTS_DB_ID: " TOOL_REQUESTS_DB_ID
fi

if [[ -z "${TOOL_REQUESTS_DB_ID:-}" ]]; then
  echo "TOOL_REQUESTS_DB_ID is required." >&2
  exit 1
fi

escape_env() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

DROPIN_DIR="/etc/systemd/system/${VM_SERVICE}.d"
REMOTE_ENV_FILE="$DROPIN_DIR/env.conf"
VENV_PY="${VM_VENV_PY:-/home/ubuntu/mcp-server-template/src/venv/bin/python}"

tmp_file="$(mktemp)"
cat >"$tmp_file" <<EOF
[Service]
Environment="NOTION_TOKEN=$(escape_env "$NOTION_TOKEN")"
Environment="TOOL_REQUESTS_DB_ID=$(escape_env "$TOOL_REQUESTS_DB_ID")"
EOF

echo "Updating systemd drop-in on $VM_HOST..."
ssh -i "$VM_SSH_KEY" "$VM_USER@$VM_HOST" \
  "sudo mkdir -p '$DROPIN_DIR' && sudo tee '$REMOTE_ENV_FILE' >/dev/null" <"$tmp_file"
rm -f "$tmp_file"

echo "Reloading and restarting $VM_SERVICE"
ssh -i "$VM_SSH_KEY" "$VM_USER@$VM_HOST" \
  "sudo systemctl daemon-reload && sudo systemctl restart '$VM_SERVICE'"

echo "Service drop-in (token redacted):"
ssh -i "$VM_SSH_KEY" "$VM_USER@$VM_HOST" \
  "sudo systemctl cat '$VM_SERVICE' | sed -E 's/(NOTION_TOKEN=)[^\"]+/\\1***REDACTED***/g'"

echo "Env check (bools only):"
ssh -i "$VM_SSH_KEY" "$VM_USER@$VM_HOST" \
  "sudo '$VENV_PY' - <<'PY'
import os
import re
from pathlib import Path

path = Path('$REMOTE_ENV_FILE')
text = path.read_text()
for line in text.splitlines():
    line = line.strip()
    if not line.startswith('Environment='):
        continue
    match = re.match(r'Environment=\"([A-Z0-9_]+)=(.*)\"', line)
    if not match:
        continue
    key, val = match.group(1), match.group(2)
    val = val.replace('\\\\\"', '\"').replace('\\\\\\\\', '\\\\')
    os.environ[key] = val

print('NOTION_TOKEN set:', bool(os.getenv('NOTION_TOKEN')))
print('TOOL_REQUESTS_DB_ID set:', bool(os.getenv('TOOL_REQUESTS_DB_ID')))
PY"
