---
name: hdl-workflow-orchestrator
description: Orchestrate the full requirements-frontdoor-to-RTL/UVM-to-ModelSim loop inside this workspace. Use when the user wants to start a new HDL project, resume a paused project, determine the current stage, or drive iterative verification without losing project memory.
---

# HDL Workflow Orchestrator

Use this skill as the entry point for the HDL workflow rooted at the current
workspace. Resolve the workspace from the active working directory; do not bind
the workflow to a hard-coded repository or project name.

## When To Use

Use this skill when the user wants any of these:

- create or bootstrap a new RTL/UVM project through the official creation scripts
- resume a project after token loss or a new chat
- decide the current stage from existing artifacts
- run the full loop from structured requirements analysis to ModelSim debug
- keep the project state synchronized in `work/memory/`

Do not use this skill for detailed RTL coding, UVM coding, or log triage by itself. Route those tasks to the specialized skills:

- `$hdl-requirements-decompose`
- `$register-spec-and-ral`
- `$rtl-architecture-and-gen`
- `$uvm-env-and-test-build`
- `$modelsim-run-triage-debug`
- `$assertion-and-coverage`

## Workspace Contract

Assume the current workspace exposes this layout:

- `env/core/`
- `env/core/hooks/`, `env/rule/`, `env/tool/scripts/`, and `lib/`
- `prj/<project_name>/`

Projects must be created only through `env/tool/scripts/New-HdlProject.ps1` or
`env/tool/scripts/new_hdl_project.py`. Do not call the internal scaffold CLI directly
and do not create directories under `prj/` by hand.

Each active project should contain:

- `prj/<project_name>/work/config/project_config.yaml`
- `work/memory/`
- `input/spec/`, `work/docparse/architecture/`, `work/docparse/verification/`, `work/docparse/prototype/`
- `work/docparse/parsed/mineru_extract/`, `work/docparse/structured_spec/`, `work/docparse/req_decompose/`
- `output/rtl/`, `output/tb/`, `output/uvm/`, `output/sim/`
- `work/loop1_rtl_tb/sim/ or work/loop2_uvm/sim/`
- `output/reports/`
- `work/docparse/trace_matrix/`

## Stage Order

1. Read `work/memory/00_global/ACTIVE_PLAN.md`, `PLAN_FINDINGS.md`, `PLAN_ERRORS.md`, `PROJECT_BRIEF.md`, `CURRENT_STATE.md`, `NEXT_STEPS.md`, and `OPEN_QUESTIONS.md` when present.
   For multi-step work, update `ACTIVE_PLAN.md` before relying on chat memory;
   record durable discoveries in `PLAN_FINDINGS.md` and failed attempts or
   abandoned approaches in `PLAN_ERRORS.md`. Use `ralph-status` to recover the
   current loop, active change requests, review blockers, failed gates, and
   next action from files; use `ralph-check` before claiming a file-backed
   iteration is clean.
