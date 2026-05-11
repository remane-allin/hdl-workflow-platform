# HDL Workflow Platform

HDL Workflow Platform is a template-driven workspace for managing HDL projects with a clear pipeline, centralized configuration, and separated deliverables.

The repository contains the platform, templates, workflow rules, and helper engine. It does not include a concrete chip project instance.

## What This Repository Provides

- A standard HDL project directory template.
- Global configuration for tools, gates, naming, reports, snapshots, and Git rules.
- A small Python workflow engine for validating project layout and configuration.
- Codex hook and prompt surfaces for keeping workflow operations inside the workspace.
- HDL-focused skills for document normalization, requirement decomposition, RTL generation, UVM construction, simulation triage, and coverage closure.

## Repository Layout

- `config/` - global rules and project configuration templates.
- `engine/` - CLI and hook scripts for workspace validation and project setup.
- `skills/` - reusable HDL workflow skill definitions.
- `templates/` - project skeleton used to initialize new HDL projects.
- `projects/` - placeholder for local project instances. Concrete project contents are ignored by Git.
- `.codex/` - local automation hooks and prompts for this workspace.

## Project Model

Each HDL project follows the same ordered structure:

```text
00_SPEC
01_DocParse
02_Loop1_RTL_TB
03_Loop2_UVM_Verify
04_Loop3_FPGA_Prototype
05_Output
memory
_archive
```

`05_Output/` is the canonical editable deliverable area for RTL, TB, UVM, FPGA files, and final reports. Loop directories hold process context, scripts, runtime data, and tracking records.

## Privacy And Publication Rules

Do not commit concrete project instances, raw datasheets, parser extracts, runtime directories, simulator outputs, credentials, license host IDs, device IDs, personal paths, or local machine metadata.

The checked-in repository should stay reusable as a platform template. Project-specific work belongs in local `projects/<project_name>/` directories unless it is intentionally prepared as a separate public example.

## Basic Commands

From `engine/`, after creating a local project from the template:

```powershell
python -m hdlflow.cli doctor --workspace .. --project ..\projects\<project_name>
python -m hdlflow.cli plan --project ..\projects\<project_name>
python -m hdlflow.cli run-config --workspace .. --project ..\projects\<project_name>
python -m hdlflow.cli ensure-output --project ..\projects\<project_name>
```
