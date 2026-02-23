#!/usr/bin/env python3
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

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.registry import register_tools

mcp = FastMCP(
    "Lina Serendipity MCP Server",
)
app = mcp.http_app(stateless_http=True)

# Register health endpoint for external checks on the HTTP app
@app.get("/health")
async def health() -> dict:
    """Health check endpoint for monitoring."""
    return {"ok": True, "status": "healthy"}

register_tools(mcp)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
    )
