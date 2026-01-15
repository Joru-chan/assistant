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

if [[ -z "${VM_HOST:-}" || -z "${VM_USER:-}" || -z "${VM_SSH_KEY:-}" || -z "${VM_SERVICE:-}" || -z "${VM_DEST_DIR:-}" ]]; then
  echo "Missing VM_HOST, VM_USER, VM_SSH_KEY, VM_SERVICE, or VM_DEST_DIR in vm/config.sh." >&2
  exit 1
fi

REMOTE_PY="${VM_VENV_PY:-$VM_DEST_DIR/venv/bin/python}"
REMOTE_SERVER="$VM_DEST_DIR/server.py"

ssh -i "$VM_SSH_KEY" "$VM_USER@$VM_HOST" \
  "if [[ ! -f $REMOTE_SERVER ]]; then echo 'Missing server.py at $REMOTE_SERVER'; exit 1; fi; \
   $REMOTE_PY -m py_compile $REMOTE_SERVER && \
   sudo systemctl daemon-reload && sudo systemctl restart $VM_SERVICE && \
   systemctl status $VM_SERVICE --no-pager -n 10 || \
   echo 'Syntax check failed; service not restarted.'"
