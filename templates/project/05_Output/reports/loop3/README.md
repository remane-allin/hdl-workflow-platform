# Loop3 Reports

- [Report index](../README.md)
- [FPGA package area](../../fpga/)
- [Prototype node](../../../04_Loop3_FPGA_Prototype/)
- [Preflight evidence](preflight/)

## Required Loop3 Outputs

- `preflight/database_preflight.md`: generated local-library evidence for board resources and Tcl guidance.
- `preflight/prototype_plan_check.md`: generated prototype-plan validation report.
- `vivado_implementation_report.md`: synthesis/implementation, bitstream, and XSA evidence.
- `timing_drc_report.md`: timing, DRC, unconstrained-path, and waiver evidence.
- `vitis_boot_report.md`: platform, application, ELF, and BOOT.bin packaging evidence when PS software is in scope.
- `board_smoke_report.md`: download, serial, LED/GPIO, DDR, and board-observed behavior evidence.
- `loop3_exit_report.md`: gate-level conclusion for Loop3.

Loop3 must start from the database preflight and prototype plan check. Do not
close Loop3 from hand-copied pin notes, stale Vivado artifacts, or board logs
that cannot be traced back to the signed Loop2 RTL.

Use the `.template` files in this directory as the required report shape. Do
not rename a template to `.md` until the evidence fields are filled from a fresh
prototype run.
