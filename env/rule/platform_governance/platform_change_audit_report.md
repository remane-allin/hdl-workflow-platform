# Platform Change Audit Report

- result: PASS
- pcr_id: PCR-20260625-001
- platform_contract: 2026.06-contract-v2

## Changed Files
- env/core/hdlflow/cli.py
- env/core/hdlflow/docgen/collect.py
- env/core/hdlflow/docgen/constants.py
- env/core/hdlflow/docgen/render.py
- env/core/hdlflow/gates.py
- env/core/hdlflow/platform_governance.py
- env/core/hdlflow/repair.py
- env/core/hdlflow/requirements_frontend.py
- env/core/hdlflow/review.py
- env/core/hdlflow/waveform_gate.py
- env/rule/global/agents/requirements_frontend_roles.yaml
- env/rule/global/gates/global_gate_rules.yaml
- env/rule/platform_governance/
- env/rule/project_default/project_config.yaml
- env/rule/scaffold/project_scaffold.yaml
- env/rule/scaffold/work/docparse/README.md
- env/rule/scaffold/work/docparse/doc_projection.yaml
- env/rule/scaffold/work/docparse/frontdoor/README.md
- env/rule/scaffold/work/docparse/frontdoor/baseline/
- env/rule/scaffold/work/docparse/frontdoor/contract.yaml
- env/rule/scaffold/work/docparse/frontdoor/generated/
- env/rule/scaffold/work/docparse/frontdoor/history/
- env/rule/scaffold/work/docparse/frontdoor/intake/
- env/rule/scaffold/work/docparse/frontdoor/templates/
- env/rule/scaffold/work/docparse/prototype/prototype_plan.yaml
- env/rule/scaffold/work/docparse/trace_matrix/req_to_uvm_intent.yaml
- env/rule/scaffold/work/docparse/verification/uvm_plan.yaml
- env/rule/scaffold/work/gates/claim_policy.yaml
- env/rule/scaffold/work/loop1_rtl_tb/README.md
- env/rule/scaffold/work/loop1_rtl_tb/config/top_wave_manifest.yaml
- env/rule/scaffold/work/loop1_rtl_tb/sim/README.md
- env/rule/scaffold/work/loop1_rtl_tb/sim/rtl_functional.do
- env/rule/scaffold/work/loop3_fpga_proto/board_tests/prototype_plan.yaml
- env/rule/skills/modelsim-run-triage-debug/SKILL.md
- env/rule/skills/requirements-frontdoor/SKILL.md
- env/rule/skills/rtl-architecture-and-gen/SKILL.md
- env/rule/skills/uvm-env-and-test-build/SKILL.md
- env/test/tests/test_hdlflow_platform.py
- env/tool/scripts/Invoke-HdlLoop3BoardVerify.ps1
- env/tool/scripts/Invoke-HdlVitis.ps1
- env/tool/scripts/README.md

## Impact
- components: arbtr_review, cli_commands, core_modules, fpga_prototype, gates, parsers, platform_governance, regression, report_generators, requirements_planning, rules, schemas, skills, templates, tests, tool_scripts, vcd_analysis
- stages: directed_tb, fpga_prototype, platform_governance, regression, requirements_planning, uvm, vcd_analysis
- required_fixtures: claim_overreach_block_project, full_contract_pass_project, legacy_frontdoor_contract_migration_project, loop3_emulated_boundary_claim_project, plan_drift_block_project, requirement_intake_refresh_project, tb_pass_vcd_fail_project, vcd_required_signal_missing_project

## Checks
| Check | Status | Detail |
| --- | --- | --- |
| platform_pcr_gate | PASS | PCR PCR-20260625-001 is complete and post-draft |
| reduced_scope_policy_gate | PASS | formal platform files use full-contract validation language |
| impact_completeness_gate | PASS | 41 changed env file(s) are covered by PCR and impact matrix |
| template_schema_gate | PASS | template/schema coupling is declared |
| regression_coverage_gate | PASS | 8 required platform fixture(s) are declared and passed |
| migration_readiness_gate | PASS | contract migration path is declared |
| arbtr_platform_review_gate | PASS | Arbtr platform review decision is ACCEPT_WITH_WAIVER |
| platform_regression_command_gate | PASS | Ran 195 tests in 7.560s

OK (skipped=5) |
