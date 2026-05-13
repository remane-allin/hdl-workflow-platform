# Test Workspace Rules

- `templates/` is the template project source.
- Every project under `projects/` must be created through the unified script
  entry point, normally `powershell -ExecutionPolicy Bypass -File
  scripts\New-HdlProject.ps1 -Name <project_name>` from the `Test` workspace
  root.
- Do not manually create a new project directory directly under `projects/`.
  After the script creates the project skeleton, add project-specific RTL, TB,
  FPGA, software, reports, and scripts inside that generated project.
- Do not use the old informal validation label for Loop1/Loop2/Loop3 checks.
  Use precise terms: directed test, regression, build, board test, timing check,
  serial capture, or prototype validation.
- Before Loop3 PL or PS_PL prototype work, query the local library/database and
  write `05_Output/reports/loop3/preflight/database_preflight.md`. Use that
  evidence for board pins, PS MIO, DDR ownership, Vivado Tcl, and Vitis flow
  choices.
- Read Vivado and Vitis launch paths from `config/global/toolchains/toolchains.yaml`
  instead of rediscovering or hardcoding them in new scripts.
- Keep Vivado project artifacts under `05_Output/fpga/vivado/` and Vitis project
  artifacts under `05_Output/fpga/vitis/`.
- For PL prototype work, generate XDC from the database-backed `generate-xdc`
  path unless a reviewed exception is recorded.
- For PS_PL prototype work, run `validate-prototype-plan` before BD or Vitis
  generation. AXI address overlaps, PS MIO ownership, PL pin conflicts, DDR
  test ranges, and cache flush/invalidate policy must be checked.
- Use the shared board-test config and generator scripts under
  `04_Loop3_FPGA_Prototype/board_tests` and `scripts` before writing project
  specific board scripts.
- Automated workflow commands must auto-record successful micro-steps to project
  memory and run `python -m hdlflow.cli memory-check`. For human-authored stage
  handoffs, use `python -m hdlflow.cli memory-record`. Treat `memory/index.yaml`
  as the canonical machine-readable source; `active_versions.md`, node
  `iterations.md`, and `CURRENT_STATE.md` are synchronized views.
