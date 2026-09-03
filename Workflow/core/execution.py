from __future__ import annotations

from pathlib import Path
from typing import Any

from .access import authorize_project_write
from .contracts import STAGES, ProjectContext, WorkflowError
from .departments import configuration, physical, release, reporting, rtl_tb, verification
from .review import prerequisites, review_design, review_gate_b
from .state import load_state, note_attempt_failure, rebase_state, recover_state, set_action, set_stage
from Workflow.reports.tools.extract import (
    ISSUE_HEADER,
    append_flow,
    load_report,
    parse_xsim_log,
    rebase_report,
    reconcile_report,
    record_failure,
)
from Workflow.tools.design import load_design
from Workflow.tools.dispatch import StageDispatch
from Workflow.tools.filesystem import atomic_write_json, read_json, remove_owned
from Workflow.tools.rtl import reliable_rule_findings
from Workflow.tools.xilinx import run_vivado


def _authorize_stage_writes(
    context: ProjectContext,
    design: dict[str, Any],
    stage: str,
    gate_a_passed: bool,
) -> None:
    targets = [
        context.state_path,
        context.project_root / "output" / "report",
    ]
    if stage == "design":
        targets.extend([
            context.project_root / "input" / "current",
            context.project_root / "input" / "previous",
        ])
    else:
        targets.append(context.project_root / "output" / "vivado")
    if stage == "release" and design["implementation"]["vitis"].get("enabled"):
        targets.append(context.project_root / "output" / "vitis")
    for target in targets:
        authorize_project_write(
            context,
            target,
            gate_a_passed=gate_a_passed,
            stage=stage,
        )


def _design_invalidation_stage(previous: dict[str, Any], current: dict[str, Any]) -> str:
    """Return the earliest stage whose evidence a reviewed design change invalidates."""
    for section in ("project", "requirements", "architecture", "interfaces", "budgets", "verification"):
        if previous.get(section) != current.get(section):
            return "design"

    old_impl = previous.get("implementation", {})
    new_impl = current.get("implementation", {})
    for section in ("rtl", "verification_sources"):
        if old_impl.get(section) != new_impl.get(section):
            return "rtl"
    if old_impl.get("constraints") != new_impl.get("constraints"):
        return "synth"

    old_vivado = old_impl.get("vivado", {})
    new_vivado = new_impl.get("vivado", {})
    vivado_keys = set(old_vivado) | set(new_vivado)
    changed_vivado = {key for key in vivado_keys if old_vivado.get(key) != new_vivado.get(key)}
    release_keys = {"release_mode", "results"}
    synth_keys = {
        "synthesis_strategy", "synthesis_directive", "synthesis_mode",
        "constraints_used_in_synthesis",
    }
    route_keys = {
        "implementation_strategy", "opt_directive", "opt_resynth_area", "place_directive",
        "phys_opt_directive", "route_directive", "seed",
    }
    if changed_vivado - release_keys - route_keys - synth_keys:
        return "rtl"
    if changed_vivado & synth_keys:
        return "synth"
    if changed_vivado & route_keys:
        return "route"
    if changed_vivado & release_keys or old_impl.get("vitis") != new_impl.get("vitis"):
        return "release"
    if old_impl.get("reuse_assets", []) != new_impl.get("reuse_assets", []):
        return "release"
    return "design"


def _execute_stage(context: ProjectContext, design: dict[str, Any], stage: str) -> dict[str, Any]:
    if stage == "design":
        return configuration.gate_a(context)
    if stage == "rtl":
        result = rtl_tb.run(context, design)
        sync = run_vivado(context, design, "sync")
        result["native_project"] = sync
        return result
    if stage == "verify":
        run_vivado(context, design, "sync")
        result = verification.run(context, design)
        interim = load_report(context, design)
        interim["rtl_tb"] = {"status": "PASS"}
        interim["verification"] = result
        review_gate_b(context, interim)
        result["gate_b"] = "PASS"
        return result
    if stage in {"synth", "route"}:
        return physical.run(context, design, stage)
    if stage == "release":
        return release.run(context, design)
    raise WorkflowError(f"unsupported stage: {stage}")


