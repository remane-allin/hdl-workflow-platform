# Library Files

This workspace is parsed-database-first. Raw source PDFs and uploaded parser
inputs are staged here only while they are being reviewed and normalized.

Keep only placeholder README files in this tree unless a workflow explicitly
records a reviewed source-file retention policy.

## Staging Areas

- `fpga_io_tables/` - source IO tables before normalization.
- `fpga_schematics/` - source schematic documents before normalization.
- `fpga_ug_pdfs/` - FPGA/Vivado/Vitis guide PDFs before normalization.
- `rtl_template_uploads/` - uploaded RTL template packs before review.
- `uvm_guides/` - UVM PDF/DOC/HTML guide inputs before MinerU parsing.
- `uvm_template_uploads/` - UVM reference projects, template packs, or code
  bundles before review and conversion into reusable source entries.

Reviewed and normalized outputs should move to `lib/parsed/`,
`lib/sources/`, and `lib/indexes/`, then be indexed into the local
SQLite database with `hdlflow library-build`.
