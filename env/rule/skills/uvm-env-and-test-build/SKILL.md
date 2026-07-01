---
name: uvm-env-and-test-build
description: Build or refine a spec-driven, maintainable UVM environment from normalized HDL specs. Use when the user needs agents, monitors, scoreboards, base tests, virtual sequences, scenario tests, or asks to split a monolithic UVM package into an RKV-style cfg/agents/env/seq_lib/tests/tb framework that stays aligned with the spec instead of the current RTL behavior.
---

# UVM Env And Test Build

Use this skill for SystemVerilog/UVM verification code under `output/uvm/`.
Do not place UVM or SystemVerilog helper files under `output/tb/`; that
directory is reserved for Verilog-2001 directed Loop1 testbenches.

## Inputs

- `work/docparse/structured_spec/interface_spec.yaml`
- `work/docparse/structured_spec/register_map.yaml`
- `work/docparse/structured_spec/test_intent.yaml`
- `work/docparse/structured_spec/timing_rules.yaml`
- `work/docparse/verification/uvm_plan.yaml`
- `work/docparse/trace_matrix/req_to_uvm_intent.yaml`
- existing UVM files in `output/uvm/`
- triage output when the issue is TB-side

## Workflow

1. Treat the normalized spec as the authority for expected behavior.
2. Start Loop2 only after Loop1 has finished and the Loop1 gate evidence is PASS.
3. Instantiate project-specific UVM source files from templates or prior plans; `.template` files are not deliverables and must not remain under `output/uvm/` at Loop2 signoff.
4. Define or update interfaces, transactions, configs, agents, monitors, sequencers, virtual sequences, tests, coverage, environment, package, and top-level TB.
5. Build the scoreboard and reference model from the spec, not from the buggy DUT behavior.
6. Prefer the RKV-style framework layout when creating or refactoring non-trivial UVM code:
   - `cfg/`
   - `agents/<protocol_or_bus>/`
   - `cov/`
   - `env/`
   - `seq_lib/`
   - `tests/`
   - `tb/`
   Read [references/rkv-style-uvm-framework.md](references/rkv-style-uvm-framework.md) before doing this split.
   Also query the local template database entries when available:
   - `uvm.rkv_style_framework`
   - `uvm.rkv_i2c_reference_profile`
7. Run `python -m hdlflow.cli loop2-database-preflight --workspace <workspace> --project <project>` after the skeleton exists, then use `output/reports/loop2/preflight/uvm_flesh_plan.md` as the implementation provenance for the next pass.
   The local UVM database must guide the "flesh" after the template creates the bones:
   - `uvm_config_db` and virtual interface ownership for `cfg/` and `tb/`
   - agent driver, monitor, sequencer, and transaction responsibilities under `agents/`
   - sequences, virtual sequences, and scenario tests under `seq_lib/` and `tests/`
   - analysis port/export wiring, scoreboard queues, and reference model behavior in `env/`
   - monitor-sampled functional coverage in `cov/`
   - RAL adapter/register model pieces when `register_map.yaml` requires them
8. Create or refine:
   - environment
   - package
   - base test
   - virtual sequence base
   - scenario tests and vseqs
   - functional coverage model
   - scoreboard/reference model
   - protocol agent files
9. If register modeling is needed, consume outputs from `$register-spec-and-ral` or align manually with `register_map.yaml`.
10. Preserve the DocParse UVM planning intent in `work/docparse/trace_matrix/req_to_uvm_intent.yaml`, then update `work/loop2_uvm/trace_matrix/req_to_uvm.yaml`, `work/loop2_uvm/trace_matrix/req_to_assertion.yaml`, and `work/loop2_uvm/trace_matrix/req_to_coverage.yaml` after the UVM, assertion, and coverage artifacts exist.
11. Run or hand off to `$modelsim-run-triage-debug`, then update the unified Loop2 report, current run manifest, and binding database evidence together. The binding database is an intermediate trace artifact, not the Loop2 completion result.
12. Treat Loop2 final reports as current-run artifacts. Every full functional regression run must overwrite `work/loop2_uvm/current/log/modelsim.log`, `output/reports/loop2/loop2_report.md`, `output/reports/loop2/loop2_report.json`, and `output/reports/loop2/loop2_report_manifest.json`; never append a new run into stale reports.
13. Emit structured `HDLFLOW|UVM_CHECK|...` log events from sequences, tests, monitors, or scoreboards. Emit structured `HDLFLOW|UVM_CHECK|schema=hdlflow_event_v1|version=1|stage=loop2|...` log events for every checked test item. Each event must include `test_id`, `txn_id`, `sent`, `expected`, `actual`, and `result` fields. Each signoff run must also emit one `HDLFLOW|UVM_SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop2|...` event so `loop2-refresh-reports` can generate the final report directly from the real log.
14. `loop2_independent_oracle` is a hard gate. Monitors must reconstruct and publish observed transactions; scoreboards must compare observed transactions against a spec/reference model. Do not route `req.pass` or driver-side verdicts into the scoreboard as the source of truth.
15. `loop2_code_coverage` is a hard gate for develop/release levels. The raw coverage report must meet the configured threshold or have an explicit row-level waiver accepted by the platform gate.

