# work/loop1_rtl_tb

Owns RTL implementation and directed functional verification.

- `output/rtl/` - canonical editable RTL source.
- `output/tb/` - canonical editable directed self-checking testbenches.
- `output/tb/full_function_test_plan.md` - TB-owned directed full-function test plan.
- `sim/` - filelists, compile scripts, and regression scripts for Loop1.
- `_runtime/` - disposable compile work libraries and temporary simulator outputs.
- `snapshots/` - node-local iteration snapshots.
- `issue_tracking/` - Loop1 issue and fix records.
- `output/reports/loop1/` - final Loop1 reports.

Language hard rule: RTL under `output/rtl/` and directed Loop1 TB under
`output/tb/` are Verilog-2001 `.v` files only. Do not place
SystemVerilog `.sv` or `.svh` files in either directory. SystemVerilog belongs
under `output/uvm/` for Loop2.

RTL hard rule: the project has exactly one selected top module, and that top module is hierarchy-only. Put reset generation, protocol control, datapath, CDC, and board/application behavior in named submodules instantiated by the top.

Do not keep editable RTL/TB source trees under this node; the canonical code is in `output`.

Loop1 waveform rule: after directed function checks pass, the TB must emit
`HDLFLOW_WAVE_BEGIN`/`HDLFLOW_WAVE_END` or `HDLFLOW_WAVE_WINDOW` markers for the
verified spans. `sim/rtl_functional.do` records WLF/VCD evidence under
`output/sim/loop1/wave/`, and the
`loop1_waveform_check` gate validates those windows before Loop2 may start.
`waveform_hierarchy.json` groups captured VCD signals by module scope for
waveform-guided review.
