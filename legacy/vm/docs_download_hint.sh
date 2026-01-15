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

DOC_FILE="${VM_DOC_FILE:-/home/ubuntu/MCP_SYSTEM_OVERVIEW.md}"

if [[ -z "${VM_HOST:-}" || -z "${VM_USER:-}" || -z "${VM_SSH_KEY:-}" ]]; then
  echo "Missing VM_HOST, VM_USER, or VM_SSH_KEY in vm/config.sh." >&2
  exit 1
fi

echo "To download the docs file to your local machine, run:" 
echo "scp -i $VM_SSH_KEY $VM_USER@$VM_HOST:$DOC_FILE ~/Desktop/"
