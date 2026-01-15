#!/usr/bin/env bash
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

ssh -i "$VM_SSH_KEY" "$VM_USER@$VM_HOST" \
  "systemctl status $VM_SERVICE --no-pager && echo '' && journalctl -u $VM_SERVICE -n 50 --no-pager"
