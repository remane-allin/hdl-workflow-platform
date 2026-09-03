from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import ContractError, ProjectContext
from Workflow.tools.design import load_design, validate_design
from Workflow.tools.filesystem import atomic_write_json


def prepare_next(context: ProjectContext, next_design: dict[str, Any]) -> Path:
    """Persist one AI-prepared complete candidate without consuming pending inputs."""
    current_version = load_design(context.design_path)["design_version"] if context.design_path.exists() else 0
    if next_design.get("design_version") != current_version + 1:
        raise ContractError("candidate design_version must increment current by exactly one")
    errors = validate_design(next_design, context.project_root, context.project_id)
    if errors:
        raise ContractError("candidate design is incomplete: " + "; ".join(errors))
    target = context.project_root / "input" / "next" / "design.json"
    atomic_write_json(target, next_design)
    return target
