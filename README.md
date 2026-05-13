# HDL Workflow Platform

HDL Workflow Platform is a reusable workspace scaffold for HDL projects and
AI-assisted FPGA development. It standardizes how requirements, parsed
documents, RTL, testbenches, UVM verification, FPGA prototype work, reports,
and final deliverables are organized.

The current library also contains a structured Vivado/Vitis 2024.2 software
reference layer for Tcl script generation, command lookup, and debug workflows.
The generated SQLite database is local-only, while the schema, ingest code,
indexes, and normalized artifacts are versioned so the database can be rebuilt.

## Why This Exists

HDL projects often become hard to maintain when source files, generated files,
reports, logs, and temporary tool outputs are mixed together. This platform
keeps those concerns separated:

- Global rules live in one configuration tree.
- Each project instance lives under its own project directory.
- Pipeline stages are numbered and ordered.
- Memory records are indexed and separated into permanent archive, local
  transient notes, and recovery evidence.
- Design changes use a controlled request, impact, approval, and trace-update
  flow.
- Gate rules can distinguish debug, develop, and release levels.
- Runtime outputs stay disposable.
- Final deliverables stay in one canonical output area.

## Repository Contents

```text
config/      Global rules and project configuration templates
engine/      Python CLI and PowerShell hooks for workflow validation
library/     Agent-facing RTL, FPGA hardware, Vivado, and Vitis reference library
skills/      HDL workflow skill definitions for AI-assisted work
templates/   Standard HDL project skeleton
projects/    Local project workspace, ignored for concrete project contents
.codex/      Project-local Codex hooks and prompt fragments
```

## Project Creation Rule

`templates/` is the template project source. Directories under `projects/`
must be created by the unified workflow script entry point, not by manually
creating folders or copying files. Use `scripts/New-HdlProject.ps1` first, then
add project-specific RTL, TB, FPGA, software, reports, and scripts under the
created project. Each generated project carries `project_scaffold.yaml`; project
validation treats that marker as required evidence that the script path was used.

## Project Layout

Every project created from the template follows this structure:

```text
<project_name>/
|-- memory/
|-- 00_SPEC/
|-- 01_DocParse/
|-- 02_Loop1_RTL_TB/
|-- 03_Loop2_UVM_Verify/
|-- 04_Loop3_FPGA_Prototype/
|-- 05_Output/
`-- _archive/
```

The intended flow is:

```text
00_SPEC -> 01_DocParse -> 02_Loop1_RTL_TB -> 03_Loop2_UVM_Verify -> 04_Loop3_FPGA_Prototype -> 05_Output
```

`05_Output/` is the canonical editable deliverable area. It is where RTL, TB,
UVM, FPGA files, final reports, and manifests converge after review. Loop
directories keep scripts, runtime state, tracking records, and process context.

## Quick Start

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\New-HdlProject.ps1 -Name <project_name>
```

Then validate the created project:

```powershell
cd engine
python -m hdlflow.cli doctor --workspace .. --project ..\projects\<project_name>
python -m hdlflow.cli plan --project ..\projects\<project_name>
python -m hdlflow.cli run-config --workspace .. --project ..\projects\<project_name>
```

## Agent Library

The `library/` directory stores reusable RTL templates, FPGA board reference
material, and Xilinx software user-guide content for automated loops.

The basic agent flow is:

```text
get-workflow-toc -> select entry ID -> get-command-detail or get-template-detail
```

Build the local SQLite index:

```powershell
python -m hdlflow.cli library-build --workspace ..
```

Query FPGA timing commands:

```powershell
python -m hdlflow.cli get-workflow-toc --workspace .. --flow fpga.timing_analysis --tool vivado
python -m hdlflow.cli get-command-detail --workspace .. --id vivado.report_timing_summary
```

Query Vivado/Vitis Tcl and software guide content:

