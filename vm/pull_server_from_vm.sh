#!/usr/bin/env bash
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

if [[ -z "${VM_HOST:-}" || -z "${VM_USER:-}" || -z "${VM_SSH_KEY:-}" || -z "${VM_DEST_DIR:-}" || -z "${VM_LOCAL_SRC:-}" ]]; then
  echo "Missing required VM_* variables in vm/config.sh." >&2
  exit 1
fi

LOCAL_SRC="$VM_LOCAL_SRC"
if [[ "$LOCAL_SRC" != /* ]]; then
  LOCAL_SRC="$ROOT_DIR/$LOCAL_SRC"
fi

RSYNC_EXCLUDES=(
  "--exclude=venv/"
  "--exclude=__pycache__/"
  "--exclude=*.pyc"
  "--exclude=*.bak*"
  "--exclude=*~"
  "--exclude=.env"
  "--exclude=memory/"
  "--exclude=.git/"
)

mkdir -p "$LOCAL_SRC"

echo "Pulling from $VM_USER@$VM_HOST:$VM_DEST_DIR to $LOCAL_SRC"

rsync -az "${RSYNC_EXCLUDES[@]}" \
  -e "ssh -i $VM_SSH_KEY" \
  "$VM_USER@$VM_HOST:$VM_DEST_DIR/" "$LOCAL_SRC/"

echo "Pull complete. Local files refreshed: $LOCAL_SRC"
