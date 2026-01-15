from __future__ import annotations

from fastmcp import FastMCP

from tools import (
    admin,
    basic,
    health,
    hello,
    mood,
    notion_editor,
    serendipity,
    system_overview,
    tool_requests,
)


def register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools with the server."""
    for module in (
        admin,
        basic,
        mood,
        serendipity,
        system_overview,
        hello,
        tool_requests,
        notion_editor,
        health,
    ):
        module.register(mcp)
