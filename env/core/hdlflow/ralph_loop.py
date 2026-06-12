"""File-backed Ralph loop status and completion checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .layout import project_memory_path
from .memory import (
    ACTIVE_PLAN_REL,
    append_plan_note,
    check_memory,
    update_active_plan_step,
)
from .project import require_project_instance
from .review import review_blockers
from .state_sync import NODE_ORDER, sync_project_state


STEP_RE = re.compile(r"^- \[([ x>!])\] (P\d{3}):\s*(.*)$")

MARKER_STATUS = {
    " ": "pending",
    ">": "in_progress",
    "x": "done",
    "!": "blocked",
}

CHANGE_STATUS_ORDER = ("open", "impact_ready", "approved", "closed")


@dataclass(frozen=True)
class RalphStep:
    step_id: str
    status: str
    text: str


@dataclass(frozen=True)
class RalphStatusResult:
    report_path: Path
    messages: list[str]
    next_action: str
    current_loop: str
    overall_status: str
    open_step: RalphStep | None
    open_changes: list[str]
    approved_changes: list[str]
    review_blockers: list[str]
    failed_nodes: list[str]
    memory_errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.failed_nodes and not self.memory_errors and not self.review_blockers


@dataclass(frozen=True)
class RalphCheckResult:
    report_path: Path
    ok: bool
    errors: list[str]
    warnings: list[str]


@dataclass(frozen=True)
class RalphStepResult:
    path: Path
    step_id: str
    status: str
    messages: list[str]


def ralph_status(project_path: Path) -> RalphStatusResult:
    """Synchronize state and write a human-readable Ralph status report."""

    project = require_project_instance(project_path)
    sync = sync_project_state(project)
    plan_steps = _read_plan_steps(project)
    open_step = _next_open_step(plan_steps)
    change_summary = _read_change_summary(project)
    blockers = review_blockers(project)
    try:
        memory = check_memory(project)
        memory_errors = list(memory.errors)
        memory_warnings = list(memory.warnings)
    except Exception as exc:
        memory_errors = [f"memory-check failed: {exc}"]
        memory_warnings = []

    next_action = _resolve_next_action(
        project,
        current_loop=sync.current_loop,
        overall_status=sync.overall_status,
        failed_nodes=sync.failed_nodes,
        open_step=open_step,
        change_summary=change_summary,
        review_blockers=blockers,
        memory_errors=memory_errors,
    )
    report_path = project_memory_path(project) / "00_global" / "RALPH_STATUS.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        _format_status_report(
            project,
            sync.current_loop,
            sync.overall_status,
            sync.passed_nodes,
            sync.failed_nodes,
            plan_steps,
            open_step,
            change_summary,
            blockers,
            memory_errors,
            memory_warnings,
            next_action,
        ),
        encoding="utf-8",
    )
    return RalphStatusResult(
        report_path=report_path,
        messages=[f"state_sync: {sync.overall_status} current_loop={sync.current_loop}", f"report: {report_path}"],
        next_action=next_action,
        current_loop=sync.current_loop,
        overall_status=sync.overall_status,
        open_step=open_step,
        open_changes=change_summary["open"] + change_summary["impact_ready"],
        approved_changes=change_summary["approved"],
        review_blockers=blockers,
        failed_nodes=sync.failed_nodes,
        memory_errors=memory_errors,
    )


def ralph_check(project_path: Path, *, require_final: bool = False) -> RalphCheckResult:
    """Validate whether the Ralph loop has a clean stop condition."""

    project = require_project_instance(project_path)
    status = ralph_status(project)
    steps = _read_plan_steps(project)
    change_summary = _read_change_summary(project)
    errors: list[str] = []
    warnings: list[str] = []

    if not steps:
        errors.append(f"missing executable plan steps in {ACTIVE_PLAN_REL}")
    open_steps = [step for step in steps if step.status in {"pending", "in_progress", "blocked"}]
    if open_steps:
        errors.append("active plan has unfinished or blocked step(s): " + ", ".join(step.step_id for step in open_steps))
    if status.memory_errors:
        errors.extend(status.memory_errors)
    if status.review_blockers:
        errors.append("open review blocker(s): " + "; ".join(status.review_blockers[:8]))
    if status.failed_nodes:
        errors.append("latest failed node(s): " + ", ".join(status.failed_nodes))
    active_changes = change_summary["open"] + change_summary["impact_ready"] + change_summary["approved"]
    if active_changes:
        errors.append("change request(s) still need impact/approval/gate/close: " + ", ".join(active_changes))
    if require_final and status.overall_status != "final_passed":
        errors.append(f"final gate is not passed: {status.overall_status}")
    if not require_final and status.overall_status != "final_passed":
        warnings.append(f"final gate not required for this check; current status is {status.overall_status}")

    report_path = project_memory_path(project) / "00_global" / "RALPH_CHECK.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "\n".join(
            [
                "# Ralph Check",
                "",
                f"- project: {project.name}",
                f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
                f"- result: {'PASS' if not errors else 'FAIL'}",
                f"- require_final: {'yes' if require_final else 'no'}",
                "",
                "## Errors",
                "",
                *([f"- {item}" for item in errors] or ["- none"]),
                "",
                "## Warnings",
                "",
                *([f"- {item}" for item in warnings] or ["- none"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return RalphCheckResult(report_path=report_path, ok=not errors, errors=errors, warnings=warnings)


def ralph_step(
    project_path: Path,
    *,
    status: str,
    step_id: str | None = None,
    note: str = "",
    evidence: str = "",
) -> RalphStepResult:
    """Update the selected or next open plan step and record blockers."""

    project = require_project_instance(project_path)
    normalized = status.strip().lower()
    if normalized not in {"pending", "in_progress", "done", "blocked"}:
        raise ValueError("status must be pending, in_progress, done, or blocked")
    steps = _read_plan_steps(project)
    target = step_id.strip().upper() if step_id else None
    if not target:
        open_step = _next_open_step(steps)
        if not open_step:
            raise ValueError("no open step found in ACTIVE_PLAN.md")
        target = open_step.step_id
    result = update_active_plan_step(project, step_id=target, status=normalized, note=note, evidence=evidence)
    messages = list(result.messages)
    if normalized == "blocked":
        note_result = append_plan_note(
            project,
            kind="error",
            note=note or f"{target} blocked",
            source=ACTIVE_PLAN_REL,
            detail=evidence or "none",
        )
        messages.extend(note_result.messages)
    return RalphStepResult(path=result.path, step_id=target, status=normalized, messages=messages)


def _read_plan_steps(project: Path) -> list[RalphStep]:
    path = project / ACTIVE_PLAN_REL
    if not path.exists():
        return []
    steps: list[RalphStep] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = STEP_RE.match(line)
        if match:
            marker, step_id, text = match.groups()
            steps.append(RalphStep(step_id=step_id, status=MARKER_STATUS[marker], text=text.strip()))
    return steps


def _next_open_step(steps: list[RalphStep]) -> RalphStep | None:
    for wanted in ("in_progress", "pending", "blocked"):
        for step in steps:
            if step.status == wanted:
                return step
    return None


def _read_change_summary(project: Path) -> dict[str, list[str]]:
    summary = {status: [] for status in CHANGE_STATUS_ORDER}
    requests = project / "work/change" / "requests"
    if not requests.exists():
        return summary
    for path in sorted(requests.glob("CR-*.md")):
        fields = _parse_fields(path)
        status = fields.get("status", "")
        change_id = fields.get("id") or path.stem
        if status in summary:
            summary[status].append(change_id)
    return summary


def _parse_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("- ") and ":" in line:
            key, value = line[2:].split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def _resolve_next_action(
    project: Path,
    *,
    current_loop: str,
    overall_status: str,
    failed_nodes: list[str],
    open_step: RalphStep | None,
    change_summary: dict[str, list[str]],
    review_blockers: list[str],
    memory_errors: list[str],
) -> str:
    if memory_errors:
        return "fix memory synchronization, then run `python -m hdlflow.cli memory-check --project <project>`"
    if change_summary["open"]:
        change_id = change_summary["open"][0]
        return f"record impact for {change_id} with `change-impact`; include affected requirements, artifacts, verification, and docset decision"
    if change_summary["impact_ready"]:
        change_id = change_summary["impact_ready"][0]
        return f"review and approve or reject {change_id} with `change-approve`"
    if change_summary["approved"]:
        change_id = change_summary["approved"][0]
        return (
            f"rerun requirements-frontdoor-check, generate-docs, and the affected gate with `--change-id {change_id}`, "
            "then close the change with `change-close`"
        )
    if review_blockers:
        return f"route review blocker with Arbtr, fix owning artifact, then rerun `review-check`: {review_blockers[0]}"
    if failed_nodes:
        node = failed_nodes[0]
        return f"inspect the latest {node} gate report and failure record, then mark the active plan step blocked or rerun after fixing evidence"
    if open_step:
        return f"continue active plan step {open_step.step_id}: {open_step.text}"
    if overall_status == "final_passed":
        return "no next action; final gate is passed and active plan has no open steps"
    return _next_gate_action(current_loop)


def _next_gate_action(current_loop: str) -> str:
    mapping = {
        "docparse": "run requirements-frontdoor-check, generate-docs, then `run-gate --node docparse`",
        "loop1": "run or refresh Loop1 evidence, then `run-gate --node loop1`",
        "loop2": "run Loop2 database/regression evidence, then `run-gate --node loop2`",
        "loop3": "run Loop3 preflight/generation/board evidence, then `run-gate --node loop3`",
        "final": "run `final-audit --level release`",
        "complete": "no next action; workflow is complete",
    }
    return mapping.get(current_loop, "run `sync-project-state` and inspect CURRENT_STATE.md")


def _format_status_report(
    project: Path,
    current_loop: str,
    overall_status: str,
    passed_nodes: list[str],
    failed_nodes: list[str],
    steps: list[RalphStep],
    open_step: RalphStep | None,
    change_summary: dict[str, list[str]],
    review_blockers: list[str],
    memory_errors: list[str],
    memory_warnings: list[str],
    next_action: str,
) -> str:
    lines = [
        "# Ralph Status",
        "",
        f"- project: {project.name}",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- current_loop: {current_loop}",
        f"- overall_status: {overall_status}",
        f"- passed_nodes: {', '.join(passed_nodes) if passed_nodes else 'none'}",
        f"- failed_nodes: {', '.join(failed_nodes) if failed_nodes else 'none'}",
        f"- open_step: {open_step.step_id if open_step else 'none'}",
        f"- next_action: {next_action}",
        "",
        "## Active Plan Steps",
        "",
    ]
    lines.extend([f"- {step.step_id}: {step.status} - {step.text}" for step in steps] or ["- none"])
    lines.extend(["", "## Change Requests", ""])
    for status in CHANGE_STATUS_ORDER:
        values = change_summary.get(status, [])
        lines.append(f"- {status}: {', '.join(values) if values else 'none'}")
    lines.extend(["", "## Review Blockers", ""])
    lines.extend([f"- {item}" for item in review_blockers] or ["- none"])
    lines.extend(["", "## Memory Errors", ""])
    lines.extend([f"- {item}" for item in memory_errors] or ["- none"])
    lines.extend(["", "## Memory Warnings", ""])
    lines.extend([f"- {item}" for item in memory_warnings] or ["- none"])
    lines.extend(["", "## Node Order", ""])
    lines.append("- " + " -> ".join(NODE_ORDER))
    return "\n".join(lines) + "\n"
