from __future__ import annotations

import json
import re
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from Workflow.core.contracts import STAGES, ContractError, ProjectContext
from Workflow.tools.filesystem import atomic_write_json, atomic_write_text, replace_directory


ISSUE_HEADER = (
    "issue_id,design_version,stage,category,symptom,root_cause,impact,"
    "attempt_count,decision,status,evidence_ref,return_gate\n"
)


def initial_report(context: ProjectContext, design: dict[str, Any]) -> dict[str, Any]:
    return {
        "context": {
            "project_id": context.project_id,
            "design_version": design["design_version"],
            "active_sources": design["implementation"]["rtl"]["sources"],
            "tools": design["project"].get("tool_profile", "xilinx-2024.2"),
        },
        "rtl_tb": {"status": "NOT_RUN"},
        "verification": {"status": "NOT_RUN", "cases": []},
        "physical": {"synth": {"status": "NOT_RUN"}, "route": {"status": "NOT_RUN"}},
        "review": {"gate_a": "NOT_RUN", "gate_b": "NOT_RUN", "extraction_quality": 1.0},
        "release": {"status": "NOT_RUN", "gui_review": "PENDING_USER_GUI_REVIEW"},
    }


def report_path(context: ProjectContext) -> Path:
    return context.project_root / "output" / "report" / "current" / "report.json"


def load_report(context: ProjectContext, design: dict[str, Any]) -> dict[str, Any]:
    path = report_path(context)
    if path.exists():
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream)
        if value.get("context", {}).get("design_version") == design["design_version"]:
            return value
    return initial_report(context, design)


def rebase_report(
    context: ProjectContext,
    design: dict[str, Any],
    first_invalidated_stage: str,
) -> dict[str, Any]:
    """Bind the current report to a new design while retaining valid evidence."""
    if first_invalidated_stage not in STAGES:
        raise ContractError("invalid report invalidation stage")
    path = report_path(context)
    previous = None
    if path.exists():
        with path.open("r", encoding="utf-8") as stream:
            previous = json.load(stream)
    updated = initial_report(context, design)
    if isinstance(previous, dict):
        boundary = STAGES.index(first_invalidated_stage)
        if boundary > STAGES.index("rtl"):
            updated["rtl_tb"] = deepcopy(previous.get("rtl_tb", updated["rtl_tb"]))
        if boundary > STAGES.index("verify"):
            updated["verification"] = deepcopy(previous.get("verification", updated["verification"]))
            updated["review"]["gate_b"] = previous.get("review", {}).get("gate_b", "NOT_RUN")
        if boundary > STAGES.index("synth"):
            updated["physical"]["synth"] = deepcopy(
                previous.get("physical", {}).get("synth", updated["physical"]["synth"])
            )
        if boundary > STAGES.index("route"):
            updated["physical"]["route"] = deepcopy(
                previous.get("physical", {}).get("route", updated["physical"]["route"])
            )
        if boundary > STAGES.index("release"):
            updated["release"] = deepcopy(previous.get("release", updated["release"]))
    atomic_write_json(path, updated)
    atomic_write_text(
        context.project_root / "output" / "report" / "current" / "flow.log",
        f"design_version={design['design_version']}|event=DESIGN_REBASE|first_invalidated_stage={first_invalidated_stage}\n",
    )
    return updated


def append_flow(
    context: ProjectContext,
    design_version: int,
    stage: str,
    action: str,
    status: str,
    parameters: str = "",
) -> None:
    path = context.project_root / "output" / "report" / "current" / "flow.log"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = (
        f"time={stamp}|design_version={design_version}|stage={stage}|"
        f"action={action}|parameters={parameters}|status={status}\n"
    )
    atomic_write_text(path, existing + line)


