# Parsed FPGA Schematics

Parsed FPGA schematic outputs belong here.

Suggested layout:

```text
fpga_schematics/
└─ <board_or_project>/
   └─ <revision>/
      ├─ metadata.yaml
      ├─ sheets.yaml
      ├─ nets.yaml
      ├─ interfaces.yaml
      ├─ power_tree.yaml
      ├─ clock_reset.yaml
      └─ review_notes.md
```

Use this area for extracted schematic evidence. Keep raw PDFs under `library/files/fpga_schematics/`.
