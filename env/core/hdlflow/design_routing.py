"""Design routing helpers for requirement-to-architecture closure."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .simple_yaml import load_yaml


DESIGN_ROUTING_REL = "work/docparse/architecture/design_routing.yaml"
MODULE_OWNERSHIP_REL = "work/docparse/architecture/module_ownership_matrix.yaml"


def load_design_routes(project: Path) -> list[dict[str, Any]]:
    return _rows(project / DESIGN_ROUTING_REL, "routes")


def load_module_owners(project: Path) -> list[dict[str, Any]]:
    return _rows(project / MODULE_OWNERSHIP_REL, "owners")


def _rows(path: Path, key: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = load_yaml(path)
    rows = data.get(key, []) if isinstance(data, dict) else []
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
