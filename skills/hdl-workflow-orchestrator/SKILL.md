---
name: hdl-workflow-orchestrator
description: Orchestrate the full requirements-frontdoor-to-RTL/UVM-to-ModelSim loop inside this workspace. Use when the user wants to start a new HDL project, resume a paused project, determine the current stage, or drive iterative verification without losing project memory.
---

# HDL Workflow Orchestrator

Use this skill as the entry point for the local HDL workflow under `Test/`.

## When To Use

Use this skill when the user wants any of these:

- create or bootstrap a new RTL/UVM project
- resume a project after token loss or a new chat
- decide the current stage from existing artifacts
- run the full loop from structured requirements analysis to ModelSim debug
- keep the project state synchronized in `memory/`

Do not use this skill for detailed RTL coding, UVM coding, or log triage by itself. Route those tasks to the specialized skills:

- `$hdl-requirements-decompose`
- `$register-spec-and-ral`
- `$rtl-architecture-and-gen`
- `$uvm-env-and-test-build`
- `$modelsim-run-triage-debug`
- `$assertion-and-coverage`

## Workspace Contract

Assume this repository layout:

- `engine/`
- `engine/hooks/`, `skills/`, and `config/`
- `projects/<project_name>/`

Each active project should contain:

- `config/projects/<project_name>/project_config.yaml`
- `memory/`
- `00_SPEC/raw_docs/`, `00_SPEC/requirements/`, `01_DocParse/architecture/`, `01_DocParse/verification/`, `01_DocParse/prototype/`
- `01_DocParse/structured_spec/`, `01_DocParse/req_decompose/`
- `05_Output/rtl/`, `05_Output/tb/`, `05_Output/uvm/`
- `02_Loop1_RTL_TB/sim/ or 03_Loop2_UVM_Verify/sim/`
- `05_Output/reports/`
- `01_DocParse/trace_matrix/`

## Stage Order

1. Read `memory/00_global/PROJECT_BRIEF.md`, `CURRENT_STATE.md`, `NEXT_STEPS.md`, `OPEN_QUESTIONS.md` when present.
2. Read `config/projects/<project_name>/project_config.yaml`.
3. If the five-role requirements front door is missing or stale, run `requirements-frontdoor-init` and route to `$hdl-requirements-decompose`.
4. If the design has register-heavy control logic, route to `$register-spec-and-ral` before broad RTL/UVM generation.
5. If module planning is incomplete or RTL needs creation or fixes, route to `$rtl-architecture-and-gen`.
6. Enter Loop2 only after Loop1 has a passing gate manifest and fresh Loop1 evidence. If UVM environment, sequences, or tests are missing or stale, route to `$uvm-env-and-test-build`.
7. If simulation evidence is needed, route to `$modelsim-run-triage-debug`.
8. If the base loop is stable and the user asks for assertions or coverage closure, route to `$assertion-and-coverage`.
9. At the end of each meaningful iteration, update `memory/` and summarize the next step.

## Current-Stage Decision

Use these signals to decide the stage quickly:

- No project directory yet: bootstrap stage
- `00_SPEC/requirements/` changed or `01_DocParse/architecture/`, `verification/`, or `prototype/` is stale: requirements front-door stage
- `05_Output/rtl/` is empty or architecture is unresolved: RTL stage
- `05_Output/uvm/` is empty or tests do not reflect `test_intent.yaml`: UVM stage
- `02_Loop1_RTL_TB/sim/` or `03_Loop2_UVM_Verify/sim/` exists and user wants compile, run, or debug: ModelSim stage
- Coverage or assertions requested after stable configuration verification runs: quality stage

## Session Discipline

- Treat repository files as the source of truth, not chat memory.
- Prefer small forward steps and persist the result before switching topics.
- If the correct next action is ambiguous, state the branch point and choose the smallest safe step.
- Never silently overwrite generated or hand-written project files without checking what already exists.
- End by updating the checkpoint through the local PowerShell helper when practical.

## References

- Read [references/stage-map.md](references/stage-map.md) when deciding stage handoff or recovery behavior.
