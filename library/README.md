# Agent Library

This library is the local retrieval layer for AI-assisted HDL, FPGA board, and
Vivado/Vitis Tcl work.

It is designed for automated loops: query indexes first, select the most
relevant IDs, then load detailed command, topic, example, or hardware records.

## Library Domains

- `rtl_templates` - reusable RTL, interface, assertion, and testbench templates.
- `fpga` - FPGA Tcl commands, schematic connection patterns, UG references,
  workflow recipes, and diagnostic playbooks.
- `eda_tcl` - Vivado/Vitis 2024.2 user-guide content for Tcl scripting,
  programming/debug, custom IP, embedded software, Vitis CLI, and PDM workflows.

## Layout

```text
library/
|-- files/       Uploaded source files such as FPGA UG PDFs
|-- work/        Temporary parser workspace, ignored and disposable
|-- parsed/      Normalized structured artifacts produced from library files
|-- indexes/     YAML indexes used to build the local SQLite database
|-- sources/     Markdown details referenced by indexes
|-- schema/      SQLite schema
`-- .local/      Generated SQLite database, ignored by Git
```

## Current Software Guide Set

The 2024.2 software database target currently covers:

| Document | Area |
| --- | --- |
| UG835 | Vivado Tcl Command Reference |
| UG894 | Vivado Tcl Scripting |
| UG908 | Vivado Programming and Debugging |
| UG1118 | Creating and Packaging Custom IP |
| UG1553 | Vitis Unified IDE and Common Command-Line Reference |
| UG1556 | Power Design Manager |
| UG1701 | Embedded Design Development Using Vitis |
| UG1702 | Vitis Reference Guide |

The generated SQLite database is local-only:

```text
library/.local/library.sqlite
```

## Retrieval Contract

The agent-facing flow is:

1. Search the focused surface for the current task.
2. Select the best 1 to 2 records from command names, titles, tags, versions,
   pages, and summaries.
3. Load detailed command or document content.
4. Use the detailed entry to write scripts, debug tool behavior, or record the
   chosen source in project memory and reports.

Large PDFs are placed under `files/fpga_ug_pdfs/`. They are local inputs and are
ignored by Git to avoid repository bloat. Temporary parser outputs belong under
`work/` and are removed after database finalization. Useful normalized command,
topic, example, and chunk records are stored in `parsed/`, `indexes/`, and
`sources/`.

See `UG_DATABASE_POLICY.md` for the multi-UG ingest, retention, and cleanup
contract.

## CLI

Run commands from the repository root after setting `PYTHONPATH`:

```powershell
$env:PYTHONPATH="engine"
$env:PYTHONIOENCODING="utf-8"
```

Build the SQLite index:

```powershell
python -m hdlflow.cli library-build --workspace .
```

Build the SQLite index and remove parser temporary outputs:

```powershell
python -m hdlflow.cli library-finalize --workspace .
```

Search Vivado Tcl commands:

```powershell
python -m hdlflow.cli search-tcl-commands --workspace . --keyword timing --limit 10
python -m hdlflow.cli search-tcl-commands --workspace . --option -file --limit 20
```

Read a Tcl command:

```powershell
python -m hdlflow.cli get-tcl-command-detail --workspace . --id report_timing_summary
```

Search UG document text, topics, and examples:

```powershell
python -m hdlflow.cli search-tcl-doc --workspace . --query "hardware manager" --limit 10
python -m hdlflow.cli search-tcl-topics --workspace . --keyword "custom IP" --limit 10
python -m hdlflow.cli search-tcl-examples --workspace . --keyword create_project --limit 10
```

Limit searches to a specific guide:

```powershell
python -m hdlflow.cli search-tcl-doc --workspace . --doc-id xilinx.ug908.2024_2 --query ILA --limit 10
```

Query FPGA board data:

```powershell
python -m hdlflow.cli get-fpga-io-pins --workspace . --signal clk --limit 20
python -m hdlflow.cli get-fpga-schematic-nets --workspace . --signal ddr --limit 20
python -m hdlflow.cli get-fpga-hardware-resource --workspace . --keyword clock --limit 20
```

Legacy workflow and template lookups are still available:

```powershell
python -m hdlflow.cli get-workflow-toc --workspace . --flow fpga.timing_analysis --tool vivado
python -m hdlflow.cli get-command-detail --workspace . --id vivado.report_timing_summary
python -m hdlflow.cli get-template-detail --workspace . --id rtl.module_header
```
