# Agent Library

This library is the local retrieval layer for AI-assisted HDL work.

It is not a user-facing FAQ. During automated loops, the agent should query the indexes, select the most relevant IDs, then load the detailed source entry.

## Library Domains

- `rtl_templates` - reusable RTL, interface, assertion, and testbench templates.
- `fpga` - FPGA TCL commands, schematic connection patterns, UG references, workflow recipes, and diagnostic playbooks.

## Layout

```text
library/
├─ files/       Uploaded source files such as FPGA UG PDFs
├─ parsed/      MinerU outputs produced from library files
├─ indexes/     YAML indexes used to build the local SQLite database
├─ sources/     Markdown details referenced by indexes
├─ schema/      SQLite schema
└─ .local/      Generated SQLite database, ignored by Git
```

## Retrieval Contract

The agent-facing flow is:

1. Query a table of contents for the current flow, node, tool, version, or stage.
2. Select the best 1 to 2 IDs from `short_description`, `use_when`, tags, and version fields.
3. Load the detailed entry by ID.
4. Use the detailed entry to continue the loop and record the chosen ID in project memory or reports.

Large PDFs are placed under `files/fpga_ug_pdfs/`. They are local inputs and ignored by Git to avoid repository bloat. The useful extracted summaries and command records should be stored in `indexes/` and `sources/`.

## CLI

Build the SQLite index:

```powershell
python -m hdlflow.cli library-build --workspace ..
```

List entries for a flow:

```powershell
python -m hdlflow.cli get-workflow-toc --workspace .. --flow fpga.timing_analysis --tool vivado
```

Read a command:

```powershell
python -m hdlflow.cli get-command-detail --workspace .. --id vivado.report_timing_summary
```

Read a template:

```powershell
python -m hdlflow.cli get-template-detail --workspace .. --id rtl.module_header
```
