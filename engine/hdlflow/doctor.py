"""Workspace and project doctor checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .change_control import check_changes
from .config import load_project, load_workspace, validate_config
from .memory import check_memory
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

    for orphan in _orphan_project_configs(workspace_cfg.root):
        messages.append(f"workspace warning: orphan project config without project directory: {orphan}")

    memory = check_memory(project_path)
    if memory.ok:
        messages.append("memory: PASS")
    else:
        messages.append("memory: FAIL")
        messages.extend(f"memory error: {error}" for error in memory.errors)
    messages.extend(f"memory warning: {warning}" for warning in memory.warnings)

    changes = check_changes(project_path)
    if changes.ok:
        messages.append("change_control: PASS")
    else:
        messages.append("change_control: FAIL")
        messages.extend(f"change_control issue: {message}" for message in changes.messages)

    lower_test = workspace_cfg.root.parent / "test"
    if lower_test.exists() and lower_test.resolve() != workspace_cfg.root:
        messages.append(f"case check: FAIL found lowercase sibling {lower_test}")
    else:
        messages.append("case check: PASS")

    ok = layout.ok and not config_errors and bool(pipeline) and memory.ok and changes.ok
    return DoctorResult(ok=ok, messages=messages)


def _orphan_project_configs(workspace_root: Path) -> list[str]:
    config_root = workspace_root / "config" / "projects"
    projects_root = workspace_root / "projects"
    if not config_root.is_dir() or not projects_root.is_dir():
        return []
    orphans: list[str] = []
    for path in sorted(config_root.iterdir()):
        if not path.is_dir():
            continue
        if not (path / "project_config.yaml").is_file():
            continue
        if not (projects_root / path.name).is_dir():
            orphans.append(f"config/projects/{path.name}/project_config.yaml")
    return orphans
