---
name: hdl-requirements-decompose
description: Decompose normalized HDL specs and parsed source documents into hierarchical requirements, executable RTL or verification subtasks, and scored checklists. Use when the user wants a datasheet, protocol spec, or normalized YAML turned into epics, features, tasks, acceptance checks, feature backlog items, and requirement scorecards.
---

# HDL Requirements Decompose

Use this skill when the project needs a requirement baseline before broad RTL or UVM work.

## Scope

This skill owns the transformation from:

- `work/docparse/structured_spec/*.yaml`
- `work/docparse/structured_spec/document_analysis.yaml`
- `work/docparse/architecture/*.yaml`
- `work/docparse/verification/*.yaml`
- `work/docparse/prototype/*.yaml`
- user requirement notes

into:

- `work/docparse/req_decompose/requirements.json`
- `work/docparse/req_decompose/requirements.md`
- `work/docparse/req_decompose/decomposition_notes.md`
- `work/docparse/req_decompose/requirements.json`
- `work/docparse/req_decompose/requirements.md`
- `work/docparse/req_decompose/module_plan.md`
- `work/docparse/req_decompose/path_partition.md`
- `work/docparse/req_decompose/decomposition_notes.md`
- `work/gates/feature_backlog.json`
- `work/gates/scorecard.json`

It can also suggest entries for `work/gates/bug_backlog.json` when the decomposition reveals known open risk areas.

## When To Use

Use this skill when the user says things like:

- "decompose this document into RTL tasks"
- "split the spec into features and implementation tasks"
- "create a requirements checklist"
- "turn the normalized spec into backlog items"
- "build acceptance checks before coding"

Do not use this skill for detailed RTL coding, UVM coding, or direct ModelSim log triage.

## Workflow

1. Read `prj/<project_name>/work/config/project_config.yaml`.
2. Read the latest normalized spec files under `work/docparse/structured_spec/`.
3. Read `work/docparse/structured_spec/document_analysis.yaml` first and use
   its `analysis_units`, `evidence_map`, ambiguities, and contradictions to
   avoid losing source-document context during decomposition.
4. If needed, inspect the multi-role front-door outputs under `work/docparse/architecture/`, `verification/`, and `prototype/`.
5. Identify top-level epics from protocol areas, functional blocks, register groups, or document chapters.
6. Split each epic into features that can map to real engineering ownership.
7. Split each feature into executable tasks with:
   - clear titles
   - owner layers such as `rtl`, `tb`, `uvm`, `doc`, or `integration`
   - acceptance checks
   - dependency references
   - score placeholders
8. Write or update decomposition artifacts under `work/docparse/req_decompose/`. Do not put generated decomposition files under `input/spec/`; that folder is only for user-provided requirement sources.
9. Translate the executable tasks into `work/gates/feature_backlog.json`.
10. Regenerate `requirements.md` through the local tooling when appropriate.
11. Refresh `work/gates/scorecard.json` after the requirement baseline changes.
12. Do not generate sidecar analysis files such as `design_blueprint.md`, `*_scope.md`, or `*_implementation_analysis.md`; design intent belongs in front-door YAML and the generated docset.

## Decomposition Rules

- Prefer one epic per meaningful subsystem, protocol slice, or requirement family.
- Prefer one feature per coherent implementation or verification theme.
- Prefer one task per bounded unit of engineering work.
- Use the normalized spec as the authority.
- Preserve each task's source evidence by carrying requirement IDs and
  `document_analysis.yaml` evidence references into decomposition notes or task
  acceptance checks.
- If the source is ambiguous, record the ambiguity in `decomposition_notes.md` instead of inventing certainty.
- RTL-first projects should still include later verification tasks, but the first actionable tasks should usually target `rtl` and `tb` before `uvm`.
- Every functional requirement that needs dynamic behavior evidence should carry a waveform planning hook: add or update `test_intent.yaml.waveform_windows` and `verification_plan.yaml.waveform_comparison` with observed top-level signals/scopes, trigger or time span, expected activity, and pass/fail criteria. If a requirement is not waveform-observable, record why in assumptions or decomposition notes.

## Task Quality Gate

Each generated task should ideally answer:

- what gets built or checked
- which layer owns it
- what "done" means
- what it depends on
- which files or modules it is likely to touch

If a task does not have a meaningful completion condition, refine it again.

## Output Quality Gate

Before declaring the decomposition usable, confirm:

- `requirements.json` has epics, features, and tasks
- `requirements.md` is readable as a checklist
- `feature_backlog.json` reflects executable work rather than vague goals
- tasks are not too broad to execute in one iteration
- major ambiguities are written down

## References

- Read [references/decomposition-patterns.md](references/decomposition-patterns.md) when deciding how to split a spec into epics, features, and tasks.
