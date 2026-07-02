"""Shared obligation loading and coverage helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .simple_yaml import load_yaml


def load_obligations(path: Path, key: str = "obligations") -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = load_yaml(path)
    rows = data.get(key, []) if isinstance(data, dict) else []
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def covered_ids(rows: list[dict[str, Any]], *keys: str) -> set[str]:
    ids: set[str] = set()
    for row in rows:
        for key in keys:
            if row.get(key):
                ids.add(str(row[key]))
    return ids


def missing_ids(required: set[str], covered: set[str]) -> list[str]:
    return sorted(required - covered)
