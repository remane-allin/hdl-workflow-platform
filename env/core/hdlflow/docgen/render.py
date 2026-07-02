"""Markdown rendering for HDL document snapshots."""

from __future__ import annotations

from typing import Any

from .constants import DOCS_BY_TYPE, DocDefinition


_METADATA_KEYS = {"schema_version", "project", "status", "generated_at", "source_refs", "owner_role"}


def render_document(snapshot: dict[str, Any]) -> str:
    definition = DOCS_BY_TYPE[str(snapshot["doc_type"])]
    data = snapshot.get("data", {})
    header = _front_matter(definition, snapshot)
    if definition.doc_type == "application_guide":
        body = _application_doc(definition, snapshot, data)
    elif definition.doc_type == "microarchitecture_specification":
        body = _uarch_doc(definition, snapshot, data)
    elif definition.doc_type == "verification_plan":
        body = _verification_doc(definition, snapshot, data)
    elif definition.doc_type == "delivery_package":
        body = _delivery_doc(definition, snapshot, data)
    else:
        raise ValueError(f"unsupported doc type: {definition.doc_type}")
    return header + "\n" + body.rstrip() + "\n"


def _front_matter(definition: DocDefinition, snapshot: dict[str, Any]) -> str:
    review_agents = ", ".join(definition.review_agents)
    return "\n".join(
        [
            "---",
            f"doc_type: {definition.doc_type}",
            f"project: {snapshot['project']}",
            f"ip_name: {snapshot['ip_name']}",
            f"version: {snapshot['version']}",
            f"status: {snapshot['status']}",
            f"generated_at: {snapshot['generated_at']}",
            f"generator: hdlflow.docgen.{definition.doc_type}",
            f"source_manifest: {definition.manifest_rel}",
            f"owner_agent: {definition.owner_agent}",
            f"review_agents: [{review_agents}]",
            f"change_id: {_value(snapshot.get('change_id'))}",
            "---",
            "",
        ]
    )


def _application_doc(definition: DocDefinition, snapshot: dict[str, Any], data: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {snapshot['ip_name']} Application Guide",
            "",
            f"<!-- {definition.marker_start} -->",
            "",
            "## 0. Document Status",
            _status_table(definition, snapshot),
            "## 1. Black Box View",
            _paragraph(_first(data.get("requirements"), "purpose", "objective", "goal", "description")),
            "## 2. User Visible Features",
            _requirements_table(data.get("requirements")),
            "## 3. Integration View",
            _interfaces_table(data),
            "## 4. Interfaces",
            _ports_table(data),
            "## 5. Clocks and Resets",
            _generic_yaml_table(data.get("interface_timing") or data.get("timing_rules")),
            "## 6. Register / Config",
            _register_table(data.get("register_map")),
            "## 7. Operation Sequence",
            _operation_sequence_table(data),
            "## 8. Acceptance Criteria",
            _items_table(_list_from(data.get("acceptance"), "criteria", "acceptance_criteria"), ("Criteria", "Evidence")),
            "## 9. Active Requirement Baseline",
            _active_requirements_table(data),
            f"<!-- {definition.marker_end} -->",
        ]
    )


def _uarch_doc(definition: DocDefinition, snapshot: dict[str, Any], data: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {snapshot['ip_name']} Microarchitecture Specification",
            "",
            f"<!-- {definition.marker_start} -->",
            "",
            "## 0. Document Status",
            _status_table(definition, snapshot),
            "## 1. Design Overview",
            _design_overview(data),
            "## 2. Requirement-to-Architecture Summary",
            _design_routing_table(data.get("design_routing")),
            "## 3. Functional Domain Model",
            _functional_domain_table(data.get("functional_domain_model")),
            "## 4. Module Ownership Matrix",
            _module_ownership_table(data.get("module_ownership_matrix")),
            "## 5. Logic Level Design",
            _lld_contract_table(data.get("module_plan")),
            "## 6. Implementation Order / Granularity",
            _implementation_order_table(data.get("module_plan")),
            "## 7. Storage / FIFO / Counter Plan",
            _storage_counter_table(data.get("module_plan")),
            "## 8. State Machines",
            _state_machine_table(data.get("state_machines")),
            "## 9. Module Topology",
            _modules_table(data.get("module_plan"), data.get("rtl_modules")),
            "## 10. Interfaces",
            _interfaces_table(data),
            "## 11. Interface Contract",
            _interface_contract_table(data.get("interface_contract")),
            "## 12. Clocks and Resets",
            _generic_yaml_table(data.get("timing_model") or data.get("timing_rules")),
            "## 13. Dataflow",
            _generic_yaml_table(data.get("dataflow")),
            "## 14. State / Registers",
            _register_table(data.get("register_map")),
            "## 15. Operation Model Hooks",
            _operation_model_table(data.get("operation_model")),
            f"<!-- {definition.marker_end} -->",
        ]
    )


