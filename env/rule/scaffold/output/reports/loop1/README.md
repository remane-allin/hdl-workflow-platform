# Loop1 Reports

- [Report index](../README.md)
- [RTL source](../../rtl/)
- [Directed TB source](../../tb/)

## Required Loop1 Outputs

- `loop1_rtl_tb_run_report.md`: evidence from the latest directed RTL/TB run.
- `waveform_check.md` / `waveform_check.json`: machine waveform verification
  from marked Loop1 VCD windows under `output/sim/loop1/wave/`.
- `waveform_hierarchy.md` / `waveform_hierarchy.json`: VCD signal grouping by
  module scope for waveform-guided analysis.
- `loop1_exit_report.md`: gate-level conclusion for Loop1.

Use these template files only as report shape references. Final `.md` reports
must be generated or refreshed from the latest Loop1 RTL/TB run; do not promote
an unfilled template into final evidence.
