---
name: requirements-frontdoor
description: Run the isolated six-agent Spec -> Arch -> Exec -> Sim -> Review -> Arbtr front door, producing executable spec, architecture, implementation boundary, simulation intent, review, arbitration, and trace artifacts before Loop1/Loop2/Loop3 consume design intent.
---

# Requirements Front Door

Use this skill before broad RTL, UVM, simulation, or FPGA prototype work.

## Agents

- Spec Agent: owns requirements, protocol originals, metric parameters, executable chip Spec, interface timing, and forbidden design boundaries.
- Arch Agent: owns module topology, bus architecture, hierarchy partition, throughput planning, module interfaces, and dataflow.
- Exec Agent: owns Verilog RTL, module instantiation, complete functional directed TB, combinational logic, and sequential logic.
- Sim Agent: owns simulation stimulus, UVM, waveform sampling, simulator logs, coverage, waveform comparison, and Loop1/Loop2/Loop3 validation evidence.
- Review Agent: owns defect lists, severities, lifecycle status, risks, correction advice, compliance review, and root-cause routing. It does not edit Spec, architecture, RTL, or TB.
- Review Agent defect lists remain structured YAML records with lifecycle status and evidence.
- Arbtr Agent: owns global flow records, disputes, version baselines, iteration count, feedback routing, termination checks, and final freeze. It does not edit Spec, architecture, RTL, or TB.

## Flow

1. Read external datasheets, protocol specs, user requests, and human-authored requirements under `input/spec/`.
2. If any Spec, DocParse, or generated design baseline already exists, open a
   controlled requirement change before editing front-door source artifacts:
   run `python -m hdlflow.cli change-open --project <project> ...`, then record
   impact, approval, gate binding, and closeout through the platform commands.
   A chat confirmation is not enough authority to edit `input/spec/`
   or `work/docparse/{structured_spec,req_decompose,architecture,verification,prototype,trace_matrix}/`.
   Project-specific requirement updates must be written into those source
   artifacts first. Do not edit `env/tool/scripts/populate_*_frontdoor.py`, generator
   helpers, templates, or reports as a substitute for updating the project
   source artifacts.
   During this change flow, do not edit gate policy, gate guard code, project
   gate conditions, or gate reports to make the change pass; record suspected
   gate issues under `work/docparse/review/` or `work/memory/` and handle gate
   maintenance as a separate platform task.
3. Run `python -m hdlflow.cli requirements-frontdoor-init --project <project> --status DRAFT` if artifacts are missing.
4. Fill or refresh:
   - `work/docparse/frontdoor/srs.yaml`
   - `work/docparse/frontdoor/open_questions.md`
   - `work/docparse/frontdoor/forbidden_designs.yaml`
   - `work/docparse/structured_spec/document_analysis.yaml`
   - `work/docparse/structured_spec/interface_spec.yaml`
   - `work/docparse/structured_spec/interface_timing.yaml`
   - `work/docparse/structured_spec/register_map.yaml`
   - `work/docparse/structured_spec/test_intent.yaml`
   - `work/docparse/structured_spec/timing_rules.yaml`
   - `work/docparse/req_decompose/*.md` and `work/docparse/req_decompose/*.json`
   - `work/docparse/architecture/*.yaml`
   - `work/docparse/verification/*.yaml`
   - `work/docparse/prototype/*.yaml`
   - `work/docparse/review/*.yaml`
   - `work/docparse/trace_matrix/req_to_*.yaml`
   Use platform-checker field names exactly:
   `document_analysis.yaml.source_documents[]` uses `source_ref`,
   `parser_output`, and `document_type`; `analysis_units[]` uses `unit_id`,
   `source_ref`, `section`, `summary`, plus `extracted_requirements` or
   `evidence_refs`. Open questions are mapping entries, not bare IDs. Trace
   matrices use `links`, not `mappings`.
   `work/docparse/structured_spec/test_intent.yaml` must include
   `waveform_windows`, and `work/docparse/verification/verification_plan.yaml`
   must include `waveform_comparison`. These are Sim Agent planning artifacts,
   not Loop1 afterthoughts: they define which requirement windows need WLF/VCD
   evidence, which top-level signals/scopes are observed first, the trigger or
   time span, expected activity, and pass/fail criteria.
