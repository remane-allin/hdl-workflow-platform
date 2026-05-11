# Spec Normalization Prompt

Convert parsed MinerU output into stable normalized files:

- `interface_spec.yaml`
- `register_map.yaml`
- `timing_rules.yaml`
- `test_intent.yaml`

Rules:

- keep facts separated from assumptions
- record unknowns in `docs/review/assumption_log.md`
- prefer exact signal names from the document
- preserve page or section references when available
- do not let raw markdown become the final source of truth
