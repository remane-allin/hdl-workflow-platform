# Gate Report: work/loop2_uvm

- generated_at: 2026-06-26T21:29:53
- project: Hi3593_v2
- node: work/loop2_uvm
- level: develop
- change_id: none
- result: PASS

## Checks

| Check | Status | Detail |
| --- | --- | --- |
| project_scaffold_schema | PASS | script-created scaffold marker is valid |
| project_root_tool_logs | PASS | no Vivado journal/log files in project root |
| project_local_loop_scripts_absent | PASS | no project-local Loop1/Loop2 ad hoc generator scripts found |
| change_control_state | PASS | no open or unbound approved change request blocks this gate |
| frontdoor_execution_lock | PASS | no pending or unmerged approved frontdoor intake blocks downstream execution |
| requirements_docparse_reentry | PASS | latest DocParse manifest work_docparse_develop_20260626205022.json is newer than requirement files |
| loop2_report_refresh | PASS | reports refreshed: 4 file(s) |
| prerequisite:work/loop1_rtl_tb | PASS | work\memory\recovery\rollback_manifests\work_loop1_rtl_tb_develop_20260626211505.json |
| skill_policy:hdl-workflow-orchestrator | PASS | env/rule/skills/hdl-workflow-orchestrator/SKILL.md constraint markers present |
| skill_policy:rtl-architecture-and-gen | PASS | env/rule/skills/rtl-architecture-and-gen/SKILL.md constraint markers present |
| skill_policy:uvm-env-and-test-build | PASS | env/rule/skills/uvm-env-and-test-build/SKILL.md constraint markers present |
| skill_policy:modelsim-run-triage-debug | PASS | env/rule/skills/modelsim-run-triage-debug/SKILL.md constraint markers present |
| source_policy:rtl | PASS | output/rtl follows Verilog-2001 policy |
| source_policy:directed_tb | PASS | output/tb follows Verilog-2001 policy |
| source_policy:uvm | PASS | output/uvm follows SystemVerilog policy |
| official_protocol_naming | PASS | official UART boundary names use uart_rx/uart_tx |
| rtl_task_usage | PASS | RTL .v files under output/rtl contain no task/endtask declarations |
| rtl_comment_headers | PASS | RTL files include module description and scope headers |
| rtl_skill_per_file_audit | PASS | platform-generated RTL skill audit passed for 7 file(s) |
| rtl_semantic_stub_absent | PASS | no event-level/prototype/accept-all/always-hit RTL semantics found |
| docset_sync | PASS | output/docs/manifests/docset_manifest.json synchronized |
| loop2_database_preflight_report_available | PASS | output/reports/loop2/preflight/database_preflight.md |
| loop2_database_preflight_pass | PASS | marker found: result: PASS |
| loop2_uvm_flesh_plan_available | PASS | output/reports/loop2/preflight/uvm_flesh_plan.md |
| loop2_uvm_flesh_plan_pass | PASS | marker found: result: PASS |
| loop2_no_entry_check_final_report | PASS | entry-check evidence is transient and not part of final Loop2 reports |
| loop2_no_template_artifacts | PASS | no .template files under output/uvm |
| loop2_full_uvm_required_files | PASS | 9 required real UVM file(s) present |
| loop2_full_uvm_required_globs | PASS | all required UVM artifact patterns matched |
| loop2_no_template_placeholders | PASS | no forbidden template placeholder markers in real UVM files |
| path:work/loop2_uvm/current/cmd/command.json | PASS | exists |
| path:work/loop2_uvm/current/cmd/command.md | PASS | exists |
| path:work/loop2_uvm/current/log/modelsim.log | PASS | exists |
| path:work/loop2_uvm/current/manifest.json | PASS | exists |
| path:output/reports/loop2/loop2_report.md | PASS | exists |
| path:output/reports/loop2/loop2_report.json | PASS | exists |
| path:output/reports/loop2/loop2_report_manifest.json | PASS | exists |
| loop2_report_json | PASS | hdlflow_loop2_report_v1 result=PASS |
| loop2_report_markdown_shape | PASS | unified report sections found and no Evidence section |
| loop2_command_schema | PASS | schema hdlflow_command_v1 |
| loop2_current_manifest_schema | PASS | schema hdlflow_run_current_v1 |
| loop2_report_manifest_schema | PASS | schema hdlflow_report_manifest_v1 |
| loop2_current_manifest_hashes | PASS | 4 current artifact hash(es) recorded |
| loop2_report_manifest_hashes | PASS | report manifest hashes match current artifacts |
| loop2_report_no_raw_logs | PASS | output/reports contains report artifacts only |
| loop2_report_no_timestamp_runs | PASS | no default timestamp run archive |
| path:work/loop2_uvm/_runtime/loop2_bindings.sqlite | PASS | exists |
| path:work/loop2_uvm/trace_matrix/req_to_uvm.yaml | PASS | exists |
| path:work/loop2_uvm/trace_matrix/req_to_assertion.yaml | PASS | exists |
| path:work/loop2_uvm/trace_matrix/req_to_coverage.yaml | PASS | exists |
| skill_policy_freshness | PASS | evidence reports are newer than configured skill constraints |
| loop2_report_pass | PASS | structured report result PASS |
| loop2_report_parser_clean | PASS | no structured parser errors |
| loop2_transaction_contract | PASS | 64 structured transaction(s) checked |
| loop2_zero_error_counts | PASS | uvm_error=0, uvm_fatal=0, failed_checks=0 |
| loop2_functional_coverage | PASS | 100.00% >= 80.00% |
| loop2_checked_transaction_count | PASS | 64 checked transaction(s) >= 64 |
| loop2_min_scenario_tests | PASS | 8 scenario/test sequence class(es) found |
| loop2_stress_multi_stimulus | PASS | stress sequence has at least 2 stimulus operation(s) |
| loop2_coverage_triage_closed | PASS | no unresolved coverage triage rows found |
| loop2_bound_assertions_present | PASS | assertion source present: output/uvm/assertions/dut_assertions.sv |
| loop2_functional_coverage_observed | PASS | coverage collector appears connected to observed analysis traffic |
| loop2_independent_oracle | PASS | monitor publishes observed transactions and scoreboard compares against a spec/reference model |
| loop2_code_coverage | PASS | 100.00% >= 80.00% from work/loop2_uvm/current/log/coverage_raw.txt |
| loop2_stimulus_breadth | PASS | required stress stimulus patterns found |
| loop2_configured_scenario_evidence | PASS | no extra Loop2 scenario marker policy configured |
| bug_closure_pass | PASS | no open critical/major bug candidates found |
| forbidden_formal_text | PASS | formal artifacts contain no forbidden workflow vocabulary |
| review_findings_gate | PASS | report: output\reports\review\review_check.md; blockers=0 |
| artifact_hash_drift | PASS | no previous gate manifest to compare |
| skill_policy_hash_drift | PASS | no previous gate manifest to compare |
| protected_gate_hash_drift | PASS | no previous gate manifest to compare |
| artifact_freshness | PASS | evidence reports are newer than checked source files |
