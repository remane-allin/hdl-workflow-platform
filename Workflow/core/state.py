from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from .contracts import FORMAT_VERSION, STAGES, STATUSES, ContractError, ProjectContext
from Workflow.tools.filesystem import atomic_write_json, read_json


def initial_state(project_id: str, design_version: int) -> dict[str, Any]:
    return {
        "format_version": FORMAT_VERSION,
        "project_id": project_id,
        "design_version": design_version,
        "stages": {
            stage: {
                "status": "NOT_RUN",
                "design_version": design_version,
                "summary": "",
                "report": "",
                "issue": "",
            }
            for stage in STAGES
        },
        "current_action": None,
        "attempts": {stage: 0 for stage in STAGES},
    }


def validate_state(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("format_version") != FORMAT_VERSION:
        raise ContractError("invalid state format")
    if not isinstance(value.get("project_id"), str):
        raise ContractError("state project_id is required")
    if value.get("current_action") is not None and not isinstance(value["current_action"], str):
        raise ContractError("current_action must be null or a string")
    stages = value.get("stages")
    if not isinstance(stages, dict) or tuple(stages) != STAGES:
        raise ContractError("state must contain the six ordered stages")
    for stage in STAGES:
        if stages[stage].get("status") not in STATUSES:
            raise ContractError(f"invalid status for {stage}")
    attempts = value.get("attempts")
    if not isinstance(attempts, dict) or tuple(attempts) != STAGES:
        raise ContractError("state attempts must contain the six ordered stages")
    if any(not isinstance(attempts[stage], int) or attempts[stage] < 0 for stage in STAGES):
        raise ContractError("state attempts must be non-negative integers")
    return value


def load_state(context: ProjectContext, *, create: bool = False, design_version: int = 1) -> dict[str, Any]:
    if not context.state_path.exists():
        if not create:
            raise ContractError("project state is missing")
        value = initial_state(context.project_id, design_version)
        atomic_write_json(context.state_path, value)
        return value
    value = validate_state(read_json(context.state_path))
    if value.get("design_version") != design_version:
        if not create:
            raise ContractError("state design_version does not match current design")
        value = initial_state(context.project_id, design_version)
        atomic_write_json(context.state_path, value)
    return value


def save_state(context: ProjectContext, value: dict[str, Any]) -> None:
    validate_state(value)
    atomic_write_json(context.state_path, value)


def rebase_state(
    context: ProjectContext,
    previous: dict[str, Any],
    design_version: int,
    first_invalidated_stage: str,
) -> dict[str, Any]:
    """Bind state to a new design and retain only evidence that is still valid."""
    if first_invalidated_stage not in STAGES:
        raise ContractError("invalid design invalidation stage")
    updated = initial_state(context.project_id, design_version)
    boundary = STAGES.index(first_invalidated_stage)
    for stage in STAGES[1:boundary]:
        if previous["stages"][stage]["status"] == "PASS":
            updated["stages"][stage] = deepcopy(previous["stages"][stage])
            updated["stages"][stage]["design_version"] = design_version
    previous_attempts = previous.get("attempts", {})
    for stage in STAGES[:boundary]:
        updated["attempts"][stage] = previous_attempts.get(stage, 0)
    save_state(context, updated)
    return updated


def set_action(context: ProjectContext, state: dict[str, Any], action: str | None) -> dict[str, Any]:
    updated = deepcopy(state)
    updated["current_action"] = action
    save_state(context, updated)
    return updated


def set_stage(
    context: ProjectContext,
    state: dict[str, Any],
    stage: str,
    status: str,
    *,
    summary: str = "",
    report: str = "",
    issue: str = "",
) -> dict[str, Any]:
    if stage not in STAGES or status not in STATUSES:
        raise ContractError("invalid stage transition")
    updated = deepcopy(state)
    updated["stages"][stage] = {
        "status": status,
        "design_version": updated["design_version"],
        "summary": summary,
        "report": report,
        "issue": issue,
    }
    if status == "PASS":
        updated["attempts"][stage] = 0
    if status != "PASS":
        index = STAGES.index(stage)
        for downstream in STAGES[index + 1 :]:
            updated["stages"][downstream] = {
                "status": "NOT_RUN",
                "design_version": updated["design_version"],
                "summary": "invalidated by upstream change",
                "report": "",
                "issue": "",
            }
    updated["current_action"] = None
    save_state(context, updated)
    return updated


def note_attempt_failure(context: ProjectContext, state: dict[str, Any], stage: str) -> tuple[dict[str, Any], int]:
    if stage not in STAGES:
        raise ContractError("invalid attempt stage")
    updated = deepcopy(state)
    attempt = updated["attempts"][stage] + 1
    updated["attempts"][stage] = attempt
    save_state(context, updated)
    return updated, attempt


def recover_state(context: ProjectContext, design_version: int) -> dict[str, Any]:
    try:
        value = load_state(context, design_version=design_version)
    except (OSError, ValueError, ContractError):
        value = initial_state(context.project_id, design_version)
    value["current_action"] = None
    if value.get("design_version") != design_version:
        value = initial_state(context.project_id, design_version)
    save_state(context, value)
    return value


def status_view(context: ProjectContext, state: dict[str, Any]) -> dict[str, Any]:
    timings: dict[str, dict[str, datetime]] = {stage: {} for stage in STAGES}
    flow = context.project_root / "output" / "report" / "current" / "flow.log"
    if flow.is_file():
        for line in flow.read_text(encoding="utf-8", errors="replace").splitlines():
            fields = dict(
                part.split("=", 1) for part in line.split("|") if "=" in part
            )
            stage = fields.get("stage")
            status = fields.get("status")
            if stage not in timings or "time" not in fields:
                continue
            stamp = datetime.fromisoformat(fields["time"])
            if status == "START":
                timings[stage]["start"] = stamp
                timings[stage].pop("end", None)
            elif status in {"PASS", "FAIL", "BLOCKED"} and "start" in timings[stage]:
                timings[stage]["end"] = stamp
    stages = deepcopy(state["stages"])
    for stage in STAGES:
        stamps = timings[stage]
        stages[stage]["elapsed_seconds"] = (
            (stamps["end"] - stamps["start"]).total_seconds()
            if "start" in stamps and "end" in stamps
            else None
        )
    next_stage = next(
        (stage for stage in STAGES if state["stages"][stage]["status"] != "PASS"),
        None,
    )
    blocked = [
        stage for stage in STAGES if state["stages"][stage]["status"] in {"BLOCKED", "FAIL"}
    ]
    return {
        "project_id": state["project_id"],
        "design_version": state["design_version"],
        "current_action": state["current_action"],
        "stages": stages,
        "attempts": deepcopy(state["attempts"]),
        "recovery_required": state["current_action"] is not None,
        "waiting_for": "architecture review" if any(value >= 3 for value in state["attempts"].values()) else (
            "stage correction" if blocked else "none"
        ),
        "next_legal_action": f"run --to {next_stage}" if next_stage else "none; local release is complete",
    }
