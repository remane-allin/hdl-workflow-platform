from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import GateError, ProjectContext, STAGES
from Workflow.tools.assets import resolve_reuse_assets
from Workflow.tools.design import load_design, required_case_ids, validate_design


def _ids(items: list[dict[str, Any]]) -> set[str]:
    return {item["id"] for item in items if isinstance(item.get("id"), str)}


def _required_fields(
    items: list[dict[str, Any]],
    fields: tuple[str, ...],
    label: str,
) -> list[str]:
    errors: list[str] = []
    for item in items:
        identifier = item.get("id", "<unknown>")
        for field in fields:
            value = item.get(field)
            if value is None or value == "" or value == []:
                errors.append(f"{label} {identifier} lacks {field}")
    return errors


def review_design(context: ProjectContext, path: Path | None = None) -> dict[str, Any]:
    design = load_design(path or context.design_path)
    errors = validate_design(design, context.project_root, context.project_id)
    resolved_assets: list[dict[str, Any]] = []
    try:
        resolved_assets = resolve_reuse_assets(context, design)
    except GateError as error:
        errors.append(str(error))
    requirements = design["requirements"]["items"]
    architectures = design["architecture"]["items"]
    interfaces = design["interfaces"]["items"]
    budgets = design["budgets"]["items"]
    cases = design["verification"]["cases"]
    req_ids = _ids(requirements)
    arch_req = {value for item in architectures for value in item.get("requirements", [])}
    case_req = {value for item in cases for value in item.get("requirements", [])}
    errors.extend(_required_fields(
        architectures,
        ("requirements", "blocks", "dataflow", "control", "storage", "reuse"),
        "architecture",
    ))
    errors.extend(_required_fields(
        interfaces,
        ("name", "endpoints", "direction", "width", "protocol", "clock", "reset", "ordering", "lifecycle"),
        "interface",
    ))
    errors.extend(f"architecture references unknown requirement: {item}" for item in sorted(arch_req - req_ids))
    errors.extend(f"verification references unknown requirement: {item}" for item in sorted(case_req - req_ids))
    errors.extend(f"requirement lacks architecture coverage: {item}" for item in sorted(req_ids - arch_req))
    errors.extend(f"requirement lacks verification coverage: {item}" for item in sorted(req_ids - case_req))
    interface_ids = _ids(interfaces)
    case_if = {value for item in cases for value in item.get("interfaces", [])}
    errors.extend(f"verification references unknown interface: {item}" for item in sorted(case_if - interface_ids))
    errors.extend(f"interface lacks verification coverage: {item}" for item in sorted(interface_ids - case_if))
    budget_req = {value for item in budgets for value in item.get("requirements", [])}
    errors.extend(f"budget references unknown requirement: {item}" for item in sorted(budget_req - req_ids))
    for budget in budgets:
        identifier = budget.get("id", "<unknown>")
        if budget.get("evidence_stage") not in STAGES:
            errors.append(f"budget {identifier} has invalid evidence_stage")
        if not isinstance(budget.get("planned"), (int, float)):
            errors.append(f"budget {identifier} lacks numeric planned estimate")
        if budget.get("estimate_tolerance_percent") != 10:
            errors.append(f"budget {identifier} estimate tolerance must be 10 percent")
        if not any(key in budget for key in ("maximum", "minimum", "exclusive_minimum", "equals")):
            errors.append(f"budget {identifier} lacks an acceptance condition")
    for case in cases:
        identifier = case.get("id", "<unknown>")
        if case.get("stage") not in STAGES:
            errors.append(f"verification {identifier} has invalid stage")
        for field in ("stimulus", "oracle", "expected"):
            if not case.get(field):
                errors.append(f"verification {identifier} lacks {field}")
        if case.get("stage") == "verify" and not case.get("key_waves"):
            errors.append(f"verification {identifier} lacks key_waves")
    if errors:
        raise GateError("Gate A failed: " + "; ".join(errors))
    return {
        "gate": "A",
        "status": "PASS",
        "checks": [
            "requirements-architecture",
            "architecture-interfaces-dataflow",
            "interfaces-implementation-sources",
            "verification-requirements-interfaces",
            "budgets-evidence-stage",
            "design-version-evidence-binding",
        ],
        "required_cases": required_case_ids(design),
        "resolved_assets": resolved_assets,
    }


def review_gate_b(context: ProjectContext, report: dict[str, Any]) -> dict[str, Any]:
    design = load_design(context.design_path)
    required = set(required_case_ids(design))
    completed = {case.get("case") for case in report.get("verification", {}).get("cases", []) if case.get("result") == "PASS"}
    missing = required - completed
    if missing:
        raise GateError("Gate B missing required verification cases: " + ", ".join(sorted(missing)))
    if report.get("rtl_tb", {}).get("status") != "PASS" or report.get("verification", {}).get("status") != "PASS":
        raise GateError("Gate B requires RTL/TB and verification PASS")
    return {"gate": "B", "status": "PASS", "required_cases": sorted(required)}


def prerequisites(state: dict[str, Any], stage: str) -> None:
    index = STAGES.index(stage)
    missing = [name for name in STAGES[:index] if state["stages"][name]["status"] != "PASS"]
    if missing:
        raise GateError(f"{stage} prerequisites are not PASS: {', '.join(missing)}")
