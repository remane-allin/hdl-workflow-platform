# FPGA IO Table Review

## Use When

Use this entry when an FPGA IO table, pin spreadsheet, or board interface table is uploaded for prototype work.

## Agent Procedure

1. Identify device part, package, board revision, and table version.
2. Normalize pins into signal name, FPGA pin, bank, IO standard, voltage, direction, and interface group.
3. Check that related signals share consistent bank voltage and IO standard assumptions.
4. Flag missing clocks, resets, JTAG/configuration pins, differential pair mates, and unconstrained pins.
5. Generate or update constraint notes for Loop3.
6. Link parsed outputs from `library/parsed/fpga_io_tables/` into the relevant project memory or report when used.

## Expected Parsed Files

```text
metadata.yaml
pins.yaml
banks.yaml
interfaces.yaml
constraints_notes.md
```

## Notes

Raw spreadsheets stay in `library/files/fpga_io_tables/`. Curated reusable connection guidance should be summarized here or in a related schematic pattern entry.
