---
name: mineru-spec-normalizer
description: Ingest HDL project datasheets and protocol documents with the platform-approved MinerU high-precision API path, then normalize parsed content into front-door YAML artifacts.
---

# MinerU Spec Normalizer

Use this skill when an active HDL project needs document parsing evidence for
the requirements front door.

## Workspace Contract

Resolve the active workspace and project from the current directory or
`HDL_PROJECT_PATH`. Do not hard-code project names or user-specific paths.

Raw source documents live under:

- `input/spec/`

Formal DocParse evidence must live under:

- `work/docparse/parsed/mineru_extract/`

## Parser Rule

Use only MinerU high-precision API evidence for this HDL workflow:

```powershell
mineru-open-api extract <input> -o <project>\work/docparse\parsed\mineru_extract
```

The formal provenance must show the high-precision API task path, not the fast
channel. Acceptable API endpoint evidence includes:

- `/api/v4/extract/task`
- `/api/v4/file-urls/batch`

Do not use the fast channel for this workflow. Do not split long PDFs into fast
page ranges. Do not treat `parsed/mineru/`, `parsed/local_text/`, or temporary
side outputs as gate evidence.

The output directory must contain `provenance.yaml` with:

```yaml
tool: mineru-open-api
command: extract
channel: mineru-open-api high_precision_api
api_mode: high_precision
api_endpoints:
  - /api/v4/file-urls/batch
  - /api/v4/extract/task
```

After parsing, fill the formal requirements-frontdoor artifacts rather than
creating sidecar scope, implementation analysis, design blueprint, or design
draft Markdown files.

## Document Analysis Rule

Use a Superpowers-style analysis loop before marking DocParse READY:

1. Inventory every raw source document and parser output.
2. Split each source into bounded analysis units such as chapters, tables,
   register sections, timing sections, protocol flows, and board constraints.
3. Extract requirement candidates from each unit with source evidence.
4. Record ambiguities, contradictions, and rejected interpretations.
5. Cross-check requirements against architecture, verification, prototype, and
   trace artifacts.
6. Verify the evidence map before claiming the document analysis is complete.

Write this machine-readable analysis to:

- `work/docparse/structured_spec/document_analysis.yaml`

For READY status, the file must contain non-empty `source_documents`,
`analysis_units`, and `evidence_map` entries. Each analysis unit should name its
`unit_id`, `source_ref`, `section`, short `summary`, and either
`extracted_requirements` or `evidence_refs`.

Use checker-compatible field names exactly. Source documents use `source_ref`,
`parser_output`, and `document_type`; analysis units use `unit_id`,
`source_ref`, `section`, `summary`, and either `extracted_requirements` or
`evidence_refs`. Open questions must be mapping entries with `id`, `question`,
`status`, and `resolution` or `answer` when closed; do not write bare question
IDs. Requirement trace files under `work/docparse/trace_matrix/` use `links`,
not `mappings`.

Minimal READY skeleton:

```yaml
source_documents:
  - source_ref: input/spec/source.pdf
    parser_output: work/docparse/parsed/mineru_extract/source.md
    document_type: datasheet
analysis_units:
  - unit_id: AU-001
    source_ref: work/docparse/parsed/mineru_extract/source.md
    section: Section or table name
    summary: Source-backed requirement facts.
    evidence_refs:
      - work/docparse/parsed/mineru_extract/source.md:1
evidence_map:
  - requirement_id: REQ-001
    evidence_refs:
      - AU-001
open_questions: []
question_review:
  status: REVIEWED
  reviewed_by: user-or-reviewer
  review_evidence: work/docparse/frontdoor/open_questions.md
  unresolved_count: 0
```

Normalize into these machine-readable structured spec files before any generated
docset document is written:

- `work/docparse/structured_spec/document_analysis.yaml`
- `work/docparse/structured_spec/interface_spec.yaml`
- `work/docparse/structured_spec/interface_timing.yaml`
- `work/docparse/structured_spec/register_map.yaml`
- `work/docparse/structured_spec/test_intent.yaml`
- `work/docparse/structured_spec/timing_rules.yaml`

Do not place operation notes, command records, or manual review commentary under
`work/docparse/parsed/mineru_extract/`; that directory is only for parser outputs
and `provenance.yaml`. Put operation logs, process issue records, and manual
review commentary under `work/docparse/review/`, for example
`docparse_operation_log.md`, `process_violation_record.md`,
`violation_record.md`, or `assumption_log.md`, so Review Agent can analyze
them without treating them as parser evidence.

Write normalized YAML in the platform-compatible subset: plain block mappings
and lists only. Do not use anchors, aliases, inline flow maps, or compact field
shorthand in machine-readable specs.
