from __future__ import annotations

import socket
from datetime import datetime, timezone

from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.tool(name="hello")
    def hello(name: str | None = None) -> dict:
        """
        Return a basic greeting plus server metadata.
        """
        server_time = datetime.now(timezone.utc).isoformat()
        hostname = socket.gethostname()
        who = name or "there"
        return {
            "summary": f"Hello, {who}.",
            "result": {
                "server_time": server_time,
                "hostname": hostname,
                "name": name,
            },
            "next_actions": [],
            "errors": [],
        }
