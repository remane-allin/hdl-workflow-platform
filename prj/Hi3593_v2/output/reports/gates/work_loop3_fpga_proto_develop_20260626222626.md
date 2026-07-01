# Gate Report: work/loop3_fpga_proto

- generated_at: 2026-06-26T22:26:26
- project: Hi3593_v2
- node: work/loop3_fpga_proto
- level: develop
- change_id: none
- result: FAIL

## Checks

| Check | Status | Detail |
| --- | --- | --- |
| project_scaffold_schema | PASS | script-created scaffold marker is valid |
| project_root_tool_logs | PASS | no Vivado journal/log files in project root |
| project_local_loop_scripts_absent | PASS | no project-local Loop1/Loop2 ad hoc generator scripts found |
| change_control_state | PASS | no open or unbound approved change request blocks this gate |
| frontdoor_execution_lock | PASS | no pending or unmerged approved frontdoor intake blocks downstream execution |
| requirements_docparse_reentry | PASS | latest DocParse manifest work_docparse_develop_20260626205022.json is newer than requirement files |
| loop3_report_refresh | PASS | board_validation_report=PASS, loop3_exit_report=PASS, vitis_boot_report=PASS, vivado_implementation_report=PASS |
| prerequisite:work/loop2_uvm | PASS | work\memory\recovery\rollback_manifests\work_loop2_uvm_develop_20260626212953.json |
| docset_sync | PASS | output/docs/manifests/docset_manifest.json synchronized |
| skill_policy:hdl-workflow-orchestrator | PASS | env/rule/skills/hdl-workflow-orchestrator/SKILL.md constraint markers present |
| skill_policy:rtl-architecture-and-gen | PASS | env/rule/skills/rtl-architecture-and-gen/SKILL.md constraint markers present |
| skill_policy:requirements-frontdoor | PASS | env/rule/skills/requirements-frontdoor/SKILL.md constraint markers present |
| source_policy:rtl | PASS | output/rtl follows Verilog-2001 policy |
| source_policy:fpga_constraints | PASS | output/fpga/vivado/constraints follows XDC policy |
| source_policy:fpga_scripts | PASS | output/fpga/vivado/scripts follows Tcl policy |
| source_policy:vitis_sources | PASS | output/fpga/vitis/src follows C/C++/headers/linker policy |
| source_policy:board_profiles | PASS | work/loop3_fpga_proto/board_profiles follows YAML/Tcl/Markdown policy |
| source_policy:board_tests | PASS | work/loop3_fpga_proto/board_tests follows YAML/JSON/Markdown policy |
| source_policy:loop3_scripts | PASS | work/loop3_fpga_proto/scripts follows PowerShell/Python/Markdown policy |
| official_protocol_naming | PASS | official UART boundary names use uart_rx/uart_tx |
| rtl_task_usage | PASS | RTL .v files under output/rtl contain no task/endtask declarations |
| rtl_skill_per_file_audit | PASS | platform-generated RTL skill audit passed for 7 file(s) |
| rtl_semantic_stub_absent | PASS | no event-level/prototype/accept-all/always-hit RTL semantics found |
| loop3_no_project_local_ad_hoc_scripts | PASS | Loop3 uses only scaffold scripts plus platform wrappers |
| path:output/reports/loop3/preflight/database_preflight.md | PASS | exists |
| path:output/reports/loop3/preflight/prototype_plan_check.md | PASS | exists |
| path:output/fpga/vivado/reports/post_impl_timing_summary.rpt | PASS | exists |
| path:output/fpga/vivado/reports/post_impl_drc.rpt | PASS | exists |
| path:output/reports/loop3/serial/latest_serial_text.log | PASS | exists |
| path:output/reports/loop3/serial/latest_serial_validation_report.md | PASS | exists |
| path:output/reports/loop3/vivado_implementation_report.md | PASS | exists |
| path:output/reports/loop3/vitis_boot_report.md | PASS | exists |
| path:output/reports/loop3/board_validation_report.md | PASS | exists |
| path:output/reports/loop3/loop3_exit_report.md | PASS | exists |
| loop3_bitstream_available | PASS | output/fpga/vivado/bitstream/hi3593_v2_ps_pl.bit |
| loop3_database_preflight_pass | PASS | marker found: result: PASS |
| loop3_prototype_plan_pass | PASS | marker found: result: PASS |
| loop3_external_stimulus_boundary | PASS | PS_PL bus/UART stimulus is outside synthesizable PL RTL |
| loop3_validation_boundary_claim | PASS | Loop3 validation boundary and claim policy are explicit |
| loop3_timing_setup_met | PASS | WNS=3.15, TNS failing endpoints=0 |
| loop3_timing_hold_met | PASS | WHS=0.068, THS failing endpoints=0 |
| loop3_serial_echo | PASS | PL UART command read produced DDR response: read data=0x00000180 |
| loop3_configured_serial_stress | PASS | no Loop3 serial stress marker policy configured |
| loop3_vivado_implementation_report | PASS | output/reports/loop3/vivado_implementation_report.md result PASS |
| loop3_vitis_boot_report | PASS | output/reports/loop3/vitis_boot_report.md result PASS |
| loop3_board_validation_report | PASS | output/reports/loop3/board_validation_report.md result PASS |
| loop3_exit_report | PASS | output/reports/loop3/loop3_exit_report.md result PASS |
| loop3_database_ug_flow | PASS | prototype Tcl run is guarded by database preflight and local UG/Tcl command evidence |
| loop3_warning_policy | PASS | develop gate allows documented Vivado warnings; release gate is strict |
| forbidden_formal_text | PASS | formal artifacts contain no forbidden workflow vocabulary |
| review_findings_gate | PASS | report: output\reports\review\review_check.md; blockers=0 |
| artifact_hash_drift | PASS | no previous gate manifest to compare |
| skill_policy_hash_drift | PASS | no previous gate manifest to compare |
| protected_gate_hash_drift | PASS | no previous gate manifest to compare |
| artifact_freshness | FAIL | source file is newer than one or more evidence reports; rerun the owning checks |
