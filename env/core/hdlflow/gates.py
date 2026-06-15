"""Executable project gate checks."""

from __future__ import annotations

import hashlib
import fnmatch
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .change_control import validate_change_bundle
from .config import load_project
from .docgen import check_docset
from .docgen.constants import DOC_DEFINITIONS, DOCSET_MANIFEST_REL, DOCSET_REPORT_REL
from .layout import find_workspace_root, project_memory_path
from .loop1_reports import refresh_loop1_reports
from .loop2_reports import refresh_loop2_reports
from .prototype import refresh_loop3_reports
from .project import require_project_instance
from .reports.constants import (
    COMMAND_SCHEMA,
    LOOP1_REPORT,
    LOOP2_REPORT,
    REPORT_MANIFEST_SCHEMA,
    REPORT_SCHEMA,
    RUN_MANIFEST_SCHEMA,
    StageReportDefinition,
)
from .reports.manifest import sha256_file
from .requirements_frontend import DOCUMENT_ANALYSIS_REL, FRONTDOOR_REL, SPEC_INPUT_REL, check_requirements_frontend, required_frontend_paths
from .review import check_review_findings
from .rtl_skill_audit import run_rtl_skill_audit
from .simple_yaml import load_yaml
from .waveform import LOOP1_WAVE_DIR_REL
from .waveform_gate import (
    QUERY_TRANSCRIPT_JSON_REL,
    TOP_WAVE_MANIFEST_REL,
    WAVEFORM_GATE_JSON_REL,
    WAVEFORM_QUERY_REPORT_REL,
    check_loop1_waveform_gate_report,
)


PASS_RESULTS = {"PASS", "COMPLETE"}

LOOP3_ALLOWED_PROJECT_SCRIPT_NAMES = {
    "Generate-BoardXdc.ps1",
    "Generate-PsPlBd.ps1",
    "Generate-VitisBoot.ps1",
    "Invoke-PrototypePreflight.ps1",
    "README.md",
}

MINERU_HIGH_PRECISION_CHANNEL = "mineru-open-api high_precision_api"
MINERU_HIGH_PRECISION_ENDPOINTS = {
    "/api/v4/extract/task",
    "/api/v4/file-urls/batch",
}
PARSER_OUTPUT_SUFFIXES = {".md", ".json", ".html", ".txt"}
CHAT_ONLY_PARSER_OUTPUTS = {"manual_chat_capture", "chat_request", "chat_capture"}
CHAT_ONLY_SUPPORT_OUTPUTS = {"project_local_yaml", "sqlite_query", "workspace_config", "toolchain_config", "platform_config"}
ILLEGAL_DOCPARSE_EVIDENCE_NAMES = {
    "parse_operation_record.md",
    "operation_record.md",
    "analysis_record.md",
    "process_violation_record.md",
    "violation_record.md",
}

ILLEGAL_PROVENANCE_RECORD_MARKERS = {
    "operation_record",
    "process_violation_record",
    "violation_record",
    "manual_review",
    "docparse_operation_log",
}

PROTECTED_GATE_FILES = [
    "env/core/hdlflow/change_control.py",
    "env/core/hdlflow/cli.py",
    "env/core/hdlflow/docgen/checks.py",
    "env/core/hdlflow/docgen/collect.py",
    "env/core/hdlflow/docgen/constants.py",
    "env/core/hdlflow/docgen/manifests.py",
    "env/core/hdlflow/docgen/render.py",
    "env/core/hdlflow/docgen/snapshots.py",
    "env/core/hdlflow/frontdoor_guard.py",
    "env/core/hdlflow/gates.py",
    "env/core/hdlflow/loop1_reports.py",
    "env/core/hdlflow/loop2_reports.py",
    "env/core/hdlflow/memory.py",
    "env/core/hdlflow/plan_checks.py",
    "env/core/hdlflow/ralph_loop.py",
    "env/core/hdlflow/report_checks.py",
    "env/core/hdlflow/reports/__init__.py",
    "env/core/hdlflow/reports/constants.py",
    "env/core/hdlflow/reports/loop1_report.py",
    "env/core/hdlflow/reports/loop2_report.py",
    "env/core/hdlflow/reports/manifest.py",
    "env/core/hdlflow/reports/parser_hdlflow_events.py",
    "env/core/hdlflow/reports/render_report.py",
    "env/core/hdlflow/requirements_frontend.py",
    "env/core/hdlflow/review.py",
    "env/core/hdlflow/state_sync.py",
    "env/core/hdlflow/waveform.py",
    "env/core/hdlflow/waveform_backend.py",
    "env/core/hdlflow/waveform_gate.py",
    "env/core/hdlflow/waveform_query.py",
    "env/rule/global/gates/gate_levels.yaml",
    "env/rule/global/gates/global_gate_rules.yaml",
    "env/rule/global/reports/report_policy.yaml",
    "env/tool/scripts/Invoke-HdlLoop3BoardVerify.ps1",
]

GENERATED_REQUIREMENT_FILES = {
    "README.md",
    "srs.yaml",
    "srs.md",
    "acceptance_criteria.yaml",
    "forbidden_designs.yaml",
    "open_questions.md",
    "requirements.json",
    "requirements.md",
    "module_plan.md",
    "path_partition.md",
    "decomposition_notes.md",
    "design_blueprint.md",
}

DOC_PARSE_ALLOWED_MARKDOWN_RELS = {
    "work/docparse/README.md",
    "work/docparse/architecture/add.md",
    "work/docparse/verification/verification_plan.md",
    "work/docparse/prototype/prototype_plan.md",
    "work/docparse/req_decompose/requirements.md",
    "work/docparse/req_decompose/module_plan.md",
    "work/docparse/req_decompose/path_partition.md",
    "work/docparse/req_decompose/decomposition_notes.md",
    "work/docparse/review/assumption_log.md",
    "work/docparse/review/docparse_operation_log.md",
    "work/docparse/review/README.md",
    "work/docparse/review/multi_agent_review.md",
    "work/docparse/review/process_violation_record.md",
    "work/docparse/review/spec_diff.md",
    "work/docparse/review/violation_record.md",
}

SPEC_REQUIREMENTS_ALLOWED_MARKDOWN = {
    f"{SPEC_INPUT_REL}/README.md",
    f"{FRONTDOOR_REL}/srs.md",
    f"{FRONTDOOR_REL}/open_questions.md",
    "work/docparse/req_decompose/requirements.md",
    "work/docparse/req_decompose/module_plan.md",
    "work/docparse/req_decompose/path_partition.md",
    "work/docparse/req_decompose/decomposition_notes.md",
}

DESIGN_REPORT_ALLOWED_MARKDOWN = {
    definition.doc_rel for definition in DOC_DEFINITIONS
}

FORBIDDEN_FORMAL_TEXT_PATTERNS = [
    re.compile(r"\b" + "smo" + "ke" + r"\b", re.IGNORECASE),
    re.compile("\u70df\u6d4b"),
    re.compile("\u5192\u70df"),
]

FORMAL_TEXT_SCAN_ROOTS = [
    SPEC_INPUT_REL,
    "work/docparse/architecture",
    "work/docparse/verification",
    "work/docparse/prototype",
    "work/docparse/req_decompose",
    "work/docparse/review",
    "work/docparse/structured_spec",
    "work/docparse/trace_matrix",
    "output/docs",
    "output/reports/loop1",
    "output/reports/loop2",
    "output/reports/loop3",
    "output/rtl",
    "output/tb",
    "output/uvm",
    "output/fpga",
]

PROJECT_ROOT_TOOL_LOG_PATTERNS = (
    "vivado*.jou",
    "vivado*.log",
)

