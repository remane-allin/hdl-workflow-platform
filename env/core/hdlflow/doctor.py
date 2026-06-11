"""Workspace and project doctor checks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .change_control import check_changes
from .config import load_project, load_workspace, validate_config
from .layout import PROJECTS_ROOT, project_gates_path
from .memory import check_memory
from .pipeline import build_pipeline
from .validate import validate_project

WORKSPACE_ROOT_TOOL_LOG_PATTERNS = (
    "vivado*.jou",
    "vivado*.log",
)


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

    workspace_root_logs = _workspace_root_tool_log_issues(workspace_cfg.root)
    if workspace_root_logs:
        messages.append("workspace_root_tool_logs: FAIL")
        messages.extend(f"workspace root tool log: {path}" for path in workspace_root_logs)
    else:
        messages.append("workspace_root_tool_logs: PASS")

    memory = check_memory(project_path)
    if memory.ok:
        messages.append("memory: PASS")
    else:
        messages.append("memory: FAIL")
        messages.extend(f"memory error: {error}" for error in memory.errors)
    messages.extend(f"memory warning: {warning}" for warning in memory.warnings)

    changes = check_changes(project_path)
    if changes.ok:
        messages.append("work/change: PASS")
    else:
        messages.append("work/change: FAIL")
        messages.extend(f"work/change issue: {message}" for message in changes.messages)

    blocked_state = _blocked_loop_state(project_path)
    if blocked_state:
        messages.append(f"stage_state: FAIL {blocked_state}")
    else:
        messages.append("stage_state: PASS")

    lower_test = next((path for path in workspace_cfg.root.parent.iterdir() if path.name == "test"), None)
    if lower_test and lower_test.resolve() != workspace_cfg.root:
        messages.append(f"case check: FAIL found lowercase sibling {lower_test}")
    else:
        messages.append("case check: PASS")

    ok = (
        layout.ok
        and not config_errors
        and bool(pipeline)
        and not workspace_root_logs
        and memory.ok
        and changes.ok
        and not blocked_state
    )
    return DoctorResult(ok=ok, messages=messages)


def _workspace_root_tool_log_issues(workspace_root: Path) -> list[str]:
    hits: list[Path] = []
    for pattern in WORKSPACE_ROOT_TOOL_LOG_PATTERNS:
        hits.extend(path for path in workspace_root.glob(pattern) if path.is_file())
    return [str(path.relative_to(workspace_root)).replace("\\", "/") for path in sorted(hits)]


def _orphan_project_configs(workspace_root: Path) -> list[str]:
    projects_root = workspace_root / PROJECTS_ROOT
    if not projects_root.is_dir():
        return []
    orphans: list[str] = []
    for path in sorted(projects_root.iterdir()):
        if not path.is_dir():
            continue
        if not (path / "project_scaffold.yaml").is_file() and (path / "work" / "config" / "project_config.yaml").is_file():
            orphans.append(f"prj/{path.name}/work/config/project_config.yaml")
    return orphans


def _blocked_loop_state(project_path: Path) -> str:
    path = project_gates_path(project_path) / "loop_state.json"
    if not path.exists():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return f"loop_state.json is not readable: {exc}"
    status = str(data.get("overall_status") or "")
    current_loop = str(data.get("current_loop") or "")
    if "blocked" in status.lower():
        return f"{status} current_loop={current_loop or 'unknown'}"
    return ""
