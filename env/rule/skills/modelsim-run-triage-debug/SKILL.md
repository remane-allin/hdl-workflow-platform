---
name: modelsim-run-triage-debug
description: Run ModelSim or Questa compile and regression loops, then classify failures and route the next fix deliberately. Use when the project has sim sources and the user needs configuration verification runs, regressions, compile-log diagnosis, sim-log diagnosis, or waveform-guided debug.
---

# ModelSim Run Triage Debug

Use this skill for evidence-driven simulation work under `work/loop1_rtl_tb/sim/`, `work/loop2_uvm/sim/`, and `output/reports/`.

## Inputs

- `prj/<project_name>/work/config/project_config.yaml`
- `work/loop1_rtl_tb/sim/*.do` or `work/loop2_uvm/sim/*.do`
- `output/rtl/`, `output/tb/`, `output/uvm/`
- `output/reports/`
- `work/memory/`

## Execution Path

1. Choose the right `.do` target:
   - `compile.do` for compile-only checks
   - `baseline.do` for a focused sanity run
   - `regression.do` for broader batch work
2. Run the selected ModelSim/Questa `.do` script from the owning Loop directory.
3. Read the generated runtime log and the corresponding report under `output/reports/loop1/` or `output/reports/loop2/`.
4. Treat the simulator log as the report source. Loop1 reports must be regenerated from `HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|...` plus `HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|...`; Loop2 reports must be regenerated from `HDLFLOW|UVM_CHECK|schema=hdlflow_event_v1|version=1|stage=loop2|...` plus `HDLFLOW|UVM_SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop2|...`. Do not hand-edit generated reports.
   For Loop1, `rtl_functional.do` must also record WLF/VCD evidence under `output/sim/loop1/wave`, emit `HDLFLOW_WAVE_GROUP` scope markers, pass `work/loop1_rtl_tb/config/top_wave_manifest.yaml`, and run `loop1-waveform-gate` after `loop1-refresh-reports`.
5. Classify the result:
   - compile issue
   - elaboration or setup issue
   - runtime DUT issue
   - runtime TB issue
   - spec or contract mismatch
6. Route the smallest justified next action:
   - RTL-side -> `$rtl-architecture-and-gen`
   - TB/UVM-side -> `$uvm-env-and-test-build`
   - document contradiction -> `$requirements-frontdoor` or `$hdl-requirements-decompose`
7. If logs are insufficient, reduce the suspect area and use waveform-guided debugging.
8. Update project memory with the latest status and next step.

## Rules

- Do not edit RTL or UVM blindly before classifying the failure.
- Keep wave dumps purposeful; trace the smallest useful set of signals first.
- Loop1 waveform capture starts at the TB top and DUT top-level ports. Add `loop1_wave_extra_signals` only when the top-level VCD window fails and a deeper suspect must be isolated.
- Use `loop1_wave_extra_groups` for deeper hierarchy capture when needed. Each item is `{name scope recursive}`, for example `{rx_core /loop1_tb/dut/u_rx/* 1}`.
- Treat `output/sim/loop1/wave` as the canonical waveform deliverable. Analyze the VCD/WLF there in place; do not create a second copy under `_runtime` for AI analysis.
- Treat `output/reports/loop1/waveform_query_report.md`, `output/reports/loop1/waveform_gate.json`, and `output/reports/loop1/query_transcript.json` as advisory structured waveform evidence. Pywellen is the extractor; the deterministic signal-rule engine writes the PASS/FAIL fields in `waveform_gate.json`. AI/MCP may explain or extract context, but it must not be the Loop1 pass/fail judge.
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
