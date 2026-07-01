# Platform Document Compliance Matrix

- scope: platform-only changes under `env/`
- evidence command: `python -m hdlflow.cli platform-regression --workspace . --all`
- status labels:
  - PASS: platform rule, template, gate, or test is implemented and checked.
  - PARTIAL: platform blocks or records the issue, but the full long-term mechanism is not complete.
  - OPEN: not implemented in the platform yet.

## Document 1: Hi3593_prj_平台工程缺陷分析报告.docx

| Item | Document Requirement / Defect | Platform Checkpoint | Status |
| --- | --- | --- | --- |
| D1-REQ-01 | Quarantine old `open_questions.md` and prevent mixed frontdoor contracts. | `frontdoor_contract_v2`, legacy inactive rule, baseline/intake/generated/history scaffold, frontdoor checker. | PASS |
| D1-REQ-02 | Convert broad requirements into blocking obligations. | New intake templates require design/verification/prototype obligations and trace links; trace freshness gate exists. Full obligation state machine is not complete. | PARTIAL |
| D1-ARCH-01 | Use one active design baseline; derived plans must not add design intent. | `contract.yaml` authoritative baseline, generated active baseline files, downstream execution lock. | PASS |
| D1-RTL-01 | Detect event-level RX injection / prototype RTL that claims full ARINC decode. | `rtl_semantic_stub_absent` scans RTL for event-level injection, prototype words, placeholder/stub, accept-all, always-hit patterns. | PASS |
| D1-RTL-02 | Detect accept-all filter and always-hit mailbox. | Same semantic gate explicitly checks `| 1'b1`, `priority_match_hit <= 1'b1`, accept-all patterns. | PASS |
| D1-L1-01 | Directed TB must be task/requirement bound, not loose PASS markers. | `loop1_task_requirement_evidence` requires task begin, requirement binding, and structured checks. | PASS |
| D1-L1-02 | VCD gate failure must block Loop1. | `loop1_waveform_blocking`, `waveform_gate.py` gate policy blocking, ModelSim do file exits non-zero on waveform gate fail. | PASS |
| D1-L1-03 | VCD evidence should prioritize top-level IO; internal signals debug-only. | `top_wave_manifest.yaml` has signal source and task binding policy. A full per-protocol waveform decoder is not complete. | PARTIAL |
| D1-L2-01 | UVM monitor/scoreboard must be independent, not driver `pass` echo. | `loop2_independent_oracle` checks monitors, `run_phase`, analysis port publication, expected/observed scoreboard evidence, and blocks driver-pass self-oracle patterns. | PASS |
| D1-L2-02 | Code coverage threshold must be enforced. | `loop2_code_coverage` parses `coverage_raw.txt` and applies configured threshold. | PASS |
| D1-L3-01 | Loop3 must state PS/PL emulation boundary and limit claims. | Loop3 prototype plans include `external_boundary`, `validation_modes`, `claim_policy`; `loop3_validation_boundary_claim` and `final_claim_gate` enforce claim limits. | PASS |
| D1-FINAL-01 | Final audit must not miss semantic issues. | Final gate includes RTL semantic signoff and claim gate. Full requirement-obligation closure is not complete. | PARTIAL |
| D1-GOV-01 | Review must block semantic mismatch, not just summarize. | `review.py` requires semantic signoff, Loop1 task/VCD evidence, Loop2 independent oracle, Loop3 claim policy citations. | PASS |
| D1-GOV-02 | Use a single authoritative state machine instead of scattered task_board/scorecard/approvals. | State sync exists, but a single `project_state.yaml` replacing all status sources is not implemented. | OPEN |
| D1-DB-01 | FPGA scripts should prove query-to-script database provenance. | Loop3 preflight and wrappers exist; line-level query -> Tcl/XDC/Vitis artifact provenance gate is not implemented. | PARTIAL |

## Document 2: HDL_Workflow_Platform_补充缺陷与整改建议.docx