def _verification_doc(definition: DocDefinition, snapshot: dict[str, Any], data: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {snapshot['ip_name']} Verification Plan",
            "",
            f"<!-- {definition.marker_start} -->",
            "",
            "## 0. Document Status",
            _status_table(definition, snapshot),
            "## 1. Verification Goals",
            _verification_goals_table(data.get("verification_plan")),
            "## 2. Operation Model",
            _operation_model_table(data.get("operation_model")),
            "## 3. Directed TB Obligations",
            _tb_obligation_table(data.get("tb_obligations")),
            "## 4. VCD Semantic Windows",
            _wave_semantic_table(data.get("wave_semantic_manifest")),
            "## 5. Test Matrix",
            _verification_test_matrix(data.get("verification_plan")),
            "## 6. Coverage",
            _generic_yaml_table(data.get("coverage_plan")),
            "## 7. Assertions",
            _generic_yaml_table(data.get("assertion_plan")),
            "## 8. Waveform Secondary Check Plan",
            _waveform_table(data),
            "## 9. Directed TB Log / Waveform Artifact Contract",
            _directed_tb_contract_table(data.get("verification_plan")),
            "## 10. UVM Environment Plan",
            _uvm_environment_table(data.get("uvm_plan")),
            "## 11. UVM Tests / Scoreboards / Coverage",
            _uvm_tests_table(data.get("uvm_plan"), data.get("trace_req_to_uvm_intent")),
            "## 12. UVM Multi-Scenario Obligations",
            _uvm_obligation_table(data.get("uvm_obligations")),
            "## 13. FPGA Validation Matrix",
            _fpga_matrix_table(data.get("fpga_validation_matrix")),
            "## 14. Exit Criteria",
            _items_table(_list_from(data.get("acceptance"), "criteria", "acceptance_criteria"), ("Criteria", "Evidence")),
            f"<!-- {definition.marker_end} -->",
        ]
    )


def _delivery_doc(definition: DocDefinition, snapshot: dict[str, Any], data: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {snapshot['ip_name']} Delivery Package",
            "",
            f"<!-- {definition.marker_start} -->",
            "",
            "## 0. Delivery Status",
            _status_table(definition, snapshot),
            "## 1. Release Decision",
            _release_table(data),
            "## 2. Delivered Document Set",
            _delivered_docs_table(),
            "## 3. Delivered Engineering Artifacts",
            _artifact_table(data),
            "## 4. Gate Status Summary",
            _generic_yaml_table(data.get("gate_status")),
            "## 5. Semantic Gate Status",
            _semantic_gate_status_table(data.get("semantic_gate_status")),
            "## 6. Release State",
            _release_state_table(data.get("release_state")),
            "## 7. Verification Evidence",
            _verification_evidence_table(data),
            "## 8. Prototype / Board Validation Plan",
            _prototype_validation_table(data.get("prototype_plan")),
            "## 9. FPGA Validation Matrix",
            _fpga_matrix_table(data.get("fpga_validation_matrix")),
            "## 10. Change Control Summary",
            _generic_yaml_table(data.get("output_manifest")),
            "## 11. Signoff Checklist",
            _signoff_table(),
            f"<!-- {definition.marker_end} -->",
        ]
    )


def _status_table(definition: DocDefinition, snapshot: dict[str, Any]) -> str:
    return _table(
        ("Item", "Value"),
        [
            ("Project", snapshot["project"]),
            ("IP / Module", snapshot["ip_name"]),
            ("Status", snapshot["status"]),
            ("Owner Agent", definition.owner_agent),
            ("Review Agents", ", ".join(definition.review_agents)),
            ("Generated At", snapshot["generated_at"]),
            ("Change ID", _value(snapshot.get("change_id"))),
        ],
    )


def _design_overview(data: dict[str, Any]) -> str:
    module_plan = data.get("module_plan")
    if isinstance(module_plan, dict):
        for key in ("description", "purpose", "summary"):
            value = module_plan.get(key)
            if value not in (None, "", [], {}):
                return _paragraph(_compact(value))
        top_level = module_plan.get("top_level")
        if isinstance(top_level, dict):
            overview = _first_present(top_level, "wrapper_policy", "file", default="")
            if overview:
                return _paragraph(overview)
        policy = module_plan.get("module_partition_policy")
        if isinstance(policy, dict) and policy:
            return _paragraph("Module partition policy: " + _compact(policy))
    return _paragraph(_first(data.get("requirements"), "purpose", "objective", "goal", "description"))


def _active_requirements_table(data: dict[str, Any]) -> str:
    rows = []
    for item in _list_from(data.get("active_requirements"), "requirements"):
        if isinstance(item, dict):
            rows.append(
                (
                    _first_present(item, "requirement_id", default="requirement"),
                    _first_present(item, "functional_domain", default="unassigned"),
                    _first_present(item, "title", "full_text", default="requirement text not recorded"),
                    _first_present(item, "lifecycle_state", "status", default="state not recorded"),
                )
            )
    return _table(
        ("Requirement", "Domain", "Title / Text", "Lifecycle"),
        rows or [("no active requirement", "not recorded", "not recorded", "not recorded")],
    )


def _functional_domain_table(model: Any) -> str:
    rows = []
    for item in _named_list(model, "domains"):
        if isinstance(item, dict):
            rows.append(
                (
                    _first_present(item, "domain", "name", default="domain"),
                    _first_present(item, "requirement_ids", default="requirements not recorded"),
                    _first_present(item, "owner_modules", default="modules not recorded"),
                    _first_present(item, "primary_interfaces", default="interfaces not recorded"),
                    _first_present(item, "verification_focus", default="verification focus not recorded"),
                )
            )
    return _table(
        ("Domain", "Requirements", "Owner Modules", "Interfaces", "Verification Focus"),
        rows or [("no domain", "not recorded", "not recorded", "not recorded", "not recorded")],
    )


