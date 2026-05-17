# 02_Loop1_RTL_TB

Owns RTL implementation and directed functional verification.

- `05_Output/rtl/` - canonical editable RTL source.
- `05_Output/tb/` - canonical editable directed self-checking testbenches.
- `sim/` - filelists, compile scripts, and regression scripts for Loop1.
- `_runtime/` - disposable compile, wave, and log outputs.
- `snapshots/` - node-local iteration snapshots.
- `issue_tracking/` - Loop1 issue and fix records.
- `05_Output/reports/loop1/` - final Loop1 reports.

Language hard rule: RTL under `05_Output/rtl/` and directed Loop1 TB under
`05_Output/tb/` are Verilog-2001 `.v` files only. Do not place
SystemVerilog `.sv` or `.svh` files in either directory. SystemVerilog belongs
under `05_Output/uvm/` for Loop2.

RTL hard rule: the project has exactly one selected top module, and that top module is hierarchy-only. Put reset generation, protocol control, datapath, CDC, and board/application behavior in named submodules instantiated by the top.

Do not keep editable RTL/TB source trees under this node; the canonical code is in `05_Output`.
