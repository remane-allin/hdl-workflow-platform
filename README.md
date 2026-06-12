# HDL Workflow Platform

HDL Workflow Platform is a reusable workspace scaffold for HDL projects and
AI-assisted FPGA development. It standardizes how requirements, parsed
documents, RTL, testbenches, UVM verification, FPGA prototype work, reports,
and final deliverables are organized.

The current library also contains a structured Vivado/Vitis 2024.2 software
reference layer for Tcl script generation, command lookup, and debug workflows.
The generated SQLite database is local-only, while the schema, indexes, and
normalized artifacts are versioned so the database can be rebuilt without raw
PDF inputs or parser workspaces.

## Why This Exists

HDL projects often become hard to maintain when source files, generated files,
reports, logs, and temporary tool outputs are mixed together. This platform
keeps those concerns separated:

- Global rules live in one configuration tree.
- Each project instance lives under its own project directory.
- Pipeline stages are numbered and ordered.
- The input -> work/docparse handoff has an isolated six-agent
  Spec -> Arch -> Exec -> Sim -> Review -> Arbtr front door before RTL, UVM,
  simulation, or FPGA prototype work begins.
- Memory records are indexed and separated into permanent archive, local
  transient notes, and recovery evidence.
- Requirement or behavior changes use a controlled request, platform-inferred
  impact, approval, regenerated front-door/design evidence, gate binding, and
  trace-update flow.
- Gate rules can distinguish debug, develop, and release levels.
- Runtime outputs stay disposable.
- Final deliverables stay in one canonical output area.

## Repository Contents

```text
env/        Platform runtime: core CLI, hooks, rules, skills, scripts, tests
lib/        Agent-facing RTL, FPGA hardware, Vivado, and Vitis reference library
prj/        Local project instances
local/      Disposable local runtime, archives, caches, and tool outputs
```

## Project Creation Rule

`env/rule/scaffold/` is the template project source. Directories under `prj/`
must be created by the unified workflow script entry point, not by manually
creating folders or copying files. Use `env/tool/scripts/New-HdlProject.ps1` first, then
add project-specific RTL, TB, FPGA, software, reports, and scripts under the
created project. Each generated project carries `project_scaffold.yaml`; project
validation treats that marker as required evidence that the script path was used.

## Multi-Project Runtime Rule

One platform workspace may hold several unrelated child projects under
`prj/`. Each child project owns its authoritative memory in
`prj/<project_name>/work/memory/`; workspace `local/runtime/omx/` files are only a
multi-project runtime index and may have `active_project: null` when no project
can be inferred safely.

Use `HDL_PROJECT_PATH` or pass `--project` / `-ProjectPath` for commands that
must target a specific child project. Hooks must not treat a stale `.omx`
project field as authority.

## Project Layout

Every project created from the template follows this structure:

```text
<project_name>/
|-- input/
|   `-- spec/
|-- work/docparse/
|-- work/loop1_rtl_tb/
|-- work/loop2_uvm/
|-- work/loop3_fpga_proto/
|-- work/gates/
|-- work/memory/
|-- work/change/
|-- work/traces/
|-- output/
|   |-- rtl/
|   |-- tb/
|   |-- uvm/
|   |-- fpga/
|   |-- reports/
|   `-- exports/
```

The intended flow is:

```text
input -> work/docparse -> work/loop1_rtl_tb -> work/loop2_uvm -> work/loop3_fpga_proto -> output
```

`output/` is the canonical editable deliverable area. It is where RTL, TB,
UVM, FPGA files, final reports, and manifests converge after review. Loop
directories keep scripts, runtime state, tracking records, and process context.

The work/docparse front door uses six isolated engineering agents. Loop1, Loop2,
and Loop3 remain the engineering evidence layers; the agents own the governance
and correction flow above them:

- Spec Agent: executable chip Spec, interface timing, protocol metrics, legal design boundary, forbidden design list.
- Arch Agent: module topology, bus architecture, hierarchy, throughput planning, interfaces, dataflow.
- Exec Agent: Verilog RTL, module instantiation, complete functional directed TB.
- Sim Agent: Loop1/Loop2/Loop3 simulation, UVM, waveforms, logs, coverage, board-validation evidence.
- Review Agent: structured defects, severity, lifecycle status, risks, correction advice, compliance review; no direct Spec/Arch/RTL edits.
- Arbtr Agent: global flow record, disputes, iteration routing, termination check, final freeze; no direct Spec/Arch/RTL edits.