5. Before promoting artifacts to READY, Spec Agent must publish its unresolved doubts in `work/docparse/frontdoor/open_questions.md` and mirror them in `work/docparse/structured_spec/document_analysis.yaml.open_questions`. Send those questions to the user for review. Every question must be answered, accepted, waived, or marked not blocking, and `document_analysis.yaml.question_review` must record `status: REVIEWED`, `reviewed_by`, `review_evidence: work/docparse/frontdoor/open_questions.md`, and `unresolved_count: 0`. If there are no unresolved doubts, record that explicit zero-question review instead of leaving the field empty.
6. Promote artifact `status` values to `READY` only after Spec, Arch, Sim planning, Review, and Arbtr handoff fields are consistent and requirement questions are reviewed.
7. Run `python -m hdlflow.cli requirements-frontdoor-check --project <project>`.
8. Run `python -m hdlflow.cli review-check --project <project> --level develop`; critical/high findings must be verified, closed, or waived before the DocParse gate can pass. `fixed` means the owning agent claims a fix exists; it is still blocking until Review marks the finding `verified`, `closed`, or `waived`.
9. Run `python -m hdlflow.cli generate-design-doc --project <project>` only after steps 7 and 8 pass.
10. Run `python -m hdlflow.cli run-gate --project <project> --node docparse --level develop`.

## Reverse Iteration

Review classifies defects by layer. Arbtr selects exactly one feedback target
(`spec`, `arch`, `exec`, or `sim`) and records the route in memory. The owning
agent edits only its own artifacts, then the flow reruns forward from that
agent through Sim, Review, and Arbtr.

Each Review Agent defect in `work/docparse/review/role_findings.yaml` must be a
structured finding with id, severity, status, category, owner, artifact, issue,
impact, evidence, recommendation, and route_to. Status is one of open, routed,
fixed, verified, closed, or waived. Develop gates block unclosed critical/high
findings; release gates also block unclosed medium findings. The only closed
lifecycle statuses are `verified`, `closed`, and `waived`; `open`, `routed`,
and `fixed` remain blocking when their severity is in the active gate level. Do
not use a separate informal blocker list as the machine-readable source of
truth.

When implementation artifacts exist, Review Agent must include structured
formal-artifact review findings, even if the result is PASS. RTL review must
cite `output/reports/loop1/rtl_skill_audit.md`, the `rtl-architecture-and-gen`
skill or `verilog-rtl-style-guide`, and every RTL file name reviewed. Directed
TB review must cite `output/tb/full_function_test_plan.md` and the owning
Loop1/ModelSim skill evidence. UVM review must cite `uvm-env-and-test-build`
and every UVM file name reviewed. Loop3 review must cite `prototype-preflight`,
`validate-prototype-plan`, and `loop3-refresh-reports`. A handwritten PASS
statement without the platform audit and skill references is not review
evidence.

## Output Rule

Markdown files are for human review. YAML files are the machine-readable source
for gates, traceability, permissions, and Loop1/Loop2/Loop3 handoff.

The structured spec YAML files are the required machine-readable bridge
from DocParse into architecture and verification. Generate or update them before
writing the generated design document; never create the design document first and
then backfill these YAML files from prose.

The document analysis YAML is the first structured DocParse bridge. Build it
from a Superpowers-style loop: source inventory, bounded section analysis,
requirement extraction, ambiguity/contradiction recording, cross-role review,
and evidence-map verification. It must name raw documents, parser outputs,
analysis units, extracted requirements, and evidence references before READY.
Use this checker-compatible shape:

```yaml
source_documents:
  - source_ref: input/spec/example.pdf
    parser_output: work/docparse/parsed/mineru_extract/example.md
    document_type: datasheet
analysis_units:
  - unit_id: AU-001
    source_ref: work/docparse/parsed/mineru_extract/example.md
    section: Register table
    summary: Register defaults and access rules.
    extracted_requirements:
      - REQ-REG-001
evidence_map:
  - requirement_id: REQ-REG-001
    evidence_refs:
      - AU-001
open_questions:
  - id: Q-001
    owner_role: spec
    question: Confirm unresolved requirement detail.
    status: WAIVED
    resolution: Accepted as non-blocking for the current gate.
question_review:
  status: REVIEWED
  reviewed_by: user-or-reviewer
  review_evidence: work/docparse/frontdoor/open_questions.md
  unresolved_count: 0
```

