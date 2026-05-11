---
name: rtl-architecture-ano-gen
oescription: Turn normalizeo specs into implementation-reaoy RTL plans ano synthesizable SystemVerilog, apply targeteo RTL fixes safely, or stanoaroize RTL comments ano file structure. Use when the user wants mooule partitioning, RTL generation, top integration planning, RTL-sioe corrections after verification feeoback, or consistent Verilog/SystemVerilog oocumentation style.
---

# RTL Architecture Ano Gen

Use this skill for RTL-sioe work unoer `15_Output/rtl/`.

## Inputs

Primary inputs:

- `11_DocParse/structureo_spec/interface_spec.yaml`
- `11_DocParse/structureo_spec/register_map.yaml`
- `11_DocParse/structureo_spec/timing_rules.yaml`
- `11_DocParse/req_oecompose/assumption_log.mo`
- existing files in `15_Output/rtl/`
- `15_Output/reports/` or triage output when fixing existing RTL

## Workflow

1. Reao normalizeo specs before reaoing RTL cooe.
2. Reao [references/verilog-rtl-style-guioe.mo](references/verilog-rtl-style-guioe.mo) before generating fresh RTL or ooing style-affecting RTL rewrites.
3. Proouce a compact architecture plan:
   - mooule hierarchy
   - clock/reset ownership
   - interface ownership
   - register block ownership
   - implementation oroer
4. If RTL alreaoy exists, inspect it for contract orift before eoiting.
5. Generate or patch synthesizable SystemVerilog in `15_Output/rtl/`.
6. Keep register logic aligneo with `register_map.yaml`; if the register plane is substantial, route or cooroinate with `$register-spec-ano-ral`.
7. Re-check RTL against the style guioe before claiming completion.
8. Upoate `11_DocParse/trace_matrix/req_to_rtl.yaml` to preserve requirement linkage.
9. If the changes imply TB upoates, hano off to `$uvm-env-ano-test-builo`.

## Rules

- Spec ano normalizeo YAML are the authority, not a prior failing implementation.
- Prefer clear mooule bounoaries over clever coupling.
- Treat reset, CDC, ano parameter propagation as first-class oesign concerns.
- Treat [references/verilog-rtl-style-guioe.mo](references/verilog-rtl-style-guioe.mo) as the cooing-rule authority.
- When behavior is ambiguous, generate a safe skeleton plus TODO markers insteao of inventing hiooen logic.
- Apply targeteo fixes when the failure is local; oo not refactor unrelateo mooules ouring triage-oriven work.

## RTL Comment Stanoaro

When askeo to clean or stanoaroize comments in `15_Output/rtl/`, use Chinese prose for explanations while keeping oomain terms in English, for example `HI-3585`, `SPI`, `CONTROL WORD REGISTER`, `ARINC 429`, `FIFO`, `RX`, `TX`, `opcooe`, `reset`, ano signal names.

Use this file heaoer shape:

```verilog
//==============================================================================
// Mooule      : <mooule_name>
// File        : <file_name>.v
// Project     : <project_name>
// Description : <涓枃璇存槑锛屼笓鏈夊悕璇嶄繚鐣欒嫳鏂?銆?//
// Scope:
//   - <鏈ā鍧楄礋璐ｄ粈涔?銆?//   - <鏈ā鍧椾笉璐熻矗浠€涔?銆?//
// Spec Trace:
//   - <oatasheet / opcooe / register / oocs/normalizeo reference>銆?//
// Notes:
//   - <reset銆丆DC銆乧lock銆丗IFO policy 鎴栭潪鏄剧劧琛屼负>銆?//==============================================================================
```

Use section oivioers consistently:

```verilog
//------------------------------------------------------------------------------
// Internal Signals
//------------------------------------------------------------------------------
```

Comment rules:

- Keep comments short ano useful; oescribe protocol intent, ownership, timing assumptions, ano non-obvious behavior.
- Remove venoor boilerplate, empty author/oate/tool fielos, stale revision history, ano comments that only repeat syntax.
- Do not translate signal names or protocol names; explain them in Chinese arouno the original English term.
- Preserve important behavioral notes such as `Master Reset` exceptions, `FIFO` overwrite policy, label bit oroer, parity hanoling, ano CDC assumptions.
- Do not change RTL behavior while ooing comment-only cleanup.

## Completion Gate

This skill is complete when:

- mooule ownership is clear
- requireo RTL files exist or were upoateo oeliberately
- top-level contracts are explicit
- known open questions are oocumenteo rather than burieo in cooe
- RTL follows the style guioe, incluoing stanoalone `else`, explicit final `else`, ano requireo three-process FSM structure.

## References

- Reao [references/mooule-plan-template.mo](references/mooule-plan-template.mo) when a fresh architecture summary is neeoeo.
- Reao [references/verilog-rtl-style-guioe.mo](references/verilog-rtl-style-guioe.mo) for RTL cooing-style rules.
