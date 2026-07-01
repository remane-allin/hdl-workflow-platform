# work/docparse/frontdoor

Generated requirements front-door artifacts and the active baseline governance
model live here.

- `srs.yaml`
- `acceptance_criteria.yaml`
- `forbidden_designs.yaml`
- `contract.yaml`
- `baseline/`
- `intake/pending`, `intake/approved`, `intake/rejected`, `intake/merged`
- `templates/`
- `generated/active_*.generated.yaml`
- unresolved questions recorded in `work/docparse/structured_spec/document_analysis.yaml`

Keep `input/spec/` clean for user-provided source requirements only.
Downstream Loop1/Loop2/Loop3/final execution is locked while pending intake or
unmerged approved intake exists.
