from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


FORMAT_VERSION = 1
STAGES = ("design", "rtl", "verify", "synth", "route", "release")
STATUSES = ("NOT_RUN", "BLOCKED", "FAIL", "PASS")
DESIGN_SECTIONS = (
    "project",
    "requirements",
    "architecture",
    "interfaces",
    "implementation",
    "budgets",
    "verification",
)


class WorkflowError(RuntimeError):
    """Base error with a stable workflow classification."""

    kind = "BLOCKED"


class ContractError(WorkflowError):
    pass


class GateError(WorkflowError):
    pass


class ToolFailure(WorkflowError):
    kind = "FAIL"


@dataclass(frozen=True)
class ProjectContext:
    workflow_root: Path
    project_id: str
    project_root: Path

    @property
    def design_path(self) -> Path:
        return self.project_root / "input" / "current" / "design.json"

    @property
    def state_path(self) -> Path:
        return self.project_root / "work" / "state.json"


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return value


def validate_design_shape(design: Any) -> dict[str, Any]:
    document = require_mapping(design, "design")
    if document.get("format_version") != FORMAT_VERSION:
        raise ContractError("unsupported design format_version")
    version = document.get("design_version")
    if not isinstance(version, int) or version < 1:
        raise ContractError("design_version must be a positive integer")
    for section in DESIGN_SECTIONS:
        value = document.get(section)
        if not isinstance(value, (dict, list)) or not value:
            raise ContractError(f"design.{section} is required and cannot be empty")
    return document

