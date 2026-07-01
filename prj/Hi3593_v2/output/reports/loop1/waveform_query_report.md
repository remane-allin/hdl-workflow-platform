# Loop1 Waveform Query Gate

- project: Hi3593_v2
- generated_at: 2026-06-30T22:29:08
- result: PASS
- manifest: work/loop1_rtl_tb/config/top_wave_manifest.yaml
- backend: pywellen
- vcd: output/sim/loop1/wave/loop1_tb_top.vcd
- wlf: output/sim/loop1/wave/loop1_tb.wlf
- dut_scope: /loop1_tb/dut
- transcript: output/reports/loop1/query_transcript.json

## Gate Checks

| Check | Status | Detail |
| --- | --- | --- |
| top_wave_manifest_exists | PASS | work/loop1_rtl_tb/config/top_wave_manifest.yaml |
| top_wave_manifest_parse | PASS | manifest parsed |
| top_waveform_exists | PASS | vcd=output/sim/loop1/wave/loop1_tb_top.vcd; wlf=output/sim/loop1/wave/loop1_tb.wlf |
| waveform_backend_loaded | PASS | backend=pywellen; signals=137; windows=11 |
| manifest_matched | PASS | matched 19/19 required manifest signals |
| dump_scope_is_top_only | PASS | DUT dump contains only top-level port signals |
| dump_duration_within_limit | PASS | max_dump_duration=100000000; max_file_size_mb=50.0 |
| query_interface_pass | PASS | query interface listed scopes and resolved required ports |
| wave_window:reset_release:required_ports_present | PASS | all required signals resolved |
| wave_window:reset_release:no_xz | PASS | no X/Z values observed |
| wave_window:reset_release:clock_edges_present | PASS | ACLK transitions=17 |
| wave_window:reset_release:non_clock_activity | PASS | non-clock transitions=1 |
| wave_window:spi_opcode_activity:required_ports_present | PASS | all required signals resolved |
| wave_window:spi_opcode_activity:no_xz | PASS | no X/Z values observed |
| wave_window:spi_opcode_activity:clock_edges_present | PASS | ACLK transitions=751 |
| wave_window:spi_opcode_activity:input_event_exists | PASS | input transitions=230 |
| wave_window:rx_location32_overwrite:required_ports_present | PASS | all required signals resolved |
| wave_window:rx_location32_overwrite:no_xz | PASS | no X/Z values observed |
| wave_window:rx_location32_overwrite:clock_edges_present | PASS | ACLK transitions=2997 |
| wave_window:rx_location32_overwrite:input_event_exists | PASS | input transitions=701 |
| wave_window:rx_location32_overwrite:output_response_exists | PASS | output transitions=2 |
| wave_window:arinc_tx_response:required_ports_present | PASS | all required signals resolved |
| wave_window:arinc_tx_response:no_xz | PASS | no X/Z values observed |
| wave_window:arinc_tx_response:clock_edges_present | PASS | ACLK transitions=717 |
| wave_window:arinc_tx_response:output_response_exists | PASS | output transitions=21 |
| waveform_analysis_pass | PASS | 17/17 waveform query checks passed |

## Errors

- none

## Warnings

- none
