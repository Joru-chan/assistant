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

KEY="${1:-}"
VALUE_B64="${2:-}"
if [[ -z "$KEY" || -z "$VALUE_B64" ]]; then
  echo "Usage: ./vm/env_set.sh <KEY> <VALUE_BASE64>" >&2
  exit 1
fi

ssh -i "$VM_SSH_KEY" "$VM_USER@$VM_HOST" \
  "KEY='$KEY' VALUE_B64='$VALUE_B64' SERVICE_NAME='$VM_SERVICE' bash -lc 'set -euo pipefail;\
    value=$(echo "$VALUE_B64" | base64 -d);\
    dropin_dir="/etc/systemd/system/${SERVICE_NAME}.d";\
    env_file="$dropin_dir/env.conf";\
    sudo mkdir -p "$dropin_dir";\
    if [[ -f "$env_file" ]]; then\
      if grep -q "^Environment=\"$KEY=" "$env_file"; then\
        sudo sed -i "s|^Environment=\"$KEY=.*\"|Environment=\"$KEY=$value\"|" "$env_file";\
      else\
        echo "Environment=\"$KEY=$value\"" | sudo tee -a "$env_file" > /dev/null;\
      fi;\
    else\
      printf "[Service]\nEnvironment=\"%s=%s\"\n" "$KEY" "$value" | sudo tee "$env_file" > /dev/null;\
    fi;\
    sudo systemctl daemon-reload;\
    sudo systemctl restart "$SERVICE_NAME";\
    echo "Updated $KEY for $SERVICE_NAME (value redacted)."'"
