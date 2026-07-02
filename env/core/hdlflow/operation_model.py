"""Generic operation model helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .project import require_project_instance
from .simple_yaml import load_yaml


OPERATION_MODEL_REL = "work/docparse/verification/operation_model.yaml"
OPERATION_KEYS = ("operations", "register_map", "opcode_map", "packet_map", "streaming_protocol", "custom_operations")


def load_operation_model(project_path: Path) -> dict[str, Any]:
    project = require_project_instance(project_path)
    path = project / OPERATION_MODEL_REL
    if not path.exists():
        return {"schema_version": 1, "operations": []}
    data = load_yaml(path)
    return data if isinstance(data, dict) else {"schema_version": 1, "operations": []}


def operation_entries(project_path: Path) -> list[dict[str, Any]]:
    model = load_operation_model(project_path)
    rows: list[dict[str, Any]] = []
    for key in OPERATION_KEYS:
        value = model.get(key, [])
        if isinstance(value, list):
            rows.extend(item for item in value if isinstance(item, dict))
    return rows


def operation_ids(project_path: Path) -> set[str]:
    ids: set[str] = set()
    for row in operation_entries(project_path):
        for key in ("operation_id", "opcode", "register", "packet_id", "stream_id"):
            if row.get(key):
                ids.add(str(row[key]))
    return ids
