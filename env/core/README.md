# Core Engine

This directory is the single execution surface of the new HDL workflow platform.

The first implementation should keep these modules separate:

- `config_loader` - read workspace and project config, merge inherited policy, validate required fields.
- `pipeline_builder` - discover active nodes from config and build the ordered pipeline.
- `gate_runner` - run entry and exit gates for each node.
- `artifact_manager` - verify and maintain the canonical `output/` deliverable directories.
- `snapshot_manager` - create, retain, restore, and archive node snapshots.
- `report_writer` - generate process reports and final audit reports.
- `cli` - expose one command-line entry point.

## Current Commands

Run from the workspace root with `PYTHONPATH` pointed at `env/core`:

```powershell
$env:PYTHONPATH = "env/core"
python -m hdlflow.cli doctor --workspace . --project prj\<project_name>
python -m hdlflow.cli plan --project prj\<project_name>
python -m hdlflow.cli run-config --workspace . --project prj\<project_name>
python -m hdlflow.cli ensure-output --project prj\<project_name>
python -m hdlflow.cli requirements-frontdoor-init --project prj\<project_name> --status DRAFT
python -m hdlflow.cli requirements-frontdoor-check --project prj\<project_name> --allow-draft
python -m hdlflow.cli review-check --project prj\<project_name> --level develop
python -m hdlflow.cli loop1-waveform-check --project prj\<project_name>
python -m hdlflow.cli run-gate --project prj\<project_name> --node loop2 --level develop
python -m hdlflow.cli final-audit --project prj\<project_name>
python -m hdlflow.cli change-open --project prj\<project_name> --title "change title" --reason "why" --scope "files" --risk "low"
python -m hdlflow.cli change-impact --project prj\<project_name> --change-id CR-... --requirement REQ-... --artifact output/rtl/foo.v --rollback "restore last rollback manifest" --risk low
python -m hdlflow.cli ralph-status --project prj\<project_name>
python -m hdlflow.cli ralph-check --project prj\<project_name>
```

Current scope:

- load all global rule files
- load the project config
- validate project layout
- validate expected nodes and path rules
- run executable node gates against reports, logs, coverage, Vivado evidence, and freshness checks
- create and validate multi-role requirements front-door artifacts before Loop handoff
- validate structured Review Agent findings and block open severity issues
- validate Loop1 top-level VCD waveform windows before Loop2 handoff
- maintain change-control request, platform-inferred impact, approval, gate-binding, and trace-update records
- synchronize the file-backed Ralph loop status from active plan, memory, gate state, review blockers, and change records
- record CLI failures and rollback/hash manifests under project memory
- generate the active pipeline
- write `work/memory/00_global/CONFIG_RUN_REPORT.md`
- ensure the canonical `output/` source and report directories exist

The gate runner validates existing evidence; it does not launch document
parsers, ModelSim, UVM regressions, or FPGA implementation tools directly.
