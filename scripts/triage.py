#!/usr/bin/env python3
"""
Deprecated: use scripts/fetch_tool_requests.py.

This script now returns raw candidates only (no selection).
"""

from __future__ import annotations

import argparse
import json

from fetch_tool_requests import fetch_candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch tool request candidates (legacy triage wrapper).")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--query", type=str, default=None)
    args = parser.parse_args()

    output = fetch_candidates(limit=args.limit, query=args.query)
    output["summary"] = f"(Deprecated triage) {output['summary']}"
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
