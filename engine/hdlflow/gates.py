"""Executable project gate checks."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import load_project
from .design_doc import check_design_document, design_doc_manifest_rel, design_doc_report_rel
from .loop1_reports import refresh_loop1_reports
from .loop2_reports import refresh_loop2_reports
from .project import require_project_instance
from .requirements_frontend import check_requirements_frontend, required_frontend_paths
from .simple_yaml import load_yaml


PASS_RESULTS = {"PASS", "COMPLETE"}

GENERATED_REQUIREMENT_FILES = {
    "README.md",
    "srs.yaml",
    "srs.md",
    "acceptance_criteria.yaml",
    "open_questions.md",
    "requirements.json",
    "module_plan.md",
    "path_partition.md",
    "design_blueprint.md",
    "decomposition_notes.md",
}


@dataclass(frozen=True)
class GateCheck:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class GateRunResult:
    node: str
    level: str
    ok: bool
    report_path: Path
    checks: list[GateCheck]
    manifest_path: Path | None


def run_gate(project_path: Path, node: str, level: str = "develop", change_id: str | None = None) -> GateRunResult:
    project = require_project_instance(project_path)

    normalized_node = _normalize_node(node)
    checks: list[GateCheck] = []
    checks.extend(_check_project_scaffold(project))
    checks.extend(_check_change_control(project, change_id))
    checks.extend(_refresh_reports_for_gate(project, normalized_node))

    source_paths, evidence_paths = _gate_paths(project, normalized_node)

    if normalized_node == "00_SPEC":
        checks.extend(_check_doc_sources(project))
    elif normalized_node == "01_DocParse":
        checks.extend(_check_docparse(project))
    elif normalized_node == "02_Loop1_RTL_TB":
        checks.extend(_check_loop1(project))
    elif normalized_node == "03_Loop2_UVM_Verify":
        checks.extend(_check_loop2(project, level))
    elif normalized_node == "04_Loop3_FPGA_Prototype":
        checks.extend(_check_loop3(project, level))
    elif normalized_node == "05_Output":
        checks.extend(_check_final(project, level))
    else:
        raise ValueError(f"unsupported gate node: {node}")

    checks.extend(_check_manifest_drift(project, normalized_node, source_paths, change_id))
    checks.extend(_check_skill_manifest_drift(project, normalized_node, change_id))
    checks.extend(_check_evidence_freshness(project, source_paths, evidence_paths))
    ok = all(check.status == "PASS" for check in checks)

    report_path = _write_gate_report(project, normalized_node, level, ok, checks, change_id)
    manifest_path = None
    if ok:
        manifest_path = _write_gate_manifest(project, normalized_node, level, source_paths, evidence_paths, report_path, change_id)
    return GateRunResult(normalized_node, level, ok, report_path, checks, manifest_path)


def run_final_audit(project_path: Path, level: str = "release") -> GateRunResult:
    return run_gate(project_path, "05_Output", level=level)


def _refresh_reports_for_gate(project: Path, node: str) -> list[GateCheck]:
    if node == "02_Loop1_RTL_TB":
        try:
            result = refresh_loop1_reports(project)
        except Exception as exc:
            return [GateCheck("loop1_report_refresh", "FAIL", f"failed to refresh Loop1 reports from latest log: {exc}")]
        return [GateCheck("loop1_report_refresh", "PASS", f"reports refreshed: {len(result.report_paths)} file(s)")]
    if node == "03_Loop2_UVM_Verify":
        try:
            result = refresh_loop2_reports(project)
        except Exception as exc:
            return [GateCheck("loop2_report_refresh", "FAIL", f"failed to refresh Loop2 reports from latest log: {exc}")]
        return [GateCheck("loop2_report_refresh", "PASS", f"reports refreshed: {len(result.report_paths)} file(s)")]
    return []


def _normalize_node(node: str) -> str:
    aliases = {
        "spec": "00_SPEC",
        "00": "00_SPEC",
        "docparse": "01_DocParse",
        "01": "01_DocParse",
        "loop1": "02_Loop1_RTL_TB",
        "02": "02_Loop1_RTL_TB",
        "loop2": "03_Loop2_UVM_Verify",
        "03": "03_Loop2_UVM_Verify",
        "loop3": "04_Loop3_FPGA_Prototype",
        "04": "04_Loop3_FPGA_Prototype",
        "final": "05_Output",
        "output": "05_Output",
        "05": "05_Output",
    }
    return aliases.get(node.lower(), node)


def _check_project_scaffold(project: Path) -> list[GateCheck]:
    path = project / "project_scaffold.yaml"
    if not path.exists():
        return [GateCheck("project_scaffold_schema", "FAIL", "missing project_scaffold.yaml")]
    try:
        data = load_yaml(path)
    except Exception as exc:
        return [GateCheck("project_scaffold_schema", "FAIL", f"project_scaffold.yaml is not parseable: {exc}")]
    required = {
        "schema_version": 1,
        "project": project.name,
        "creation_mode": "script_only",
        "template_source": "templates/project",
        "manual_project_directory_creation": "forbidden",
    }
    errors = [f"{key}={data.get(key)!r}" for key, expected in required.items() if data.get(key) != expected]
    if errors:
        return [GateCheck("project_scaffold_schema", "FAIL", "invalid scaffold marker fields: " + ", ".join(errors))]
    if not data.get("created_by") or not data.get("created_at"):
        return [GateCheck("project_scaffold_schema", "FAIL", "created_by and created_at are required")]
    return [GateCheck("project_scaffold_schema", "PASS", "script-created scaffold marker is valid")]


def _check_change_control(project: Path, change_id: str | None) -> list[GateCheck]:
    open_requests = _read_change_requests(project, statuses={"open", "impact_ready"})
    if not change_id:
        if open_requests:
            ids = ", ".join(item["id"] for item in open_requests)
            return [GateCheck("change_control_state", "FAIL", f"open or unapproved change request(s): {ids}")]
        return [GateCheck("change_control_state", "PASS", "no open unapproved change request blocks this gate")]

    request = _read_change_request(project, change_id)
    if not request:
        return [GateCheck("change_control_state", "FAIL", f"change request not found: {change_id}")]
    if request.get("status") != "approved":
        return [GateCheck("change_control_state", "FAIL", f"{change_id} status is {request.get('status')!r}, expected approved")]
    return [GateCheck("change_control_state", "PASS", f"approved change request bound: {change_id}")]


def _check_doc_sources(project: Path) -> list[GateCheck]:
    req = project / "00_SPEC" / "requirements"
    files = [path for path in req.glob("*") if path.is_file() and path.name != "README.md"]
    if files:
        return [GateCheck("source_spec_available", "PASS", f"{len(files)} requirement file(s) available")]
    return [GateCheck("source_spec_available", "FAIL", "no requirement source files under 00_SPEC/requirements")]


def _check_docparse(project: Path) -> list[GateCheck]:
    checks = _check_prerequisite_gate(project, "00_SPEC", "00_SPEC gate must pass before DocParse exit")
    required = [
        "01_DocParse/structured_spec/interface_spec.yaml",
        "01_DocParse/structured_spec/test_intent.yaml",
        "01_DocParse/structured_spec/timing_rules.yaml",
        "01_DocParse/req_decompose/module_plan.md",
        "01_DocParse/trace_matrix/req_to_rtl.yaml",
        "01_DocParse/trace_matrix/req_to_test.yaml",
    ]
    checks.extend(_path_checks(project, [*required, *required_frontend_paths()]))
    result = check_requirements_frontend(project, require_ready=True)
    checks.append(
        GateCheck(
            "requirements_frontdoor_ready",
            "PASS" if result.ok else "FAIL",
            f"report: {result.report_path.relative_to(project)}",
        )
    )
    for error in result.errors:
        checks.append(GateCheck("requirements_frontdoor_error", "FAIL", error))
    for warning in result.warnings:
        checks.append(GateCheck("requirements_frontdoor_warning", "PASS", warning))
    checks.extend(_check_design_doc(project, ["requirements", "rtl", "uvm", "fpga"]))
    checks.append(_check_official_protocol_naming(project))
    return checks


def _check_loop1(project: Path) -> list[GateCheck]:
    evidence = _node_evidence(project, "02_Loop1_RTL_TB")
    checks = _check_prerequisite_gate(project, "01_DocParse", "DocParse must pass before Loop1 starts")
    checks.extend(_check_skill_policy(project, "02_Loop1_RTL_TB"))
    checks.extend(_check_source_policy(project, "02_Loop1_RTL_TB"))
    checks.append(_check_official_protocol_naming(project))
    checks.append(_check_rtl_comment_headers(project))
    checks.extend(_check_design_doc(project, ["requirements", "rtl"]))
    run_report_rel = _evidence_str(evidence, "reports", "run", "05_Output/reports/loop1/loop1_rtl_tb_run_report.md")
    exit_report_rel = _evidence_str(evidence, "reports", "exit", "05_Output/reports/loop1/loop1_exit_report.md")
    checks.extend(_path_checks(
        project,
        [
            run_report_rel,
            exit_report_rel,
            "01_DocParse/trace_matrix/req_to_test.yaml",
        ],
    ))
    checks.extend(_check_skill_policy_freshness(project, "02_Loop1_RTL_TB", _files(project, [run_report_rel, exit_report_rel])))
    run_report = _read(_project_path(project, run_report_rel))
    exit_report = _read(_project_path(project, exit_report_rel))
    checks.append(_contains_any("loop1_directed_pass", run_report, _evidence_list(evidence, "required_markers", "directed_pass_any", ["PASS"])))
    checks.append(_contains_any("loop1_zero_errors", run_report + "\n" + exit_report, _evidence_list(evidence, "required_markers", "zero_errors_any", ["Errors: 0"])))
    checks.append(_check_bug_tracking(project, "02_Loop1_RTL_TB/bug_tracking"))
    return checks


def _check_loop2(project: Path, level: str) -> list[GateCheck]:
    evidence = _node_evidence(project, "03_Loop2_UVM_Verify")
    checks = _check_prerequisite_gate(project, "02_Loop1_RTL_TB", "Loop1 must pass before Loop2 starts")
    checks.extend(_check_skill_policy(project, "03_Loop2_UVM_Verify"))
    checks.extend(_check_source_policy(project, "03_Loop2_UVM_Verify"))
    checks.append(_check_official_protocol_naming(project))
    checks.append(_check_rtl_comment_headers(project))
    checks.extend(_check_design_doc(project, ["requirements", "rtl", "uvm"]))
    checks.extend(_check_loop2_uvm_policy(project))
    regression_rel = _evidence_str(evidence, "reports", "regression", "05_Output/reports/loop2/loop2_uvm_regression_report.md")
    exit_rel = _evidence_str(evidence, "reports", "exit", "05_Output/reports/loop2/loop2_exit_report.md")
    coverage_rel = _evidence_str(evidence, "reports", "coverage", "05_Output/reports/loop2/coverage_index.md")
    database_rel = _evidence_str(evidence, "artifacts", "binding_database", "03_Loop2_UVM_Verify/_runtime/loop2_bindings.sqlite")
    checks.extend(_path_checks(
        project,
        [
            regression_rel,
            exit_rel,
            coverage_rel,
            database_rel,
            "01_DocParse/trace_matrix/req_to_test.yaml",
        ],
    ))
    checks.extend(_check_skill_policy_freshness(project, "03_Loop2_UVM_Verify", _files(project, [regression_rel, exit_rel, coverage_rel, database_rel])))
    regression = _read(_project_path(project, regression_rel))
    exit_report = _read(_project_path(project, exit_rel))
    coverage = _read(_project_path(project, coverage_rel))
    text = regression + "\n" + exit_report
    checks.append(_contains_any("loop2_regression_pass", text, _evidence_list(evidence, "required_markers", "regression_pass_any", ["PASS"])))
    checks.append(_contains_any("loop2_scoreboard_pass", text, _evidence_list(evidence, "required_markers", "scoreboard_pass_any", ["SCOREBOARD_PASS", "Scoreboard | PASS", "scoreboard | PASS"])))
    checks.append(_zero_count_check("loop2_zero_uvm_error", text, _evidence_str(evidence, "count_labels", "uvm_error", "UVM_ERROR")))
    checks.append(_zero_count_check("loop2_zero_uvm_fatal", text, _evidence_str(evidence, "count_labels", "uvm_fatal", "UVM_FATAL")))
    checks.append(_contains_any("loop2_assertion_no_failure", exit_report, _evidence_list(evidence, "required_markers", "assertion_pass_any", ["Assertions | PASS"])))
    checks.append(_coverage_check("loop2_functional_coverage", coverage, _evidence_str(evidence, "coverage_patterns", "functional", r"legal_scenario_cg=([0-9.]+)"), _threshold(project, level, "functional")))
    checks.append(_coverage_check("loop2_code_statement_coverage", coverage, _evidence_str(evidence, "coverage_patterns", "code_statement", r"Aggregate \|\s*([0-9.]+)%"), _threshold(project, level, "code")))
    checks.append(_loop2_transaction_count_check(project, text + "\n" + coverage, evidence))
    checks.append(_loop2_coverage_triage_check(project, coverage))
    checks.append(_loop2_bound_assertion_check(project))
    checks.append(_loop2_functional_coverage_sampling_check(project))
    checks.append(_loop2_stimulus_breadth_check(project, level))
    checks.append(_check_bug_tracking(project, "03_Loop2_UVM_Verify/bug_tracking"))
    return checks


def _check_loop3(project: Path, level: str) -> list[GateCheck]:
    evidence = _node_evidence(project, "04_Loop3_FPGA_Prototype")
    bitstream_glob = _evidence_str(evidence, "globs", "bitstreams", "05_Output/fpga/vivado/bitstream/*.bit")
    bitstreams = _glob_project_files(project, bitstream_glob)
    bitstream_rels = [_rel(project, path) for path in bitstreams]
    database_preflight_rel = _evidence_str(evidence, "reports", "database_preflight", "05_Output/reports/loop3/preflight/database_preflight.md")
    prototype_plan_rel = _evidence_str(evidence, "reports", "prototype_plan_check", "05_Output/reports/loop3/preflight/prototype_plan_check.md")
    timing_rel = _evidence_str(evidence, "reports", "timing", "05_Output/fpga/vivado/reports/post_impl_timing_summary.rpt")
    drc_rel = _evidence_str(evidence, "reports", "drc", "05_Output/fpga/vivado/reports/post_impl_drc.rpt")
    serial_rel = _evidence_str(evidence, "reports", "serial", "05_Output/reports/loop3/serial/latest_serial_text.log")
    serial_validation_rel = _evidence_str(evidence, "reports", "serial_validation", "05_Output/reports/loop3/serial/latest_serial_validation_report.md")
    checks = _check_prerequisite_gate(project, "03_Loop2_UVM_Verify", "Loop2 must pass before Loop3 starts")
    checks.extend(_check_design_doc(project, ["requirements", "rtl", "uvm", "fpga"]))
    checks.extend(_path_checks(
        project,
        [
            database_preflight_rel,
            prototype_plan_rel,
            timing_rel,
            drc_rel,
            serial_rel,
            serial_validation_rel,
        ],
    ))
    checks.append(
        GateCheck(
            "loop3_bitstream_available",
            "PASS" if bitstream_rels else "FAIL",
            ", ".join(bitstream_rels) if bitstream_rels else "no .bit file under 05_Output/fpga/vivado/bitstream",
        )
    )
    preflight = _read(_project_path(project, database_preflight_rel))
    plan = _read(_project_path(project, prototype_plan_rel))
    timing = _read(_project_path(project, timing_rel))
    drc = _read(_project_path(project, drc_rel))
    serial_path = _project_path(project, serial_rel)
    serial_validation_path = _project_path(project, serial_validation_rel)
    serial_text = _read(serial_path)
    serial_validation = _read(serial_validation_path)
    checks.append(_contains_any("loop3_database_preflight_pass", preflight, _evidence_list(evidence, "required_markers", "database_preflight_pass_any", ["result: PASS"])))
    checks.append(_contains_any("loop3_prototype_plan_pass", plan, _evidence_list(evidence, "required_markers", "prototype_plan_pass_any", ["result: PASS"])))
    checks.extend(_loop3_timing_checks(timing))
    checks.append(_loop3_serial_echo_check(serial_validation, serial_text))
    checks.append(_loop3_database_ug_flow_check(preflight, _read(project / "05_Output" / "fpga" / "vivado" / "reports" / "pure_pl_uart_led_proto_run.md")))
    if level == "release":
        checks.append(_loop3_release_warning_check(project, "loop3_drc_release_clean", drc, "vivado_drc", _evidence_list(evidence, "release_forbidden_markers", "drc", [" Warning", "Warnings", "Checks found: 1"])))
        checks.append(_loop3_release_warning_check(project, "loop3_timing_methodology_release_clean", timing, "timing_methodology", _evidence_list(evidence, "release_forbidden_markers", "timing", ["TIMING-18", "Missing input or output delay", "no_input_delay", "no_output_delay"])))
    else:
        checks.append(GateCheck("loop3_warning_policy", "PASS", "develop gate allows documented Vivado warnings; release gate is strict"))
    return checks


def _loop3_serial_echo_check(serial_validation: str, serial_text: str) -> GateCheck:
    serial_text = serial_text.lstrip("\ufeff").strip()
    tx_match = re.search(r"^-\s*TX\[[^\]]+\]\s*[：:]\s*(.+?)\s*$", serial_validation, flags=re.MULTILINE)
    rx_match = re.search(r"^-\s*RX\[[^\]]+\]\s*[：:]\s*(.+?)\s*$", serial_validation, flags=re.MULTILINE)
    result_pass = re.search(r"^-\s*result:\s*PASS\s*$", serial_validation, flags=re.MULTILINE)
    if not tx_match or not rx_match or not result_pass:
        return GateCheck("loop3_serial_echo", "FAIL", "serial validation must contain TX[time], RX[time], and result: PASS")
    tx_payload = tx_match.group(1).strip()
    rx_payload = rx_match.group(1).strip()
    if tx_payload != rx_payload:
        return GateCheck("loop3_serial_echo", "FAIL", f"TX/RX payload mismatch: tx={tx_payload!r}, rx={rx_payload!r}")
    raw_match = re.search(r"^RX\[[^\]]+\]\s*[：:]\s*(.+?)\s*$", serial_text.strip(), flags=re.MULTILINE)
    if not raw_match:
        return GateCheck("loop3_serial_echo", "FAIL", "latest_serial_text.log must contain RX[time]：payload")
    raw_payload = raw_match.group(1).strip()
    if raw_payload != rx_payload:
        return GateCheck("loop3_serial_echo", "FAIL", f"raw RX log payload mismatch: log={raw_payload!r}, report={rx_payload!r}")
    return GateCheck("loop3_serial_echo", "PASS", f"TX/RX payloads match and raw RX log is timestamped: {rx_payload}")


def _loop3_timing_checks(timing: str) -> list[GateCheck]:
    if "All user specified timing constraints are met." not in timing:
        detail = "Vivado timing report does not state that all user specified timing constraints are met"
        return [
            GateCheck("loop3_timing_setup_met", "FAIL", detail),
            GateCheck("loop3_timing_hold_met", "FAIL", detail),
        ]
    summary = _loop3_timing_summary_values(timing)
    if not summary:
        detail = "Vivado timing summary table could not be parsed"
        return [
            GateCheck("loop3_timing_setup_met", "FAIL", detail),
            GateCheck("loop3_timing_hold_met", "FAIL", detail),
        ]
    wns, tns_fail, whs, ths_fail = summary
    setup_ok = wns >= 0.0 and tns_fail == 0
    hold_ok = whs >= 0.0 and ths_fail == 0
    return [
        GateCheck("loop3_timing_setup_met", "PASS" if setup_ok else "FAIL", f"WNS={wns}, TNS failing endpoints={tns_fail}"),
        GateCheck("loop3_timing_hold_met", "PASS" if hold_ok else "FAIL", f"WHS={whs}, THS failing endpoints={ths_fail}"),
    ]


def _loop3_timing_summary_values(timing: str) -> tuple[float, int, float, int] | None:
    header_seen = False
    for line in timing.splitlines():
        if "WNS(ns)" in line and "TNS Failing Endpoints" in line and "WHS(ns)" in line:
            header_seen = True
            continue
        if not header_seen:
            continue
        values = line.split()
        if len(values) < 12:
            continue
        try:
            wns = float(values[0])
            tns_fail = int(values[2])
            whs = float(values[4])
            ths_fail = int(values[6])
        except ValueError:
            continue
        return wns, tns_fail, whs, ths_fail
    return None


def _loop3_database_ug_flow_check(preflight: str, run_report: str) -> GateCheck:
    required = [
        "## Hardware Resources",
        "## Vivado Tcl Commands",
        "result: PASS",
        "## Database and UG Provenance",
        "ug_flow_guard: PASS",
        "vivado_tcl_source: local software UG/Tcl database",
    ]
    missing = [marker for marker in required[:3] if marker not in preflight]
    missing.extend(marker for marker in required[3:] if marker not in run_report)
    if missing:
        return GateCheck("loop3_database_ug_flow", "FAIL", "missing database/UG provenance marker(s): " + ", ".join(missing))
    return GateCheck("loop3_database_ug_flow", "PASS", "prototype Tcl run is guarded by database preflight and local UG/Tcl command evidence")


def _loop3_release_warning_check(project: Path, name: str, report: str, waiver_section: str, forbidden: list[str]) -> GateCheck:
    hits = [marker for marker in forbidden if marker in report]
    if not hits:
        return GateCheck(name, "PASS", "no release-blocking warning marker found")
    waiver_ids = _loop3_release_waiver_ids(project, waiver_section)
    if not waiver_ids:
        return GateCheck(name, "FAIL", "release gate blocks warning marker(s): " + ", ".join(hits))
    if waiver_section == "vivado_drc":
        report_rule_ids = _vivado_drc_warning_rule_ids(report)
        unwaived_rules = sorted(rule for rule in report_rule_ids if rule not in waiver_ids)
        if unwaived_rules:
            return GateCheck(name, "FAIL", "release gate blocks unwaived DRC rule(s): " + ", ".join(unwaived_rules))
        return GateCheck(name, "PASS", f"DRC warning rule(s) documented by prototype release waiver(s): {', '.join(sorted(report_rule_ids))}")
    unwaived = [marker for marker in hits if not _loop3_marker_is_waived(marker, report, waiver_ids)]
    if unwaived:
        return GateCheck(name, "FAIL", "release gate blocks unwaived warning marker(s): " + ", ".join(unwaived))
    return GateCheck(name, "PASS", f"warning marker(s) documented by prototype release waiver(s): {', '.join(sorted(waiver_ids))}")


def _vivado_drc_warning_rule_ids(report: str) -> set[str]:
    ids: set[str] = set()
    for match in re.finditer(r"^\|\s*([A-Z]+[A-Z0-9-]*\d+)\s*\|\s*Warning\s*\|", report, flags=re.MULTILINE):
        ids.add(match.group(1))
    for match in re.finditer(r"^([A-Z]+[A-Z0-9-]*\d+)#\d+\s+Warning\b", report, flags=re.MULTILINE):
        ids.add(match.group(1))
    return ids


def _loop3_release_waiver_ids(project: Path, section: str) -> set[str]:
    plan = project / "04_Loop3_FPGA_Prototype" / "board_tests" / "prototype_plan.yaml"
    try:
        data = load_yaml(plan)
    except Exception:
        return set()
    waivers = data.get("release_waivers", {}) if isinstance(data, dict) else {}
    items = waivers.get(section, []) if isinstance(waivers, dict) else []
    ids: set[str] = set()
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and item.get("id"):
                ids.add(str(item.get("id")))
            elif isinstance(item, str):
                ids.add(item)
    return ids


def _loop3_marker_is_waived(marker: str, report: str, waiver_ids: set[str]) -> bool:
    if marker in {" Warning", "Warnings", "Checks found: 1"}:
        return all(waiver_id in report for waiver_id in waiver_ids)
    if marker in waiver_ids:
        return True
    if marker == "Missing input or output delay":
        return {"no_input_delay", "no_output_delay"}.issubset(waiver_ids)
    return any(waiver_id in report for waiver_id in waiver_ids)


def _check_final(project: Path, level: str) -> list[GateCheck]:
    evidence = _node_evidence(project, "05_Output")
    manifest_rel = _evidence_str(evidence, "reports", "manifest", "05_Output/manifest.yaml")
    checks = _path_checks(project, [manifest_rel])
    manifest = _read(_project_path(project, manifest_rel))
    for marker in _evidence_list(evidence, "required_markers", "manifest", ["loop1_gate: PASS", "loop2_gate: PASS", "loop3_gate: PASS"]):
        checks.append(_contains(f"manifest_{marker.split(':')[0]}", manifest, [marker]))
    for node in ["02_Loop1_RTL_TB", "03_Loop2_UVM_Verify", "04_Loop3_FPGA_Prototype"]:
        manifest_path = _latest_gate_manifest(project, node, level if level == "release" else None)
        if manifest_path:
            checks.append(GateCheck(f"{node}_gate_manifest", "PASS", str(manifest_path.relative_to(project))))
        else:
            expected = f"{level} " if level == "release" else ""
            checks.append(GateCheck(f"{node}_gate_manifest", "FAIL", f"missing passed {expected}gate manifest for {node}; run run-gate first"))
    if level == "release":
        checks.append(GateCheck("final_level", "PASS", "release final gate requested"))
    return checks


def _path_checks(project: Path, rel_paths: list[str]) -> list[GateCheck]:
    checks = []
    for rel in rel_paths:
        path = _project_path(project, rel)
        status = "PASS" if path.exists() else "FAIL"
        detail = "exists" if path.exists() else "missing"
        checks.append(GateCheck(f"path:{rel}", status, detail))
    return checks


def _check_prerequisite_gate(project: Path, node: str, detail: str) -> list[GateCheck]:
    manifest = _latest_gate_manifest(project, node)
    if not manifest:
        return [GateCheck(f"prerequisite:{node}", "FAIL", f"{detail}; missing passed gate manifest for {node}")]
    return [GateCheck(f"prerequisite:{node}", "PASS", str(manifest.relative_to(project)))]


def _check_loop2_uvm_policy(project: Path) -> list[GateCheck]:
    node_cfg = _node_config(project, "03_Loop2_UVM_Verify")
    policy = node_cfg.get("uvm_policy", {})
    if not isinstance(policy, dict):
        return [GateCheck("loop2_uvm_policy", "FAIL", "uvm_policy must be configured")]

    checks: list[GateCheck] = []
    if policy.get("baseline_artifacts_transient", True):
        legacy_entry_report = project / "05_Output" / "reports" / "loop2" / "loop2_uvm_baseline_report.md"
        if legacy_entry_report.exists():
            checks.append(
                GateCheck(
                    "loop2_no_entry_check_final_report",
                    "FAIL",
                    "entry-check evidence remains as a final Loop2 report; keep final evidence in regression, coverage, and exit reports only",
                )
            )
        else:
            checks.append(
                GateCheck(
                    "loop2_no_entry_check_final_report",
                    "PASS",
                    "entry-check evidence is transient and not part of final Loop2 reports",
                )
            )

    if policy.get("template_artifacts_forbidden", True):
        uvm_root = project / "05_Output" / "uvm"
        templates = sorted(uvm_root.rglob("*.template")) if uvm_root.exists() else []
        if templates:
            rels = ", ".join(_rel(project, path) for path in templates[:8])
            checks.append(GateCheck("loop2_no_template_artifacts", "FAIL", f"template artifact(s) remain under 05_Output/uvm: {rels}"))
        else:
            checks.append(GateCheck("loop2_no_template_artifacts", "PASS", "no .template files under 05_Output/uvm"))

    if policy.get("full_uvm_required", True):
        required_files = [str(item) for item in policy.get("required_real_files", []) if str(item)]
        missing_files = [rel for rel in required_files if not _project_path(project, rel).is_file()]
        if missing_files:
            checks.append(GateCheck("loop2_full_uvm_required_files", "FAIL", "missing real UVM file(s): " + ", ".join(missing_files[:8])))
        else:
            checks.append(GateCheck("loop2_full_uvm_required_files", "PASS", f"{len(required_files)} required real UVM file(s) present"))

        missing_globs = []
        for pattern in [str(item) for item in policy.get("required_real_globs", []) if str(item)]:
            if not _glob_project_files(project, pattern):
                missing_globs.append(pattern)
        if missing_globs:
            checks.append(GateCheck("loop2_full_uvm_required_globs", "FAIL", "missing UVM artifact pattern(s): " + ", ".join(missing_globs[:8])))
        else:
            checks.append(GateCheck("loop2_full_uvm_required_globs", "PASS", "all required UVM artifact patterns matched"))

    forbidden_markers = [str(item) for item in policy.get("forbidden_markers", []) if str(item)]
    if forbidden_markers:
        hits: list[str] = []
        uvm_root = project / "05_Output" / "uvm"
        if uvm_root.exists():
            for path in sorted(uvm_root.rglob("*")):
                if not path.is_file() or path.suffix.lower() not in {".sv", ".svh"}:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                for marker in forbidden_markers:
                    if marker in text:
                        hits.append(f"{_rel(project, path)} contains {marker}")
                        break
        if hits:
            checks.append(GateCheck("loop2_no_template_placeholders", "FAIL", "; ".join(hits[:8])))
        else:
            checks.append(GateCheck("loop2_no_template_placeholders", "PASS", "no forbidden template placeholder markers in real UVM files"))

    return checks


def _contains(name: str, text: str, markers: list[str]) -> GateCheck:
    missing = [marker for marker in markers if marker not in text]
    if missing:
        return GateCheck(name, "FAIL", "missing marker(s): " + ", ".join(missing))
    return GateCheck(name, "PASS", "required marker(s) found")


def _contains_any(name: str, text: str, markers: list[str]) -> GateCheck:
    for marker in markers:
        if marker in text:
            return GateCheck(name, "PASS", f"marker found: {marker}")
    return GateCheck(name, "FAIL", "missing any marker: " + ", ".join(markers))


def _zero_count_check(name: str, text: str, label: str) -> GateCheck:
    patterns = [
        rf"{re.escape(label)}\s*\|\s*0\b",
        rf"{re.escape(label)}\s*:\s*0\b",
        rf"{re.escape(label)}\s+0\b",
    ]
    for pattern in patterns:
        if re.search(pattern, text):
            return GateCheck(name, "PASS", f"{label} count is zero")
    return GateCheck(name, "FAIL", f"{label} zero-count marker not found")


def _coverage_check(name: str, text: str, pattern: str, threshold: float | None) -> GateCheck:
    match = re.search(pattern, text)
    if not match:
        return GateCheck(name, "FAIL", f"coverage marker not found: {pattern}")
    value = float(match.group(1))
    if threshold is None:
        return GateCheck(name, "PASS", f"{value:.2f}% reported; no threshold for this gate level")
    if value < threshold:
        return GateCheck(name, "FAIL", f"{value:.2f}% below threshold {threshold:.2f}%")
    return GateCheck(name, "PASS", f"{value:.2f}% >= {threshold:.2f}%")


def _loop2_transaction_count_check(project: Path, text: str, evidence: dict[str, Any]) -> GateCheck:
    policy = _node_config(project, "03_Loop2_UVM_Verify").get("uvm_policy", {})
    min_count = 64
    if isinstance(policy, dict):
        try:
            min_count = int(policy.get("min_checked_transactions", min_count))
        except (TypeError, ValueError):
            return GateCheck("loop2_checked_transaction_count", "FAIL", "uvm_policy.min_checked_transactions must be an integer")
    pattern = _evidence_str(evidence, "metric_patterns", "checked_transactions", r"transactions_total:\s*([0-9]+)")
    match = re.search(pattern, text)
    if not match:
        return GateCheck("loop2_checked_transaction_count", "FAIL", f"transaction count marker not found: {pattern}")
    count = int(match.group(1))
    if count < min_count:
        return GateCheck("loop2_checked_transaction_count", "FAIL", f"{count} checked transaction(s) below minimum {min_count}")
    return GateCheck("loop2_checked_transaction_count", "PASS", f"{count} checked transaction(s) >= {min_count}")


def _loop2_coverage_triage_check(project: Path, coverage: str) -> GateCheck:
    policy = _loop2_policy(project)
    if not _policy_bool(policy, "coverage_triage_required", True):
        return GateCheck("loop2_coverage_triage_closed", "PASS", "coverage triage closure not required by policy")
    unresolved = [line for line in coverage.splitlines() if "Classify as " in line]
    if not unresolved:
        return GateCheck("loop2_coverage_triage_closed", "PASS", "no unresolved coverage triage rows found")
    if _coverage_triage_has_closure_record(project):
        return GateCheck("loop2_coverage_triage_closed", "PASS", "coverage triage closure record or waiver exists")
    return GateCheck(
        "loop2_coverage_triage_closed",
        "FAIL",
        f"{len(unresolved)} coverage triage row(s) still ask for classification/waiver before Loop2 closure",
    )


def _loop2_bound_assertion_check(project: Path) -> GateCheck:
    policy = _loop2_policy(project)
    if not _policy_bool(policy, "bound_assertions_required", True):
        return GateCheck("loop2_bound_assertions_present", "PASS", "bound assertions not required by policy")
    root = project / "05_Output" / "uvm" / "assertions"
    files = sorted(path for path in root.glob("*") if path.is_file() and path.suffix.lower() in {".sv", ".svh"} and path.suffix.lower() != ".template")
    if not files:
        return GateCheck("loop2_bound_assertions_present", "FAIL", "no real SVA/bind files under 05_Output/uvm/assertions")
    hits = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"\b(bind|property|assert\s+property)\b", text):
            hits.append(_rel(project, path))
    if hits:
        return GateCheck("loop2_bound_assertions_present", "PASS", "assertion source present: " + ", ".join(hits[:4]))
    return GateCheck("loop2_bound_assertions_present", "FAIL", "assertion files exist but no bind/property/assert property syntax was found")


def _loop2_functional_coverage_sampling_check(project: Path) -> GateCheck:
    policy = _loop2_policy(project)
    if not _policy_bool(policy, "monitor_sampled_functional_coverage_required", True):
        return GateCheck("loop2_functional_coverage_observed", "PASS", "monitor-sampled functional coverage not required by policy")
    tests = project / "05_Output" / "uvm" / "tests" / "tests.svh"
    text = _read(tests)
    if re.search(r"\bsample_scenario\s*\(", text):
        return GateCheck(
            "loop2_functional_coverage_observed",
            "FAIL",
            "tests.svh calls sample_scenario directly; functional coverage must be sampled from observed monitor/scoreboard transactions",
        )
    coverage_text = _read(project / "05_Output" / "uvm" / "cov" / "coverage.sv")
    if re.search(r"\bwrite\s*\(|uvm_subscriber|analysis_export|analysis_imp", coverage_text):
        return GateCheck("loop2_functional_coverage_observed", "PASS", "coverage collector appears connected to observed analysis traffic")
    return GateCheck("loop2_functional_coverage_observed", "FAIL", "no monitor/scoreboard-sampled functional coverage path detected")


def _loop2_stimulus_breadth_check(project: Path, level: str) -> GateCheck:
    policy = _loop2_policy(project)
    if not _policy_bool(policy, "stimulus_breadth_required", True):
        return GateCheck("loop2_stimulus_breadth", "PASS", "stimulus breadth check not required by policy")
    if level == "debug":
        return GateCheck("loop2_stimulus_breadth", "PASS", "debug gate does not require full breadth stimulus")
    patterns = {
        "reset_mid_frame": [r"reset_mid_frame", r"mid_frame_reset", r"reset.*mid.*frame"],
        "bad_stop_bit": [r"bad_stop", r"stop_bit_error", r"framing_error"],
        "glitch": [r"glitch", r"noise", r"short_pulse"],
        "overflow": [r"overflow", r"fifo_full", r"pending_full"],
        "baud_div_434": [r"baud_div_434", r"BAUD_DIV\s*[=:(]\s*434\b", r"\b434\b.*baud"],
    }
    configured = policy.get("required_stimulus_scenarios")
    names = [str(item) for item in configured if str(item) in patterns] if isinstance(configured, list) else list(patterns.keys())
    haystack = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in _source_files_by_suffix(project, {"05_Output/uvm": {".sv", ".svh"}, "03_Loop2_UVM_Verify/sim": {".do"}})
    )
    missing = [name for name in names if not any(re.search(pattern, haystack, flags=re.IGNORECASE | re.DOTALL) for pattern in patterns[name])]
    if missing:
        return GateCheck("loop2_stimulus_breadth", "FAIL", "missing required stress stimulus: " + ", ".join(missing))
    return GateCheck("loop2_stimulus_breadth", "PASS", "required stress stimulus patterns found")


def _coverage_triage_has_closure_record(project: Path) -> bool:
    waiver = project / "loop" / "coverage_waiver.json"
    try:
        data = json.loads(waiver.read_text(encoding="utf-8")) if waiver.exists() else {}
    except Exception:
        data = {}
    if isinstance(data, dict):
        waivers = data.get("waivers")
        if isinstance(waivers, list) and waivers:
            return True
    tracking = project / "03_Loop2_UVM_Verify" / "coverage_tracking"
    if tracking.exists():
        for path in tracking.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".md", ".yaml", ".yml", ".json", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            if any(marker in text for marker in ["unreachable-by-spec", "missing legal stimulus", "waiver", "classified"]):
                return True
    return False


def _loop2_policy(project: Path) -> dict[str, Any]:
    policy = _node_config(project, "03_Loop2_UVM_Verify").get("uvm_policy", {})
    return policy if isinstance(policy, dict) else {}


def _policy_bool(policy: dict[str, Any], key: str, default: bool) -> bool:
    value = policy.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


def _threshold(project: Path, level: str, kind: str) -> float | None:
    key_by_kind = {
        "code": "code_coverage_percent",
        "functional": "functional_coverage_percent",
        "requirement": "requirement_coverage_percent",
    }
    fallback = {
        "release": {"code": 90.0, "functional": 90.0, "requirement": 100.0},
        "develop": {"code": 80.0, "functional": 80.0, "requirement": 100.0},
        "debug": {"code": None, "functional": None, "requirement": None},
    }
    try:
        levels = load_yaml(_find_workspace_root(project) / "config" / "global" / "gates" / "gate_levels.yaml").get("levels", {})
        threshold = levels.get(level, {}).get("thresholds", {}).get(key_by_kind[kind])
        if threshold is None:
            return None
        return float(threshold)
    except Exception:
        return fallback.get(level, fallback["develop"]).get(kind)


def _release_warning_check(name: str, text: str, forbidden: list[str]) -> GateCheck:
    hits = [item for item in forbidden if item in text]
    if hits:
        return GateCheck(name, "FAIL", "release gate blocks warning marker(s): " + ", ".join(hits))
    return GateCheck(name, "PASS", "no blocked release warning markers found")


def _check_bug_tracking(project: Path, rel_dir: str) -> GateCheck:
    path = project / rel_dir
    if not path.exists():
        return GateCheck("bug_closure_pass", "PASS", "no bug tracking directory for this node")
    blockers: list[str] = []
    for bug_file in path.rglob("*"):
        if not bug_file.is_file() or bug_file.suffix.lower() not in {".md", ".yaml", ".yml", ".json", ".txt"}:
            continue
        text = bug_file.read_text(encoding="utf-8", errors="ignore").lower()
        if ("critical" in text or "major" in text) and "closed" not in text and "resolved" not in text:
            blockers.append(str(bug_file.relative_to(project)))
    if blockers:
        return GateCheck("bug_closure_pass", "FAIL", "open critical/major bug candidate(s): " + ", ".join(blockers))
    return GateCheck("bug_closure_pass", "PASS", "no open critical/major bug candidates found")


def _check_design_doc(project: Path, sections: list[str]) -> list[GateCheck]:
    result = check_design_document(project, sections=sections)
    checks = [
        GateCheck(
            "design_doc_sync",
            "PASS" if result.ok else "FAIL",
            f"{design_doc_report_rel()} synchronized" if result.ok else "; ".join(result.errors),
        )
    ]
    for warning in result.warnings:
        checks.append(GateCheck("design_doc_warning", "PASS", warning))
    return checks


def _check_evidence_freshness(project: Path, source_paths: list[Path], evidence_paths: list[Path]) -> list[GateCheck]:
    existing_sources = [path for path in source_paths if path.exists()]
    existing_evidence = [path for path in evidence_paths if path.exists()]
    if not existing_sources or not existing_evidence:
        return [GateCheck("artifact_freshness", "PASS", "freshness skipped; no comparable source/evidence set")]
    newest_source = max(path.stat().st_mtime for path in existing_sources)
    oldest_evidence = min(path.stat().st_mtime for path in existing_evidence)
    if newest_source > oldest_evidence:
        return [
            GateCheck(
                "artifact_freshness",
                "FAIL",
                "source file is newer than one or more evidence reports; rerun the owning checks",
            )
        ]
    return [GateCheck("artifact_freshness", "PASS", "evidence reports are newer than checked source files")]


def _check_manifest_drift(project: Path, node: str, source_paths: list[Path], change_id: str | None) -> list[GateCheck]:
    manifest = _latest_gate_manifest(project, node)
    if not manifest or not source_paths:
        return [GateCheck("artifact_hash_drift", "PASS", "no previous gate manifest to compare")]
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception as exc:
        return [GateCheck("artifact_hash_drift", "FAIL", f"cannot read previous gate manifest {manifest}: {exc}")]

    previous = {item.get("path"): item.get("sha256") for item in data.get("sources", []) if isinstance(item, dict)}
    previous_paths = {str(path) for path in previous if path}
    current_paths = {_rel(project, path) for path in source_paths if path.exists() and path.is_file()}
    changed: list[str] = []
    added = sorted(current_paths - previous_paths)
    removed = sorted(rel for rel in previous_paths - current_paths if not _project_path(project, rel).exists())
    changed.extend(added + removed)
    for path in source_paths:
        if not path.exists() or not path.is_file():
            continue
        rel = _rel(project, path)
        old_hash = previous.get(rel)
        if old_hash and old_hash != hashlib.sha256(path.read_bytes()).hexdigest():
            changed.append(rel)
    if not changed:
        return [GateCheck("artifact_hash_drift", "PASS", f"source hashes match previous gate manifest {manifest.name}")]
    if change_id:
        return [GateCheck("artifact_hash_drift", "PASS", f"{len(changed)} source hash change(s) are bound to {change_id}")]
    return [
        GateCheck(
            "artifact_hash_drift",
            "FAIL",
            f"{len(changed)} source hash change(s) since previous gate; open/approve a change request and pass --change-id",
        )
    ]


def _check_skill_manifest_drift(project: Path, node: str, change_id: str | None) -> list[GateCheck]:
    current = _skill_hash_entries(project, node)
    if not current:
        return []
    manifest = _latest_gate_manifest(project, node)
    if not manifest:
        return [GateCheck("skill_policy_hash_drift", "PASS", "no previous gate manifest to compare")]
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception as exc:
        return [GateCheck("skill_policy_hash_drift", "FAIL", f"cannot read previous gate manifest {manifest}: {exc}")]
    previous_items = data.get("skill_constraints", [])
    if not isinstance(previous_items, list) or not previous_items:
        return [GateCheck("skill_policy_hash_drift", "PASS", "previous gate manifest did not record skill constraints")]
    previous = {item.get("skill"): item.get("sha256") for item in previous_items if isinstance(item, dict)}
    changed = [item["skill"] for item in current if previous.get(item["skill"]) != item["sha256"]]
    if not changed:
        return [GateCheck("skill_policy_hash_drift", "PASS", f"skill hashes match previous gate manifest {manifest.name}")]
    if change_id:
        return [GateCheck("skill_policy_hash_drift", "PASS", f"{len(changed)} skill hash change(s) are bound to {change_id}")]
    return [GateCheck("skill_policy_hash_drift", "FAIL", "skill constraint hash changed since previous gate: " + ", ".join(changed))]


def _gate_paths(project: Path, node: str) -> tuple[list[Path], list[Path]]:
    if node == "00_SPEC":
        return (_files(project, ["00_SPEC/raw_docs", "00_SPEC/requirements"]), [])
    if node == "01_DocParse":
        evidence_rels = [rel for rel in required_frontend_paths() if rel.startswith("01_DocParse/")]
        evidence_rels.append("05_Output/reports/docparse/requirements_frontend_report.md")
        evidence_rels.extend([design_doc_report_rel(), design_doc_manifest_rel()])
        return (_requirement_source_files(project), _files(project, evidence_rels))
    if node == "02_Loop1_RTL_TB":
        evidence = _node_evidence(project, node)
        return (
            _source_files_by_suffix(
                project,
                {
                    "05_Output/rtl": {".v"},
                    "05_Output/tb": {".v"},
                    "01_DocParse/structured_spec": {".yaml", ".yml", ".json"},
                    "01_DocParse/trace_matrix": {".yaml", ".yml", ".json"},
                },
            ),
            _files(project, _evidence_report_paths(evidence, ["05_Output/reports/loop1/loop1_rtl_tb_run_report.md", "05_Output/reports/loop1/loop1_exit_report.md"])),
        )
    if node == "03_Loop2_UVM_Verify":
        evidence = _node_evidence(project, node)
        return (
            _source_files_by_suffix(
                project,
                {
                    "05_Output/rtl": {".v"},
                    "05_Output/uvm": {".sv", ".svh"},
                    "01_DocParse/structured_spec": {".yaml", ".yml", ".json"},
                    "01_DocParse/trace_matrix": {".yaml", ".yml", ".json"},
                },
            ),
            _files(
                project,
                _evidence_report_paths(
                    evidence,
                    [
                    "05_Output/reports/loop2/loop2_uvm_regression_report.md",
                    "05_Output/reports/loop2/loop2_exit_report.md",
                    "05_Output/reports/loop2/coverage_index.md",
                    ],
                )
                + [
                    "03_Loop2_UVM_Verify/_runtime/loop2_bindings.sqlite",
                ],
            ),
        )
    if node == "04_Loop3_FPGA_Prototype":
        evidence = _node_evidence(project, node)
        bitstream_glob = _evidence_str(evidence, "globs", "bitstreams", "05_Output/fpga/vivado/bitstream/*.bit")
        return (
            _files(
                project,
                [
                    "05_Output/rtl",
                    "05_Output/fpga/vivado/constraints",
                    "05_Output/fpga/vivado/scripts",
                    "04_Loop3_FPGA_Prototype/board_tests",
                    "04_Loop3_FPGA_Prototype/scripts",
                ],
            ),
            _files(project, _evidence_report_paths(evidence, [
                "05_Output/reports/loop3/preflight/database_preflight.md",
                "05_Output/reports/loop3/preflight/prototype_plan_check.md",
                "05_Output/fpga/vivado/reports/post_impl_timing_summary.rpt",
                "05_Output/fpga/vivado/reports/post_impl_drc.rpt",
                "05_Output/reports/loop3/serial/latest_serial_text.log",
                "05_Output/reports/loop3/serial/latest_serial_validation_report.md",
            ])) + _glob_project_files(project, bitstream_glob),
        )
    if node == "05_Output":
        return ([], [])
    return (_files(project, ["00_SPEC", "01_DocParse"]), _files(project, ["01_DocParse"]))


def _source_files_by_suffix(project: Path, roots: dict[str, set[str]]) -> list[Path]:
    paths: list[Path] = []
    for rel, suffixes in roots.items():
        root = _project_path(project, rel)
        if root.is_file() and root.suffix in suffixes:
            paths.append(root)
        elif root.is_dir():
            paths.extend(path for path in root.rglob("*") if path.is_file() and path.suffix in suffixes)
    return paths


def _files(project: Path, rels: list[str]) -> list[Path]:
    paths: list[Path] = []
    for rel in rels:
        path = _project_path(project, rel)
        if path.is_file():
            paths.append(path)
        elif path.is_dir():
            paths.extend(item for item in path.rglob("*") if item.is_file() and "_runtime" not in item.parts)
    return sorted(set(paths))


def _requirement_source_files(project: Path) -> list[Path]:
    root = project / "00_SPEC" / "requirements"
    if not root.is_dir():
        return []
    return sorted(
        path
        for path in root.glob("*")
        if path.is_file() and path.name not in GENERATED_REQUIREMENT_FILES
    )


def _project_config(project: Path) -> dict[str, Any]:
    try:
        data = load_project(project).data
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _node_evidence(project: Path, node: str) -> dict[str, Any]:
    node_cfg = _node_config(project, node)
    evidence = node_cfg.get("evidence", {})
    return evidence if isinstance(evidence, dict) else {}


def _node_config(project: Path, node: str) -> dict[str, Any]:
    nodes = _project_config(project).get("nodes", {})
    if not isinstance(nodes, dict):
        return {}
    node_cfg = nodes.get(node, {})
    if not isinstance(node_cfg, dict):
        return {}
    return node_cfg


def _check_source_policy(project: Path, node: str) -> list[GateCheck]:
    node_cfg = _node_config(project, node)
    policy = node_cfg.get("source_policy", {})
    if not isinstance(policy, dict) or not policy:
        return [GateCheck("source_policy", "PASS", "no source policy configured")]

    checks: list[GateCheck] = []
    for section_name, section in policy.items():
        if not isinstance(section, dict):
            checks.append(GateCheck(f"source_policy:{section_name}", "FAIL", "source policy section must be a mapping"))
            continue
        root_rel = str(section.get("root") or "").strip()
        if not root_rel:
            checks.append(GateCheck(f"source_policy:{section_name}", "FAIL", "root is required"))
            continue
        root = _project_path(project, root_rel)
        allowed = _extension_set(section.get("allowed_extensions", []))
        forbidden = _extension_set(section.get("forbidden_extensions", []))
        template_exts = _extension_set(section.get("template_extensions", []))
        if not root.exists():
            checks.append(GateCheck(f"source_policy:{section_name}", "PASS", f"{root_rel} does not exist yet"))
            continue
        files = [path for path in root.rglob("*") if path.is_file()]
        forbidden_hits = [path for path in files if path.suffix.lower() in forbidden]
        if forbidden_hits:
            rels = ", ".join(_rel(project, path) for path in forbidden_hits[:8])
            checks.append(GateCheck(f"source_policy:{section_name}", "FAIL", f"forbidden extension(s) under {root_rel}: {rels}"))
            continue
        hdl_files = [path for path in files if path.suffix.lower() in {".v", ".sv", ".svh"} | template_exts]
        unknown = [path for path in hdl_files if path.suffix.lower() not in allowed and path.suffix.lower() not in template_exts]
        if unknown:
            rels = ", ".join(_rel(project, path) for path in unknown[:8])
            checks.append(GateCheck(f"source_policy:{section_name}", "FAIL", f"extension not allowed by source policy: {rels}"))
            continue
        checks.append(GateCheck(f"source_policy:{section_name}", "PASS", f"{root_rel} follows {section.get('language', 'configured language')} policy"))
    return checks


def _check_official_protocol_naming(project: Path) -> GateCheck:
    """Block direction suffixes on official UART physical boundary names."""

    scan_roots = [
        "00_SPEC/requirements",
        "01_DocParse/architecture",
        "01_DocParse/prototype",
        "05_Output/rtl",
        "05_Output/tb",
        "05_Output/uvm",
    ]
    forbidden = ["uart_rx_i", "uart_tx_o"]
    hits: list[str] = []
    for root in _files(project, scan_roots):
        if not root.exists() or not root.is_file():
            continue
        if root.suffix.lower() not in {".v", ".sv", ".svh", ".yaml", ".yml", ".md"}:
            continue
        text = root.read_text(encoding="utf-8", errors="ignore")
        found = [name for name in forbidden if re.search(rf"\b{re.escape(name)}\b", text)]
        if found:
            hits.append(f"{_rel(project, root)}: {', '.join(found)}")
    if hits:
        return GateCheck("official_protocol_naming", "FAIL", "official UART boundary names must be uart_rx/uart_tx: " + "; ".join(hits[:8]))
    return GateCheck("official_protocol_naming", "PASS", "official UART boundary names use uart_rx/uart_tx")


def _check_rtl_comment_headers(project: Path) -> GateCheck:
    rtl_dir = project / "05_Output" / "rtl"
    if not rtl_dir.exists():
        return GateCheck("rtl_comment_headers", "PASS", "05_Output/rtl does not exist yet")
    missing: list[str] = []
    for path in sorted(rtl_dir.glob("*.v")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "// Module" not in text[:800] or "// Description" not in text[:800] or "// Scope:" not in text[:1200]:
            missing.append(_rel(project, path))
    if missing:
        return GateCheck("rtl_comment_headers", "FAIL", "missing required RTL header comment(s): " + ", ".join(missing[:8]))
    return GateCheck("rtl_comment_headers", "PASS", "RTL files include module description and scope headers")


def _check_skill_policy(project: Path, node: str) -> list[GateCheck]:
    node_cfg = _node_config(project, node)
    policy = node_cfg.get("skill_policy", {})
    if not isinstance(policy, dict) or not policy:
        if node in {"02_Loop1_RTL_TB", "03_Loop2_UVM_Verify"}:
            return [GateCheck("skill_policy", "FAIL", "Loop1/Loop2 require configured skill_policy")]
        return []
    required = policy.get("required_skills", {})
    if not isinstance(required, dict) or not required:
        return [GateCheck("skill_policy", "FAIL", "required_skills must be a non-empty mapping")]

    checks: list[GateCheck] = []
    workspace = _find_workspace_root(project)
    for skill_name, spec in required.items():
        if not isinstance(spec, dict):
            checks.append(GateCheck(f"skill_policy:{skill_name}", "FAIL", "skill entry must be a mapping"))
            continue
        rel = str(spec.get("path") or f"skills/{skill_name}/SKILL.md")
        try:
            path = _workspace_path(workspace, rel)
        except ValueError as exc:
            checks.append(GateCheck(f"skill_policy:{skill_name}", "FAIL", str(exc)))
            continue
        if not path.is_file():
            checks.append(GateCheck(f"skill_policy:{skill_name}", "FAIL", f"missing skill file: {rel}"))
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        markers = spec.get("required_markers", [])
        if not isinstance(markers, list):
            checks.append(GateCheck(f"skill_policy:{skill_name}", "FAIL", "required_markers must be a list"))
            continue
        missing = [str(marker) for marker in markers if str(marker) not in text]
        if missing:
            checks.append(GateCheck(f"skill_policy:{skill_name}", "FAIL", "missing required marker(s): " + ", ".join(missing[:5])))
            continue
        checks.append(GateCheck(f"skill_policy:{skill_name}", "PASS", f"{rel} constraint markers present"))
    return checks


def _check_skill_policy_freshness(project: Path, node: str, evidence_paths: list[Path]) -> list[GateCheck]:
    skill_paths = [item[1] for item in _skill_policy_specs(project, node) if item[1].is_file()]
    existing_evidence = [path for path in evidence_paths if path.exists()]
    if not skill_paths or not existing_evidence:
        return [GateCheck("skill_policy_freshness", "PASS", "freshness skipped; no comparable skill/evidence set")]
    newest_skill = max(path.stat().st_mtime for path in skill_paths)
    oldest_evidence = min(path.stat().st_mtime for path in existing_evidence)
    if newest_skill > oldest_evidence:
        return [GateCheck("skill_policy_freshness", "FAIL", "skill file is newer than one or more evidence reports; rerun the owning Loop evidence")]
    return [GateCheck("skill_policy_freshness", "PASS", "evidence reports are newer than configured skill constraints")]


def _skill_policy_specs(project: Path, node: str) -> list[tuple[str, Path]]:
    node_cfg = _node_config(project, node)
    policy = node_cfg.get("skill_policy", {})
    required = policy.get("required_skills", {}) if isinstance(policy, dict) else {}
    if not isinstance(required, dict):
        return []
    workspace = _find_workspace_root(project)
    specs: list[tuple[str, Path]] = []
    for skill_name, spec in required.items():
        if not isinstance(spec, dict):
            continue
        rel = str(spec.get("path") or f"skills/{skill_name}/SKILL.md")
        try:
            specs.append((str(skill_name), _workspace_path(workspace, rel)))
        except ValueError:
            continue
    return specs


def _skill_hash_entries(project: Path, node: str) -> list[dict[str, Any]]:
    workspace = _find_workspace_root(project)
    entries: list[dict[str, Any]] = []
    for skill_name, path in _skill_policy_specs(project, node):
        if not path.is_file():
            continue
        data = path.read_bytes()
        entries.append(
            {
                "skill": skill_name,
                "path": str(path.resolve().relative_to(workspace)).replace("\\", "/"),
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
                "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
            }
        )
    return entries


def _extension_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).lower() for item in value if str(item).startswith(".")}


def _evidence_str(evidence: dict[str, Any], section: str, key: str, default: str) -> str:
    mapping = evidence.get(section, {})
    if isinstance(mapping, dict):
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return default


def _evidence_list(evidence: dict[str, Any], section: str, key: str, default: list[str]) -> list[str]:
    mapping = evidence.get(section, {})
    if not isinstance(mapping, dict):
        return default
    value = mapping.get(key)
    if isinstance(value, list):
        items = [str(item) for item in value if str(item)]
        return items or default
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return default


def _evidence_report_paths(evidence: dict[str, Any], defaults: list[str]) -> list[str]:
    reports = evidence.get("reports", {})
    if not isinstance(reports, dict):
        return defaults
    paths = [str(path).strip() for path in reports.values() if isinstance(path, str) and path.strip()]
    return paths or defaults


def _project_path(project: Path, rel: str) -> Path:
    path = (project / rel).resolve()
    try:
        path.relative_to(project.resolve())
    except ValueError as exc:
        raise ValueError(f"configured project path escapes project root: {rel}") from exc
    return path


def _workspace_path(workspace: Path, rel: str) -> Path:
    path = (workspace / rel).resolve()
    try:
        path.relative_to(workspace.resolve())
    except ValueError as exc:
        raise ValueError(f"configured workspace path escapes workspace root: {rel}") from exc
    return path


def _glob_project_files(project: Path, pattern: str) -> list[Path]:
    if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
        raise ValueError(f"configured glob must stay inside project: {pattern}")
    return sorted(path for path in project.glob(pattern) if path.is_file())


def _write_gate_report(project: Path, node: str, level: str, ok: bool, checks: list[GateCheck], change_id: str | None) -> Path:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    report_dir = project / "05_Output" / "reports" / "gates"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{node.replace('/', '_')}_{level}_{stamp}.md"
    lines = [
        f"# Gate Report: {node}",
        "",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- project: {project.name}",
        f"- node: {node}",
        f"- level: {level}",
        f"- change_id: {change_id or 'none'}",
        f"- result: {'PASS' if ok else 'FAIL'}",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {_escape_md(check.detail)} |")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if node == "05_Output" and ok:
        final_path = project / "05_Output" / "reports" / "final_audit_report.md"
        final_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def _write_gate_manifest(
    project: Path,
    node: str,
    level: str,
    source_paths: list[Path],
    evidence_paths: list[Path],
    report_path: Path,
    change_id: str | None,
) -> Path:
    manifest_dir = project / "memory" / "recovery" / "rollback_manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    manifest_path = manifest_dir / f"{node}_{level}_{stamp}.json"
    data = {
        "schema_version": 1,
        "project": project.name,
        "node": node,
        "level": level,
        "change_id": change_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "gate_report": _rel(project, report_path),
        "sources": [_hash_entry(project, path) for path in source_paths if path.exists()],
        "evidence": [_hash_entry(project, path) for path in evidence_paths if path.exists()],
        "skill_constraints": _skill_hash_entries(project, node),
    }
    manifest_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def _latest_gate_manifest(project: Path, node: str, level: str | None = None) -> Path | None:
    manifest_dir = project / "memory" / "recovery" / "rollback_manifests"
    pattern = f"{node}_{level}_*.json" if level else f"{node}_*.json"
    matches = sorted(manifest_dir.glob(pattern))
    return matches[-1] if matches else None


def _hash_entry(project: Path, path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": _rel(project, path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
        "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
    }


def _read_change_requests(project: Path, statuses: set[str]) -> list[dict[str, str]]:
    requests_dir = project / "change_control" / "requests"
    items: list[dict[str, str]] = []
    if not requests_dir.exists():
        return items
    for path in requests_dir.glob("CR-*.md"):
        item = _parse_front_matter(path)
        if item.get("status") in statuses:
            item["id"] = item.get("id") or path.stem
            items.append(item)
    return items


def _read_change_request(project: Path, change_id: str) -> dict[str, str] | None:
    path = project / "change_control" / "requests" / f"{change_id}.md"
    if not path.exists():
        return None
    item = _parse_front_matter(path)
    item["id"] = item.get("id") or change_id
    return item


def _parse_front_matter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    data: dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("- ") or ":" not in line:
            continue
        key, value = line[2:].split(":", 1)
        data[key.strip()] = value.strip()
    return data


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _rel(project: Path, path: Path) -> str:
    return str(path.resolve().relative_to(project)).replace("\\", "/")


def _find_workspace_root(path: Path) -> Path:
    for candidate in [path, *path.parents]:
        if (candidate / "config" / "global" / "workspace_config.yaml").exists():
            return candidate
    if path.parent.name == "projects":
        return path.parent.parent
    raise FileNotFoundError(f"could not find workspace config from: {path}")


def _escape_md(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")
