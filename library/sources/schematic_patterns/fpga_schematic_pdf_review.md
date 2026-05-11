# FPGA Schematic PDF Review

## Use When

Use this entry when a board schematic PDF is uploaded for FPGA prototype work.

## Agent Procedure

1. Identify board/project name, schematic revision, page count, and source PDF path.
2. Parse schematic sheets into page-level notes.
3. Extract FPGA-related nets, connectors, clocks, resets, power rails, configuration pins, JTAG pins, and high-speed or differential interfaces.
4. Cross-check extracted nets against available IO tables.
5. Record unresolved OCR or symbol ambiguity in `review_notes.md`.
6. Store parsed structure under `library/parsed/fpga_schematics/<board>/<revision>/`.
7. Link reusable connection patterns back into `connection_index.yaml` only after review.

## Expected Parsed Files

```text
metadata.yaml
sheets.yaml
nets.yaml
interfaces.yaml
power_tree.yaml
clock_reset.yaml
review_notes.md
```

## Notes

Raw schematic PDFs stay in `library/files/fpga_schematics/`. Parsed raw MinerU output should stay local unless it is compact and intentionally curated.
