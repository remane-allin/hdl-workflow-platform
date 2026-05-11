---
name: register-spec-and-ral
description: Convert structured register specifications into consistent CSR artifacts for RTL and verification. Use when the design has a significant register map and the user wants clean register ownership, RAL alignment, or preparation for generators such as RgGen.
---

# Register Spec And RAL

Use this skill when the control plane is substantial enough that register discipline matters.

## Inputs

- `01_DocParse/structured_spec/register_map.yaml`
- `01_DocParse/structured_spec/interface_spec.yaml`
- existing register RTL or UVM RAL files when present

## Workflow

1. Validate register names, offsets, widths, access types, reset values, and field ownership.
2. Resolve missing semantics in `01_DocParse/req_decompose/` before generating broad artifacts.
3. Shape the register description so it can drive:
   - RTL register blocks
   - UVM RAL or mirrored register models
   - software-facing headers if the project later needs them
4. If the project uses RgGen, prepare the normalized map in a generator-friendly form instead of inventing a one-off schema.
5. Keep `01_DocParse/trace_matrix/req_to_rtl.yaml` and `01_DocParse/trace_matrix/req_to_test.yaml` aligned with register intent.

## Rules

- Register semantics belong to the spec, not to whichever implementation came first.
- Keep field behavior explicit for RO, RW, W1C, sticky, pulse, and side-effect fields.
- Do not let the UVM model drift away from the RTL view of the same register file.

## Completion Gate

This skill is complete when:

- the register map is internally consistent
- downstream RTL and UVM work have a clear CSR contract
- any generator assumptions are documented

## References

- Read [references/register-map-contract.md](references/register-map-contract.md) when validating a control-plane heavy design.
