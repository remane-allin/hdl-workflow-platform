---
name: rtl-architecture-and-gen
description: Turn normalized HDL specs into implementation-ready RTL plans and synthesizable Verilog-2001, apply targeted RTL fixes safely, or standardize RTL comments and file structure. Use when the user wants module partitioning, RTL generation, top integration planning, RTL-side corrections after verification feedback, or consistent HDL documentation style.
---

# RTL Architecture And Gen

Use this skill for RTL-side work under `05_Output/rtl/`.

## Inputs

Primary inputs:

- `01_DocParse/structured_spec/interface_spec.yaml`
- `01_DocParse/structured_spec/register_map.yaml`
- `01_DocParse/structured_spec/timing_rules.yaml`
- `01_DocParse/req_decompose/module_plan.md`
- `01_DocParse/architecture/*.yaml`
- existing files in `05_Output/rtl/`
- `05_Output/reports/` or triage output when fixing existing RTL

## Workflow

1. Read normalized specs before reading RTL code.
2. Read [references/verilog-rtl-style-guide.md](references/verilog-rtl-style-guide.md) before generating fresh RTL or doing style-affecting RTL rewrites.
3. Produce a compact architecture plan: module hierarchy, clock/reset ownership, interface ownership, official bus/protocol naming ownership, register block ownership, and implementation order.
4. If RTL already exists, inspect it for contract drift before editing.
5. Generate or patch synthesizable Verilog-2001 `.v` files in `05_Output/rtl/`.
6. Keep register logic aligned with `register_map.yaml`; if the register plane is substantial, route or coordinate with `$register-spec-and-ral`.
7. Re-check RTL against the style guide before claiming completion.
8. Update `01_DocParse/trace_matrix/req_to_rtl.yaml` to preserve requirement linkage.
9. If the changes imply TB or UVM updates, hand off to `$uvm-env-and-test-build`.

## Rules

- Spec and normalized YAML are the authority, not a prior failing implementation.
- RTL under `05_Output/rtl/` is Verilog-2001 `.v` only. Do not generate SystemVerilog constructs such as `logic`, `always_ff`, `always_comb`, `typedef enum`, interfaces, packages, or `.sv/.svh` RTL files.
- Directed Loop1 TB under `05_Output/tb/` is also Verilog-2001 `.v` only. SystemVerilog is reserved for UVM under `05_Output/uvm/`.
- Preserve official bus/protocol/IP signal names exactly as written in the vendor UG, protocol specification, or generated IP interface. Do not append local direction suffixes such as `_i` or `_o`, change case, translate, or otherwise rename official protocol boundary signals. If local direction clarity is needed, use a documented adapter or internal alias away from the official boundary.
- Prefer clear module boundaries over clever coupling.
- Treat reset, CDC, and parameter propagation as first-class design concerns.
- Treat [references/verilog-rtl-style-guide.md](references/verilog-rtl-style-guide.md) as the coding-rule authority.
- When behavior is ambiguous, generate a safe skeleton plus TODO markers instead of inventing hidden logic.
- Apply targeted fixes when the failure is local; do not refactor unrelated modules during triage-driven work.

## RTL Comment Standard

When asked to clean or standardize comments in `05_Output/rtl/`, use concise technical prose. Preserve signal names, register names, protocol names, reset names, and timing terms exactly.

Use this file header shape:

```verilog
//==============================================================================
// Module      : <module_name>
// File        : <file_name>.v
// Project     : <project_name>
// Description : <brief functional responsibility>
// Scope:
//   - <what this module owns>
//   - <what this module does not own>
// Spec Trace:
//   - <requirement / register / interface / normalized spec reference>
// Notes:
//   - <reset, CDC, clock, FIFO, latency, or non-obvious behavior>
//==============================================================================
```

Use section dividers consistently:

```verilog
//------------------------------------------------------------------------------
// Internal Signals
//------------------------------------------------------------------------------
```

Comment rules:

- Keep comments short and useful; describe protocol intent, ownership, timing assumptions, and non-obvious behavior.
- Remove vendor boilerplate, empty author/date/tool fields, stale revision history, and comments that only repeat syntax.
- Do not translate or rewrite signal names or protocol names.
- Do not translate, suffix, or rewrite official bus/protocol/IP signal names from the referenced UG or IP.
- Preserve important behavioral notes such as reset exceptions, FIFO overwrite policy, bit order, parity handling, and CDC assumptions.
- Do not change RTL behavior during comment-only cleanup.

## Completion Gate

This skill is complete when:

- module ownership is clear
- required RTL files exist or were updated deliberately
- top-level contracts are explicit
- known open questions are documented instead of buried in code
- RTL follows the style guide, including standalone `else`, explicit final `else`, and required three-process FSM structure when applicable
- official bus/protocol/IP boundary names match the referenced UG/IP naming, with no added `_i`/`_o` suffixes
- no `.sv` or `.svh` files exist under `05_Output/rtl/` or `05_Output/tb/`

## References

- Read [references/module-plan-template.md](references/module-plan-template.md) when a fresh architecture summary is needed.
- Read [references/verilog-rtl-style-guide.md](references/verilog-rtl-style-guide.md) for RTL coding-style rules.