def _design_routing_table(routing: Any) -> str:
    rows = []
    for item in _named_list(routing, "routes"):
        if isinstance(item, dict):
            rows.append(
                (
                    _first_present(item, "requirement_id", default="requirement"),
                    _first_present(item, "functional_domain", default="domain not recorded"),
                    _first_present(item, "design_doc_sections", default="sections not recorded"),
                    _first_present(item, "affected_modules", default="modules not recorded"),
                    _first_present(item, "verification_hooks", default="hooks not recorded"),
                )
            )
    return _table(
        ("Requirement", "Domain", "Design Sections", "Affected Modules", "Verification Hooks"),
        rows or [("no route", "not recorded", "not recorded", "not recorded", "not recorded")],
    )


def _module_ownership_table(matrix: Any) -> str:
    rows = []
    for item in _named_list(matrix, "owners"):
        if isinstance(item, dict):
            rows.append(
                (
                    _first_present(item, "requirement_id", default="requirement"),
                    _first_present(item, "functional_domain", default="domain not recorded"),
                    _first_present(item, "rtl_owner_module", default="rtl owner not recorded"),
                    _first_present(item, "interface_owner", default="interface owner not recorded"),
                    _first_present(item, "verification_owner", default="verification owner not recorded"),
                )
            )
    return _table(
        ("Requirement", "Domain", "RTL Owner", "Interface Owner", "Verification Owner"),
        rows or [("no owner", "not recorded", "not recorded", "not recorded", "not recorded")],
    )


def _interface_contract_table(contract: Any) -> str:
    rows = []
    for item in _named_list(contract, "interfaces"):
        if isinstance(item, dict):
            rows.append(
                (
                    _first_present(item, "name", "interface_name", default="interface"),
                    _first_present(item, "protocol", default="protocol not recorded"),
                    _first_present(item, "top_module", default="top module not recorded"),
                    _first_present(item, "ports", default="ports not recorded"),
                    _first_present(item, "observability", default="observability not recorded"),
                )
            )
    return _table(
        ("Interface", "Protocol", "Top Module", "Ports", "Observability"),
        rows or [("no interface", "not recorded", "not recorded", "not recorded", "not recorded")],
    )


def _operation_model_table(model: Any) -> str:
    rows = []
    for item in _named_list(model, "operations"):
        if isinstance(item, dict):
            rows.append(
                (
                    _first_present(item, "operation_id", default="operation"),
                    _first_present(item, "requirement_ids", default="requirements not recorded"),
                    _first_present(item, "operation_type", default="type not recorded"),
                    _first_present(item, "interface_name", default="interface not recorded"),
                    _first_present(item, "expected_response", default="expected response not recorded"),
                    _first_present(item, "coverage_bins", default="coverage bins not recorded"),
                )
            )
    return _table(
        ("Operation", "Requirements", "Type", "Interface", "Expected Response", "Coverage Bins"),
        rows or [("no operation", "not recorded", "not recorded", "not recorded", "not recorded", "not recorded")],
    )


def _tb_obligation_table(obligations: Any) -> str:
    rows = []
    for item in _named_list(obligations, "obligations"):
        if isinstance(item, dict):
            rows.append(
                (
                    _first_present(item, "test_id", default="test"),
                    _first_present(item, "requirement_id", default="requirement"),
                    _first_present(item, "operation_id", default="operation"),
                    _first_present(item, "observed_interface", default="interface not recorded"),
                    _first_present(item, "evidence_type", default="evidence type not recorded"),
                    _first_present(item, "status", default="status not recorded"),
                )
            )
    return _table(
        ("TB Test", "Requirement", "Operation", "Observed Interface", "Evidence Type", "Status"),
        rows or [("no TB obligation", "not recorded", "not recorded", "not recorded", "not recorded", "not recorded")],
    )


def _wave_semantic_table(manifest: Any) -> str:
    rows = []
    for item in _named_list(manifest, "windows"):
        if isinstance(item, dict):
            rows.append(
                (
                    _first_present(item, "window_id", default="window"),
                    _first_present(item, "operation_id", default="operation"),
                    _first_present(item, "interface_name", default="interface not recorded"),
                    _first_present(item, "decoder", default="decoder not recorded"),
                    _first_present(item, "evidence_level", default="evidence level not recorded"),
                    _first_present(item, "expected_events", default="expected events not recorded"),
                )
            )
    return _table(
        ("Window", "Operation", "Interface", "Decoder", "Evidence Level", "Expected Events"),
        rows or [("no semantic window", "not recorded", "not recorded", "not recorded", "not recorded", "not recorded")],
    )


def _uvm_obligation_table(obligations: Any) -> str:
    rows = []
    for item in _named_list(obligations, "obligations"):
        if isinstance(item, dict):
            rows.append(
                (
                    _first_present(item, "sequence_id", default="sequence"),
                    _first_present(item, "operation_id", default="operation"),
                    _first_present(item, "coverage_bins", default="coverage bins not recorded"),
                    _first_present(item, "scoreboard_model", default="scoreboard not recorded"),
                    _first_present(item, "assertions", default="assertions not recorded"),
                    _first_present(item, "status", default="status not recorded"),
                )
            )
    return _table(
        ("Sequence", "Operation", "Coverage Bins", "Scoreboard", "Assertions", "Status"),
        rows or [("no UVM obligation", "not recorded", "not recorded", "not recorded", "not recorded", "not recorded")],
    )


