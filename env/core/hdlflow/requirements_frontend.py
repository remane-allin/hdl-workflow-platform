"""Structured requirements front-end for the HDL workflow."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .layout import find_workspace_root
from .plan_checks import check_plan
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
ACCEPTANCE_REL = f"{FRONTDOOR_REL}/acceptance_criteria.yaml"
FORBIDDEN_DESIGNS_REL = f"{FRONTDOOR_REL}/forbidden_designs.yaml"
CONTRACT_REL = f"{FRONTDOOR_REL}/contract.yaml"
FRONTDOOR_BASELINE_RELS = [
    f"{FRONTDOOR_REL}/baseline/srs.yaml",
    f"{FRONTDOOR_REL}/baseline/acceptance_criteria.yaml",
    f"{FRONTDOOR_REL}/baseline/design_intent.yaml",
    f"{FRONTDOOR_REL}/baseline/verification_intent.yaml",
    f"{FRONTDOOR_REL}/baseline/prototype_intent.yaml",
    f"{FRONTDOOR_REL}/baseline/forbidden_designs.yaml",
]
FRONTDOOR_TEMPLATE_RELS = [
    f"{FRONTDOOR_REL}/templates/new_requirement.template.yaml",
    f"{FRONTDOOR_REL}/templates/requirement_change.template.yaml",
    f"{FRONTDOOR_REL}/templates/architecture_supplement.template.yaml",
    f"{FRONTDOOR_REL}/templates/verification_supplement.template.yaml",
    f"{FRONTDOOR_REL}/templates/prototype_supplement.template.yaml",
]
FRONTDOOR_TEMPLATE_CONTRACTS = {
    f"{FRONTDOOR_REL}/templates/new_requirement.template.yaml": {
        "template_type": "new_requirement",
        "requires_merge_policy": True,
        "required_fields": [
            "id",
            "request_type",
            "source_refs",
            "requirement_text",
            "rationale",
            "acceptance_criteria",
            "affected_modules",
            "affected_interfaces",
            "design_obligations",
            "verification_obligations",
            "prototype_obligations",
            "trace_links",
            "impacted_documents",
            "risk_impact",
            "approval_status",
            "merge_status",
        ],
        "example_fields": [
            "id",
            "request_type",
            "source_refs",
            "requirement_text",
            "rationale",
            "acceptance_criteria",
            "affected_modules",
            "affected_interfaces",
            "design_obligations",
            "verification_obligations",
            "prototype_obligations",
            "trace_links",
            "impacted_documents",
            "risk_impact",
            "approval_status",
            "merge_status",
        ],
    },
    f"{FRONTDOOR_REL}/templates/requirement_change.template.yaml": {
        "template_type": "requirement_change",
        "requires_merge_policy": True,
        "required_fields": [
            "change_id",
            "target_requirement_id",
            "old_text",
            "new_text",
            "reason",
            "impact_analysis",
            "affected_artifacts",
            "reverification_required",
            "rollback_plan",
            "approval_status",
            "merge_status",
        ],
        "example_fields": [
            "change_id",
            "target_requirement_id",
            "old_text",
            "new_text",
            "reason",
            "impact_analysis",
            "affected_artifacts",
            "reverification_required",
            "rollback_plan",
            "approval_status",
            "merge_status",
        ],
    },
    f"{FRONTDOOR_REL}/templates/architecture_supplement.template.yaml": {
        "template_type": "architecture_supplement",
        "requires_merge_policy": False,
        "required_fields": [
            "supplement_id",
            "source_requirement_ids",
            "rule_text",
            "applies_to",
            "module_plan_changes",
            "interface_contract_changes",
            "forbidden_design_impacts",
            "blocking",
            "documents_to_update",
            "gates_to_update",
            "approval_status",
        ],
        "example_fields": [
            "supplement_id",
            "source_requirement_ids",
            "rule_text",
            "applies_to",
            "module_plan_changes",
            "interface_contract_changes",
            "forbidden_design_impacts",
            "blocking",
            "documents_to_update",
            "gates_to_update",
            "approval_status",
        ],
    },
    f"{FRONTDOOR_REL}/templates/verification_supplement.template.yaml": {
        "template_type": "verification_supplement",
        "requires_merge_policy": False,
        "required_fields": [
            "supplement_id",
            "requirement_ids",
            "test_tasks",
            "task_packaging",
            "expected_model",
            "required_signals",
            "vcd_parser",
            "uvm_obligations",
            "coverage_obligations",
            "final_verdict_rule",
            "approval_status",
        ],
        "example_fields": [
            "supplement_id",
            "requirement_ids",
            "test_tasks",
            "task_packaging",
            "expected_model",
            "required_signals",
            "vcd_parser",
            "uvm_obligations",
            "coverage_obligations",
            "final_verdict_rule",
            "approval_status",
        ],
    },
    f"{FRONTDOOR_REL}/templates/prototype_supplement.template.yaml": {
        "template_type": "prototype_supplement",
        "requires_merge_policy": False,
        "required_fields": [
            "supplement_id",
            "requirement_ids",
            "external_interfaces",
            "database_queries",
            "fallback_mode",
            "validation_modes",
            "claim_policy",
            "pin_level_validation_status",
            "approval_status",
        ],
        "example_fields": [
            "supplement_id",
            "requirement_ids",
            "external_interfaces",
            "database_queries",
            "fallback_mode",
            "validation_modes",
            "claim_policy",
            "pin_level_validation_status",
            "approval_status",
        ],
    },
}
FRONTDOOR_GENERATED_RELS = [
    f"{FRONTDOOR_REL}/generated/active_srs.generated.yaml",
    f"{FRONTDOOR_REL}/generated/active_design_intent.generated.yaml",
    f"{FRONTDOOR_REL}/generated/active_verification_intent.generated.yaml",
    f"{FRONTDOOR_REL}/generated/active_prototype_intent.generated.yaml",
    f"{FRONTDOOR_REL}/generated/active_trace_matrix.generated.yaml",
]
FRONTDOOR_REQUIRED_DIR_RELS = [
    f"{FRONTDOOR_REL}/intake/pending",
    f"{FRONTDOOR_REL}/intake/approved",
    f"{FRONTDOOR_REL}/intake/rejected",
    f"{FRONTDOOR_REL}/intake/merged",
    f"{FRONTDOOR_REL}/history/baseline_snapshots",
    f"{FRONTDOOR_REL}/history/merged_intake",
    f"{FRONTDOOR_REL}/history/rejected_intake",
]
DOCUMENT_ANALYSIS_REL = "work/docparse/structured_spec/document_analysis.yaml"
DOC_PROJECTION_REL = "work/docparse/doc_projection.yaml"
DOCPARSE_TRACE_RELS = [
    "work/docparse/trace_matrix/req_to_design_intent.yaml",
    "work/docparse/trace_matrix/req_to_test_intent.yaml",
    "work/docparse/trace_matrix/req_to_uvm_intent.yaml",
]
LOOP_TRACE_RELS = [
    "work/loop1_rtl_tb/trace_matrix/req_to_rtl.yaml",
    "work/loop1_rtl_tb/trace_matrix/req_to_directed_tb.yaml",
    "work/loop2_uvm/trace_matrix/req_to_uvm.yaml",
    "work/loop2_uvm/trace_matrix/req_to_assertion.yaml",
    "work/loop2_uvm/trace_matrix/req_to_coverage.yaml",
    "work/loop3_fpga_proto/trace_matrix/req_to_fpga_evidence.yaml",
]
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
            ACCEPTANCE_REL,
            FORBIDDEN_DESIGNS_REL,
            "work/docparse/structured_spec/interface_spec.yaml",
            DOCUMENT_ANALYSIS_REL,
            "work/docparse/structured_spec/interface_timing.yaml",
            "work/docparse/structured_spec/register_map.yaml",
            "work/docparse/structured_spec/test_intent.yaml",
            "work/docparse/structured_spec/timing_rules.yaml",
            "work/docparse/req_decompose/requirements.json",
        ],
    },
    {
        "role": "arch",
        "title": "Arch Agent",
        "owns": "module topology, bus architecture, hierarchy partition, throughput planning, interfaces, and dataflow",
        "primary_outputs": [
            "work/docparse/architecture/module_plan.yaml",
            "work/docparse/architecture/interface_contracts.yaml",
            "work/docparse/architecture/dataflow.yaml",
            "work/docparse/architecture/state_machines.yaml",
            "work/docparse/architecture/timing_model.yaml",
            "work/docparse/doc_projection.yaml",
            "work/docparse/trace_matrix/req_to_design_intent.yaml",
        ],
    },
    {
        "role": "exec",
        "title": "Exec Agent",
        "owns": "Verilog RTL implementation, instance relationships, full functional directed TB, combinational logic, and sequential logic",
        "primary_outputs": [
            "output/rtl/",
            "output/tb/",
            "work/loop1_rtl_tb/trace_matrix/req_to_rtl.yaml",
            "work/loop1_rtl_tb/trace_matrix/req_to_directed_tb.yaml",
        ],
    },
    {
        "role": "sim",
        "title": "Sim Agent",
        "owns": "simulation tests, wave sampling, logs, coverage, UVM, board-level validation evidence, and waveform comparison",
        "primary_outputs": [
            "work/docparse/verification/verification_plan.yaml",
            "work/docparse/verification/uvm_plan.yaml",
            "work/docparse/verification/assertion_plan.yaml",
            "work/docparse/verification/coverage_plan.yaml",
            "output/uvm/",
            "output/reports/loop1/",
            "output/reports/loop2/",
            "output/reports/loop3/",
            "work/docparse/trace_matrix/req_to_test_intent.yaml",
            "work/docparse/trace_matrix/req_to_uvm_intent.yaml",
            "work/loop2_uvm/trace_matrix/req_to_uvm.yaml",
            "work/loop2_uvm/trace_matrix/req_to_assertion.yaml",
            "work/loop2_uvm/trace_matrix/req_to_coverage.yaml",
            "work/loop3_fpga_proto/trace_matrix/req_to_fpga_evidence.yaml",
        ],
    },
    {
        "role": "review",
        "title": "Review Agent",
        "owns": "defect list, risk level, correction advice, compliance review, and root-cause routing without editing spec, architecture, or RTL",
        "primary_outputs": [
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
    CONTRACT_REL,
    SRS_REL,
    ACCEPTANCE_REL,
    FORBIDDEN_DESIGNS_REL,
    *FRONTDOOR_BASELINE_RELS,
    *FRONTDOOR_TEMPLATE_RELS,
    *FRONTDOOR_GENERATED_RELS,
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
    "work/docparse/verification/uvm_plan.yaml",
    "work/docparse/verification/assertion_plan.yaml",
    "work/docparse/verification/coverage_plan.yaml",
    "work/docparse/prototype/prototype_plan.yaml",
    "work/docparse/prototype/clock_plan.yaml",
    "work/docparse/prototype/pin_resource_intent.yaml",
    "work/docparse/review/role_findings.yaml",
    "work/docparse/review/decision_log.yaml",
    "work/docparse/review/arbitration_log.yaml",
    DOC_PROJECTION_REL,
    *DOCPARSE_TRACE_RELS,
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
    _check_architecture_cross_file_contracts(project, errors, require_ready=require_ready)
    _check_doc_projection_contract(project, errors, require_ready=require_ready)
    _check_frontdoor_governance_model(project, errors, warnings, require_ready=require_ready)
    _check_requirement_question_review(project, errors, warnings, require_ready=require_ready)
    _check_external_document_parse_policy(project, errors, warnings, require_ready=require_ready)
    plan_result = check_plan(project, maturity="loop1" if require_ready else "docparse")
    warnings.extend(f"plan-check: {issue.severity}: {issue.path}: {issue.message}" for issue in plan_result.issues[:20])

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
    module_item_template = {
        "id": "",
        "name": "",
        "type": "leaf",
        "status": "draft",
        "confidence": "low",
        "known_unknowns": [],
        "open_questions": [],
        "source_file": "",
        "parent": "",
        "children": [],
        "responsibility": "",
        "boundary_rationale": "",
        "clock_domain": "",
        "reset_domain": "",
        "owns": {
            "registers": [],
            "register_fields": [],
            "fsms": [],
            "fifos": [],
            "memories": [],
            "counters": [],
            "arbiters": [],
            "error_flags": [],
        },
        "interfaces": {
            "inputs": [],
            "outputs": [],
            "internal": [],
        },
        "dataflow": {
            "consumes": [],
            "produces": [],
            "transforms": [],
        },
        "req_ids": [],
        "design_feature_ids": [],
        "verification_refs": {
            "tests": [],
            "assertions": [],
            "coverage": [],
        },
        "forbidden_responsibilities": [],
    }

    return {
        **_frontdoor_governance_templates(project_name, status, source_refs),
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
                    "top_down_module_partitioning",
                    "cohesive_module_boundary",
                    "balanced_module_granularity",
                    "verilog_2001_rtl_only",
                    "no_systemverilog_in_rtl_or_directed_tb",
                    "official_bus_protocol_naming",
                    "protocol_naming_follows_official_or_industry_standard",
                    "three_process_fsm_when_applicable",
                    "no_monolithic_fsm_file",
                    "fsm_single_responsibility",
                    "standalone_else",
                    "explicit_final_else",
                    "explicit_cdc_plan",
                    "staged_trace_contract_required",
                ],
                "module_plan_requirements": [
                    "module hierarchy",
                    "parent/child module composition",
                    "top-down functional-domain partition",
                    "clear module boundary and ownership",
                    "balanced granularity that avoids broad monoliths and over-fragmented helper files",
                    "clock/reset ownership",
                    "interface ownership",
                    "register block ownership",
                    "protocol module naming follows official or industry terminology",
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
                "top_level": {
                    "name": "",
                    "type": "top",
                    "source_file": "",
                    "wrapper_policy": "hierarchy_only_top",
                    "allowed_responsibilities": [
                        "instantiate_child_modules",
                        "connect_interfaces",
                        "expose_top_ports",
                    ],
                    "forbidden_responsibilities": [
                        "protocol_decode",
                        "register_field_update",
                        "datapath_mutation",
                        "fifo_storage",
                        "arbitration_decision",
                        "monolithic_fsm",
                    ],
                },
                "module_partition_policy": {
                    "hierarchy_required": True,
                    "one_primary_module_per_file": True,
                    "top_down_partitioning": True,
                    "file_boundary_granularity": "functional_domain",
                    "cohesive_responsibility_per_file": True,
                    "composite_modules_instantiate_children": True,
                    "allow_internal_subblocks_without_files": True,
                    "no_over_fragmentation": True,
                    "no_under_fragmentation": True,
                    "no_monolithic_fsm": True,
                    "no_free_floating_top_logic": True,
                    "protocol_module_names_follow_official_standard": True,
                    "explicit_ownership_required": True,
                },
                "module_granularity_policy": {
                    "planning_order": "top_down",
                    "file_boundary_rule": "Use one RTL file for a cohesive protocol, register, FIFO, datapath, status, or boundary block.",
                    "split_when": [
                        "a child has independent clock/reset ownership",
                        "a child has reusable storage/IP ownership",
                        "a child is a separately verifiable protocol or datapath boundary",
                        "keeping it inside the parent would create a broad monolithic FSM or hidden side effect",
                    ],
                    "keep_inside_parent_when": [
                        "the logic is only a small decode, mux, counter, bit-order, parity, or pulse-generation subblock",
                        "the subblock has no independent interface contract",
                        "the subblock is only meaningful inside one protocol engine",
                    ],
                    "naming_rule": "Protocol-facing modules use official or industry names such as spi_slave_if, axi_lite_if, arinc429_tx, or arinc429_rx.",
                },
                "module_item_contract": {
                    "required_fields": [
                        "id",
                        "name",
                        "type",
                        "status",
                        "confidence",
                        "known_unknowns",
                        "source_file",
                        "parent",
                        "responsibility",
                        "clock_domain",
                        "reset_domain",
                        "owns",
                        "interfaces",
                        "dataflow",
                        "req_ids or design_feature_ids",
                        "verification_refs",
                        "forbidden_responsibilities",
                    ],
                    "allowed_types": ["top", "composite", "leaf"],
                    "ownership_lists": [
                        "registers",
                        "register_fields",
                        "fsms",
                        "fifos",
                        "memories",
                        "counters",
                        "arbiters",
                        "error_flags",
                    ],
                    "interface_lists": ["inputs", "outputs", "internal"],
                    "dataflow_lists": ["consumes", "produces", "transforms"],
                },
                "modules": [module_item_template],
                "clock_reset": [],
                "throughput_plan": [],
                "composition": [],
                "implementation_order": [],
                "dependencies": [],
                "agent_consumers": ["Exec Agent", "Sim Agent", "Review Agent", "Arbtr Agent"],
                "assumptions": [],
            }
        ),
        "work/docparse/architecture/interface_contracts.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "arch",
                "interfaces": [
                    {
                        "id": "",
                        "name": "",
                        "producer_module": "",
                        "consumer_module": "",
                        "clock_domain": "",
                        "reset_domain": "",
                        "pins": [],
                        "signals": [],
                        "protocol": "",
                        "contract": [],
                        "latency": "",
                        "req_ids": [],
                    }
                ],
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
                "flows": [
                    {
                        "id": "",
                        "name": "",
                        "producer_module": "",
                        "consumer_module": "",
                        "path": [],
                        "payload": "",
                        "control": "",
                        "latency": "",
                        "req_ids": [],
                    }
                ],
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
                "clock_domains": [
                    {
                        "name": "",
                        "source": "",
                    }
                ],
                "resets": [],
                "latency_requirements": [],
                "cdc_requirements": [
                    {
                        "id": "",
                        "interface": "",
                        "producer_module": "",
                        "consumer_module": "",
                        "from_clock_domain": "",
                        "to_clock_domain": "",
                        "synchronizer": "",
                        "req_ids": [],
                    }
                ],
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
        "work/docparse/verification/uvm_plan.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "sim",
                "framework": {
                    "root": "output/uvm",
                    "template_family": "rkv_style_uvm",
                    "package_entry": "output/uvm/env/uvm_pkg.sv",
                    "tb_top": "output/uvm/tb/tb_uvm.sv",
                    "entry_check": "work/loop2_uvm/sim/uvm_full_functional.do",
                    "regression_entry": "work/loop2_uvm/sim/regression.do",
                    "required_entry_files": [
                        "output/uvm/tb/tb_dut_if.sv",
                        "output/uvm/env/uvm_pkg.sv",
                        "output/uvm/tb/tb_uvm.sv",
                    ],
                },
                "interfaces": [],
                "agents": [],
                "env_components": [],
                "scoreboards": [],
                "tests": [],
                "coverage": [],
                "handoff_gates": [],
                "assumptions": [],
            }
        ),
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
                    "review_evidence": DOCUMENT_ANALYSIS_REL,
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
        DOC_PROJECTION_REL: _doc_projection_yaml(project_name, status, source_refs),
        "work/docparse/trace_matrix/req_to_design_intent.yaml": _trace_yaml(
            project_name,
            status,
            source_refs,
            "docparse",
            "design_intent",
            "arch",
        ),
        "work/docparse/trace_matrix/req_to_test_intent.yaml": _trace_yaml(
            project_name,
            status,
            source_refs,
            "docparse",
            "test_intent",
            "sim",
        ),
        "work/docparse/trace_matrix/req_to_uvm_intent.yaml": _trace_yaml(
            project_name,
            status,
            source_refs,
            "docparse",
            "uvm_intent",
            "sim",
        ),
    }


def _frontdoor_governance_templates(project_name: str, status: str, source_refs: list[str]) -> dict[str, str]:
    base = {
        "schema_version": FRONTEND_VERSION,
        "project": project_name,
        "status": status,
        "source_refs": source_refs,
    }
    machine_readable = list(FRONTDOOR_GENERATED_RELS)
    artifacts: dict[str, str] = {
        CONTRACT_REL: _yaml_doc(
            {
                **base,
                "owner_role": "arbtr",
                "contract_version": "frontdoor_contract_v2",
                "active_contract": "generated_active_baseline",
                "authoritative_baseline": {
                    "human_readable": [
                        "output/docs/design/microarchitecture_spec.md",
                        "output/docs/test/verification_plan.md",
                        "output/docs/delivery/delivery_package.md",
                    ],
                    "machine_readable": machine_readable,
                    "hash_binding": {
                        "required": True,
                        "manifest": "output/docs/manifests/docset_manifest.json",
                    },
                },
                "derived_plans": [
                    "work/docparse/architecture/module_plan.yaml",
                    "work/docparse/verification/verification_plan.yaml",
                    "work/docparse/verification/uvm_plan.yaml",
                    "work/loop1_rtl_tb/config/top_wave_manifest.yaml",
                    "work/loop3_fpga_proto/board_tests/prototype_plan.yaml",
                ],
                "legacy_contracts": {
                    f"{FRONTDOOR_REL}/open_questions.md": {
                        "status": "inactive",
                        "replacement": DOCUMENT_ANALYSIS_REL,
                        "reason": "Open questions are tracked in document_analysis.yaml question_review and open_questions mappings.",
                    }
                },
                "execution_lock": {
                    "pending_intake_blocks_execution": True,
                    "approved_intake_must_merge_before_execution": True,
                    "derived_plans_must_not_add_design_intent": True,
                },
            }
        ),
    }

    baseline_refs = {
        f"{FRONTDOOR_REL}/baseline/srs.yaml": SRS_REL,
        f"{FRONTDOOR_REL}/baseline/acceptance_criteria.yaml": ACCEPTANCE_REL,
        f"{FRONTDOOR_REL}/baseline/design_intent.yaml": "work/docparse/architecture/module_plan.yaml",
        f"{FRONTDOOR_REL}/baseline/verification_intent.yaml": "work/docparse/verification/verification_plan.yaml",
        f"{FRONTDOOR_REL}/baseline/prototype_intent.yaml": "work/docparse/prototype/prototype_plan.yaml",
        f"{FRONTDOOR_REL}/baseline/forbidden_designs.yaml": FORBIDDEN_DESIGNS_REL,
    }
    for rel, source_rel in baseline_refs.items():
        artifacts[rel] = _yaml_doc(
            {
                **base,
                "owner_role": "arbtr",
                "baseline_source": source_rel,
                "baseline_type": Path(rel).stem,
                "snapshot_policy": "refresh only through approved frontdoor intake merge",
                "items": [],
                "assumptions": [],
            }
        )

    template_payloads = {
        f"{FRONTDOOR_REL}/templates/new_requirement.template.yaml": {
            "template_type": "new_requirement",
            "intake_target": f"{FRONTDOOR_REL}/intake/pending",
            "merge_policy": "approved request must merge into generated active_srs, design, verification, prototype, and trace baselines before execution",
            "required_fields": [
                "id",
                "request_type",
                "source_refs",
                "requirement_text",
                "rationale",
                "acceptance_criteria",
                "affected_modules",
                "affected_interfaces",
                "design_obligations",
                "verification_obligations",
                "prototype_obligations",
                "trace_links",
                "impacted_documents",
                "risk_impact",
                "approval_status",
                "merge_status",
            ],
            "example": {
                "id": "REQ-NEW-001",
                "request_type": "new_requirement",
                "source_refs": ["input/spec/user_request.md"],
                "owner_role": "spec",
                "requirement_text": "The design shall implement the requested observable behavior.",
                "rationale": "Record why this is a product requirement, not an implementation guess.",
                "priority": "must",
                "acceptance_criteria": [
                    {
                        "id": "AC-REQ-NEW-001",
                        "text": "Observable pass/fail condition tied to the requirement.",
                        "verification_method": "loop1_directed_tb_or_loop2_uvm",
                    }
                ],
                "affected_modules": ["module_or_new_module_name"],
                "affected_interfaces": ["top_or_bus_signal_name"],
                "affected_registers": [],
                "design_obligations": ["Update module_plan/dataflow/interface_contracts when approved."],
                "verification_obligations": ["Create task-bound Loop1 checks and UVM coverage/scoreboard intent."],
                "prototype_obligations": ["State whether Loop3 evidence is required or explicitly not applicable."],
                "trace_links": [
                    {
                        "requirement_id": "REQ-NEW-001",
                        "design_intent": "work/docparse/architecture/module_plan.yaml",
                        "verification_intent": "work/docparse/verification/verification_plan.yaml",
                        "prototype_intent": "work/docparse/prototype/prototype_plan.yaml",
                    }
                ],
                "impacted_documents": [
                    f"{FRONTDOOR_REL}/generated/active_srs.generated.yaml",
                    f"{FRONTDOOR_REL}/generated/active_design_intent.generated.yaml",
                    f"{FRONTDOOR_REL}/generated/active_verification_intent.generated.yaml",
                    f"{FRONTDOOR_REL}/generated/active_trace_matrix.generated.yaml",
                ],
                "risk_impact": "List compatibility, timing, protocol, coverage, and claim risks.",
                "approval_status": "pending",
                "merge_status": "not_merged",
            },
        },
        f"{FRONTDOOR_REL}/templates/requirement_change.template.yaml": {
            "template_type": "requirement_change",
            "intake_target": f"{FRONTDOOR_REL}/intake/pending",
            "merge_policy": "approved change must update generated active baselines and invalidate downstream stale gate evidence",
            "required_fields": [
                "change_id",
                "target_requirement_id",
                "old_text",
                "new_text",
                "reason",
                "impact_analysis",
                "affected_artifacts",
                "reverification_required",
                "rollback_plan",
                "approval_status",
                "merge_status",
            ],
            "example": {
                "change_id": "REQ-CHG-001",
                "target_requirement_id": "REQ-EXISTING-001",
                "old_text": "Previous approved requirement text.",
                "new_text": "Replacement requirement text.",
                "reason": "Why the previous baseline is wrong or incomplete.",
                "impact_analysis": ["architecture", "directed_tb", "uvm", "claim_policy"],
                "affected_artifacts": [
                    f"{FRONTDOOR_REL}/generated/active_srs.generated.yaml",
                    "work/docparse/architecture/module_plan.yaml",
                    "work/docparse/verification/verification_plan.yaml",
                ],
                "reverification_required": True,
                "rollback_plan": "Reject or archive this intake if evidence does not support the change.",
                "approval_status": "pending",
                "merge_status": "not_merged",
            },
        },
        f"{FRONTDOOR_REL}/templates/architecture_supplement.template.yaml": {
            "template_type": "architecture_supplement",
            "intake_target": f"{FRONTDOOR_REL}/intake/pending",
            "required_fields": [
                "supplement_id",
                "source_requirement_ids",
                "rule_text",
                "applies_to",
                "module_plan_changes",
                "interface_contract_changes",
                "forbidden_design_impacts",
                "blocking",
                "documents_to_update",
                "gates_to_update",
                "approval_status",
            ],
            "example": {
                "supplement_id": "ARCH-SUP-001",
                "source_requirement_ids": ["REQ-NEW-001"],
                "rule_text": "Architecture rule or partitioning decision.",
                "applies_to": ["work/docparse/architecture/module_plan.yaml"],
                "module_plan_changes": ["Add/modify module ownership and interfaces."],
                "interface_contract_changes": ["Signal, timing, or register contract updates."],
                "forbidden_design_impacts": ["No event-level injection or accept-all shortcut."],
                "blocking": True,
                "documents_to_update": ["output/docs/design/microarchitecture_spec.md"],
                "gates_to_update": ["docparse", "loop1"],
                "approval_status": "pending",
            },
        },
        f"{FRONTDOOR_REL}/templates/verification_supplement.template.yaml": {
            "template_type": "verification_supplement",
            "intake_target": f"{FRONTDOOR_REL}/intake/pending",
            "required_fields": [
                "supplement_id",
                "requirement_ids",
                "test_tasks",
                "task_packaging",
                "expected_model",
                "required_signals",
                "vcd_parser",
                "uvm_obligations",
                "coverage_obligations",
                "final_verdict_rule",
                "approval_status",
            ],
            "example": {
                "supplement_id": "VERIF-SUP-001",
                "requirement_ids": ["REQ-NEW-001"],
                "test_tasks": ["tb_task_name_bound_to_requirement"],
                "task_packaging": "Each task emits HDLFLOW|TEST_BEGIN, HDLFLOW|CHECK, and HDLFLOW|SUMMARY evidence.",
                "expected_model": "Spec-derived expected behavior, not DUT echo.",
                "required_signals": ["top.input_signal", "top.output_signal"],
                "vcd_parser": "loop1-waveform-gate must sample required_signals and fail missing/incorrect transitions.",
                "uvm_obligations": ["monitor observed transactions", "scoreboard independent expected model"],
                "coverage_obligations": ["functional coverpoint or code coverage target"],
                "final_verdict_rule": "TB PASS and VCD FAIL means final Loop1 result FAIL.",
                "approval_status": "pending",
            },
        },
        f"{FRONTDOOR_REL}/templates/prototype_supplement.template.yaml": {
            "template_type": "prototype_supplement",
            "intake_target": f"{FRONTDOOR_REL}/intake/pending",
            "required_fields": [
                "supplement_id",
                "requirement_ids",
                "external_interfaces",
                "database_queries",
                "fallback_mode",
                "validation_modes",
                "claim_policy",
                "pin_level_validation_status",
                "approval_status",
            ],
            "example": {
                "supplement_id": "PROTO-SUP-001",
                "requirement_ids": ["REQ-NEW-001"],
                "external_interfaces": ["board connector, pin, UART, SPI, or GPIO boundary"],
                "database_queries": ["FPGA IO/schematic/tool command lookups required before script generation."],
                "fallback_mode": "none_or_ps_pl_software_emulated",
                "validation_modes": ["simulation", "prototype_bringup"],
                "claim_policy": {
                    "may_claim_external_pin_level_validation": False,
                    "may_claim_full_hardware_validation": False,
                },
                "pin_level_validation_status": "not_validated",
                "approval_status": "pending",
            },
        },
    }
    for rel, payload in template_payloads.items():
        artifacts[rel] = _yaml_doc(
            {
                "schema_version": FRONTEND_VERSION,
                "project": project_name,
                **payload,
            }
        )

    generated_payloads = {
        f"{FRONTDOOR_REL}/generated/active_srs.generated.yaml": {
            "source_artifacts": [SRS_REL, f"{FRONTDOOR_REL}/intake/merged"],
            "requirements": [],
        },
        f"{FRONTDOOR_REL}/generated/active_design_intent.generated.yaml": {
            "source_artifacts": ["work/docparse/architecture/module_plan.yaml", f"{FRONTDOOR_REL}/intake/merged"],
            "design_obligations": [],
        },
        f"{FRONTDOOR_REL}/generated/active_verification_intent.generated.yaml": {
            "source_artifacts": ["work/docparse/verification/verification_plan.yaml", "work/docparse/verification/uvm_plan.yaml", f"{FRONTDOOR_REL}/intake/merged"],
            "verification_obligations": [],
        },
        f"{FRONTDOOR_REL}/generated/active_prototype_intent.generated.yaml": {
            "source_artifacts": ["work/docparse/prototype/prototype_plan.yaml", f"{FRONTDOOR_REL}/intake/merged"],
            "prototype_obligations": [],
        },
        f"{FRONTDOOR_REL}/generated/active_trace_matrix.generated.yaml": {
            "source_artifacts": [*DOCPARSE_TRACE_RELS, f"{FRONTDOOR_REL}/intake/merged"],
            "links": [],
        },
    }
    for rel, payload in generated_payloads.items():
        artifacts[rel] = _yaml_doc(
            {
                **base,
                "owner_role": "arbtr",
                "generated_from": "approved and merged frontdoor baseline",
                **payload,
                "assumptions": [],
            }
        )

    for rel in FRONTDOOR_REQUIRED_DIR_RELS:
        artifacts[f"{rel}/README.md"] = "\n".join(
            [
                f"# {rel}",
                "",
                "Managed by the requirements frontdoor governance model.",
                "Do not bypass approved intake, merge, and active baseline refresh gates.",
                "",
            ]
        )

    return artifacts


def _requirement_source_refs(project: Path) -> list[str]:
    root = project / SPEC_INPUT_REL
    if not root.is_dir():
        return []
    ignored = {
        ".gitkeep",
        "README.md",
        "srs.yaml",
        "acceptance_criteria.yaml",
        "forbidden_designs.yaml",
        "requirements.json",
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
    if rel == SRS_REL:
        functional = data.get("functional_requirements")
        non_functional = data.get("non_functional_requirements")
        if not _non_empty_list(functional) and not _non_empty_list(non_functional):
            errors.append(f"{rel} must contain at least one requirement for READY")
    if rel == ACCEPTANCE_REL and not _non_empty_list(data.get("criteria")):
        errors.append(f"{rel} criteria must be non-empty for READY")
    if rel == FORBIDDEN_DESIGNS_REL and not _non_empty_list(data.get("forbidden_designs")):
        errors.append(f"{rel} forbidden_designs must be non-empty for READY")
    if rel.endswith("interface_spec.yaml") and not _has_any_ready_payload(data, ["interfaces", "ports"]):
        errors.append(f"{rel} interfaces or ports must be non-empty for READY")
    if rel == DOCUMENT_ANALYSIS_REL:
        _check_document_analysis_payload(data, errors)
    if rel.endswith("register_map.yaml") and not _has_any_ready_payload(data, ["registers", "opcodes", "commands"]):
        errors.append(f"{rel} registers, opcodes, or commands must be non-empty for READY")
    if rel.endswith("structured_spec/test_intent.yaml") and not _has_any_ready_payload(
        data,
        ["functional_tests", "baseline_entry_checks", "full_function_matrix", "corner_cases", "coverage_targets"],
    ):
        errors.append(f"{rel} functional test intent must be non-empty for READY")
    if rel.endswith("structured_spec/test_intent.yaml") and not _non_empty_list(data.get("waveform_windows")):
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
        "uvm_plan.yaml": "agents",
        "assertion_plan.yaml": "assertions",
        "coverage_plan.yaml": "functional_coverage",
        "prototype_plan.yaml": "resource_estimate",
        "clock_plan.yaml": "clocks",
        "pin_resource_intent.yaml": "external_ports",
        "doc_projection.yaml": "documents",
    }
    key = required_by_name.get(Path(rel).name)
    if key == "documents":
        if not isinstance(data.get(key), dict) or not data.get(key):
            errors.append(f"{rel} {key} must be non-empty for READY")
    elif key and not _non_empty_list(data.get(key)):
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
    if rel.endswith("uvm_plan.yaml"):
        for uvm_key in ["framework", "interfaces", "agents", "env_components", "scoreboards", "tests", "coverage"]:
            value = data.get(uvm_key)
            if uvm_key == "framework":
                if not isinstance(value, dict) or not value:
                    errors.append(f"{rel} {uvm_key} must be non-empty for READY")
            elif not _non_empty_list(value):
                errors.append(f"{rel} {uvm_key} must be non-empty for READY")


def _check_frontdoor_governance_model(
    project: Path,
    errors: list[str],
    warnings: list[str],
    *,
    require_ready: bool,
) -> None:
    for rel in FRONTDOOR_REQUIRED_DIR_RELS:
        if not (project / rel).is_dir():
            errors.append(f"missing required frontdoor governance directory: {rel}")

    contract = _load_structured(project / CONTRACT_REL)
    if contract is None:
        errors.append(f"{CONTRACT_REL} is not parseable")
        return

    if contract.get("contract_version") != "frontdoor_contract_v2":
        errors.append(f"{CONTRACT_REL} contract_version must be frontdoor_contract_v2")
    if contract.get("active_contract") != "generated_active_baseline":
        errors.append(f"{CONTRACT_REL} active_contract must be generated_active_baseline")

    baseline = contract.get("authoritative_baseline")
    if not isinstance(baseline, dict):
        errors.append(f"{CONTRACT_REL} authoritative_baseline must be a mapping")
    else:
        machine = baseline.get("machine_readable")
        if not _non_empty_list(machine):
            errors.append(f"{CONTRACT_REL} authoritative_baseline.machine_readable must be non-empty")
        else:
            missing = [str(rel) for rel in machine if not (project / str(rel)).is_file()]
            if missing:
                errors.append(f"{CONTRACT_REL} authoritative_baseline.machine_readable missing path(s): " + ", ".join(missing[:8]))
        human = baseline.get("human_readable")
        if human is not None and not isinstance(human, list):
            errors.append(f"{CONTRACT_REL} authoritative_baseline.human_readable must be a list")

    legacy = contract.get("legacy_contracts")
    if isinstance(legacy, dict):
        open_questions = legacy.get(f"{FRONTDOOR_REL}/open_questions.md")
        if (project / FRONTDOOR_REL / "open_questions.md").exists():
            if not isinstance(open_questions, dict) or str(open_questions.get("status", "")).lower() != "inactive":
                errors.append(f"{CONTRACT_REL} must mark {FRONTDOOR_REL}/open_questions.md as inactive legacy")
    elif (project / FRONTDOOR_REL / "open_questions.md").exists():
        errors.append(f"{CONTRACT_REL} legacy_contracts must quarantine {FRONTDOOR_REL}/open_questions.md")

    for rel in FRONTDOOR_TEMPLATE_RELS:
        payload = _load_structured(project / rel)
        if payload is None:
            errors.append(f"{rel} is not parseable")
            continue
        errors.extend(_frontdoor_template_contract_errors(rel, payload))

    generated_text = "\n".join(_read_optional(project, rel) for rel in FRONTDOOR_GENERATED_RELS)
    approved = _frontdoor_intake_files(project, "approved")
    if approved:
        missing_merge = []
        for path in approved:
            token = _frontdoor_intake_token(path)
            if token and token not in generated_text and not _frontdoor_has_merged_intake(project, token):
                missing_merge.append(str(path.relative_to(project)).replace("\\", "/"))
        if missing_merge:
            errors.append(
                "approved_intake_merge_gate: approved intake must be merged into active generated baseline: "
                + ", ".join(missing_merge[:8])
            )

    pending = _frontdoor_intake_files(project, "pending")
    if pending and require_ready:
        errors.append(
            "execution_lock_gate: pending frontdoor intake blocks READY promotion and downstream execution: "
            + ", ".join(str(path.relative_to(project)).replace("\\", "/") for path in pending[:8])
        )
    elif pending:
        warnings.append(
            "execution_lock_gate: pending frontdoor intake exists and must be approved or rejected before execution: "
            + ", ".join(str(path.relative_to(project)).replace("\\", "/") for path in pending[:8])
        )

    trace = _load_structured(project / f"{FRONTDOOR_REL}/generated/active_trace_matrix.generated.yaml")
    if trace is None:
        errors.append(f"{FRONTDOOR_REL}/generated/active_trace_matrix.generated.yaml is not parseable")
    elif approved and not _non_empty_list(trace.get("links")):
        errors.append("trace_freshness_gate: approved intake requires active_trace_matrix.generated.yaml links")


def _frontdoor_template_contract_errors(rel: str, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    contract = FRONTDOOR_TEMPLATE_CONTRACTS.get(rel)
    if not isinstance(contract, dict):
        return [f"{rel} has no platform template contract"]
    expected_type = contract.get("template_type")
    if payload.get("template_type") != expected_type:
        errors.append(f"{rel} template_type must be {expected_type}")
    if payload.get("intake_target") != f"{FRONTDOOR_REL}/intake/pending":
        errors.append(f"{rel} intake_target must be {FRONTDOOR_REL}/intake/pending")
    if contract.get("requires_merge_policy") and not _non_empty_value(payload.get("merge_policy")):
        errors.append(f"{rel} merge_policy must be non-empty")

    required = payload.get("required_fields")
    if not isinstance(required, list) or not required:
        errors.append(f"{rel} required_fields must be a non-empty list")
        required = []
    expected_required = [str(item) for item in contract.get("required_fields", [])]
    missing_required = [field for field in expected_required if field not in required]
    if missing_required:
        errors.append(f"{rel} required_fields missing required platform field(s): " + ", ".join(missing_required))

    example = payload.get("example")
    if not isinstance(example, dict) or not example:
        errors.append(f"{rel} example must be a non-empty mapping")
        return errors
    missing_example = [field for field in contract.get("example_fields", []) if not _non_empty_value(example.get(str(field)))]
    if missing_example:
        errors.append(f"{rel} example missing non-empty field(s): " + ", ".join(str(item) for item in missing_example))
    if "approval_status" in expected_required and example.get("approval_status") != "pending":
        errors.append(f"{rel} example.approval_status must be pending")
    if "merge_status" in expected_required and example.get("merge_status") != "not_merged":
        errors.append(f"{rel} example.merge_status must be not_merged")
    if rel.endswith("new_requirement.template.yaml"):
        if not _non_empty_list(example.get("trace_links")):
            errors.append(f"{rel} example.trace_links must bind requirement to design/verification/prototype intent")
        if not _non_empty_list(example.get("acceptance_criteria")):
            errors.append(f"{rel} example.acceptance_criteria must be non-empty")
    if rel.endswith("verification_supplement.template.yaml"):
        if not _non_empty_list(example.get("required_signals")):
            errors.append(f"{rel} example.required_signals must be non-empty")
        if not _non_empty_value(example.get("vcd_parser")):
            errors.append(f"{rel} example.vcd_parser must be non-empty")
    if rel.endswith("prototype_supplement.template.yaml"):
        claim_policy = example.get("claim_policy")
        if not isinstance(claim_policy, dict):
            errors.append(f"{rel} example.claim_policy must be a mapping")
        else:
            if claim_policy.get("may_claim_external_pin_level_validation") is not False:
                errors.append(f"{rel} example.claim_policy.may_claim_external_pin_level_validation must be false")
            if claim_policy.get("may_claim_full_hardware_validation") is not False:
                errors.append(f"{rel} example.claim_policy.may_claim_full_hardware_validation must be false")
    return errors


def _frontdoor_intake_files(project: Path, state: str) -> list[Path]:
    root = project / FRONTDOOR_REL / "intake" / state
    if not root.is_dir():
        return []
    ignored = {".gitkeep", "README.md"}
    return sorted(path for path in root.iterdir() if path.is_file() and path.name not in ignored)


def _frontdoor_intake_token(path: Path) -> str:
    payload = _load_structured(path)
    if isinstance(payload, dict):
        for key in ("id", "change_id", "requirement_id", "supplement_id"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return path.stem


def _frontdoor_has_merged_intake(project: Path, token: str) -> bool:
    merged_roots = [
        project / FRONTDOOR_REL / "intake" / "merged",
        project / FRONTDOOR_REL / "history" / "merged_intake",
    ]
    for root in merged_roots:
        if not root.is_dir():
            continue
        for path in root.iterdir():
            if path.is_file() and token in path.name:
                return True
    return False


def _read_optional(project: Path, rel: str) -> str:
    path = project / rel
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


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
    expected_targets = {
        "work/docparse/trace_matrix/req_to_design_intent.yaml": "design_intent",
        "work/docparse/trace_matrix/req_to_test_intent.yaml": "test_intent",
        "work/docparse/trace_matrix/req_to_uvm_intent.yaml": "uvm_intent",
    }
    for rel in DOCPARSE_TRACE_RELS:
        data = _load_structured(project / rel)
        if data is None:
            continue
        if str(data.get("stage") or "") != "docparse":
            errors.append(f"{rel} stage must be docparse")
        expected_target = expected_targets.get(rel)
        if expected_target and str(data.get("target") or "") != expected_target:
            errors.append(f"{rel} target must be {expected_target}")
        if "links" not in data:
            errors.append(f"{rel} must contain links")
        elif not isinstance(data.get("links"), list):
            errors.append(f"{rel} links must be a list")
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
        "top_down_module_partitioning",
        "cohesive_module_boundary",
        "balanced_module_granularity",
        "verilog_2001_rtl_only",
        "no_systemverilog_in_rtl_or_directed_tb",
        "official_bus_protocol_naming",
        "protocol_naming_follows_official_or_industry_standard",
        "three_process_fsm_when_applicable",
        "no_monolithic_fsm_file",
        "fsm_single_responsibility",
        "standalone_else",
        "explicit_final_else",
        "explicit_cdc_plan",
        "staged_trace_contract_required",
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
        if require_ready and not _policy_true(partition_policy.get("top_down_partitioning")):
            errors.append(f"{module_plan_rel} module_partition_policy.top_down_partitioning must be true")
        if require_ready and "functional" not in str(partition_policy.get("file_boundary_granularity") or "").lower():
            errors.append(f"{module_plan_rel} module_partition_policy.file_boundary_granularity must be functional_domain")
        if require_ready and not _policy_true(partition_policy.get("cohesive_responsibility_per_file")):
            errors.append(f"{module_plan_rel} module_partition_policy.cohesive_responsibility_per_file must be true")
        if require_ready and not _policy_true(partition_policy.get("no_over_fragmentation")):
            errors.append(f"{module_plan_rel} module_partition_policy.no_over_fragmentation must be true")
        if require_ready and not _policy_true(partition_policy.get("no_under_fragmentation")):
            errors.append(f"{module_plan_rel} module_partition_policy.no_under_fragmentation must be true")
        if require_ready and not _policy_true(partition_policy.get("protocol_module_names_follow_official_standard")):
            errors.append(f"{module_plan_rel} module_partition_policy.protocol_module_names_follow_official_standard must be true")
        if require_ready and not _policy_true(partition_policy.get("composite_modules_instantiate_children")):
            errors.append(f"{module_plan_rel} module_partition_policy.composite_modules_instantiate_children must be true")
        granularity_policy = module_plan.get("module_granularity_policy") or {}
        if require_ready:
            if str(granularity_policy.get("planning_order") or "").lower() != "top_down":
                errors.append(f"{module_plan_rel} module_granularity_policy.planning_order must be top_down")
            if not _non_empty_list(granularity_policy.get("split_when")):
                errors.append(f"{module_plan_rel} module_granularity_policy.split_when must be non-empty")
            if not _non_empty_list(granularity_policy.get("keep_inside_parent_when")):
                errors.append(f"{module_plan_rel} module_granularity_policy.keep_inside_parent_when must be non-empty")
        if require_ready:
            _check_module_plan_contract(module_plan_rel, module_plan, errors)

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


def _check_module_plan_contract(rel: str, data: dict[str, Any], errors: list[str]) -> None:
    top = data.get("top_level") if isinstance(data.get("top_level"), dict) else {}
    top_name = str(top.get("name") or "").strip()
    if not top_name:
        errors.append(f"{rel} top_level.name must be non-empty for READY")
    top_forbidden = _string_set(top.get("forbidden_responsibilities"))
    for item in ["protocol_decode", "register_field_update", "datapath_mutation", "fifo_storage", "monolithic_fsm"]:
        if item not in top_forbidden:
            errors.append(f"{rel} top_level.forbidden_responsibilities must include {item}")

    modules = data.get("modules")
    if not isinstance(modules, list) or not modules:
        errors.append(f"{rel} modules must be a non-empty list for READY")
        return

    module_names: set[str] = set()
    ownership: dict[str, dict[str, str]] = {
        "registers": {},
        "register_fields": {},
        "fsms": {},
        "fifos": {},
        "memories": {},
        "counters": {},
        "arbiters": {},
        "error_flags": {},
    }
    required_owns = list(ownership.keys())
    required_interfaces = ["inputs", "outputs", "internal"]
    required_dataflow = ["consumes", "produces", "transforms"]
    module_children: dict[str, list[str]] = {}
    for index, module in enumerate(modules, start=1):
        label = f"{rel} modules[{index}]"
        if not isinstance(module, dict):
            errors.append(f"{label} must be a mapping")
            continue
        name = str(module.get("name") or "").strip()
        if not name:
            errors.append(f"{label}.name must be non-empty")
        else:
            if name in module_names:
                errors.append(f"{rel} duplicate module name: {name}")
            module_names.add(name)
        for key in ["id", "type", "responsibility"]:
            if key == "parent" and name == top_name:
                continue
            if not str(module.get(key) or "").strip():
                errors.append(f"{label}.{key} must be non-empty")
        for key in ["source_file", "parent", "clock_domain", "reset_domain", "status", "confidence", "known_unknowns"]:
            if key not in module and not (key == "parent" and name == top_name):
                errors.append(f"{label}.{key} must be present")

        owns = module.get("owns")
        if not isinstance(owns, dict):
            errors.append(f"{label}.owns must be a mapping")
            owns = {}
        for key in required_owns:
            if key not in owns:
                errors.append(f"{label}.owns.{key} must be present")
            elif not isinstance(owns.get(key), list):
                errors.append(f"{label}.owns.{key} must be a list")
        interfaces = module.get("interfaces")
        if not isinstance(interfaces, dict):
            errors.append(f"{label}.interfaces must be a mapping")
            interfaces = {}
        for key in required_interfaces:
            if key not in interfaces:
                errors.append(f"{label}.interfaces.{key} must be present")
            elif not isinstance(interfaces.get(key), list):
                errors.append(f"{label}.interfaces.{key} must be a list")
        dataflow = module.get("dataflow")
        if not isinstance(dataflow, dict):
            errors.append(f"{label}.dataflow must be a mapping")
            dataflow = {}
        for key in required_dataflow:
            if key not in dataflow:
                errors.append(f"{label}.dataflow.{key} must be present")
            elif not isinstance(dataflow.get(key), list):
                errors.append(f"{label}.dataflow.{key} must be a list")
        if "req_ids" not in module:
            errors.append(f"{label}.req_ids must be present")
        elif not isinstance(module.get("req_ids"), list):
            errors.append(f"{label}.req_ids must be a list")
        if "design_feature_ids" not in module:
            errors.append(f"{label}.design_feature_ids must be present")
        elif not isinstance(module.get("design_feature_ids"), list):
            errors.append(f"{label}.design_feature_ids must be a list")
        verification = module.get("verification_refs")
        if not isinstance(verification, dict):
            errors.append(f"{label}.verification_refs must be a mapping")
            verification = {}
        for key in ["tests", "assertions", "coverage"]:
            if key not in verification:
                errors.append(f"{label}.verification_refs.{key} must be present")
            elif not isinstance(verification.get(key), list):
                errors.append(f"{label}.verification_refs.{key} must be a list")
        if "forbidden_responsibilities" not in module:
            errors.append(f"{label}.forbidden_responsibilities must be present")
        elif not isinstance(module.get("forbidden_responsibilities"), list):
            errors.append(f"{label}.forbidden_responsibilities must be a list")

        module_type = str(module.get("type") or "").lower()
        if module_type not in {"top", "composite", "leaf"}:
            errors.append(f"{label}.type must be one of top, composite, leaf")
        children = module.get("children")
        if children is not None and not isinstance(children, list):
            errors.append(f"{label}.children must be a list")
            children = []
        module_children[name] = [str(child).strip() for child in children or [] if str(child).strip()]
        if module_type == "leaf" and _non_empty_list(children):
            errors.append(f"{label} leaf module must not declare children")

        for ownership_key, seen in ownership.items():
            values = owns.get(ownership_key)
            if not isinstance(values, list):
                continue
            for value in values:
                owned = str(value).strip()
                if not owned:
                    continue
                previous = seen.get(owned)
                if previous and previous != name:
                    errors.append(f"{rel} {ownership_key}.{owned} owned by both {previous} and {name}")
                else:
                    seen[owned] = name

    if top_name and top_name not in module_names:
        errors.append(f"{rel} top_level.name must match a module name")
    for index, module in enumerate(modules, start=1):
        if not isinstance(module, dict):
            continue
        label = f"{rel} modules[{index}]"
        name = str(module.get("name") or "").strip()
        parent = str(module.get("parent") or "").strip()
        if name and name != top_name and parent and parent not in module_names:
            errors.append(f"{label}.parent references unknown module {parent}")
        for child in module_children.get(name, []):
            if child not in module_names:
                errors.append(f"{label}.children references unknown module {child}")


def _check_architecture_cross_file_contracts(project: Path, errors: list[str], *, require_ready: bool) -> None:
    if not require_ready:
        return
    module_plan_rel = "work/docparse/architecture/module_plan.yaml"
    module_plan = _load_structured(project / module_plan_rel)
    if module_plan is None:
        return
    modules = module_plan.get("modules")
    if not isinstance(modules, list):
        return

    module_names: set[str] = set()
    module_clocks: dict[str, str] = {}
    module_fsms: dict[str, set[str]] = {}
    for module in modules:
        if not isinstance(module, dict):
            continue
        name = str(module.get("name") or "").strip()
        if not name:
            continue
        module_names.add(name)
        module_clocks[name] = str(module.get("clock_domain") or "").strip()
        owns = module.get("owns") if isinstance(module.get("owns"), dict) else {}
        module_fsms[name] = _string_set(owns.get("fsms"))

    interface_names = _check_interface_contract_refs(project, errors, module_names)
    _check_dataflow_refs(project, errors, module_names)
    _check_state_machine_refs(project, errors, module_names, module_fsms)
    _check_timing_refs(project, errors, module_names, module_clocks, interface_names)


def _check_interface_contract_refs(project: Path, errors: list[str], module_names: set[str]) -> set[str]:
    rel = "work/docparse/architecture/interface_contracts.yaml"
    data = _load_structured(project / rel)
    interface_names: set[str] = set()
    if data is None:
        return interface_names
    interfaces = data.get("interfaces")
    if not isinstance(interfaces, list):
        return interface_names
    for index, item in enumerate(interfaces, start=1):
        label = f"{rel} interfaces[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be a mapping")
            continue
        name = str(item.get("name") or item.get("id") or "").strip()
        if not name:
            errors.append(f"{label}.name must be non-empty")
        else:
            interface_names.add(name)
        for key in ["producer_module", "consumer_module"]:
            value = str(item.get(key) or "").strip()
            if not value:
                errors.append(f"{label}.{key} must be non-empty")
            elif value not in module_names:
                errors.append(f"{label}.{key} references unknown module {value}")
        if not str(item.get("clock_domain") or "").strip():
            errors.append(f"{label}.clock_domain must be non-empty")
    return interface_names


def _check_dataflow_refs(project: Path, errors: list[str], module_names: set[str]) -> None:
    rel = "work/docparse/architecture/dataflow.yaml"
    data = _load_structured(project / rel)
    if data is None:
        return
    flows = data.get("flows")
    if not isinstance(flows, list):
        return
    for index, item in enumerate(flows, start=1):
        label = f"{rel} flows[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be a mapping")
            continue
        if not str(item.get("name") or item.get("id") or "").strip():
            errors.append(f"{label}.name must be non-empty")
        for key in ["producer_module", "consumer_module"]:
            value = str(item.get(key) or "").strip()
            if not value:
                errors.append(f"{label}.{key} must be non-empty")
            elif value not in module_names:
                errors.append(f"{label}.{key} references unknown module {value}")


def _check_state_machine_refs(
    project: Path,
    errors: list[str],
    module_names: set[str],
    module_fsms: dict[str, set[str]],
) -> None:
    rel = "work/docparse/architecture/state_machines.yaml"
    data = _load_structured(project / rel)
    if data is None:
        return
    fsms = data.get("state_machines")
    if not isinstance(fsms, list):
        return
    for index, item in enumerate(fsms, start=1):
        label = f"{rel} state_machines[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be a mapping")
            continue
        name = str(item.get("name") or item.get("id") or "").strip()
        owner = str(item.get("owning_module") or "").strip()
        if not owner:
            errors.append(f"{label}.owning_module must be non-empty")
        elif owner not in module_names:
            errors.append(f"{label}.owning_module references unknown module {owner}")
        elif name and name not in module_fsms.get(owner, set()):
            errors.append(f"{label}.name must be listed in module_plan owns.fsms for {owner}")


def _check_timing_refs(
    project: Path,
    errors: list[str],
    module_names: set[str],
    module_clocks: dict[str, str],
    interface_names: set[str],
) -> None:
    rel = "work/docparse/architecture/timing_model.yaml"
    data = _load_structured(project / rel)
    if data is None:
        return
    clock_domains = data.get("clock_domains")
    if not isinstance(clock_domains, list):
        return
    clock_names = {
        str(item.get("name") or "").strip()
        for item in clock_domains
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    }
    for module, clock in sorted(module_clocks.items()):
        if clock and clock not in clock_names:
            errors.append(f"{rel} clock_domains must cover module {module} clock_domain {clock}")
    cdc_requirements = data.get("cdc_requirements")
    if not isinstance(cdc_requirements, list):
        return
    for index, item in enumerate(cdc_requirements, start=1):
        label = f"{rel} cdc_requirements[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be a mapping")
            continue
        interface = str(item.get("interface") or "").strip()
        if not interface:
            errors.append(f"{label}.interface must be non-empty")
        elif interface not in interface_names:
            errors.append(f"{label}.interface references unknown interface {interface}")
        producer = str(item.get("producer_module") or "").strip()
        consumer = str(item.get("consumer_module") or "").strip()
        for key, value in [("producer_module", producer), ("consumer_module", consumer)]:
            if not value:
                errors.append(f"{label}.{key} must be non-empty")
            elif value not in module_names:
                errors.append(f"{label}.{key} references unknown module {value}")
        from_clock = str(item.get("from_clock_domain") or "").strip()
        to_clock = str(item.get("to_clock_domain") or "").strip()
        for key, value in [("from_clock_domain", from_clock), ("to_clock_domain", to_clock)]:
            if not value:
                errors.append(f"{label}.{key} must be non-empty")
            elif value not in clock_names:
                errors.append(f"{label}.{key} references unknown clock domain {value}")
        if from_clock and to_clock and from_clock == to_clock:
            errors.append(f"{label} must cross two different clock domains")
        if producer in module_clocks and from_clock and module_clocks[producer] != from_clock:
            errors.append(f"{label}.from_clock_domain must match {producer} clock_domain {module_clocks[producer]}")
        if consumer in module_clocks and to_clock and module_clocks[consumer] != to_clock:
            errors.append(f"{label}.to_clock_domain must match {consumer} clock_domain {module_clocks[consumer]}")


def _check_doc_projection_contract(project: Path, errors: list[str], *, require_ready: bool) -> None:
    if not require_ready:
        return
    rel = DOC_PROJECTION_REL
    data = _load_structured(project / rel)
    if data is None:
        return
    documents = data.get("documents")
    if not isinstance(documents, dict) or not documents:
        errors.append(f"{rel} documents must be a non-empty mapping")
        return
    for doc_name, spec in documents.items():
        label = f"{rel} documents.{doc_name}"
        if not isinstance(spec, dict):
            errors.append(f"{label} must be a mapping")
            continue
        if not str(spec.get("output") or "").strip():
            errors.append(f"{label}.output must be non-empty")
        sources = spec.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append(f"{label}.sources must be a non-empty list")
            continue
        seen_ids: set[str] = set()
        for index, source in enumerate(sources, start=1):
            source_label = f"{label}.sources[{index}]"
            if not isinstance(source, dict):
                errors.append(f"{source_label} must be a mapping")
                continue
            source_id = str(source.get("id") or "").strip()
            source_path = str(source.get("path") or "").strip()
            if not source_id:
                errors.append(f"{source_label}.id must be non-empty")
            elif source_id in seen_ids:
                errors.append(f"{source_label}.id duplicates {source_id}")
            seen_ids.add(source_id)
            if not source_path:
                errors.append(f"{source_label}.path must be non-empty")
            elif source.get("required", True) is not False and not (project / source_path).exists():
                errors.append(f"{source_label}.path missing required source {source_path}")


def _policy_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "yes", "1"}


def _string_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).strip() for item in value if str(item).strip()}


def _check_requirement_question_review(
    project: Path,
    errors: list[str],
    warnings: list[str],
    *,
    require_ready: bool,
) -> None:
    analysis = _load_structured(project / DOCUMENT_ANALYSIS_REL)
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
    if evidence != DOCUMENT_ANALYSIS_REL:
        errors.append(f"{DOCUMENT_ANALYSIS_REL} question_review.review_evidence must be {DOCUMENT_ANALYSIS_REL}")

    unresolved_count = review.get("unresolved_count")
    if unresolved_count not in (0, "0"):
        errors.append(f"{DOCUMENT_ANALYSIS_REL} question_review.unresolved_count must be 0 for READY")
    if unresolved:
        errors.append(
            "unresolved requirement questions must be sent to the user and closed before READY: "
            + ", ".join(unresolved[:8])
        )


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


def _non_empty_value(value: Any) -> bool:
    if value in (None, "", [], {}):
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


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


def _doc_projection_yaml(project_name: str, status: str, source_refs: list[str]) -> str:
    base_source = {
        "required": True,
        "source_refs": source_refs,
    }
    return _yaml_doc(
        {
            "schema_version": FRONTEND_VERSION,
            "project": project_name,
            "status": status,
            "owner_role": "arch",
            "source_refs": source_refs,
            "documents": {
                "application_guide": {
                    "output": "output/docs/application/application_guide.md",
                    "sources": [
                        {"id": "requirements", "path": SRS_REL, **base_source},
                        {"id": "acceptance", "path": ACCEPTANCE_REL, **base_source},
                        {"id": "interface_spec", "path": "work/docparse/structured_spec/interface_spec.yaml", **base_source},
                        {"id": "register_map", "path": "work/docparse/structured_spec/register_map.yaml", **base_source},
                    ],
                },
                "microarchitecture_spec": {
                    "output": "output/docs/design/microarchitecture_spec.md",
                    "sources": [
                        {"id": "module_plan", "path": "work/docparse/architecture/module_plan.yaml", **base_source},
                        {"id": "interface_contracts", "path": "work/docparse/architecture/interface_contracts.yaml", **base_source},
                        {"id": "dataflow", "path": "work/docparse/architecture/dataflow.yaml", **base_source},
                        {"id": "state_machines", "path": "work/docparse/architecture/state_machines.yaml", **base_source},
                        {"id": "timing_model", "path": "work/docparse/architecture/timing_model.yaml", **base_source},
                        {"id": "trace_req_to_design_intent", "path": "work/docparse/trace_matrix/req_to_design_intent.yaml", **base_source},
                    ],
                },
                "verification_plan": {
                    "output": "output/docs/test/verification_plan.md",
                    "sources": [
                        {"id": "test_intent", "path": "work/docparse/structured_spec/test_intent.yaml", **base_source},
                        {"id": "verification_plan", "path": "work/docparse/verification/verification_plan.yaml", **base_source},
                        {"id": "uvm_plan", "path": "work/docparse/verification/uvm_plan.yaml", **base_source},
                        {"id": "assertion_plan", "path": "work/docparse/verification/assertion_plan.yaml", **base_source},
                        {"id": "coverage_plan", "path": "work/docparse/verification/coverage_plan.yaml", **base_source},
                        {"id": "trace_req_to_test_intent", "path": "work/docparse/trace_matrix/req_to_test_intent.yaml", **base_source},
                        {"id": "trace_req_to_uvm_intent", "path": "work/docparse/trace_matrix/req_to_uvm_intent.yaml", **base_source},
                    ],
                },
                "delivery_package": {
                    "output": "output/docs/delivery/delivery_package.md",
                    "sources": [
                        {"id": "prototype_plan", "path": "work/docparse/prototype/prototype_plan.yaml", **base_source},
                        {"id": "review_findings", "path": "work/docparse/review/role_findings.yaml", **base_source},
                        {"id": "gate_status", "path": "work/gates/gate_status.json", "required": False},
                        {"id": "output_manifest", "path": "output/manifest.yaml", "required": False},
                    ],
                },
            },
            "assumptions": [],
        }
    )


def _trace_yaml(
    project_name: str,
    status: str,
    source_refs: list[str],
    stage: str,
    target: str,
    owner_role: str,
) -> str:
    return _yaml_doc(
        {
            "schema_version": FRONTEND_VERSION,
            "project": project_name,
            "status": status,
            "owner_role": owner_role,
            "stage": stage,
            "target": target,
            "source_refs": source_refs,
            "links": [],
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
            "- The generated verification_plan.md must carry this plan before Loop1 can be treated as planned.",
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
