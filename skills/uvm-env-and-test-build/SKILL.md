---
name: uvm-env-and-test-build
description: Build or refine a spec-driven, maintainable UVM environment from normalized HDL specs. Use when the user needs agents, monitors, scoreboards, base tests, virtual sequences, scenario tests, or asks to split a monolithic UVM package into an RKV-style cfg/agents/env/seq_lib/tests/tb framework that stays aligned with the spec instead of the current RTL behavior.
---

# UVM Env And Test Build

Use this skill for verification code under `05_Output/uvm/` and related TB helpers under `05_Output/tb/`.

## Inputs

- `01_DocParse/structured_spec/interface_spec.yaml`
- `01_DocParse/structured_spec/register_map.yaml`
- `01_DocParse/structured_spec/test_intent.yaml`
- `01_DocParse/structured_spec/timing_rules.yaml`
- existing UVM files in `05_Output/uvm/`
- triage output when the issue is TB-side

## Workflow

1. Treat the normalized spec as the authority for expected behavior.
2. Define or update interfaces, transactions, configs, agents, monitors, and sequencers.
3. Build the scoreboard and reference model from the spec, not from the buggy DUT behavior.
4. Prefer the RKV-style framework layout when creating or refactoring non-trivial UVM code:
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
5. Create or refine:
   - environment
   - package
   - base test
   - virtual sequence base
   - scenario tests and vseqs
6. If register modeling is needed, consume outputs from `$register-spec-and-ral` or align manually with `register_map.yaml`.
7. Update `01_DocParse/trace_matrix/req_to_test.yaml`.
8. If compile or runtime evidence is needed, hand off to `$modelsim-run-triage-debug`.

## UVM Test And Coverage Strategy

Use a legal-scenario coverage strategy. Functional coverage should prove that
the intended protocol, register, FIFO, reset, parity, label, and status
behaviors were exercised with active checking. It is not a raw cross-product
scoreboard.

When building UVM tests and covergroups:

- Prefer deterministic functional sequences before broad randomization.
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
- Do not keep all classes in one large package file for a real project; use the package as a thin include hub.
- Every generated test should have a clear intent and a checker path.
- Start with baseline functional and deterministic scenarios before broad randomization.
- Keep configuration, virtual interface hookup, and scoreboard assumptions explicit.
- If the issue belongs to RTL or the spec itself, record the mismatch and route it back instead of masking it in UVM.
- Do not chase meaningless coverage bins by creating invalid stimulus or deleting checks.

## Completion Gate

This skill is complete when:

- the environment compiles in principle
- basic tests map to `test_intent.yaml`
- scoreboard ownership is clear
- known monitor or checker assumptions are documented
- functional coverage bins and crosses are tied to legal verification intent, with impossible combinations ignored or documented

## References

- Read [references/uvm-handoff-checklist.md](references/uvm-handoff-checklist.md) before handing off to simulation.
- Read [references/rkv-style-uvm-framework.md](references/rkv-style-uvm-framework.md) when creating a new maintainable UVM environment or refactoring a monolithic UVM package.