def _fpga_matrix_table(matrix: Any) -> str:
    rows = []
    for item in _named_list(matrix, "tests"):
        if isinstance(item, dict):
            rows.append(
                (
                    _first_present(item, "test_id", default="test"),
                    _first_present(item, "requirement_id", default="requirement"),
                    _first_present(item, "validation_mode", default="mode not recorded"),
                    _first_present(item, "claim_level", default="claim level not recorded"),
                    _first_present(item, "evidence_level", default="evidence level not recorded"),
                    _first_present(item, "status", default="status not recorded"),
                )
            )
    return _table(
        ("FPGA Test", "Requirement", "Mode", "Claim Level", "Evidence Level", "Status"),
        rows or [("no FPGA validation", "not recorded", "not recorded", "not recorded", "not recorded", "not recorded")],
    )


def _semantic_gate_status_table(status: Any) -> str:
    rows = []
    for item in _named_list(status, "gates"):
        if isinstance(item, dict):
            rows.append(
                (
                    _first_present(item, "name", default="gate"),
                    _first_present(item, "mode", default="mode not recorded"),
                    _first_present(item, "status", default="status not recorded"),
                    _first_present(item, "issue_count", default="0"),
                )
            )
    if isinstance(status, dict) and not rows and status:
        return _generic_yaml_table(status)
    return _table(("Gate", "Mode", "Status", "Issue Count"), rows or [("no semantic gate", "not recorded", "not recorded", "not recorded")])


def _release_state_table(state: Any) -> str:
    if not isinstance(state, dict):
        return _table(("Field", "Value"), [("release_state", "not recorded")])
    return _table(
        ("Field", "Value"),
        [
            ("state", state.get("state", "not recorded")),
            ("ok", state.get("ok", "not recorded")),
            ("blockers", _compact(state.get("blockers", []))),
            ("warnings", _compact(state.get("warnings", []))),
        ],
    )


def _operation_sequence_table(data: dict[str, Any]) -> str:
    rows = []
    for item in _named_list(data.get("operation_model"), "operations"):
        if isinstance(item, dict):
            rows.append(
                (
                    _first_present(item, "operation_id", default="operation"),
                    _first_present(item, "expected_response", "readback_rule", default="operation evidence not recorded"),
                )
            )
    for item in _list_from(data.get("test_intent"), "operation_sequence", "scenarios", "tests"):
        if isinstance(item, dict):
            rows.append(
                (
                    _first_present(item, "id", "name", "title", "description", default="operation_step"),
                    _first_present(item, "expected", "result", "evidence", "description", default="covered by operation intent"),
                )
            )
        else:
            rows.append((_compact(item), "covered by operation intent"))
    if not rows:
        for item in _named_list(data.get("register_map"), "opcodes"):
            step = _first_present(item, "opcode", default="opcode") + " " + _first_present(item, "name", default="command")
            rows.append((step, _first_present(item, "description", "behavior", default="execute documented command behavior")))
    if not rows:
        for item in _list_from(data.get("verification_plan"), "scenario_tests", "system_level"):
            rows.append((_compact(item), "covered by verification scenario"))
    return _table(("Step", "Expected Result"), rows or [("no operation step", "not recorded")])


def _interfaces_table(data: dict[str, Any]) -> str:
    rows = []
    for root in (data.get("interface_spec"), data.get("interface_contracts"), data.get("interface_contract")):
        for item in _named_list(root, "interfaces"):
            protocol = _first_present(item, "type", "protocol", default="interface_contract")
            description = _first_present(item, "description", "summary", "contract", "signals", "pins", default="defined by source interface")
            rows.append((_first_present(item, "name", default="unnamed_interface"), protocol, description))
    return _table(("Interface", "Type / Protocol", "Description"), rows or [("no interface", "not recorded", "no interface data supplied")])


def _ports_table(data: dict[str, Any]) -> str:
    rows = []
    for root, owner in (
        (data.get("interface_spec"), "interface_spec"),
        (data.get("interface_contracts"), "interface_contracts"),
        (data.get("interface_contract"), "semantic_interface_contract"),
    ):
        for port in _named_list(root, "ports"):
            rows.append(
                (
                    _first_present(port, "name", default="unnamed_port"),
                    _first_present(port, "direction", default="direction not specified"),
                    _first_present(port, "width", default="width not specified"),
                    owner,
                )
            )
    for module in data.get("rtl_modules") or []:
        for port in module.get("ports") or []:
            rows.append(
                (
                    _first_present(port, "name", default="unnamed_port"),
                    _first_present(port, "direction", default="direction not specified"),
                    _first_present(port, "width", default="width not specified"),
                    module.get("module", "rtl_module"),
                )
            )
    return _table(("Port", "Direction", "Width", "Owner"), rows or [("no port", "not recorded", "not recorded", "no source")])


def _register_table(register_map: Any) -> str:
    rows = []
    for item in _named_list(register_map, "registers"):
        rows.append(
            (
                _first_present(item, "offset", default="address assigned by opcode map"),
                _first_present(item, "name", default="unnamed_register"),
                _first_present(item, "access", "width", default="access not specified"),
                _first_present(item, "reset", default="reset not specified in current source"),
                _first_present(item, "description", "fields", default="register fields not specified"),
            )
        )
    for item in _named_list(register_map, "opcodes"):
        rows.append(
            (
                _first_present(item, "opcode", default="opcode not specified"),
                _first_present(item, "name", default="unnamed_command"),
                "command",
                "not applicable: opcode row",
                _first_present(item, "description", "behavior", default="command behavior defined by opcode name"),
            )
        )
    for item in _named_list(register_map, "commands"):
        rows.append(("not applicable: command note", _compact(item), "command note", "not applicable: command note", "source note"))
    return _table(("Offset / Opcode", "Register / Command", "Access / Width", "Reset", "Description"), rows or [("no map", "not recorded", "not recorded", "not recorded", "no register map supplied")])


