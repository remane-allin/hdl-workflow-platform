---
name: uvm-env-and-test-build
description: Build or refine a spec-driven, maintainable UVM environment from normalized HDL specs. Use when the user needs agents, monitors, scoreboards, base tests, virtual sequences, scenario tests, or asks to split a monolithic UVM package into an RKV-style cfg/agents/env/seq_lib/tests/tb framework that stays aligned with the spec instead of the current RTL behavior.
---

# UVM Env And Test Build

Use this skill for SystemVerilog/UVM verification code under `05_Output/uvm/`.
Do not place UVM or SystemVerilog helper files under `05_Output/tb/`; that
directory is reserved for Verilog-2001 directed Loop1 testbenches.

## Inputs

- `01_DocParse/structured_spec/interface_spec.yaml`
- `01_DocParse/structured_spec/register_map.yaml`
- `01_DocParse/structured_spec/test_intent.yaml`
- `01_DocParse/structured_spec/timing_rules.yaml`
- existing UVM files in `05_Output/uvm/`
- triage output when the issue is TB-side

## Workflow

1. Treat the normalized spec as the authority for expected behavior.
2. Start Loop2 only after Loop1 has finished and the Loop1 gate evidence is PASS.
3. Instantiate project-specific UVM source files from templates or prior plans; `.template` files are not deliverables and must not remain under `05_Output/uvm/` at Loop2 signoff.
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
7. Create or refine:
   - environment
   - package
   - base test
   - virtual sequence base
   - scenario tests and vseqs
   - functional coverage model
   - scoreboard/reference model
   - protocol agent files
8. If register modeling is needed, consume outputs from `$register-spec-and-ral` or align manually with `register_map.yaml`.
9. Update `01_DocParse/trace_matrix/req_to_test.yaml`.
10. Run or hand off to `$modelsim-run-triage-debug`, then update regression, exit, coverage, and binding database evidence together. The binding database is an intermediate trace artifact, not the Loop2 completion result.
11. Treat Loop2 final reports as current-run artifacts. Every full functional regression run must overwrite `loop2_uvm_regression_report.md`, `coverage_index.md`, and `loop2_exit_report.md` from the latest simulator log and coverage output; never append a new run into stale reports.

## UVM Test And Coverage Strategy

Use a legal-scenario coverage strategy. Functional coverage should prove that
the intended protocol, register, FIFO, reset, parity, label, and status
behaviors were exercised with active checking. It is not a raw cross-product
scoreboard.

When building UVM tests and covergroups:

- Prefer deterministic functional sequences before broad randomization.
- A Loop2 signoff regression must not be a tiny sanity run. Define a project-appropriate minimum transaction count in `uvm_policy.min_checked_transactions`; for ordinary byte/packet protocols, use at least 64 checked transactions unless the spec justifies a smaller bound.
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
- Keep SystemVerilog in `05_Output/uvm/`. RTL and directed Loop1 TB remain Verilog-2001 `.v` files under `05_Output/rtl/` and `05_Output/tb/`.
- Do not leave `.template` files under `05_Output/uvm/` in a Loop2-ready project; templates must be instantiated into real project-specific `.sv` / `.svh` files.
- Do not keep all classes in one large package file for a real project; use the package as a thin include hub.
- Do not treat the Loop2 binding database as signoff by itself. Loop2 signoff requires compiled UVM, passing regression, scoreboard evidence, assertion evidence, coverage evidence, and a binding database.
- Do not claim authoritative UVM signoff from a handful of hand-written transactions. Use sequencer/driver-generated transactions, monitor-observed transactions, scoreboard matching, and functional coverage tied to the transaction stream.
- Every generated test should have a clear intent and a checker path.
- Use baseline/precheck runs only as entry checks. After the full functional regression passes, final Loop2 deliverables keep regression, coverage, exit, and binding evidence only; do not keep a baseline functional-test report as signoff evidence.
- Start with deterministic functional scenarios before broad randomization.
- Keep configuration, virtual interface hookup, and scoreboard assumptions explicit.
- If the issue belongs to RTL or the spec itself, record the mismatch and route it back instead of masking it in UVM.
- Do not chase meaningless coverage bins by creating invalid stimulus or deleting checks.

## Completion Gate

This skill is complete when:

- the environment compiles in principle
- basic tests map to `test_intent.yaml`
- scoreboard ownership is clear
- no `.template` artifacts remain under `05_Output/uvm/`
- configuration, agent, monitor, driver, sequencer, scoreboard, coverage, virtual sequence, tests, package, interface, and TB top are present as real project-specific UVM files
- checked transaction count meets `uvm_policy.min_checked_transactions`
- regression, exit, coverage, and binding database evidence are all updated from the same Loop2 pass
- final report files were overwritten by the latest full functional regression run
- known monitor or checker assumptions are documented
- functional coverage bins and crosses are tied to legal verification intent, with impossible combinations ignored or documented

## References

- Read [references/uvm-handoff-checklist.md](references/uvm-handoff-checklist.md) before handing off to simulation.
- Read [references/rkv-style-uvm-framework.md](references/rkv-style-uvm-framework.md) when creating a new maintainable UVM environment or refactoring a monolithic UVM package.
