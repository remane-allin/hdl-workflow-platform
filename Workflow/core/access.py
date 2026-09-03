from __future__ import annotations

from pathlib import Path

from .contracts import GateError, ProjectContext


IMPLEMENTATION_STAGE_ROOTS = {
    "rtl": {"rtl", "tb", "vivado"},
    "verify": {"tb", "uvm", "vivado"},
    "synth": {"constraints", "vivado"},
    "route": {"constraints", "vivado"},
    "release": {"vivado", "vitis"},
}


def _resolved(path: Path) -> Path:
    return path.resolve(strict=False)


def is_within(path: Path, parent: Path) -> bool:
    try:
        _resolved(path).relative_to(_resolved(parent))
        return True
    except ValueError:
        return False


def discover_project(workflow_root: Path, project_id: str) -> ProjectContext:
    if not project_id or project_id in {".", ".."} or any(c in project_id for c in "/\\"):
        raise GateError("project id must be one direct prj directory name")
    root = _resolved(workflow_root)
    project_root = _resolved(root / "prj" / project_id)
    if not is_within(project_root, root / "prj") or not project_root.is_dir():
        raise GateError(f"project does not exist: {project_id}")
    return ProjectContext(root, project_id, project_root)


def require_workspace_write(path: Path, workspace_root: Path) -> Path:
    target = _resolved(path)
    if not is_within(target, workspace_root):
        raise GateError(f"write target escapes workspace: {target}")
    return target


def authorize_project_write(
    context: ProjectContext,
    path: Path,
    *,
    gate_a_passed: bool,
    stage: str | None = None,
    workflow_core_change: bool = False,
) -> Path:
    target = require_workspace_write(path, context.workflow_root.parent)
    if workflow_core_change:
        if not is_within(target, context.workflow_root):
            raise GateError("Workflow core changes must stay under Workflow")
        return target
    if not is_within(target, context.project_root):
        raise GateError("cross-project write is forbidden")
    implementation_roots = {
        name: context.project_root / "output" / name
        for name in ("rtl", "tb", "uvm", "constraints", "vivado", "vitis")
    }
    owner = next((name for name, root in implementation_roots.items() if is_within(target, root)), None)
    if owner is not None:
        if not gate_a_passed:
            raise GateError("Gate A must PASS before implementation writes")
        if stage not in IMPLEMENTATION_STAGE_ROOTS:
            raise GateError("an approved implementation stage is required")
        if owner not in IMPLEMENTATION_STAGE_ROOTS[stage]:
            raise GateError(f"{stage} cannot write output/{owner}")
    return target
