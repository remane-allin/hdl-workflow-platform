"""Workspace and project doctor checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import load_project, load_workspace, validate_config
from .pipeline import build_pipeline
from .validate import validate_project


@dataclass(frozen=True)
class DoctorResult:
    ok: bool
    messages: list[str]


def run_doctor(workspace: Path, project_path: Path) -> DoctorResult:
    messages: list[str] = []
    workspace_cfg = load_workspace(workspace)
    project_cfg = load_project(project_path)

    layout = validate_project(project_path)
    messages.extend(layout.messages)

    config_errors = validate_config(workspace_cfg, project_cfg)
    if config_errors:
        messages.append("config: FAIL")
        messages.extend(f"config error: {error}" for error in config_errors)
    else:
        messages.append("config: PASS")

    pipeline = build_pipeline(project_cfg.data)
    if pipeline:
        messages.append("pipeline: " + " -> ".join(node.name for node in pipeline))
    else:
        messages.append("pipeline: FAIL empty")

    lower_test = workspace_cfg.root.parent / "test"
    if lower_test.exists() and lower_test.resolve() != workspace_cfg.root:
        messages.append(f"case check: FAIL found lowercase sibling {lower_test}")
    else:
        messages.append("case check: PASS")

    ok = layout.ok and not config_errors and bool(pipeline)
    return DoctorResult(ok=ok, messages=messages)