def _modules_table(module_plan: Any, rtl_modules: Any) -> str:
    rows = []
    if isinstance(module_plan, dict):
        top_level = module_plan.get("top_level")
        if isinstance(top_level, dict):
            rows.append(
                (
                    _first_present(top_level, "name", default="top_level"),
                    "top integration",
                    _first_present(top_level, "wrapper_policy", "file", default="top-level module"),
                )
            )
        policy = module_plan.get("module_partition_policy")
        if isinstance(policy, dict):
            rows.append(("module_partition_policy", "planning policy", _compact(policy)))
        for item in _named_list(module_plan, "clock_reset"):
            rows.append(
                (
                    _first_present(item, "name", default="clock_reset_item"),
                    "clock/reset",
                    _first_present(item, "owns", "file", default="clock/reset responsibility"),
                )
            )
        for item in _named_list(module_plan, "modules"):
            role = _first_present(item, "role", "responsibility", "layer", default="module responsibility")
            description = _first_present(item, "description", "children", "dependencies", "file", default="source-defined module")
            rows.append((_first_present(item, "name", default="unnamed_module"), role, description))
    for item in rtl_modules or []:
        rows.append((item.get("module", "rtl_module"), "RTL source", item.get("path", "path not recorded")))
    return _table(("Module", "Role", "Description / Source"), rows or [("no module", "not recorded", "no module data supplied")])


def _lld_contract_table(module_plan: Any) -> str:
    rows = []
    for item in _named_list(module_plan, "modules"):
        if not isinstance(item, dict):
            continue
        logic = item.get("logic") if isinstance(item.get("logic"), dict) else {}
        behavior_parts = []
        for key in ("combinational", "sequential", "edge_cases"):
            value = logic.get(key)
            if value not in (None, "", [], {}):
                behavior_parts.append(f"{key}: {_compact(value)}")
        if not behavior_parts:
            behavior_parts.append(_first_present(item, "responsibility", "role", default="module behavior described by responsibility"))
        verification = item.get("verification_refs") if isinstance(item.get("verification_refs"), dict) else {}
        rows.append(
            (
                _first_present(item, "name", default="unnamed_module"),
                _first_present(item, "clock_domain", default="clock not specified") + " / " + _first_present(item, "reset_domain", default="reset not specified"),
                _ownership_summary(item.get("owns")),
                _first_present(item, "internal_subblocks", "subblocks", default="none"),
                " ; ".join(behavior_parts),
                _compact(verification),
            )
        )
    return _table(
        ("Module", "Clock / Reset", "Owned State", "Internal Subblocks", "Coding Behavior", "Verification Hooks"),
        rows or [("no module", "not recorded", "not recorded", "not recorded", "not recorded", "not recorded")],
    )


def _implementation_order_table(module_plan: Any) -> str:
    rows = []
    modules_by_name = {}
    if isinstance(module_plan, dict):
        for item in _named_list(module_plan, "modules"):
            if isinstance(item, dict):
                name = _first_present(item, "name", default="")
                if name:
                    modules_by_name[name] = item
        for index, item in enumerate(_list_from(module_plan, "implementation_order"), start=1):
            name = _compact(item)
            module = modules_by_name.get(name, {})
            detail = _first_present(module, "file", "source_file", "responsibility", default="implementation order item")
            rows.append((str(index), name, detail))
        policy = module_plan.get("module_granularity_policy")
        if isinstance(policy, dict):
            for key in ("planning_order", "file_boundary_rule", "split_when", "keep_inside_parent_when", "naming_rule"):
                value = policy.get(key)
                if value not in (None, "", [], {}):
                    rows.append(("policy", key, _compact(value)))
        for helper in _named_list(module_plan, "prototype_helpers"):
            if isinstance(helper, dict):
                rows.append(
                    (
                        "prototype_helper",
                        _first_present(helper, "name", default="helper"),
                        _first_present(helper, "role", "file", default="prototype helper"),
                    )
                )
    return _table(
        ("Order", "Item", "Detail"),
        rows or [("no order", "not recorded", "implementation order not supplied")],
    )


def _ownership_summary(owns: Any) -> str:
    if not isinstance(owns, dict):
        return "ownership not specified"
    rows = []
    for key in ("registers", "register_fields", "fsms", "fifos", "memories", "counters", "arbiters", "error_flags"):
        value = owns.get(key)
        rows.append(f"{key}={_compact(value) if value not in (None, [], {}) else 'none'}")
    return "; ".join(rows)


def _storage_counter_table(module_plan: Any) -> str:
    rows = []
    for item in _named_list(module_plan, "modules"):
        if not isinstance(item, dict):
            continue
        owns = item.get("owns") if isinstance(item.get("owns"), dict) else {}
        storage = []
        for key in ("registers", "register_fields", "fifos", "memories", "counters", "error_flags"):
            value = owns.get(key)
            if value not in (None, "", [], {}):
                storage.append(f"{key}: {_compact(value)}")
        if storage:
            rows.append(
                (
                    _first_present(item, "name", default="unnamed_module"),
                    _first_present(item, "source_file", "file", default="source file not specified"),
                    "; ".join(storage),
                    _first_present(item, "reset_domain", default="reset not specified"),
                )
            )
    return _table(
        ("Module", "Source File", "Storage / Counter Ownership", "Reset Rule"),
        rows or [("no storage owner", "not applicable", "not applicable", "not applicable")],
    )


