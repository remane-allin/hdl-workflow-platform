# Gate Report: output

- generated_at: 2026-07-02T16:03:10
- project: Hi3593_v2
- node: output
- level: develop
- change_id: CR-20260702155634-forbid-directed-tb-markdown-sidecar
- result: PASS

## Checks

| Check | Status | Detail |
| --- | --- | --- |
| project_scaffold_schema | PASS | script-created scaffold marker is valid |
| project_root_tool_logs | PASS | no Vivado journal/log files in project root |
| project_local_loop_scripts_absent | PASS | no project-local Loop1/Loop2 ad hoc generator scripts found |
| change_control_state | PASS | approved change request bound: CR-20260702155634-forbid-directed-tb-markdown-sidecar |
| frontdoor_execution_lock | PASS | no pending or unmerged approved frontdoor intake blocks downstream execution |
| requirements_docparse_reentry | PASS | latest DocParse manifest work_docparse_develop_20260702154528.json is newer than requirement files |
| path:output/manifest.yaml | PASS | exists |
| docset_sync | PASS | output/docs/manifests/docset_manifest.json synchronized |
| manifest_loop1_gate | PASS | required marker(s) found |
| manifest_loop2_gate | PASS | required marker(s) found |
| manifest_loop3_gate | PASS | required marker(s) found |
| work/loop1_rtl_tb_gate_manifest | PASS | work\memory\recovery\rollback_manifests\work_loop1_rtl_tb_develop_20260702155923.json |
| work/loop2_uvm_gate_manifest | PASS | work\memory\recovery\rollback_manifests\work_loop2_uvm_develop_20260702155923.json |
| work/loop3_fpga_proto_gate_manifest | PASS | work\memory\recovery\rollback_manifests\work_loop3_fpga_proto_develop_20260702154551.json |
| rtl_task_usage | PASS | RTL .v files under output/rtl contain no task/endtask declarations |
| rtl_semantic_stub_absent | PASS | no event-level/prototype/accept-all/always-hit RTL semantics found |
| final_claim_gate | PASS | Arbtr decision ACCEPT; final claims are within available evidence |
| forbidden_formal_text | PASS | formal artifacts contain no forbidden workflow vocabulary |
| review_findings_gate | PASS | report: output\reports\review\review_check.md; blockers=0 |
| artifact_hash_drift | PASS | no previous gate manifest to compare |
| protected_gate_hash_drift | PASS | 1 protected gate/platform file change(s) are covered by CR-20260702155634-forbid-directed-tb-markdown-sidecar impact artifacts |
| artifact_freshness | PASS | freshness skipped; no comparable source/evidence set |
| requirements_consistency_gate | PASS | advisory: no semantic issue |
| architecture_impact_gate | PASS | advisory: no semantic issue |
| design_routing_gate | PASS | advisory: no semantic issue |
| microarchitecture_completeness_gate | PASS | advisory: no semantic issue |
| rtl_obligation_gate | PASS | advisory: no semantic issue |
| tb_blackbox_obligation_gate | PASS | advisory: no semantic issue |
| waveform_semantic_gate | PASS | advisory: no semantic issue |
| uvm_obligation_gate | PASS | advisory: no semantic issue |
| fpga_validation_obligation_gate | PASS | advisory: no semantic issue |
| release_truth_gate | PASS | advisory: no semantic issue |