def reconcile_report(
    context: ProjectContext,
    design: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    """Reconcile a report only from retained raw evidence and recorded PASS stages."""
    report = load_report(context, design)
    changed = False
    if state["stages"]["design"]["status"] == "PASS" and report["review"]["gate_a"] != "PASS":
        report["review"]["gate_a"] = "PASS"
        changed = True

    if state["stages"]["rtl"]["status"] == "PASS" and report["rtl_tb"].get("status") != "PASS":
        from Workflow.tools.rtl import reliable_rule_findings

        root = context.project_root / "output" / "report" / "current" / "rtl-tb"
        required = (root / "xvlog.log", root / "xvlog-console.log")
        if not all(path.is_file() for path in required):
            raise ContractError("cannot reconcile RTL PASS without retained raw reports")
        sources = design["implementation"]["rtl"]["sources"]
        findings = reliable_rule_findings(context.project_root, sources)
        if findings:
            raise ContractError("cannot reconcile RTL PASS after reliable-rule findings")
        report["rtl_tb"] = {
            "status": "PASS",
            "source_count": len(sources),
            "rule_findings": [],
            "raw_reports": ["rtl-tb/xvlog.log", "rtl-tb/xvlog-console.log"],
        }
        changed = True

    if state["stages"]["verify"]["status"] == "PASS" and report["verification"].get("status") != "PASS":
        path = context.project_root / "output" / "report" / "current" / "verification" / "xsim.log"
        if not path.is_file():
            raise ContractError("cannot reconcile verification PASS without retained xsim.log")
        required_cases = [
            item["id"] for item in design["verification"]["cases"] if item["stage"] == "verify"
        ]
        verification = parse_xsim_log(path, required_cases)
        verification["raw_reports"] = [
            "verification/xvlog.log",
            "verification/xelab.log",
            "verification/xsim.log",
        ]
        verification["gate_b"] = "PASS"
        report["verification"] = verification
        report["review"]["gate_b"] = "PASS"
        changed = True

    report_status = {
        "synth": report["physical"]["synth"].get("status"),
        "route": report["physical"]["route"].get("status"),
        "release": report["release"].get("status"),
    }
    for stage, status in report_status.items():
        if state["stages"][stage]["status"] == "PASS" and status != "PASS":
            raise ContractError(f"cannot reconcile {stage} PASS without a matching extracted report")

    if changed:
        atomic_write_json(report_path(context), report)
    flow = context.project_root / "output" / "report" / "current" / "flow.log"
    if not flow.exists():
        for stage in STAGES:
            status = state["stages"][stage]["status"]
            if status != "NOT_RUN":
                append_flow(context, design["design_version"], stage, "reconcile", status)
    return report


def ensure_issue_table(context: ProjectContext) -> None:
    path = context.project_root / "output" / "report" / "issue-report.csv"
    if not path.exists():
        atomic_write_text(path, ISSUE_HEADER)


def merge_stage_report(
    context: ProjectContext,
    design: dict[str, Any],
    stage: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    current_root = context.project_root / "output" / "report" / "current"
    staging = context.project_root / "output" / "report" / ".staging" / stage
    current_root.mkdir(parents=True, exist_ok=True)
    report = load_report(context, design)
    if stage == "design":
        report["review"]["gate_a"] = result["status"]
    elif stage == "rtl":
        report["rtl_tb"] = result
    elif stage == "verify":
        report["verification"] = result
        report["review"]["gate_b"] = result.get("gate_b", "NOT_RUN")
    elif stage in {"synth", "route"}:
        report["physical"][stage] = result
    elif stage == "release":
        report["release"].update(result)
    if staging.exists():
        for category in list(staging.iterdir()):
            target = current_root / category.name
            if category.name == "physical":
                if not any(category.iterdir()):
                    shutil.rmtree(category)
                    continue
                combined = staging / ".physical-combined"
                if target.exists():
                    shutil.copytree(target, combined)
                else:
                    combined.mkdir(parents=True)
                shutil.copytree(category, combined, dirs_exist_ok=True)
                shutil.rmtree(category)
                replace_directory(combined, target)
            else:
                replace_directory(category, target)
        shutil.rmtree(staging)
    atomic_write_json(report_path(context), report)
    atomic_write_text(context.project_root / "output" / "report" / "issue-report.csv", ISSUE_HEADER)
    return report


def record_failure(
    context: ProjectContext,
    design: dict[str, Any],
    stage: str,
    category: str,
    message: str,
    attempt_count: int,
) -> None:
    report_root = context.project_root / "output" / "report"
    staging = report_root / ".staging" / stage
    failure = report_root / "last-failure"
    failure_staging = report_root / ".failure-staging"
    if failure_staging.exists():
        shutil.rmtree(failure_staging)
    failure_staging.mkdir(parents=True)
    if staging.exists():
        shutil.move(str(staging), str(failure_staging / stage))
    replace_directory(failure_staging, failure)
    evidence = (failure / stage).relative_to(context.workflow_root).as_posix() if (failure / stage).exists() else ""
    row = [
        "ISSUE-CURRENT", str(design["design_version"]), stage, category, message,
        message, "stage did not PASS", str(attempt_count), "return to responsible owner",
        "OPEN", evidence, "Gate A" if stage == "design" else stage,
    ]
    path = report_root / "issue-report.csv"
    with_path = ISSUE_HEADER + ",".join('"' + item.replace('"', '""') + '"' for item in row) + "\n"
    atomic_write_text(path, with_path)


WF_INFO = re.compile(
    r"^WF_INFO\|case=(?P<case>[^|]+)\|purpose=(?P<purpose>[^|]*)\|input=(?P<input>[^|]*)"
    r"\|expected=(?P<expected>[^|]*)\|actual=(?P<actual>[^|]*)\|result=(?P<result>PASS|FAIL)$"
)
WF_SUMMARY = re.compile(r"^WF_SUMMARY\|total=(\d+)\|pass=(\d+)\|fail=(\d+)$")


def parse_xsim_log(path: Path, required_cases: list[str]) -> dict[str, Any]:
    cases: list[dict[str, str]] = []
    summaries: list[tuple[int, int, int]] = []
    errors: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        info = WF_INFO.match(line)
        if info:
            cases.append(info.groupdict())
        summary = WF_SUMMARY.match(line)
        if summary:
            summaries.append(tuple(int(item) for item in summary.groups()))
        if line.startswith("WF_ERROR|"):
            errors.append(line)
    if len(summaries) != 1:
        raise ValueError("XSim output must contain exactly one WF_SUMMARY")
    total, passed, failed = summaries[0]
    observed = {case["case"] for case in cases if case["result"] == "PASS"}
    missing = sorted(set(required_cases) - observed)
    if errors or failed or total != passed or missing:
        raise ValueError(
            f"XSim verification failed: errors={len(errors)} failed={failed} missing={missing}"
        )
    if total != len(cases):
        raise ValueError("WF_SUMMARY count does not match WF_INFO count")
    return {"status": "PASS", "cases": cases, "summary": {"total": total, "pass": passed, "fail": failed}}
