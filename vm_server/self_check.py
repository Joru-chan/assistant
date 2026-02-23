#!/usr/bin/env python3
"""Local import self-check for MCP server modules."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastmcp import FastMCP
from tools.registry import register_tools


def main() -> int:
    mcp = FastMCP("Self-check MCP")
    register_tools(mcp)
    print("OK: tools registry imported and registered.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
