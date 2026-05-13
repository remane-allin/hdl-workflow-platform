# Projects

Each child directory is one isolated project instance.

Rules:

- No shared design source between project directories.
- No project-specific memory outside the project directory.
- No direct writes to another project's output area.
- New project directories must be created with `scripts/New-HdlProject.ps1` from
  the workspace root. A valid project contains `project_scaffold.yaml`.
- Manual folder creation under `projects/` is invalid, even if the folder shape
  looks similar to the template.
