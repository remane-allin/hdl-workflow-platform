# Workspace Scripts

Use these scripts as the normal entry points for project-level workflow actions.

## Project Creation

Create projects only through:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\New-HdlProject.ps1 -Name <project_name>
```

The script calls `python -m hdlflow.cli init-project`, validates the result with
`doctor`, ensures canonical output folders, and leaves a `project_scaffold.yaml`
marker inside the project.

Do not manually create directories under `projects/`.
