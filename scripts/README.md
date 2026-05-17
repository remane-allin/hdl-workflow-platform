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
