# Test Workspace Contract

This is the active HDL workflow workspace.

Rules:

- Treat `Test/` as self-contained.
- Use `Test/config/` for all workspace and project configuration.
- Use `Test/skills/` and `Test/.codex/` for project-local Codex surfaces.
- Use `Test/.omx/` only for runtime summaries.
- Use `projects/<project_name>/05_Output/` as the canonical editable RTL, TB, UVM, FPGA, and report area after a local project is created.
- Do not read from or write to a legacy workspace unless the user explicitly asks for a migration lookup.
- Do not create root-level `.codex` or `.omx` surfaces for this project.
