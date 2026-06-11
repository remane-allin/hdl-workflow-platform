# Spec Normalization Prompt

Convert parsed MinerU output into stable normalized files:

- `document_analysis.yaml`
- `interface_spec.yaml`
- `register_map.yaml`
- `timing_rules.yaml`
- `test_intent.yaml`

Rules:

- keep facts separated from assumptions
- record unknowns in `work/docparse/review/assumption_log.md`
- prefer exact signal names from the document
- preserve page or section references when available
- do not let raw markdown become the final source of truth
- use platform checker field names exactly:
  `source_documents[].source_ref`, `parser_output`, `document_type`,
  `analysis_units[].unit_id`, `source_ref`, `section`, `summary`, and
  `extracted_requirements` or `evidence_refs`
- write `open_questions` as mapping entries, not bare IDs; a READY file needs
  `question_review.status: REVIEWED` and `unresolved_count: 0`
- write trace matrices with `links`, not `mappings`
- do not create or rely on `work/docparse/parsed/local_text/` or other
  temporary parser output when external documents exist