| Item | Document Requirement | Platform Checkpoint | Status |
| --- | --- | --- | --- |
| SUP-REQ-001 | Build `baseline/intake/templates/generated/history` frontdoor model. | Scaffold and initializer create the complete model. | PASS |
| SUP-REQ-002 | Approved intake must merge into active SRS/design/verification/prototype/trace. | Approved intake merge gate blocks stale generated baseline. A dedicated merge command is not implemented. | PARTIAL |
| SUP-RTL-001 | Move gen_rtl hard rules into gates. | RTL semantic gate and RTL skill rules cover synthesizable RTL, no task in RTL, no stub/accept-all/always-hit. | PASS |
| SUP-TB-001 | Directed TB tasks must bind requirements/protocol roles. | Loop1 task evidence gate and requirements-frontdoor skill require task packaging. | PASS |
| SUP-TB-002 | TB must emit human-readable and machine-readable structured logs. | Gate requires structured task/check evidence. A reusable `tb_logger.sv` library/template is not implemented. | PARTIAL |
| SUP-VCD-001 | VCD manifest must be task/requirement driven and top-level-signal first. | `top_wave_manifest.yaml` has task binding, signal source, and blocking policy. Per-task generated VCD manifests are not fully automated. | PARTIAL |
| SUP-VCD-002 | VCD parser must reconstruct real waveform inputs/outputs and compare expected model. | Waveform gate blocks missing required signals and records analysis. Full ARINC/SPI protocol reconstruction plugin is not complete. | PARTIAL |
| SUP-VCD-003 | TB, VCD, combined verification reports must be generated and final gate must use combined result. | Loop1 report refresh and waveform gate exist. Dedicated `loop1_combined_verification_report.json` is not implemented. | PARTIAL |
| SUP-L3-001 | Split Loop3 into IP-level, PS/PL emulation, and external pin-level validation. | Prototype plan records validation modes and claim policy. Separate Loop3A/Loop3B/Loop3C commands/gates are not complete. | PARTIAL |
| SUP-L3-002 | External-boundary fallback must include claim policy. | Prototype plans and final claim gate enforce external pin-level/full hardware claim limits. | PASS |
| SUP-PLAN-001 | Main design report + active baseline YAML must be authoritative. | `contract.yaml` names human and machine authoritative baselines; generated active baseline exists. Full hash-binding enforcement is still docset-manifest dependent. | PARTIAL |
| SUP-ARB-001 | Arbtr must act as acceptance reviewer with ACCEPT/WAIVER/REWORK/REJECT/CLAIM_DOWNGRADE. | `claim_policy.yaml`, requirements-frontdoor skill, review requirements, final claim gate, and platform PCR Arbtr review implement this. | PASS |
| SUP-CLAIM-001 | Final claim gate must block over-claiming. | `final_claim_gate` checks Arbtr decision, waivers, and Loop3 claim overreach. | PASS |

## Document 3: HDL_Workflow_Platform_平台修改治理方案.docx

| Item | Document Requirement | Platform Checkpoint | Status |
| --- | --- | --- | --- |
| GOV-PCR-001 | Every platform change has a PCR with purpose, scope, acceptance criteria, regression, migration, Arbtr result. | `env/rule/platform_governance/platform_change_request.yaml`; `platform_pcr_gate`. | PASS |
| GOV-IMPACT-001 | Impact matrix prevents partial updates. | `impact_matrix.yaml`; `impact_completeness_gate` compares actual `env/` diff classification against PCR and matrix. | PASS |
| GOV-AUTO-001 | Path-triggered auto impact detection. | `platform_governance.py` classifies skills, templates, gates, parsers, reports, tests, tool scripts, UVM/VCD/Loop3/frontdoor paths. | PASS |
| GOV-CONTRACT-001 | Platform contract version and project migration path. | `platform_contract.yaml`, `migrate-project`, `migration_manifest.yaml`, scaffold `platform_contract_version`. | PASS |
| GOV-REG-001 | Required positive/negative fixtures for changed areas. | `regression_manifest.yaml` declares full-contract positive and blocking negative fixtures; `platform-regression --all` executes the full test suite. Separate directory fixtures under `env/test/fixtures/` are not implemented. | PARTIAL |
| GOV-GATE-001 | Platform gates: PCR, impact, template/schema, regression, migration, Arbtr. | Implemented in `platform_governance.py`; global gate rules list `platform_change`. | PASS |
| GOV-GATE-002 | Gate fixture and report provenance gates. | Regression coverage gate exists; report provenance hash gate for platform audit is not a separate gate. | PARTIAL |
| GOV-CMD-001 | Unified `platform-regression --all`. | CLI command exists and runs governance checks plus full platform tests. | PASS |
| GOV-MIG-001 | Migrate legacy frontdoor to contract/baseline/intake/generated/history and archive old files. | `migrate-project` creates missing scaffold artifacts and archives legacy `open_questions.md`. | PASS |
| GOV-ARB-001 | Arbtr platform review must challenge scope, migration, fixture, claim, docs. | PCR Arbtr review and `arbtr_platform_review_gate` enforce multi-status decision and waiver. | PASS |
| GOV-DOC-001 | Docs/user workflow mention platform governance commands. | `env/tool/scripts/README.md` documents `platform-regression` and `migrate-project`. | PASS |

## Open Follow-Up Items

1. Implement a real approved-intake merge command that updates active SRS/design/verification/prototype/trace baselines instead of only blocking stale approved intake.
2. Add a reusable TB logging package/template so structured human-readable and JSONL logs are generated consistently.
3. Add protocol-aware VCD parser plugins and a combined Loop1 verification report as the final Loop1 verdict source.
4. Split Loop3 into explicit Loop3A IP-level, Loop3B PS/PL emulated, and Loop3C external pin-level gates.
5. Add line-level database provenance for generated Tcl/XDC/Vitis scripts.
6. Replace scattered project status files with one authoritative project state model.
7. Add separate platform end-to-end fixtures under `env/test/fixtures/` if the team wants the governance方案’s fixture-directory model exactly; these must be full-contract positive or blocking negative fixtures, and must not reduce the signoff scope.
