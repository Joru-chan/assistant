#!/usr/bin/env python3
# Deployment: NUCLEAR OPTION with enhanced debugging
import os
import sys
from pathlib import Path
import json

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

# Enhanced nuclear option with logging and ANY path handling
async def respond_to_everything(scope, receive, send):
    """
    Enhanced nuclear option: responds to ANY request with detailed debug info
    and logs the request for analysis
    """
    path = scope.get('path', '')
    method = scope.get('method', '')
    query_string = scope.get('query_string', b'').decode('utf-8')
    
    # Log incoming request to console/logs for debugging
    print(f"🔍 NUCLEAR OPTION: Received {method} request for path: '{path}'")
    if query_string:
        print(f"🔍 NUCLEAR OPTION: Query string: '{query_string}'")
    
    # Create detailed debug response
    debug_response = {
        "ok": True,
        "status": "healthy",
        "nuclear_option": True,
        "debug": {
            "message": "NUCLEAR OPTION: Responding to ALL requests",
            "received_path": path,
            "received_method": method,
            "scope_type": scope.get('type', ''),
            "query_string": query_string,
            "path_length": len(path),
            "headers": {k.decode('utf-8'): v.decode('utf-8') 
                       for k, v in scope.get('headers', [])},
            "server_name": scope.get('server', ['unknown', 0])[0] if scope.get('server') else 'unknown',
            "server_port": scope.get('server', ['unknown', 0])[1] if scope.get('server') else 'unknown'
        }
    }
    
    # Log the full response for debugging
    print(f"🔍 NUCLEAR OPTION: Responding with: {json.dumps(debug_response, indent=2)}")
    
    response = JSONResponse(debug_response)
    await response(scope, receive, send)

# Replace the entire app with enhanced nuclear option
app = respond_to_everything

register_tools(mcp)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
    )
