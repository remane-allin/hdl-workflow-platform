# Parsed Library Sources

Normalized outputs from library source files belong here.

This area is separate from project document parsing. Do not place project requirement parses here.

- `fpga_ug_mineru/` - normalized FPGA UG database artifacts.
- `fpga_io_tables/` - normalized FPGA IO tables and pin/bank summaries.
- `fpga_schematics/` - parsed FPGA schematic PDFs and extracted nets/interfaces.

Raw parser output is temporary. Keep it under `library/work/` while ingesting, then run `library-finalize` to rebuild SQLite and remove temporary parser files.