def _state_machine_table(state_machines: Any) -> str:
    rows = []
    for item in _named_list(state_machines, "state_machines"):
        if not isinstance(item, dict):
            continue
        rows.append(
            (
                _first_present(item, "name", default="unnamed_fsm"),
                _first_present(item, "owning_module", default="owner not specified"),
                _first_present(item, "reset_state", default="reset state not specified"),
                _first_present(item, "states", default="states not specified"),
                _first_present(item, "transitions", default="transitions not specified"),
                _first_present(item, "illegal_state_behavior", default="illegal-state behavior not specified"),
            )
        )
    return _table(
        ("FSM", "Owning Module", "Reset State", "States", "Transitions", "Illegal State Behavior"),
        rows or [("no FSM", "not recorded", "not recorded", "not recorded", "not recorded", "not recorded")],
    )


def _trace_table(data: dict[str, Any]) -> str:
    rows = []
    target_keys = {
        "trace_req_to_design_intent": ("design_intent", "Design Intent"),
        "trace_req_to_test_intent": ("test_intent", "Test Intent"),
        "trace_req_to_rtl": ("planned_rtl", "Loop1 RTL"),
        "trace_req_to_test": ("tests", "Loop1 Directed TB"),
        "trace_req_to_proto": ("prototype_checks", "Loop3 Prototype"),
    }
    for key, (target_key, label) in target_keys.items():
        for item in _named_list(data.get(key), "links"):
            target = _first_present(item, target_key, "target", "description", default="linked target not specified")
            rows.append((_first_present(item, "req_id", "requirement", default="unnamed_requirement"), label, target))
    return _table(("Requirement ID", "Trace Target", "Linked Artifact / Status"), rows or [("no requirement", "not recorded", "no trace links supplied")])


def _verification_goals_table(verification_plan: Any) -> str:
    goals = _list_from(verification_plan, "goals", "verification_goals")
    if goals:
        return _items_table(goals, ("Goal", "Requirement IDs"))
    rows = []
    for item in _named_list(verification_plan, "module_level"):
        if isinstance(item, dict):
            rows.append((_first_present(item, "module", "name", default="module"), _first_present(item, "checks", default="checks not recorded")))
        else:
            rows.append((_compact(item), "module-level verification goal"))
    for item in _list_from(verification_plan, "system_level"):
        rows.append(("system_level", _compact(item)))
    for item in _list_from(verification_plan, "scoreboards"):
        rows.append(("scoreboard", _compact(item)))
    for item in _list_from(verification_plan, "reference_models"):
        rows.append(("reference_model", _compact(item)))
    return _table(("Goal", "Requirement IDs / Checks"), rows or [("no goal", "not recorded")])


def _verification_test_matrix(verification_plan: Any) -> str:
    tests = _list_from(verification_plan, "tests", "test_matrix", "directed_tests")
    if tests:
        return _items_table(tests, ("Test", "Expected Result"))
    rows = []
    for item in _named_list(verification_plan, "full_function_matrix"):
        if isinstance(item, dict):
            rows.append((_first_present(item, "feature", "id", "name", default="feature"), _first_present(item, "tests", "expected", default="tests not recorded")))
        else:
            rows.append((_compact(item), "full-function matrix item"))
    for key, label in (
        ("scenario_tests", "scenario"),
        ("stress_tests", "stress"),
        ("fpga_realistic_tests", "fpga-realistic"),
        ("negative_tests", "negative"),
        ("baseline_entry_checks", "baseline"),
    ):
        for item in _list_from(verification_plan, key):
            rows.append((_compact(item), label))
    return _table(("Test", "Expected Result"), rows or [("no test", "not recorded")])


def _waveform_table(data: dict[str, Any]) -> str:
    rows = []
    for item in _list_from(data.get("test_intent"), "waveform_checks", "waveform_secondary_checks", "waveform_windows"):
        if isinstance(item, dict):
            rows.append(
                (
                    _first_present(item, "id", "name", "description", default="waveform_query"),
                    _first_present(item, "evidence", "signals", "pass_criteria", "description", default="covered by waveform intent"),
                )
            )
        else:
            rows.append((_compact(item), "covered by waveform intent"))
    for item in _list_from(data.get("verification_plan"), "waveform_comparison"):
        if isinstance(item, dict):
            rows.append(
                (
                    _first_present(item, "name", "id", default="waveform_comparison"),
                    _first_present(item, "pass_criteria", "signals", "trigger", default="waveform comparison criterion"),
                )
            )
        else:
            rows.append((_compact(item), "waveform comparison item"))
    return _table(("Check", "Evidence"), rows or [("no waveform check", "not recorded")])


def _directed_tb_contract_table(verification_plan: Any) -> str:
    rows = []
    for item in _list_from(verification_plan, "directed_tb_log_contract"):
        rows.append(("log_contract", _compact(item)))
    if isinstance(verification_plan, dict):
        wave = verification_plan.get("directed_tb_waveform_contract")
        if isinstance(wave, dict):
            for key in ("waveform_manifest", "waveform_directory", "waveform_files", "markers", "reports", "policy"):
                value = wave.get(key)
                if value not in (None, "", [], {}):
                    rows.append((key, _compact(value)))
    return _table(
        ("Contract Area", "Value"),
        rows or [("no directed TB contract", "not recorded")],
    )


