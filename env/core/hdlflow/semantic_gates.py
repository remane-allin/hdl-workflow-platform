"""Semantic gate layer for requirement, design, verification, and release closure."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .project import require_project_instance
from .release_state import evaluate_release_state
from .requirements_compiler import (
    ACTIVE_ACCEPTANCE_REL,
    ACTIVE_REQUIREMENTS_REL,
    EVIDENCE_INDEX_REL,
    REQUIREMENT_LIFECYCLE_REL,
    compile_requirements,
    load_active_acceptance,
    load_active_requirements,
    load_evidence_index,
)
from .simple_yaml import load_yaml


SEMANTIC_GATE_STATUS_REL = "work/gates/semantic_gate_status.json"
SEMANTIC_GATE_POLICY_REL = "work/config/semantic_gate_policy.yaml"

GATE_NAMES = [
    "requirements_consistency_gate",
    "architecture_impact_gate",
    "design_routing_gate",
    "microarchitecture_completeness_gate",
    "rtl_obligation_gate",
    "tb_blackbox_obligation_gate",
    "waveform_semantic_gate",
    "uvm_obligation_gate",
    "fpga_validation_obligation_gate",
    "release_truth_gate",
]


@dataclass(frozen=True)
class SemanticIssue:
    gate: str
    severity: str
    message: str
    evidence: str = ""


@dataclass(frozen=True)
class SemanticGateResult:
    name: str
    mode: str
    status: str
    issues: list[SemanticIssue]


@dataclass(frozen=True)
class SemanticGateRun:
    project: Path
    level: str
    ok: bool
    status_path: Path
    gates: list[SemanticGateResult]


def run_semantic_gates(
    project_path: Path,
    *,
    level: str = "develop",
    gate_names: list[str] | None = None,
    compile_active: bool = False,
    write_status: bool = True,
) -> SemanticGateRun:
    project = require_project_instance(project_path)
    if compile_active:
        compile_requirements(project)
    policy = _load_policy(project)
    selected = gate_names or GATE_NAMES
    results: list[SemanticGateResult] = []
    for name in selected:
        checker = CHECKERS.get(name)
        if checker is None:
            results.append(SemanticGateResult(name=name, mode="off", status="SKIP", issues=[]))
            continue
        mode = _gate_mode(policy, name, level)
        if mode == "off":
            results.append(SemanticGateResult(name=name, mode=mode, status="SKIP", issues=[]))
            continue
        issues = checker(project, level)
        status = _status_for(mode, issues, level)
        results.append(SemanticGateResult(name=name, mode=mode, status=status, issues=issues))

    ok = all(result.status != "FAIL" for result in results)
    status_path = project / SEMANTIC_GATE_STATUS_REL
    if write_status:
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text(
            json.dumps(_payload(project, level, results), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return SemanticGateRun(project=project, level=level, ok=ok, status_path=status_path, gates=results)


def gate_check_summaries(project_path: Path, *, level: str = "develop", gate_names: list[str] | None = None) -> list[dict[str, str]]:
    """Return strict gate summaries for the executable gate layer."""

    run = run_semantic_gates(project_path, level=level, gate_names=gate_names, compile_active=False, write_status=True)
    summaries: list[dict[str, str]] = []
    for result in run.gates:
        if result.status == "SKIP":
            summaries.append({"name": result.name, "status": "PASS", "detail": "semantic gate disabled"})
        elif result.status == "FAIL":
            summaries.append({"name": result.name, "status": "FAIL", "detail": _detail(result)})
        else:
            summaries.append({"name": result.name, "status": "PASS", "detail": _detail(result)})
    return summaries


def _payload(project: Path, level: str, results: list[SemanticGateResult]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "project": project.name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "level": level,
        "result": "PASS" if all(result.status != "FAIL" for result in results) else "FAIL",
        "gates": [
            {
                "name": result.name,
                "mode": result.mode,
                "status": result.status,
                "issue_count": len(result.issues),
                "issues": [
                    {
                        "severity": issue.severity,
                        "message": issue.message,
                        "evidence": issue.evidence,
                    }
                    for issue in result.issues
                ],
            }
            for result in results
        ],
    }


def _load_policy(project: Path) -> dict[str, Any]:
    path = project / SEMANTIC_GATE_POLICY_REL
    if not path.exists():
        return {"default_mode": "advisory", "release_default_mode": "blocking", "gates": {}}
    try:
        data = load_yaml(path)
    except Exception:
        return {"default_mode": "advisory", "release_default_mode": "blocking", "gates": {}}
    return data if isinstance(data, dict) else {}


def _gate_mode(policy: dict[str, Any], gate_name: str, level: str) -> str:
    gates = policy.get("gates", {}) if isinstance(policy, dict) else {}
    raw = gates.get(gate_name) if isinstance(gates, dict) else None
    if isinstance(raw, dict):
        if level == "release":
            raw = raw.get("release_mode") or policy.get("release_default_mode") or raw.get("mode")
        else:
            raw = raw.get("mode")
    elif level == "release":
        raw = policy.get("release_default_mode") or raw
    mode = str(raw or policy.get("default_mode") or "advisory").lower()
    return mode if mode in {"off", "advisory", "blocking"} else "advisory"


def _status_for(mode: str, issues: list[SemanticIssue], level: str) -> str:
    if not issues:
        return "PASS"
    return "FAIL"


def _detail(result: SemanticGateResult) -> str:
    if not result.issues:
        return f"{result.mode}: no semantic issue"
    first = result.issues[0].message
    return f"{result.mode}: {len(result.issues)} issue(s); first: {first}"


def _requirements_consistency_gate(project: Path, level: str) -> list[SemanticIssue]:
    issues: list[SemanticIssue] = []
    requirements = load_active_requirements(project)
    acceptance = load_active_acceptance(project)
    evidence = load_evidence_index(project)
    lifecycle = _items(project / REQUIREMENT_LIFECYCLE_REL, "requirements")
    req_ids = _ids(requirements, "requirement_id")
    if not (project / ACTIVE_REQUIREMENTS_REL).exists():
        issues.append(_issue("requirements_consistency_gate", "error", "missing active_requirements.yaml", ACTIVE_REQUIREMENTS_REL))
    if not requirements:
        issues.append(_issue("requirements_consistency_gate", "error", "active requirement baseline is empty", ACTIVE_REQUIREMENTS_REL))
        return issues

    evidence_ids = _ids(evidence, "requirement_id")
    acceptance_ids = _ids(acceptance, "requirement_id")
    lifecycle_ids = _ids(lifecycle, "requirement_id")
    for missing in sorted(req_ids - evidence_ids):
        issues.append(_issue("requirements_consistency_gate", "error", f"{missing} has no evidence index row", EVIDENCE_INDEX_REL))
    for missing in sorted(req_ids - acceptance_ids):
        issues.append(_issue("requirements_consistency_gate", "error", f"{missing} has no active acceptance criterion", ACTIVE_ACCEPTANCE_REL))
    for missing in sorted(req_ids - lifecycle_ids):
        issues.append(_issue("requirements_consistency_gate", "error", f"{missing} has no lifecycle state", REQUIREMENT_LIFECYCLE_REL))

    for row in evidence:
        for key in ("source_path", "parsed_path"):
            rel = str(row.get(key) or "")
            if rel and not rel.startswith(("http://", "https://")) and not (project / rel).exists():
                issues.append(_issue("requirements_consistency_gate", "error", f"{row.get('requirement_id')} {key} does not exist: {rel}", EVIDENCE_INDEX_REL))

    traced = _trace_requirement_ids(project)
    if traced:
        for missing in sorted(req_ids - traced):
            issues.append(_issue("requirements_consistency_gate", "error", f"{missing} is missing from generated trace links", "work/docparse/trace_matrix"))
        for stale in sorted(traced - req_ids):
            issues.append(_issue("requirements_consistency_gate", "error", f"trace link references stale requirement {stale}", "work/docparse/trace_matrix"))
    return issues


def _architecture_impact_gate(project: Path, level: str) -> list[SemanticIssue]:
    issues: list[SemanticIssue] = []
    change_root = project / "work/change/requests"
    if not change_root.exists():
        return issues
    for req in sorted(change_root.glob("CR-*.md")) + sorted(change_root.glob("CR-*.yaml")):
        change_id = req.stem
        change_dir = project / "work/docparse/change" / change_id
        impact = change_dir / "architecture_impact_review.yaml"
        design_plan = change_dir / "design_replanning_record.md"
        verification_plan = change_dir / "verification_replanning_record.md"
        if not impact.exists():
            issues.append(_issue("architecture_impact_gate", "error", f"{change_id} missing architecture impact review", f"work/docparse/change/{change_id}/architecture_impact_review.yaml"))
        else:
            issues.extend(_architecture_impact_content_issues(project, impact, change_id))
        if not design_plan.exists():
            issues.append(_issue("architecture_impact_gate", "error", f"{change_id} missing design replanning record", f"work/docparse/change/{change_id}/design_replanning_record.md"))
        else:
            issues.extend(_replanning_record_issues(project, design_plan, change_id, "design", ("module", "interface", "state", "reset", "cdc", "timing")))
        if not verification_plan.exists():
            issues.append(_issue("architecture_impact_gate", "error", f"{change_id} missing verification replanning record", f"work/docparse/change/{change_id}/verification_replanning_record.md"))
        else:
            issues.extend(_replanning_record_issues(project, verification_plan, change_id, "verification", ("tb", "vcd", "uvm", "fpga", "coverage", "claim")))
    return issues


def _design_routing_gate(project: Path, level: str) -> list[SemanticIssue]:
    issues: list[SemanticIssue] = []
    requirements = load_active_requirements(project)
    req_ids = _ids(requirements, "requirement_id")
    routing = _items(project / "work/docparse/architecture/design_routing.yaml", "routes")
    ownership = _items(project / "work/docparse/architecture/module_ownership_matrix.yaml", "owners")
    domains = _items(project / "work/docparse/architecture/functional_domain_model.yaml", "domains")
    route_ids = _ids(routing, "requirement_id")
    owner_ids = _ids(ownership, "requirement_id")
    if requirements and not domains:
        issues.append(_issue("design_routing_gate", "error", "missing functional domain model", "work/docparse/architecture/functional_domain_model.yaml"))
    if requirements and not routing:
        issues.append(_issue("design_routing_gate", "error", "missing design_routing routes", "work/docparse/architecture/design_routing.yaml"))
    for missing in sorted(req_ids - route_ids):
        issues.append(_issue("design_routing_gate", "error", f"{missing} has no design routing", "work/docparse/architecture/design_routing.yaml"))
    for row in routing:
        req_id = row.get("requirement_id")
        for key in ("design_doc_sections", "affected_modules", "affected_interfaces", "verification_hooks"):
            if not _as_list(row.get(key)):
                issues.append(_issue("design_routing_gate", "error", f"{req_id} routing missing {key}", "work/docparse/architecture/design_routing.yaml"))
    for missing in sorted(req_ids - owner_ids):
        issues.append(_issue("design_routing_gate", "error", f"{missing} has no module owner", "work/docparse/architecture/module_ownership_matrix.yaml"))
    for row in ownership:
        req_id = row.get("requirement_id")
        for key in ("functional_domain", "design_doc_sections", "rtl_owner_module", "interface_owner", "verification_owner"):
            if not _as_list(row.get(key)):
                issues.append(_issue("design_routing_gate", "error", f"{req_id} ownership missing {key}", "work/docparse/architecture/module_ownership_matrix.yaml"))
    return issues


def _microarchitecture_completeness_gate(project: Path, level: str) -> list[SemanticIssue]:
    issues: list[SemanticIssue] = []
    doc_root = project / "output/docs"
    for path in sorted(doc_root.rglob("*.md")) if doc_root.exists() else []:
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = _rel(project, path)
        if level == "release" and re.search(r"(?mi)\bDRAFT\b", text):
            issues.append(_issue("microarchitecture_completeness_gate", "error", f"release document is still DRAFT: {rel}", rel))
        if level == "release" and re.search(r"(?mi)\bnot specified\b", text):
            issues.append(_issue("microarchitecture_completeness_gate", "error", f"release document contains not specified: {rel}", rel))
    for rel in ("work/docparse/architecture/state_machines.yaml", "work/docparse/architecture/timing_model.yaml"):
        path = project / rel
        if path.exists() and re.search(r"(?mi)\bnot specified\b", path.read_text(encoding="utf-8", errors="ignore")):
            issues.append(_issue("microarchitecture_completeness_gate", "error", f"{rel} contains not specified", rel))
    return issues


def _rtl_obligation_gate(project: Path, level: str) -> list[SemanticIssue]:
    issues: list[SemanticIssue] = []
    requirements = load_active_requirements(project)
    req_ids = _ids(requirements, "requirement_id")
    impl = _items(project / "work/loop1_rtl_tb/trace_matrix/req_to_rtl_implementation.yaml", "implementations")
    impl_ids = _ids(impl, "requirement_id")
    for missing in sorted(req_ids - impl_ids):
        issues.append(_issue("rtl_obligation_gate", "error", f"{missing} has no RTL implementation entry", "work/loop1_rtl_tb/trace_matrix/req_to_rtl_implementation.yaml"))
    for row in impl:
        status = str(row.get("implementation_status") or row.get("status") or "").lower()
        req_id = row.get("requirement_id")
        if level == "release" and status in {"", "planned", "todo", "unknown", "partial", "missing", "deferred"}:
            issues.append(_issue("rtl_obligation_gate", "error", f"{req_id} RTL implementation status is {status}", "work/loop1_rtl_tb/trace_matrix/req_to_rtl_implementation.yaml"))
        for key in ("rtl_file", "module", "implementation_points"):
            if not _as_list(row.get(key)):
                issues.append(_issue("rtl_obligation_gate", "error", f"{req_id} RTL implementation missing {key}", "work/loop1_rtl_tb/trace_matrix/req_to_rtl_implementation.yaml"))
    return issues


def _tb_blackbox_obligation_gate(project: Path, level: str) -> list[SemanticIssue]:
    issues: list[SemanticIssue] = []
    operation_ids = _operation_ids(project)
    if _active_requirement_ids(project) and not operation_ids:
        issues.append(_issue("tb_blackbox_obligation_gate", "error", "active requirements have no operation_model entries", "work/docparse/verification/operation_model.yaml"))
    interface_names = _interface_names(project)
    if (operation_ids or _active_requirement_ids(project)) and not interface_names:
        issues.append(_issue("tb_blackbox_obligation_gate", "error", "missing interface contract", "work/loop1_rtl_tb/config/interface_contract.yaml"))
    obligations = _items(project / "work/loop1_rtl_tb/config/tb_obligations.yaml", "obligations")
    obligation_ops = _ids(obligations, "operation_id")
    if operation_ids and not obligations:
        issues.append(_issue("tb_blackbox_obligation_gate", "error", "operation model exists but tb_obligations.yaml has no obligations", "work/loop1_rtl_tb/config/tb_obligations.yaml"))
    for missing in sorted(operation_ids - obligation_ops):
        issues.append(_issue("tb_blackbox_obligation_gate", "error", f"operation {missing} has no TB obligation", "work/loop1_rtl_tb/config/tb_obligations.yaml"))
    for row in obligations:
        test_id = row.get("test_id") or row.get("operation_id") or row.get("requirement_id")
        evidence_type = str(row.get("evidence_type") or row.get("allowed_whitebox_debug") or "").lower()
        status = str(row.get("status") or "").lower()
        if level == "release" and status in {"", "planned", "todo", "unknown", "missing"}:
            issues.append(_issue("tb_blackbox_obligation_gate", "error", f"{test_id} TB obligation status is {status or 'missing'}", "work/loop1_rtl_tb/config/tb_obligations.yaml"))
        if status in {"pass", "passed", "verified"} and evidence_type in {"whitebox", "whitebox_only"}:
            issues.append(_issue("tb_blackbox_obligation_gate", "error", f"{test_id} uses whitebox-only PASS evidence", "work/loop1_rtl_tb/config/tb_obligations.yaml"))
        if status in {"pass", "passed", "verified"} and not row.get("required_blackbox_check") and evidence_type != "blackbox":
            issues.append(_issue("tb_blackbox_obligation_gate", "error", f"{test_id} PASS lacks required black-box check declaration", "work/loop1_rtl_tb/config/tb_obligations.yaml"))
        observed = str(row.get("observed_interface") or "")
        if status in {"pass", "passed", "verified"} and not observed and not row.get("expected_top_interface_response"):
            issues.append(_issue("tb_blackbox_obligation_gate", "error", f"{test_id} PASS lacks observed top interface", "work/loop1_rtl_tb/config/tb_obligations.yaml"))
        if observed and interface_names and observed not in interface_names:
            issues.append(_issue("tb_blackbox_obligation_gate", "error", f"{test_id} observes interface not in interface_contract: {observed}", "work/loop1_rtl_tb/config/interface_contract.yaml"))
    report = _read_json(project / "output/reports/loop1/loop1_report.json")
    if level == "release" and operation_ids and not report:
        issues.append(_issue("tb_blackbox_obligation_gate", "error", "missing Loop1 report for TB obligation closure", "output/reports/loop1/loop1_report.json"))
    if report:
        issues.extend(_loop1_report_semantic_issues(project, report, operation_ids, interface_names))
    return issues


def _waveform_semantic_gate(project: Path, level: str) -> list[SemanticIssue]:
    issues: list[SemanticIssue] = []
    operation_ids = _operation_ids(project)
    manifest = _items(project / "work/loop1_rtl_tb/config/wave_semantic_manifest.yaml", "windows")
    if (operation_ids or _active_requirement_ids(project)) and not manifest:
        issues.append(_issue("waveform_semantic_gate", "error", "operation model exists but wave_semantic_manifest.yaml has no windows", "work/loop1_rtl_tb/config/wave_semantic_manifest.yaml"))
    verification_windows = [row for row in manifest if str(row.get("evidence_level") or "").lower() == "verification"]
    if manifest and not verification_windows:
        issues.append(_issue("waveform_semantic_gate", "error", "wave semantic manifest has no verification-level window", "work/loop1_rtl_tb/config/wave_semantic_manifest.yaml"))
    for row in verification_windows:
        window_id = row.get("window_id")
        if not row.get("decoder") or not _as_list(row.get("expected_events")):
            issues.append(_issue("waveform_semantic_gate", "error", f"{window_id} missing decoder or expected events", "work/loop1_rtl_tb/config/wave_semantic_manifest.yaml"))
    report = project / "output/reports/loop1/waveform_semantic_report.json"
    if level == "release" and verification_windows and not report.exists():
        issues.append(_issue("waveform_semantic_gate", "error", "missing waveform semantic report for verification windows", "output/reports/loop1/waveform_semantic_report.json"))
    payload = _read_json(report)
    if payload:
        if str(payload.get("result") or "").upper() != "PASS":
            issues.append(_issue("waveform_semantic_gate", "error", "waveform semantic report result is not PASS", "output/reports/loop1/waveform_semantic_report.json"))
        for row in payload.get("windows", []) if isinstance(payload.get("windows"), list) else []:
            if isinstance(row, dict) and str(row.get("status") or "").upper() != "PASS":
                issues.append(_issue("waveform_semantic_gate", "error", f"{row.get('window_id')} waveform semantic window failed", "output/reports/loop1/waveform_semantic_report.json"))
        for event in payload.get("decoded_transactions", []) if isinstance(payload.get("decoded_transactions"), list) else []:
            if isinstance(event, dict) and str(event.get("status") or "").upper() in {"FAIL", "UNSUPPORTED", "UNKNOWN"}:
                issues.append(_issue("waveform_semantic_gate", "error", f"{event.get('event_id')} waveform semantic transaction status is {event.get('status')}", "output/reports/loop1/waveform_semantic_report.json"))
    return issues


def _uvm_obligation_gate(project: Path, level: str) -> list[SemanticIssue]:
    issues: list[SemanticIssue] = []
    operation_ids = _operation_ids(project)
    if _active_requirement_ids(project) and not operation_ids:
        issues.append(_issue("uvm_obligation_gate", "error", "active requirements have no operation_model entries", "work/docparse/verification/operation_model.yaml"))
    obligations = _items(project / "work/loop2_uvm/config/uvm_obligations.yaml", "obligations")
    obligation_ops = _ids(obligations, "operation_id")
    if operation_ids and not obligations:
        issues.append(_issue("uvm_obligation_gate", "error", "operation model exists but uvm_obligations.yaml has no obligations", "work/loop2_uvm/config/uvm_obligations.yaml"))
    for missing in sorted(operation_ids - obligation_ops):
        issues.append(_issue("uvm_obligation_gate", "error", f"operation {missing} has no UVM obligation", "work/loop2_uvm/config/uvm_obligations.yaml"))
    for row in obligations:
        item = row.get("sequence_id") or row.get("operation_id") or row.get("requirement_id")
        status = str(row.get("status") or "").lower()
        if level == "release" and status in {"", "planned", "todo", "unknown", "missing"}:
            issues.append(_issue("uvm_obligation_gate", "error", f"{item} UVM obligation status is {status or 'missing'}", "work/loop2_uvm/config/uvm_obligations.yaml"))
        if not _as_list(row.get("coverage_bins")):
            issues.append(_issue("uvm_obligation_gate", "error", f"{item} missing coverage bins", "work/loop2_uvm/config/uvm_obligations.yaml"))
        scoreboard = str(row.get("scoreboard_model") or "").lower()
        if scoreboard in {"", "scenario_code", "scenario-only", "none"}:
            issues.append(_issue("uvm_obligation_gate", "error", f"{item} has no reference-model scoreboard", "work/loop2_uvm/config/uvm_obligations.yaml"))
        for key in ("cross_coverage", "assertions"):
            if not _as_list(row.get(key)):
                issues.append(_issue("uvm_obligation_gate", "error", f"{item} missing {key}", "work/loop2_uvm/config/uvm_obligations.yaml"))
        if not any(_as_list(row.get(key)) for key in ("negative_tests", "randomized_tests", "long_sequence_tests")):
            issues.append(_issue("uvm_obligation_gate", "error", f"{item} lacks randomized/long/negative scenario obligation", "work/loop2_uvm/config/uvm_obligations.yaml"))
    for path in sorted((project / "output/uvm").rglob("*.sv*")) if (project / "output/uvm").exists() else []:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"coverage\s*=\s*100(?:\.0)?", text):
            issues.append(_issue("uvm_obligation_gate", "error", f"hard-coded coverage=100 found in {_rel(project, path)}", _rel(project, path)))
    report = _read_json(project / "output/reports/loop2/loop2_report.json")
    if level == "release" and operation_ids and not report:
        issues.append(_issue("uvm_obligation_gate", "error", "missing Loop2 report for UVM obligation closure", "output/reports/loop2/loop2_report.json"))
    if report:
        issues.extend(_loop2_report_semantic_issues(project, report, operation_ids))
    return issues


def _fpga_validation_obligation_gate(project: Path, level: str) -> list[SemanticIssue]:
    issues: list[SemanticIssue] = []
    rows = _items(project / "work/loop3_fpga_proto/config/fpga_validation_matrix.yaml", "tests")
    if _active_requirement_ids(project) and not rows:
        issues.append(_issue("fpga_validation_obligation_gate", "error", "active requirements have no FPGA validation matrix", "work/loop3_fpga_proto/config/fpga_validation_matrix.yaml"))
    for row in rows:
        test_id = row.get("test_id") or row.get("requirement_id")
        status = str(row.get("status") or "").lower()
        if level == "release" and status in {"", "planned", "todo", "unknown", "missing"}:
            issues.append(_issue("fpga_validation_obligation_gate", "error", f"{test_id} FPGA validation status is {status or 'missing'}", "work/loop3_fpga_proto/config/fpga_validation_matrix.yaml"))
        if status in {"hardcoded_pass", "forced_pass"}:
            issues.append(_issue("fpga_validation_obligation_gate", "error", f"{test_id} uses hard-coded PASS", "work/loop3_fpga_proto/config/fpga_validation_matrix.yaml"))
        if status in {"pass", "passed", "verified"}:
            for key in ("expected", "actual", "comparison"):
                if not row.get(key):
                    issues.append(_issue("fpga_validation_obligation_gate", "error", f"{test_id} PASS missing {key}", "work/loop3_fpga_proto/config/fpga_validation_matrix.yaml"))
        if str(row.get("external_boundary") or "").lower() == "deferred" and not row.get("deferred_reason"):
            issues.append(_issue("fpga_validation_obligation_gate", "error", f"{test_id} deferred external boundary lacks reason", "work/loop3_fpga_proto/config/fpga_validation_matrix.yaml"))
        claim = _level(row.get("claim_level"))
        evidence = _level(row.get("evidence_level"))
        if claim is not None and evidence is not None and claim > evidence:
            issues.append(_issue("fpga_validation_obligation_gate", "error", f"{test_id} claim level exceeds evidence level", "work/loop3_fpga_proto/config/fpga_validation_matrix.yaml"))
    return issues


def _release_truth_gate(project: Path, level: str) -> list[SemanticIssue]:
    state, blockers, warnings, _ = evaluate_release_state(project, level=level)
    issues = [_issue("release_truth_gate", "error", item, "work/gates/release_state.json") for item in blockers]
    issues.extend(_issue("release_truth_gate", "warning", item, "work/gates/release_state.json") for item in warnings)
    if level == "release" and state == "RELEASE_FAIL":
        issues.append(_issue("release_truth_gate", "error", "release state evaluates to RELEASE_FAIL", "work/gates/release_state.json"))
    return issues


CHECKERS: dict[str, Callable[[Path, str], list[SemanticIssue]]] = {
    "requirements_consistency_gate": _requirements_consistency_gate,
    "architecture_impact_gate": _architecture_impact_gate,
    "design_routing_gate": _design_routing_gate,
    "microarchitecture_completeness_gate": _microarchitecture_completeness_gate,
    "rtl_obligation_gate": _rtl_obligation_gate,
    "tb_blackbox_obligation_gate": _tb_blackbox_obligation_gate,
    "waveform_semantic_gate": _waveform_semantic_gate,
    "uvm_obligation_gate": _uvm_obligation_gate,
    "fpga_validation_obligation_gate": _fpga_validation_obligation_gate,
    "release_truth_gate": _release_truth_gate,
}


def _items(path: Path, key: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = load_yaml(path)
    except Exception:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
    rows = data.get(key, []) if isinstance(data, dict) else []
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _active_requirement_ids(project: Path) -> set[str]:
    return _ids(load_active_requirements(project), "requirement_id")


def _operation_ids(project: Path) -> set[str]:
    rows: list[dict[str, Any]] = []
    for key in ("operations", "register_map", "opcode_map", "packet_map", "streaming_protocol", "custom_operations"):
        rows.extend(_items(project / "work/docparse/verification/operation_model.yaml", key))
    ids = _ids(rows, "operation_id") | _ids(rows, "opcode") | _ids(rows, "register")
    return ids


def _interface_names(project: Path) -> set[str]:
    path = project / "work/loop1_rtl_tb/config/interface_contract.yaml"
    if not path.exists():
        return set()
    try:
        data = load_yaml(path)
    except Exception:
        return set()
    names: set[str] = set()
    if isinstance(data, dict):
        for key in ("interface_name", "name"):
            if data.get(key):
                names.add(str(data[key]))
        interfaces = data.get("interfaces")
        if isinstance(interfaces, list):
            for row in interfaces:
                if isinstance(row, dict):
                    for key in ("interface_name", "name"):
                        if row.get(key):
                            names.add(str(row[key]))
    return names


def _architecture_impact_content_issues(project: Path, path: Path, change_id: str) -> list[SemanticIssue]:
    try:
        data = load_yaml(path)
    except Exception:
        data = {}
    if isinstance(data, dict) and isinstance(data.get("impact"), dict):
        data = data["impact"]
    if not isinstance(data, dict):
        data = {}
    required_groups = {
        "affected functional domains": ("affected_functional_domains", "functional_domains"),
        "affected modules": ("affected_modules", "modules"),
        "interface changes": ("interface_changes", "affected_interfaces"),
        "state machine changes": ("state_machine_changes", "fsm_changes", "affected_states"),
        "reset changes": ("reset_changes",),
        "CDC changes": ("cdc_changes",),
        "timing changes": ("timing_changes",),
        "operation model changes": ("operation_model_changes", "register_changes", "opcode_changes"),
        "TB changes": ("tb_changes", "directed_tb_changes"),
        "VCD changes": ("vcd_changes", "waveform_changes"),
        "UVM changes": ("uvm_changes",),
        "FPGA changes": ("fpga_changes", "claim_changes"),
        "stale reports": ("stale_reports", "invalidated_reports"),
    }
    issues: list[SemanticIssue] = []
    rel = _rel(project, path)
    for label, keys in required_groups.items():
        if not any(_field_has_value(data.get(key)) for key in keys):
            issues.append(_issue("architecture_impact_gate", "error", f"{change_id} architecture impact review missing {label}", rel))
    return issues


def _replanning_record_issues(project: Path, path: Path, change_id: str, kind: str, keywords: tuple[str, ...]) -> list[SemanticIssue]:
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    rel = _rel(project, path)
    return [
        _issue("architecture_impact_gate", "error", f"{change_id} {kind} replanning record does not discuss {keyword}", rel)
        for keyword in keywords
        if keyword.lower() not in text
    ]


def _loop1_report_semantic_issues(project: Path, report: dict[str, Any], operation_ids: set[str], interface_names: set[str]) -> list[SemanticIssue]:
    issues: list[SemanticIssue] = []
    report_rel = "output/reports/loop1/loop1_report.json"
    transactions = report.get("transactions", []) if isinstance(report.get("transactions"), list) else []
    covered_ops: set[str] = set()
    for item in transactions:
        if not isinstance(item, dict) or str(item.get("result") or "").upper() != "PASS":
            continue
        op_id = str(item.get("operation_id") or "")
        if op_id:
            covered_ops.add(op_id)
        observed = str(item.get("observed_interface") or "")
        evidence_type = str(item.get("evidence_type") or "").lower()
        test_id = item.get("test_id") or item.get("txn_id") or "loop1_check"
        if not observed:
            issues.append(_issue("tb_blackbox_obligation_gate", "error", f"{test_id} PASS lacks observed_interface in Loop1 report", report_rel))
        if observed and interface_names and observed not in interface_names:
            issues.append(_issue("tb_blackbox_obligation_gate", "error", f"{test_id} observed interface is not in contract: {observed}", report_rel))
        if evidence_type in {"", "whitebox", "whitebox_only"}:
            issues.append(_issue("tb_blackbox_obligation_gate", "error", f"{test_id} PASS has non-blackbox evidence_type: {evidence_type or 'missing'}", report_rel))
    for missing in sorted(operation_ids - covered_ops):
        issues.append(_issue("tb_blackbox_obligation_gate", "error", f"operation {missing} is not covered by Loop1 report", report_rel))
    semantic = report.get("semantic_summary", {}) if isinstance(report.get("semantic_summary"), dict) else {}
    if _int_value(semantic.get("whitebox_only_check_count")):
        issues.append(_issue("tb_blackbox_obligation_gate", "error", "Loop1 report contains whitebox-only PASS checks", report_rel))
    if _int_value(semantic.get("missing_observed_interface_count")):
        issues.append(_issue("tb_blackbox_obligation_gate", "error", "Loop1 report contains PASS checks without observed_interface", report_rel))
    return issues


def _loop2_report_semantic_issues(project: Path, report: dict[str, Any], operation_ids: set[str]) -> list[SemanticIssue]:
    del project
    issues: list[SemanticIssue] = []
    report_rel = "output/reports/loop2/loop2_report.json"
    semantic = report.get("semantic_summary", {}) if isinstance(report.get("semantic_summary"), dict) else {}
    summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
    coverage_source = str(semantic.get("coverage_source") or summary.get("coverage_source") or "not_reported").lower()
    if coverage_source in {"", "not_reported", "hardcoded", "hard-coded", "constant"}:
        issues.append(_issue("uvm_obligation_gate", "error", f"Loop2 coverage source is not a collector: {coverage_source}", report_rel))
    if operation_ids and _int_value(semantic.get("scenario_kind_count")) < 2:
        issues.append(_issue("uvm_obligation_gate", "error", "Loop2 report does not prove multi-scenario UVM coverage", report_rel))
    if operation_ids and _int_value(semantic.get("reference_model_check_count")) == 0:
        issues.append(_issue("uvm_obligation_gate", "error", "Loop2 report has no reference-model scoreboard checks", report_rel))
    if operation_ids and _int_value(semantic.get("monitor_observed_check_count")) == 0:
        issues.append(_issue("uvm_obligation_gate", "error", "Loop2 report has no monitor-observed transaction checks", report_rel))
    if operation_ids and _int_value(semantic.get("covered_operation_count")) < len(operation_ids):
        issues.append(_issue("uvm_obligation_gate", "error", "Loop2 report does not cover every operation_model entry", report_rel))
    return issues


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _field_has_value(value: Any) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, list | dict):
        return bool(value)
    return True


def _int_value(value: Any) -> int:
    try:
        return int(str(value))
    except Exception:
        return 0


def _trace_requirement_ids(project: Path) -> set[str]:
    ids: set[str] = set()
    for root_rel in ("work/docparse/trace_matrix", "work/traces"):
        root = project / root_rel
        if not root.exists():
            continue
        for path in sorted(root.glob("*.yaml")) + sorted(root.glob("*.json")):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            try:
                payload = load_yaml(path)
            except Exception:
                payload = None
            ids.update(_trace_ids_from_payload(payload))
            ids.update(re.findall(r"\b(?:REQ|ASM|BASELINE)-[A-Za-z0-9_.:-]+\b", text))
    return ids


def _trace_ids_from_payload(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        req_id = value.get("requirement_id")
        if req_id:
            found.add(str(req_id))
        for item in value.values():
            found.update(_trace_ids_from_payload(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_trace_ids_from_payload(item))
    return found


def _ids(rows: list[dict[str, Any]], key: str) -> set[str]:
    return {str(row.get(key)) for row in rows if row.get(key)}


def _issue(gate: str, severity: str, message: str, evidence: str) -> SemanticIssue:
    return SemanticIssue(gate=gate, severity=severity, message=message, evidence=evidence)


def _as_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    return value if isinstance(value, list) else [value]


def _level(value: Any) -> int | None:
    if value is None or value == "":
        return None
    match = re.search(r"(\d+)", str(value))
    return int(match.group(1)) if match else None


def _rel(project: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")
