"""Compile semantic architecture and verification closure artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import load_project
from .project import require_project_instance
from .requirements_compiler import compile_requirements, load_active_requirements
from .simple_yaml import load_yaml


GENERATED_BY = "hdlflow.semantic_closure"

FUNCTIONAL_DOMAIN_MODEL_REL = "work/docparse/architecture/functional_domain_model.yaml"
DESIGN_ROUTING_REL = "work/docparse/architecture/design_routing.yaml"
MODULE_OWNERSHIP_REL = "work/docparse/architecture/module_ownership_matrix.yaml"
OPERATION_MODEL_REL = "work/docparse/verification/operation_model.yaml"
REQ_TO_DESIGN_INTENT_REL = "work/docparse/trace_matrix/req_to_design_intent.yaml"
REQ_TO_TEST_INTENT_REL = "work/docparse/trace_matrix/req_to_test_intent.yaml"
REQ_TO_RTL_REL = "work/loop1_rtl_tb/trace_matrix/req_to_rtl_implementation.yaml"
INTERFACE_CONTRACT_REL = "work/loop1_rtl_tb/config/interface_contract.yaml"
TB_OBLIGATIONS_REL = "work/loop1_rtl_tb/config/tb_obligations.yaml"
WAVE_SEMANTIC_MANIFEST_REL = "work/loop1_rtl_tb/config/wave_semantic_manifest.yaml"
UVM_OBLIGATIONS_REL = "work/loop2_uvm/config/uvm_obligations.yaml"
FPGA_VALIDATION_MATRIX_REL = "work/loop3_fpga_proto/config/fpga_validation_matrix.yaml"


@dataclass(frozen=True)
class SemanticClosureResult:
    project: Path
    requirement_count: int
    operation_count: int
    written: list[Path]
    skipped: list[Path]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return self.requirement_count > 0


def compile_semantic_closure(project_path: Path, *, overwrite: bool = False) -> SemanticClosureResult:
    """Generate P1-P4 semantic planning artifacts from the active requirement baseline.

    The compiler deliberately writes obligation state as ``planned``. It creates
    traceable work items and release-blocking evidence expectations, but it does
    not fabricate implementation or verification PASS evidence.
    """

    project = require_project_instance(project_path)
    req_result = compile_requirements(project)
    requirements = load_active_requirements(project)
    warnings = list(req_result.warnings)
    if not requirements:
        return SemanticClosureResult(project, 0, 0, req_result.written, [], warnings)

    rtl_modules = _scan_rtl(project)
    interface = _infer_interface(project, requirements, rtl_modules)
    operations = [_operation_for_requirement(req, interface["name"]) for req in requirements]
    evidence = _semantic_evidence(project, operations)
    domains = _functional_domains(requirements, operations, interface["name"], rtl_modules)
    routes = [_route_for_requirement(req, operations[index], interface["name"], rtl_modules) for index, req in enumerate(requirements)]
    owners = [_owner_for_route(route) for route in routes]

    artifacts: list[tuple[str, dict[str, Any], str]] = [
        (
            FUNCTIONAL_DOMAIN_MODEL_REL,
            {
                "schema_version": 1,
                "generated_by": GENERATED_BY,
                "generated_at": _now(),
                "domains": domains,
            },
            "domains",
        ),
        (
            DESIGN_ROUTING_REL,
            {
                "schema_version": 1,
                "generated_by": GENERATED_BY,
                "generated_at": _now(),
                "routes": routes,
            },
            "routes",
        ),
        (
            MODULE_OWNERSHIP_REL,
            {
                "schema_version": 1,
                "generated_by": GENERATED_BY,
                "generated_at": _now(),
                "owners": owners,
            },
            "owners",
        ),
        (
            OPERATION_MODEL_REL,
            {
                "schema_version": 1,
                "generated_by": GENERATED_BY,
                "generated_at": _now(),
                "operations": operations,
                "register_map": [],
                "opcode_map": [],
                "packet_map": [],
                "streaming_protocol": [],
                "custom_operations": [],
            },
            "operations",
        ),
        (
            REQ_TO_DESIGN_INTENT_REL,
            {
                "schema_version": 1,
                "generated_by": GENERATED_BY,
                "generated_at": _now(),
                "project": project.name,
                "status": "READY",
                "owner_role": "arch",
                "stage": "docparse",
                "target": "design_intent",
                "links": [_design_trace_link(route) for route in routes],
                "unmapped_requirements": [],
                "assumptions": [],
            },
            "links",
        ),
        (
            REQ_TO_TEST_INTENT_REL,
            {
                "schema_version": 1,
                "generated_by": GENERATED_BY,
                "generated_at": _now(),
                "project": project.name,
                "status": "READY",
                "owner_role": "sim",
                "stage": "docparse",
                "target": "test_intent",
                "links": [_test_trace_link(operation) for operation in operations],
                "unmapped_requirements": [],
                "assumptions": [],
            },
            "links",
        ),
        (
            REQ_TO_RTL_REL,
            {
                "schema_version": 1,
                "generated_by": GENERATED_BY,
                "generated_at": _now(),
                "implementations": [_rtl_implementation_for_route(route, rtl_modules, evidence) for route in routes],
            },
            "implementations",
        ),
        (
            INTERFACE_CONTRACT_REL,
            {
                "schema_version": 1,
                "generated_by": GENERATED_BY,
                "generated_at": _now(),
                "interface_name": interface["name"],
                "interfaces": [interface],
            },
            "interfaces",
        ),
        (
            TB_OBLIGATIONS_REL,
            {
                "schema_version": 1,
                "generated_by": GENERATED_BY,
                "generated_at": _now(),
                "obligations": [_tb_obligation_for_operation(operation, interface["name"], evidence) for operation in operations],
            },
            "obligations",
        ),
        (
            WAVE_SEMANTIC_MANIFEST_REL,
            {
                "schema_version": 1,
                "generated_by": GENERATED_BY,
                "generated_at": _now(),
                "windows": [_wave_window_for_operation(operation, interface["name"], evidence) for operation in operations],
            },
            "windows",
        ),
        (
            UVM_OBLIGATIONS_REL,
            {
                "schema_version": 1,
                "generated_by": GENERATED_BY,
                "generated_at": _now(),
                "obligations": [_uvm_obligation_for_operation(operation, evidence) for operation in operations],
            },
            "obligations",
        ),
        (
            FPGA_VALIDATION_MATRIX_REL,
            {
                "schema_version": 1,
                "generated_by": GENERATED_BY,
                "generated_at": _now(),
                "claim_levels": {
                    "level_0": "Build / Implementation",
                    "level_1": "Wrapper / PS-PL Connectivity",
                    "level_2": "Protocol Bring-up / Connectivity Validation",
                    "level_3": "Requirement-Mapped FPGA Validation",
                    "level_4": "External Pin / Hardware Boundary",
                },
                "tests": [_fpga_test_for_operation(operation, interface["name"], evidence) for operation in operations],
                "timing_cdc_issues": _timing_cdc_issues(project),
                "hash_manifest": _fpga_hash_manifest(project),
            },
            "tests",
        ),
    ]

    written = list(req_result.written)
    skipped: list[Path] = []
    for rel, payload, primary_key in artifacts:
        path = project / rel
        if _should_write(path, primary_key, overwrite):
            written.append(_write_yaml(path, payload))
        else:
            skipped.append(path)

    written.extend(_write_change_closure(project, requirements, routes, operations, overwrite=overwrite))
    return SemanticClosureResult(project, len(requirements), len(operations), written, skipped, warnings)


def _functional_domains(
    requirements: list[dict[str, Any]],
    operations: list[dict[str, Any]],
    interface_name: str,
    rtl_modules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_domain: dict[str, dict[str, Any]] = {}
    module_names = [str(item.get("module")) for item in rtl_modules if item.get("module")]
    default_module = module_names[0] if module_names else "rtl_module_planned"
    op_by_req = {op["requirement_ids"][0]: op["operation_id"] for op in operations if op.get("requirement_ids")}
    for req in requirements:
        domain = _domain(req)
        row = by_domain.setdefault(
            domain,
            {
                "domain": domain,
                "requirement_ids": [],
                "operation_ids": [],
                "owner_modules": [],
                "primary_interfaces": [interface_name],
                "verification_focus": ["directed_tb", "waveform_semantic", "uvm", "fpga"],
                "release_evidence": [
                    "RTL implementation trace",
                    "Loop1 black-box TB transaction",
                    "verification-level waveform semantic decode",
                    "UVM reference-model coverage",
                    "FPGA validation matrix claim evidence",
                ],
            },
        )
        row["requirement_ids"].append(str(req.get("requirement_id")))
        op_id = op_by_req.get(str(req.get("requirement_id")))
        if op_id:
            row["operation_ids"].append(op_id)
        owner = _preferred_module_for_domain(domain, module_names) or default_module
        if owner not in row["owner_modules"]:
            row["owner_modules"].append(owner)
    return sorted(by_domain.values(), key=lambda item: item["domain"])


def _route_for_requirement(
    req: dict[str, Any],
    operation: dict[str, Any],
    interface_name: str,
    rtl_modules: list[dict[str, Any]],
) -> dict[str, Any]:
    req_id = str(req.get("requirement_id"))
    domain = _domain(req)
    modules = [item["module"] for item in rtl_modules if item.get("module")]
    owner = _preferred_module_for_domain(domain, modules) or (modules[0] if modules else "rtl_module_planned")
    return {
        "requirement_id": req_id,
        "functional_domain": domain,
        "change_id": str(req.get("change_id") or "baseline"),
        "operation_id": operation["operation_id"],
        "design_doc_sections": [
            "Microarchitecture Specification / Requirement-to-Architecture Summary",
            "Microarchitecture Specification / Module Ownership Matrix",
            "Verification Plan / Operation Model",
            "Verification Plan / TB VCD UVM FPGA Semantic Obligations",
        ],
        "affected_modules": [owner],
        "affected_interfaces": [interface_name],
        "verification_hooks": [
            f"tb:{operation['operation_id']}",
            f"vcd:{operation['operation_id']}",
            f"uvm:{operation['operation_id']}",
            f"fpga:{req_id}",
        ],
        "routing_status": "planned",
    }


def _owner_for_route(route: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": route["requirement_id"],
        "functional_domain": route["functional_domain"],
        "design_doc_sections": route["design_doc_sections"],
        "rtl_owner_module": route["affected_modules"],
        "interface_owner": route["affected_interfaces"],
        "verification_owner": route["verification_hooks"],
        "operation_id": route["operation_id"],
        "ownership_status": "planned",
    }


def _operation_for_requirement(req: dict[str, Any], interface_name: str) -> dict[str, Any]:
    req_id = str(req.get("requirement_id"))
    text = " ".join(str(req.get(key) or "") for key in ("title", "full_text", "description")).lower()
    op_type = _operation_type(text)
    op_id = "OP_" + _sanitize_id(req_id)
    stimulus = _stimulus_for(op_type, req)
    expected = _expected_for(op_type, req)
    return {
        "operation_id": op_id,
        "requirement_ids": [req_id],
        "operation_type": op_type,
        "access": _access_for(op_type),
        "interface_name": interface_name,
        "stimulus": stimulus,
        "expected_response": expected,
        "readback_rule": "black-box observable response or status readback must match acceptance criterion",
        "side_effects": ["no undocumented side effects may be inferred as PASS evidence"],
        "reset_behavior": "operation remains deterministic across reset entry and release unless requirement explicitly waives it",
        "coverage_bins": [
            f"{op_id.lower()}_nominal",
            f"{op_id.lower()}_reset_interaction",
            f"{op_id.lower()}_negative_or_boundary",
        ],
        "source_requirement_title": str(req.get("title") or req_id),
        "status": "planned",
    }


def _design_trace_link(route: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": route["requirement_id"],
        "design_intent": route["operation_id"],
        "artifact": DESIGN_ROUTING_REL,
        "affected_modules": route.get("affected_modules") or [],
        "affected_interfaces": route.get("affected_interfaces") or [],
    }


def _test_trace_link(operation: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": str(_first(operation.get("requirement_ids")) or ""),
        "test_intent": operation["operation_id"],
        "artifact": OPERATION_MODEL_REL,
        "coverage_bins": operation.get("coverage_bins") or [],
    }


def _rtl_implementation_for_route(route: dict[str, Any], rtl_modules: list[dict[str, Any]], evidence: dict[str, Any]) -> dict[str, Any]:
    module = str(_first(route.get("affected_modules")) or "rtl_module_planned")
    op_id = str(route["operation_id"])
    rtl_by_module = {str(item.get("module")): item for item in rtl_modules if item.get("module")}
    rtl_file = str(rtl_by_module.get(module, {}).get("path") or f"output/rtl/{module}.v")
    rtl_exists = bool(evidence.get("rtl_files", {}).get(rtl_file))
    covered = rtl_exists and op_id in evidence.get("loop1_operations", set())
    evidence_paths = [rtl_file] if rtl_exists else []
    if covered:
        evidence_paths.extend(evidence.get("loop1_evidence_paths", []))
    return {
        "requirement_id": route["requirement_id"],
        "operation_id": op_id,
        "rtl_file": rtl_file,
        "module": module,
        "implementation_points": [
            "functional behavior logic",
            "top-interface observable response",
            "reset and CDC-safe state ownership",
        ],
        "implementation_status": "implemented" if covered else "planned",
        "evidence": evidence_paths,
    }


def _tb_obligation_for_operation(operation: dict[str, Any], interface_name: str, evidence: dict[str, Any]) -> dict[str, Any]:
    op_id = str(operation["operation_id"])
    req_id = str(_first(operation.get("requirement_ids")) or "")
    covered = op_id in evidence.get("loop1_operations", set())
    return {
        "requirement_id": req_id,
        "operation_id": op_id,
        "test_id": f"tb_{op_id.lower()}",
        "observed_interface": interface_name,
        "evidence_type": "blackbox",
        "required_blackbox_check": True,
        "stimulus": operation.get("stimulus"),
        "expected_top_interface_response": operation.get("expected_response"),
        "required_report_fields": [
            "requirement_id",
            "operation_id",
            "observed_interface",
            "evidence_type",
            "expected",
            "actual",
            "latency_cycles",
            "result",
        ],
        "status": "verified" if covered else "planned",
        "evidence_paths": evidence.get("loop1_evidence_paths", []) if covered else [],
    }


def _wave_window_for_operation(operation: dict[str, Any], interface_name: str, evidence: dict[str, Any]) -> dict[str, Any]:
    op_id = str(operation["operation_id"])
    covered = op_id in evidence.get("wave_operations", set())
    return {
        "window_id": f"wave_{op_id.lower()}",
        "operation_id": op_id,
        "interface_name": interface_name,
        "decoder": "event_list_decoder",
        "evidence_level": "verification",
        "event_source": "output/reports/loop1/interface_transaction_report.json",
        "expected_events": [
            {
                "interface": interface_name,
                "operation": op_id,
                "status": "PASS",
            }
        ],
        "required_waveform_sources": ["output/sim/loop1/wave/*.vcd", "output/sim/loop1/wave/*.wlf"],
        "status": "verified" if covered else "planned",
    }


def _uvm_obligation_for_operation(operation: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    op_id = str(operation["operation_id"])
    req_id = str(_first(operation.get("requirement_ids")) or "")
    covered = op_id in evidence.get("loop2_operations", set())
    return {
        "requirement_id": req_id,
        "operation_id": op_id,
        "sequence_id": f"seq_{op_id.lower()}",
        "coverage_bins": operation.get("coverage_bins") or [f"{op_id.lower()}_bin"],
        "cross_coverage": [f"{op_id.lower()}_x_reset", f"{op_id.lower()}_x_error_or_boundary"],
        "scoreboard_model": "reference_model",
        "assertions": [f"assert_{op_id.lower()}_blackbox_response"],
        "randomized_tests": [f"random_{op_id.lower()}"],
        "long_sequence_tests": [f"long_{op_id.lower()}"],
        "negative_tests": [f"negative_{op_id.lower()}"],
        "required_monitor_role": "monitor_observed_transaction",
        "coverage_source": "coverage_collector",
        "status": "verified" if covered else "planned",
        "evidence_paths": evidence.get("loop2_evidence_paths", []) if covered else [],
    }


def _fpga_test_for_operation(operation: dict[str, Any], interface_name: str, evidence: dict[str, Any]) -> dict[str, Any]:
    op_id = str(operation["operation_id"])
    req_id = str(_first(operation.get("requirement_ids")) or op_id)
    fpga_pass = bool(evidence.get("loop3_pass"))
    return {
        "test_id": f"fpga_{_sanitize_id(req_id).lower()}",
        "requirement_id": req_id,
        "operation_id": op_id,
        "interface_name": interface_name,
        "validation_mode": "ps_pl_emulation",
        "claim_level": "level_0",
        "evidence_level": "level_0",
        "expected": operation.get("expected_response"),
        "actual": "Loop3 build, timing, boot, and board validation reports are PASS" if fpga_pass else "",
        "comparison": "PASS evidence level matches claim level" if fpga_pass else "",
        "external_boundary": "deferred",
        "deferred_reason": "No external board/pin evidence has been attached to this requirement yet.",
        "status": "verified" if fpga_pass else "planned",
        "evidence_paths": evidence.get("loop3_evidence_paths", []) if fpga_pass else [],
    }


def _semantic_evidence(project: Path, operations: list[dict[str, Any]]) -> dict[str, Any]:
    loop1_report_rel = "output/reports/loop1/loop1_report.json"
    interface_report_rel = "output/reports/loop1/interface_transaction_report.json"
    wave_report_rel = "output/reports/loop1/waveform_semantic_report.json"
    loop2_report_rel = "output/reports/loop2/loop2_report.json"
    loop3_exit_rel = "output/reports/loop3/loop3_exit_report.md"
    loop3_impl_rel = "output/reports/loop3/vivado_implementation_report.md"
    loop3_board_rel = "output/reports/loop3/board_validation_report.md"
    loop3_boot_rel = "output/reports/loop3/vitis_boot_report.md"

    loop1 = _read_json(project / loop1_report_rel)
    loop2 = _read_json(project / loop2_report_rel)
    wave = _read_json(project / wave_report_rel)

    loop1_ops = _covered_ops_from_transactions(loop1)
    loop2_ops = _covered_ops_from_transactions(loop2)
    wave_ops = _covered_wave_ops(wave)

    loop3_paths = [loop3_exit_rel, loop3_impl_rel, loop3_board_rel, loop3_boot_rel]
    loop3_pass = all(_markdown_result_is_pass(project / rel) for rel in loop3_paths)
    rtl_files = {_rel(project, path): True for path in sorted((project / "output/rtl").glob("*.v")) + sorted((project / "output/rtl").glob("*.sv"))}

    return {
        "rtl_files": rtl_files,
        "loop1_operations": loop1_ops,
        "loop1_evidence_paths": [rel for rel in (loop1_report_rel, interface_report_rel) if (project / rel).exists()],
        "wave_operations": wave_ops,
        "loop2_operations": loop2_ops,
        "loop2_evidence_paths": [loop2_report_rel] if (project / loop2_report_rel).exists() else [],
        "loop3_pass": loop3_pass,
        "loop3_evidence_paths": [rel for rel in loop3_paths if (project / rel).exists()],
    }


def _covered_ops_from_transactions(report: dict[str, Any]) -> set[str]:
    if str(report.get("result") or "").upper() != "PASS":
        return set()
    transactions = report.get("transactions")
    if not isinstance(transactions, list):
        return set()
    return {
        str(item.get("operation_id"))
        for item in transactions
        if isinstance(item, dict)
        and str(item.get("result") or "").upper() == "PASS"
        and item.get("operation_id")
    }


def _covered_wave_ops(report: dict[str, Any]) -> set[str]:
    if str(report.get("result") or "").upper() != "PASS":
        return set()
    rows = report.get("windows")
    if not isinstance(rows, list):
        return set()
    return {
        str(item.get("operation_id"))
        for item in rows
        if isinstance(item, dict)
        and str(item.get("status") or "").upper() == "PASS"
        and item.get("operation_id")
    }


def _markdown_result_is_pass(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="ignore")
    return bool(re.search(r"(?mi)^\s*-?\s*result:\s*PASS\s*$", text))


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _write_change_closure(
    project: Path,
    requirements: list[dict[str, Any]],
    routes: list[dict[str, Any]],
    operations: list[dict[str, Any]],
    *,
    overwrite: bool,
) -> list[Path]:
    written: list[Path] = []
    request_root = project / "work/change/requests"
    if not request_root.exists():
        return written
    route_modules = sorted({module for route in routes for module in _as_list(route.get("affected_modules"))})
    route_interfaces = sorted({iface for route in routes for iface in _as_list(route.get("affected_interfaces"))})
    domains = sorted({_domain(req) for req in requirements})
    operation_ids = [str(operation.get("operation_id")) for operation in operations]
    for request in sorted(request_root.glob("CR-*.md")) + sorted(request_root.glob("CR-*.yaml")):
        change_id = request.stem
        change_dir = project / "work/docparse/change" / change_id
        impact_rel = f"work/docparse/change/{change_id}/architecture_impact_review.yaml"
        impact = {
            "schema_version": 1,
            "generated_by": GENERATED_BY,
            "generated_at": _now(),
            "impact": {
                "change_id": change_id,
                "source_request": _rel(project, request),
                "affected_functional_domains": domains or ["unassigned"],
                "affected_modules": route_modules or ["rtl_module_planned"],
                "interface_changes": route_interfaces or ["top_interface"],
                "state_machine_changes": ["state ownership must be rechecked for changed operations"],
                "reset_changes": ["reset behavior must be revalidated for affected operations"],
                "cdc_changes": ["CDC crossings must be revalidated for affected interfaces"],
                "timing_changes": ["timing and constraints reports become stale until regenerated"],
                "operation_model_changes": operation_ids or ["operation model recompile required"],
                "tb_changes": ["directed TB obligations and black-box report fields must be regenerated"],
                "vcd_changes": ["wave semantic verification windows must be regenerated"],
                "uvm_changes": ["UVM sequences, scoreboard, assertions, and coverage must be regenerated"],
                "fpga_changes": ["FPGA validation matrix claim levels and evidence paths must be regenerated"],
                "stale_reports": [
                    "output/reports/loop1/loop1_report.json",
                    "output/reports/loop2/loop2_report.json",
                    "output/reports/loop3/loop3_exit_report.md",
                    "output/reports/final_audit_report.md",
                ],
                "status": "analysis_required",
            },
        }
        if _should_write(project / impact_rel, "impact", overwrite):
            written.append(_write_yaml(project / impact_rel, impact))

        design_record = change_dir / "design_replanning_record.md"
        if _should_write_text(design_record, overwrite):
            design_record.parent.mkdir(parents=True, exist_ok=True)
            design_record.write_text(_design_replan_text(change_id, route_modules, route_interfaces), encoding="utf-8")
            written.append(design_record)

        verification_record = change_dir / "verification_replanning_record.md"
        if _should_write_text(verification_record, overwrite):
            verification_record.parent.mkdir(parents=True, exist_ok=True)
            verification_record.write_text(_verification_replan_text(change_id, operation_ids), encoding="utf-8")
            written.append(verification_record)
    return written


def _design_replan_text(change_id: str, modules: list[str], interfaces: list[str]) -> str:
    module_text = ", ".join(modules or ["rtl_module_planned"])
    interface_text = ", ".join(interfaces or ["top_interface"])
    return "\n".join(
        [
            f"# Design Replanning Record {change_id}",
            "",
            f"- generated_by: {GENERATED_BY}",
            f"- generated_at: {_now()}",
            f"- module impact: {module_text}",
            f"- interface impact: {interface_text}",
            "- state impact: re-evaluate FSM/state ownership for every changed operation",
            "- reset impact: reset entry, reset exit, and post-reset observable response must be restated",
            "- cdc impact: CDC boundaries must be rechecked for command/data/status crossings",
            "- timing impact: constraints, paths, and implementation timing reports become stale",
            "- status: analysis_required",
            "",
        ]
    )


def _verification_replan_text(change_id: str, operation_ids: list[str]) -> str:
    op_text = ", ".join(operation_ids or ["operation model recompile required"])
    return "\n".join(
        [
            f"# Verification Replanning Record {change_id}",
            "",
            f"- generated_by: {GENERATED_BY}",
            f"- generated_at: {_now()}",
            f"- operation scope: {op_text}",
            "- tb impact: directed TB obligations and black-box interface reports must be regenerated",
            "- vcd impact: semantic waveform windows must decode expected transaction events",
            "- uvm impact: UVM sequences, monitors, coverage collectors, assertions, and scoreboards must be regenerated",
            "- fpga impact: FPGA validation matrix expected/actual/comparison evidence must be regenerated",
            "- coverage impact: operation coverage must be collected, not hard-coded",
            "- claim impact: FPGA claim level cannot exceed attached evidence level",
            "- status: analysis_required",
            "",
        ]
    )


def _infer_interface(project: Path, requirements: list[dict[str, Any]], rtl_modules: list[dict[str, Any]]) -> dict[str, Any]:
    text = " ".join(str(req.get(key) or "") for req in requirements for key in ("title", "full_text", "functional_domain")).lower()
    protocol = "generic_blackbox"
    name = "top_interface"
    if "spi" in text:
        protocol = "spi"
        name = "spi_host"
    elif "axi" in text:
        protocol = "axi_lite"
        name = "axi_lite"
    elif "apb" in text:
        protocol = "apb"
        name = "apb"
    top = _top_module(project, rtl_modules)
    ports = top.get("ports", []) if top else []
    return {
        "name": name,
        "protocol": protocol,
        "direction": "top_level_blackbox",
        "top_module": top.get("module") if top else "top_module_planned",
        "ports": ports,
        "observability": "TB, waveform, UVM monitor, and FPGA evidence must observe this boundary",
    }


def _top_module(project: Path, rtl_modules: list[dict[str, Any]]) -> dict[str, Any]:
    if not rtl_modules:
        return {}
    top_name = ""
    try:
        cfg = load_project(project).data
        top_name = str(cfg.get("top_module") or cfg.get("ip_name") or "")
        nested = cfg.get("project")
        if not top_name and isinstance(nested, dict):
            top_name = str(nested.get("top_module") or nested.get("ip_name") or "")
    except Exception:
        top_name = ""
    if top_name:
        for module in rtl_modules:
            if module.get("module") == top_name:
                return module
    for module in rtl_modules:
        if str(module.get("module") or "").endswith("_top"):
            return module
    return rtl_modules[0]


def _scan_rtl(project: Path) -> list[dict[str, Any]]:
    root = project / "output/rtl"
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.v")) + sorted(root.glob("*.sv")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        module = re.search(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)", text)
        rows.append(
            {
                "path": _rel(project, path),
                "module": module.group(1) if module else path.stem,
                "ports": _parse_ports(text),
            }
        )
    return rows


def _parse_ports(text: str) -> list[dict[str, str]]:
    ports: list[dict[str, str]] = []
    for raw in text.splitlines():
        line = raw.split("//", 1)[0].strip().rstrip(",);")
        match = re.match(r"(input|output|inout)\s+(?:wire|reg|logic)?\s*(\[[^\]]+\])?\s*([A-Za-z_][A-Za-z0-9_$]*)", line)
        if match:
            direction, width, name = match.groups()
            ports.append({"name": name, "direction": direction, "width": width or "1"})
    return ports


def _operation_type(text: str) -> str:
    if any(word in text for word in ("reset", "复位")):
        return "reset"
    if any(word in text for word in ("read", "status", "mailbox", "读取", "状态")):
        return "read"
    if any(word in text for word in ("write", "config", "command", "control", "写", "配置", "命令")):
        return "write"
    if any(word in text for word in ("stream", "packet", "frame", "rx", "tx", "数据", "帧")):
        return "stream"
    return "functional"


def _access_for(operation_type: str) -> str:
    return {
        "read": "read",
        "write": "write",
        "reset": "reset_sequence",
        "stream": "transaction_stream",
    }.get(operation_type, "stimulus_response")


def _stimulus_for(operation_type: str, req: dict[str, Any]) -> str:
    title = str(req.get("title") or req.get("requirement_id") or "requirement")
    return f"{operation_type} stimulus derived from requirement: {title}"


def _expected_for(operation_type: str, req: dict[str, Any]) -> str:
    title = str(req.get("title") or req.get("requirement_id") or "requirement")
    return f"observable {operation_type} response satisfies requirement: {title}"


def _preferred_module_for_domain(domain: str, modules: list[str]) -> str:
    if not modules:
        return ""
    normalized = _sanitize_id(domain).lower()
    for module in modules:
        if normalized and normalized in module.lower():
            return module
    for token in normalized.split("_"):
        if len(token) < 3:
            continue
        for module in modules:
            if token in module.lower():
                return module
    for module in modules:
        if module.endswith("_top"):
            return module
    return modules[0]


def _timing_cdc_issues(project: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    reports = [
        project / "output/fpga/vivado/reports/post_impl_timing_summary.rpt",
        project / "output/fpga/vivado/reports/post_impl_drc.rpt",
    ]
    for report in reports:
        if not report.exists():
            rows.append({"report": _rel(project, report), "status": "missing", "summary": "report not generated"})
            continue
        text = report.read_text(encoding="utf-8", errors="ignore")
        status = "needs_review" if re.search(r"\b(FAIL|VIOLATED|CRITICAL WARNING|ERROR)\b", text, re.I) else "reported"
        rows.append({"report": _rel(project, report), "status": status, "sha256": _sha256(report)})
    return rows


def _fpga_hash_manifest(project: Path) -> dict[str, list[dict[str, str]]]:
    patterns = {
        "bitstream": ["output/fpga/**/*.bit"],
        "xsa": ["output/fpga/**/*.xsa"],
        "elf": ["output/fpga/**/*.elf"],
        "boot_bin": ["output/fpga/**/*.bin", "output/fpga/**/*.bif"],
    }
    manifest: dict[str, list[dict[str, str]]] = {}
    for key, globs in patterns.items():
        rows: list[dict[str, str]] = []
        for pattern in globs:
            for path in sorted(project.glob(pattern)):
                if path.is_file():
                    rows.append({"path": _rel(project, path), "sha256": _sha256(path)})
        manifest[key] = rows
    return manifest


def _should_write(path: Path, primary_key: str, overwrite: bool) -> bool:
    if overwrite or not path.exists():
        return True
    try:
        data = load_yaml(path)
    except Exception:
        return False
    if not isinstance(data, dict):
        return False
    if data.get("generated_by") == GENERATED_BY:
        return True
    value = data.get(primary_key)
    return value in (None, "", [], {})


def _should_write_text(path: Path, overwrite: bool) -> bool:
    if overwrite or not path.exists():
        return True
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    return not text or GENERATED_BY in text


def _write_yaml(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump_yaml(data), encoding="utf-8")
    return path


def _dump_yaml(value: Any, indent: int = 0) -> str:
    lines: list[str] = []
    prefix = " " * indent
    if isinstance(value, dict):
        for key, child in value.items():
            if child == []:
                lines.append(f"{prefix}{key}: []")
            elif child == {}:
                lines.append(f"{prefix}{key}: {{}}")
            elif isinstance(child, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.append(_dump_yaml(child, indent + 2).rstrip())
            else:
                lines.append(f"{prefix}{key}: {_scalar(child)}")
    elif isinstance(value, list):
        if not value:
            lines.append(f"{prefix}[]")
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.append(_dump_yaml(item, indent + 2).rstrip())
            else:
                lines.append(f"{prefix}- {_scalar(item)}")
    else:
        lines.append(f"{prefix}{_scalar(value)}")
    return "\n".join(line for line in lines if line != "") + ("\n" if indent == 0 else "")


def _scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "":
        return '""'
    safe = all(ch.isalnum() or ch in "._-/:" for ch in text)
    if safe and text.lower() not in {"true", "false", "null", "none"}:
        return text
    return json.dumps(text, ensure_ascii=False)


def _domain(req: dict[str, Any]) -> str:
    return str(req.get("functional_domain") or req.get("domain") or "unassigned")


def _sanitize_id(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return text.upper() or hashlib.sha1(value.encode("utf-8")).hexdigest()[:8].upper()


def _as_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    return value if isinstance(value, list) else [value]


def _first(value: Any) -> Any:
    items = _as_list(value)
    return items[0] if items else ""


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return ""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _rel(project: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")
