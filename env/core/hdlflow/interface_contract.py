"""Generic top-interface contract helpers for directed TB obligations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .project import require_project_instance
from .simple_yaml import load_yaml


INTERFACE_CONTRACT_REL = "work/loop1_rtl_tb/config/interface_contract.yaml"


def load_interface_contract(project_path: Path) -> dict[str, Any]:
    project = require_project_instance(project_path)
    path = project / INTERFACE_CONTRACT_REL
    if not path.exists():
        return {"schema_version": 1, "interfaces": []}
    data = load_yaml(path)
    return data if isinstance(data, dict) else {"schema_version": 1, "interfaces": []}


def interface_names(project_path: Path) -> set[str]:
    data = load_interface_contract(project_path)
    names: set[str] = set()
    for key in ("interface_name", "name"):
        if data.get(key):
            names.add(str(data[key]))
    interfaces = data.get("interfaces", [])
    if not isinstance(interfaces, list):
        return names
    for item in interfaces:
        if not isinstance(item, dict):
            continue
        for key in ("interface_name", "name"):
            if item.get(key):
                names.add(str(item[key]))
    return names