NODE_FILE_STEMS = {
    "input": ["input"],
    "work/docparse": ["work_docparse"],
    "work/loop1_rtl_tb": ["work_loop1_rtl_tb"],
    "work/loop2_uvm": ["work_loop2_uvm"],
    "work/loop3_fpga_proto": ["work_loop3_fpga_proto"],
    "output": ["output"],
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
    checks.append(_check_project_root_tool_logs(project))
    checks.extend(_check_change_control(project, change_id))
    if _requires_docparse_reentry(normalized_node):
        checks.extend(_check_requirements_reentered_docparse(project))
    if all(check.status == "PASS" for check in checks):
        checks.extend(_refresh_reports_for_gate(project, normalized_node))
    else:
        checks.append(
            GateCheck(
                "automatic_report_refresh",
                "PASS",
                "skipped because an upstream gate precondition failed; evidence was not regenerated",
            )
        )

    source_paths, evidence_paths = _gate_paths(project, normalized_node)

    if normalized_node == "input":
        checks.extend(_check_doc_sources(project))
    elif normalized_node == "work/docparse":
        checks.extend(_check_docparse(project))
    elif normalized_node == "work/loop1_rtl_tb":
        checks.extend(_check_loop1(project, level))
    elif normalized_node == "work/loop2_uvm":
        checks.extend(_check_loop2(project, level))
    elif normalized_node == "work/loop3_fpga_proto":
        checks.extend(_check_loop3(project, level))
    elif normalized_node == "output":
        checks.extend(_check_final(project, level))
    else:
        raise ValueError(f"unsupported gate node: {node}")

    if normalized_node != "input":
        checks.extend(_check_review_findings_gate(project, level))

    checks.extend(_check_manifest_drift(project, normalized_node, source_paths, change_id))
    checks.extend(_check_skill_manifest_drift(project, normalized_node, change_id))
    checks.extend(_check_protected_gate_manifest_drift(project, normalized_node, change_id))
    checks.extend(_check_evidence_freshness(project, source_paths, evidence_paths))
    ok = all(check.status == "PASS" for check in checks)

    report_path = _write_gate_report(project, normalized_node, level, ok, checks, change_id)
    manifest_path = None
    if ok:
        manifest_path = _write_gate_manifest(project, normalized_node, level, source_paths, evidence_paths, report_path, change_id)
    return GateRunResult(normalized_node, level, ok, report_path, checks, manifest_path)


def run_final_audit(project_path: Path, level: str = "release") -> GateRunResult:
    return run_gate(project_path, "output", level=level)


def _refresh_reports_for_gate(project: Path, node: str) -> list[GateCheck]:
    if node == "work/loop1_rtl_tb":
        prerequisite = _check_prerequisite_gate(project, "work/docparse", "DocParse must pass before Loop1 report refresh")
        if any(check.status != "PASS" for check in prerequisite):
            return [
                GateCheck(
                    "loop1_report_refresh",
                    "FAIL",
                    "skipped because DocParse prerequisite gate is missing; evidence was not regenerated",
                )
            ]
        try:
            result = refresh_loop1_reports(project)
        except Exception as exc:
            return [GateCheck("loop1_report_refresh", "FAIL", f"failed to refresh Loop1 reports from latest log: {exc}")]
        return [GateCheck("loop1_report_refresh", "PASS", f"reports refreshed: {len(result.report_paths)} file(s)")]
    if node == "work/loop2_uvm":
        prerequisite = _check_prerequisite_gate(project, "work/loop1_rtl_tb", "Loop1 must pass before Loop2 report refresh")
        if any(check.status != "PASS" for check in prerequisite):
            return [
                GateCheck(
                    "loop2_report_refresh",
                    "FAIL",
                    "skipped because Loop1 prerequisite gate is missing; evidence was not regenerated",
                )
            ]
        try:
            result = refresh_loop2_reports(project)
        except Exception as exc:
            return [GateCheck("loop2_report_refresh", "FAIL", f"failed to refresh Loop2 reports from latest log: {exc}")]
        return [GateCheck("loop2_report_refresh", "PASS", f"reports refreshed: {len(result.report_paths)} file(s)")]
    if node == "work/loop3_fpga_proto":
        prerequisite = _check_prerequisite_gate(project, "work/loop2_uvm", "Loop2 must pass before Loop3 report refresh")
        if any(check.status != "PASS" for check in prerequisite):
            return [
                GateCheck(
                    "loop3_report_refresh",
                    "FAIL",
                    "skipped because Loop2 prerequisite gate is missing; evidence was not regenerated",
                )
            ]
        try:
            result = refresh_loop3_reports(project)
        except Exception as exc:
            return [GateCheck("loop3_report_refresh", "FAIL", f"failed to refresh Loop3 reports from current evidence: {exc}")]
        detail = ", ".join(f"{name}={status}" for name, status in sorted(result.statuses.items()))
        return [GateCheck("loop3_report_refresh", "PASS", detail)]
    return []


def _normalize_node(node: str) -> str:
    aliases = {
        "spec": "input",
        "00": "input",
        "docparse": "work/docparse",
        "01": "work/docparse",
        "loop1": "work/loop1_rtl_tb",
        "02": "work/loop1_rtl_tb",
        "loop2": "work/loop2_uvm",
        "03": "work/loop2_uvm",
        "loop3": "work/loop3_fpga_proto",
        "04": "work/loop3_fpga_proto",
        "final": "output",
        "output": "output",
        "05": "output",
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
        "template_source": "env/rule/scaffold",
        "manual_project_directory_creation": "forbidden",
    }
    errors = [f"{key}={data.get(key)!r}" for key, expected in required.items() if data.get(key) != expected]
    if errors:
        return [GateCheck("project_scaffold_schema", "FAIL", "invalid scaffold marker fields: " + ", ".join(errors))]
    if not data.get("created_by") or not data.get("created_at"):
        return [GateCheck("project_scaffold_schema", "FAIL", "created_by and created_at are required")]
    return [GateCheck("project_scaffold_schema", "PASS", "script-created scaffold marker is valid")]


def _check_project_root_tool_logs(project: Path) -> GateCheck:
    hits: list[Path] = []
    for pattern in PROJECT_ROOT_TOOL_LOG_PATTERNS:
        hits.extend(path for path in project.glob(pattern) if path.is_file())
    if hits:
        rels = ", ".join(_rel(project, path) for path in sorted(hits)[:10])
        return GateCheck(
            "project_root_tool_logs",
            "FAIL",
            (
                "tool journal/log files must not live in the project root; launch "
                "Vivado through env/tool/scripts/Invoke-HdlVivado.ps1 so logs go under "
                "output/fpga/vivado/logs: " + rels
            ),
        )
    return GateCheck("project_root_tool_logs", "PASS", "no Vivado journal/log files in project root")


def _check_change_control(project: Path, change_id: str | None) -> list[GateCheck]:
    open_requests = _read_change_requests(project, statuses={"open", "impact_ready"})
    if not change_id:
        if open_requests:
            ids = ", ".join(item["id"] for item in open_requests)
            return [GateCheck("change_control_state", "FAIL", f"open or unapproved change request(s): {ids}")]
        approved_requests = _read_change_requests(project, statuses={"approved"})
        if approved_requests:
            ids = ", ".join(item["id"] for item in approved_requests)
            return [
                GateCheck(
                    "change_control_state",
                    "FAIL",
                    f"approved change request(s) must be bound to this gate with --change-id: {ids}",
                )
            ]
        return [GateCheck("change_control_state", "PASS", "no open or unbound approved change request blocks this gate")]

    request = _read_change_request(project, change_id)
    if not request:
        return [GateCheck("change_control_state", "FAIL", f"change request not found: {change_id}")]
    if request.get("status") != "approved":
        return [GateCheck("change_control_state", "FAIL", f"{change_id} status is {request.get('status')!r}, expected approved")]
    missing_records = [
        rel
        for rel in (
            f"work/change/impact_analysis/{change_id}.md",
            f"work/change/approvals/{change_id}.md",
        )
        if not (project / rel).exists()
    ]
    if missing_records:
        return [
            GateCheck(
                "change_control_state",
                "FAIL",
                "approved change request is incomplete; missing " + ", ".join(missing_records),
            )
        ]
    bundle_errors = validate_change_bundle(project, change_id, require_approval=True)
    if bundle_errors:
        return [
            GateCheck(
                "change_control_state",
                "FAIL",
                "approved change request records are incomplete: " + "; ".join(bundle_errors[:8]),
            )
        ]
    return [GateCheck("change_control_state", "PASS", f"approved change request bound: {change_id}")]


def _check_doc_sources(project: Path) -> list[GateCheck]:
    req = project / SPEC_INPUT_REL
    files = [path for path in req.glob("*") if path.is_file() and path.name not in {"README.md", ".gitkeep"}]
    checks = [_check_source_encoding_integrity(project, files)]
    generated = sorted(path.name for path in files if path.name in GENERATED_REQUIREMENT_FILES)
    if generated:
        checks.append(
            GateCheck(
                "source_spec_clean",
                "FAIL",
                f"generated front-door/decomposition artifacts must not live under {SPEC_INPUT_REL}; use {FRONTDOOR_REL} or work/docparse/req_decompose: "
                + ", ".join(generated[:8]),
            )
        )
        return checks
    if files:
        checks.append(GateCheck("source_spec_clean", "PASS", f"{SPEC_INPUT_REL} contains user requirement source files only"))
        checks.append(GateCheck("source_spec_available", "PASS", f"{len(files)} requirement file(s) available"))
        return checks
    checks.append(GateCheck("source_spec_clean", "PASS", f"{SPEC_INPUT_REL} is clean"))
    checks.append(GateCheck("source_spec_available", "FAIL", f"no requirement source files under {SPEC_INPUT_REL}"))
    return checks


def _check_source_encoding_integrity(project: Path, files: list[Path] | None = None) -> GateCheck:
    if files is None:
        req = project / SPEC_INPUT_REL
        files = [path for path in req.glob("*") if path.is_file() and path.name != "README.md"]
    text_suffixes = {".md", ".txt", ".yaml", ".yml", ".json", ".v", ".sv", ".svh", ".tcl", ".xdc", ".do"}
    hits: list[str] = []
    mojibake_markers = ("�", "锛", "鐨", "绔", "搴", "鍦", "潃", "鏁", "閲嶆柊", "€")
    for path in files:
        if path.suffix.lower() not in text_suffixes:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            hits.append(f"{_rel(project, path)}: not valid UTF-8")
            continue
        marker_count = sum(text.count(marker) for marker in mojibake_markers)
        if marker_count >= 3:
            hits.append(f"{_rel(project, path)}: suspected mojibake/encoding damage")
    if hits:
        return GateCheck("source_encoding_integrity", "FAIL", "; ".join(hits[:8]))
    return GateCheck("source_encoding_integrity", "PASS", "requirement sources are valid UTF-8 with no mojibake markers")


def _check_docparse(project: Path) -> list[GateCheck]:
    checks = _check_prerequisite_gate(project, "input", "input gate must pass before DocParse exit")
    checks.append(_check_source_encoding_integrity(project))
    required = [
        "work/docparse/structured_spec/interface_spec.yaml",
        "work/docparse/structured_spec/interface_timing.yaml",
        "work/docparse/structured_spec/register_map.yaml",
        "work/docparse/structured_spec/test_intent.yaml",
        "work/docparse/structured_spec/timing_rules.yaml",
        "work/docparse/req_decompose/requirements.json",
        "work/docparse/req_decompose/requirements.md",
        "work/docparse/req_decompose/module_plan.md",
        "work/docparse/req_decompose/path_partition.md",
        "work/docparse/req_decompose/decomposition_notes.md",
        "work/docparse/trace_matrix/req_to_design_intent.yaml",
        "work/docparse/trace_matrix/req_to_test_intent.yaml",
    ]
    checks.extend(_path_checks(project, [*required, *required_frontend_paths()]))
    result = check_requirements_frontend(project, require_ready=True)
    machine_errors = [
        error
        for error in result.errors
        if "work/docparse/structured_spec/" in error
    ]
    checks.append(
        GateCheck(
            "machine_readable_specs_ready",
            "PASS" if not machine_errors else "FAIL",
            (
                "structured interface, register/op-code, timing, and test-intent specs are READY"
                if not machine_errors
                else "; ".join(machine_errors[:6])
            ),
        )
    )
    checks.append(
        GateCheck(
            "requirements_frontdoor_ready",
            "PASS" if result.ok else "FAIL",
            f"report: {result.report_path.relative_to(project)}",
        )
    )
    question_errors = [
        error
        for error in result.errors
        if "question_review" in error
        or "open_questions" in error
        or "Open Requirement Questions" in error
        or "unresolved requirement questions" in error
    ]
    checks.append(
        GateCheck(
            "requirement_questions_reviewed",
            "PASS" if not question_errors else "FAIL",
            (
                "requirement ambiguity questions were reviewed by the user and no unresolved blockers remain"
                if not question_errors
                else "; ".join(question_errors[:6])
            ),
        )
    )
    if result.ok:
        checks.extend(
            [
                GateCheck("spec_agent_ready", "PASS", "Spec Agent artifacts define executable spec boundaries and trace roots"),
                GateCheck("arch_agent_ready", "PASS", "Arch Agent artifacts define topology, interfaces, dataflow, state machines, and timing model"),
                GateCheck("exec_agent_boundary_ready", "PASS", "Exec Agent is limited to RTL and complete functional directed TB implementation roots"),
                GateCheck("sim_agent_plan_ready", "PASS", "Sim Agent owns verification, UVM, waveform, coverage, and Loop1/Loop2/Loop3 evidence plans"),
                GateCheck("review_agent_ready", "PASS", "Review Agent findings surface is present and write-limited to defects, risks, and advice"),
                GateCheck("arbtr_flow_ready", "PASS", "Arbtr Agent decision and arbitration logs are present for feedback routing and freeze control"),
            ]
        )
    for error in result.errors:
        checks.append(GateCheck("requirements_frontdoor_error", "FAIL", error))
    for warning in result.warnings:
        checks.append(GateCheck("requirements_frontdoor_warning", "PASS", warning))
    if result.ok:
        checks.extend(_check_docset(project, ["application_guide", "microarchitecture_specification", "verification_plan"]))
    else:
        checks.append(
            GateCheck(
                "docset_sync",
                "FAIL",
                "docset generation is blocked until requirements-frontdoor-check passes with READY artifacts",
            )
        )
    checks.append(_check_official_protocol_naming(project))
    checks.append(_check_docparse_extract_policy(project))
    checks.append(_check_docparse_verification_breadth(project))
    checks.append(_check_no_ad_hoc_analysis_artifacts(project))
    checks.append(_check_forbidden_formal_text(project))
    return checks


def _check_review_findings_gate(project: Path, level: str) -> list[GateCheck]:
    result = check_review_findings(project, level=level)
    checks = [
        GateCheck(
            "review_findings_gate",
            "PASS" if result.ok else "FAIL",
            f"report: {result.report_path.relative_to(project)}; blockers={len(result.blocking_findings)}",
        )
    ]
    for item in result.blocking_findings[:8]:
        checks.append(GateCheck("review_blocker", "FAIL", item))
    for error in result.errors:
        if error.startswith(("open blocking review finding", "unclosed blocking review finding")):
            continue
        checks.append(GateCheck("review_schema_error", "FAIL", error))
    for warning in result.warnings:
        checks.append(GateCheck("review_schema_warning", "PASS", warning))
    return checks


def _check_loop1(project: Path, level: str) -> list[GateCheck]:
    checks = _check_prerequisite_gate(project, "work/docparse", "DocParse must pass before Loop1 starts")
    checks.extend(_check_skill_policy(project, "work/loop1_rtl_tb"))
    checks.extend(_check_source_policy(project, "work/loop1_rtl_tb"))
    checks.append(_check_official_protocol_naming(project))
    checks.append(_check_rtl_task_usage(project))
    checks.append(_check_rtl_comment_headers(project))
    checks.extend(_check_docset(project, ["application_guide", "microarchitecture_specification", "verification_plan"]))
    report_checks, report_payload = _check_stage_report_contract(project, LOOP1_REPORT)
    checks.extend(report_checks)
    required_paths = [
        LOOP1_WAVE_DIR_REL,
        "work/loop1_rtl_tb/trace_matrix/req_to_directed_tb.yaml",
        "output/tb/full_function_test_plan.md",
    ]
    checks.extend(_path_checks(project, required_paths))
    freshness_rels = _stage_report_required_rels(LOOP1_REPORT)
    checks.extend(_check_skill_policy_freshness(project, "work/loop1_rtl_tb", _files(project, freshness_rels)))
    checks.append(_check_rtl_skill_audit_freshness(project))
    checks.append(_check_report_pass("loop1_report_pass", report_payload))
    checks.append(_check_report_parser_clean("loop1_report_parser_clean", report_payload))
    checks.append(_check_report_transactions("loop1_transaction_contract", report_payload))
    checks.append(_loop1_deterministic_gate_check(project, report_payload))
    checks.append(_loop1_baseline_gate_check(report_payload))
    checks.append(_loop1_full_function_matrix_check(project, report_payload))
    checks.append(_check_loop1_waveform_advisory_report(project, WAVEFORM_GATE_JSON_REL, level))
    checks.append(_check_bug_tracking(project, "work/loop1_rtl_tb/bug_tracking"))
    checks.append(_check_forbidden_formal_text(project))
    return checks


def _check_loop2(project: Path, level: str) -> list[GateCheck]:
    checks = _check_prerequisite_gate(project, "work/loop1_rtl_tb", "Loop1 must pass before Loop2 starts")
    checks.extend(_check_skill_policy(project, "work/loop2_uvm"))
    checks.extend(_check_source_policy(project, "work/loop2_uvm"))
    checks.append(_check_official_protocol_naming(project))
    checks.append(_check_rtl_task_usage(project))
    checks.append(_check_rtl_comment_headers(project))
    checks.append(_check_rtl_skill_audit_freshness(project))
    checks.extend(_check_docset(project, ["application_guide", "microarchitecture_specification", "verification_plan"]))
    checks.extend(_check_loop2_uvm_policy(project))
    report_checks, report_payload = _check_stage_report_contract(project, LOOP2_REPORT)
    checks.extend(report_checks)
    database_rel = "work/loop2_uvm/_runtime/loop2_bindings.sqlite"
    checks.extend(_path_checks(
        project,
        [
            database_rel,
            "work/loop2_uvm/trace_matrix/req_to_uvm.yaml",
            "work/loop2_uvm/trace_matrix/req_to_assertion.yaml",
            "work/loop2_uvm/trace_matrix/req_to_coverage.yaml",
        ],
    ))
    checks.extend(_check_skill_policy_freshness(project, "work/loop2_uvm", _files(project, _stage_report_required_rels(LOOP2_REPORT) + [database_rel])))
    checks.append(_check_report_pass("loop2_report_pass", report_payload))
    checks.append(_check_report_parser_clean("loop2_report_parser_clean", report_payload))
    checks.append(_check_report_transactions("loop2_transaction_contract", report_payload))
    checks.append(_check_loop2_zero_counts(report_payload))
    checks.append(_loop2_coverage_summary_check(project, report_payload, level))
    checks.append(_loop2_transaction_count_check(project, report_payload))
    checks.append(_loop2_scenario_count_check(project))
    checks.append(_loop2_stress_transaction_check(project))
    checks.append(_loop2_coverage_triage_check(project, _read(project / LOOP2_REPORT.report_md)))
    checks.append(_loop2_bound_assertion_check(project))
    checks.append(_loop2_functional_coverage_sampling_check(project))
    checks.append(_loop2_stimulus_breadth_check(project, level))
    checks.append(_loop2_configured_scenario_evidence_check(project, _report_payload_evidence_text(report_payload)))
    checks.append(_check_bug_tracking(project, "work/loop2_uvm/bug_tracking"))
    checks.append(_check_forbidden_formal_text(project))
    return checks


def _check_loop3(project: Path, level: str) -> list[GateCheck]:
    evidence = _node_evidence(project, "work/loop3_fpga_proto")
    prototype_policy = _node_config(project, "work/loop3_fpga_proto").get("prototype_policy", {})
    bitstream_glob = _evidence_str(evidence, "globs", "bitstreams", "output/fpga/vivado/bitstream/*.bit")
    bitstreams = _glob_project_files(project, bitstream_glob)
    bitstream_rels = [_rel(project, path) for path in bitstreams]
    database_preflight_rel = _evidence_str(evidence, "reports", "database_preflight", "output/reports/loop3/preflight/database_preflight.md")
    prototype_plan_rel = _evidence_str(evidence, "reports", "prototype_plan_check", "output/reports/loop3/preflight/prototype_plan_check.md")
    timing_rel = _evidence_str(evidence, "reports", "timing", "output/fpga/vivado/reports/post_impl_timing_summary.rpt")
    drc_rel = _evidence_str(evidence, "reports", "drc", "output/fpga/vivado/reports/post_impl_drc.rpt")
    serial_rel = _evidence_str(evidence, "reports", "serial", "output/reports/loop3/serial/latest_serial_text.log")
    serial_validation_rel = _evidence_str(evidence, "reports", "serial_validation", "output/reports/loop3/serial/latest_serial_validation_report.md")
    vivado_impl_rel = _loop3_report_rel(evidence, prototype_policy, "vivado_implementation", "vivado_implementation_report", "output/reports/loop3/vivado_implementation_report.md")
    vitis_boot_rel = _loop3_report_rel(evidence, prototype_policy, "vitis_boot", "vitis_boot_report", "output/reports/loop3/vitis_boot_report.md")
    board_validation_rel = _loop3_report_rel(evidence, prototype_policy, "board_validation", "board_validation_report", "output/reports/loop3/board_validation_report.md")
    loop3_exit_rel = _loop3_report_rel(evidence, prototype_policy, "loop3_exit", "loop3_exit_report", "output/reports/loop3/loop3_exit_report.md")
    checks = _check_prerequisite_gate(project, "work/loop2_uvm", "Loop2 must pass before Loop3 starts")
    checks.extend(_check_docset(project, ["application_guide", "microarchitecture_specification", "verification_plan", "delivery_package"]))
    checks.extend(_check_skill_policy(project, "work/loop3_fpga_proto"))
    checks.extend(_check_source_policy(project, "work/loop3_fpga_proto"))
    checks.append(_check_official_protocol_naming(project))
    checks.append(_check_rtl_task_usage(project))
    checks.append(_check_rtl_skill_audit_freshness(project))
    checks.append(_check_no_project_local_loop3_scripts(project))
    checks.extend(_path_checks(
        project,
        [
            database_preflight_rel,
            prototype_plan_rel,
            timing_rel,
            drc_rel,
            serial_rel,
            serial_validation_rel,
            vivado_impl_rel,
            vitis_boot_rel,
            board_validation_rel,
            loop3_exit_rel,
        ],
    ))
    checks.append(
        GateCheck(
            "loop3_bitstream_available",
            "PASS" if bitstream_rels else "FAIL",
            ", ".join(bitstream_rels) if bitstream_rels else "no .bit file under output/fpga/vivado/bitstream",
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
    checks.append(_loop3_external_stimulus_boundary_check(project, plan))
    checks.extend(_loop3_timing_checks(timing))
    checks.append(_loop3_serial_echo_check(serial_validation, serial_text, serial_validation_path, serial_path))
    checks.append(_loop3_configured_serial_stress_check(project, serial_text))
    checks.append(_loop3_formal_report_pass_check(project, "loop3_vivado_implementation_report", vivado_impl_rel))
    checks.append(_loop3_formal_report_pass_check(project, "loop3_vitis_boot_report", vitis_boot_rel))
    checks.append(_loop3_formal_report_pass_check(project, "loop3_board_validation_report", board_validation_rel))
    checks.append(_loop3_formal_report_pass_check(project, "loop3_exit_report", loop3_exit_rel))
    checks.append(_loop3_database_ug_flow_check(preflight, _read(project / "output" / "fpga" / "vivado" / "reports" / "pure_pl_uart_led_proto_run.md")))
    if level == "release":
        checks.append(_loop3_release_warning_check(project, "loop3_drc_release_clean", drc, "vivado_drc", _evidence_list(evidence, "release_forbidden_markers", "drc", [" Warning", "Warnings", "Checks found: 1"])))
        checks.append(_loop3_release_warning_check(project, "loop3_timing_methodology_release_clean", timing, "timing_methodology", _evidence_list(evidence, "release_forbidden_markers", "timing", ["TIMING-18", "Missing input or output delay", "no_input_delay", "no_output_delay"])))
    else:
        checks.append(GateCheck("loop3_warning_policy", "PASS", "develop gate allows documented Vivado warnings; release gate is strict"))
    checks.append(_check_forbidden_formal_text(project))
    return checks


def _loop3_serial_echo_check(
    serial_validation: str,
    serial_text: str,
    serial_validation_path: Path | None = None,
    serial_path: Path | None = None,
) -> GateCheck:
    serial_text = serial_text.lstrip("\ufeff").strip()
    if (
        serial_validation_path is not None
        and serial_path is not None
        and serial_validation_path.exists()
        and serial_path.exists()
        and serial_validation_path.stat().st_mtime < serial_path.stat().st_mtime
    ):
        return GateCheck(
            "loop3_serial_echo",
            "FAIL",
            "serial validation report is older than latest_serial_text.log; rerun serial validation from the latest raw log",
        )
    tx_match = _serial_payload_match("TX", serial_validation, bullet=True)
    rx_match = _serial_payload_match("RX", serial_validation, bullet=True)
    result_pass = re.search(r"^-\s*result:\s*PASS\s*$", serial_validation, flags=re.MULTILINE)
    if not tx_match or not rx_match or not result_pass:
        return GateCheck("loop3_serial_echo", "FAIL", "serial validation must contain TX[time], RX[time], and result: PASS")
    tx_payload = tx_match.group(1).strip()
    rx_payload = rx_match.group(1).strip()
    command_response = tx_payload.lower() == "read" and re.match(r"^read data=0x[0-9A-Fa-f]{8}$", rx_payload)
    legacy_echo = tx_payload == rx_payload
    if not command_response and not legacy_echo:
        return GateCheck("loop3_serial_echo", "FAIL", f"serial command/response mismatch: tx={tx_payload!r}, rx={rx_payload!r}")
    failure_lines = _loop3_serial_failure_lines(serial_text)
    if failure_lines:
        return GateCheck(
            "loop3_serial_echo",
            "FAIL",
            "latest_serial_text.log contains raw failure/error marker(s): " + "; ".join(failure_lines[:4]),
        )
    if not re.search(r"(?m)^\s*LOOP3_RESULT\s+PASS\s*$", serial_text):
        return GateCheck("loop3_serial_echo", "FAIL", "latest_serial_text.log must contain final LOOP3_RESULT PASS")
    raw_match = _serial_payload_match("RX", serial_text.strip(), bullet=False)
    if not raw_match:
        return GateCheck("loop3_serial_echo", "FAIL", "latest_serial_text.log must contain RX[time] payload")
    raw_payload = raw_match.group(1).strip()
    if raw_payload != rx_payload:
        return GateCheck("loop3_serial_echo", "FAIL", f"raw RX log payload mismatch: log={raw_payload!r}, report={rx_payload!r}")
    if command_response:
        return GateCheck("loop3_serial_echo", "PASS", f"PL UART command read produced DDR response: {rx_payload}")
    return GateCheck("loop3_serial_echo", "PASS", f"TX/RX payloads match and raw RX log is timestamped: {rx_payload}")


def _loop3_report_rel(evidence: dict[str, Any], prototype_policy: Any, report_key: str, policy_key: str, default: str) -> str:
    reports = evidence.get("reports", {}) if isinstance(evidence, dict) else {}
    if isinstance(reports, dict) and reports.get(report_key):
        return str(reports.get(report_key))
    if isinstance(prototype_policy, dict) and prototype_policy.get(policy_key):
        return str(prototype_policy.get(policy_key))
    return default


def _loop3_formal_report_pass_check(project: Path, name: str, rel_path: str) -> GateCheck:
    path = _project_path(project, rel_path)
    if not path.exists():
        return GateCheck(name, "FAIL", f"missing formal Loop3 report: {rel_path}")
    text = path.read_text(encoding="utf-8", errors="ignore")
    if "TODO" in text:
        return GateCheck(name, "FAIL", f"formal Loop3 report still contains TODO: {rel_path}")
    if re.search(r"(?mi)^\s*-?\s*result:\s*PASS\s*$", text):
        return GateCheck(name, "PASS", f"{rel_path} result PASS")
    return GateCheck(name, "FAIL", f"{rel_path} does not contain result: PASS")


def _check_no_project_local_loop3_scripts(project: Path) -> GateCheck:
    script_dir = project / "work/loop3_fpga_proto/scripts"
    if not script_dir.exists():
        return GateCheck("loop3_no_project_local_ad_hoc_scripts", "PASS", "Loop3 script directory is absent")
    hits = [
        _rel(project, path)
        for path in sorted(script_dir.iterdir())
        if path.is_file() and path.name not in LOOP3_ALLOWED_PROJECT_SCRIPT_NAMES
    ]
    if hits:
        return GateCheck(
            "loop3_no_project_local_ad_hoc_scripts",
            "FAIL",
            "project-local Loop3 scripts are not signoff evidence; use env/tool/scripts wrappers: " + ", ".join(hits[:8]),
        )
    return GateCheck("loop3_no_project_local_ad_hoc_scripts", "PASS", "Loop3 uses only scaffold scripts plus platform wrappers")


def _serial_payload_match(kind: str, text: str, *, bullet: bool) -> re.Match[str] | None:
    prefix = r"^-\s*" if bullet else r"^"
    separator = r"(?:锛[^\w\s]?|[：:]|->)?"
    return re.search(rf"{prefix}{re.escape(kind)}\[[^\]]+\]\s*{separator}\s*(.+?)\s*$", text, flags=re.MULTILINE)


def _loop3_serial_failure_lines(serial_text: str) -> list[str]:
    lines: list[str] = []
    for line in serial_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        upper = stripped.upper()
        if "FAIL" in upper and ("LOOP3_RESULT" in upper or "DUT_PROTOCOL_MODEL" in upper):
            lines.append(stripped)
        elif re.search(r"\b(ERROR|FATAL)\b", stripped) and not re.search(r"\bPASS\b", stripped):
            lines.append(stripped)
    return lines


def _loop1_baseline_gate_check(report_payload: dict[str, Any]) -> GateCheck:
    if not isinstance(report_payload, dict) or not report_payload:
        return GateCheck("loop1_baseline_function_gate", "FAIL", "missing Loop1 report.json payload")
    if str(report_payload.get("result", "")).upper() != "PASS":
        return GateCheck("loop1_baseline_function_gate", "FAIL", f"Loop1 result is {report_payload.get('result')}")
    if _summary_int(report_payload, "failed_tests") != 0 or _summary_int(report_payload, "failed_checks") != 0:
        return GateCheck("loop1_baseline_function_gate", "FAIL", "Loop1 summary contains failed tests or checks")
    if _summary_int(report_payload, "total_checks") <= 0:
        return GateCheck("loop1_baseline_function_gate", "FAIL", "Loop1 summary has no checked transaction")
    return GateCheck("loop1_baseline_function_gate", "PASS", "Loop1 structured summary passed with zero failed checks")


def _loop1_deterministic_gate_check(project: Path, report_payload: dict[str, Any]) -> GateCheck:
    issues: list[str] = []
    if not isinstance(report_payload, dict) or not report_payload:
        issues.append("missing Loop1 report.json payload")
    elif str(report_payload.get("result", "")).upper() != "PASS":
        issues.append(f"TB report result is {report_payload.get('result')}")
    if isinstance(report_payload, dict):
        parser_errors = report_payload.get("parser_errors")
        if parser_errors:
            issues.append("parser_errors=" + ", ".join(str(item) for item in parser_errors[:4]))
        if _summary_int(report_payload, "failed_tests") != 0:
            issues.append(f"failed_tests={_summary_int(report_payload, 'failed_tests')}")
        if _summary_int(report_payload, "failed_checks") != 0:
            issues.append(f"failed_checks={_summary_int(report_payload, 'failed_checks')}")
        if _summary_int(report_payload, "total_checks") <= 0:
            issues.append("total_checks=0")

    log_text = _read(project / LOOP1_REPORT.log_rel)
    if not log_text:
        issues.append(f"missing TB log: {LOOP1_REPORT.log_rel}")
    else:
        issues.extend(_loop1_hard_log_issues(log_text))

    if issues:
        return GateCheck("loop1_deterministic_gate", "FAIL", "; ".join(issues[:8]))
    return GateCheck(
        "loop1_deterministic_gate",
        "PASS",
        "TB PASS, structured parser clean, failed checks=0, simulator errors=0, fatal=0, assertion pass if enabled",
    )


def _loop1_hard_log_issues(text: str) -> list[str]:
    issues: list[str] = []
    error_patterns = [
        r"(?im)^\s*(?:#\s*)?\*\*\s+Error\b",
        r"(?im)^\s*(?:#\s*)?Error:",
        r"(?im)\bHDLFLOW\|CHECK\|.*\bresult=FAIL\b",
    ]
    fatal_patterns = [
        r"(?im)^\s*(?:#\s*)?\*\*\s+Fatal\b",
        r"(?im)^\s*(?:#\s*)?Fatal:",
        r"(?im)\$fatal\b",
        r"(?im)\bUVM_FATAL\b",
    ]
    if _first_regex_hit(text, error_patterns):
        issues.append("simulator_errors_nonzero")
    if _first_regex_hit(text, fatal_patterns):
        issues.append("fatal_nonzero")

    assertion_enabled = bool(re.search(r"(?i)\b(assertion|assert\s+property|sva)\b", text))
    assertion_fail = bool(
        re.search(r"(?i)\b(ASSERTION_FAIL|assertion\s+(?:failed|failure|error)|sva\s+(?:failed|failure|error))\b", text)
        or re.search(r"(?i)\b(assertion|sva)\b.*\b(FAIL|FAILED|FATAL|ERROR)\b", text)
    )
    if assertion_fail:
        issues.append("assertion_failure")
    elif assertion_enabled:
        assertion_pass = bool(re.search(r"(?i)\b(assertion|sva)\b.*\b(PASS|PASSED|0\s+failures?)\b", text))
        if not assertion_pass:
            issues.append("assertion_enabled_without_pass_marker")
    return issues


def _first_regex_hit(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None


def _loop1_full_function_matrix_check(project: Path, report_payload: dict[str, Any]) -> GateCheck:
    report_text = _report_payload_evidence_text(report_payload)
    policy = _node_config(project, "work/loop1_rtl_tb").get("directed_test_policy", {})
    opcodes = _docparse_required_opcode_tokens(project)
    missing_opcodes = []
    for opcode in opcodes:
        opcode = opcode.lower().replace("h", "").zfill(2)
        if not _run_report_has_noncompat_opcode_evidence(report_text, opcode):
            missing_opcodes.append(opcode.upper() + "h")

    required_boundaries = [
        "partial",
        "rx_location32_overwrite",
        "master_reset_keeps_control_register",
        "selftest",
        "tx_fifo",
    ]
    configured_boundaries = policy.get("required_boundary_markers") if isinstance(policy, dict) else None
    boundaries = [str(item) for item in configured_boundaries] if isinstance(configured_boundaries, list) else required_boundaries
    missing_boundaries = [marker for marker in boundaries if not re.search(re.escape(marker), report_text, flags=re.IGNORECASE)]

    missing = [*missing_opcodes, *missing_boundaries]
    if missing:
        return GateCheck("loop1_full_function_matrix", "FAIL", "missing full-function directed evidence: " + ", ".join(missing))
    return GateCheck("loop1_full_function_matrix", "PASS", f"{len(opcodes)} opcode(s) plus boundary markers covered by directed Loop1 evidence")


def _run_report_has_noncompat_opcode_evidence(run_report: str, opcode: str) -> bool:
    opcode = opcode.lower().replace("h", "").zfill(2)
    for line in run_report.splitlines():
        lower = line.lower()
        has_opcode = f"opcode_{opcode}" in lower or f"opcode[{opcode}]" in lower
        if not has_opcode:
            continue
        if re.search(r"\|\s*compat\s*\|", line, flags=re.IGNORECASE):
            continue
        if "pass" in lower:
            return True
    return False


def _check_loop1_waveform_advisory_report(project: Path, report_rel: str, level: str) -> GateCheck:
    errors = check_loop1_waveform_gate_report(project, report_rel)
    if errors:
        return GateCheck("loop1_waveform_advisory", "PASS", "advisory waveform issue: " + "; ".join(errors[:8]))
    return GateCheck("loop1_waveform_advisory", "PASS", f"{report_rel} generated by deterministic waveform rule engine")


def _loop2_configured_scenario_evidence_check(project: Path, text: str) -> GateCheck:
    policy = _loop2_policy(project)
    configured = policy.get("required_scenario_markers") if isinstance(policy, dict) else None
    required: list[str] = []
    if isinstance(configured, list):
        required = [str(item) for item in configured]
    elif isinstance(configured, dict):
        for value in configured.values():
            if isinstance(value, list):
                required.extend(str(item) for item in value)
            elif value:
                required.append(str(value))
    if not required:
        return GateCheck("loop2_configured_scenario_evidence", "PASS", "no extra Loop2 scenario marker policy configured")
    missing = [marker for marker in required if marker not in text]
    if missing:
        return GateCheck("loop2_configured_scenario_evidence", "FAIL", "missing configured Loop2 scenario marker(s): " + ", ".join(missing))
    return GateCheck("loop2_configured_scenario_evidence", "PASS", f"{len(required)} configured scenario marker(s) found")


def _loop3_configured_serial_stress_check(project: Path, serial_text: str) -> GateCheck:
    required_markers = _loop3_configured_serial_stress_markers(project)
    if not required_markers:
        return GateCheck("loop3_configured_serial_stress", "PASS", "no Loop3 serial stress marker policy configured")
    missing: list[str] = []
    for marker in required_markers:
        if marker.startswith("OPCODE["):
            opcode = re.escape(marker.split("[", 1)[1].split("]", 1)[0])
            pattern = rf"(?m)^OPCODE\[{opcode}\].*\bPASS\b"
            if re.search(pattern, serial_text, flags=re.IGNORECASE) is None:
                missing.append(f"{marker} ... PASS")
            continue
        if marker not in serial_text:
            missing.append(marker)
    if missing:
        return GateCheck("loop3_configured_serial_stress", "FAIL", "missing configured Loop3 serial marker(s): " + ", ".join(missing))
    return GateCheck("loop3_configured_serial_stress", "PASS", f"{len(required_markers)} configured Loop3 serial marker(s) found")


def _loop3_configured_serial_stress_markers(project: Path) -> list[str]:
    node_cfg = _node_config(project, "work/loop3_fpga_proto")
    evidence = node_cfg.get("evidence", {})
    required = evidence.get("required_markers", {}) if isinstance(evidence, dict) else {}
    marker_values: list[Any] = []
    if isinstance(required, dict):
        for key in ("serial_stress_all", "loop3_serial_stress_all", "uart_stress_all"):
            raw = required.get(key)
            if isinstance(raw, list):
                marker_values.extend(raw)

    prototype_policy = node_cfg.get("prototype_policy", {})
    if isinstance(prototype_policy, dict):
        raw = prototype_policy.get("serial_stress_markers")
        if isinstance(raw, list):
            marker_values.extend(raw)
        if prototype_policy.get("full_opcode_fifo_stress_required") is True:
            marker_values.extend(f"OPCODE[{token[:-1].upper()}]" for token in _docparse_required_opcode_tokens(project))
            marker_values.extend(
                [
                    "MULTIWORD_TX_PASS",
                    "TX_FIFO_FULL_DROP_CLEAR_PASS",
                    "RX_FIFO_OVERWRITE_DRAIN_PASS",
                    "BURST_A_TO_B_PASS",
                    "BURST_B_TO_A_PASS",
                    "LOOP3_RESULT PASS",
                ]
            )

    markers: list[str] = []
    for value in marker_values:
        marker = str(value).strip()
        if marker and marker not in markers:
            markers.append(marker)
    return markers


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


def _loop3_external_stimulus_boundary_check(project: Path, plan: str) -> GateCheck:
    plan_text = _read(project / "work/loop3_fpga_proto" / "board_tests" / "prototype_plan.yaml")
    if "mode: ps_pl" not in (plan_text or plan):
        return GateCheck("loop3_external_stimulus_boundary", "PASS", "external-stimulus RTL screen is only required for PS_PL plans")
    rtl_root = project / "output" / "rtl"
    if not rtl_root.is_dir():
        return GateCheck("loop3_external_stimulus_boundary", "FAIL", "output/rtl is missing")

    hits: list[str] = []
    for path in sorted(rtl_root.glob("*.v")):
        code = _strip_verilog_comments(path.read_text(encoding="utf-8", errors="ignore"))
        stem = path.stem.lower()
        if re.search(r"(^|_)(stimulus|reporter|model)($|_)", stem):
            hits.append(f"{path.name}: stimulus/model/reporter RTL ownership")
        if re.search(r"\bfunction\b[\s\S]{0,160}\b(message_byte|hex_ascii|ascii)\b", code, flags=re.IGNORECASE):
            hits.append(f"{path.name}: RTL formats protocol/message bytes")
        if re.search(r"=\s*\"[ -~]+\"", code):
            hits.append(f"{path.name}: synthesizable RTL contains literal ASCII/message text")
        if re.search(r"\bread\s+data\s*=", code, flags=re.IGNORECASE):
            hits.append(f"{path.name}: fixed read-data report text in RTL")
        if re.search(r"\b(SECOND_CYCLES|READ_CYCLES|DDR_TEST_ADDR)\b", code):
            hits.append(f"{path.name}: PS DDR/software timing modeled in RTL")
    if hits:
        return GateCheck("loop3_external_stimulus_boundary", "FAIL", "; ".join(hits))
    return GateCheck("loop3_external_stimulus_boundary", "PASS", "PS_PL bus/UART stimulus is outside synthesizable PL RTL")


def _strip_verilog_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


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
    plan = project / "work/loop3_fpga_proto" / "board_tests" / "prototype_plan.yaml"
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
    _sync_output_manifest(project, level=level, final_gate="PENDING")
    evidence = _node_evidence(project, "output")
    manifest_rel = _evidence_str(evidence, "reports", "manifest", "output/manifest.yaml")
    checks = _path_checks(project, [manifest_rel])
    checks.extend(_check_docset(project, ["application_guide", "microarchitecture_specification", "verification_plan", "delivery_package"], level=level))
    manifest = _read(_project_path(project, manifest_rel))
    for marker in _evidence_list(evidence, "required_markers", "manifest", ["loop1_gate: PASS", "loop2_gate: PASS", "loop3_gate: PASS"]):
        if marker.strip().startswith("final_gate:"):
            continue
        checks.append(_contains(f"manifest_{marker.split(':')[0]}", manifest, [marker]))
    for node in ["work/loop1_rtl_tb", "work/loop2_uvm", "work/loop3_fpga_proto"]:
        manifest_path = _latest_gate_manifest(project, node, level if level == "release" else None)
        if manifest_path:
            checks.append(GateCheck(f"{node}_gate_manifest", "PASS", str(manifest_path.relative_to(project))))
        else:
            expected = f"{level} " if level == "release" else ""
            checks.append(GateCheck(f"{node}_gate_manifest", "FAIL", f"missing passed {expected}gate manifest for {node}; run run-gate first"))
    if level == "release":
        checks.append(GateCheck("final_level", "PASS", "release final gate requested"))
    checks.append(_check_rtl_task_usage(project))
    checks.append(_check_forbidden_formal_text(project))
    return checks


def _path_checks(project: Path, rel_paths: list[str]) -> list[GateCheck]:
    checks = []
    for rel in rel_paths:
        path = _project_path(project, rel)
        status = "PASS" if path.exists() else "FAIL"
        detail = "exists" if path.exists() else "missing"
        checks.append(GateCheck(f"path:{rel}", status, detail))
    return checks


def _stage_report_required_rels(definition: StageReportDefinition) -> list[str]:
    return [
        definition.command_json,
        definition.command_md,
        definition.log_rel,
        definition.current_manifest,
        definition.report_md,
        definition.report_json,
        definition.report_manifest,
    ]


def _check_stage_report_contract(project: Path, definition: StageReportDefinition) -> tuple[list[GateCheck], dict[str, Any]]:
    checks = _path_checks(project, _stage_report_required_rels(definition))
    payload = _load_json_mapping(project / definition.report_json)
    checks.append(_stage_report_json_check(definition, payload))
    checks.append(_stage_report_markdown_shape_check(project, definition))
    checks.extend(_stage_report_manifest_checks(project, definition))
    checks.append(_stage_report_no_raw_logs_check(project, definition))
    checks.append(_stage_report_no_default_runs_check(project, definition))
    return checks, payload


def _stage_report_json_check(definition: StageReportDefinition, payload: dict[str, Any]) -> GateCheck:
    if not payload:
        return GateCheck(f"{definition.report_type}_report_json", "FAIL", f"{definition.report_json} is missing or invalid JSON")
    schema = payload.get("schema")
    if schema != definition.report_json_schema:
        return GateCheck(
            f"{definition.report_type}_report_json",
            "FAIL",
            f"schema must be {definition.report_json_schema}, got {schema}",
        )
    result = str(payload.get("result", "")).upper()
    if result not in {"PASS", "FAIL", "BLOCKED"}:
        return GateCheck(f"{definition.report_type}_report_json", "FAIL", f"result must be PASS, FAIL, or BLOCKED, got {result}")
    if payload.get("source") != {"cmd": definition.command_json, "manifest": definition.current_manifest}:
        return GateCheck(f"{definition.report_type}_report_json", "FAIL", "source must point to current command and run manifest")
    return GateCheck(f"{definition.report_type}_report_json", "PASS", f"{schema} result={result}")


def _stage_report_markdown_shape_check(project: Path, definition: StageReportDefinition) -> GateCheck:
    text = _read(project / definition.report_md)
    if not text:
        return GateCheck(f"{definition.report_type}_report_markdown_shape", "FAIL", f"{definition.report_md} is missing or empty")
    required = [
        f"report_schema: {REPORT_SCHEMA}",
        "## 0. Result",
        "## 1. Summary",
        "## 2. Main Results",
        "## 3. Failed Items",
        "## 4. Notes",
    ]
    missing = [marker for marker in required if marker not in text]
    if missing:
        return GateCheck(f"{definition.report_type}_report_markdown_shape", "FAIL", "missing section(s): " + ", ".join(missing))
    if re.search(r"(?im)^##\s+.*Evidence\b", text):
        return GateCheck(f"{definition.report_type}_report_markdown_shape", "FAIL", "report body must not contain an Evidence section")
    return GateCheck(f"{definition.report_type}_report_markdown_shape", "PASS", "unified report sections found and no Evidence section")


def _stage_report_manifest_checks(project: Path, definition: StageReportDefinition) -> list[GateCheck]:
    checks: list[GateCheck] = []
    command = _load_json_mapping(project / definition.command_json)
    current = _load_json_mapping(project / definition.current_manifest)
    report_manifest = _load_json_mapping(project / definition.report_manifest)
    checks.append(_json_schema_check(f"{definition.report_type}_command_schema", command, COMMAND_SCHEMA))
    checks.append(_json_schema_check(f"{definition.report_type}_current_manifest_schema", current, RUN_MANIFEST_SCHEMA))
    checks.append(_json_schema_check(f"{definition.report_type}_report_manifest_schema", report_manifest, REPORT_MANIFEST_SCHEMA))

    if current:
        entries = []
        command_entry = current.get("command")
        if isinstance(command_entry, dict):
            entries.append(command_entry)
        for key in ("logs", "generated_reports"):
            items = current.get(key)
            if isinstance(items, list):
                entries.extend(item for item in items if isinstance(item, dict))
        missing_hashes = [str(item.get("path", "")) for item in entries if item.get("sha256") in {None, "", "MISSING"}]
        if missing_hashes:
            checks.append(
                GateCheck(
                    f"{definition.report_type}_current_manifest_hashes",
                    "FAIL",
                    "manifest contains missing hash(es): " + ", ".join(missing_hashes[:6]),
                )
            )
        else:
            checks.append(GateCheck(f"{definition.report_type}_current_manifest_hashes", "PASS", f"{len(entries)} current artifact hash(es) recorded"))

    if report_manifest:
        expected_hashes = {
            "report_sha256": project / definition.report_md,
            "report_json_sha256": project / definition.report_json,
            "source_manifest_sha256": project / definition.current_manifest,
        }
        drift = [
            key
            for key, path in expected_hashes.items()
            if not path.is_file() or str(report_manifest.get(key)) != sha256_file(path)
        ]
        if drift:
            checks.append(GateCheck(f"{definition.report_type}_report_manifest_hashes", "FAIL", "hash drift: " + ", ".join(drift)))
        else:
            checks.append(GateCheck(f"{definition.report_type}_report_manifest_hashes", "PASS", "report manifest hashes match current artifacts"))
    return checks


def _json_schema_check(name: str, payload: dict[str, Any], schema: str) -> GateCheck:
    if not payload:
        return GateCheck(name, "FAIL", "missing or invalid JSON")
    actual = payload.get("schema")
    if actual != schema:
        return GateCheck(name, "FAIL", f"schema must be {schema}, got {actual}")
    return GateCheck(name, "PASS", f"schema {schema}")


def _stage_report_no_raw_logs_check(project: Path, definition: StageReportDefinition) -> GateCheck:
    root = project / definition.output_dir
    if not root.exists():
        return GateCheck(f"{definition.report_type}_report_no_raw_logs", "FAIL", f"{definition.output_dir} is missing")
    raw = [
        _rel(project, path)
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".log", ".out", ".txt"}
    ]
    if raw:
        return GateCheck(f"{definition.report_type}_report_no_raw_logs", "FAIL", "raw log artifact(s) under output/reports: " + ", ".join(raw[:6]))
    return GateCheck(f"{definition.report_type}_report_no_raw_logs", "PASS", "output/reports contains report artifacts only")


def _stage_report_no_default_runs_check(project: Path, definition: StageReportDefinition) -> GateCheck:
    forbidden = [
        project / definition.stage_dir / "runs",
        project / definition.output_dir / "runs",
    ]
    existing = [_rel(project, path) for path in forbidden if path.exists()]
    if existing:
        return GateCheck(f"{definition.report_type}_report_no_timestamp_runs", "FAIL", "default timestamp run archive exists: " + ", ".join(existing))
    return GateCheck(f"{definition.report_type}_report_no_timestamp_runs", "PASS", "no default timestamp run archive")


def _load_json_mapping(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _check_report_pass(name: str, payload: dict[str, Any]) -> GateCheck:
    result = str(payload.get("result", "MISSING")).upper() if payload else "MISSING"
    if result == "PASS":
        return GateCheck(name, "PASS", "structured report result PASS")
    return GateCheck(name, "FAIL", f"structured report result must be PASS, got {result}")


def _check_report_transactions(name: str, payload: dict[str, Any]) -> GateCheck:
    transactions = payload.get("transactions") if isinstance(payload, dict) else None
    if not isinstance(transactions, list) or not transactions:
        return GateCheck(name, "FAIL", "report.json must contain at least one checked transaction")
    required = ["test_id", "txn_id", "sent", "expected", "actual", "result"]
    failures: list[str] = []
    for index, item in enumerate(transactions, start=1):
        if not isinstance(item, dict):
            failures.append(f"transaction[{index}] is not an object")
            continue
        missing = [field for field in required if item.get(field) in {None, ""}]
        if missing:
            failures.append(f"transaction[{index}] missing " + ", ".join(missing))
        if str(item.get("result", "")).upper() != "PASS":
            failures.append(f"transaction[{index}] result={item.get('result')}")
    if failures:
        return GateCheck(name, "FAIL", "; ".join(failures[:6]))
    return GateCheck(name, "PASS", f"{len(transactions)} structured transaction(s) checked")


def _check_report_parser_clean(name: str, payload: dict[str, Any]) -> GateCheck:
    parser_errors = payload.get("parser_errors") if isinstance(payload, dict) else None
    if isinstance(parser_errors, list) and parser_errors:
        return GateCheck(name, "FAIL", "parser error(s): " + "; ".join(str(item) for item in parser_errors[:6]))
    return GateCheck(name, "PASS", "no structured parser errors")


def _summary_int(payload: dict[str, Any], key: str) -> int:
    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    try:
        return int(summary.get(key, 0))
    except (TypeError, ValueError):
        return 0


def _summary_float(payload: dict[str, Any], key: str) -> float | None:
    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    value = summary.get(key)
    if value is None:
        return None
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", str(value))
    if not match:
        return None
    return float(match.group(1))


def _report_payload_evidence_text(payload: dict[str, Any]) -> str:
    chunks: list[str] = []
    if isinstance(payload, dict):
        chunks.append(json.dumps(payload.get("summary", {}), ensure_ascii=False, sort_keys=True))
        transactions = payload.get("transactions", [])
        if isinstance(transactions, list):
            for item in transactions:
                chunks.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
    return "\n".join(chunks)


def _check_prerequisite_gate(project: Path, node: str, detail: str) -> list[GateCheck]:
    manifest = _latest_gate_manifest(project, node)
    if not manifest:
        return [GateCheck(f"prerequisite:{node}", "FAIL", f"{detail}; missing passed gate manifest for {node}")]
    return [GateCheck(f"prerequisite:{node}", "PASS", str(manifest.relative_to(project)))]


def _check_loop2_uvm_policy(project: Path) -> list[GateCheck]:
    node_cfg = _node_config(project, "work/loop2_uvm")
    policy = node_cfg.get("uvm_policy", {})
    if not isinstance(policy, dict):
        return [GateCheck("loop2_uvm_policy", "FAIL", "uvm_policy must be configured")]

    checks: list[GateCheck] = []
    if policy.get("database_preflight_required", True):
        preflight_rel = str(policy.get("database_preflight_report") or "output/reports/loop2/preflight/database_preflight.md")
        preflight_path = _project_path(project, preflight_rel)
        if preflight_path.exists():
            preflight = _read(preflight_path)
            checks.append(GateCheck("loop2_database_preflight_report_available", "PASS", preflight_rel))
            checks.append(_contains_any("loop2_database_preflight_pass", preflight, ["result: PASS"]))
        else:
            checks.append(GateCheck("loop2_database_preflight_report_available", "FAIL", f"missing {preflight_rel}"))

    if policy.get("flesh_plan_required", True):
        flesh_plan_rel = str(policy.get("flesh_plan_report") or "output/reports/loop2/preflight/uvm_flesh_plan.md")
        flesh_plan_path = _project_path(project, flesh_plan_rel)
        if flesh_plan_path.exists():
            flesh_plan = _read(flesh_plan_path)
            checks.append(GateCheck("loop2_uvm_flesh_plan_available", "PASS", flesh_plan_rel))
            checks.append(_contains_any("loop2_uvm_flesh_plan_pass", flesh_plan, ["result: PASS"]))
        else:
            checks.append(GateCheck("loop2_uvm_flesh_plan_available", "FAIL", f"missing {flesh_plan_rel}"))

    if policy.get("baseline_artifacts_transient", True):
        legacy_entry_report = project / "output" / "reports" / "loop2" / "loop2_uvm_baseline_report.md"
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
        uvm_root = project / "output" / "uvm"
        templates = sorted(uvm_root.rglob("*.template")) if uvm_root.exists() else []
        if templates:
            rels = ", ".join(_rel(project, path) for path in templates[:8])
            checks.append(GateCheck("loop2_no_template_artifacts", "FAIL", f"template artifact(s) remain under output/uvm: {rels}"))
        else:
            checks.append(GateCheck("loop2_no_template_artifacts", "PASS", "no .template files under output/uvm"))

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
        uvm_root = project / "output" / "uvm"
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


def _check_docparse_extract_policy(project: Path) -> GateCheck:
    parsed_root = project / "work/docparse" / "parsed"
    extract_root = parsed_root / "mineru_extract"
    if not parsed_root.exists():
        return GateCheck("docparse_extract_policy", "FAIL", "work/docparse/parsed is missing")
    foreign_files = sorted(
        path for path in parsed_root.rglob("*")
        if path.is_file() and extract_root not in path.parents
    )
    if foreign_files:
        rels = ", ".join(_rel(project, path) for path in foreign_files[:8])
        return GateCheck(
            "docparse_extract_policy",
            "FAIL",
            "parsed document files outside work/docparse/parsed/mineru_extract are not accepted: " + rels,
        )
    extract_files = sorted(path for path in extract_root.rglob("*") if path.is_file()) if extract_root.exists() else []
    illegal_records = [path for path in extract_files if path.name.lower() in ILLEGAL_DOCPARSE_EVIDENCE_NAMES]
    if illegal_records:
        rels = ", ".join(_rel(project, path) for path in illegal_records[:8])
        return GateCheck(
            "docparse_extract_policy",
            "FAIL",
            "operation records are not parser output and must not be stored as DocParse parsed evidence: " + rels,
        )
    chat_only_check = _check_chat_only_docparse_policy(project)
    if chat_only_check is not None:
        return chat_only_check
    if not extract_files:
        return GateCheck("docparse_extract_policy", "FAIL", "parsed document output must use work/docparse/parsed/mineru_extract")
    provenance = extract_root / "provenance.yaml"
    if not provenance.is_file():
        return GateCheck("docparse_extract_policy", "FAIL", "missing parser provenance: work/docparse/parsed/mineru_extract/provenance.yaml")
    try:
        provenance_data = load_yaml(provenance)
    except Exception as exc:
        return GateCheck("docparse_extract_policy", "FAIL", f"cannot read parser provenance: {exc}")
    if not isinstance(provenance_data, dict):
        return GateCheck("docparse_extract_policy", "FAIL", "parser provenance must be a mapping")
    tool = str(provenance_data.get("tool", "")).strip()
    command = str(provenance_data.get("command", "")).strip()
    channel = str(provenance_data.get("channel", "")).strip()
    api_mode = str(provenance_data.get("api_mode", "")).strip().lower()
    if tool != "mineru-open-api" or command != "extract" or channel != MINERU_HIGH_PRECISION_CHANNEL:
        return GateCheck(
            "docparse_extract_policy",
            "FAIL",
            (
                "parser provenance must declare tool=mineru-open-api, command=extract, "
                f"channel='{MINERU_HIGH_PRECISION_CHANNEL}'"
            ),
        )
    if api_mode != "high_precision":
        return GateCheck("docparse_extract_policy", "FAIL", "parser provenance api_mode must be high_precision")
    endpoints = _provenance_endpoint_set(provenance_data)
    if not (endpoints & MINERU_HIGH_PRECISION_ENDPOINTS):
        required = ", ".join(sorted(MINERU_HIGH_PRECISION_ENDPOINTS))
        return GateCheck(
            "docparse_extract_policy",
            "FAIL",
            "parser provenance must include high-precision API endpoint evidence: " + required,
        )
    manual_record_refs = _provenance_manual_record_refs(provenance_data)
    if manual_record_refs:
        return GateCheck(
            "docparse_extract_policy",
            "FAIL",
            "parser provenance must not link operation, violation, or manual review records: "
            + ", ".join(manual_record_refs[:8]),
        )
    operation_record = str(provenance_data.get("operation_record", "")).replace("\\", "/").lower()
    if "work/docparse/parsed/mineru_extract/" in operation_record:
        return GateCheck(
            "docparse_extract_policy",
            "FAIL",
            "parser provenance must not point operation records into work/docparse/parsed/mineru_extract",
        )
    content_files = [
        path
        for path in extract_files
        if path.name != "provenance.yaml"
        and path.name.lower() not in ILLEGAL_DOCPARSE_EVIDENCE_NAMES
        and path.suffix.lower() in PARSER_OUTPUT_SUFFIXES
        and path.stat().st_size > 0
    ]
    if not content_files:
        return GateCheck("docparse_extract_policy", "FAIL", "MinerU high-precision API produced no parsed content files")
    return GateCheck("docparse_extract_policy", "PASS", f"{len(content_files)} parsed content file(s) from MinerU high-precision API")


def _check_chat_only_docparse_policy(project: Path) -> GateCheck | None:
    analysis_path = project / DOCUMENT_ANALYSIS_REL
    if not analysis_path.is_file():
        return None
    try:
        analysis = load_yaml(analysis_path)
    except Exception as exc:
        return GateCheck("docparse_extract_policy", "FAIL", f"cannot read chat-source document analysis: {exc}")
    if not isinstance(analysis, dict):
        return GateCheck("docparse_extract_policy", "FAIL", "chat-source document analysis must be a mapping")

    source_documents = _as_list(analysis.get("source_documents"))
    chat_docs = [
        item for item in source_documents
        if isinstance(item, dict) and str(item.get("parser_output", "")).strip() in CHAT_ONLY_PARSER_OUTPUTS
    ]
    if not chat_docs:
        return None

    errors: list[str] = []
    unsupported = []
    for item in source_documents:
        if not isinstance(item, dict):
            errors.append("document_analysis.source_documents entries must be mappings")
            continue
        parser_output = str(item.get("parser_output", "")).strip()
        if parser_output not in CHAT_ONLY_PARSER_OUTPUTS | CHAT_ONLY_SUPPORT_OUTPUTS:
            unsupported.append(parser_output or "<missing>")
    if unsupported:
        errors.append(
            "chat-only DocParse may reference only chat captures or local structured support sources; "
            "MinerU is still required for parser_output(s): " + ", ".join(sorted(set(unsupported))[:8])
        )

    for item in chat_docs:
        source_ref = str(item.get("source_ref", "")).strip()
        source_path = _project_path(project, source_ref)
        if not source_ref.startswith(f"{SPEC_INPUT_REL}/"):
            errors.append(f"chat source must live under {SPEC_INPUT_REL}: {source_ref or '<missing>'}")
            continue
        if not source_path.is_file():
            errors.append(f"chat source file is missing: {source_ref}")
            continue
        source_text = source_path.read_text(encoding="utf-8", errors="ignore").lower()
        if "source_type: chat_request" not in source_text:
            errors.append(f"chat source must declare source_type: chat_request: {source_ref}")

    if not _as_list(analysis.get("analysis_units")):
        errors.append(f"{DOCUMENT_ANALYSIS_REL} analysis_units must be non-empty for chat-only DocParse")
    if not _as_list(analysis.get("evidence_map")):
        errors.append(f"{DOCUMENT_ANALYSIS_REL} evidence_map must be non-empty for chat-only DocParse")

    if errors:
        return GateCheck("docparse_extract_policy", "FAIL", "; ".join(errors[:8]))
    return GateCheck("docparse_extract_policy", "PASS", f"{len(chat_docs)} chat requirement source(s) accepted without MinerU")


def _docparse_uses_chat_only_sources(project: Path) -> bool:
    check = _check_chat_only_docparse_policy(project)
    return check is not None and check.status == "PASS"


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _provenance_manual_record_refs(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key).lower()
            child_path = f"{path}.{key}" if path else str(key)
            if any(marker in key_text for marker in ILLEGAL_PROVENANCE_RECORD_MARKERS):
                hits.append(child_path)
            hits.extend(_provenance_manual_record_refs(item, child_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            hits.extend(_provenance_manual_record_refs(item, f"{path}[{index}]"))
    elif isinstance(value, str):
        text = value.replace("\\", "/").lower()
        if any(marker in text for marker in ILLEGAL_PROVENANCE_RECORD_MARKERS):
            hits.append(path or "value")
    return hits


def _provenance_endpoint_set(provenance_data: dict[str, Any]) -> set[str]:
    raw_values: list[Any] = []
    for key in ("api_endpoints", "endpoints"):
        value = provenance_data.get(key)
        if isinstance(value, list):
            raw_values.extend(value)
        elif isinstance(value, str):
            raw_values.append(value)
    for key in ("api_endpoint", "endpoint"):
        value = provenance_data.get(key)
        if isinstance(value, str):
            raw_values.append(value)
    endpoints: set[str] = set()
    for value in raw_values:
        text = str(value).strip()
        if not text:
            continue
        match = re.search(r"(/api/v4/[A-Za-z0-9_./-]+)", text)
        endpoints.add(match.group(1) if match else text)
    return endpoints


def _normalize_opcode_token(value: Any) -> str:
    if isinstance(value, int):
        return f"{value:02X}h"
    text = str(value).strip()
    if text.lower().startswith("0x"):
        text = text[2:]
    if text.lower().endswith("h"):
        text = text[:-1]
    return text.upper().zfill(2) + "h"


def _docparse_required_opcode_tokens(project: Path) -> list[str]:
    register_map_path = project / "work/docparse" / "structured_spec" / "register_map.yaml"
    if register_map_path.exists():
        register_map = load_yaml(register_map_path)
        opcodes = register_map.get("opcodes") if isinstance(register_map, dict) else None
        if isinstance(opcodes, list):
            tokens: list[str] = []
            for item in opcodes:
                if isinstance(item, dict) and "code" in item:
                    tokens.append(_normalize_opcode_token(item["code"]))
            if tokens:
                return tokens

    policy = _node_config(project, "work/loop1_rtl_tb").get("directed_test_policy", {})
    explicit = bool(policy.get("required_opcodes_explicit")) if isinstance(policy, dict) else False
    configured = policy.get("required_opcodes") if isinstance(policy, dict) else None
    if explicit and isinstance(configured, list):
        return [_normalize_opcode_token(item) for item in configured]
    return []


def _check_docparse_verification_breadth(project: Path) -> GateCheck:
    intent = _read(project / "work/docparse" / "structured_spec" / "test_intent.yaml")
    verification = _read(project / "work/docparse" / "verification" / "verification_plan.yaml")
    text = intent + "\n" + verification
    missing_opcodes = []
    for token in _docparse_required_opcode_tokens(project):
        if token not in text and token.lower() not in text:
            missing_opcodes.append(token)
    required_terms = [
        "scenario_tests",
        "stress_tests",
        "directed",
        "FIFO pressure",
        "PS+PL",
    ]
    missing_terms = [term for term in required_terms if term.lower() not in text.lower()]
    missing = [*missing_opcodes, *missing_terms]
    if missing:
        return GateCheck("docparse_test_analysis_breadth", "FAIL", "verification planning is incomplete: " + ", ".join(missing))
    return GateCheck("docparse_test_analysis_breadth", "PASS", "source-bound opcodes plus scenario/stress/prototype analysis are planned")


def _check_no_ad_hoc_analysis_artifacts(project: Path) -> GateCheck:
    roots = [
        project / SPEC_INPUT_REL,
        project / "work/docparse",
        project / "output" / "reports" / "design",
    ]
    forbidden: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            rel = _rel(project, path)
            rel_posix = rel.replace("\\", "/")
            name = path.name.lower()
            if _is_allowed_docparse_markdown(rel_posix):
                continue
            if _is_parsed_extract_markdown(rel_posix):
                continue
            if _is_generated_design_report_markdown(rel_posix):
                continue
            forbidden_reason = (
                "design_draft" in name
                or name.endswith("_draft.md")
                or name.startswith("draft_")
                or name == "scope.md"
                or name.endswith("_scope.md")
                or "design_blueprint" in name
                or "implementation_analysis" in name
                or name.endswith("_analysis.md")
            )
            if forbidden_reason or root.name in {"docparse", "design"}:
                forbidden.append(rel)
    if forbidden:
        return GateCheck(
            "docparse_no_ad_hoc_analysis_artifacts",
            "FAIL",
            "ad hoc scope, analysis, design blueprint, or draft files are not gate artifacts; decompose requirements first, then generate the docset from front-door outputs: "
            + ", ".join(forbidden[:8]),
        )
    return GateCheck("docparse_no_ad_hoc_analysis_artifacts", "PASS", "no ad hoc scope, analysis, or draft artifacts found")


def _check_forbidden_formal_text(project: Path) -> GateCheck:
    suffixes = {".md", ".yaml", ".yml", ".json", ".v", ".sv", ".svh", ".txt", ".log", ".rpt", ".tcl"}
    hits: list[str] = []
    for rel_root in FORMAL_TEXT_SCAN_ROOTS:
        root = project / rel_root
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(pattern.search(text) for pattern in FORBIDDEN_FORMAL_TEXT_PATTERNS):
                hits.append(_rel(project, path))
    if hits:
        return GateCheck(
            "forbidden_formal_text",
            "FAIL",
            "forbidden workflow vocabulary found in formal artifact(s): " + ", ".join(hits[:10]),
        )
    return GateCheck("forbidden_formal_text", "PASS", "formal artifacts contain no forbidden workflow vocabulary")


def _is_allowed_docparse_markdown(rel_posix: str) -> bool:
    if rel_posix in SPEC_REQUIREMENTS_ALLOWED_MARKDOWN:
        return True
    if rel_posix in DOC_PARSE_ALLOWED_MARKDOWN_RELS:
        return True
    return False


def _is_parsed_extract_markdown(rel_posix: str) -> bool:
    return rel_posix.startswith("work/docparse/parsed/mineru_extract/") and rel_posix.endswith(".md")


def _is_generated_design_report_markdown(rel_posix: str) -> bool:
    return rel_posix in DESIGN_REPORT_ALLOWED_MARKDOWN


def _check_rtl_skill_audit_freshness(project: Path) -> GateCheck:
    try:
        result = run_rtl_skill_audit(project)
    except Exception as exc:
        return GateCheck("rtl_skill_per_file_audit", "FAIL", f"failed to run platform RTL skill audit: {exc}")
    if result.ok:
        return GateCheck(
            "rtl_skill_per_file_audit",
            "PASS",
            f"platform-generated RTL skill audit passed for {len(result.file_results)} file(s)",
        )

    issue_count = sum(len(item.issues) for item in result.file_results)
    details = list(result.errors)
    for item in result.file_results:
        if item.issues:
            details.append(f"{item.rel_path}: " + "; ".join(item.issues[:3]))
    suffix = "; ".join(details[:8]) if details else f"{issue_count} RTL skill issue(s)"
    return GateCheck("rtl_skill_per_file_audit", "FAIL", suffix)


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


def _structured_result_pass_check(name: str, text: str) -> GateCheck:
    fail_lines = [
        line.strip()
        for line in text.splitlines()
        if re.search(r"(?im)^\s*(?:[-*]\s*)?result\s*[:=]\s*FAIL\s*$", line)
        or re.search(r"(?im)^\s*\|\s*[^|]+\|\s*[^|]+\|\s*[^|]+\|\s*[^|]+\|\s*FAIL\s*\|", line)
    ]
    if fail_lines:
        return GateCheck(name, "FAIL", "structured FAIL result found: " + "; ".join(fail_lines[:4]))
    if re.search(r"(?im)^\s*(?:[-*]\s*)?result\s*[:=]\s*PASS\s*$", text):
        return GateCheck(name, "PASS", "structured result: PASS")
    return GateCheck(name, "FAIL", "missing structured result: PASS")


def _zero_count_check(name: str, text: str, label: str) -> GateCheck:
    pattern = rf"(?im)(?:^|\b){re.escape(label)}\s*(?:[:|=]|\s)\s*([0-9]+)\b"
    counts = [int(match.group(1)) for match in re.finditer(pattern, text)]
    if not counts:
        return GateCheck(name, "FAIL", f"{label} count marker not found")
    nonzero = [count for count in counts if count != 0]
    if nonzero:
        return GateCheck(name, "FAIL", f"{label} nonzero count(s) found: " + ", ".join(str(count) for count in nonzero[:4]))
    return GateCheck(name, "PASS", f"all {len(counts)} {label} count marker(s) are zero")


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


def _check_loop2_zero_counts(report_payload: dict[str, Any]) -> GateCheck:
    uvm_error = _summary_int(report_payload, "uvm_error")
    uvm_fatal = _summary_int(report_payload, "uvm_fatal")
    failed_checks = _summary_int(report_payload, "failed_checks")
    if uvm_error or uvm_fatal or failed_checks:
        return GateCheck(
            "loop2_zero_error_counts",
            "FAIL",
            f"uvm_error={uvm_error}, uvm_fatal={uvm_fatal}, failed_checks={failed_checks}",
        )
    return GateCheck("loop2_zero_error_counts", "PASS", "uvm_error=0, uvm_fatal=0, failed_checks=0")


def _loop2_coverage_summary_check(project: Path, report_payload: dict[str, Any], level: str) -> GateCheck:
    threshold = _threshold(project, level, "functional")
    value = _summary_float(report_payload, "coverage")
    if value is None:
        return GateCheck("loop2_functional_coverage", "FAIL", "coverage value missing from loop2_report.json summary")
    if threshold is not None and value < threshold:
        return GateCheck("loop2_functional_coverage", "FAIL", f"{value:.2f}% below threshold {threshold:.2f}%")
    if threshold is None:
        return GateCheck("loop2_functional_coverage", "PASS", f"{value:.2f}% reported; no threshold for this gate level")
    return GateCheck("loop2_functional_coverage", "PASS", f"{value:.2f}% >= {threshold:.2f}%")


def _loop2_transaction_count_check(project: Path, report_payload: dict[str, Any]) -> GateCheck:
    policy = _node_config(project, "work/loop2_uvm").get("uvm_policy", {})
    min_count = 64
    if isinstance(policy, dict):
        try:
            min_count = int(policy.get("min_checked_transactions", min_count))
        except (TypeError, ValueError):
            return GateCheck("loop2_checked_transaction_count", "FAIL", "uvm_policy.min_checked_transactions must be an integer")
    count = _summary_int(report_payload, "total_checks")
    if count <= 0 and isinstance(report_payload, dict):
        transactions = report_payload.get("transactions")
        count = len(transactions) if isinstance(transactions, list) else 0
    if count < min_count:
        return GateCheck("loop2_checked_transaction_count", "FAIL", f"{count} checked transaction(s) below minimum {min_count}")
    return GateCheck("loop2_checked_transaction_count", "PASS", f"{count} checked transaction(s) >= {min_count}")


def _loop2_scenario_count_check(project: Path) -> GateCheck:
    policy = _loop2_policy(project)
    try:
        minimum = int(policy.get("min_scenario_tests", 5))
    except (TypeError, ValueError):
        return GateCheck("loop2_min_scenario_tests", "FAIL", "uvm_policy.min_scenario_tests must be an integer")

    haystack = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in _source_files_by_suffix(project, {"output/uvm": {".sv", ".svh"}})
    )
    class_names = {
        match.group(1)
        for match in re.finditer(r"\bclass\s+([A-Za-z0-9_]*(?:scenario|sequence|vseq|test)[A-Za-z0-9_]*)\b", haystack)
    }
    scenario_names = {
        name
        for name in class_names
        if not re.match(r"^(base|dut_|spi_|uvm_)", name)
        and name not in {"full_functional_test"}
    }
    if len(scenario_names) < minimum:
        return GateCheck(
            "loop2_min_scenario_tests",
            "FAIL",
            f"{len(scenario_names)} scenario/test sequence class(es) found, minimum is {minimum}",
        )
    return GateCheck("loop2_min_scenario_tests", "PASS", f"{len(scenario_names)} scenario/test sequence class(es) found")


def _loop2_stress_transaction_check(project: Path) -> GateCheck:
    policy = _loop2_policy(project)
    try:
        minimum = int(policy.get("min_stress_stimuli_per_transaction", 2))
    except (TypeError, ValueError):
        return GateCheck("loop2_stress_multi_stimulus", "FAIL", "uvm_policy.min_stress_stimuli_per_transaction must be an integer")

    uvm_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in _source_files_by_suffix(project, {"output/uvm": {".sv", ".svh"}})
    )
    stress_blocks = [
        match.group(1)
        for match in re.finditer(
            r"\bclass\s+[A-Za-z0-9_]*stress[A-Za-z0-9_]*\b(.*?)(?=\n\s*class\s+|\Z)",
            uvm_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
    ]
    if not stress_blocks:
        return GateCheck("loop2_stress_multi_stimulus", "FAIL", "no stress sequence/test class found")

    stimulus_patterns = [
        r"\bstart_kind\s*\(",
        r"\bspi_(?:write|read|opcode|transfer)",
        r"\buvm_do(?:_with)?\s*\(",
        r"\bseq\.start\s*\(",
        r"\brepeat\s*\(",
    ]
    best = 0
    for block in stress_blocks:
        count = sum(len(re.findall(pattern, block, flags=re.IGNORECASE)) for pattern in stimulus_patterns)
        best = max(best, count)
    if best < minimum:
        return GateCheck(
            "loop2_stress_multi_stimulus",
            "FAIL",
            f"stress sequence has {best} stimulus operation(s), minimum is {minimum}",
        )
    return GateCheck("loop2_stress_multi_stimulus", "PASS", f"stress sequence has at least {best} stimulus operation(s)")


def _loop2_coverage_triage_check(project: Path, coverage: str) -> GateCheck:
    policy = _loop2_policy(project)
    if not _policy_bool(policy, "coverage_triage_required", True):
        return GateCheck("loop2_coverage_triage_closed", "PASS", "coverage triage closure not required by policy")
    unresolved = _coverage_triage_unresolved_items(coverage)
    if not unresolved:
        return GateCheck("loop2_coverage_triage_closed", "PASS", "no unresolved coverage triage rows found")
    closed = _coverage_triage_closure_items(project)
    missing = [item for item in unresolved if _coverage_item_key(item) not in closed]
    if not missing:
        return GateCheck("loop2_coverage_triage_closed", "PASS", f"{len(unresolved)} coverage triage row(s) have row-level closure")
    return GateCheck(
        "loop2_coverage_triage_closed",
        "FAIL",
        f"{len(missing)} coverage triage row(s) still need row-level classification/waiver: " + ", ".join(missing[:6]),
    )


def _loop2_bound_assertion_check(project: Path) -> GateCheck:
    policy = _loop2_policy(project)
    if not _policy_bool(policy, "bound_assertions_required", True):
        return GateCheck("loop2_bound_assertions_present", "PASS", "bound assertions not required by policy")
    root = project / "output" / "uvm" / "assertions"
    files = sorted(path for path in root.glob("*") if path.is_file() and path.suffix.lower() in {".sv", ".svh"} and path.suffix.lower() != ".template")
    if not files:
        return GateCheck("loop2_bound_assertions_present", "FAIL", "no real SVA/bind files under output/uvm/assertions")
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
    tests = project / "output" / "uvm" / "tests" / "tests.svh"
    text = _read(tests)
    if re.search(r"\bsample_scenario\s*\(", text):
        return GateCheck(
            "loop2_functional_coverage_observed",
            "FAIL",
            "tests.svh calls sample_scenario directly; functional coverage must be sampled from observed monitor/scoreboard transactions",
        )
    coverage_text = _read(project / "output" / "uvm" / "cov" / "coverage.sv")
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
        for path in _source_files_by_suffix(project, {"output/uvm": {".sv", ".svh"}, "work/loop2_uvm/sim": {".do"}})
    )
    missing = [name for name in names if not any(re.search(pattern, haystack, flags=re.IGNORECASE | re.DOTALL) for pattern in patterns[name])]
    if missing:
        return GateCheck("loop2_stimulus_breadth", "FAIL", "missing required stress stimulus: " + ", ".join(missing))
    return GateCheck("loop2_stimulus_breadth", "PASS", "required stress stimulus patterns found")


def _coverage_triage_unresolved_items(coverage: str) -> list[str]:
    items: list[str] = []
    for line in coverage.splitlines():
        if "Classify as " not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        item = cells[0] if cells and cells[0] else line.strip()
        if item and item not in items:
            items.append(item)
    return items


def _coverage_triage_closure_items(project: Path) -> set[str]:
    closed: set[str] = set()
    waiver = project / "work" / "gates" / "coverage_waiver.json"
    try:
        data = json.loads(waiver.read_text(encoding="utf-8")) if waiver.exists() else {}
    except Exception:
        data = {}
    if isinstance(data, dict):
        waivers = data.get("waivers")
        if isinstance(waivers, list):
            for item in waivers:
                closure_item = _coverage_closure_item_from_mapping(item)
                if closure_item:
                    closed.add(_coverage_item_key(closure_item))
    tracking = project / "work/loop2_uvm" / "coverage_tracking"
    if tracking.exists():
        for path in tracking.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".md", ".yaml", ".yml", ".json", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if path.suffix.lower() == ".json":
                try:
                    payload = json.loads(text)
                except Exception:
                    payload = None
                closed.update(_coverage_closure_items_from_json(payload))
            closed.update(_coverage_closure_items_from_text(text))
    return closed


def _coverage_triage_has_closure_record(project: Path) -> bool:
    return bool(_coverage_triage_closure_items(project))


def _coverage_closure_items_from_json(payload: Any) -> set[str]:
    closed: set[str] = set()
    if isinstance(payload, dict):
        for key in ("closures", "waivers", "items"):
            items = payload.get(key)
            if isinstance(items, list):
                for item in items:
                    closure_item = _coverage_closure_item_from_mapping(item)
                    if closure_item:
                        closed.add(_coverage_item_key(closure_item))
        closure_item = _coverage_closure_item_from_mapping(payload)
        if closure_item:
            closed.add(_coverage_item_key(closure_item))
    elif isinstance(payload, list):
        for item in payload:
            closure_item = _coverage_closure_item_from_mapping(item)
            if closure_item:
                closed.add(_coverage_item_key(closure_item))
    return closed


def _coverage_closure_item_from_mapping(item: Any) -> str | None:
    if not isinstance(item, dict):
        return None
    status = str(item.get("status") or item.get("state") or "").strip().lower()
    classification = str(item.get("classification") or item.get("disposition") or item.get("reason") or item.get("type") or "").strip().lower()
    approved = bool(item.get("approved"))
    has_closed_status = status in {"approved", "accepted", "closed", "resolved", "waived"} or approved
    has_classification = any(marker in classification for marker in ["unreachable", "missing legal stimulus", "waiver", "waived", "covered"])
    if not has_closed_status or not has_classification:
        return None
    explicit = item.get("item") or item.get("coverage_item") or item.get("target")
    if explicit:
        return str(explicit).strip()
    file_name = item.get("file") or item.get("rtl_file")
    metric = item.get("metric") or item.get("coverage_type") or item.get("kind")
    if file_name and metric:
        return f"{file_name} {metric}".strip()
    return None


def _coverage_closure_items_from_text(text: str) -> set[str]:
    closed: set[str] = set()
    for line in text.splitlines():
        lower = line.lower()
        if not any(marker in lower for marker in ["unreachable", "missing legal stimulus", "waiver", "waived"]):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] and cells[0].lower() not in {"item", "---"}:
            closed.add(_coverage_item_key(cells[0]))
            continue
        match = re.search(r"\bitem\s*[:=]\s*([^,;#]+)", line, flags=re.IGNORECASE)
        if match:
            closed.add(_coverage_item_key(match.group(1)))
    return closed


def _coverage_item_key(item: str) -> str:
    item = item.strip().strip("`'\"")
    item = re.sub(r"\s+", " ", item)
    return item.lower()


def _loop2_policy(project: Path) -> dict[str, Any]:
    policy = _node_config(project, "work/loop2_uvm").get("uvm_policy", {})
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


def _check_docset(project: Path, required_docs: list[str], *, level: str = "develop") -> list[GateCheck]:
    result = check_docset(project, level=level, required_docs=required_docs)
    checks = [
        GateCheck(
            "docset_sync",
            "PASS" if result.ok else "FAIL",
            f"{DOCSET_MANIFEST_REL} synchronized" if result.ok else "; ".join(result.errors),
        )
    ]
    for warning in result.warnings:
        checks.append(GateCheck("docset_warning", "PASS", warning))
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


def _requires_docparse_reentry(node: str) -> bool:
    return node in {
        "work/loop1_rtl_tb",
        "work/loop2_uvm",
        "work/loop3_fpga_proto",
        "output",
    }


def _check_requirements_reentered_docparse(project: Path) -> list[GateCheck]:
    req_sources = _requirement_source_files(project)
    if not req_sources:
        return [GateCheck("requirements_docparse_reentry", "FAIL", f"no requirement files found under {SPEC_INPUT_REL}")]

    manifest = _latest_gate_manifest(project, "work/docparse")
    if not manifest:
        return [
            GateCheck(
                "requirements_docparse_reentry",
                "FAIL",
                "DocParse gate must pass after requirements are documented and before downstream loops run",
            )
        ]

    newest_req = max(path.stat().st_mtime for path in req_sources if path.exists())
    if newest_req > manifest.stat().st_mtime:
        newest_path = max((path for path in req_sources if path.exists()), key=lambda path: path.stat().st_mtime)
        return [
            GateCheck(
                "requirements_docparse_reentry",
                "FAIL",
                f"requirements changed after latest DocParse gate ({_rel(project, newest_path)}); rerun work/docparse before Loop1/Loop2/Loop3",
            )
        ]

    return [
        GateCheck(
            "requirements_docparse_reentry",
            "PASS",
            f"latest DocParse manifest {manifest.name} is newer than requirement files",
        )
    ]


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
    removed = sorted(rel for rel in previous_paths - current_paths if not _manifest_rel_exists(project, rel))
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
        changed = sorted(set(changed))
        allowed = _change_request_allowed_artifacts(project, change_id)
        if not allowed:
            return [
                GateCheck(
                    "artifact_hash_drift",
                    "FAIL",
                    f"{change_id} impact analysis must list changed source artifact path(s) under ## Artifacts",
                )
            ]
        unscoped = [rel for rel in changed if not _change_scope_covers(rel, allowed)]
        if unscoped:
            return [
                GateCheck(
                    "artifact_hash_drift",
                    "FAIL",
                    f"{len(unscoped)} source hash change(s) are not covered by {change_id} impact artifacts: "
                    + ", ".join(unscoped[:8]),
                )
            ]
        return [GateCheck("artifact_hash_drift", "PASS", f"{len(changed)} source hash change(s) are covered by {change_id} impact artifacts")]
    return [
        GateCheck(
            "artifact_hash_drift",
            "FAIL",
            f"{len(changed)} source hash change(s) since previous gate; open/approve a change request and pass --change-id",
        )
    ]


def _change_request_allowed_artifacts(project: Path, change_id: str) -> set[str]:
    impact = project / "work/change" / "impact_analysis" / f"{change_id}.md"
    if not impact.exists():
        return set()
    return _impact_analysis_artifact_paths(impact.read_text(encoding="utf-8", errors="ignore"))


def _impact_analysis_artifact_paths(text: str) -> set[str]:
    paths: set[str] = set()
    in_artifacts = False
    for line in text.splitlines():
        header = re.match(r"^\s*##+\s+(.+?)\s*$", line)
        if header:
            title = header.group(1).strip().lower()
            if in_artifacts and "artifact" not in title:
                break
            in_artifacts = "artifact" in title
            continue
        if not in_artifacts:
            continue
        bullet = re.match(r"^\s*[-*]\s+(.+?)\s*$", line)
        if not bullet:
            continue
        candidate = _clean_impact_artifact_token(bullet.group(1))
        if candidate:
            paths.add(candidate)
    return paths


def _clean_impact_artifact_token(text: str) -> str | None:
    text = text.strip()
    quoted = re.search(r"`([^`]+)`", text)
    if quoted:
        text = quoted.group(1)
    else:
        text = re.split(r"\s+-\s+|\s+#|\s+\(|\s+--\s+", text, maxsplit=1)[0]
        if ":" in text and not re.match(r"^[A-Za-z]:", text):
            text = text.split(":", 1)[0]
    text = text.strip().strip("`'\"").replace("\\", "/")
    if not text or text.lower() in {"none", "n/a", "na"}:
        return None
    if Path(text).is_absolute() or text.startswith("../") or "/../" in text:
        return None
    return text.rstrip("/") + ("/" if text.endswith("/") else "")


def _change_scope_covers(rel: str, allowed: set[str]) -> bool:
    rel = rel.replace("\\", "/")
    rel_options = {rel, rel.removeprefix("workspace:")}
    if not rel.startswith("workspace:") and not rel.startswith("external:"):
        rel_options.add("workspace:" + rel)
    for pattern in allowed:
        normalized = pattern.replace("\\", "/")
        pattern_options = {normalized, normalized.removeprefix("workspace:")}
        if not normalized.startswith("workspace:") and not normalized.startswith("external:"):
            pattern_options.add("workspace:" + normalized)
        for rel_value in rel_options:
            for pattern_value in pattern_options:
                if any(char in pattern_value for char in "*?[]") and fnmatch.fnmatch(rel_value, pattern_value):
                    return True
                if pattern_value.endswith("/") and rel_value.startswith(pattern_value):
                    return True
                if rel_value == pattern_value:
                    return True
                if Path(pattern_value).suffix == "" and rel_value.startswith(pattern_value.rstrip("/") + "/"):
                    return True
    return False


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
    previous = {item.get("skill"): item for item in previous_items if isinstance(item, dict) and item.get("skill")}
    current_map = {item["skill"]: item for item in current}
    changed = sorted(set(current_map) - set(previous))
    changed.extend(sorted(set(previous) - set(current_map)))
    changed.extend(sorted(skill for skill in set(current_map) & set(previous) if previous[skill].get("sha256") != current_map[skill]["sha256"]))
    if not changed:
        return [GateCheck("skill_policy_hash_drift", "PASS", f"skill hashes match previous gate manifest {manifest.name}")]
    if change_id:
        allowed = _change_request_allowed_artifacts(project, change_id)
        changed_paths = [
            str((current_map.get(skill) or previous.get(skill) or {}).get("path") or f"env/rule/skills/{skill}/SKILL.md")
            for skill in changed
        ]
        unscoped = [path for path in changed_paths if not _change_scope_covers(path, allowed)]
        if unscoped:
            return [
                GateCheck(
                    "skill_policy_hash_drift",
                    "FAIL",
                    f"{len(unscoped)} skill policy hash change(s) are not covered by {change_id} impact artifacts: "
                    + ", ".join(unscoped[:8]),
                )
            ]
        return [GateCheck("skill_policy_hash_drift", "PASS", f"{len(changed)} skill policy hash change(s) are covered by {change_id} impact artifacts")]
    return [GateCheck("skill_policy_hash_drift", "FAIL", "skill constraint hash changed since previous gate: " + ", ".join(changed))]


def _check_protected_gate_manifest_drift(project: Path, node: str, change_id: str | None) -> list[GateCheck]:
    current = _protected_gate_hash_entries(project)
    if not current:
        return [GateCheck("protected_gate_hash_drift", "FAIL", "no protected gate/platform files were found")]
    manifest = _latest_gate_manifest(project, node)
    if not manifest:
        return [GateCheck("protected_gate_hash_drift", "PASS", "no previous gate manifest to compare")]
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception as exc:
        return [GateCheck("protected_gate_hash_drift", "FAIL", f"cannot read previous gate manifest {manifest}: {exc}")]
    previous_items = data.get("protected_gate_files", [])
    if not isinstance(previous_items, list) or not previous_items:
        return [GateCheck("protected_gate_hash_drift", "PASS", "previous gate manifest did not record protected gate files")]

    previous = {item.get("path"): item.get("sha256") for item in previous_items if isinstance(item, dict)}
    current_map = {item["path"]: item["sha256"] for item in current}
    previous_paths = {str(path) for path in previous if path}
    current_paths = set(current_map)
    changed = sorted(current_paths - previous_paths)
    changed.extend(sorted(previous_paths - current_paths))
    changed.extend(sorted(path for path in current_paths & previous_paths if previous.get(path) != current_map[path]))
    if not changed:
        return [GateCheck("protected_gate_hash_drift", "PASS", f"protected gate files match previous manifest {manifest.name}")]
    if change_id:
        allowed = _change_request_allowed_artifacts(project, change_id)
        unscoped = [path for path in changed if not _change_scope_covers(path, allowed)]
        if unscoped:
            return [
                GateCheck(
                    "protected_gate_hash_drift",
                    "FAIL",
                    f"{len(unscoped)} protected gate/platform file change(s) are not covered by {change_id} impact artifacts: "
                    + ", ".join(unscoped[:8]),
                )
            ]
        return [GateCheck("protected_gate_hash_drift", "PASS", f"{len(changed)} protected gate/platform file change(s) are covered by {change_id} impact artifacts")]
    return [
        GateCheck(
            "protected_gate_hash_drift",
            "FAIL",
            "protected gate/platform file hash changed since previous gate; automatic loops cannot modify gate policy or report refreshers: "
            + ", ".join(changed[:8]),
        )
    ]


def _gate_paths(project: Path, node: str) -> tuple[list[Path], list[Path]]:
    if node == "input":
        return (_files(project, [SPEC_INPUT_REL]), [])
    if node == "work/docparse":
        evidence_rels = [rel for rel in required_frontend_paths() if rel.startswith("work/docparse/")]
        evidence_rels.extend(
            [
                "output/reports/docparse/requirements_frontend_report.md",
                "output/reports/review/review_check.md",
            ]
        )
        evidence_rels.extend(_docset_evidence_rels())
        return (_docparse_source_files(project), _files(project, evidence_rels))
    if node == "work/loop1_rtl_tb":
        evidence_rels = [
            *_stage_report_required_rels(LOOP1_REPORT),
            WAVEFORM_QUERY_REPORT_REL,
            WAVEFORM_GATE_JSON_REL,
            QUERY_TRANSCRIPT_JSON_REL,
            "output/reports/loop1/rtl_skill_audit.md",
        ]
        wave_files = _glob_project_files(project, f"{LOOP1_WAVE_DIR_REL}/*.vcd")
        wave_files.extend(_glob_project_files(project, f"{LOOP1_WAVE_DIR_REL}/*.wlf"))
        return (
            _source_files_by_suffix(
                project,
                {
                    "output/rtl": {".v"},
                    "output/tb": {".v"},
                    "work/loop1_rtl_tb/config": {".yaml", ".yml"},
                    "work/docparse/structured_spec": {".yaml", ".yml", ".json"},
                    "work/docparse/trace_matrix": {".yaml", ".yml", ".json"},
                },
            ),
            sorted(set(_files(project, evidence_rels) + wave_files)),
        )
    if node == "work/loop2_uvm":
        return (
            _source_files_by_suffix(
                project,
                {
                    "output/rtl": {".v"},
                    "output/uvm": {".sv", ".svh"},
                    "work/docparse/structured_spec": {".yaml", ".yml", ".json"},
                    "work/docparse/trace_matrix": {".yaml", ".yml", ".json"},
                },
            ),
            _files(
                project,
                [
                    *_stage_report_required_rels(LOOP2_REPORT),
                    "work/loop2_uvm/_runtime/loop2_bindings.sqlite",
                ],
            ),
        )
    if node == "work/loop3_fpga_proto":
        evidence = _node_evidence(project, node)
        bitstream_glob = _evidence_str(evidence, "globs", "bitstreams", "output/fpga/vivado/bitstream/*.bit")
        return (
            _files(
                project,
                [
                    "output/rtl",
                    "output/fpga/vivado/constraints",
                    "output/fpga/vivado/scripts",
                    "work/loop3_fpga_proto/board_tests",
                    "work/loop3_fpga_proto/scripts",
                ],
            ),
            _files(project, _evidence_report_paths(evidence, [
                "output/reports/loop3/preflight/database_preflight.md",
                "output/reports/loop3/preflight/prototype_plan_check.md",
                "output/fpga/vivado/reports/post_impl_timing_summary.rpt",
                "output/fpga/vivado/reports/post_impl_drc.rpt",
                "output/reports/loop3/serial/latest_serial_text.log",
                "output/reports/loop3/serial/latest_serial_validation_report.md",
                "output/reports/loop3/vivado_implementation_report.md",
                "output/reports/loop3/vitis_boot_report.md",
                "output/reports/loop3/board_validation_report.md",
                "output/reports/loop3/loop3_exit_report.md",
            ])) + _glob_project_files(project, bitstream_glob),
        )
    if node == "output":
        return ([], _files(project, ["output/manifest.yaml", "output/reports/final_audit_report.md", *_docset_evidence_rels()]))
    return (_files(project, ["input", "work/docparse"]), _files(project, ["work/docparse"]))


def _docset_evidence_rels() -> list[str]:
    rels = [DOCSET_MANIFEST_REL, DOCSET_REPORT_REL]
    for definition in DOC_DEFINITIONS:
        rels.extend([definition.doc_rel, definition.manifest_rel, definition.snapshot_rel])
    return rels


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
    root = project / SPEC_INPUT_REL
    if not root.is_dir():
        return []
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"README.md", ".gitkeep"}
    )


def _docparse_source_files(project: Path) -> list[Path]:
    """Return formal requirement sources consumed by document analysis.

    `input/spec` stores user-provided requirement captures only. For DocParse
    freshness, compare evidence against the documents listed by
    `document_analysis.yaml` instead of generated front-door files under
    `work/docparse/frontdoor`.
    """

    analysis_path = project / DOCUMENT_ANALYSIS_REL
    if not analysis_path.is_file():
        return _requirement_source_files(project)
    try:
        analysis = load_yaml(analysis_path)
    except Exception:
        return _requirement_source_files(project)
    if not isinstance(analysis, dict):
        return _requirement_source_files(project)

    paths: list[Path] = []
    for item in _as_list(analysis.get("source_documents")):
        if not isinstance(item, dict):
            continue
        source_ref = str(item.get("source_ref", "")).strip()
        if not source_ref:
            continue
        try:
            source_path = _project_path(project, source_ref)
        except ValueError:
            continue
        if source_path.is_file():
            paths.append(source_path)
    return sorted(set(paths)) or _requirement_source_files(project)


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
        if node in {"work/loop1_rtl_tb", "work/loop2_uvm", "work/loop3_fpga_proto"}:
            return [GateCheck("source_policy", "FAIL", "Loop1/Loop2/Loop3 require configured source_policy")]
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
        enforce_all_extensions = _policy_bool(section, "enforce_all_extensions", False)
        if not root.exists():
            checks.append(GateCheck(f"source_policy:{section_name}", "PASS", f"{root_rel} does not exist yet"))
            continue
        files = [path for path in root.rglob("*") if path.is_file() and path.name != ".gitkeep"]
        forbidden_hits = [path for path in files if path.suffix.lower() in forbidden]
        if forbidden_hits:
            rels = ", ".join(_rel(project, path) for path in forbidden_hits[:8])
            checks.append(GateCheck(f"source_policy:{section_name}", "FAIL", f"forbidden extension(s) under {root_rel}: {rels}"))
            continue
        candidate_files = files if enforce_all_extensions else [path for path in files if path.suffix.lower() in {".v", ".sv", ".svh"} | template_exts]
        unknown = [path for path in candidate_files if path.suffix.lower() not in allowed and path.suffix.lower() not in template_exts]
        if unknown:
            rels = ", ".join(_rel(project, path) for path in unknown[:8])
            checks.append(GateCheck(f"source_policy:{section_name}", "FAIL", f"extension not allowed by source policy: {rels}"))
            continue
        checks.append(GateCheck(f"source_policy:{section_name}", "PASS", f"{root_rel} follows {section.get('language', 'configured language')} policy"))
    return checks


def _check_official_protocol_naming(project: Path) -> GateCheck:
    """Block direction suffixes on official UART physical boundary names."""

    scan_roots = [
        SPEC_INPUT_REL,
        "work/docparse/architecture",
        "work/docparse/prototype",
        "output/rtl",
        "output/tb",
        "output/uvm",
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
    rtl_dir = project / "output" / "rtl"
    if not rtl_dir.exists():
        return GateCheck("rtl_comment_headers", "PASS", "output/rtl does not exist yet")
    missing: list[str] = []
    mismatched: list[str] = []
    for path in sorted(rtl_dir.glob("*.v")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        module_match = re.search(r"(?m)^\s*module\s+\w+", text)
        header = text[: module_match.start()] if module_match else text[:1200]
        if "// Module" not in text[:800] or "// Description" not in text[:800] or "// Scope:" not in header:
            missing.append(_rel(project, path))
            continue
        semantic_error = _rtl_header_semantic_error(path, text, header)
        if semantic_error:
            mismatched.append(f"{_rel(project, path)}: {semantic_error}")
    if missing:
        return GateCheck("rtl_comment_headers", "FAIL", "missing required RTL header comment(s): " + ", ".join(missing[:8]))
    if mismatched:
        return GateCheck("rtl_comment_headers", "FAIL", "RTL header description does not match module ownership: " + "; ".join(mismatched[:8]))
    return GateCheck("rtl_comment_headers", "PASS", "RTL files include module description and scope headers")


def _check_rtl_task_usage(project: Path) -> GateCheck:
    rtl_dir = project / "output" / "rtl"
    if not rtl_dir.exists():
        return GateCheck("rtl_task_usage", "PASS", "output/rtl does not exist yet")
    hits: list[str] = []
    task_pattern = re.compile(r"(?m)^\s*(?:virtual\s+)?(?:automatic\s+)?task\b|^\s*endtask\b|\btask\s+(?:automatic\s+)?[A-Za-z_]")
    for path in sorted(rtl_dir.rglob("*.v")):
        code = _strip_verilog_comments(path.read_text(encoding="utf-8", errors="ignore"))
        if task_pattern.search(code):
            hits.append(_rel(project, path))
    if hits:
        return GateCheck(
            "rtl_task_usage",
            "FAIL",
            "Verilog task/endtask declarations are forbidden in RTL .v files under output/rtl; "
            "move procedural helpers to TB files under output/tb: " + ", ".join(hits[:8]),
        )
    return GateCheck("rtl_task_usage", "PASS", "RTL .v files under output/rtl contain no task/endtask declarations")


def _rtl_header_semantic_error(path: Path, text: str, header: str) -> str | None:
    header_l = header.lower()
    text_l = text.lower()
    stem_l = path.stem.lower()
    register_owner = stem_l in {"regs", "registers", "regfile", "csr", "csrs"}
    if register_owner and re.search(r"\bcontrol_reg\b|\bcontrol_[a-z0-9_]*reg\b", text_l) and not any(
        token in header_l for token in ["control register", "control_reg", "control word", "control bits", "控制寄存器"]
    ):
        return "body owns control register signals but header does not state control-register ownership"
    if register_owner and re.search(r"\bstatus_reg\b|\bstatus_[a-z0-9_]*reg\b", text_l) and not any(
        token in header_l for token in ["status register", "status_reg", "status word", "status bits", "状态寄存器"]
    ):
        return "body owns status register signals but header does not state status-register ownership"
    if register_owner and "register" not in header_l and "寄存器" not in header_l:
        return "register-like module name requires explicit register ownership in header"
    return None


def _check_skill_policy(project: Path, node: str) -> list[GateCheck]:
    node_cfg = _node_config(project, node)
    policy = node_cfg.get("skill_policy", {})
    if not isinstance(policy, dict) or not policy:
        if node in {"work/loop1_rtl_tb", "work/loop2_uvm", "work/loop3_fpga_proto"}:
            return [GateCheck("skill_policy", "FAIL", "Loop1/Loop2/Loop3 require configured skill_policy")]
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
        rel = str(spec.get("path") or f"env/rule/skills/{skill_name}/SKILL.md")
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
        rel = str(spec.get("path") or f"env/rule/skills/{skill_name}/SKILL.md")
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


def _protected_gate_hash_entries(project: Path) -> list[dict[str, Any]]:
    workspace = _find_workspace_root(project)
    entries: list[dict[str, Any]] = []
    for rel in PROTECTED_GATE_FILES:
        try:
            path = _workspace_path(workspace, rel)
        except ValueError:
            continue
        if not path.is_file():
            continue
        data = path.read_bytes()
        entries.append(
            {
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
    report_dir = project / "output" / "reports" / "gates"
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
    if node == "output" and ok:
        final_path = project / "output" / "reports" / "final_audit_report.md"
        final_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _sync_output_manifest(project, level=level, final_gate="PASS", final_report=final_path)
    return report_path


def _sync_output_manifest(
    project: Path,
    *,
    level: str,
    final_gate: str,
    final_report: Path | None = None,
) -> Path:
    manifest_path = project / "output" / "manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    gate_level = level if level == "release" else None
    loop_nodes = {
        "loop1": "work/loop1_rtl_tb",
        "loop2": "work/loop2_uvm",
        "loop3": "work/loop3_fpga_proto",
    }
    gate_entries: dict[str, tuple[str, str]] = {}
    for label, node in loop_nodes.items():
        manifest = _latest_gate_manifest(project, node, gate_level)
        gate_entries[label] = ("PASS" if manifest else "FAIL", _rel(project, manifest) if manifest else "")

    final_report_rel = _rel(project, final_report) if final_report else ""
    lines = [
        "schema_version: 1",
        f"project: {project.name}",
        "output:",
        "  version: 1",
        f"  generated_at: {datetime.now().isoformat(timespec='seconds')}",
        "  signoff_owner: Arbtr Agent",
        "  source_origin: requirements-frontdoor-gated flow",
        "deliverables:",
        *(_manifest_list_lines("rtl", _collect_manifest_files(project, "output/rtl", {".v"}))),
        *(_manifest_list_lines("tb", _collect_manifest_files(project, "output/tb", {".v"}))),
        *(_manifest_list_lines("uvm", _collect_manifest_files(project, "output/uvm", {".sv", ".svh", ".yaml", ".yml", ".md"}))),
        *(_manifest_list_lines("fpga", _collect_manifest_files(project, "output/fpga/vivado/bitstream", {".bit"}))),
        *(_manifest_list_lines("vivado", _collect_manifest_files(project, "output/fpga/vivado/reports", {".rpt", ".md"}) + _collect_manifest_files(project, "output/fpga/vivado/scripts", {".tcl"}))),
        *(_manifest_list_lines("vitis", _collect_manifest_files(project, "output/fpga/vitis/src", {".c", ".h", ".ld", ".md", ".yaml", ".yml"}) + _collect_manifest_files(project, "output/fpga/vitis/boot", {".bif", ".ps1", ".bin"}) + _collect_manifest_files(project, "output/fpga/vitis/workspace", {".elf", ".xsa", ".xpfm"}))),
        "reports:",
        "  index:",
        "    - output/reports/README.md",
        f"  audit_report: {final_report_rel}",
        "  trace_matrix: work/docparse/trace_matrix",
        "  compliance_summary: output/reports/final_audit_report.md",
        "verification:",
    ]
    for label in ("loop1", "loop2", "loop3"):
        status, manifest = gate_entries[label]
        lines.append(f"  {label}_gate: {status}")
        lines.append(f"  {label}_manifest: {manifest}")
    lines.append(f"  final_gate: {final_gate}")
    if final_report_rel:
        lines.append(f"  final_report: {final_report_rel}")
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest_path


def _manifest_list_lines(name: str, paths: list[Path]) -> list[str]:
    if not paths:
        return [f"  {name}: []"]
    lines = [f"  {name}:"]
    for path in paths:
        rel = str(path).replace("\\", "/")
        lines.append(f"    - {rel}")
    return lines


def _collect_manifest_files(project: Path, rel_root: str, suffixes: set[str]) -> list[Path]:
    root = project / rel_root
    if not root.exists():
        return []
    paths = [
        Path(_rel(project, path))
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.suffix.lower() in suffixes
    ]
    return paths[:200]


def _write_gate_manifest(
    project: Path,
    node: str,
    level: str,
    source_paths: list[Path],
    evidence_paths: list[Path],
    report_path: Path,
    change_id: str | None,
) -> Path:
    manifest_dir = project_memory_path(project) / "recovery" / "rollback_manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    manifest_path = manifest_dir / f"{_node_file_stem(node)}_{level}_{stamp}.json"
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
        "protected_gate_files": _protected_gate_hash_entries(project),
    }
    manifest_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def _latest_gate_manifest(project: Path, node: str, level: str | None = None) -> Path | None:
    manifest_dir = project_memory_path(project) / "recovery" / "rollback_manifests"
    matches: list[Path] = []
    if manifest_dir.exists():
        for stem in NODE_FILE_STEMS.get(node, [_node_file_stem(node)]):
            pattern = f"{stem}_{level}_*.json" if level else f"{stem}_*.json"
            matches.extend(manifest_dir.glob(pattern))
    matches = sorted(set(matches))
    return matches[-1] if matches else None


def _node_file_stem(node: str) -> str:
    return node.replace("/", "_")


def _hash_entry(project: Path, path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": _rel(project, path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
        "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
    }


def _read_change_requests(project: Path, statuses: set[str]) -> list[dict[str, str]]:
    requests_dir = project / "work/change" / "requests"
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
    path = project / "work/change" / "requests" / f"{change_id}.md"
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
    resolved = path.resolve()
    project_resolved = project.resolve()
    try:
        return str(resolved.relative_to(project_resolved)).replace("\\", "/")
    except ValueError:
        pass
    workspace = _find_workspace_root(project)
    try:
        return "workspace:" + str(resolved.relative_to(workspace.resolve())).replace("\\", "/")
    except ValueError:
        return "external:" + str(resolved).replace("\\", "/")


def _manifest_rel_exists(project: Path, rel: str) -> bool:
    if rel.startswith("workspace:"):
        return (_find_workspace_root(project) / rel.removeprefix("workspace:")).exists()
    if rel.startswith("external:"):
        return Path(rel.removeprefix("external:")).exists()
    return _project_path(project, rel).exists()


def _find_workspace_root(path: Path) -> Path:
    return find_workspace_root(path)


def _escape_md(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")
