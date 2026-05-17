# 04_Loop3_FPGA_Prototype

Owns FPGA implementation and board validation.

- Run `python -m hdlflow.cli prototype-preflight --workspace <workspace> --project <project> --mode pl|ps_pl` before generating board-specific scripts.
- Run `validate-prototype-plan` before Vivado/Vitis generation. It checks AXI overlap, DDR range, PS MIO ownership, PL pin conflicts, and PS cache maintenance policy.
- Generate PL XDC through `generate-xdc` or `scripts/Generate-BoardXdc.ps1`; do not hand-copy board pins from memory.
- Generate PS_PL Block Design skeletons through `generate-ps-pl-bd` or `scripts/Generate-PsPlBd.ps1`.
- Generate FSBL/BOOT.bin packaging templates through `generate-vitis-boot` or `scripts/Generate-VitisBoot.ps1`.
- Board, Vivado/Vitis version, generated files, reports, bitstreams, serial
  logs, and board-validation evidence paths are configured in
  `config/projects/<project_name>/project_config.yaml` under
  `nodes.04_Loop3_FPGA_Prototype.prototype_policy` and `evidence`.
- `05_Output/fpga/vivado/` - Vivado project, scripts, constraints, bitstream, XSA, and implementation reports.
- `05_Output/fpga/vitis/` - Vitis workspace, platform, application sources, ELF, and software build reports.
- `05_Output/fpga/` - canonical FPGA package root.
- `scripts/` - implementation and board-test scripts.
- `_runtime/` - disposable FPGA build outputs.
- `snapshots/` - node-local implementation snapshots.
- `board_tests/` - board test plans, logs, and results.
- `05_Output/reports/loop3/preflight/` - database lookup evidence for board resources and Tcl command selection.
- `05_Output/reports/loop3/` - final timing, resource, DRC, software, serial, download, and board reports.
