# ZYNQ Core Board Pin Map V1.0

## Source

- Parsed data: `library/parsed/fpga_io_tables/zynq_core_board_pin_map/v1_0/`
- Table ID: `zynq_core_board_pin_map.v1_0`
- Retention: structured database artifacts only

## Extracted Content

- Connectors: `X3`, `X4`
- Normalized pin rows: 200
- Main PL banks:
  - `Bank35`: X3, 3.3V, 49 PL IO rows
  - `Bank34`: X4, 3.3V, 49 PL IO rows
  - `Bank13`: X4, 3.3V, 25 PL IO rows

## Agent Usage

Use `get-fpga-io-pins` to query connector pins, banks, package pins, or signal
names.

Examples:

```powershell
python -m hdlflow.cli get-fpga-io-pins --workspace .. --table-id zynq_core_board_pin_map.v1_0 --connector X3 --bank Bank35
python -m hdlflow.cli get-fpga-io-pins --workspace .. --table-id zynq_core_board_pin_map.v1_0 --signal UART
```

## Review Warnings

- The local repository retains normalized rows only, not the original PDF or
  parser workspace.
- Cells with uncertain package pins keep the original recognized text in
  `raw_zynq_pin`.
- Use this as an AI lookup database and constraint-generation aid; unresolved
  rows still need board-level review before final signoff.
