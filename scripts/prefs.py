#!/usr/bin/env python3
"""Preference helpers for agent behavior (local-only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

PREFS_PATH = Path("memory/prefs.json")
DEFAULT_PREFS: Dict[str, object] = {
    "auto_apply_enabled": False,
    "auto_apply_threshold": 0.92,
    "auto_apply_scope": ["notion_corrections"],
}


def _ensure_memory_dir() -> None:
    PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_prefs() -> Dict[str, object]:
    _ensure_memory_dir()
    if not PREFS_PATH.exists():
        save_prefs(DEFAULT_PREFS.copy())
        return DEFAULT_PREFS.copy()
    data = json.loads(PREFS_PATH.read_text(encoding="utf-8"))
    merged = DEFAULT_PREFS.copy()
    if isinstance(data, dict):
        merged.update(data)
    save_prefs(merged)
    return merged


def save_prefs(prefs: Dict[str, object]) -> None:
    _ensure_memory_dir()
    PREFS_PATH.write_text(json.dumps(prefs, indent=2), encoding="utf-8")
