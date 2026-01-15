from __future__ import annotations

from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.tool
    def health_check() -> dict:
        """
        Fallback health check for environments without explicit /health routing.
        """
        return {
            "summary": "Health check ok.",
            "result": {"ok": True},
            "next_actions": [],
            "errors": [],
        }