def _uvm_environment_table(uvm_plan: Any) -> str:
    rows = []
    if isinstance(uvm_plan, dict):
        framework = uvm_plan.get("framework")
        if isinstance(framework, dict):
            for key in ("root", "template_family", "package_entry", "tb_top", "entry_check", "regression_entry"):
                value = framework.get(key)
                if value not in (None, "", [], {}):
                    rows.append(("framework", key, _compact(value)))
            for key in ("authoritative_planning_sources", "forbidden_planning_outputs", "anti_sidecar_rule", "pre_generation_check"):
                value = framework.get(key)
                if value not in (None, "", [], {}):
                    rows.append(("planning_guard", key, _compact(value)))
            for item in _list_from(framework, "required_entry_files"):
                rows.append(("required_entry_file", _compact(item), "Loop2 compile prerequisite"))
        for item in _named_list(uvm_plan, "interfaces"):
            if isinstance(item, dict):
                rows.append(
                    (
                        "interface",
                        _first_present(item, "name", default="interface"),
                        _first_present(item, "signals", "role", "path", default="interface contract"),
                    )
                )
        for item in _named_list(uvm_plan, "agents"):
            if isinstance(item, dict):
                rows.append(
                    (
                        "agent",
                        _first_present(item, "name", default="agent"),
                        _first_present(item, "mode", "owns", "analysis_exports", default="agent ownership"),
                    )
                )
        for item in _named_list(uvm_plan, "env_components"):
            if isinstance(item, dict):
                rows.append(
                    (
                        "env_component",
                        _first_present(item, "name", default="component"),
                        _first_present(item, "role", "connects", "path", default="environment component"),
                    )
                )
    return _table(
        ("Area", "Item", "Detail"),
        rows or [("no UVM plan", "not recorded", "not recorded")],
    )


def _uvm_tests_table(uvm_plan: Any, trace: Any) -> str:
    rows = []
    if isinstance(uvm_plan, dict):
        for item in _named_list(uvm_plan, "scoreboards"):
            if isinstance(item, dict):
                rows.append(
                    (
                        "scoreboard",
                        _first_present(item, "name", default="scoreboard"),
                        _first_present(item, "checks", "model", "inputs", default="scoreboard check"),
                    )
                )
        for item in _named_list(uvm_plan, "tests"):
            if isinstance(item, dict):
                rows.append(
                    (
                        "test",
                        _first_present(item, "name", default="test"),
                        _first_present(item, "virtual_sequence", "req_ids", "checker_path", default="test intent"),
                    )
                )
        for item in _named_list(uvm_plan, "coverage"):
            if isinstance(item, dict):
                rows.append(
                    (
                        "coverage",
                        _first_present(item, "id", "name", default="coverage"),
                        _first_present(item, "bins", "crosses", "ignore_bins", default="coverage intent"),
                    )
                )
    for item in _named_list(trace, "links"):
        if isinstance(item, dict):
            rows.append(
                (
                    "trace",
                    _first_present(item, "requirement_id", "req_id", default="requirement"),
                    _first_present(item, "uvm_tests", "virtual_sequences", "scoreboard_checks", "coverage_points", default="UVM trace target"),
                )
            )
    return _table(
        ("Kind", "Item", "Plan / Trace"),
        rows or [("no UVM test plan", "not recorded", "not recorded")],
    )


def _release_table(data: dict[str, Any]) -> str:
    gate = data.get("gate_status") if isinstance(data.get("gate_status"), dict) else {}
    return _table(
        ("Item", "Status"),
        [
            ("Docset Current", "DRAFT"),
            ("Spec Exit", gate.get("spec_exit", "not recorded")),
            ("Loop1 Exit", gate.get("loop1_exit", "not recorded")),
            ("Loop2 Exit", gate.get("loop2_exit", "not recorded")),
            ("Loop3 Exit", gate.get("loop3_exit", "not recorded")),
            ("Final Gate", gate.get("final_gate", "not recorded")),
        ],
    )


def _delivered_docs_table() -> str:
    return _table(
        ("Document", "Path", "Status"),
        [
            ("Application Guide", "output/docs/application/application_guide.md", "DRAFT"),
            ("Microarchitecture Specification", "output/docs/design/microarchitecture_spec.md", "DRAFT"),
            ("Verification Plan", "output/docs/test/verification_plan.md", "DRAFT"),
            ("Delivery Package", "output/docs/delivery/delivery_package.md", "DRAFT"),
        ],
    )


def _artifact_table(data: dict[str, Any]) -> str:
    return _table(
        ("Artifact Type", "Count", "Root"),
        [
            ("RTL", len(data.get("rtl_modules") or []), "output/rtl"),
            ("Directed TB", len(data.get("tb_files") or []), "output/tb"),
            ("UVM", len(data.get("uvm_files") or []), "output/uvm"),
            ("FPGA", len(data.get("fpga_files") or []), "output/fpga"),
            ("Reports", len(data.get("loop_reports") or []), "output/reports"),
        ],
    )


def _verification_evidence_table(data: dict[str, Any]) -> str:
    gate = data.get("gate_status") if isinstance(data.get("gate_status"), dict) else {}
    return _table(
        ("Evidence Area", "Value", "Required"),
        [
            ("Loop1", gate.get("loop1_exit", "not recorded"), "pass"),
            ("Loop2", gate.get("loop2_exit", "not recorded"), "pass"),
            ("Loop3", gate.get("loop3_exit", "not recorded"), "pass"),
            ("Review Findings", "see work/docparse/review/role_findings.yaml", "no blockers"),
        ],
    )


