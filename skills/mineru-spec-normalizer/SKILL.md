---
name: mineru-spec-normalizer
description: Ingest datasheets and design documents with MinerU, then convert the parsed output into stable normalized YAML files for RTL and UVM work. Use when the user provides a datasheet, PDF, protocol note, or asks to refresh structured specs after document changes.
---

# MinerU Spec Normalizer

Use this skill when the project needs document-driven facts, not guesses.

## Scope

This skill owns:

- `00_SPEC/raw_docs/`
- `01_DocParse/mineru_raw/`
- `01_DocParse/structured_spec/`
- `01_DocParse/req_decompose/`

It does not generate RTL, UVM, or run ModelSim.

## Workflow

1. Read `config/projects/<project_name>/project_config.yaml` and confirm the document directories.
2. Inspect `00_SPEC/raw_docs/` for source files and versions.
3. Choose MinerU mode:
   - `flash` for quick extraction and short documents
   - `api` for larger or higher-fidelity extraction
4. Use the configured MinerU command or project-specific helper, then store raw parser output under `01_DocParse/mineru_raw/`.
5. Review the latest parsed markdown, JSON, tables, and metadata.
6. Normalize the parsed results into:
   - `interface_spec.yaml`
   - `register_map.yaml`
   - `timing_rules.yaml`
   - `test_intent.yaml`
7. Put uncertainties into `01_DocParse/req_decompose/assumption_log.md` and change impact into `01_DocParse/req_decompose/spec_diff.md`.
8. Update `memory/OPEN_QUESTIONS.md` when a document contradiction affects downstream work.

## Normalization Rules

- Separate facts from assumptions.
- Preserve signal names, reset polarity, widths, offsets, and timing language from the source when available.
- Prefer structured tables over prose when both exist.
- If the design has a CSR plane, shape `register_map.yaml` so it can later feed `$register-spec-and-ral`.
- Do not let raw markdown become the final authority once normalized YAML exists.

## Output Quality Gate

Before declaring the spec normalized, confirm:

- interfaces and clocks are named
- register ownership and access types are explicit when applicable
- reset behavior is captured
- test intent includes baseline and corner coverage ideas
- open ambiguities are tracked instead of silently guessed

## References

- Read [references/normalized-yaml-contract.md](references/normalized-yaml-contract.md) for the expected YAML structure.
