# HDL Workflow Workspace Rules

- `env/rule/scaffold/` is the template project source.
- Every project under `prj/` must be created through the unified script
  entry point, normally `powershell -ExecutionPolicy Bypass -File
  env\tool\scripts\New-HdlProject.ps1 -Name <project_name>` from the current workspace
  root.
- Do not manually create a new project directory directly under `prj/`.
  After the script creates the project skeleton, add project-specific RTL, TB,
  FPGA, software, reports, and scripts inside that generated project.
- Any task requirement raised in chat must enter the six-agent platform flow
  before implementation work. Capture the user request as a requirement source
  under `input/spec`, then run the requirements
  front door (`requirements-frontdoor-init` as needed and
  `requirements-frontdoor-check`). Spec, Arch, Exec, Sim, Review, and Arbtr have
  isolated contexts and write scopes; Review writes defects and risks only, and
  Arbtr writes `work/memory`, `work/gates`, and freeze decisions only. Do not write or modify formal
  implementation artifacts under `output/rtl`, `output/tb`,
  `output/uvm`, `work/loop3_fpga_proto`, or `output/fpga` until the
  relevant front-door/gate evidence allows the next loop.
- For any multi-step task, keep the active plan in
  `work/memory/00_global/ACTIVE_PLAN.md`; record durable findings in
  `work/memory/00_global/PLAN_FINDINGS.md` and failed attempts or blockers in
  `work/memory/00_global/PLAN_ERRORS.md`. Read these files before continuing
  after context compaction.
- After any gate baseline exists, every requirement-affecting change must start
  with `change-open` before editing sources. Use `change-impact` to record
  affected requirements, artifacts, downstream nodes, verification, rollback,
  and whether `generate-docs` must be rerun; approval and bound gates must
  reject incomplete impact records.
- Use `review-check` to validate structured Review Agent findings. Open
  critical/high findings block develop gates; open medium findings also block
  release. Use `ralph-status` to decide the next action from files. Open or
  approved change requests and review blockers take priority over normal loop
  work; `ralph-check` is the stop condition for a clean file-backed iteration.
- Do not use the old informal validation label for Loop1/Loop2/Loop3 checks.
  Use precise terms: directed test, regression, build, board test, timing check,
  serial capture, or prototype validation.
- Before Loop3 PL or PS_PL prototype work, query the local lib/database and
  write `output/reports/loop3/preflight/database_preflight.md`. Use that
  evidence for board pins, PS MIO, DDR ownership, Vivado Tcl, and Vitis flow
  choices.
- Read Vivado and Vitis launch paths from `env/rule/global/toolchains/toolchains.yaml`
  instead of rediscovering or hardcoding them in new scripts.
- Keep Vivado project artifacts under `output/fpga/vivado/` and Vitis project
  artifacts under `output/fpga/vitis/`.
- For PL prototype work, generate XDC from the database-backed `generate-xdc`
  path unless a reviewed exception is recorded.
- For PS_PL prototype work, run `validate-prototype-plan` before BD or Vitis
  generation. AXI address overlaps, PS MIO ownership, PL pin conflicts, DDR
  test ranges, and cache flush/invalidate policy must be checked.
- Use the shared board-test config and generator scripts under
  `work/loop3_fpga_proto/board_tests` and `work/loop3_fpga_proto/scripts` before writing project
  specific board scripts.
- Automated workflow commands must auto-record successful micro-steps to project
  memory and run `python -m hdlflow.cli memory-check`. For human-authored stage
  handoffs, use `python -m hdlflow.cli memory-record`. Treat `work/memory/index.yaml`
  as the canonical machine-readable source; `active_versions.md`, node
  `iterations.md`, and `CURRENT_STATE.md` are synchronized views.