2. Read `prj/<project_name>/work/config/project_config.yaml`.
3. If raw or generated requirements changed, re-enter DocParse before any loop work. External document evidence must be produced only by the MinerU high-precision API path, recorded in `work/docparse/parsed/mineru_extract/provenance.yaml`, and stored under `work/docparse/parsed/mineru_extract/`; the provenance must include `/api/v4/extract/task` or `/api/v4/file-urls/batch`. For chat-only requirements, use the formal exception: capture the request under `input/spec/` with `source_type: chat_request` and bind it from `document_analysis.yaml` with `parser_output: manual_chat_capture`, `analysis_units`, and `evidence_map`. Local parser side outputs, fast-channel page splits, operation records inside parsed evidence, or legacy parsed output paths are not completion evidence.
4. If the requirements front door is missing or stale, run `requirements-frontdoor-init`, normalize the five machine-readable structured spec files (`interface_spec.yaml`, `interface_timing.yaml`, `register_map.yaml`, `test_intent.yaml`, and `timing_rules.yaml`), and route to `$hdl-requirements-decompose`. During this stage, Spec Agent must write unresolved doubts to `work/docparse/frontdoor/open_questions.md`, mirror them in `work/docparse/structured_spec/document_analysis.yaml.open_questions`, send them to the user for review, and record `question_review.status: REVIEWED` with `unresolved_count: 0` before READY. Sim Agent must plan Loop1 waveform observability in `test_intent.yaml.waveform_windows` and `verification_plan.yaml.waveform_comparison`; `generate-docs` must carry this plan into `output/docs/test/verification_plan.md` before Loop1 work begins.
   `document_analysis.yaml` must use checker-compatible keys:
   `source_documents[].source_ref`, `parser_output`, `document_type`,
   `analysis_units[].unit_id`, `source_ref`, `section`, `summary`, and
   `extracted_requirements` or `evidence_refs`. Trace matrices must use
   `links`, not `mappings`.
   For any user-requested requirement, architecture, RTL intent,
   directed-TB intent, UVM intent, assertion/coverage intent, or prototype
   intent change after the owning gate has a baseline, open a controlled
   change first with `change-open`. Record the affected requirements and
   artifact paths with `change-impact`; record the changed requirements before
   approval. The platform infers downstream nodes,
   verification, and whether `generate-docs` must be rerun. Approval is
   blocked until the impact record has non-placeholder requirements, artifacts,
   downstream nodes, required verification, rollback, and docset
   decision. After approval, update front-door sources, rerun
   `requirements-frontdoor-check`, regenerate the docset
   when required, rerun the affected gate with `--change-id`, and close the
   change with trace evidence.
   Review Agent findings must be structured in
   `work/docparse/review/role_findings.yaml`; run `review-check` after Review
   and before DocParse/Loop gates. Open critical/high findings block develop
   gates, and open medium findings also block release gates. `fixed` is not a
   closed status; blocking findings must become `verified`, `closed`, or
   `waived` after Review evidence. Arbtr chooses the feedback target; the owning
   agent edits only its owned artifact set, then the flow reruns forward through
   Review.
5. If the design has register-heavy control logic, route to `$register-spec-and-ral` before broad RTL/UVM generation.
6. Before entering Loop1, read `$rtl-architecture-and-gen` and its style guide once for constraints. Keep the directed full-function TB plan in `output/tb/full_function_test_plan.md`. Directed TBs must emit `HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|...` and `HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|...` events plus waveform window markers (`HDLFLOW_WAVE_BEGIN`/`HDLFLOW_WAVE_END` or `HDLFLOW_WAVE_WINDOW`) so `loop1-refresh-reports` and `loop1-waveform-gate` can both produce evidence. Loop1 WLF/VCD capture is a deliverable under `output/sim/loop1/wave/`; analysis must use those files in place and must not make `_runtime` waveform copies. The waveform gate uses the recommended pywellen backend and `work/loop1_rtl_tb/config/top_wave_manifest.yaml` to generate `output/reports/loop1/waveform_query_report.md`, `waveform_gate.json`, and `query_transcript.json`. The semantic waveform gate must pass at develop/release level before Loop2 entry. After each `.v` file is generated or edited, run `python -m hdlflow.cli rtl-skill-audit --project <project>`; the platform-generated `output/reports/loop1/rtl_skill_audit.md` is the only valid RTL skill audit evidence. Review Agent must then add a structured finding for every formal implementation surface it reviews: RTL cites the audit and RTL skill/style guide, directed TB cites the full-function plan and Loop1/ModelSim skill, UVM cites `uvm-env-and-test-build`, and Loop3 cites the prototype preflight/report refresh commands.
   After a Loop1 gate baseline exists, RTL behavior changes, directed TB model
   changes, protocol timing model changes, and test plan changes must be
   backed by the controlled front-door change flow before editing
   `output/rtl/`, `output/tb/`, or `work/loop1_rtl_tb/sim/`.
