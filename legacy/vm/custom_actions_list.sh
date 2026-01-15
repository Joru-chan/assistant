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

ACTIONS_BASE="${VM_ACTIONS_BASE:-/home/ubuntu/mcp-admin/actions}"

ssh -i "$VM_SSH_KEY" "$VM_USER@$VM_HOST" \
  "bash -lc 'set -euo pipefail;\
    echo "=== Custom Admin Actions ===";\
    for area in mcp n8n admin; do\
      dir="$ACTIONS_BASE/$area";\
      echo;\
      echo "[$area]";\
      if compgen -G "$ACTIONS_BASE/$area/*.sh" > /dev/null; then\
        for f in $ACTIONS_BASE/$area/*.sh; do\
          [[ -e \"$f\" ]] || continue;\
          base=$(basename \"$f\");\
          desc=$(grep -m1 "^#" \"$f\" | sed "s/^#\\s*//");\
          echo " - $base : ${desc:-no description}";\
        done;\
      else\
        echo " (none)";\
      fi;\
    done'"
