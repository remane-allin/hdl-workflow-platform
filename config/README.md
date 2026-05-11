# Unified Configuration

All workflow management configuration lives here.

- `global/` - workspace-wide policy, gates, naming, reports, snapshots, tools, and Git rules.
- `projects/<project_name>/project_config.yaml` - project-specific pipeline configuration.
- `templates/project/project_config.yaml` - default config used by `hdlflow init-project`.

Project directories should not keep their own `project_config.yaml`; project code, reports, runtime state, and memory stay under `projects/`.

