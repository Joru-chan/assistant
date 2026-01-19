#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config.sh"
CONFIG_EXAMPLE="$SCRIPT_DIR/config.example.sh"

if [[ -f "$CONFIG_FILE" ]]; then
  # shellcheck source=/dev/null
  source "$CONFIG_FILE"
elif [[ -f "$CONFIG_EXAMPLE" ]]; then
  # shellcheck source=/dev/null
  source "$CONFIG_EXAMPLE"
fi

MCP_URL="${VM_MCP_URL:-https://mcp-lina.duckdns.org/mcp}"
resolve_args=()
if [[ -n "${VM_MCP_RESOLVE:-}" ]]; then
  resolve_args=(--resolve "$VM_MCP_RESOLVE")
fi

build_payload() {
  python3 - "$@" <<'PY'
import json
import os
import sys

name = sys.argv[1] if len(sys.argv) > 1 else ""
raw_args = sys.argv[2] if len(sys.argv) > 2 else "{}"

if os.environ.get("DEBUG") == "1":
    print(f"Tool: {name}", file=sys.stderr)
    print(f"Args: {raw_args}", file=sys.stderr)

try:
    args = json.loads(raw_args)
except json.JSONDecodeError as exc:
    print(f"Invalid JSON arguments: {exc}. Raw args: {raw_args}", file=sys.stderr)
    sys.exit(2)

payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {"name": name, "arguments": args},
}
payload_json = json.dumps(payload)
if os.environ.get("DEBUG") == "1":
    print(f"Payload: {payload_json}", file=sys.stderr)
print(payload_json)
PY
}

parse_json_or_sse() {
  python3 - <<'PY'
import json
import sys

raw = sys.stdin.read()
raw = raw.strip()
if not raw:
    sys.exit(1)

def try_parse(text):
    json.loads(text)
    return True

try:
    try_parse(raw)
    sys.exit(0)
except Exception:
    pass

data_lines = []
for line in raw.splitlines():
    if line.startswith("data:"):
        data_lines.append(line[len("data:"):].strip())

if data_lines:
    joined = "\n".join(data_lines)
    try:
        try_parse(joined)
        sys.exit(0)
    except Exception:
        pass

sys.exit(1)
PY
}

raw_mode=0
list_mode=0
use_local=0

if [[ "${1:-}" == "--self-test" ]]; then
  resp="$(DEBUG=1 "$0" hello '{"name":"Jordane"}')"
  if ! printf "%s" "$resp" | parse_json_or_sse; then
    echo "Self-test failed: hello response is not JSON." >&2
    exit 1
  fi
  resp="$(DEBUG=1 "$0" tool_requests_latest '{"limit":5}')"
  if ! printf "%s" "$resp" | parse_json_or_sse; then
    echo "Self-test failed: tool_requests_latest response is not JSON." >&2
    exit 1
  fi
  echo "Self-test OK"
  exit 0
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --raw)
      raw_mode=1
      shift
      ;;
    --list)
      list_mode=1
      shift
      ;;
    --local)
      use_local=1
      shift
      ;;
    *)
      break
      ;;
  esac
done

if [[ "$use_local" -eq 1 && -n "${VM_MCP_LOCAL_URL:-}" ]]; then
  MCP_URL="$VM_MCP_LOCAL_URL"
fi

name="${1:-}"

if [[ "$list_mode" -eq 0 && -z "$name" ]]; then
  echo "Usage: $0 <tool_name> [json_args]" >&2
  echo "Usage: $0 --list [--local]" >&2
  echo "Example: $0 health_check" >&2
  echo "Example: $0 tool_requests_latest '{\"limit\":5}'" >&2
  echo "Example: $0 hello '{\"name\":\"Jordane\"}'" >&2
  exit 1
fi

if [[ "$list_mode" -eq 1 ]]; then
  payload="$(python3 - <<'PY'
import json

payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
print(json.dumps(payload))
PY
)"
else
  if [[ $# -ge 2 ]]; then
    payload="$(build_payload "$1" "$2")"
  else
    payload="$(build_payload "$1")"
  fi
fi

response="$(curl -sS \
  "${resolve_args[@]}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$payload" \
  "$MCP_URL")"

if [[ "$raw_mode" -eq 1 ]]; then
  printf "%s\n" "$response"
  exit 0
fi

data_json="$(printf "%s\n" "$response" | awk '/^data: /{sub(/^data: /,""); last=$0} END{if (last) print last}')"
if [[ -z "$data_json" ]]; then
  echo "ERROR: No data: line found in response." >&2
  printf "%s\n" "$response"
  exit 1
fi

if command -v jq >/dev/null 2>&1; then
  printf "%s\n" "$data_json" | jq .
else
  printf "%s\n" "$data_json"
fi
