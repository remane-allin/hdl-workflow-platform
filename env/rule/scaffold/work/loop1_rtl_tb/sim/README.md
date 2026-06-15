# Loop1 ModelSim Scripts

Use these project-local entries for directed RTL/TB verification:

```tcl
do compile.do
do rtl_functional.do
```

`rtl_functional.do` defaults to a TB top named `loop1_tb`. Project scripts may
override before running:

```tcl
set loop1_tb_tops [list my_unit_tb my_top_tb]
do rtl_functional.do
```

The same entry captures top-level waveform evidence into the canonical output
deliverable directory `output/sim/loop1/wave/`:

- `<tb_top>.wlf`: ModelSim-native waveform database for human debug.
- `<tb_top>_top.vcd`: bounded top-level VCD for machine checks.

The default DUT instance under the TB is `dut`. Override it before the run when
the TB uses another instance name:

```tcl
set loop1_dut_instance u_dut
set loop1_wave_extra_groups [list [list rx_core /my_top_tb/u_dut/u_rx/* 1]]
set loop1_wave_extra_signals [list /my_top_tb/u_dut/internal_state]
do rtl_functional.do
```

The generated VCD is parsed through the recommended `pywellen` backend by the
manifest-driven top-port query gate.

After `loop1-refresh-reports`, the script runs
`python -m hdlflow.cli loop1-waveform-gate --project <project> --manifest
work/loop1_rtl_tb/config/top_wave_manifest.yaml`. Loop1 develop/release cannot
exit unless `waveform_query_report.md`, `waveform_gate.json`, and
`query_transcript.json` are valid.

Waveform analysis must use the VCD/WLF files in `output/sim/loop1/wave/`
directly. Do not make secondary analysis copies under `work/_runtime`.

The template fails when RTL or TB sources are missing, so Loop1 cannot report a
false pass.
