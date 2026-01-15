from __future__ import annotations

import aiofiles
from fastmcp import FastMCP

SYSTEM_DOC_PATH = "/home/ubuntu/MCP_SYSTEM_OVERVIEW.md"


def register(mcp: FastMCP) -> None:
    @mcp.tool
    async def get_system_overview() -> dict:
        """
        Return the full contents of MCP_SYSTEM_OVERVIEW.md so external agents
        (like Poke) can gain context before making plans.

        This is safe: read-only, no side-effects.
        """
        try:
            async with aiofiles.open(SYSTEM_DOC_PATH, "r") as handle:
                content = await handle.read()

            return {
                "ok": True,
                "system_overview_md": content,
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
