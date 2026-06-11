# work/docparse

Owns the six-agent structured front door and the normalized design intent that
feeds all three engineering evidence loops.

- `architecture/` - ADD, RTL planning rules, module partition, interfaces, dataflow, state machines, timing model.
- `frontdoor/` - generated SRS, acceptance criteria, forbidden design list, and reviewed open questions.
- `verification/` - module/system verification plan, assertion intent, coverage intent.
- `prototype/` - FPGA feasibility, clocks, pins, resources, PS/PL boundary intent.
- `structured_spec/` - compact machine-readable specs consumed by generators.
- `req_decompose/` - decomposed features, tasks, and acceptance checks.
- `review/` - Review Agent findings, Arbtr decisions, assumptions, disputes, and spec diffs.
- `trace_matrix/` - requirement-to-architecture/RTL/test/prototype trace matrices.

Document parsing evidence is accepted only when produced by the MinerU
high-precision API path and stored under `parsed/mineru_extract/` with
`parsed/mineru_extract/provenance.yaml`. The provenance must include
`/api/v4/extract/task` or `/api/v4/file-urls/batch`; fast-channel page splits
are not accepted as completion evidence.

Chat-only requirements do not use MinerU. Capture the request under
`input/spec/` with `source_type: chat_request`, then bind it from
`structured_spec/document_analysis.yaml` with
`parser_output: manual_chat_capture`, non-empty `analysis_units`, and non-empty
`evidence_map`.

`structured_spec/document_analysis.yaml` must use the platform checker field
names: `source_documents[].source_ref`, `parser_output`, `document_type`,
`analysis_units[].unit_id`, `source_ref`, `section`, `summary`, and either
`extracted_requirements` or `evidence_refs`. `open_questions` entries are
mappings, not bare IDs. Requirement trace files under `trace_matrix/` use
`links`, not `mappings`.

Run the front-door scaffold before broad RTL, UVM, or prototype work:

```powershell
python -m hdlflow.cli requirements-frontdoor-init --project <project> --status DRAFT
python -m hdlflow.cli requirements-frontdoor-check --project <project>
python -m hdlflow.cli review-check --project <project> --level develop
```

Loop1, Loop2, and Loop3 must share this same analysis output. Do not edit these
files merely to match a broken implementation. Review must classify the defect,
Arbtr must route the feedback target, and only the owning agent may edit its
owned artifacts.

Review findings are machine-readable. Use `role_findings.yaml` structured
entries with severity, lifecycle status, affected artifact, evidence, impact,
recommendation, and route target. Develop gates block open critical/high
findings; release gates also block open medium findings. A finding with
`status: fixed` is still unclosed and blocking at the relevant severity until
Review marks it `verified`, `closed`, or `waived`.

Do not create sidecar scope, implementation analysis, design blueprint, or
design draft Markdown files during requirements parsing. Put design intent into
`frontdoor/` and the structured YAML files, then generate the user-readable
design document through `python -m hdlflow.cli generate-design-doc`. Do not put
generated front-door or decomposition files under `input/spec/`.
Do not hand-write `output/reports/design/design_rule_and_architecture.md` or
`output/reports/design/design_doc_manifest.json`; the generator writes both
after frontdoor and review checks pass.

Architecture planning must reference `architecture/rtl_planning_rules.yaml`,
which is derived from `env/rule/skills/rtl-architecture-and-gen/SKILL.md` and its
Verilog RTL style guide. Loop1 RTL generation is blocked unless that planning
policy is present and READY.