def _prototype_validation_table(prototype_plan: Any) -> str:
    rows = []
    if isinstance(prototype_plan, dict):
        for key in ("prototype_mode", "board", "tool_version", "ps7_preset_tcl"):
            value = prototype_plan.get(key)
            if value not in (None, "", [], {}):
                rows.append((key, _compact(value), "prototype setting"))
        clocking = prototype_plan.get("clocking")
        if isinstance(clocking, dict):
            for key, value in clocking.items():
                rows.append(("clocking", key, _compact(value)))
        for item in _named_list(prototype_plan, "resource_estimate"):
            if isinstance(item, dict):
                rows.append(("resource_estimate", _first_present(item, "resource", default="resource"), _first_present(item, "estimate", default="estimate not recorded")))
            else:
                rows.append(("resource_estimate", _compact(item), "estimate"))
        for key in ("ps_pl_boundary", "validation_flow", "expected_board_checks", "risk_items", "board_waveform_checks"):
            for item in _list_from(prototype_plan, key):
                if isinstance(item, dict):
                    rows.append((key, _first_present(item, "name", "type", default="item"), _first_present(item, "expected", "blocking", "description", default=_compact(item))))
                else:
                    rows.append((key, _compact(item), "planned item"))
    return _table(
        ("Area", "Item", "Detail"),
        rows or [("no prototype plan", "not recorded", "not recorded")],
    )


def _signoff_table() -> str:
    return _table(
        ("Checklist ID", "Item", "Required"),
        [
            ("SIGN-001", "Application Guide generated and current", "yes"),
            ("SIGN-002", "Microarchitecture Spec generated and current", "yes"),
            ("SIGN-003", "Verification Plan generated and current", "yes"),
            ("SIGN-004", "Docset manifest matches all documents", "yes"),
            ("SIGN-005", "Required engineering gates passed", "yes"),
        ],
    )


def _source_table(snapshot: dict[str, Any]) -> str:
    rows = [(item["path"], item["sha256"]) for item in snapshot.get("sources", [])[:80]]
    return _table(("Path", "SHA256"), rows or [("not recorded", "not recorded")])


def _generic_yaml_table(value: Any) -> str:
    rows = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _METADATA_KEYS:
                continue
            if isinstance(item, (dict, list)):
                rows.append((key, _compact(item)))
            else:
                rows.append((key, item))
    elif isinstance(value, list):
        rows.extend((str(index + 1), _compact(item)) for index, item in enumerate(value))
    return _table(("Field", "Value"), rows or [("no entries", "not recorded")])


def _items_table(items: list[Any], columns: tuple[str, str]) -> str:
    rows = []
    for item in items:
        if isinstance(item, dict):
            rows.append(
                (
                    _first(item, "id", "name", "title", "description", "text", "check", "feature"),
                    _first(item, "req_ids", "requirement_ids", "expected", "evidence", "evidence_ref", "status", "check", "description", "text"),
                )
            )
        else:
            rows.append((str(item), "covered by listed item"))
    return _table(columns, rows or [("no entry", "not recorded")])


def _requirements_table(requirements: Any) -> str:
    rows = []
    for item in _list_from(requirements, "functional_requirements", "requirements"):
        if isinstance(item, dict):
            rows.append(
                (
                    _first_present(item, "id", "name", default="unnamed_requirement"),
                    _first_present(item, "text", "description", "title", default="requirement text not recorded"),
                )
            )
        else:
            rows.append((_compact(item), "requirement text supplied as inline item"))
    return _table(("Requirement ID", "Requirement Text"), rows or [("no requirement", "not recorded")])


def _list_from(root: Any, *keys: str) -> list[Any]:
    if not isinstance(root, dict):
        return []
    for key in keys:
        value = root.get(key)
        if isinstance(value, list):
            return value
        if value not in (None, "", {}):
            return [value]
    return []


def _flatten_named_items(root: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(root, dict):
        for key, value in root.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        rows.append({"name": item.get("name", key), **item})
            elif isinstance(value, dict):
                rows.append({"name": value.get("name", key), **value})
    elif isinstance(root, list):
        rows.extend(item for item in root if isinstance(item, dict))
    return rows


def _named_list(root: Any, key: str) -> list[Any]:
    if isinstance(root, dict):
        value = root.get(key)
        if isinstance(value, list):
            return value
        if value not in (None, "", {}):
            return [value]
    if isinstance(root, list):
        return root
    return []


def _first(root: Any, *keys: str) -> str:
    if not isinstance(root, dict):
        return "not recorded"
    for key in keys:
        value = root.get(key)
        if value not in (None, "", [], {}):
            return _compact(value)
    return "not recorded"


def _first_present(root: Any, *keys: str, default: str) -> str:
    if not isinstance(root, dict):
        return default
    for key in keys:
        value = root.get(key)
        if value not in (None, "", [], {}):
            return _compact(value)
    return default


def _paragraph(value: str) -> str:
    return value if value and value != "TBD" else "not recorded"


def _compact(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(_compact(item) for item in value) or "not recorded"
    if isinstance(value, dict):
        items = [(key, item) for key, item in value.items() if key not in _METADATA_KEYS]
        return "; ".join(f"{key}={_compact(item)}" for key, item in items) or "not recorded"
    return str(value).replace("\n", " ") if value not in (None, "") else "not recorded"


def _table(headers: tuple[str, ...], rows: list[tuple[Any, ...]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        padded = list(row) + [""] * (len(headers) - len(row))
        lines.append("| " + " | ".join(_escape(item) for item in padded[: len(headers)]) + " |")
    return "\n".join(lines) + "\n"


def _escape(value: Any) -> str:
    return _compact(value).replace("|", "\\|")


def _value(value: Any) -> str:
    return "null" if value in (None, "") else str(value)
