# Loop3 Vivado PS/PL Run

- project: Hi3593_v2
- board: navigator_zynq_7020
- part: xc7z020clg400-2
- mode: ps_pl
- top_module: hi3593_v2_proto_top
- serial_path: PS software over PS UART0 MIO 14..15 / COM3; AXI UARTLite remains a PL peripheral only
- bitstream: output/fpga/vivado/bitstream/hi3593_v2_ps_pl.bit
- timing_report: output/fpga/vivado/reports/post_impl_timing_summary.rpt
- drc_report: output/fpga/vivado/reports/post_impl_drc.rpt
- result: PASS

## Database and UG Provenance

ug_flow_guard: PASS
vivado_tcl_source: local software UG/Tcl database
database_preflight: output/reports/loop3/preflight/database_preflight.md
prototype_plan_check: output/reports/loop3/preflight/prototype_plan_check.md
