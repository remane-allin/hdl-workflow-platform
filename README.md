# HDL Workflow Platform

HDL Workflow Platform is a reusable workspace scaffold for HDL projects. It standardizes how requirements, parsed documents, RTL, testbenches, UVM verification, FPGA prototype work, reports, and final deliverables are organized.

This repository is the platform template. It intentionally does not publish any concrete chip project.

## Why This Exists

HDL projects often become hard to maintain when source files, generated files, reports, logs, and temporary tool outputs are mixed together. This platform keeps those concerns separated:

- Global rules live in one configuration tree.
- Each project instance lives under its own project directory.
- Pipeline stages are numbered and ordered.
- Runtime outputs stay disposable.
- Final deliverables stay in one canonical output area.

## Repository Contents

```text
config/      Global rules and project configuration templates
engine/      Python CLI and PowerShell hooks for workflow validation
skills/      HDL workflow skill definitions for AI-assisted work
templates/   Standard HDL project skeleton
projects/    Local project workspace, ignored for concrete project contents
.codex/      Project-local Codex hooks and prompt fragments
```

## Project Layout

Every project created from the template follows this structure:

```text
<project_name>/
├─ memory/
├─ 00_SPEC/
├─ 01_DocParse/
├─ 02_Loop1_RTL_TB/
├─ 03_Loop2_UVM_Verify/
├─ 04_Loop3_FPGA_Prototype/
├─ 05_Output/
└─ _archive/
```

The intended flow is:

```text
00_SPEC -> 01_DocParse -> 02_Loop1_RTL_TB -> 03_Loop2_UVM_Verify -> 04_Loop3_FPGA_Prototype -> 05_Output
```

`05_Output/` is the canonical editable deliverable area. It is where RTL, TB, UVM, FPGA files, final reports, and manifests converge after review. Loop directories keep scripts, runtime state, tracking records, and process context.

## Quick Start

From the repository root:

```powershell
cd engine
python -m hdlflow.cli init-project <project_name> --workspace ..
```

Then validate the created project:

```powershell
python -m hdlflow.cli doctor --workspace .. --project ..\projects\<project_name>
python -m hdlflow.cli plan --project ..\projects\<project_name>
python -m hdlflow.cli run-config --workspace .. --project ..\projects\<project_name>
python -m hdlflow.cli ensure-output --project ..\projects\<project_name>
```

## Configuration Model

- `config/global/` holds shared workspace rules.
- `config/templates/project/project_config.yaml` defines the default project configuration shape.
- Local project configs should be created under `config/projects/<project_name>/`.
- A pipeline node is active when its configuration section exists and passes validation.

## Publication Rules

Keep this repository platform-focused. Do not commit:

- Concrete project source trees under `projects/<project_name>/`
- Raw datasheets or vendor documents
- Parser extracts
- Simulator work directories, logs, waves, and databases
- Local runtime state such as `.omx/`
- Credentials, tokens, license host IDs, device IDs, personal paths, or machine-specific metadata

If a public example project is needed, prepare it as a separate reviewed example with its own README and data policy.

## Current Scope

The current engine validates layout and configuration, builds the configured pipeline order, writes configuration reports, and ensures canonical output directories exist.

It does not yet run document parsing, HDL simulation, UVM regressions, or FPGA implementation tools directly.