```powershell
python -m hdlflow.cli search-tcl-commands --workspace .. --keyword timing --limit 10
python -m hdlflow.cli get-tcl-command-detail --workspace .. --id report_timing_summary
python -m hdlflow.cli search-tcl-doc --workspace .. --query "hardware manager" --limit 10
python -m hdlflow.cli search-tcl-examples --workspace .. --keyword create_project --limit 10
```

The current software guide set is Vivado UG835, UG894, UG908, UG1118 and Vitis
UG1553, UG1556, UG1701, UG1702 for the 2024.2 database target. UG PDFs belong
under `library/files/fpga_ug_pdfs/`, not under project requirement folders.
Large PDF files and generated SQLite databases are local-only by default.

Before any Loop3 FPGA prototype script generation, run the database preflight:

```powershell
cd engine
python -m hdlflow.cli prototype-preflight --workspace .. --project ..\projects\<project_name> --mode pl
python -m hdlflow.cli prototype-preflight --workspace .. --project ..\projects\<project_name> --mode ps_pl
```

The generated report belongs in `05_Output/reports/loop3/preflight/` and must be
used as the source for board pins, PS MIO mappings, DDR ownership, and Vivado or
Vitis Tcl command choices.

Loop3 generators are available for repeatable prototype work:

```powershell
python -m hdlflow.cli validate-prototype-plan --workspace .. --project ..\projects\<project_name>
python -m hdlflow.cli generate-xdc --workspace .. --project ..\projects\<project_name> --port sys_clk=PL_GCLK_50MHZ --clock sys_clk=20.000 --port pl_led0=PL_LED0 --port uart_rx_i=UART3_RX --port uart_tx_o=UART3_TX
python -m hdlflow.cli generate-ps-pl-bd --project ..\projects\<project_name>
python -m hdlflow.cli generate-vitis-boot --project ..\projects\<project_name>
```

For PS_PL designs, `prototype_plan.yaml` is the checked planning source for AXI
address maps, DDR test windows, cache maintenance rules, PS MIO assignments, and
PL external ports.

## Memory Synchronization

Project memory has one canonical machine-readable iteration source:
`memory/index.yaml`. Workflow commands auto-record successful micro-steps.
For a real stage handoff or user-visible checkpoint, write a closed iteration
through the CLI so the index, node-local iteration table, active version table,
and current state stay aligned:

```powershell
cd engine
python -m hdlflow.cli memory-record --project ..\projects\<project_name> --iteration-id <id> --node 04_Loop3_FPGA_Prototype --gate-level process --gate-result PASS --memory-record memory/00_global/DECISIONS.md --report 05_Output/reports/loop3/preflight/prototype_plan_check.md --notes "short note"
python -m hdlflow.cli memory-check --project ..\projects\<project_name>
```

## Configuration Model

- `config/global/` holds shared workspace rules.
- `config/global/gates/gate_levels.yaml` defines debug, develop, and release
  gate levels.
- `config/templates/project/project_config.yaml` defines the default project
  configuration shape.
- Local project configs should be created under `config/projects/<project_name>/`.
- A pipeline node is active when its configuration section exists and passes
  validation.

## Publication Rules

Keep this repository platform-focused. Do not commit:

- Concrete project source trees under `projects/<project_name>/`
- Raw datasheets or vendor documents
- Local generated SQLite databases
- Simulator work directories, logs, waves, and databases
- Local runtime state such as `.omx/`
- Credentials, tokens, license host IDs, device IDs, personal paths, or
  machine-specific metadata

Generated normalized library artifacts may be committed when they are concise,
queryable, and needed to rebuild the local database without keeping disposable
parser workspaces.

## Current Scope

The current engine validates layout and configuration, builds the configured
pipeline order, writes configuration reports, ensures canonical output
directories exist, and builds the local agent retrieval database.

It does not yet run document parsing, HDL simulation, UVM regressions, or FPGA
implementation tools directly.
