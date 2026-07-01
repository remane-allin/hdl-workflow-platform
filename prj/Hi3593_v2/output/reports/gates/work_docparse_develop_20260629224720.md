# Gate Report: work/docparse

- generated_at: 2026-06-29T22:47:20
- project: Hi3593_v2
- node: work/docparse
- level: develop
- change_id: CR-20260626224447-complete-hi3593-digital-functional-cover
- result: PASS

## Checks

| Check | Status | Detail |
| --- | --- | --- |
| project_scaffold_schema | PASS | script-created scaffold marker is valid |
| project_root_tool_logs | PASS | no Vivado journal/log files in project root |
| project_local_loop_scripts_absent | PASS | no project-local Loop1/Loop2 ad hoc generator scripts found |
| change_control_state | PASS | approved change request bound: CR-20260626224447-complete-hi3593-digital-functional-cover |
| frontdoor_execution_lock | PASS | frontdoor intake may be edited only before DocParse exit |
| prerequisite:input | PASS | work\memory\recovery\rollback_manifests\input_develop_20260626204816.json |
| source_encoding_integrity | PASS | requirement sources are valid UTF-8 with no mojibake markers |
| path:work/docparse/structured_spec/interface_spec.yaml | PASS | exists |
| path:work/docparse/structured_spec/interface_timing.yaml | PASS | exists |
| path:work/docparse/structured_spec/register_map.yaml | PASS | exists |
| path:work/docparse/structured_spec/test_intent.yaml | PASS | exists |
| path:work/docparse/structured_spec/timing_rules.yaml | PASS | exists |
| path:work/docparse/req_decompose/requirements.json | PASS | exists |
| path:work/docparse/trace_matrix/req_to_design_intent.yaml | PASS | exists |
| path:work/docparse/trace_matrix/req_to_test_intent.yaml | PASS | exists |
| path:work/docparse/frontdoor/contract.yaml | PASS | exists |
| path:work/docparse/frontdoor/srs.yaml | PASS | exists |
| path:work/docparse/frontdoor/acceptance_criteria.yaml | PASS | exists |
| path:work/docparse/frontdoor/forbidden_designs.yaml | PASS | exists |
| path:work/docparse/frontdoor/baseline/srs.yaml | PASS | exists |
| path:work/docparse/frontdoor/baseline/acceptance_criteria.yaml | PASS | exists |
| path:work/docparse/frontdoor/baseline/design_intent.yaml | PASS | exists |
| path:work/docparse/frontdoor/baseline/verification_intent.yaml | PASS | exists |
| path:work/docparse/frontdoor/baseline/prototype_intent.yaml | PASS | exists |
| path:work/docparse/frontdoor/baseline/forbidden_designs.yaml | PASS | exists |
| path:work/docparse/frontdoor/templates/new_requirement.template.yaml | PASS | exists |
| path:work/docparse/frontdoor/templates/requirement_change.template.yaml | PASS | exists |
| path:work/docparse/frontdoor/templates/architecture_supplement.template.yaml | PASS | exists |
| path:work/docparse/frontdoor/templates/verification_supplement.template.yaml | PASS | exists |
| path:work/docparse/frontdoor/templates/prototype_supplement.template.yaml | PASS | exists |
| path:work/docparse/frontdoor/generated/active_srs.generated.yaml | PASS | exists |
| path:work/docparse/frontdoor/generated/active_design_intent.generated.yaml | PASS | exists |
| path:work/docparse/frontdoor/generated/active_verification_intent.generated.yaml | PASS | exists |
| path:work/docparse/frontdoor/generated/active_prototype_intent.generated.yaml | PASS | exists |
| path:work/docparse/frontdoor/generated/active_trace_matrix.generated.yaml | PASS | exists |
| path:work/docparse/structured_spec/interface_spec.yaml | PASS | exists |
| path:work/docparse/structured_spec/document_analysis.yaml | PASS | exists |
| path:work/docparse/structured_spec/register_map.yaml | PASS | exists |
| path:work/docparse/structured_spec/test_intent.yaml | PASS | exists |
| path:work/docparse/structured_spec/timing_rules.yaml | PASS | exists |
| path:work/docparse/structured_spec/interface_timing.yaml | PASS | exists |
| path:work/docparse/architecture/module_plan.yaml | PASS | exists |
| path:work/docparse/architecture/interface_contracts.yaml | PASS | exists |
| path:work/docparse/architecture/dataflow.yaml | PASS | exists |
| path:work/docparse/architecture/state_machines.yaml | PASS | exists |
| path:work/docparse/architecture/timing_model.yaml | PASS | exists |
| path:work/docparse/architecture/rtl_planning_rules.yaml | PASS | exists |
| path:work/docparse/verification/verification_plan.yaml | PASS | exists |
| path:work/docparse/verification/uvm_plan.yaml | PASS | exists |
| path:work/docparse/verification/assertion_plan.yaml | PASS | exists |
| path:work/docparse/verification/coverage_plan.yaml | PASS | exists |
| path:work/docparse/prototype/prototype_plan.yaml | PASS | exists |
| path:work/docparse/prototype/clock_plan.yaml | PASS | exists |
| path:work/docparse/prototype/pin_resource_intent.yaml | PASS | exists |
| path:work/docparse/review/role_findings.yaml | PASS | exists |
| path:work/docparse/review/decision_log.yaml | PASS | exists |
| path:work/docparse/review/arbitration_log.yaml | PASS | exists |
| path:work/docparse/doc_projection.yaml | PASS | exists |
| path:work/docparse/trace_matrix/req_to_design_intent.yaml | PASS | exists |
| path:work/docparse/trace_matrix/req_to_test_intent.yaml | PASS | exists |
| path:work/docparse/trace_matrix/req_to_uvm_intent.yaml | PASS | exists |
| machine_readable_specs_ready | PASS | structured interface, register/op-code, timing, and test-intent specs are READY |
| requirements_frontdoor_ready | PASS | report: output\reports\docparse\requirements_frontend_report.md |
| requirement_questions_reviewed | PASS | requirement ambiguity questions were reviewed by the user and no unresolved blockers remain |
| spec_agent_ready | PASS | Spec Agent artifacts define executable spec boundaries and trace roots |
| arch_agent_ready | PASS | Arch Agent artifacts define topology, interfaces, dataflow, state machines, and timing model |
| exec_agent_boundary_ready | PASS | Exec Agent is limited to RTL and complete functional directed TB implementation roots |
| sim_agent_plan_ready | PASS | Sim Agent owns verification, UVM, waveform, coverage, and Loop1/Loop2/Loop3 evidence plans |
| review_agent_ready | PASS | Review Agent findings surface is present and write-limited to defects, risks, and advice |
| arbtr_flow_ready | PASS | Arbtr Agent decision and arbitration logs are present for feedback routing and freeze control |
| docset_sync | PASS | output/docs/manifests/docset_manifest.json synchronized |
| official_protocol_naming | PASS | official UART boundary names use uart_rx/uart_tx |
| docparse_extract_policy | PASS | 4 parsed content file(s) from MinerU high-precision API |
| docparse_test_analysis_breadth | PASS | source-bound opcodes plus scenario/stress/prototype analysis are planned |
| docparse_no_ad_hoc_analysis_artifacts | PASS | no ad hoc scope, analysis, or draft artifacts found |
| forbidden_formal_text | PASS | formal artifacts contain no forbidden workflow vocabulary |
| review_findings_gate | PASS | report: output\reports\review\review_check.md; blockers=0 |
| artifact_hash_drift | PASS | source hashes match previous gate manifest work_docparse_develop_20260626205022.json |
| protected_gate_hash_drift | PASS | 2 protected gate/platform file change(s) are covered by CR-20260626224447-complete-hi3593-digital-functional-cover impact artifacts |
| artifact_freshness | PASS | evidence reports are newer than checked source files |
