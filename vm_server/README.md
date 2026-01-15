# VM MCP Server

This folder contains the exact server code deployed to the VM at
`/home/ubuntu/mcp-server-template/src`.

## Adding a new tool
1) Create a module in `vm_server/tools/` with a `register(mcp: FastMCP)` function.
2) Decorate tool functions with `@mcp.tool` inside `register`.
3) Import the module in `vm_server/tools/registry.py` and add it to the list.

Example skeleton:
```python
from fastmcp import FastMCP

def register(mcp: FastMCP) -> None:
    @mcp.tool
    def my_tool() -> dict:
        return {"summary": "ok", "result": {}, "next_actions": [], "errors": []}
```

## Test hello tool (remote)
```bash
curl -sS https://mcp-lina.duckdns.org/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"hello","arguments":{"name":"Jordane"}}}'
```

## Tool Requests (Notion)
Required env vars on the VM service:
- `NOTION_TOKEN`
- `TOOL_REQUESTS_DB_ID`

Latest items:
```bash
curl -sS https://mcp-lina.duckdns.org/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"tool_requests_latest","arguments":{"limit":10,"statuses":["new","triaging"]}}}'
```

Search by keyword:
```bash
curl -sS https://mcp-lina.duckdns.org/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"tool_requests_search","arguments":{"query":"calendar","limit":10}}}'
```

Safety: read-only tools (no writes).

## Health check
- Primary: `GET /health` (returns `{"ok": true}`).
- Fallback: call the `health_check` tool via `/mcp`.