def refresh_design(context: ProjectContext) -> dict[str, Any]:
    next_path = context.project_root / "input" / "next" / "design.json"
    pending = context.project_root / "input" / "pending"
    pending_items = [item for item in pending.iterdir()] if pending.exists() else []
    if not next_path.exists():
        if pending_items:
            raise WorkflowError("pending inputs exist but no complete next/design.json has been prepared")
        return review_design(context)
    next_design = load_design(next_path)
    if context.design_path.exists():
        current = load_design(context.design_path)
        if next_design["design_version"] != current["design_version"] + 1:
            raise WorkflowError("next design_version must increment current by exactly one")
    result = review_design(context, next_path)
    previous = context.project_root / "input" / "previous" / "design.json"
    previous.parent.mkdir(parents=True, exist_ok=True)
    original = read_json(context.design_path) if context.design_path.exists() else None
    try:
        if original is not None:
            atomic_write_json(previous, original)
        atomic_write_json(context.design_path, next_design)
        next_path.unlink()
        if next_path.parent.exists() and not any(next_path.parent.iterdir()):
            next_path.parent.rmdir()
        for item in pending_items:
            remove_owned(item)
    except BaseException:
        if original is not None:
            atomic_write_json(context.design_path, original)
        raise
    return result


def run_to(context: ProjectContext, target: str) -> dict[str, Any]:
    if target not in STAGES:
        raise WorkflowError(f"invalid target stage: {target}")
    next_design_path = context.project_root / "input" / "next" / "design.json"
    if context.design_path.is_file():
        design = load_design(context.design_path)
    elif target == "design" and next_design_path.is_file():
        design = load_design(next_design_path)
    else:
        raise WorkflowError("current design is missing; prepare input/next/design.json and run design first")
    state = load_state(context, create=True, design_version=design["design_version"])
    target_index = STAGES.index(target)
    for stage in STAGES[: target_index + 1]:
        pending = context.project_root / "input" / "pending"
        design_change_waiting = stage == "design" and (
            next_design_path.exists() or (pending.exists() and any(pending.iterdir()))
        )
        if state["stages"][stage]["status"] == "PASS" and not design_change_waiting:
            continue
        prerequisites(state, stage)
        _authorize_stage_writes(
            context,
            design,
            stage,
            gate_a_passed=(stage != "design" and state["stages"]["design"]["status"] == "PASS"),
        )
        if state["attempts"][stage] >= 3:
            message = f"{stage} reached the three-attempt limit; return to Gate A architecture review"
            record_failure(context, design, stage, "AttemptLimit", message, 3)
            state = set_stage(
                context,
                state,
                stage,
                "BLOCKED",
                summary=message,
                issue="output/report/issue-report.csv",
            )
            raise WorkflowError(message)
        state = set_action(context, state, stage)
        append_flow(
            context,
            design["design_version"],
            stage,
            "execute",
            "START",
            f"target={target}",
        )
        try:
            with StageDispatch(context, design, stage):
                previous_design = design
                previous_state = state
                result = refresh_design(context) if stage == "design" else _execute_stage(context, design, stage)
                if stage == "design":
                    design = load_design(context.design_path)
                    if state["design_version"] != design["design_version"]:
                        invalidated = _design_invalidation_stage(previous_design, design)
                        state = rebase_state(
                            context,
                            previous_state,
                            design["design_version"],
                            invalidated,
                        )
                        rebase_report(context, design, invalidated)
            reporting.record(context, design, stage, result)
            state = set_stage(
                context, state, stage, "PASS", summary=result.get("status", "PASS"),
                report=(context.project_root / "output" / "report" / "current" / "report.json").relative_to(context.workflow_root).as_posix(),
            )
            append_flow(context, design["design_version"], stage, "execute", "PASS")
        except WorkflowError as error:
            state, attempt = note_attempt_failure(context, state, stage)
            status = "BLOCKED" if attempt >= 3 else getattr(error, "kind", "BLOCKED")
            record_failure(context, design, stage, error.__class__.__name__, str(error), attempt)
            state = set_stage(context, state, stage, status, summary=str(error), issue="output/report/issue-report.csv")
            append_flow(context, design["design_version"], stage, "execute", status)
            raise
        except Exception as error:
            state, attempt = note_attempt_failure(context, state, stage)
            record_failure(context, design, stage, error.__class__.__name__, str(error), attempt)
            status = "BLOCKED" if attempt >= 3 else "FAIL"
            state = set_stage(context, state, stage, status, summary=str(error), issue="output/report/issue-report.csv")
            append_flow(context, design["design_version"], stage, "execute", status)
            raise WorkflowError(str(error)) from error
    return state


