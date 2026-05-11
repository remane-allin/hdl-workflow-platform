# 02_Loop1_RTL_TB

Owns RTL implementation and directed functional verification.

- `05_Output/rtl/` - canonical editable RTL source.
- `05_Output/tb/` - canonical editable directed self-checking testbenches.
- `sim/` - filelists, compile scripts, and regression scripts for Loop1.
- `_runtime/` - disposable compile, wave, and log outputs.
- `snapshots/` - node-local iteration snapshots.
- `issue_tracking/` - Loop1 issue and fix records.
- `05_Output/reports/loop1/` - final Loop1 reports.

Do not keep editable RTL/TB source trees under this node; the canonical code is in `05_Output`.
