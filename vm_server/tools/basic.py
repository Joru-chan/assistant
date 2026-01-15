from __future__ import annotations

import platform
import socket
from datetime import datetime

from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.tool
    def greet(name: str) -> str:
        """
        Greet a user by name with a welcome message from the MCP server.
        """
        return f"Hi {name}! This is Lina's Serendipity MCP server saying hello 👋"

    @mcp.tool
    def get_server_info() -> dict:
        """
        Get information about the MCP server and environment.
        """
        return {
            "server_name": "Lina Serendipity MCP Server",
            "version": "1.0.0",
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "time_utc": datetime.utcnow().isoformat() + "Z",
        }
