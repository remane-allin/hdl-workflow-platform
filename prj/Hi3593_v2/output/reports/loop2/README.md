# Loop2 Reports

- [Report index](../README.md)
- [RTL source](../../rtl/)
- [UVM source](../../uvm/)
- [Loop2 database preflight](preflight/database_preflight.md)
- [Loop2 binding database](../../../work/loop2_uvm/_runtime/loop2_bindings.sqlite)

## Current Run Contract

- User-facing report: `loop2_report.md`
- Machine report: `loop2_report.json`
- Report manifest: `loop2_report_manifest.json`
- Command record: `../../../work/loop2_uvm/current/cmd/command.json`
- Current log: `../../../work/loop2_uvm/current/log/modelsim.log`
- Optional raw coverage: `../../../work/loop2_uvm/current/log/coverage_raw.txt`
- Current run manifest: `../../../work/loop2_uvm/current/manifest.json`

`loop2_report.md` is generated from structured `HDLFLOW|UVM_CHECK|...` and
`HDLFLOW|UVM_SUMMARY|...` events. Do not hand edit it, and do not store raw
simulator logs under `output/reports/loop2/`.
