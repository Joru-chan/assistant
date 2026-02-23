#!/usr/bin/env python3
# Deployment: NUCLEAR OPTION - Respond to everything with 200 OK
import os
import sys
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, rely on system env

from fastmcp import FastMCP
from starlette.responses import JSONResponse

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.registry import register_tools

mcp = FastMCP(
    "Lina Serendipity MCP Server",
)
original_app = mcp.http_app(stateless_http=True)

# NUCLEAR OPTION: Respond to EVERYTHING with 200 OK
async def respond_to_everything(scope, receive, send):
    """Nuclear option: respond to ALL requests with 200 OK for debugging."""
    method = scope.get('method', 'UNKNOWN')
    path = scope.get('path', 'UNKNOWN')
    
    debug_info = {
        "ok": True,
        "status": "healthy",
        "debug": {
            "message": "NUCLEAR OPTION: Responding to ALL requests",
            "received_method": method,
            "received_path": path,
            "scope_type": scope.get('type', 'UNKNOWN'),
            "query_string": scope.get('query_string', b'').decode('utf-8'),
            "headers": {k.decode('utf-8'): v.decode('utf-8') for k, v in scope.get('headers', [])}
        }
    }
    
    response = JSONResponse(debug_info)
    await response(scope, receive, send)

# Replace the entire app with nuclear option
app = respond_to_everything

register_tools(mcp)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
    )
