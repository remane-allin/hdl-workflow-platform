---
name: modelsim-run-triage-debug
description: Run ModelSim or Questa compile and regression loops, then classify failures and route the next fix deliberately. Use when the project has sim sources and the user needs configuration verification runs, regressions, compile-log diagnosis, sim-log diagnosis, or waveform-guided debug.
---

# ModelSim Run Triage Debug

Use this skill for evidence-driven simulation work under `02_Loop1_RTL_TB/sim/`, `03_Loop2_UVM_Verify/sim/`, and `05_Output/reports/`.

## Inputs

- `config/projects/<project_name>/project_config.yaml`
- `02_Loop1_RTL_TB/sim/*.do` or `03_Loop2_UVM_Verify/sim/*.do`
- `05_Output/rtl/`, `05_Output/tb/`, `05_Output/uvm/`
- `05_Output/reports/`
- `memory/`

## Execution Path

1. Choose the right `.do` target:
   - `compile.do` for compile-only checks
   - `baseline.do` for a focused sanity run
   - `regression.do` for broader batch work
2. Run the selected ModelSim/Questa `.do` script from the owning Loop directory.
3. Read the generated runtime log and the corresponding report under `05_Output/reports/loop1/` or `05_Output/reports/loop2/`.
4. Classify the result:
   - compile issue
   - elaboration or setup issue
   - runtime DUT issue
   - runtime TB issue
   - spec or contract mismatch
5. Route the smallest justified next action:
   - RTL-side -> `$rtl-architecture-and-gen`
   - TB/UVM-side -> `$uvm-env-and-test-build`
   - document contradiction -> `$mineru-spec-normalizer`
6. If logs are insufficient, reduce the suspect area and use waveform-guided debugging.
7. Update project memory with the latest status and next step.

## Rules

- Do not edit RTL or UVM blindly before classifying the failure.
- Keep wave dumps purposeful; trace the smallest useful set of signals first.
- Distinguish compile, elaboration, and runtime failures early.
- Repeated failures with the same signature should trigger an upstream contract review, not endless local edits.

## Completion Gate

This skill is complete when:

- a run artifact exists
- the likely failure layer is stated
- the next owner is explicit
- the project checkpoint is updated

## References

- Read [references/triage-routing.md](references/triage-routing.md) when routing failures back into the workflow.
