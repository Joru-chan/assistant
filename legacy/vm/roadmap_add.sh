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

ITEM="${1:-}"
if [[ -z "$ITEM" ]]; then
  echo "Usage: ./vm/roadmap_add.sh \"roadmap item text\"" >&2
  exit 1
fi

ROADMAP_FILE="${VM_ROADMAP_FILE:-/home/ubuntu/MCP_ROADMAP.md}"
ITEM_B64=$(printf '%s' "$ITEM" | base64)

ssh -i "$VM_SSH_KEY" "$VM_USER@$VM_HOST" \
  "ITEM_B64='$ITEM_B64' ROADMAP_FILE='$ROADMAP_FILE' bash -lc 'set -euo pipefail;\
    if [[ ! -f "$ROADMAP_FILE" ]]; then\
      cat > "$ROADMAP_FILE" << "EOF_ROADMAP"\
# MCP / Serendipity Engine Roadmap\
\
This file tracks future ideas & milestones for Lina's Serendipity Engine.\
\
Initial themes:\
- Micro-adventures based on mood + time + context\
- Serendipity nudges via Poke (iMessage)\
- Qdrant-based semantic retrieval for "this moment feels like..."\
- Daily or weekly digest of mood + events\
- Deeper integration with Notion / other life dashboards\
\
EOF_ROADMAP\
    fi;\
    ITEM=$(echo "$ITEM_B64" | base64 -d);\
    DATE=$(date -Iseconds);\
    echo "- [$DATE] $ITEM" >> "$ROADMAP_FILE";\
    echo "Added to $ROADMAP_FILE"'"
