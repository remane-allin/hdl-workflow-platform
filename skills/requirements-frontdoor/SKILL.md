---
name: requirements-frontdoor
description: Run the five-role 00_SPEC to 01_DocParse requirements analysis front door, producing PM, architecture, verification, prototype, review, and trace artifacts before Loop1/Loop2/Loop3 consume the design intent.
---

# Requirements Front Door

Use this skill before broad RTL, UVM, or FPGA prototype work.

## Roles

- Coordinator: workflow state, role handoff, review collection, memory checkpoint.
- PM: SRS, ambiguity removal, acceptance criteria, boundary conditions.
- Architect: dataflow, state machines, timing model, module partition, interface contracts.
- Verification Planner: module/system verification plan, assertion intent, coverage intent.
- Prototype Planner: FPGA feasibility, resources, pins, clocks, resets, PS/PL boundary.

## Workflow

1. Read `00_SPEC/requirements/` and any normalized specs already present.
2. Run `python -m hdlflow.cli requirements-frontdoor-init --project <project> --status DRAFT` if artifacts are missing.
3. Fill or refresh:
   - `00_SPEC/requirements/srs.yaml`
   - `01_DocParse/architecture/*.yaml`
   - `01_DocParse/verification/*.yaml`
   - `01_DocParse/prototype/*.yaml`
   - `01_DocParse/review/*.yaml`
   - `01_DocParse/trace_matrix/req_to_*.yaml`
4. Promote artifact `status` values to `READY` only after cross-role conflicts are resolved.
5. Run `python -m hdlflow.cli requirements-frontdoor-check --project <project>`.
6. Run `python -m hdlflow.cli run-gate --project <project> --node docparse --level develop`.

## Output Rule

Markdown files are for human review. YAML files are the machine-readable source
for gates, traceability, and Loop1/Loop2/Loop3 handoff.
