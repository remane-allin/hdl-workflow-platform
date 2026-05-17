# Agent Library

This library is the local retrieval layer for AI-assisted HDL, FPGA board, and
Vivado/Vitis Tcl work.

The library is parsed-database-only: normal operation consumes normalized
artifacts under `parsed/`, YAML indexes under `indexes/`, Markdown details under
`sources/`, and the generated SQLite database under `.local/`.

## Layout

```text
library/
|-- parsed/      Normalized structured artifacts
|-- indexes/     YAML indexes used to build the local SQLite database
|-- sources/     Markdown details referenced by indexes
|-- schema/      SQLite schema
`-- .local/      Generated SQLite database, ignored by Git
```

`library/files/` may contain README placeholders only. Raw PDFs and parser
workspaces are not retained in this workspace.

## Build

Build the SQLite index from normalized artifacts:

```powershell
python -m hdlflow.cli library-build --workspace .
```

## Query

```powershell
python -m hdlflow.cli search-tcl-commands --workspace . --keyword timing --limit 10
python -m hdlflow.cli get-tcl-command-detail --workspace . --id report_timing_summary
python -m hdlflow.cli search-tcl-doc --workspace . --query "hardware manager" --limit 10
python -m hdlflow.cli get-fpga-io-pins --workspace . --signal clk --limit 20
python -m hdlflow.cli get-fpga-schematic-nets --workspace . --net ddr --limit 20
python -m hdlflow.cli get-fpga-hardware-resource --workspace . --keyword clock --limit 20
```

