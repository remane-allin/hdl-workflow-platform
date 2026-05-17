# Parsed FPGA Schematics

Curated FPGA schematic database artifacts belong here.

Suggested layout:

```text
fpga_schematics/
`-- <board_or_project>/
    `-- <revision>/
        |-- metadata.yaml
        |-- sheets.yaml
        |-- nets.yaml
        |-- interfaces.yaml
        |-- power_tree.yaml
        |-- clock_reset.yaml
        `-- review_notes.md
```

Use this area for extracted schematic evidence that is already normalized for
database lookup. Raw schematic PDFs and parser workspaces are not retained here.
