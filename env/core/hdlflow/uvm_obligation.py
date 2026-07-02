"""UVM obligation helpers."""

from __future__ import annotations

from pathlib import Path

from .obligations import load_obligations
from .project import require_project_instance


UVM_OBLIGATIONS_REL = "work/loop2_uvm/config/uvm_obligations.yaml"


def load_uvm_obligations(project_path: Path) -> list[dict[str, object]]:
    project = require_project_instance(project_path)
    return load_obligations(project / UVM_OBLIGATIONS_REL)


def missing_reference_models(project_path: Path) -> list[str]:
    offenders: list[str] = []
    for row in load_uvm_obligations(project_path):
        model = str(row.get("scoreboard_model") or "").lower()
        if model in {"", "none", "scenario_code", "scenario-only"}:
            offenders.append(str(row.get("sequence_id") or row.get("operation_id") or row.get("requirement_id") or "unknown"))
    return offenders
