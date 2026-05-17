---
name: hdl-requirements-decompose
description: Decompose normalized HDL specs and parsed design documents into hierarchical requirements, executable RTL or verification subtasks, and scored checklists. Use when the user wants a datasheet, protocol spec, or normalized YAML turned into epics, features, tasks, acceptance checks, feature backlog items, and requirement scorecards.
---

# HDL Requirements Decompose

Use this skill when the project needs a requirement baseline before broad RTL or UVM work.

## Scope

This skill owns the transformation from:

- `01_DocParse/structured_spec/*.yaml`
- `01_DocParse/architecture/*.yaml`
- `01_DocParse/verification/*.yaml`
- `01_DocParse/prototype/*.yaml`
- user requirement notes

into:

- `00_SPEC/requirements/requirements.json`
- `00_SPEC/requirements/requirements.md`
- `00_SPEC/requirements/decomposition_notes.md`
- `loop/feature_backlog.json`
- `loop/scorecard.json`

It can also suggest entries for `loop/bug_backlog.json` when the decomposition reveals known open risk areas.

## When To Use

Use this skill when the user says things like:

- "decompose this document into RTL tasks"
- "split the spec into features and implementation tasks"
- "create a requirements checklist"
- "turn the normalized spec into backlog items"
- "build acceptance checks before coding"

Do not use this skill for detailed RTL coding, UVM coding, or direct ModelSim log triage.

## Workflow

1. Read `config/projects/<project_name>/project_config.yaml`.
2. Read the latest normalized spec files under `01_DocParse/structured_spec/`.
3. If needed, inspect the five-role front-door outputs under `01_DocParse/architecture/`, `verification/`, and `prototype/`.
4. Identify top-level epics from protocol areas, functional blocks, register groups, or document chapters.
5. Split each epic into features that can map to real engineering ownership.
6. Split each feature into executable tasks with:
   - clear titles
   - owner layers such as `rtl`, `tb`, `uvm`, `doc`, or `integration`
   - acceptance checks
   - dependency references
   - score placeholders
7. Write or update `requirements.json`.
8. Translate the executable tasks into `loop/feature_backlog.json`.
9. Regenerate `requirements.md` through the local tooling when appropriate.
10. Refresh `loop/scorecard.json` after the requirement baseline changes.

## Decomposition Rules

- Prefer one epic per meaningful subsystem, protocol slice, or requirement family.
- Prefer one feature per coherent implementation or verification theme.
- Prefer one task per bounded unit of engineering work.
- Use the normalized spec as the authority.
- If the source is ambiguous, record the ambiguity in `decomposition_notes.md` instead of inventing certainty.
- RTL-first projects should still include later verification tasks, but the first actionable tasks should usually target `rtl` and `tb` before `uvm`.

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