## Quick Start

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File env\tool\scripts\New-HdlProject.ps1 -Name <project_name>
```

Cross-platform:

```bash
python env/tool/scripts/new_hdl_project.py <project_name>
```

Because concrete projects are local by policy, export a project package when a
milestone should survive outside this workspace:

```powershell
powershell -ExecutionPolicy Bypass -File env\tool\scripts\Export-HdlProject.ps1 -ProjectPath prj\<project_name>
```

Then validate the created project:

```powershell
$env:PYTHONPATH = "env/core"
python -m hdlflow.cli doctor --workspace . --project prj\<project_name>
python -m hdlflow.cli plan --project prj\<project_name>
python -m hdlflow.cli run-config --workspace . --project prj\<project_name>
python -m hdlflow.cli requirements-frontdoor-init --project prj\<project_name> --status DRAFT
python -m hdlflow.cli requirements-frontdoor-check --project prj\<project_name> --allow-draft
python -m hdlflow.cli review-check --project prj\<project_name> --level develop
python -m hdlflow.cli ralph-status --project prj\<project_name>
python -m hdlflow.cli run-gate --project prj\<project_name> --node loop1 --level develop
python -m hdlflow.cli ralph-check --project prj\<project_name>
python -m hdlflow.cli final-audit --project prj\<project_name>
```

## Change-Control Rule

After any gate baseline exists, a requirement, architecture, RTL intent, TB,
UVM, assertion, coverage, prototype, board-test, or FPGA behavior change must
start with `change-open`. Record impact with `change-impact`; the platform
infers downstream nodes, required verification, and whether `generate-docs`
must be rerun from the supplied artifact paths. `change-approve --decision
approved` refuses incomplete impact records. A changed gate must then be rerun
with `--change-id`, and the request closes with `change-close` after trace
updates are recorded.

## Review Gate Rule

`work/docparse/review/role_findings.yaml` is a structured defect list. Every
finding must include id, severity, status, owner, affected artifact, impact,
evidence, recommendation, and route target. Develop gates fail on open
critical/high findings; release gates also fail on open medium findings.
`review-check` writes `output/reports/review/review_check.md`, and
`ralph-status` prioritizes those blockers before ordinary loop work.

## Agent Library

The `lib/` directory stores reusable RTL templates, FPGA board reference
material, and Xilinx software user-guide content for automated loops.

The basic agent flow is:

```text
get-workflow-toc -> select entry ID -> get-command-detail or get-template-detail
```

Build the local SQLite index:

```powershell
python -m hdlflow.cli library-build --workspace .
```

Query FPGA timing commands:

```powershell
python -m hdlflow.cli get-workflow-toc --workspace . --flow fpga.timing_analysis --tool vivado
python -m hdlflow.cli get-command-detail --workspace . --id vivado.report_timing_summary
```

Query Vivado/Vitis Tcl and software guide content:

```powershell
python -m hdlflow.cli search-tcl-commands --workspace . --keyword timing --limit 10
python -m hdlflow.cli get-tcl-command-detail --workspace . --id report_timing_summary
python -m hdlflow.cli search-tcl-doc --workspace . --query "hardware manager" --limit 10
python -m hdlflow.cli search-tcl-examples --workspace . --keyword create_project --limit 10
```

The current software guide set is Vivado UG835, UG894, UG908, UG1118 and Vitis
UG1553, UG1556, UG1701, UG1702 for the 2024.2 database target. The agent
library consumes the parsed artifacts and the local SQLite database only; raw
PDF files and parser workspaces are not retained in the repository.

Before any Loop3 FPGA prototype script generation, run the database preflight:

```powershell
$env:PYTHONPATH = "env/core"
python -m hdlflow.cli prototype-preflight --workspace . --project prj\<project_name> --mode pl
python -m hdlflow.cli prototype-preflight --workspace . --project prj\<project_name> --mode ps_pl
```

The generated report belongs in `output/reports/loop3/preflight/` and must be
used as the source for board pins, PS MIO mappings, DDR ownership, and Vivado or
Vitis Tcl command choices.

Loop3 generators are available for repeatable prototype work:

```powershell
python -m hdlflow.cli validate-prototype-plan --workspace . --project prj\<project_name>
python -m hdlflow.cli generate-xdc --workspace . --project prj\<project_name> --port sys_clk=PL_GCLK_50MHZ --clock sys_clk=20.000 --port pl_led0=PL_LED0 --port uart_rx_i=UART3_RX --port uart_tx_o=UART3_TX
python -m hdlflow.cli generate-ps-pl-bd --project prj\<project_name>
python -m hdlflow.cli generate-vitis-boot --project prj\<project_name>
```

For PS_PL designs, `prototype_plan.yaml` is the checked planning source for AXI
address maps, DDR test windows, cache maintenance rules, PS MIO assignments, and
PL external ports.

Tool launchers in `env/rule/global/toolchains/toolchains.yaml` may be overridden
per machine with environment variables such as
`HDLFLOW_VIVADO_VIVADO_BAT`, `HDLFLOW_VITIS_XSCT_BAT`, and
`HDLFLOW_VITIS_BOOTGEN_BAT`.

Prototype plans must replace template placeholders before script generation:
`rtl_top_module` and PS_PL AXI instance names are rejected when they still look
like `change_me`. If the DocParse/source prototype intent says pure PL, a
`ps_pl` board-test plan is rejected unless it explicitly records
`allow_ps_pl_wrapper: true` and a `mode_rationale`.

Loop2 closure is intentionally stricter than aggregate coverage thresholds.
The develop/release gate blocks unclassified coverage-triage rows, marker-only
assertion evidence without real SVA/bind files, manually forced functional
coverage sampling from tests, and missing stress scenarios such as mid-frame
reset, bad stop bit, glitch/noise, overflow, and BAUD_DIV=434 coverage.

## Memory Synchronization

Project memory has one canonical machine-readable iteration source:
`work/memory/index.yaml`. Workflow commands auto-record successful micro-steps.
For a real stage handoff or user-visible checkpoint, write a closed iteration
through the CLI so the index, node-local iteration table, active version table,
and current state stay aligned:

```powershell
$env:PYTHONPATH = "env/core"
python -m hdlflow.cli memory-record --project prj\<project_name> --iteration-id <id> --node work/loop3_fpga_proto --gate-level process --gate-result PASS --memory-record work/memory/00_global/DECISIONS.md --report output/reports/loop3/preflight/prototype_plan_check.md --notes "short note"
python -m hdlflow.cli memory-check --project prj\<project_name>
```

Failed CLI commands that know the project path write recovery records under
`work/memory/recovery/failure_records/`. Passing memory records and executable gates
write rollback/hash manifests under `work/memory/recovery/rollback_manifests/`.
Run `sync-project-state` whenever external scripts or manual recovery may have
left `work/gates/*.json` stale; successful and failed gates call the same synchronizer
so the latest gate result wins over older manifests:

```powershell
$env:PYTHONPATH = "env/core"
python -m hdlflow.cli sync-project-state --project prj\<project_name>
```

## Configuration Model

- `env/rule/global/` holds shared workspace rules.
- `env/rule/global/gates/gate_levels.yaml` defines debug, develop, and release
  gate levels.
- `env/rule/project_default/project_config.yaml` defines the default project
  configuration shape.
- Local project configs should be created under `prj/<project_name>/work/config/`.
- A pipeline node is active when its configuration section exists and passes
  validation.

## Platform Self-Tests

Run the dependency-free Python unit tests before changing engine parsing,
toolchain resolution, or prototype-plan checks:

```powershell
$env:PYTHONPATH = "env/core"
python -m unittest discover -s env\test\tests
```

## Publication Rules

Keep this repository platform-focused. Do not commit:

- Concrete project source trees under `prj/<project_name>/`
- Raw datasheets or vendor documents
- Local generated SQLite databases
- Simulator work directories, logs, waves, and databases
- Local runtime state such as `local/runtime/`
- Credentials, tokens, license host IDs, device IDs, personal paths, or
  machine-specific metadata

Generated normalized library artifacts may be committed when they are concise,
queryable, and needed to rebuild the local database without keeping disposable
parser workspaces.

## Current Scope

The current core validates layout and configuration, builds the configured
pipeline order, creates and checks the six-agent requirements front door,
writes configuration reports, ensures canonical output directories exist, and
builds the local agent retrieval database.

It does not yet run document parsing, HDL simulation, UVM regressions, or FPGA
implementation tools directly.
