# Loop2 ModelSim Scripts

This directory is the project-local Loop2 entry point copied into every new
`Test` project.

Use:

```tcl
do compile.do
do uvm_full_functional.do
do regression.do
```

`uvm_full_functional.do` is the Loop2 entry check. It verifies that the project
UVM framework compiles and can run the configured test, but it is not final
Loop2 signoff evidence. The final handoff evidence comes from `regression.do`
and the Loop2 reports.

Every `regression.do` run overwrites the current Loop2 final reports from the
latest `modelsim_loop2.log` and coverage data:

- `05_Output/reports/loop2/loop2_uvm_regression_report.md`
- `05_Output/reports/loop2/coverage_index.md`
- `05_Output/reports/loop2/loop2_exit_report.md`

`uvm_full_functional.do` expects generated UVM files under `05_Output/uvm`:

- `tb/tb_dut_if.sv`
- `env/uvm_pkg.sv`
- `tb/tb_uvm.sv`

Project-specific scripts may override these variables before calling
`uvm_full_functional.do`:

- `uvm_if_file`
- `uvm_pkg_file`
- `uvm_tb_top_file`
- `uvm_sva_file`
- `uvm_tb_top`
- `uvm_test_name`
- `uvm_seed_count`

The template deliberately fails if the project UVM sources are still missing,
so Loop2 cannot report a false pass.
