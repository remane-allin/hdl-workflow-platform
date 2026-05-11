# Parsed FPGA IO Tables

Normalized FPGA IO table outputs belong here.

Suggested layout:

```text
fpga_io_tables/
└─ <board_or_project>/
   └─ <version>/
      ├─ metadata.yaml
      ├─ pins.yaml
      ├─ banks.yaml
      ├─ interfaces.yaml
      └─ constraints_notes.md
```

Use this area for parsed and normalized tables. Keep project-specific source spreadsheets in `library/files/fpga_io_tables/` until they are reviewed and converted.
