"""Design change-control records and checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .project import require_project_instance


VALID_ID = re.compile(r"^CR-[0-9]{14}-[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class ChangeResult:
    path: Path
    messages: list[str]


@dataclass(frozen=True)
class ChangeCheckResult:
    ok: bool
    report_path: Path
    messages: list[str]


def open_change(
    project_path: Path,
    *,
    title: str,
    reason: str,
    scope: str,
    risk: str,
    owner: str = "project_local",
) -> ChangeResult:
    project = require_project_instance(project_path)
    change_id = _new_change_id(title)
    requests_dir = project / "change_control" / "requests"
    requests_dir.mkdir(parents=True, exist_ok=True)
    path = requests_dir / f"{change_id}.md"
    lines = [
        f"# Change Request {change_id}",
        "",
        f"- id: {change_id}",
        "- status: open",
        f"- created_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- owner: {owner}",
        f"- title: {title}",
        f"- risk: {risk}",
        "",
        "## Reason",
        "",
        reason,
        "",
        "## Scope",
        "",
        scope,
        "",
        "## Required Next Records",
        "",
        "- impact analysis under `change_control/impact_analysis/`",
        "- approval under `change_control/approvals/`",
        "- trace update under `change_control/trace_updates/` when requirements, RTL, tests, or reports move",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ChangeResult(path, [f"opened: {change_id}", f"request: {path}"])


def record_impact(
    project_path: Path,
    *,
    change_id: str,
    requirements: list[str],
    artifacts: list[str],
    verification: list[str],
    rollback: str,
    risk: str,
) -> ChangeResult:
    _validate_change_id(change_id)
    project = require_project_instance(project_path)
    _require_request(project, change_id)
    impact_dir = project / "change_control" / "impact_analysis"
    impact_dir.mkdir(parents=True, exist_ok=True)
    path = impact_dir / f"{change_id}.md"
    lines = [
        f"# Impact Analysis {change_id}",
        "",
        f"- id: {change_id}",
        "- status: impact_ready",
        f"- updated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- risk: {risk}",
        "",
        "## Requirements",
        "",
        *[f"- {item}" for item in requirements],
        "",
        "## Artifacts",
        "",
        *[f"- {item}" for item in artifacts],
        "",
        "## Required Verification",
        "",
        *[f"- {item}" for item in verification],
        "",
        "## Rollback Plan",
        "",
        rollback,
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _update_request_status(project, change_id, "impact_ready")
    return ChangeResult(path, [f"impact recorded: {change_id}", f"impact: {path}"])


def approve_change(
    project_path: Path,
    *,
    change_id: str,
    approver: str,
    decision: str,
    notes: str,
) -> ChangeResult:
    _validate_change_id(change_id)
    if decision not in {"approved", "rejected"}:
        raise ValueError("decision must be approved or rejected")
    project = require_project_instance(project_path)
    _require_request(project, change_id)
    impact = project / "change_control" / "impact_analysis" / f"{change_id}.md"
    if decision == "approved" and not impact.exists():
        raise FileNotFoundError(f"approval requires impact analysis first: {impact}")

    approvals_dir = project / "change_control" / "approvals"
    approvals_dir.mkdir(parents=True, exist_ok=True)
    path = approvals_dir / f"{change_id}.md"
    lines = [
        f"# Approval {change_id}",
        "",
        f"- id: {change_id}",
        f"- status: {decision}",
        f"- approved_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- approver: {approver}",
        "",
        "## Notes",
        "",
        notes,
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _update_request_status(project, change_id, decision)
    return ChangeResult(path, [f"{decision}: {change_id}", f"approval: {path}"])


def close_change(project_path: Path, *, change_id: str, gate_report: str, notes: str) -> ChangeResult:
    _validate_change_id(change_id)
    project = require_project_instance(project_path)
    _require_request(project, change_id)
    report_path = project / gate_report
    if not report_path.exists():
        raise FileNotFoundError(f"gate report not found: {gate_report}")
    trace_dir = project / "change_control" / "trace_updates"
    trace_dir.mkdir(parents=True, exist_ok=True)
    path = trace_dir / f"{change_id}.md"
    lines = [
        f"# Trace Update {change_id}",
        "",
        f"- id: {change_id}",
        "- status: closed",
        f"- closed_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- gate_report: {gate_report}",
        "",
        "## Notes",
        "",
        notes,
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _update_request_status(project, change_id, "closed")
    return ChangeResult(path, [f"closed: {change_id}", f"trace_update: {path}"])


def check_changes(project_path: Path) -> ChangeCheckResult:
    project = project_path.resolve()
    messages: list[str] = []
    ok = True
    requests = sorted((project / "change_control" / "requests").glob("CR-*.md"))
    for request in requests:
        fields = _parse_fields(request)
        change_id = fields.get("id") or request.stem
        status = fields.get("status", "")
        if not VALID_ID.match(change_id):
            ok = False
            messages.append(f"FAIL {request.relative_to(project)} has invalid id: {change_id}")
        if status in {"open", "impact_ready"}:
            ok = False
            messages.append(f"FAIL {change_id} is not approved or closed: {status}")
        if status in {"approved", "closed"} and not (project / "change_control" / "impact_analysis" / f"{change_id}.md").exists():
            ok = False
            messages.append(f"FAIL {change_id} missing impact analysis")
        if status == "closed" and not (project / "change_control" / "trace_updates" / f"{change_id}.md").exists():
            ok = False
            messages.append(f"FAIL {change_id} missing trace update")
    if not messages:
        messages.append("PASS no blocking change-control issues")
    report = project / "change_control" / "CHANGE_CONTROL_CHECK.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "\n".join(
            [
                "# Change Control Check",
                "",
                f"- project: {project.name}",
                f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
                f"- result: {'PASS' if ok else 'FAIL'}",
                "",
                "## Results",
                "",
                *[f"- {message}" for message in messages],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return ChangeCheckResult(ok, report, messages)


def _new_change_id(title: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", title.strip()).strip("-").lower()
    if not slug:
        slug = "change"
    return f"CR-{datetime.now().strftime('%Y%m%d%H%M%S')}-{slug[:40]}"


def _validate_change_id(change_id: str) -> None:
    if not VALID_ID.match(change_id):
        raise ValueError(f"invalid change id: {change_id}")


def _require_request(project: Path, change_id: str) -> Path:
    path = project / "change_control" / "requests" / f"{change_id}.md"
    if not path.exists():
        raise FileNotFoundError(f"change request not found: {path}")
    return path


def _update_request_status(project: Path, change_id: str, status: str) -> None:
    path = _require_request(project, change_id)
    lines = path.read_text(encoding="utf-8").splitlines()
    updated = False
    for index, line in enumerate(lines):
        if line.startswith("- status:"):
            lines[index] = f"- status: {status}"
            updated = True
            break
    if not updated:
        lines.insert(2, f"- status: {status}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("- ") and ":" in line:
            key, value = line[2:].split(":", 1)
            fields[key.strip()] = value.strip()
    return fields