Structured YAML must be readable by the platform checker. Avoid YAML anchors,
aliases, inline flow maps, and other shorthand that the gate parser cannot
round-trip; use plain lists and mappings with one field per line.

Document parsing evidence must be produced only by the MinerU high-precision API
path when external documents are used. MinerU output is written under
`work/docparse/parsed/mineru_extract/`. The directory must include
`provenance.yaml` declaring `tool: mineru-open-api`, `command: extract`,
`channel: mineru-open-api high_precision_api`, `api_mode: high_precision`, and
API endpoint evidence for `/api/v4/extract/task` or `/api/v4/file-urls/batch`;
local parser side outputs such as `parsed/local_text/` are not DocParse
completion evidence.

If the requirement source is chat-only, do not fake MinerU evidence. Store the
captured request under `input/spec/` with `source_type: chat_request`, and make
`work/docparse/structured_spec/document_analysis.yaml` reference it with
`parser_output: manual_chat_capture`, non-empty `analysis_units`, and non-empty
`evidence_map`. This is the only allowed DocParse exception to MinerU.

Do not write operation notes, manual command logs, or review commentary under
`work/docparse/parsed/mineru_extract/`, and do not link them from parser
`provenance.yaml`. Use `work/docparse/review/` for those records, including
`docparse_operation_log.md`, `process_violation_record.md`,
`violation_record.md`, or `assumption_log.md`, so Review Agent can record and
analyze process issues while parsed evidence remains parser output plus formal
provenance only.

Design documents are generated only by `python -m hdlflow.cli generate-design-doc`
after `requirements-frontdoor-check` passes with `READY` artifacts and
`review-check --level develop` has no unclosed blocking findings. ad hoc scope,
implementation analysis, design blueprint, or design draft files are not gate
artifacts. If generation fails, fix the named frontdoor/review blockers and
rerun the two checks; do not hand-write
`output/reports/design/design_rule_and_architecture.md` or
`output/reports/design/design_doc_manifest.json`.

The generated design document uses this canonical order:

- Chapter 0: project info, sync status, and change sync rules.
- Chapter 1: requirements, in/out scope, functional and non-functional requirements, top-level interfaces, sign-off criteria, and spec input inventory.
- Chapter 2: system architecture, module partitioning, data/control flow, clock/reset/CDC, and boundary conditions.
- Chapter 3: RTL file inventory, RTL rules, and per-module implementation notes.
- Chapter 4: verification architecture, Directed TB baseline checks, Loop1 waveform secondary-check planning, UVM components, coverage/SVA plan, UVM test matrix, and log format.
- Chapter 5: FPGA prototype mode, resources, PS-PL planning, prototype risks, and board test plan.
- Appendix A: requirement traceability matrix.

When normalizing YAML for the generator, canonical fields are preferred, but the
generator accepts common aliases so it does not drop valid front-door content:
`text/title/description`, `direction/type`, `protocol/description`,
`role/responsibility`, and `ports/signals`.

Any requirement or platform-controlled design change after a gate baseline must
use `change-open`, `change-impact`, `change-approve`, the gate `--change-id`
binding, and `change-close`. Approved change requests are not allowed to pass a
gate unless the gate is explicitly bound to that change ID.

Front-door source files must not be edited after a gate baseline until a change
request exists. Gate policy files and guard conditions must not be modified as
part of requirement-change execution; Review Agent records the process issue,
and Arbtr decides whether a separate platform-maintenance task is needed.
Populate/front-door helper scripts are not project requirement sources after a
baseline exists. If a confirmed requirement changes, update SRS, structured
spec, architecture, verification, prototype, and trace artifacts first, then run
the checker and generated design document path.

AI agents must not automatically modify gate rules, guard code, or protected
gate policy to make a project pass. Gate maintenance is a separate explicit
platform task with human direction, implementation review, and regression
evidence.

Formal requirements, verification plans, generated design documents, reports,
RTL, TB, UVM, and FPGA artifacts must avoid forbidden workflow vocabulary; the
`forbidden_formal_text` gate owns this check.
