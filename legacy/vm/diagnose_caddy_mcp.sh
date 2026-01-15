#!/usr/bin/env bash
# DEPRECATED: moved to legacy/vm during cleanup. Use canonical vm/ scripts instead.
set -u

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

ssh -i "$VM_SSH_KEY" "$VM_USER@$VM_HOST" <<'EOSSH'
set -u

echo "== mcp-server.service status =="
sudo systemctl status mcp-server.service --no-pager || true

echo "== mcp-server.service logs (last 120) =="
sudo journalctl -u mcp-server.service -n 120 --no-pager || true

echo "== Listening ports =="
sudo ss -lntp | grep -E '(:8000|:8001|:443|:80)' || true

echo "== Caddy status =="
sudo systemctl status caddy --no-pager || true

echo "== Caddy config =="
if [ -f /etc/caddy/Caddyfile ]; then
  sudo caddy validate --config /etc/caddy/Caddyfile || true
  sudo sed -n '1,220p' /etc/caddy/Caddyfile || true
else
  echo "No /etc/caddy/Caddyfile"
fi

echo "== Curl checks (local) =="
curl -i http://127.0.0.1:8000/mcp || true
curl -i http://127.0.0.1:8000/health || true

echo "== Curl checks (public) =="
curl -i https://mcp-lina.duckdns.org/mcp || true
curl -i https://mcp-lina.duckdns.org/health || true
EOSSH
