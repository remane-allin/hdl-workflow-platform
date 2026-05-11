# ZYNQ Core Board IO Table Notes

- table_id: `zynq_core_board_pin_map.v1_0`
- source: `library/files/fpga_io_tables/ZYNQ????????V1.0.pdf`
- connectors: X3, X4
- normalized pins: 200

## Use In Loop3

Use this normalized table when generating or checking FPGA pin constraints, board interface notes, or schematic connectivity assumptions.

## Review Warnings

- OCR/flash extraction preserved uncertain package pin cells in `raw_zynq_pin`; verify cells where `zynq_pin` is null but the signal is not power, ground, or unused.
- Bank voltages are inferred from signal naming and source summary text; confirm against the schematic and device package before signoff.
- This database is a lookup aid for AI loops, not final board signoff evidence.

## Generated Files

- `metadata.json` / `metadata.yaml`
- `pins.json` / `pins.yaml`
- `banks.json` / `banks.yaml`
- `interfaces.json` / `interfaces.yaml`