def clean_project(context: ProjectContext) -> list[str]:
    removed: list[str] = []
    owned = [
        context.project_root / "input" / "next",
        context.project_root / "output" / "report" / ".staging",
        context.project_root / "work" / "tool",
    ]
    design = load_design(context.design_path)
    state = load_state(context, design_version=design["design_version"])
    issue_path = context.project_root / "output" / "report" / "issue-report.csv"
    no_open_issue = not issue_path.exists() or issue_path.read_text(
        encoding="utf-8", errors="replace"
    ) == ISSUE_HEADER
    if all(state["stages"][stage]["status"] == "PASS" for stage in STAGES) and no_open_issue:
        owned.append(context.project_root / "output" / "report" / "last-failure")
    for path in owned:
        if path.exists():
            remove_owned(path)
            removed.append(path.relative_to(context.workflow_root).as_posix())
    return removed


def clean_workflow(workflow_root: Path) -> list[str]:
    dispatch_root = workflow_root / "work" / "dispatch"
    if dispatch_root.exists() and any(dispatch_root.rglob("*.lease")):
        raise WorkflowError("Workflow root cleanup is blocked while resource leases exist")
    removed: list[str] = []
    for path in (
        workflow_root / ".omx",
        workflow_root / "log",
        workflow_root / "work",
        workflow_root / "xsim.dir",
        workflow_root / "xelab.log",
        workflow_root / "xelab.pb",
        workflow_root / "xvlog.log",
        workflow_root / "xvlog.pb",
    ):
        if path.exists():
            remove_owned(path)
            removed.append(path.relative_to(workflow_root).as_posix())
    for pattern in ("*.jou", "*.pb"):
        for path in workflow_root.glob(pattern):
            if path.is_file():
                remove_owned(path)
                removed.append(path.relative_to(workflow_root).as_posix())
    return removed


def recover_project(context: ProjectContext) -> dict[str, Any]:
    design = load_design(context.design_path)
    for path in context.project_root.rglob(".*.tmp"):
        path.unlink(missing_ok=True)
    state = recover_state(context, design["design_version"])
    report = load_report(context, design)
    evidence = {
        "design": report["review"].get("gate_a") == "PASS",
        "rtl": report["rtl_tb"].get("status") == "PASS",
        "verify": report["verification"].get("status") == "PASS",
        "synth": report["physical"]["synth"].get("status") == "PASS",
        "route": report["physical"]["route"].get("status") == "PASS",
        "release": report["release"].get("status") == "PASS",
    }
    rtl_root = context.project_root / "output" / "report" / "current" / "rtl-tb"
    if not evidence["rtl"] and (rtl_root / "xvlog.log").is_file() and (rtl_root / "xvlog-console.log").is_file():
        evidence["rtl"] = not reliable_rule_findings(
            context.project_root, design["implementation"]["rtl"]["sources"]
        )
    verify_log = context.project_root / "output" / "report" / "current" / "verification" / "xsim.log"
    if not evidence["verify"] and verify_log.is_file():
        required_cases = [
            item["id"] for item in design["verification"]["cases"] if item["stage"] == "verify"
        ]
        parse_xsim_log(verify_log, required_cases)
        evidence["verify"] = True
    for stage in STAGES:
        if not evidence[stage]:
            break
        if state["stages"][stage]["status"] != "PASS":
            state = set_stage(
                context,
                state,
                stage,
                "PASS",
                summary="recovered from retained evidence",
                report=(context.project_root / "output" / "report" / "current" / "report.json")
                .relative_to(context.workflow_root)
                .as_posix(),
            )
    reconcile_report(context, design, state)
    return state
