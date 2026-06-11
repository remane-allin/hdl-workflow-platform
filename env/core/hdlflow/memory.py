"""Project memory write and validation helpers."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .layout import project_memory_path
from .project import require_project_instance
from .simple_yaml import load_yaml


NODE_MEMORY_DIRS = {
    "input": "00_global",
    "work/docparse": "01_docparse",
    "work/loop1_rtl_tb": "02_loop1",
    "work/loop2_uvm": "03_loop2",
    "work/loop3_fpga_proto": "04_loop3",
    "output": "00_global",
}

NODE_TITLES = {
    "00_global": "Global Iteration Index",
    "01_docparse": "DocParse Iteration Index",
    "02_loop1": "Loop1 Iteration Index",
    "03_loop2": "Loop2 Iteration Index",
    "04_loop3": "Loop3 Iteration Index",
}

BANNED_MEMORY_TERMS = [
    "\u70df\u6d4b",
    "\u5192\u70df",
    "".join(["smo", "ke"]),
    "DdrReadIndex",
    "sequential DDR",
    "16 consecutive",
    "16-word",
]

ACTIVE_PLAN_REL = "work/memory/00_global/ACTIVE_PLAN.md"
PLAN_FINDINGS_REL = "work/memory/00_global/PLAN_FINDINGS.md"
PLAN_ERRORS_REL = "work/memory/00_global/PLAN_ERRORS.md"

PLAN_STATUS_MARKERS = {
    "pending": " ",
    "in_progress": ">",
    "done": "x",
    "blocked": "!",
}


@dataclass(frozen=True)
class MemoryRecordResult:
    messages: list[str]


@dataclass(frozen=True)
class MemoryCheckResult:
    report_path: Path
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class FailureRecordResult:
    path: Path


@dataclass(frozen=True)
class PlanFileResult:
    path: Path
    messages: list[str]


def auto_record_workflow_event(
    project_path: Path,
    *,
    event: str,
    node: str,
    gate_level: str,
    gate_result: str,
    memory_record: Path | str,
    report: Path | str,
    notes: str,
    artifacts: list[Path | str] | None = None,
    latest_summary: str | None = None,
    next_action: str | None = None,
    agent: str | None = None,
    flow_direction: str = "forward",
    feedback_target: str | None = None,
    arbtr_decision: str | None = None,
    baseline_version: str | None = None,
) -> MemoryRecordResult:
    """Record successful automated workflow steps for real project instances."""

    project = require_project_instance(project_path)
    if project.parent.name != "prj":
        return MemoryRecordResult(messages=[f"memory auto-record skipped for non-project path: {project}"])

    stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    event_stem = _safe_iteration_file_stem(event) or "workflow-event"
    iteration_id = f"{event_stem}-{stamp}"
    normalized_artifacts = [_project_relative(project, item) for item in (artifacts or [])]
    result = record_memory_iteration(
        project,
        iteration_id=iteration_id,
        node=node,
        gate_level=gate_level,
        gate_result=gate_result,
        memory_record=_project_relative(project, memory_record),
        report=_project_relative(project, report),
        notes=notes,
        version=iteration_id,
        artifacts=normalized_artifacts,
        latest_summary=latest_summary,
        next_action=next_action,
        agent=agent,
        flow_direction=flow_direction,
        feedback_target=feedback_target,
        arbtr_decision=arbtr_decision,
        baseline_version=baseline_version,
    )
    check = check_memory(project)
    messages = [*result.messages, f"checked: {check.report_path}"]
    messages.extend(f"memory warning: {item}" for item in check.warnings)
    messages.extend(f"memory error: {item}" for item in check.errors)
    return MemoryRecordResult(messages=messages)


def start_active_plan(
    project_path: Path,
    *,
    title: str,
    objective: str,
    steps: list[str],
    plan_id: str | None = None,
    force: bool = False,
) -> PlanFileResult:
    """Create or replace the active file-backed execution plan."""

    project = require_project_instance(project_path)
    if not steps:
        raise ValueError("at least one plan step is required")
    memory_root = project_memory_path(project)
    path = project / ACTIVE_PLAN_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force and _plan_has_open_steps(path):
        raise FileExistsError(f"active plan has unfinished steps: {path}")
    stamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    active_plan_id = plan_id or f"PLAN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    lines = [
        "# Active Plan",
        "",
        f"- schema_version: 1",
        f"- project: {project.name}",
        f"- plan_id: {active_plan_id}",
        f"- status: active",
        f"- updated_at: {stamp}",
        f"- title: {title}",
        f"- objective: {objective}",
        "",
        "## Operating Rule",
        "",
        "- Read this file before choosing the next action.",
        "- Mark a step in this file whenever work starts, completes, or blocks.",
        "- Record durable findings in `PLAN_FINDINGS.md` and failed attempts in `PLAN_ERRORS.md`.",
        "",
        "## Steps",
        "",
    ]
    for index, step in enumerate(steps, 1):
        lines.append(f"- [ ] P{index:03d}: {step}")
    lines.extend(["", "## Step Notes", ""])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _ensure_plan_log(project / PLAN_FINDINGS_REL, "Plan Findings", "Durable analysis findings that should survive context compaction.")
    _ensure_plan_log(project / PLAN_ERRORS_REL, "Plan Errors", "Failed attempts, blockers, and changed approaches.")
    return PlanFileResult(
        path=path,
        messages=[
            f"updated: {ACTIVE_PLAN_REL}",
            f"checked: {PLAN_FINDINGS_REL}",
            f"checked: {PLAN_ERRORS_REL}",
        ],
    )


def update_active_plan_step(
    project_path: Path,
    *,
    step_id: str,
    status: str,
    note: str = "",
    evidence: str = "",
) -> PlanFileResult:
    """Mark a step in ACTIVE_PLAN.md and append a timestamped note."""

    project = require_project_instance(project_path)
    path = project / ACTIVE_PLAN_REL
    if not path.exists():
        raise FileNotFoundError(f"missing active plan: {path}")
    normalized_status = status.strip().lower()
    marker = PLAN_STATUS_MARKERS.get(normalized_status)
    if marker is None:
        raise ValueError("status must be pending, in_progress, done, or blocked")
    normalized_step = step_id.strip().upper()
    lines = path.read_text(encoding="utf-8").splitlines()
    step_pattern = re.compile(rf"^- \[[ x>!]\] {re.escape(normalized_step)}:(.*)$")
    updated = False
    for index, line in enumerate(lines):
        match = step_pattern.match(line)
        if match:
            lines[index] = f"- [{marker}] {normalized_step}:{match.group(1)}"
            updated = True
            break
    if not updated:
        raise ValueError(f"step not found in active plan: {normalized_step}")

    stamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    lines = _replace_metadata_line(lines, "updated_at", stamp)
    lines = _replace_metadata_line(lines, "status", "blocked" if normalized_status == "blocked" else ("complete" if _all_steps_done(lines) else "active"))
    note_text = note.strip() or "no note"
    evidence_text = evidence.strip() or "none"
    if "## Step Notes" not in lines:
        lines.extend(["", "## Step Notes", ""])
    lines.append(f"- {stamp} `{normalized_step}` -> `{normalized_status}`: {note_text}; evidence: {evidence_text}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return PlanFileResult(path=path, messages=[f"updated: {ACTIVE_PLAN_REL}"])


def append_plan_note(
    project_path: Path,
    *,
    kind: str,
    note: str,
    source: str = "",
    command: str = "",
    detail: str = "",
) -> PlanFileResult:
    """Append a durable finding or failed attempt to the plan log files."""

    project = require_project_instance(project_path)
    normalized = kind.strip().lower()
    if normalized not in {"finding", "error"}:
        raise ValueError("kind must be finding or error")
    rel = PLAN_FINDINGS_REL if normalized == "finding" else PLAN_ERRORS_REL
    title = "Plan Findings" if normalized == "finding" else "Plan Errors"
    description = (
        "Durable analysis findings that should survive context compaction."
        if normalized == "finding"
        else "Failed attempts, blockers, and changed approaches."
    )
    path = project / rel
    _ensure_plan_log(path, title, description)
    stamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    lines = [
        "",
        f"## {stamp}",
        "",
        f"- note: {note.strip()}",
    ]
    if source.strip():
        lines.append(f"- source: {source.strip()}")
    if command.strip():
        lines.append(f"- command: {command.strip()}")
    if detail.strip():
        lines.extend(["", "### Detail", "", detail.strip()])
    path.write_text(path.read_text(encoding="utf-8").rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return PlanFileResult(path=path, messages=[f"updated: {rel}"])


def record_memory_iteration(
    project_path: Path,
    *,
    iteration_id: str,
    node: str,
    gate_level: str,
    gate_result: str,
    memory_record: str,
    report: str,
    notes: str,
    version: str | None = None,
    artifacts: list[str] | None = None,
    latest_summary: str | None = None,
    next_action: str | None = None,
    agent: str | None = None,
    flow_direction: str = "forward",
    feedback_target: str | None = None,
    arbtr_decision: str | None = None,
    baseline_version: str | None = None,
) -> MemoryRecordResult:
    """Write a single iteration to all project memory front-door files."""

    project = require_project_instance(project_path)
    memory_root = project_memory_path(project)
    if not memory_root.is_dir():
        raise FileNotFoundError(f"missing memory directory: {memory_root}")

    with _memory_lock(memory_root):
        completed_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        agent_value = agent or _default_agent_for_node(node)
        flow_direction_value = flow_direction or "forward"
        feedback_target_value = feedback_target or "null"
        arbtr_decision_value = arbtr_decision or "null"
        baseline_version_value = baseline_version or "null"
        rollback_manifest = "null"
        if _is_active_gate(gate_result):
            rollback_manifest = _write_rollback_manifest(
                project,
                iteration_id=iteration_id,
                node=node,
                gate_level=gate_level,
                gate_result=gate_result,
                memory_record=memory_record,
                report=report,
                artifacts=artifacts or [],
                agent=agent_value,
                flow_direction=flow_direction_value,
                feedback_target=feedback_target_value,
                arbtr_decision=arbtr_decision_value,
                baseline_version=baseline_version_value,
            )
        entry = {
            "node": node,
            "started_at": completed_at,
            "completed_at": completed_at,
            "owner": "project_local",
            "agent": agent_value,
            "flow_direction": flow_direction_value,
            "feedback_target": feedback_target_value,
            "arbtr_decision": arbtr_decision_value,
            "baseline_version": baseline_version_value,
            "memory_record": memory_record,
            "snapshot": rollback_manifest,
            "report": report,
            "artifacts": ",".join(artifacts or []),
            "gate_level": gate_level,
            "gate_result": gate_result,
            "change_request": "null",
        }

        messages: list[str] = []
        _upsert_index(memory_root / "index.yaml", project.name, iteration_id, entry)
        messages.append("updated: work/memory/index.yaml")

        node_dir_name = NODE_MEMORY_DIRS.get(node)
        if not node_dir_name:
            raise ValueError(f"unsupported node for memory write: {node}")
        node_iterations = memory_root / node_dir_name / "iterations.md"
        _upsert_iteration_row(
            node_iterations,
            title=NODE_TITLES.get(node_dir_name, "Iteration Index"),
            iteration_id=iteration_id,
            time_value=completed_at[:10],
            memory_record=memory_record,
            report=report,
            gate_level=gate_level,
            gate_result=gate_result,
            notes=notes,
        )
        messages.append(f"updated: {node_iterations.relative_to(project)}")

        if _is_active_gate(gate_result):
            _upsert_active_version(
                memory_root / "active_versions.md",
                version=version or iteration_id,
                iteration_id=iteration_id,
                gate_level=gate_level,
                gate_result=gate_result,
                memory_record=memory_record,
                report=report,
                notes=notes,
            )
            messages.append("updated: work/memory/active_versions.md")
            if rollback_manifest != "null":
                messages.append(f"updated: {rollback_manifest}")

        if latest_summary or next_action:
            _update_current_state(
                memory_root / "00_global" / "CURRENT_STATE.md",
                active_node=node,
                latest_passed_gate=gate_level if _is_active_gate(gate_result) else None,
                latest_summary=latest_summary,
                next_action=next_action,
            )
            messages.append("updated: work/memory/00_global/CURRENT_STATE.md")

        return MemoryRecordResult(messages=messages)


def record_failure_event(
    project_path: Path,
    *,
    command: str,
    message: str,
    detail: str | None = None,
) -> FailureRecordResult:
    project = require_project_instance(project_path)
    failure_dir = project_memory_path(project) / "recovery" / "failure_records"
    failure_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    path = failure_dir / f"failure-{stamp}.md"
    lines = [
        "# Failure Record",
        "",
        f"- project: {project.name}",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- command: {command}",
        f"- message: {message}",
        "",
        "## Detail",
        "",
        detail or "none",
        "",
        "## Recovery Guidance",
        "",
        "- Re-run the command after fixing the reported issue.",
        "- Run `python -m hdlflow.cli doctor --workspace <workspace> --project <project>`.",
        "- Run `python -m hdlflow.cli memory-check --project <project>` after state-changing commands.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        append_plan_note(
            project,
            kind="error",
            note=message,
            command=command,
            source=str(path.relative_to(project)).replace("\\", "/"),
            detail=detail or "none",
        )
    except Exception:
        pass
    return FailureRecordResult(path)


def check_memory(project_path: Path) -> MemoryCheckResult:
    """Validate memory synchronization and write a report."""

    project = project_path.resolve()
    memory_root = project_memory_path(project)
    report_path = memory_root / "00_global" / "MEMORY_CHECK_REPORT.md"
    errors: list[str] = []
    warnings: list[str] = []

    index_path = memory_root / "index.yaml"
    try:
        index = load_yaml(index_path)
    except Exception as exc:
        index = {}
        errors.append(f"work/memory/index.yaml is not parseable: {exc}")

    if index:
        if index.get("project") != project.name:
            errors.append(f"work/memory/index.yaml project mismatch: {index.get('project')} != {project.name}")
        iterations = index.get("iterations")
        if not isinstance(iterations, dict):
            errors.append("work/memory/index.yaml iterations must be a mapping keyed by iteration_id")
            iterations = {}
        for iteration_id, raw_entry in iterations.items():
            if not isinstance(raw_entry, dict):
                errors.append(f"iteration {iteration_id} must be a mapping")
                continue
            _check_required_fields(iteration_id, raw_entry, errors)
            _check_referenced_path(project, raw_entry.get("memory_record"), warnings, f"{iteration_id}.memory_record")
            _check_referenced_path(project, raw_entry.get("report"), warnings, f"{iteration_id}.report")
            node = str(raw_entry.get("node") or "")
            node_dir = NODE_MEMORY_DIRS.get(node)
            if node_dir:
                node_iterations = memory_root / node_dir / "iterations.md"
                _check_file_contains(node_iterations, str(iteration_id), warnings, f"{iteration_id} missing from {node_iterations.relative_to(project)}")
            else:
                errors.append(f"iteration {iteration_id} has unsupported node: {node}")
            if _is_active_gate(str(raw_entry.get("gate_result") or "")):
                _check_file_contains(memory_root / "active_versions.md", str(iteration_id), warnings, f"{iteration_id} missing from work/memory/active_versions.md")

    for path in memory_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".yaml", ".yml", ".txt"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            text_l = text.lower()
            for term in BANNED_MEMORY_TERMS:
                if term.lower() in text_l:
                    warnings.append(f"banned/stale memory term '{term}' found in {path.relative_to(project)}")

    for rel in (ACTIVE_PLAN_REL, PLAN_FINDINGS_REL, PLAN_ERRORS_REL):
        plan_path = project / rel
        if not plan_path.exists():
            errors.append(f"missing planning file: {rel}")

    lines = [
        "# Memory Check Report",
        "",
        f"- project: {project.name}",
        f"- generated_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- result: {'PASS' if not errors else 'FAIL'}",
        "",
        "## Errors",
        "",
    ]
    lines.extend([f"- {item}" for item in errors] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {item}" for item in warnings] or ["- none"])
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return MemoryCheckResult(report_path=report_path, errors=errors, warnings=warnings)


def _plan_has_open_steps(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return bool(re.search(r"(?m)^- \[[ >!]\] P\d{3}:", text))


def _ensure_plan_log(path: Path, title: str, description: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {title}",
        "",
        f"- schema_version: 1",
        f"- created_at: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}",
        f"- purpose: {description}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _replace_metadata_line(lines: list[str], key: str, value: str) -> list[str]:
    prefix = f"- {key}:"
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = f"- {key}: {value}"
            return lines
    insert_at = 1
    while insert_at < len(lines) and lines[insert_at].startswith("- "):
        insert_at += 1
    return [*lines[:insert_at], f"- {key}: {value}", *lines[insert_at:]]


def _all_steps_done(lines: list[str]) -> bool:
    step_lines = [line for line in lines if re.match(r"^- \[[ x>!]\] P\d{3}:", line)]
    return bool(step_lines) and all(line.startswith("- [x] ") for line in step_lines)


def _upsert_index(path: Path, project_name: str, iteration_id: str, entry: dict[str, str]) -> None:
    if path.exists():
        try:
            data = load_yaml(path)
        except Exception:
            data = {}
    else:
        data = {}
    iterations = data.get("iterations")
    if not isinstance(iterations, dict):
        iterations = {}
    iterations[iteration_id] = entry

    lines = ["schema_version: 1", f"project: {project_name}", "iterations:"]
    for item_id, item in iterations.items():
        lines.append(f"  {item_id}:")
        for key in [
            "node",
            "started_at",
            "completed_at",
            "owner",
            "agent",
            "flow_direction",
            "feedback_target",
            "arbtr_decision",
            "baseline_version",
            "memory_record",
            "snapshot",
            "report",
            "artifacts",
            "gate_level",
            "gate_result",
            "change_request",
        ]:
            lines.append(f"    {key}: {_yaml_scalar(item.get(key))}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_rollback_manifest(
    project: Path,
    *,
    iteration_id: str,
    node: str,
    gate_level: str,
    gate_result: str,
    memory_record: str,
    report: str,
    artifacts: list[str],
    agent: str,
    flow_direction: str,
    feedback_target: str,
    arbtr_decision: str,
    baseline_version: str,
) -> str:
    rollback_dir = project_memory_path(project) / "recovery" / "rollback_manifests"
    rollback_dir.mkdir(parents=True, exist_ok=True)
    path = rollback_dir / f"{_safe_iteration_file_stem(iteration_id)}.json"
    rel_paths = [memory_record, report, *artifacts]
    unique_paths = []
    for rel in rel_paths:
        if rel and rel != "null" and rel not in unique_paths:
            unique_paths.append(rel)
    data = {
        "schema_version": 1,
        "project": project.name,
        "iteration_id": iteration_id,
        "node": node,
        "gate_level": gate_level,
        "gate_result": gate_result,
        "agent": agent,
        "flow_direction": flow_direction,
        "feedback_target": feedback_target,
        "arbtr_decision": arbtr_decision,
        "baseline_version": baseline_version,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "files": [_hash_project_file(project, rel) for rel in unique_paths],
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(path.relative_to(project)).replace("\\", "/")


def _safe_iteration_file_stem(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")


def _hash_project_file(project: Path, rel: str) -> dict[str, str | int | None]:
    path = project / rel
    item: dict[str, str | int | None] = {"path": rel.replace("\\", "/"), "sha256": None, "size": None}
    if not path.exists() or not path.is_file():
        return item
    data = path.read_bytes()
    item["sha256"] = hashlib.sha256(data).hexdigest()
    item["size"] = len(data)
    return item


@contextmanager
def _memory_lock(memory_root: Path):
    lock_path = memory_root / ".memory.lock"
    fd: int | None = None
    deadline = time.time() + 30.0
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("ascii", errors="ignore"))
            break
        except FileExistsError:
            if time.time() > deadline:
                raise TimeoutError(f"timed out waiting for memory lock: {lock_path}")
            time.sleep(0.1)
    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _upsert_iteration_row(
    path: Path,
    *,
    title: str,
    iteration_id: str,
    time_value: str,
    memory_record: str,
    report: str,
    gate_level: str,
    gate_result: str,
    notes: str,
) -> None:
    row = f"| {iteration_id} | {time_value} | {memory_record} | {report} | {gate_level} | {gate_result} | {notes} |"
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    else:
        lines = [
            f"# {title}",
            "",
            "| Iteration ID | Time | Memory Record | Report | Gate Level | Gate Result | Notes |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    updated = False
    for index, line in enumerate(lines):
        if line.startswith(f"| {iteration_id} |"):
            lines[index] = row
            updated = True
            break
    if not updated:
        if not any(line.startswith("| Iteration ID |") for line in lines):
            lines.extend(
                [
                    "",
                    "| Iteration ID | Time | Memory Record | Report | Gate Level | Gate Result | Notes |",
                    "| --- | --- | --- | --- | --- | --- | --- |",
                ]
            )
        lines.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _upsert_active_version(
    path: Path,
    *,
    version: str,
    iteration_id: str,
    gate_level: str,
    gate_result: str,
    memory_record: str,
    report: str,
    notes: str,
) -> None:
    row = f"| {version} | {iteration_id} | {gate_level} | {gate_result} | {memory_record} | {report} | {notes} |"
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    else:
        lines = [
            "# Active Version Memory",
            "",
            "This file is the project memory front door for valid, closed, or currently active versions.",
            "",
            "| Version | Iteration ID | Gate Level | Gate Result | Memory Record | Report | Notes |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    updated = False
    for index, line in enumerate(lines):
        if line.startswith(f"| {version} |") or f"| {iteration_id} |" in line:
            lines[index] = row
            updated = True
            break
    if not updated:
        lines.append(row)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _update_current_state(
    path: Path,
    *,
    active_node: str,
    latest_passed_gate: str | None,
    latest_summary: str | None,
    next_action: str | None,
) -> None:
    values = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "active_node": active_node,
    }
    if latest_passed_gate:
        values["latest_passed_gate"] = latest_passed_gate
    if latest_summary:
        values["latest_summary"] = latest_summary
    if next_action:
        values["next_action"] = next_action

    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    else:
        lines = ["# Current State", ""]
    seen: set[str] = set()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key = stripped[2:].split(":", 1)[0].strip()
        if key in values:
            lines[index] = f"- {key}: {values[key]}"
            seen.add(key)
    for key, value in values.items():
        if key not in seen:
            lines.append(f"- {key}: {value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _is_active_gate(gate_result: str) -> bool:
    text = gate_result.strip()
    if re.fullmatch(r"(?i)(PASS|COMPLETE)", text):
        return True
    return re.search(r"(?im)^\s*(?:[-*]\s*)?result\s*:\s*(PASS|COMPLETE)\s*$", text) is not None


def _default_agent_for_node(node: str) -> str:
    mapping = {
        "input": "spec",
        "work/docparse": "arch",
        "work/loop1_rtl_tb": "exec",
        "work/loop2_uvm": "sim",
        "work/loop3_fpga_proto": "sim",
        "output": "arbtr",
    }
    return mapping.get(node, "arbtr")


def _check_required_fields(iteration_id: Any, entry: dict[str, Any], errors: list[str]) -> None:
    for field in ["node", "memory_record", "report", "gate_level", "gate_result"]:
        if not entry.get(field):
            errors.append(f"iteration {iteration_id} missing required field: {field}")


def _check_referenced_path(project: Path, value: Any, warnings: list[str], label: str) -> None:
    if not value or str(value) == "null":
        return
    rel = Path(str(value))
    if rel.is_absolute() or ".." in rel.parts:
        warnings.append(f"{label} should be project-relative: {value}")
        return
    if not (project / rel).exists():
        warnings.append(f"{label} path not found: {value}")


def _check_file_contains(path: Path, needle: str, warnings: list[str], message: str) -> None:
    if not path.exists():
        warnings.append(f"missing memory view: {path}")
        return
    if needle not in path.read_text(encoding="utf-8", errors="ignore"):
        warnings.append(message)


def _yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    text = str(value)
    if text == "":
        return "null"
    if any(char in text for char in [": ", "#", "\n", "|"]):
        return '"' + text.replace('"', '\\"') + '"'
    return text


def _project_relative(project: Path, value: Path | str) -> str:
    path = Path(value)
    if path.is_absolute():
        try:
            return str(path.resolve().relative_to(project)).replace("\\", "/")
        except ValueError:
            return str(path)
    return str(path).replace("\\", "/")