7. If module planning is incomplete or RTL needs creation or fixes, route to `$rtl-architecture-and-gen`.
8. Enter Loop2 only after Loop1 has a passing gate manifest and fresh Loop1 evidence. If UVM environment, sequences, or tests are missing or stale, route to `$uvm-env-and-test-build`.
   After a Loop2 gate baseline exists, UVM model, sequence, scoreboard,
   coverage, assertion, or test-intent changes are requirement changes until
   proven otherwise and must use the same controlled front-door change flow.
9. If simulation evidence is needed, route to `$modelsim-run-triage-debug`.
10. If the base loop is stable and the user asks for assertions or coverage closure, route to `$assertion-and-coverage`.
11. Before entering `work/loop3_fpga_proto`, confirm Loop2 has passed and run the Loop3 database/plan preflight path before any board or tool script generation. The required platform entry points are `prototype-preflight`, `validate-prototype-plan`, `generate-xdc`, `generate-ps-pl-bd`, `generate-vitis-boot`, and `loop3-refresh-reports`; board serial verification uses the platform wrapper `env/tool/scripts/Invoke-HdlLoop3BoardVerify.ps1` with project default Vivado/Vitis/report paths. After Vivado/Vitis/board evidence changes, rerun `python -m hdlflow.cli loop3-refresh-reports --project <project>` before `run-gate --node work/loop3_fpga_proto`. Their reports must remain under `output/reports/loop3/` and generated FPGA files under `output/fpga/`.
    If a user asks to change prototype verification intent, board stimulus,
    PS/PL drive or sample paths, debug observation points, or stress scenarios
    after any gate baseline exists, open a controlled change first with
    `change-open`, then record impact and approval. Next update the
    requirements front-door sources, rerun `requirements-frontdoor-check`, and
    regenerate the docset with
    `python -m hdlflow.cli generate-docs --project <project>`. Only after
    those records exist may the flow edit `work/loop3_fpga_proto/board_tests/`,
    `work/loop3_fpga_proto/board_profiles/`,
    `work/loop3_fpga_proto/scripts/`, or generated FPGA source roots. Do not
    change RTL, board plans, or Vivado/Vitis files directly from chat intent.
    Launch Vivado only through `env/tool/scripts/Invoke-HdlVivado.ps1`; the wrapper pins
    Vivado journal/log output under `output/fpga/vivado/logs`. `vivado.jou`,
    `vivado.log`, or `vivado_*.backup.*` files in the project root are invalid
    Loop3 artifacts.
12. At the end of each meaningful iteration, update `work/memory/` and summarize the next step.

## Current-Stage Decision

Use these signals to decide the stage quickly:

- No project directory yet: bootstrap stage
- `input/spec/` changed or `work/docparse/structured_spec/`, `architecture/`, `verification/`, or `prototype/` is stale: requirements front-door stage
- `output/rtl/` is empty or architecture is unresolved: RTL stage
- `output/uvm/` is empty or tests do not reflect `test_intent.yaml`: UVM stage
- `work/loop1_rtl_tb/sim/` or `work/loop2_uvm/sim/` exists and user wants compile, run, or debug: ModelSim stage
- Coverage or assertions requested after stable configuration verification runs: quality stage

## Session Discipline

- Treat repository files as the source of truth, not chat memory.
- Prefer small forward steps and persist the result before switching topics.
- If the correct next action is ambiguous, state the branch point and choose the smallest safe step.
- Never silently overwrite generated or hand-written project files without checking what already exists.
- Do not create sidecar scope, implementation analysis, design blueprint, or design draft Markdown as a substitute for the requirements front door; put that content into SRS, decomposition, architecture YAML, verification YAML, prototype YAML, and the generated docset.
- Do not modify gate policy, gate reports, or temporary artifacts to force progress inside an automatic loop. Do not modify guard code for the same purpose. AI agents must not automatically change gate rules. If a gate appears wrong, record the concern in memory and abort or escalate; gate maintenance is a separate explicit platform task with regression evidence.
- End by updating the checkpoint through the local PowerShell helper when practical.

## References

- Read [references/stage-map.md](references/stage-map.md) when deciding stage handoff or recovery behavior.
