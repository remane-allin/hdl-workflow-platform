# Loop1 Waveform Deliverables

This directory is the canonical Loop1 waveform handoff.

- `<tb_top>.wlf` - ModelSim-native waveform database.
- `<tb_top>_top.vcd` - top-level VCD consumed by `loop1-waveform-gate`.

Waveform analysis must read these files in place. Do not create secondary VCD/WLF copies for AI analysis.

The VCD should expose only the DUT top-level observability requested by
`work/loop1_rtl_tb/config/top_wave_manifest.yaml`.
