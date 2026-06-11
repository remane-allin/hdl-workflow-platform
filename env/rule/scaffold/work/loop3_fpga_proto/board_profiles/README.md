# Board Profiles

Put project-selected board profiles here when Loop3 targets a real board.

The platform default board is `navigator_zynq_7020` with Vivado/Vitis library
version `2024.2`. Select another active board in
`prj/<project_name>/work/config/project_config.yaml` under
`nodes.work/loop3_fpga_proto.prototype_policy.selected_board`, or pass
`--board` to `prototype-preflight`.

PS_PL flows must provide `<board>_ps7_preset.tcl`; `generate-ps-pl-bd` refuses
to emit a BD script without that reviewed DDR/MIO preset and PASS database
preflight evidence.
