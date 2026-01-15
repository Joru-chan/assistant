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

AREA="${1:-}"
SCRIPT_NAME="${2:-}"
if [[ -z "$AREA" || -z "$SCRIPT_NAME" ]]; then
  echo "Usage: ./vm/custom_action_run.sh <area> <script_name.sh>" >&2
  exit 1
fi

ACTIONS_BASE="${VM_ACTIONS_BASE:-/home/ubuntu/mcp-admin/actions}"

ssh -i "$VM_SSH_KEY" "$VM_USER@$VM_HOST" \
  "bash -lc 'set -euo pipefail;\
    path="$ACTIONS_BASE/$AREA/$SCRIPT_NAME";\
    if [[ ! -f \"$path\" ]]; then\
      echo "Script not found: $ACTIONS_BASE/$AREA/$SCRIPT_NAME";\
      exit 1;\
    fi;\
    bash \"$path\"'"
