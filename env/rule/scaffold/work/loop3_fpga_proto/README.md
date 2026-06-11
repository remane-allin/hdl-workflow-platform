# work/loop3_fpga_proto

Owns FPGA implementation and board validation.

- Run `python -m hdlflow.cli prototype-preflight --workspace <workspace> --project <project> --mode pl|ps_pl` before generating board-specific scripts.
- Run `validate-prototype-plan` before Vivado/Vitis generation. It checks AXI overlap, DDR range, PS MIO ownership, PL pin conflicts, and PS cache maintenance policy.
- Generate PL XDC through `generate-xdc` or `env/tool/scripts/Generate-BoardXdc.ps1`; do not hand-copy board pins from memory.
- Generate PS_PL Block Design Tcl through `generate-ps-pl-bd` or `env/tool/scripts/Generate-PsPlBd.ps1`.
- PS_PL BD generation is database/UG gated: it re-checks local Vivado Tcl rows, Vitis guide topics, `database_preflight.md`, `prototype_plan_check.md`, and the board PS7 preset Tcl before writing the BD script.
- PS_PL and bus-protocol stimulus must be external to synthesizable PL RTL. PS software, testbench BFMs, or serial scripts own command/message bytes; RTL may expose registers, handshakes, and serializers only.
- Generate FSBL/BOOT.bin packaging templates through `generate-vitis-boot` or `env/tool/scripts/Generate-VitisBoot.ps1`.
- Run board serial verification through `env/tool/scripts/Invoke-HdlLoop3BoardVerify.ps1`; do not add project-local ad hoc board verification scripts.
- Refresh canonical Loop3 signoff reports through `python -m hdlflow.cli loop3-refresh-reports --project <project>` before running the Loop3 gate.
- Board, Vivado/Vitis version, generated files, reports, bitstreams, serial
  logs, and board-validation evidence paths are configured in
  `prj/<project_name>/work/config/project_config.yaml` under
  `nodes.work/loop3_fpga_proto.prototype_policy` and `evidence`.
- `output/fpga/vivado/` - Vivado project, scripts, constraints, bitstream, XSA, and implementation reports.
- `output/fpga/vitis/` - Vitis workspace, platform, application sources, ELF, and software build reports.
- `output/fpga/` - canonical FPGA package root.
- `env/tool/scripts/` - implementation and board-test scripts.
- `_runtime/` - disposable FPGA build outputs.
- `snapshots/` - node-local implementation snapshots.
- `board_tests/` - board test plans, logs, and results.
- `output/reports/loop3/preflight/` - database lookup evidence for board resources and Tcl command selection.
- `output/reports/loop3/` - final timing, resource, DRC, software, serial, download, and board reports.
