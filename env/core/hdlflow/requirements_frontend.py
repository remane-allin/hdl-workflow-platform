"""Structured requirements front-end for the HDL workflow."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .layout import find_workspace_root
from .project import require_project_instance
from .review import (
    BLOCKING_SEVERITIES_BY_LEVEL,
    CLOSED_STATUSES,
    REQUIRED_FINDING_FIELDS,
    REVIEW_ROLE_NAMES,
    VALID_STATUSES,
    validate_review_payload,
)
from .simple_yaml import load_yaml


FRONTEND_VERSION = 1
READY_STATUS = "READY"
SPEC_INPUT_REL = "input/spec"
FRONTDOOR_REL = "work/docparse/frontdoor"
SRS_REL = f"{FRONTDOOR_REL}/srs.yaml"
SRS_MD_REL = f"{FRONTDOOR_REL}/srs.md"
ACCEPTANCE_REL = f"{FRONTDOOR_REL}/acceptance_criteria.yaml"
FORBIDDEN_DESIGNS_REL = f"{FRONTDOOR_REL}/forbidden_designs.yaml"
OPEN_QUESTIONS_REL = f"{FRONTDOOR_REL}/open_questions.md"
DOCUMENT_ANALYSIS_REL = "work/docparse/structured_spec/document_analysis.yaml"
FSM_NO_MONOLITHIC_OWNERSHIP_RULE = (
    "Do not use one large FSM in a single file to own all command decode, field updates, FIFO operations, "
    "register behavior, datapath mutation, and control sequencing. Split these into owned stages, fields, "
    "blocks, or modules."
)

ROLE_CONTRACTS = [
    {
        "role": "spec",
        "title": "Spec Agent",
        "owns": "requirements, protocol source text, metrics, executable chip spec, interface timing, and forbidden design list",
        "primary_outputs": [
            SRS_REL,
            SRS_MD_REL,
            ACCEPTANCE_REL,
            FORBIDDEN_DESIGNS_REL,
            "work/docparse/structured_spec/interface_spec.yaml",
            DOCUMENT_ANALYSIS_REL,
            "work/docparse/structured_spec/interface_timing.yaml",
            "work/docparse/structured_spec/register_map.yaml",
            "work/docparse/structured_spec/test_intent.yaml",
            "work/docparse/structured_spec/timing_rules.yaml",
            "work/docparse/req_decompose/requirements.json",
            "work/docparse/req_decompose/requirements.md",
        ],
    },
    {
        "role": "arch",
        "title": "Arch Agent",
        "owns": "module topology, bus architecture, hierarchy partition, throughput planning, interfaces, and dataflow",
        "primary_outputs": [
            "work/docparse/architecture/add.md",
            "work/docparse/architecture/module_plan.yaml",
            "work/docparse/architecture/interface_contracts.yaml",
            "work/docparse/architecture/dataflow.yaml",
            "work/docparse/architecture/state_machines.yaml",
            "work/docparse/architecture/timing_model.yaml",
        ],
    },
    {
        "role": "exec",
        "title": "Exec Agent",
        "owns": "Verilog RTL implementation, instance relationships, full functional directed TB, combinational logic, and sequential logic",
        "primary_outputs": [
            "output/rtl/",
            "output/tb/",
            "output/tb/full_function_test_plan.md",
            "work/docparse/trace_matrix/req_to_rtl.yaml",
        ],
    },
    {
        "role": "sim",
        "title": "Sim Agent",
        "owns": "simulation tests, wave sampling, logs, coverage, UVM, board-level validation evidence, and waveform comparison",
        "primary_outputs": [
            "work/docparse/verification/verification_plan.yaml",
            "work/docparse/verification/assertion_plan.yaml",
            "work/docparse/verification/coverage_plan.yaml",
            "output/uvm/",
            "output/reports/loop1/",
            "output/reports/loop2/",
            "output/reports/loop3/",
        ],
    },
    {
        "role": "review",
        "title": "Review Agent",
        "owns": "defect list, risk level, correction advice, compliance review, and root-cause routing without editing spec, architecture, or RTL",
        "primary_outputs": [
            "work/docparse/review/multi_agent_review.md",
            "work/docparse/review/role_findings.yaml",
            "output/reports/review/",
        ],
    },
    {
        "role": "arbtr",
        "title": "Arbtr Agent",
        "owns": "global flow log, disputes, iteration count, correction routing, termination criteria, baseline freeze, and final decision",
        "primary_outputs": [
            "work/docparse/review/decision_log.yaml",
            "work/docparse/review/arbitration_log.yaml",
            "work/memory/",
            "work/gates/",
            "output/reports/freeze/",
        ],
    },
]

REQUIRED_FRONTEND_ARTIFACTS = [
    SRS_REL,
    ACCEPTANCE_REL,
    FORBIDDEN_DESIGNS_REL,
    OPEN_QUESTIONS_REL,
    "work/docparse/structured_spec/interface_spec.yaml",
    DOCUMENT_ANALYSIS_REL,
    "work/docparse/structured_spec/register_map.yaml",
    "work/docparse/structured_spec/test_intent.yaml",
    "work/docparse/structured_spec/timing_rules.yaml",
    "work/docparse/structured_spec/interface_timing.yaml",
    "work/docparse/architecture/module_plan.yaml",
    "work/docparse/architecture/interface_contracts.yaml",
    "work/docparse/architecture/dataflow.yaml",
    "work/docparse/architecture/state_machines.yaml",
    "work/docparse/architecture/timing_model.yaml",
    "work/docparse/architecture/rtl_planning_rules.yaml",
    "work/docparse/verification/verification_plan.yaml",
    "work/docparse/verification/assertion_plan.yaml",
    "work/docparse/verification/coverage_plan.yaml",
    "work/docparse/prototype/prototype_plan.yaml",
    "work/docparse/prototype/clock_plan.yaml",
    "work/docparse/prototype/pin_resource_intent.yaml",
    "work/docparse/review/role_findings.yaml",
    "work/docparse/review/decision_log.yaml",
    "work/docparse/review/arbitration_log.yaml",
    "work/docparse/review/multi_agent_review.md",
    "work/docparse/trace_matrix/req_to_arch.yaml",
    "work/docparse/trace_matrix/req_to_rtl.yaml",
    "work/docparse/trace_matrix/req_to_test.yaml",
    "work/docparse/trace_matrix/req_to_proto.yaml",
]

QUESTION_REVIEW_READY_STATUSES = {"REVIEWED", "USER_REVIEWED", "APPROVED"}
QUESTION_CLOSED_STATUSES = {
    "ANSWERED",
    "RESOLVED",
    "ACCEPTED",
    "CLOSED",
    "WAIVED",
    "NOT_BLOCKING",
    "NOT_APPLICABLE",
    "USER_APPROVED",
}
MINERU_HIGH_PRECISION_CHANNEL = "mineru-open-api high_precision_api"
MINERU_HIGH_PRECISION_ENDPOINTS = {
    "/api/v4/extract/task",
    "/api/v4/file-urls/batch",
}
EXTERNAL_SOURCE_SUFFIXES = {".pdf", ".doc", ".docx", ".ppt", ".pptx"}
PARSER_OUTPUT_SUFFIXES = {".md", ".json", ".html", ".latex", ".docx"}
ILLEGAL_PARSED_EVIDENCE_DIRS = {
    "local_text",
    "temp_text",
    "temporary_text",
    "text_cache",
    "cache_text",
    "flash_extract",
    "flash",
}


@dataclass(frozen=True)
class RequirementsFrontendResult:
    report_path: Path
    created: list[str]
    updated: list[str]
    warnings: list[str]
    errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def initialize_requirements_frontend(
    project_path: Path,
    *,
    status: str = "DRAFT",
    force: bool = False,
) -> RequirementsFrontendResult:
    """Create the multi-role front-end artifact contract for a project."""

    project = require_project_instance(project_path)

    status = status.upper()
    if status not in {"DRAFT", "READY"}:
        raise ValueError("status must be DRAFT or READY")

    created: list[str] = []
    updated: list[str] = []
    warnings: list[str] = []

    source_refs = _requirement_source_refs(project)
    project_name = project.name

    artifacts = _artifact_templates(project_name, status, source_refs)
    for rel, content in artifacts.items():
        path = project / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not force:
            continue
        if path.exists():
            updated.append(rel)
        else:
            created.append(rel)
        path.write_text(content, encoding="utf-8")

    if not source_refs:
        warnings.append(f"no source requirement files found under {SPEC_INPUT_REL}; generated artifact source_refs are empty")

    check = check_requirements_frontend(project, require_ready=status == READY_STATUS)
    warnings.extend(check.warnings)
    report_path = _write_frontend_report(
        project,
        title="Requirements Front-End Initialize Report",
        result="PASS" if not check.errors else "FAIL",
        created=created,
        updated=updated,
        warnings=warnings,
        errors=check.errors,
    )
    return RequirementsFrontendResult(report_path, created, updated, warnings, check.errors)


def check_requirements_frontend(project_path: Path, *, require_ready: bool = True) -> RequirementsFrontendResult:
    """Validate the multi-role artifact contract without modifying role outputs."""

    project = require_project_instance(project_path)
    warnings: list[str] = []
    errors: list[str] = []

    missing = [rel for rel in REQUIRED_FRONTEND_ARTIFACTS if not (project / rel).exists()]
    errors.extend(f"missing required front-end artifact: {rel}" for rel in missing)

    for rel in REQUIRED_FRONTEND_ARTIFACTS:
        path = project / rel
        if not path.exists() or path.suffix.lower() not in {".yaml", ".yml", ".json"}:
            continue
        data = _load_structured(path)
        if data is None:
            errors.append(f"{rel} is not parseable")
            continue
        if data.get("schema_version") != FRONTEND_VERSION:
            errors.append(f"{rel} schema_version must be {FRONTEND_VERSION}")
        if require_ready and "status" in data and str(data.get("status") or "").upper() != READY_STATUS:
            errors.append(f"{rel} status must be {READY_STATUS} for DocParse gate")
        if "source_refs" in data and not isinstance(data.get("source_refs"), list):
            errors.append(f"{rel} source_refs must be a list")
        if "assumptions" in data and not isinstance(data.get("assumptions"), list):
            errors.append(f"{rel} assumptions must be a list")
        if require_ready:
            _check_ready_payload(rel, data, errors)

    _check_role_findings(project, errors, warnings, require_ready=require_ready)
    _check_decision_log(project, errors, warnings, require_ready=require_ready)
    _check_cross_loop_trace(project, errors, require_ready=require_ready)
    _check_rtl_planning_rules(project, errors, warnings, require_ready=require_ready)
    _check_requirement_question_review(project, errors, warnings, require_ready=require_ready)
    _check_external_document_parse_policy(project, errors, warnings, require_ready=require_ready)

    report_path = _write_frontend_report(
        project,
        title="Requirements Front-End Check Report",
        result="PASS" if not errors else "FAIL",
        created=[],
        updated=[],
        warnings=warnings,
        errors=errors,
    )
    return RequirementsFrontendResult(report_path, [], [], warnings, errors)


def required_frontend_paths() -> list[str]:
    return list(REQUIRED_FRONTEND_ARTIFACTS)


def _artifact_templates(project_name: str, status: str, source_refs: list[str]) -> dict[str, str]:
    now = datetime.now().isoformat(timespec="seconds")
    refs_yaml = _yaml_list(source_refs, indent=0)
    refs_inline = ", ".join(source_refs) if source_refs else "none"

    base = {
        "schema_version": FRONTEND_VERSION,
        "project": project_name,
        "status": status,
        "generated_at": now,
        "source_refs": source_refs,
    }

    return {
        SRS_REL: _yaml_doc(
            {
                **base,
                "owner_role": "spec",
                "purpose": "single shared executable chip spec baseline for Arch, Exec, Sim, Review, and Arbtr",
                "stakeholders": [],
                "scope": {"in_scope": [], "out_of_scope": []},
                "functional_requirements": [],
                "non_functional_requirements": [],
                "interfaces": [],
                "boundary_conditions": [],
                "protocol_sources": [],
                "metric_parameters": [],
                "legal_design_boundaries": [],
                "document_analysis_ref": DOCUMENT_ANALYSIS_REL,
                "ambiguities": [],
                "assumptions": [],
                "acceptance_summary": [],
            }
        ),
        SRS_MD_REL: "\n".join(
            [
                "# Structured Requirements Specification",
                "",
                f"- project: {project_name}",
                f"- status: {status}",
                f"- source_refs: {refs_inline}",
                "",
                "## Scope",
                "",
                "## Functional Requirements",
                "",
                "## Non-Functional Requirements",
                "",
                "## Boundary Conditions",
                "",
                "## Open Questions",
                "",
            ]
        ),
        ACCEPTANCE_REL: _yaml_doc(
            {
                **base,
                "owner_role": "spec",
                "criteria": [],
                "exit_conditions": [
                    "all safety-critical ambiguities are closed or explicitly accepted",
                    "each requirement maps to architecture, verification, and prototype intent where applicable",
                    "review has no open defect and arbtr confirms compliance before freeze",
                ],
                "assumptions": [],
            }
        ),
        FORBIDDEN_DESIGNS_REL: _yaml_doc(
            {
                **base,
                "owner_role": "spec",
                "forbidden_designs": [],
                "illegal_assumptions": [],
                "out_of_scope_behaviors": [],
                "rationale": [],
            }
        ),
        OPEN_QUESTIONS_REL: _open_questions(project_name, status),
        "work/docparse/architecture/add.md": _architecture_md(project_name, status, refs_inline),
        "work/docparse/architecture/rtl_planning_rules.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "arch",
                "source_skill": "env/rule/skills/rtl-architecture-and-gen/SKILL.md",
                "style_guide": "env/rule/skills/rtl-architecture-and-gen/references/verilog-rtl-style-guide.md",
                "rtl_language": "Verilog-2001",
                "rtl_root": "output/rtl",
                "directed_tb_language": "Verilog-2001",
                "directed_tb_root": "output/tb",
                "uvm_language": "SystemVerilog",
                "uvm_root": "output/uvm",
                "hard_rules": [
                    "hierarchy_only_top",
                    "hierarchical_module_composition",
                    "one_primary_module_per_file",
                    "one_function_per_module",
                    "verilog_2001_rtl_only",
                    "no_systemverilog_in_rtl_or_directed_tb",
                    "official_bus_protocol_naming",
                    "three_process_fsm_when_applicable",
                    "no_monolithic_fsm_file",
                    "fsm_single_responsibility",
                    "standalone_else",
                    "explicit_final_else",
                    "explicit_cdc_plan",
                    "req_to_rtl_trace_required",
                ],
                "module_plan_requirements": [
                    "module hierarchy",
                    "parent/child module composition",
                    "one functional responsibility per module",
                    "clock/reset ownership",
                    "interface ownership",
                    "register block ownership",
                    "implementation order",
                ],
                "assumptions": [],
            }
        ),
        "work/docparse/architecture/module_plan.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "arch",
                "rtl_planning_policy_ref": "work/docparse/architecture/rtl_planning_rules.yaml",
                "module_partition_policy": {
                    "hierarchy_required": True,
                    "one_function_per_module": True,
                    "major_function_one_primary_rtl_file": True,
                    "composite_modules_instantiate_children": True,
                },
                "modules": [],
                "top_level": {"name": "", "wrapper_policy": ""},
                "clock_reset": [],
                "throughput_plan": [],
                "composition": [],
                "dependencies": [],
                "agent_consumers": ["Exec Agent", "Sim Agent", "Review Agent", "Arbtr Agent"],
                "assumptions": [],
            }
        ),
        "work/docparse/architecture/interface_contracts.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "arch",
                "interfaces": [],
                "ports": [],
                "protocols": [],
                "latency_contracts": [],
                "assumptions": [],
            }
        ),
        "work/docparse/architecture/dataflow.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "arch",
                "flows": [],
                "control_paths": [],
                "datapaths": [],
                "backpressure": [],
                "assumptions": [],
            }
        ),
        "work/docparse/architecture/state_machines.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "arch",
                "rtl_planning_policy_ref": "work/docparse/architecture/rtl_planning_rules.yaml",
                "fsm_style_policy": [
                    "three_process_fsm_when_applicable",
                    "fsm_single_responsibility",
                    FSM_NO_MONOLITHIC_OWNERSHIP_RULE,
                    "separate_state_next_and_datapath_control",
                    "illegal_state_default_recovery",
                ],
                "state_machines": [],
                "state_machine_entry_requirements": [
                    "name",
                    "owning_module",
                    "controlled_function",
                    "state_register_owner",
                    "next_state_owner",
                    "output_control_owner",
                    "forbidden_responsibilities",
                ],
                "forbidden_fsm_responsibilities": [
                    "datapath mutation owned by datapath modules",
                    "FIFO storage owned by FIFO modules",
                    "register storage owned by register modules",
                    "protocol field storage owned by field/datapath modules",
                ],
                "reset_states": [],
                "illegal_states": [],
                "transition_requirements": [],
                "assumptions": [],
            }
        ),
        "work/docparse/architecture/timing_model.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "arch",
                "clock_domains": [],
                "resets": [],
                "latency_requirements": [],
                "cdc_requirements": [],
                "timing_constraints": [],
                "assumptions": [],
            }
        ),
        "work/docparse/verification/verification_plan.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "sim",
                "module_level": [],
                "system_level": [],
                "scoreboards": [],
                "reference_models": [],
                "baseline_entry_checks": [],
                "full_function_matrix": [],
                "scenario_tests": [],
                "stress_tests": [],
                "fpga_realistic_tests": [],
                "negative_tests": [],
                "waveform_comparison": [],
                "agent_consumers": ["Sim Agent", "Review Agent", "Arbtr Agent"],
                "assumptions": [],
            }
        ),
        "work/docparse/verification/verification_plan.md": _verification_md(project_name, status, refs_inline),
        "work/docparse/verification/assertion_plan.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "sim",
                "assertions": [],
                "bind_targets": [],
                "disabled_conditions": [],
                "severity_policy": [],
                "assumptions": [],
            }
        ),
        "work/docparse/verification/coverage_plan.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "sim",
                "functional_coverage": [],
                "code_coverage_targets": [],
                "cross_coverage": [],
                "illegal_bins": [],
                "closure_thresholds": [],
                "assumptions": [],
            }
        ),
        "work/docparse/prototype/prototype_plan.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "sim",
                "prototype_mode": "",
                "board": "",
                "resource_estimate": [],
                "ps_pl_boundary": [],
                "risk_items": [],
                "board_waveform_checks": [],
                "loop3_feedback_policy": "Loop3 RTL issues route through Review and Arbtr, then back to Exec before Loop1/Loop2/Loop3 rerun.",
                "agent_consumers": ["Sim Agent", "Review Agent", "Arbtr Agent"],
                "assumptions": [],
            }
        ),
        "work/docparse/prototype/prototype_plan.md": _prototype_md(project_name, status, refs_inline),
        "work/docparse/prototype/clock_plan.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "sim",
                "clocks": [],
                "resets": [],
                "generated_clocks": [],
                "clock_groups": [],
                "assumptions": [],
            }
        ),
        "work/docparse/prototype/pin_resource_intent.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "sim",
                "external_ports": [],
                "pin_intent": [],
                "mio_ownership": [],
                "board_resources": [],
                "assumptions": [],
            }
        ),
        "work/docparse/review/role_findings.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "review",
                "review_policy": {
                    "blocking_severities": sorted(BLOCKING_SEVERITIES_BY_LEVEL["develop"]),
                    "release_blocking_severities": sorted(BLOCKING_SEVERITIES_BY_LEVEL["release"]),
                    "closed_statuses": sorted(CLOSED_STATUSES),
                    "valid_statuses": list(VALID_STATUSES),
                    "required_finding_fields": list(REQUIRED_FINDING_FIELDS),
                },
                "roles": {
                    item["role"]: {
                        "status": status,
                        "findings": [],
                        "confidence": "medium",
                    }
                    for item in ROLE_CONTRACTS
                },
                "cross_role_conflicts": [],
                "assumptions": [],
            }
        ),
        "work/docparse/review/decision_log.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "arbtr",
                "decisions": [],
                "rejected_alternatives": [],
                "handoff": {
                    "spec_to_arch": "Spec Agent releases input/spec plus structured spec boundaries",
                    "arch_to_exec": "Arch Agent releases architecture module/interface/dataflow/timing contracts",
                    "exec_to_sim": "Exec Agent releases compile-ready RTL and complete functional directed TB",
                    "sim_to_review": "Sim Agent releases simulation, coverage, and waveform evidence",
                    "review_to_arbtr": "Review Agent releases zero-defect or defect-routed findings",
                },
                "iteration_policy": {
                    "forward": ["spec", "arch", "exec", "sim", "review", "arbtr"],
                    "backward": "Review classifies defect layer, Arbtr selects target, then flow restarts forward from that agent.",
                    "termination": "review has no open defect and arbtr confirms compliance",
                },
                "assumptions": [],
            }
        ),
        "work/docparse/review/arbitration_log.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "arbtr",
                "disputes": [],
                "feedback_routes": [],
                "iteration_count": 0,
                "freeze_decision": "UNSET",
                "freeze_conditions": [
                    "review_no_open_defects",
                    "arbtr_confirms_compliance",
                ],
                "frozen_baseline": "",
                "assumptions": [],
            }
        ),
        "work/docparse/review/multi_agent_review.md": _review_md(project_name, status, refs_yaml),
        "work/docparse/structured_spec/interface_spec.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "spec",
                "module_name": "",
                "clock_domains": [],
                "reset_signals": [],
                "interfaces": [],
                "ports": [],
                "protocol_notes": [],
                "legal_design_boundaries": [],
                "assumptions": [],
            }
        ),
        DOCUMENT_ANALYSIS_REL: _yaml_doc(
            {
                **base,
                "owner_role": "spec",
                "analysis_policy": {
                    "method": "source_inventory_section_analysis_evidence_mapping_review",
                    "stages": [
                        "source_inventory",
                        "section_map",
                        "requirement_extraction",
                        "ambiguity_log",
                        "cross_role_review",
                        "trace_binding",
                    ],
                    "fresh_verification_required": True,
                },
                "source_documents": [],
                "analysis_units": [],
                "evidence_map": [],
                "open_questions": [],
                "question_review": {
                    "status": "UNREVIEWED",
                    "reviewed_by": "",
                    "review_evidence": OPEN_QUESTIONS_REL,
                    "unresolved_count": None,
                    "notes": "Before READY, unresolved requirement questions must be shown to the user and closed or explicitly accepted.",
                },
                "contradictions": [],
                "cross_checks": [],
                "assumptions": [],
            }
        ),
        "work/docparse/structured_spec/register_map.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "spec",
                "register_blocks": [],
                "registers": [],
                "opcodes": [],
                "fields": [],
                "access_rules": [],
                "reset_rules": [],
                "assumptions": [],
            }
        ),
        "work/docparse/structured_spec/test_intent.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "spec",
                "functional_tests": [],
                "corner_cases": [],
                "coverage_targets": [],
                "scoreboard_rules": [],
                "baseline_entry_checks": [],
                "full_function_matrix": [],
                "waveform_windows": [],
                "waveform_observability": [],
                "assumptions": [],
            }
        ),
        "work/docparse/structured_spec/timing_rules.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "spec",
                "clocking": [],
                "resets": [],
                "timing_constraints": [],
                "cdc_rules": [],
                "interface_rules": [],
                "protocol_timing": [],
                "assumptions": [],
            }
        ),
        "work/docparse/structured_spec/interface_timing.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "spec",
                "interfaces": [],
                "timing_tables": [],
                "valid_windows": [],
                "latency_bounds": [],
                "assumptions": [],
            }
        ),
        "work/docparse/trace_matrix/req_to_arch.yaml": _trace_yaml(project_name, status, source_refs, "architecture"),
        "work/docparse/trace_matrix/req_to_rtl.yaml": _trace_yaml(project_name, status, source_refs, "rtl"),
        "work/docparse/trace_matrix/req_to_test.yaml": _trace_yaml(project_name, status, source_refs, "test"),
        "work/docparse/trace_matrix/req_to_proto.yaml": _trace_yaml(project_name, status, source_refs, "prototype"),
    }


def _requirement_source_refs(project: Path) -> list[str]:
    root = project / SPEC_INPUT_REL
    if not root.is_dir():
        return []
    ignored = {
        ".gitkeep",
        "README.md",
        "srs.yaml",
        "srs.md",
        "acceptance_criteria.yaml",
        "open_questions.md",
        "forbidden_designs.yaml",
        "requirements.json",
        "module_plan.md",
        "path_partition.md",
        "decomposition_notes.md",
    }
    refs = []
    for path in sorted(root.glob("*")):
        if path.is_file() and path.name not in ignored:
            refs.append(str(path.relative_to(project)).replace("\\", "/"))
    return refs


def _load_structured(path: Path) -> dict[str, Any] | None:
    try:
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = load_yaml(path)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _check_ready_payload(rel: str, data: dict[str, Any], errors: list[str]) -> None:
    if "source_refs" in data and not data.get("source_refs"):
        errors.append(f"{rel} source_refs must be non-empty for READY")
    if rel.endswith("srs.yaml"):
        functional = data.get("functional_requirements")
        non_functional = data.get("non_functional_requirements")
        if not _non_empty_list(functional) and not _non_empty_list(non_functional):
            errors.append(f"{rel} must contain at least one requirement for READY")
    if rel.endswith("acceptance_criteria.yaml") and not _non_empty_list(data.get("criteria")):
        errors.append(f"{rel} criteria must be non-empty for READY")
    if rel.endswith("forbidden_designs.yaml") and not _non_empty_list(data.get("forbidden_designs")):
        errors.append(f"{rel} forbidden_designs must be non-empty for READY")
    if rel.endswith("interface_spec.yaml") and not _has_any_ready_payload(data, ["interfaces", "ports"]):
        errors.append(f"{rel} interfaces or ports must be non-empty for READY")
    if rel == DOCUMENT_ANALYSIS_REL:
        _check_document_analysis_payload(data, errors)
    if rel.endswith("register_map.yaml") and not _has_any_ready_payload(data, ["registers", "opcodes", "commands"]):
        errors.append(f"{rel} registers, opcodes, or commands must be non-empty for READY")
    if rel.endswith("test_intent.yaml") and not _has_any_ready_payload(
        data,
        ["functional_tests", "baseline_entry_checks", "full_function_matrix", "corner_cases", "coverage_targets"],
    ):
        errors.append(f"{rel} functional test intent must be non-empty for READY")
    if rel.endswith("test_intent.yaml") and not _non_empty_list(data.get("waveform_windows")):
        errors.append(f"{rel} waveform_windows must be non-empty for READY")
    if rel.endswith("timing_rules.yaml") and not _has_any_ready_payload(
        data,
        ["timing_constraints", "cdc_rules", "interface_rules", "protocol_timing", "spi", "arinc429"],
    ):
        errors.append(f"{rel} timing rules must be non-empty for READY")
    required_by_name = {
        "interface_timing.yaml": "timing_tables",
        "module_plan.yaml": "modules",
        "interface_contracts.yaml": "interfaces",
        "dataflow.yaml": "flows",
        "state_machines.yaml": "state_machines",
        "timing_model.yaml": "clock_domains",
        "rtl_planning_rules.yaml": "hard_rules",
        "verification_plan.yaml": "module_level",
        "assertion_plan.yaml": "assertions",
        "coverage_plan.yaml": "functional_coverage",
        "prototype_plan.yaml": "resource_estimate",
        "clock_plan.yaml": "clocks",
        "pin_resource_intent.yaml": "external_ports",
    }
    key = required_by_name.get(Path(rel).name)
    if key and not _non_empty_list(data.get(key)):
        errors.append(f"{rel} {key} must be non-empty for READY")
    if rel.endswith("verification_plan.yaml"):
        for coverage_key in [
            "baseline_entry_checks",
            "full_function_matrix",
            "scenario_tests",
            "stress_tests",
            "fpga_realistic_tests",
            "waveform_comparison",
        ]:
            if not _non_empty_list(data.get(coverage_key)):
                errors.append(f"{rel} {coverage_key} must be non-empty for READY")


def _check_role_findings(project: Path, errors: list[str], warnings: list[str], *, require_ready: bool) -> None:
    data = _load_structured(project / "work/docparse/review/role_findings.yaml")
    if data is None:
        return
    result = validate_review_payload(data, require_ready=require_ready)
    errors.extend(result.errors)
    warnings.extend(result.warnings)

    seen_roles = {finding.role for finding in result.findings}
    if require_ready:
        missing_finding_roles = [role for role in REVIEW_ROLE_NAMES if role not in seen_roles]
        if missing_finding_roles:
            errors.append(
                "work/docparse/review/role_findings.yaml READY review must include structured finding entries for role(s): "
                + ", ".join(missing_finding_roles)
            )


def _check_decision_log(project: Path, errors: list[str], warnings: list[str], *, require_ready: bool) -> None:
    data = _load_structured(project / "work/docparse/review/decision_log.yaml")
    if data is None:
        return
    if require_ready and not _non_empty_list(data.get("decisions")):
        errors.append("work/docparse/review/decision_log.yaml decisions must be non-empty for READY")
    handoff = data.get("handoff")
    if not isinstance(handoff, dict):
        errors.append("work/docparse/review/decision_log.yaml handoff must be a mapping")
        return
    for handoff_name in ["spec_to_arch", "arch_to_exec", "exec_to_sim", "sim_to_review", "review_to_arbtr"]:
        if not handoff.get(handoff_name):
            warnings.append(f"decision log handoff for {handoff_name} is empty")


def _check_cross_loop_trace(project: Path, errors: list[str], *, require_ready: bool) -> None:
    for rel in [
        "work/docparse/trace_matrix/req_to_arch.yaml",
        "work/docparse/trace_matrix/req_to_rtl.yaml",
        "work/docparse/trace_matrix/req_to_test.yaml",
        "work/docparse/trace_matrix/req_to_proto.yaml",
    ]:
        data = _load_structured(project / rel)
        if data is None:
            continue
        if "links" not in data:
            errors.append(f"{rel} must contain links")
        elif not isinstance(data.get("links"), (dict, list)):
            errors.append(f"{rel} links must be a mapping or a list")
        elif require_ready and not data.get("links"):
            errors.append(f"{rel} links must be non-empty for READY")


def _check_rtl_planning_rules(project: Path, errors: list[str], warnings: list[str], *, require_ready: bool) -> None:
    rules_rel = "work/docparse/architecture/rtl_planning_rules.yaml"
    rules = _load_structured(project / rules_rel)
    if rules is None:
        return

    expected_scalars = {
        "source_skill": "env/rule/skills/rtl-architecture-and-gen/SKILL.md",
        "style_guide": "env/rule/skills/rtl-architecture-and-gen/references/verilog-rtl-style-guide.md",
        "rtl_language": "Verilog-2001",
        "rtl_root": "output/rtl",
        "directed_tb_language": "Verilog-2001",
        "directed_tb_root": "output/tb",
        "uvm_language": "SystemVerilog",
        "uvm_root": "output/uvm",
    }
    for key, expected in expected_scalars.items():
        if str(rules.get(key) or "") != expected:
            errors.append(f"{rules_rel} {key} must be {expected}")

    required_rules = {
        "hierarchy_only_top",
        "hierarchical_module_composition",
        "one_primary_module_per_file",
        "one_function_per_module",
        "verilog_2001_rtl_only",
        "no_systemverilog_in_rtl_or_directed_tb",
        "official_bus_protocol_naming",
        "three_process_fsm_when_applicable",
        "no_monolithic_fsm_file",
        "fsm_single_responsibility",
        "standalone_else",
        "explicit_final_else",
        "explicit_cdc_plan",
        "req_to_rtl_trace_required",
    }
    hard_rules = {str(item) for item in rules.get("hard_rules", []) if str(item)}
    missing = sorted(required_rules - hard_rules)
    if missing:
        errors.append(f"{rules_rel} hard_rules missing RTL skill rule(s): " + ", ".join(missing))

    workspace = _find_workspace_root(project)
    for key in ["source_skill", "style_guide"]:
        value = str(rules.get(key) or "")
        if not value:
            continue
        path = workspace / value
        if not path.is_file():
            errors.append(f"{rules_rel} {key} file not found: {value}")

    module_plan_rel = "work/docparse/architecture/module_plan.yaml"
    module_plan = _load_structured(project / module_plan_rel)
    if module_plan is not None:
        if module_plan.get("rtl_planning_policy_ref") != rules_rel:
            errors.append(f"{module_plan_rel} rtl_planning_policy_ref must point to {rules_rel}")
        wrapper_policy = str((module_plan.get("top_level") or {}).get("wrapper_policy") or "").lower()
        if require_ready and ("hierarchy" not in wrapper_policy or "only" not in wrapper_policy):
            errors.append(f"{module_plan_rel} top_level.wrapper_policy must require a hierarchy-only top")
        partition_policy = module_plan.get("module_partition_policy") or {}
        if require_ready and not partition_policy.get("one_function_per_module"):
            errors.append(f"{module_plan_rel} module_partition_policy.one_function_per_module must be true")
        if require_ready and not partition_policy.get("composite_modules_instantiate_children"):
            errors.append(f"{module_plan_rel} module_partition_policy.composite_modules_instantiate_children must be true")

    state_machines_rel = "work/docparse/architecture/state_machines.yaml"
    state_machines = _load_structured(project / state_machines_rel)
    if state_machines is not None:
        if state_machines.get("rtl_planning_policy_ref") != rules_rel:
            errors.append(f"{state_machines_rel} rtl_planning_policy_ref must point to {rules_rel}")
        style_policy = {str(item) for item in state_machines.get("fsm_style_policy", []) if str(item)}
        if require_ready and "three_process_fsm_when_applicable" not in style_policy:
            errors.append(f"{state_machines_rel} fsm_style_policy must include three_process_fsm_when_applicable")
        if require_ready and "fsm_single_responsibility" not in style_policy:
            errors.append(f"{state_machines_rel} fsm_style_policy must include fsm_single_responsibility")
        if require_ready and FSM_NO_MONOLITHIC_OWNERSHIP_RULE not in style_policy:
            errors.append(f"{state_machines_rel} fsm_style_policy must include the no-large-FSM ownership rule")

    if not require_ready and not missing:
        warnings.append(f"{rules_rel} will be enforced when requirements front door is READY")


def _check_requirement_question_review(
    project: Path,
    errors: list[str],
    warnings: list[str],
    *,
    require_ready: bool,
) -> None:
    analysis = _load_structured(project / DOCUMENT_ANALYSIS_REL)
    questions_path = project / OPEN_QUESTIONS_REL
    if analysis is None:
        return

    review = analysis.get("question_review")
    open_questions = analysis.get("open_questions")

    if not isinstance(open_questions, list):
        errors.append(f"{DOCUMENT_ANALYSIS_REL} open_questions must be a list")
        open_questions = []

    unresolved: list[str] = []
    for index, item in enumerate(open_questions, start=1):
        if not isinstance(item, dict):
            errors.append(f"{DOCUMENT_ANALYSIS_REL} open_questions[{index}] must be a mapping")
            continue
        qid = str(item.get("id") or item.get("question_id") or f"open_questions[{index}]").strip()
        question = str(item.get("question") or "").strip()
        status = str(item.get("status") or "").strip().upper()
        resolution = str(item.get("resolution") or item.get("answer") or "").strip()
        if not question:
            errors.append(f"{DOCUMENT_ANALYSIS_REL} {qid} question must be set")
        if status not in QUESTION_CLOSED_STATUSES:
            unresolved.append(qid)
        elif status not in {"NOT_APPLICABLE", "NOT_BLOCKING"} and not resolution:
            errors.append(f"{DOCUMENT_ANALYSIS_REL} {qid} closed question must include resolution or answer")

    if not require_ready:
        if unresolved:
            warnings.append("requirement open questions remain unresolved: " + ", ".join(unresolved[:8]))
        return

    if not questions_path.is_file():
        errors.append(f"{OPEN_QUESTIONS_REL} must exist and be shown to the user before READY")
        questions_text = ""
    else:
        questions_text = questions_path.read_text(encoding="utf-8", errors="ignore")

    if not isinstance(review, dict):
        errors.append(f"{DOCUMENT_ANALYSIS_REL} question_review must be a mapping for READY")
        review = {}

    status = str(review.get("status") or "").strip().upper()
    if status not in QUESTION_REVIEW_READY_STATUSES:
        errors.append(
            f"{DOCUMENT_ANALYSIS_REL} question_review.status must be one of "
            + ", ".join(sorted(QUESTION_REVIEW_READY_STATUSES))
            + " for READY"
        )
    reviewed_by = str(review.get("reviewed_by") or review.get("reviewer") or "").strip()
    if not reviewed_by:
        errors.append(f"{DOCUMENT_ANALYSIS_REL} question_review.reviewed_by must identify the user/reviewer for READY")
    evidence = str(review.get("review_evidence") or "").strip()
    if evidence != OPEN_QUESTIONS_REL:
        errors.append(f"{DOCUMENT_ANALYSIS_REL} question_review.review_evidence must be {OPEN_QUESTIONS_REL}")

    unresolved_count = review.get("unresolved_count")
    if unresolved_count not in (0, "0"):
        errors.append(f"{DOCUMENT_ANALYSIS_REL} question_review.unresolved_count must be 0 for READY")
    if unresolved:
        errors.append(
            "unresolved requirement questions must be sent to the user and closed before READY: "
            + ", ".join(unresolved[:8])
        )

    if questions_text:
        if not re.search(r"(?mi)^\s*-\s*(?:question_)?review_status:\s*(REVIEWED|USER_REVIEWED|APPROVED)\s*$", questions_text):
            errors.append(f"{OPEN_QUESTIONS_REL} review summary must contain '- question_review_status: REVIEWED'")
        if not re.search(r"(?mi)^\s*-\s*unresolved_count:\s*0\s*$", questions_text):
            errors.append(f"{OPEN_QUESTIONS_REL} review summary must contain '- unresolved_count: 0'")


def _check_external_document_parse_policy(
    project: Path,
    errors: list[str],
    warnings: list[str],
    *,
    require_ready: bool,
) -> None:
    """Require formal MinerU high-precision evidence before READY DocParse."""

    source_docs = _external_requirement_sources(project)
    if not source_docs:
        return

    parsed_root = project / "work" / "docparse" / "parsed"
    extract_root = parsed_root / "mineru_extract"
    illegal_dirs = [
        child.name
        for child in parsed_root.iterdir()
        if child.is_dir() and child.name.lower() in ILLEGAL_PARSED_EVIDENCE_DIRS
    ] if parsed_root.is_dir() else []
    if illegal_dirs:
        errors.append(
            "external document DocParse cannot use temporary/local text evidence directories: "
            + ", ".join(sorted(illegal_dirs))
        )

    provenance_path = extract_root / "provenance.yaml"
    if not provenance_path.is_file():
        message = "external document DocParse requires work/docparse/parsed/mineru_extract/provenance.yaml"
        if require_ready:
            errors.append(message)
        else:
            warnings.append(message)
        return

    try:
        provenance = load_yaml(provenance_path)
    except Exception as exc:
        errors.append(f"cannot read MinerU provenance for external document DocParse: {exc}")
        return
    if not isinstance(provenance, dict):
        errors.append("MinerU provenance for external document DocParse must be a mapping")
        return

    tool = str(provenance.get("tool", "")).strip()
    command = str(provenance.get("command", "")).strip()
    channel = str(provenance.get("channel", "")).strip()
    api_mode = str(provenance.get("api_mode", "")).strip().lower()
    status = str(provenance.get("status", "")).strip().lower()
    endpoints = _endpoint_set(provenance)
    if (
        tool != "mineru-open-api"
        or command != "extract"
        or channel != MINERU_HIGH_PRECISION_CHANNEL
        or api_mode != "high_precision"
    ):
        errors.append(
            "external document DocParse provenance must declare tool=mineru-open-api, "
            "command=extract, channel=mineru-open-api high_precision_api, and api_mode=high_precision"
        )
    if not endpoints.intersection(MINERU_HIGH_PRECISION_ENDPOINTS):
        required = ", ".join(sorted(MINERU_HIGH_PRECISION_ENDPOINTS))
        errors.append("external document DocParse provenance must include high-precision API endpoint evidence: " + required)
    if status and status not in {"complete", "completed", "pass", "passed"}:
        errors.append("external document DocParse provenance status must be complete before READY")

    content_files = [
        path
        for path in extract_root.iterdir()
        if path.is_file() and path.name != "provenance.yaml" and path.suffix.lower() in PARSER_OUTPUT_SUFFIXES
    ] if extract_root.is_dir() else []
    if not content_files:
        errors.append("MinerU high-precision API must produce parsed content files before READY DocParse")

    source_entries = provenance.get("source_documents")
    if require_ready and isinstance(source_entries, list):
        outputs = {
            str(item.get("output", "")).replace("\\", "/")
            for item in source_entries
            if isinstance(item, dict)
        }
        missing_outputs = [
            output
            for output in sorted(outputs)
            if output and not (project / output).is_file()
        ]
        if missing_outputs:
            errors.append("MinerU provenance references missing parsed output(s): " + ", ".join(missing_outputs[:8]))


def _external_requirement_sources(project: Path) -> list[Path]:
    return [
        path
        for path in _requirement_source_files(project)
        if path.suffix.lower() in EXTERNAL_SOURCE_SUFFIXES
    ]


def _requirement_source_files(project: Path) -> list[Path]:
    root = project / SPEC_INPUT_REL
    if not root.is_dir():
        return []
    ignored = {".gitkeep", "README.md"}
    return sorted(path for path in root.iterdir() if path.is_file() and path.name not in ignored)


def _endpoint_set(provenance: dict[str, Any]) -> set[str]:
    endpoints: set[str] = set()
    for key in ("api_endpoints", "endpoints"):
        value = provenance.get(key)
        if isinstance(value, list):
            endpoints.update(str(item).strip() for item in value if str(item).strip())
        elif isinstance(value, str) and value.strip():
            endpoints.add(value.strip())
    for key in ("api_endpoint", "endpoint", "task_endpoint", "file_url_endpoint"):
        value = provenance.get(key)
        if isinstance(value, str) and value.strip():
            endpoints.add(value.strip())
    return endpoints


def _non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def _has_any_ready_payload(data: dict[str, Any], keys: list[str]) -> bool:
    for key in keys:
        value = data.get(key)
        if isinstance(value, list) and value:
            return True
        if isinstance(value, dict) and value:
            return True
        if isinstance(value, str) and value.strip():
            return True
    return False


def _check_document_analysis_payload(data: dict[str, Any], errors: list[str]) -> None:
    rel = DOCUMENT_ANALYSIS_REL
    source_documents = data.get("source_documents")
    analysis_units = data.get("analysis_units")
    evidence_map = data.get("evidence_map")

    if not _non_empty_list(source_documents):
        errors.append(f"{rel} source_documents must be non-empty for READY")
    if not _non_empty_list(analysis_units):
        errors.append(f"{rel} analysis_units must be non-empty for READY")
    if not _non_empty_list(evidence_map):
        errors.append(f"{rel} evidence_map must be non-empty for READY")

    for index, item in enumerate(source_documents if isinstance(source_documents, list) else [], start=1):
        if not isinstance(item, dict):
            errors.append(f"{rel} source_documents[{index}] must be a mapping")
            continue
        for key in ["source_ref", "parser_output", "document_type"]:
            if not str(item.get(key) or "").strip():
                errors.append(f"{rel} source_documents[{index}] {key} must be set")

    for index, item in enumerate(analysis_units if isinstance(analysis_units, list) else [], start=1):
        if not isinstance(item, dict):
            errors.append(f"{rel} analysis_units[{index}] must be a mapping")
            continue
        for key in ["unit_id", "source_ref", "section", "summary"]:
            if not str(item.get(key) or "").strip():
                errors.append(f"{rel} analysis_units[{index}] {key} must be set")
        if not _non_empty_list(item.get("extracted_requirements")) and not _non_empty_list(item.get("evidence_refs")):
            errors.append(f"{rel} analysis_units[{index}] extracted_requirements or evidence_refs must be non-empty")

    for index, item in enumerate(evidence_map if isinstance(evidence_map, list) else [], start=1):
        if not isinstance(item, dict):
            errors.append(f"{rel} evidence_map[{index}] must be a mapping")
            continue
        if not str(item.get("requirement_id") or "").strip():
            errors.append(f"{rel} evidence_map[{index}] requirement_id must be set")
        if not _non_empty_list(item.get("evidence_refs")):
            errors.append(f"{rel} evidence_map[{index}] evidence_refs must be non-empty")


def _write_frontend_report(
    project: Path,
    *,
    title: str,
    result: str,
    created: list[str],
    updated: list[str],
    warnings: list[str],
    errors: list[str],
) -> Path:
    report_dir = project / "output" / "reports" / "docparse"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "requirements_frontend_report.md"
    lines = [
        f"# {title}",
        "",
        f"- project: {project.name}",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- result: {result}",
        "",
        "## Created",
        "",
        *([f"- {item}" for item in created] or ["- none"]),
        "",
        "## Updated",
        "",
        *([f"- {item}" for item in updated] or ["- none"]),
        "",
        "## Warnings",
        "",
        *([f"- {item}" for item in warnings] or ["- none"]),
        "",
        "## Errors",
        "",
        *([f"- {item}" for item in errors] or ["- none"]),
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def _yaml_doc(data: dict[str, Any]) -> str:
    return "\n".join(_yaml_lines(data, 0)) + "\n"


def _yaml_lines(value: Any, indent: int) -> list[str]:
    pad = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if item == []:
                lines.append(f"{pad}{key}: []")
            elif item == {}:
                lines.append(f"{pad}{key}: {{}}")
            elif isinstance(item, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.extend(_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{pad}{key}: {_yaml_scalar(item)}")
        return lines
    if isinstance(value, list):
        if not value:
            return [f"{pad}[]"]
        lines = []
        for item in value:
            if isinstance(item, dict):
                lines.append(f"{pad}-")
                lines.extend(_yaml_lines(item, indent + 2))
            elif isinstance(item, list):
                lines.append(f"{pad}-")
                lines.extend(_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{pad}- {_yaml_scalar(item)}")
        return lines
    return [f"{pad}{_yaml_scalar(value)}"]


def _yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "":
        return '""'
    if any(char in text for char in [":", "#", "{", "}", "[", "]", ",", "\n"]) or text.strip() != text:
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def _yaml_list(items: list[str], indent: int) -> str:
    if not items:
        return "[]"
    pad = " " * indent
    return "\n".join(f"{pad}- {item}" for item in items)


def _trace_yaml(project_name: str, status: str, source_refs: list[str], target: str) -> str:
    return _yaml_doc(
        {
            "schema_version": FRONTEND_VERSION,
            "project": project_name,
            "status": status,
            "owner_role": "spec",
            "target": target,
            "source_refs": source_refs,
            "links": {},
            "unmapped_requirements": [],
            "assumptions": [],
        }
    )


def _open_questions(project_name: str, status: str) -> str:
    return "\n".join(
        [
            "# Open Requirement Questions",
            "",
            f"- project: {project_name}",
            f"- status: {status}",
            "- question_review_status: UNREVIEWED",
            "- reviewed_by:",
            "- unresolved_count: TBD",
            "",
            "Before promoting the requirements front door to READY, Spec Agent must show unresolved questions to the user. The user must answer, accept, waive, or explicitly mark every question not blocking.",
            "",
            "| ID | Owner Role | Question | Blocking Loop | Status | Resolution | User Decision Evidence |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            "",
        ]
    )


def _architecture_md(project_name: str, status: str, refs_inline: str) -> str:
    return "\n".join(
        [
            "# Architecture Design Document",
            "",
            f"- project: {project_name}",
            f"- status: {status}",
            f"- source_refs: {refs_inline}",
            "- rtl_skill: env/rule/skills/rtl-architecture-and-gen/SKILL.md",
            "- rtl_style_guide: env/rule/skills/rtl-architecture-and-gen/references/verilog-rtl-style-guide.md",
            "",
            "## RTL Planning Rules",
            "",
            "- Arch Agent must consume `work/docparse/architecture/rtl_planning_rules.yaml` before Exec Agent enters Loop1 implementation.",
            "- Top-level RTL must be hierarchy-only; behavior belongs in owned submodules.",
            "- Module partitioning must be hierarchical: one major function maps to one primary RTL file, each module owns one function, and parent modules compose child modules.",
            "- Exec Agent owns RTL and the complete functional directed TB; both are Verilog-2001 `.v` only.",
            "- Sim Agent owns UVM, regression, coverage, waveform comparison, and Loop3 board evidence.",
            "- Official bus/protocol/IP signal names must match vendor UG/IP naming; do not append `_i`/`_o` at official boundaries.",
            "- Non-trivial FSMs must plan separate state, next-state, datapath/control ownership, and one control responsibility per FSM.",
            "",
            "## Module Partition",
            "",
            "## Data Flow",
            "",
            "## State Machines",
            "",
            "## Timing Model",
            "",
            "## Loop Handoff",
            "",
            "- Exec Agent consumes module plan and interface contracts, then drives Loop1 RTL/TB implementation.",
            "- Sim Agent consumes RTL/TB/UVM evidence, then drives Loop1/Loop2/Loop3 simulation and board-validation evidence.",
            "- Review Agent writes defects, risks, and correction advice only.",
            "- Arbtr Agent records disputes, feedback targets, and freeze decisions without editing Spec, Arch, or RTL content.",
            "",
        ]
    )


def _verification_md(project_name: str, status: str, refs_inline: str) -> str:
    return "\n".join(
        [
            "# Verification Plan",
            "",
            f"- project: {project_name}",
            f"- status: {status}",
            f"- source_refs: {refs_inline}",
            "",
            "## Module-Level Plan",
            "",
            "## System-Level Plan",
            "",
            "## Assertions",
            "",
            "## Coverage",
            "",
            "## Waveform Secondary Check",
            "",
            "- Plan Loop1 waveform windows from requirement IDs before RTL/TB generation.",
            "- Each planned window must define observed scope/signals, trigger or time span, expected activity, and pass/fail criteria.",
            "- The generated design document must carry this plan into Chapter 4 before Loop1 can be treated as planned.",
            "",
        ]
    )


def _prototype_md(project_name: str, status: str, refs_inline: str) -> str:
    return "\n".join(
        [
            "# Prototype Plan",
            "",
            f"- project: {project_name}",
            f"- status: {status}",
            f"- source_refs: {refs_inline}",
            "",
            "## FPGA Feasibility",
            "",
            "## Resource Estimate",
            "",
            "## Clock and Reset Plan",
            "",
            "## Pin and Board Resource Intent",
            "",
        ]
    )


def _review_md(project_name: str, status: str, refs_yaml: str) -> str:
    role_rows = "\n".join(f"| {item['role']} | {item['title']} | {status} | |" for item in ROLE_CONTRACTS)
    return "\n".join(
        [
            "# Multi-Agent Requirements Review",
            "",
            f"- project: {project_name}",
            f"- status: {status}",
            "- source_refs:",
            refs_yaml,
            "",
            "| Role | Title | Status | Notes |",
            "| --- | --- | --- | --- |",
            role_rows,
            "",
            "## Cross-Agent Conflicts",
            "",
            "## Review Findings",
            "",
            "## Arbtr Handoff",
            "",
        ]
    )


def _find_workspace_root(path: Path) -> Path:
    return find_workspace_root(path)
