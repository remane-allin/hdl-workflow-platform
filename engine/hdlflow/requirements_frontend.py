"""Structured five-role requirements front-end for the HDL workflow."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .project import require_project_instance
from .simple_yaml import load_yaml


FRONTEND_VERSION = 1
READY_STATUS = "READY"

ROLE_CONTRACTS = [
    {
        "role": "coordinator",
        "title": "Workflow Coordinator",
        "owns": "workflow state, role handoff, review collection, memory checkpoint",
        "primary_outputs": [
            "01_DocParse/review/multi_agent_review.md",
            "01_DocParse/review/role_findings.yaml",
            "01_DocParse/review/decision_log.yaml",
        ],
    },
    {
        "role": "pm",
        "title": "Product Manager",
        "owns": "requirement clarification, ambiguity removal, acceptance criteria, boundary conditions",
        "primary_outputs": [
            "00_SPEC/requirements/srs.yaml",
            "00_SPEC/requirements/srs.md",
            "00_SPEC/requirements/acceptance_criteria.yaml",
            "00_SPEC/requirements/open_questions.md",
        ],
    },
    {
        "role": "architect",
        "title": "Architect",
        "owns": "dataflow, state machines, timing model, module partition, interface contracts",
        "primary_outputs": [
            "01_DocParse/architecture/add.md",
            "01_DocParse/architecture/module_plan.yaml",
            "01_DocParse/architecture/interface_contracts.yaml",
            "01_DocParse/architecture/dataflow.yaml",
            "01_DocParse/architecture/state_machines.yaml",
            "01_DocParse/architecture/timing_model.yaml",
        ],
    },
    {
        "role": "verification_planner",
        "title": "Verification Planner",
        "owns": "module/system verification plan, assertions, coverage and UVM intent",
        "primary_outputs": [
            "01_DocParse/verification/verification_plan.yaml",
            "01_DocParse/verification/verification_plan.md",
            "01_DocParse/verification/assertion_plan.yaml",
            "01_DocParse/verification/coverage_plan.yaml",
        ],
    },
    {
        "role": "prototype_planner",
        "title": "Prototype Planner",
        "owns": "FPGA feasibility, resources, pins, clocks, resets, PS/PL prototype constraints",
        "primary_outputs": [
            "01_DocParse/prototype/prototype_plan.yaml",
            "01_DocParse/prototype/prototype_plan.md",
            "01_DocParse/prototype/clock_plan.yaml",
            "01_DocParse/prototype/pin_resource_intent.yaml",
        ],
    },
]

REQUIRED_FRONTEND_ARTIFACTS = [
    "00_SPEC/requirements/srs.yaml",
    "00_SPEC/requirements/acceptance_criteria.yaml",
    "01_DocParse/architecture/module_plan.yaml",
    "01_DocParse/architecture/interface_contracts.yaml",
    "01_DocParse/architecture/dataflow.yaml",
    "01_DocParse/architecture/state_machines.yaml",
    "01_DocParse/architecture/timing_model.yaml",
    "01_DocParse/architecture/rtl_planning_rules.yaml",
    "01_DocParse/verification/verification_plan.yaml",
    "01_DocParse/verification/assertion_plan.yaml",
    "01_DocParse/verification/coverage_plan.yaml",
    "01_DocParse/prototype/prototype_plan.yaml",
    "01_DocParse/prototype/clock_plan.yaml",
    "01_DocParse/prototype/pin_resource_intent.yaml",
    "01_DocParse/review/role_findings.yaml",
    "01_DocParse/review/decision_log.yaml",
    "01_DocParse/review/multi_agent_review.md",
    "01_DocParse/trace_matrix/req_to_arch.yaml",
    "01_DocParse/trace_matrix/req_to_rtl.yaml",
    "01_DocParse/trace_matrix/req_to_test.yaml",
    "01_DocParse/trace_matrix/req_to_proto.yaml",
]


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
    """Create the five-role front-end artifact contract for a project."""

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
        warnings.append("no source requirement files found under 00_SPEC/requirements; generated artifact source_refs are empty")

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
    """Validate the five-role artifact contract without modifying role outputs."""

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
        "00_SPEC/requirements/srs.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "pm",
                "purpose": "single shared requirement baseline for Loop1, Loop2, and Loop3",
                "stakeholders": [],
                "scope": {"in_scope": [], "out_of_scope": []},
                "functional_requirements": [],
                "non_functional_requirements": [],
                "interfaces": [],
                "boundary_conditions": [],
                "ambiguities": [],
                "assumptions": [],
                "acceptance_summary": [],
            }
        ),
        "00_SPEC/requirements/srs.md": "\n".join(
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
        "00_SPEC/requirements/acceptance_criteria.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "pm",
                "criteria": [],
                "exit_conditions": [
                    "all safety-critical ambiguities are closed or explicitly accepted",
                    "each requirement maps to architecture, verification, and prototype intent where applicable",
                ],
                "assumptions": [],
            }
        ),
        "00_SPEC/requirements/open_questions.md": _open_questions(project_name, status),
        "01_DocParse/architecture/add.md": _architecture_md(project_name, status, refs_inline),
        "01_DocParse/architecture/rtl_planning_rules.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "architect",
                "source_skill": "skills/rtl-architecture-and-gen/SKILL.md",
                "style_guide": "skills/rtl-architecture-and-gen/references/verilog-rtl-style-guide.md",
                "rtl_language": "Verilog-2001",
                "rtl_root": "05_Output/rtl",
                "directed_tb_language": "Verilog-2001",
                "directed_tb_root": "05_Output/tb",
                "uvm_language": "SystemVerilog",
                "uvm_root": "05_Output/uvm",
                "hard_rules": [
                    "hierarchy_only_top",
                    "one_primary_module_per_file",
                    "verilog_2001_rtl_only",
                    "no_systemverilog_in_rtl_or_directed_tb",
                    "official_bus_protocol_naming",
                    "three_process_fsm_when_applicable",
                    "standalone_else",
                    "explicit_final_else",
                    "explicit_cdc_plan",
                    "req_to_rtl_trace_required",
                ],
                "module_plan_requirements": [
                    "module hierarchy",
                    "clock/reset ownership",
                    "interface ownership",
                    "register block ownership",
                    "implementation order",
                ],
                "assumptions": [],
            }
        ),
        "01_DocParse/architecture/module_plan.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "architect",
                "rtl_planning_policy_ref": "01_DocParse/architecture/rtl_planning_rules.yaml",
                "modules": [],
                "top_level": {"name": "", "wrapper_policy": ""},
                "clock_reset": [],
                "dependencies": [],
                "loop_consumers": ["Loop1 RTL/TB", "Loop2 UVM", "Loop3 FPGA Prototype"],
                "assumptions": [],
            }
        ),
        "01_DocParse/architecture/interface_contracts.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "architect",
                "interfaces": [],
                "ports": [],
                "protocols": [],
                "latency_contracts": [],
                "assumptions": [],
            }
        ),
        "01_DocParse/architecture/dataflow.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "architect",
                "flows": [],
                "control_paths": [],
                "datapaths": [],
                "backpressure": [],
                "assumptions": [],
            }
        ),
        "01_DocParse/architecture/state_machines.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "architect",
                "rtl_planning_policy_ref": "01_DocParse/architecture/rtl_planning_rules.yaml",
                "fsm_style_policy": [
                    "three_process_fsm_when_applicable",
                    "separate_state_next_and_datapath_control",
                    "illegal_state_default_recovery",
                ],
                "state_machines": [],
                "reset_states": [],
                "illegal_states": [],
                "transition_requirements": [],
                "assumptions": [],
            }
        ),
        "01_DocParse/architecture/timing_model.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "architect",
                "clock_domains": [],
                "resets": [],
                "latency_requirements": [],
                "cdc_requirements": [],
                "timing_constraints": [],
                "assumptions": [],
            }
        ),
        "01_DocParse/verification/verification_plan.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "verification_planner",
                "module_level": [],
                "system_level": [],
                "scoreboards": [],
                "reference_models": [],
                "negative_tests": [],
                "loop_consumers": ["Loop1 RTL/TB", "Loop2 UVM"],
                "assumptions": [],
            }
        ),
        "01_DocParse/verification/verification_plan.md": _verification_md(project_name, status, refs_inline),
        "01_DocParse/verification/assertion_plan.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "verification_planner",
                "assertions": [],
                "bind_targets": [],
                "disabled_conditions": [],
                "severity_policy": [],
                "assumptions": [],
            }
        ),
        "01_DocParse/verification/coverage_plan.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "verification_planner",
                "functional_coverage": [],
                "code_coverage_targets": [],
                "cross_coverage": [],
                "illegal_bins": [],
                "closure_thresholds": [],
                "assumptions": [],
            }
        ),
        "01_DocParse/prototype/prototype_plan.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "prototype_planner",
                "prototype_mode": "",
                "board": "",
                "resource_estimate": [],
                "ps_pl_boundary": [],
                "risk_items": [],
                "loop_consumers": ["Loop3 FPGA Prototype"],
                "assumptions": [],
            }
        ),
        "01_DocParse/prototype/prototype_plan.md": _prototype_md(project_name, status, refs_inline),
        "01_DocParse/prototype/clock_plan.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "prototype_planner",
                "clocks": [],
                "resets": [],
                "generated_clocks": [],
                "clock_groups": [],
                "assumptions": [],
            }
        ),
        "01_DocParse/prototype/pin_resource_intent.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "prototype_planner",
                "external_ports": [],
                "pin_intent": [],
                "mio_ownership": [],
                "board_resources": [],
                "assumptions": [],
            }
        ),
        "01_DocParse/review/role_findings.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "coordinator",
                "roles": {
                    item["role"]: {
                        "status": status,
                        "findings": [],
                        "blockers": [],
                        "confidence": "medium",
                    }
                    for item in ROLE_CONTRACTS
                },
                "cross_role_conflicts": [],
                "assumptions": [],
            }
        ),
        "01_DocParse/review/decision_log.yaml": _yaml_doc(
            {
                **base,
                "owner_role": "coordinator",
                "decisions": [],
                "rejected_alternatives": [],
                "handoff": {
                    "loop1": "architecture/module_plan.yaml + verification/verification_plan.yaml",
                    "loop2": "architecture/* + verification/*",
                    "loop3": "architecture/* + prototype/*",
                },
                "assumptions": [],
            }
        ),
        "01_DocParse/review/multi_agent_review.md": _review_md(project_name, status, refs_yaml),
        "01_DocParse/trace_matrix/req_to_arch.yaml": _trace_yaml(project_name, status, source_refs, "architecture"),
        "01_DocParse/trace_matrix/req_to_rtl.yaml": _trace_yaml(project_name, status, source_refs, "rtl"),
        "01_DocParse/trace_matrix/req_to_test.yaml": _trace_yaml(project_name, status, source_refs, "test"),
        "01_DocParse/trace_matrix/req_to_proto.yaml": _trace_yaml(project_name, status, source_refs, "prototype"),
    }


def _requirement_source_refs(project: Path) -> list[str]:
    root = project / "00_SPEC" / "requirements"
    if not root.is_dir():
        return []
    ignored = {
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
    required_by_name = {
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


def _check_role_findings(project: Path, errors: list[str], warnings: list[str], *, require_ready: bool) -> None:
    data = _load_structured(project / "01_DocParse/review/role_findings.yaml")
    if data is None:
        return
    roles = data.get("roles")
    if not isinstance(roles, dict):
        errors.append("01_DocParse/review/role_findings.yaml roles must be a mapping")
        return
    seen = {str(role) for role in roles}
    required = {item["role"] for item in ROLE_CONTRACTS}
    missing = sorted(required - seen)
    if missing:
        errors.append("01_DocParse/review/role_findings.yaml missing role(s): " + ", ".join(missing))
    blockers = []
    for role, item in roles.items():
        if not isinstance(item, dict):
            continue
        if require_ready and str(item.get("status") or "").upper() != READY_STATUS:
            errors.append(f"01_DocParse/review/role_findings.yaml role {role} status must be {READY_STATUS}")
        if require_ready and not _non_empty_list(item.get("findings")):
            errors.append(f"01_DocParse/review/role_findings.yaml role {role} findings must be non-empty for READY")
        raw_blockers = item.get("blockers")
        if isinstance(raw_blockers, list) and raw_blockers:
            blockers.append(str(role))
    if blockers:
        message = "role finding blocker list is non-empty for: " + ", ".join(blockers)
        if require_ready:
            errors.append(message)
        else:
            warnings.append(message)


def _check_decision_log(project: Path, errors: list[str], warnings: list[str], *, require_ready: bool) -> None:
    data = _load_structured(project / "01_DocParse/review/decision_log.yaml")
    if data is None:
        return
    if require_ready and not _non_empty_list(data.get("decisions")):
        errors.append("01_DocParse/review/decision_log.yaml decisions must be non-empty for READY")
    handoff = data.get("handoff")
    if not isinstance(handoff, dict):
        errors.append("01_DocParse/review/decision_log.yaml handoff must be a mapping")
        return
    for loop_name in ["loop1", "loop2", "loop3"]:
        if not handoff.get(loop_name):
            warnings.append(f"decision log handoff for {loop_name} is empty")


def _check_cross_loop_trace(project: Path, errors: list[str], *, require_ready: bool) -> None:
    for rel in [
        "01_DocParse/trace_matrix/req_to_arch.yaml",
        "01_DocParse/trace_matrix/req_to_rtl.yaml",
        "01_DocParse/trace_matrix/req_to_test.yaml",
        "01_DocParse/trace_matrix/req_to_proto.yaml",
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
    rules_rel = "01_DocParse/architecture/rtl_planning_rules.yaml"
    rules = _load_structured(project / rules_rel)
    if rules is None:
        return

    expected_scalars = {
        "source_skill": "skills/rtl-architecture-and-gen/SKILL.md",
        "style_guide": "skills/rtl-architecture-and-gen/references/verilog-rtl-style-guide.md",
        "rtl_language": "Verilog-2001",
        "rtl_root": "05_Output/rtl",
        "directed_tb_language": "Verilog-2001",
        "directed_tb_root": "05_Output/tb",
        "uvm_language": "SystemVerilog",
        "uvm_root": "05_Output/uvm",
    }
    for key, expected in expected_scalars.items():
        if str(rules.get(key) or "") != expected:
            errors.append(f"{rules_rel} {key} must be {expected}")

    required_rules = {
        "hierarchy_only_top",
        "one_primary_module_per_file",
        "verilog_2001_rtl_only",
        "no_systemverilog_in_rtl_or_directed_tb",
        "official_bus_protocol_naming",
        "three_process_fsm_when_applicable",
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

    module_plan_rel = "01_DocParse/architecture/module_plan.yaml"
    module_plan = _load_structured(project / module_plan_rel)
    if module_plan is not None:
        if module_plan.get("rtl_planning_policy_ref") != rules_rel:
            errors.append(f"{module_plan_rel} rtl_planning_policy_ref must point to {rules_rel}")
        wrapper_policy = str((module_plan.get("top_level") or {}).get("wrapper_policy") or "").lower()
        if require_ready and ("hierarchy" not in wrapper_policy or "only" not in wrapper_policy):
            errors.append(f"{module_plan_rel} top_level.wrapper_policy must require a hierarchy-only top")

    state_machines_rel = "01_DocParse/architecture/state_machines.yaml"
    state_machines = _load_structured(project / state_machines_rel)
    if state_machines is not None:
        if state_machines.get("rtl_planning_policy_ref") != rules_rel:
            errors.append(f"{state_machines_rel} rtl_planning_policy_ref must point to {rules_rel}")
        style_policy = {str(item) for item in state_machines.get("fsm_style_policy", []) if str(item)}
        if require_ready and "three_process_fsm_when_applicable" not in style_policy:
            errors.append(f"{state_machines_rel} fsm_style_policy must include three_process_fsm_when_applicable")

    if not require_ready and not missing:
        warnings.append(f"{rules_rel} will be enforced when requirements front door is READY")


def _non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


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
    report_dir = project / "05_Output" / "reports" / "docparse"
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
            "owner_role": "coordinator",
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
            "",
            "| ID | Owner Role | Question | Blocking Loop | Resolution |",
            "| --- | --- | --- | --- | --- |",
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
            "- rtl_skill: skills/rtl-architecture-and-gen/SKILL.md",
            "- rtl_style_guide: skills/rtl-architecture-and-gen/references/verilog-rtl-style-guide.md",
            "",
            "## RTL Planning Rules",
            "",
            "- Architecture planning must consume `01_DocParse/architecture/rtl_planning_rules.yaml` before Loop1 RTL generation.",
            "- Top-level RTL must be hierarchy-only; behavior belongs in owned submodules.",
            "- RTL and directed TB are Verilog-2001 `.v` only; SystemVerilog is reserved for UVM.",
            "- Official bus/protocol/IP signal names must match vendor UG/IP naming; do not append `_i`/`_o` at official boundaries.",
            "- Non-trivial FSMs must plan separate state, next-state, and datapath/control ownership.",
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
            "- Loop1 consumes module plan and interface contracts.",
            "- Loop2 consumes architecture plus verification plans.",
            "- Loop3 consumes architecture plus prototype plans.",
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
            "## Cross-Role Conflicts",
            "",
            "## Coordinator Handoff",
            "",
        ]
    )


def _find_workspace_root(path: Path) -> Path:
    for candidate in [path, *path.parents]:
        if (candidate / "config" / "global" / "workspace_config.yaml").exists():
            return candidate
    if path.parent.name == "projects":
        return path.parent.parent
    raise FileNotFoundError(f"could not find workspace config from: {path}")
