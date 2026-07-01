# Workspace Scripts

Use these scripts as the normal entry points for project-level workflow actions.

## Project Creation

Create projects only through:

```powershell
powershell -ExecutionPolicy Bypass -File env\tool\scripts\New-HdlProject.ps1 -Name <project_name>
```

Cross-platform entry point:

```bash
python env/tool/scripts/new_hdl_project.py <project_name>
```

Both wrappers set the required `HDLFLOW_PROJECT_CREATE_ENTRYPOINT` guard,
call the internal scaffold engine, validate the result with `doctor`, ensure
canonical output folders, initialize the six-agent front-door artifacts in
`DRAFT`, write the bootstrap memory record, and leave a `project_scaffold.yaml`
marker inside the project. Calling `python -m hdlflow.cli init-project`
directly is blocked by the engine.

Do not manually create directories under `prj/`.

## Requirements Front Door

New projects already contain a DRAFT six-agent front-end contract from the
creation script. After adding requirement sources, refresh and validate it:

```powershell
$env:PYTHONPATH = "env/core"
python -m hdlflow.cli requirements-frontdoor-init --project prj\<project_name> --status DRAFT
python -m hdlflow.cli requirements-frontdoor-check --project prj\<project_name> --allow-draft
```

Promote the artifact statuses to `READY` only after Spec, Arch, Exec, Sim,
Review, and Arbtr handoff requirements are complete.

When requirements change, update the requirement/front-door/docset sources
first and rerun the `work/docparse` gate before returning to Loop1, Loop2, Loop3,
or final output gates. Downstream gates intentionally block if any file under
`input/spec` is newer than the latest passed DocParse manifest.

## Gate Integrity

Automatic loop execution may refresh evidence, but it must not rewrite the gate
policy, gate entry point, front-door checker, or report refreshers in order to
pass a gate. Passed gate manifests record hashes for those protected platform
files, and later gates fail on protected-file drift without a change-id bypass.

Loop1 and Loop2 reports are regenerated only from complete simulator
transcripts. Hand-written lightweight PASS reports, or logs missing the
ModelSim/UVM/coverage provenance markers, are rejected by the report refresh
step instead of being accepted as gate evidence.

## Platform Change Governance

Changes under `env/` are platform changes, not project requirements. Keep the
PCR, impact matrix, migration manifest, regression manifest, and Arbtr review
under `env/rule/platform_governance/` synchronized with the diff, then run:

```powershell
$env:PYTHONPATH = "env/core"
python -m hdlflow.cli platform-regression --workspace . --all
```

For legacy projects that predate the frontdoor contract model, use the platform
migration command before applying new gates:

```powershell
python -m hdlflow.cli migrate-project --workspace . --project prj\<project_name> --to-contract 2026.06-contract-v2
```

## Tool Invocation

Launch ModelSim through the configured wrapper instead of relying on whatever
`vsim` happens to be on PATH:

```powershell
powershell -ExecutionPolicy Bypass -File env\tool\scripts\Invoke-HdlModelSim.ps1 -Project prj\<project_name> -Loop loop1
powershell -ExecutionPolicy Bypass -File env\tool\scripts\Invoke-HdlModelSim.ps1 -Project prj\<project_name> -Loop loop2
```

The wrapper first uses `env/tool/scripts/HdlToolDefaults.ps1` default paths and
machine-local `HDLFLOW_MODELSIM_*` overrides. It only falls back to
`env/rule/global/toolchains/toolchains.yaml` when the default path is unavailable.

Launch Vivado through the configured wrapper so `vivado.log`, `vivado.jou`, and
backup journals are written into a controlled log directory instead of the
workspace root:

```powershell
powershell -ExecutionPolicy Bypass -File env\tool\scripts\Invoke-HdlVivado.ps1 `
  -Project prj\<project_name> `
  -Source prj\<project_name>\output\fpga\vivado\scripts\<flow>.tcl `
  -program 1 -serial 1 -serial_port COM3
```

The wrapper first uses `env/tool/scripts/HdlToolDefaults.ps1` default paths and
machine-local `HDLFLOW_VIVADO_*` overrides. It only falls back to
`env/rule/global/toolchains/toolchains.yaml` when the default path is unavailable,
then passes explicit `-log` and `-journal` arguments under
`output/fpga/vivado/logs`. The wrapper also sets the Vivado run directory
before sourcing Tcl; by default this run directory is the same controlled log
directory, and Tcl can read `HDLFLOW_PROJECT_ROOT`, `HDLFLOW_VIVADO_ROOT`,
`HDLFLOW_VIVADO_LOG_DIR`, and `HDLFLOW_VIVADO_RUN_DIR` if it needs absolute
platform paths. After Vivado exits, the wrapper sweeps any default
`vivado*.jou` or `vivado*.log` files from the project root into the same
controlled log directory, so a completed run must not leave tool logs beside
`project_scaffold.yaml`.

## Project Export

Concrete project instances under `prj/` are intentionally local and ignored
by Git. Create a reviewable backup package before moving machines or archiving a
milestone:

```powershell
powershell -ExecutionPolicy Bypass -File env\tool\scripts\Export-HdlProject.ps1 -ProjectPath prj\<project_name>
```

The export includes the project tree plus `prj/<project_name>/work/config` and
skips disposable runtime directories, local Codex/OMX state, waves, and simulator
work libraries by default. Use `-IncludeRuntime` only for local forensic capture.

## Workspace State Sync

After deleting or moving a local project directory, refresh the runtime project
index so `local/runtime/omx/state/hdl-workflow-state.json` does not keep a stale active
project:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\Sync-HdlWorkspaceState.ps1
```

The script does not delete orphan configs. It reports any
`prj/<project_name>/work/config/project_config.yaml` entries whose project
directory no longer exists, so cleanup can be reviewed deliberately.
