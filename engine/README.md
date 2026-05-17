# Engine

This directory is the single execution surface of the new HDL workflow platform.

The first implementation should keep these modules separate:

- `config_loader` - read workspace and project config, merge inherited policy, validate required fields.
- `pipeline_builder` - discover active nodes from config and build the ordered pipeline.
- `gate_runner` - run entry and exit gates for each node.
- `artifact_manager` - verify and maintain the canonical `05_Output/` deliverable directories.
- `snapshot_manager` - create, retain, restore, and archive node snapshots.
- `report_writer` - generate process reports and final audit reports.
- `cli` - expose one command-line entry point.

## Current Commands

Run from `Test/engine`:

```powershell
python -m hdlflow.cli doctor --workspace .. --project ..\projects\<project_name>
python -m hdlflow.cli plan --project ..\projects\<project_name>
python -m hdlflow.cli run-config --workspace .. --project ..\projects\<project_name>
python -m hdlflow.cli ensure-output --project ..\projects\<project_name>
python -m hdlflow.cli requirements-frontdoor-init --project ..\projects\<project_name> --status DRAFT
python -m hdlflow.cli requirements-frontdoor-check --project ..\projects\<project_name> --allow-draft
python -m hdlflow.cli run-gate --project ..\projects\<project_name> --node loop2 --level develop
python -m hdlflow.cli final-audit --project ..\projects\<project_name>
python -m hdlflow.cli change-open --project ..\projects\<project_name> --title "change title" --reason "why" --scope "files" --risk "low"
```

Current scope:

- load all global config files
- load the project config
- validate project layout
- validate expected nodes and path rules
- run executable node gates against reports, logs, coverage, Vivado evidence, and freshness checks
- create and validate five-role requirements front-door artifacts before Loop handoff
- maintain change-control request, impact, approval, and trace-update records
- record CLI failures and rollback/hash manifests under project memory
- generate the active pipeline
- write `memory/00_global/CONFIG_RUN_REPORT.md`
- ensure the canonical `05_Output/` source and report directories exist

The gate runner validates existing evidence; it does not launch document
parsers, ModelSim, UVM regressions, or FPGA implementation tools directly.
