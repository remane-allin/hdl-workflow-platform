# Loop1 Waveform Deliverables

This directory is the canonical Loop1 waveform handoff.

- `<tb_top>.wlf` - ModelSim-native waveform database.
- `<tb_top>_top.vcd` - top-level VCD consumed by `loop1-waveform-check`.

Waveform analysis must read these files in place. Do not create secondary VCD/WLF copies for AI analysis.

The VCD should preserve module scopes. The generated hierarchy index lives under
`output/reports/loop1/waveform_hierarchy.json`.
