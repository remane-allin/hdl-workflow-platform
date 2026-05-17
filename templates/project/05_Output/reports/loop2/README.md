# Loop2 Reports

- [Report index](../README.md)
- [RTL source](../../rtl/)
- [UVM source](../../uvm/)
- [Loop2 database preflight](preflight/database_preflight.md)
- [Loop2 binding database](../../../03_Loop2_UVM_Verify/_runtime/loop2_bindings.sqlite)

## Required Loop2 Outputs

- `loop2_uvm_regression_report.md`: full UVM regression, coverage, scoreboard,
  and assertion evidence.
- `coverage_index.md`: coverage summary and waiver links.
- `loop2_exit_report.md`: gate-level conclusion for Loop2.
- `preflight/database_preflight.md`: template-library database evidence, aligned
  with the Loop3 database preflight pattern.

The Loop2 entry check is not final evidence. After the full functional
regression passes, do not keep a separate entry-check report in
`05_Output/reports/loop2/`; final Loop2 evidence is the regression report,
coverage index, exit report, binding database, and preflight/database evidence.

The three final Markdown reports are current-run artifacts. Each full
functional `regression.do` run must overwrite them from the latest simulator log
and coverage output; do not append new runs into old reports.

Loop2 is a UVM closure loop. Directed RTL/TB regression may be referenced as
supporting evidence, but it cannot by itself satisfy `loop2_exit_report.md`.

Use these template files only as report shape references. Final `.md` reports
must be generated or refreshed from the latest full functional UVM run; do not
promote an unfilled template into final evidence.
