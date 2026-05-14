# Loop2 Reports

- [Report index](../README.md)
- [RTL source](../../rtl/)
- [UVM source](../../uvm/)
- [Loop2 database preflight](preflight/database_preflight.md)
- [Loop2 binding database](../../../03_Loop2_UVM_Verify/_runtime/loop2_bindings.sqlite)

## Required Loop2 Outputs

- `loop2_uvm_baseline_report.md`: deterministic UVM baseline evidence.
- `loop2_uvm_regression_report.md`: full UVM regression, coverage, scoreboard,
  and assertion evidence.
- `coverage_index.md`: coverage summary and waiver links.
- `loop2_exit_report.md`: gate-level conclusion for Loop2.
- `preflight/database_preflight.md`: template-library database evidence, aligned
  with the Loop3 database preflight pattern.

Loop2 is a UVM closure loop. Directed RTL/TB regression may be referenced as
supporting evidence, but it cannot by itself satisfy `loop2_exit_report.md`.

Use the `.template` files in this directory as the required report shape. Do
not rename a template to `.md` until the evidence fields are filled from a fresh
UVM run.
