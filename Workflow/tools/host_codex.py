from __future__ import annotations

from pathlib import Path

from Workflow.core.access import authorize_project_write
from Workflow.core.contracts import ProjectContext


def pre_write(
    context: ProjectContext,
    target: Path,
    *,
    gate_a_passed: bool,
    stage: str | None = None,
    workflow_core_change: bool = False,
) -> Path:
    """Thin host bridge; external hook installation is intentionally optional."""
    return authorize_project_write(
        context,
        target,
        gate_a_passed=gate_a_passed,
        stage=stage,
        workflow_core_change=workflow_core_change,
    )


def bridge_status() -> dict[str, str]:
    return {
        "mode": "pre-run",
        "external_hook": "not-installed",
        "behavior": "workflow commands still enforce the same access function",
    }
