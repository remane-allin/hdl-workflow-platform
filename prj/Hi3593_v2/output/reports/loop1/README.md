# Loop1 Reports

- [Report index](../README.md)
- [RTL source](../../rtl/)
- [Directed TB source](../../tb/)

## Current Run Contract

- User-facing report: `loop1_report.md`
- Machine report: `loop1_report.json`
- Report manifest: `loop1_report_manifest.json`
- Command record: `../../../work/loop1_rtl_tb/current/cmd/command.json`
- Current log: `../../../work/loop1_rtl_tb/current/log/modelsim.log`
- Current run manifest: `../../../work/loop1_rtl_tb/current/manifest.json`
- Waveform query gate: `waveform_query_report.md` / `waveform_gate.json`
- Waveform query transcript: `query_transcript.json`
- Waveforms: `../../sim/loop1/wave/*.wlf`, `../../sim/loop1/wave/*.vcd`

`loop1_report.md` is generated from structured `HDLFLOW|CHECK|...` and
`HDLFLOW|SUMMARY|...` events. Do not hand edit it, and do not store raw
simulator logs under `output/reports/loop1/`.
