from __future__ import annotations

import os

import httpx
from fastmcp import FastMCP

# Env var for your n8n "create mood" webhook
# This should be set to: https://mcp-lina.duckdns.org/n8n/webhook/mood-pulse (or your actual URL)
MOOD_WEBHOOK = os.getenv("MOOD_MEMORY_WEBHOOK_URL")


def register(mcp: FastMCP) -> None:
    @mcp.tool
    async def create_mood_memory(
        mood: str,
        source: str | None = None,
        timestamp: str | None = None,
        poke_reaction: str | None = None,
        poke_action: str | None = None,
        poke_reason: str | None = None,
    ) -> dict:
        """
        Forward a mood snapshot and Poke's decision into Lina's n8n pipeline.

        Only sends fields that map directly to your current Google Sheet columns.
        """

        if not MOOD_WEBHOOK:
            return {
                "ok": False,
                "error": "MOOD_MEMORY_WEBHOOK_URL is not set on the MCP server",
            }

        payload = {
            "timestamp": timestamp,               # n8n -> sheet: timestamp
            "mood": mood,                         # n8n -> sheet: mood_input
            "poke_reaction": poke_reaction,       # n8n -> sheet: poke_reaction
            "source": source or "poke-mcp",       # n8n -> sheet: source
            "poke_action": poke_action,           # n8n -> sheet: poke_action
            "poke_reason": poke_reason,           # n8n -> sheet: poke_reason
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(MOOD_WEBHOOK, json=payload)
        except Exception as exc:
            return {
                "ok": False,
                "error": f"Failed to reach n8n mood webhook: {exc!r}",
            }

        body_preview = (resp.text or "")[:500]

        return {
            "ok": resp.status_code < 400,
            "status_code": resp.status_code,
            "response_preview": body_preview,
        }
