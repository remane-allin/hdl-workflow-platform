"""Lightweight workflow advisory layer.

This module is intentionally outside the gate runner. It summarizes the next
safe action from existing file-backed state, but it never relaxes a gate and it
never writes formal design reports.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .change_control import check_changes
from .project import require_project_instance
from .ralph_loop import ralph_status
from .validate import validate_project


@dataclass(frozen=True)
class WorkflowAdviceResult:
    report_path: Path
    ok: bool
    messages: list[str]
    next_action: str


def advise_next_action(project_path: Path, *, write_report: bool = True) -> WorkflowAdviceResult:
    """Create a concise, file-backed next-action summary for a project."""

    project = require_project_instance(project_path)
    validation = validate_project(project)
    status = ralph_status(project)
    changes = check_changes(project)

    messages: list[str] = [
        f"project: {project.name}",
        f"current_loop: {status.current_loop}",
        f"overall_status: {status.overall_status}",
        f"ralph_report: {_rel(project, status.report_path)}",
    ]
    messages.append("failed_nodes: " + (", ".join(status.failed_nodes) if status.failed_nodes else "none"))
    messages.append("open_step: " + (status.open_step.step_id if status.open_step else "none"))
    messages.append("open_changes: " + (", ".join(status.open_changes) if status.open_changes else "none"))
    messages.append("approved_changes: " + (", ".join(status.approved_changes) if status.approved_changes else "none"))
    messages.append("review_blockers: " + (str(len(status.review_blockers)) if status.review_blockers else "0"))
    messages.append("memory_errors: " + (str(len(status.memory_errors)) if status.memory_errors else "0"))
    messages.append("layout_check: " + ("PASS" if validation.ok else "FAIL"))
    messages.append("change_check: " + ("PASS" if changes.ok else "FAIL"))

    next_action = status.next_action
    if not validation.ok:
        next_action = "run `repair-diagnose --project <project>` and fix scaffold/layout drift before continuing"
        messages.extend(f"layout: {item}" for item in validation.messages[:8])
    elif not changes.ok:
        next_action = "finish change-control records before running downstream gates"
        messages.extend(f"change: {item}" for item in changes.messages[:8])

    report_path = project / "output" / "reports" / "workflow" / "next_action.md"
    if write_report:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(_format_report(project, messages, next_action), encoding="utf-8")

    ok = validation.ok and changes.ok and not status.memory_errors
    return WorkflowAdviceResult(report_path=report_path, ok=ok, messages=messages, next_action=next_action)


def _format_report(project: Path, messages: list[str], next_action: str) -> str:
    lines = [
        "# Workflow Next Action",
        "",
        f"- project: {project.name}",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- next_action: {next_action}",
        "",
        "## State",
        "",
        *[f"- {message}" for message in messages],
        "",
        "## Guardrail",
        "",
        "- This advisory report does not pass, waive, or weaken any gate.",
        "- Generated design documents remain owned only by `generate-design-doc`.",
    ]
    return "\n".join(lines) + "\n"


def _rel(project: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)
