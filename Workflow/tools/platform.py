from __future__ import annotations

from pathlib import Path
from typing import Any

from Workflow.core.access import discover_project, require_workspace_write
from Workflow.core.contracts import GateError, WorkflowError
from Workflow.tools.assets import require_released_project
from Workflow.tools.filesystem import atomic_write_json, atomic_write_text, read_json


PLATFORM_FORMAT_VERSION = 1


def validate_platform(workflow_root: Path, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("format_version") != PLATFORM_FORMAT_VERSION:
        raise GateError("invalid Workflow platform format")
    version = value.get("platform_version")
    if not isinstance(version, int) or version < 1:
        raise GateError("platform_version must be a positive integer")
    if value.get("product") != "Workflow":
        raise GateError("platform product must be Workflow")
    if value.get("host") != "Windows-PowerShell-7":
        raise GateError("platform host must be Windows-PowerShell-7")
    for field in ("entry", "tool_profile"):
        relative = Path(value.get(field, ""))
        if not relative.parts or relative.is_absolute() or ".." in relative.parts:
            raise GateError(f"platform {field} must be Workflow-relative")
        if not (workflow_root / relative).is_file():
            raise GateError(f"platform {field} is missing: {relative.as_posix()}")
    return value


def load_platform(workflow_root: Path) -> dict[str, Any]:
    return validate_platform(workflow_root, read_json(workflow_root / "platform.json"))


def _validate_baselines(workflow_root: Path, project_ids: list[str]) -> list[dict[str, Any]]:
    if len(project_ids) < 2 or len(project_ids) != len(set(project_ids)):
        raise WorkflowError("platform maintenance requires at least two distinct baseline projects")
    evidence = []
    for project_id in project_ids:
        context = discover_project(workflow_root, project_id)
        design, report = require_released_project(context)
        evidence.append(
            {
                "baseline_id": project_id,
                "project_id": project_id,
                "design_version": design["design_version"],
                "released_design_version": report.get("context", {}).get("design_version"),
                "release_status": report["release"]["status"],
            }
        )
    return evidence


def _restore_descriptor(path: Path, original: bytes | None) -> None:
    if original is None:
        path.unlink(missing_ok=True)
        return
    atomic_write_text(path, original.decode("utf-8"))


def _switch_platform_descriptors(
    current_path: Path,
    previous_path: Path,
    active: dict[str, Any],
    direct_previous: dict[str, Any],
) -> None:
    original_current = current_path.read_bytes() if current_path.exists() else None
    original_previous = previous_path.read_bytes() if previous_path.exists() else None
    try:
        atomic_write_json(previous_path, direct_previous)
        atomic_write_json(current_path, active)
    except BaseException:
        _restore_descriptor(current_path, original_current)
        _restore_descriptor(previous_path, original_previous)
        raise


def _platform_evidence(
    active: dict[str, Any],
    direct_previous: dict[str, Any],
    baselines: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "status": "PASS",
        "platform_version": active["platform_version"],
        "previous_version": direct_previous["platform_version"],
        "entry": active["entry"],
        "tool_profile": active["tool_profile"],
        "baselines": baselines,
    }


def upgrade_platform(
    workflow_root: Path,
    candidate_path: Path,
    project_ids: list[str],
) -> dict[str, Any]:
    require_workspace_write(candidate_path, workflow_root.parent)
    current_path = workflow_root / "platform.json"
    previous_path = workflow_root / "platform.previous.json"
    current = load_platform(workflow_root)
    candidate = validate_platform(workflow_root, read_json(candidate_path))
    if candidate["platform_version"] != current["platform_version"] + 1:
        raise GateError("platform candidate must increment the current version by exactly one")
    evidence = _validate_baselines(workflow_root, project_ids)
    _switch_platform_descriptors(current_path, previous_path, candidate, current)
    return _platform_evidence(candidate, current, evidence)


def restore_platform(workflow_root: Path, project_ids: list[str]) -> dict[str, Any]:
    current_path = workflow_root / "platform.json"
    previous_path = workflow_root / "platform.previous.json"
    current = load_platform(workflow_root)
    if not previous_path.is_file():
        raise WorkflowError("no direct platform recovery point exists")
    previous = validate_platform(workflow_root, read_json(previous_path))
    evidence = _validate_baselines(workflow_root, project_ids)
    _switch_platform_descriptors(current_path, previous_path, previous, current)
    return _platform_evidence(previous, current, evidence)
