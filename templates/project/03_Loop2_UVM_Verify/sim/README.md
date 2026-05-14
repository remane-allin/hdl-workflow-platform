# Loop2 ModelSim Scripts

This directory is the project-local Loop2 entry point copied into every new
`Test` project.

Use:

```tcl
do compile.do
do uvm_baseline.do
do regression.do
```

`uvm_baseline.do` expects instantiated UVM files under `05_Output/uvm`:

- `tb/tb_dut_if.sv`
- `env/uvm_pkg.sv`
- `tb/tb_uvm.sv`

Project-specific scripts may override these variables before calling
`uvm_baseline.do`:

- `uvm_if_file`
- `uvm_pkg_file`
- `uvm_tb_top_file`
- `uvm_sva_file`
- `uvm_tb_top`
- `uvm_test_name`
- `uvm_seed_count`

The template deliberately fails if the project UVM sources are still missing,
so Loop2 cannot report a false pass.
