#!/usr/bin/env python3
# Deployment: Health check endpoint fixes deployed (PR #8)
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
app = mcp.http_app(stateless_http=True)

# Add ultra-simple health check middleware
async def simple_health_check(scope, receive, send):
    """ASGI middleware that intercepts /health requests."""
    if scope['type'] == 'http' and scope['path'] == '/health' and scope['method'] == 'GET':
        response = JSONResponse({"ok": True, "status": "healthy"})
        await response(scope, receive, send)
        return
    # Pass through everything else to the original app
    await original_app(scope, receive, send)

# Replace app with our wrapper
original_app = app
app = simple_health_check

register_tools(mcp)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
    )
