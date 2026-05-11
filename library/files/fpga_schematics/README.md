# FPGA Schematic PDF Inbox

Place FPGA board schematic PDFs and schematic exports here.

Recommended naming:

```text
<board_or_project>_schematic_<revision>.<ext>
```

Examples:

```text
zynq_core_board_schematic_rev_a.pdf
prototype_carrier_schematic_v1_2.pdf
```

Raw schematic PDFs are local inputs and are ignored by Git. After parsing, put extracted structure under `library/parsed/fpga_schematics/` and curated reusable connection guidance under `library/sources/schematic_patterns/`.