## UVM Test And Coverage Strategy

Use a legal-scenario coverage strategy. Functional coverage should prove that
the intended protocol, register, FIFO, reset, parity, label, and status
behaviors were exercised with active checking. It is not a raw cross-product
scoreboard.

When building UVM tests and covergroups:

- Prefer deterministic functional sequences before broad randomization.
- A Loop2 signoff regression must be requirement-bound and quantitatively justified. Define a project-appropriate minimum transaction count in `uvm_policy.min_checked_transactions`; for ordinary byte/packet protocols, use at least 64 checked transactions unless the spec justifies a smaller bound.
- A Loop2 signoff plan must include at least `uvm_policy.min_scenario_tests` scenario tests. The project default is 5.
- At least one stress scenario is required, and each stress transaction must drive multiple stimuli according to `uvm_policy.min_stress_stimuli_per_transaction`.
- Every testcase must have a requirement/test-intent link and an active checker path.
- Cover operation categories, access direction, scenario class, checked-read result, and important data modes only when the combination is legal and meaningful.
- Do not create broad scenario x opcode x operation-kind crosses unless each bin has a real spec meaning.
- Use `ignore_bins` for impossible combinations, such as command-only opcodes crossed with read/write access modes.
- Treat failure bins used for debug as non-goal bins; a read mismatch should fail the test through scoreboard/assertion logic, not become a coverage closure target.
- A coverage increase is valid only when the same run still has scoreboard, assertion, or self-checking evidence enabled.
- For code coverage holes, generate new UVM scenarios only for reachable legal behavior. Dead code, reserved behavior, analog/pad scope, or unreachable-by-spec logic must be classified instead of forced.
- Remaining FSM transition or toggle holes are release-blocking only when tied to legal requirements or approved project policy.
- Do not lower thresholds silently. If a legal hole cannot be closed, record a waiver or risk note with rationale and replacement evidence.

## Rules

- Never "fix" the testbench to match an incorrect DUT.
- Keep SystemVerilog in `output/uvm/`. RTL and directed Loop1 TB remain Verilog-2001 `.v` files under `output/rtl/` and `output/tb/`.
- Do not leave `.template` files under `output/uvm/` in a Loop2-ready project; templates must be instantiated into real project-specific `.sv` / `.svh` files.
- Do not keep all classes in one large package file for a real project; use the package as a thin include hub.
- Do not treat the Loop2 binding database as signoff by itself. Loop2 signoff requires compiled UVM, passing regression, scoreboard evidence, assertion evidence, coverage evidence, and a binding database.
- Do not claim authoritative UVM signoff from a handful of hand-written transactions. Use sequencer/driver-generated transactions, monitor-observed transactions, scoreboard matching, and functional coverage tied to the transaction stream.
- Every generated test should have a clear intent and a checker path.
- Every generated test should produce structured log evidence with visible test-case boundaries and input/expected/actual/result fields.
- Use baseline/precheck runs only as entry checks. After the full functional regression passes, final Loop2 deliverables keep the unified report, current run manifest, and binding evidence only; do not keep a baseline functional-test report as signoff evidence.
- Start with deterministic functional scenarios before broad randomization.
- Keep configuration, virtual interface hookup, and scoreboard assumptions explicit.
- If the issue belongs to RTL or the spec itself, record the mismatch and route it back instead of masking it in UVM.
- Do not chase meaningless coverage bins by creating invalid stimulus or deleting checks.

## Completion Gate

This skill is complete when:

- the environment compiles in principle
- basic tests map to `test_intent.yaml`
- scoreboard ownership is clear
- no `.template` artifacts remain under `output/uvm/`
- `database_preflight.md` and `uvm_flesh_plan.md` exist and both contain `result: PASS`
- configuration, agent, monitor, driver, sequencer, scoreboard, coverage, virtual sequence, tests, package, interface, and TB top are present as real project-specific UVM files
- checked transaction count meets `uvm_policy.min_checked_transactions`
- scenario test count meets `uvm_policy.min_scenario_tests`
- stress transactions include at least `uvm_policy.min_stress_stimuli_per_transaction` stimuli
- unified report, current run manifest, and binding database evidence are all updated from the same Loop2 pass
- final report files were overwritten by the latest full functional regression run
- final report files contain per-test sections generated from `HDLFLOW|UVM_CHECK|schema=hdlflow_event_v1|version=1|stage=loop2|...` events in the real simulator log
- known monitor or checker assumptions are documented
- functional coverage bins and crosses are tied to legal verification intent, with impossible combinations ignored or documented

## References

- Read [references/uvm-handoff-checklist.md](references/uvm-handoff-checklist.md) before handing off to simulation.
- Read [references/rkv-style-uvm-framework.md](references/rkv-style-uvm-framework.md) when creating a new maintainable UVM environment or refactoring a monolithic UVM package.
