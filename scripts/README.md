# Workspace Scripts

Use these scripts as the normal entry points for project-level workflow actions.

## Project Creation

Create projects only through:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\New-HdlProject.ps1 -Name <project_name>
```

Cross-platform entry point:

```bash
python scripts/new_hdl_project.py <project_name>
```

Both wrappers call `python -m hdlflow.cli init-project`, validate the result
with `doctor`, ensure canonical output folders, and leave a
`project_scaffold.yaml` marker inside the project.

Do not manually create directories under `projects/`.

## Requirements Front Door

After adding requirement sources, create the five-role front-end contract:

```powershell
cd engine
python -m hdlflow.cli requirements-frontdoor-init --project ..\projects\<project_name> --status DRAFT
python -m hdlflow.cli requirements-frontdoor-check --project ..\projects\<project_name> --allow-draft
```

Promote the artifact statuses to `READY` only after PM, architecture,
verification, prototype, and coordinator review are complete.

## Tool Invocation

Launch ModelSim through the configured wrapper instead of relying on whatever
`vsim` happens to be on PATH:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\Invoke-HdlModelSim.ps1 -Project projects\<project_name> -Loop loop1
powershell -ExecutionPolicy Bypass -File scripts\Invoke-HdlModelSim.ps1 -Project projects\<project_name> -Loop loop2
```

The wrapper resolves `modelsim.vsim_exe` from
`config/global/toolchains/toolchains.yaml`. Machine-local overrides use the
`HDLFLOW_MODELSIM_*` environment variables declared in that file.

Launch Vivado through the configured wrapper so `vivado.log`, `vivado.jou`, and
backup journals are written into a controlled log directory instead of the
workspace root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\Invoke-HdlVivado.ps1 `
  -Project projects\<project_name> `
  -Source projects\<project_name>\05_Output\fpga\vivado\scripts\<flow>.tcl `
  -program 1 -serial 1 -serial_port COM3
```

The wrapper resolves `vivado.vivado_bat` from
`config/global/toolchains/toolchains.yaml`, then passes explicit `-log` and
`-journal` arguments under `05_Output/fpga/vivado/logs`.

## Project Export

Concrete project instances under `projects/` are intentionally local and ignored
by Git. Create a reviewable backup package before moving machines or archiving a
milestone:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\Export-HdlProject.ps1 -ProjectPath projects\<project_name>
```

The export includes the project tree plus `config/projects/<project_name>` and
skips disposable runtime directories, local Codex/OMX state, waves, and simulator
work libraries by default. Use `-IncludeRuntime` only for local forensic capture.
