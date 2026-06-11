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

The generated VCD preserves module scopes. `loop1-waveform-check` converts that
scope tree into `output/reports/loop1/waveform_hierarchy.json` and
`waveform_hierarchy.md`, so AI analysis can choose a hierarchy group before
querying detailed signal activity.

After `loop1-refresh-reports`, the script runs
`python -m hdlflow.cli loop1-waveform-check --project <project>`. Loop1 cannot
exit unless `output/reports/loop1/waveform_check.json` and the hierarchy index
are valid.

Waveform analysis must use the VCD/WLF files in `output/sim/loop1/wave/`
directly. Do not make secondary analysis copies under `work/_runtime`.

The template fails when RTL or TB sources are missing, so Loop1 cannot report a
false pass.
