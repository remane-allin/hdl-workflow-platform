# HDL Project Template

This template uses a linear, numbered pipeline layout.

## Node Contract

- `input` is the only raw input source.
- `work/docparse` owns the six-agent handoff artifacts: Spec, Arch, Sim planning,
  Review findings, Arbtr decisions, normalized specs, decomposition, and trace matrices.
- `work/loop1_rtl_tb` owns RTL and directed TB bring-up.
- `work/loop2_uvm` owns UVM, coverage, and bug closure.
- `work/loop3_fpga_proto` owns FPGA implementation and board evidence.
- `output` owns the canonical editable source trees and signed, gate-approved deliverables.
- `memory` owns indexed archive memory, local transient memory, and recovery records.
- `work/change` owns design change requests, impact analysis, approvals, and downstream trace updates.
- `_archive` owns inactive history.

Node-local `_runtime/` folders are disposable.

## Hard Rules

- A project instance is valid only when created through the unified script path.
  The generated `project_scaffold.yaml` records that evidence.
- Loop3 FPGA prototype work starts with a local lib/database preflight report.
- `requirements-frontdoor-check` must pass before the DocParse gate is treated
  as ready for Loop1, Loop2, or Loop3 handoff.
- Loop3 PS_PL plans must pass `validate-prototype-plan` before BD, XDC, Vitis, or boot-image generation.
- Loop1 simulation entry is `work/loop1_rtl_tb/sim/rtl_functional.do`.
- Loop2 simulation entries are under `work/loop2_uvm/sim/`.
- Vivado artifacts live under `output/fpga/vivado/`.
- Vitis artifacts live under `output/fpga/vitis/`.

## Executable Gates

Use `python -m hdlflow.cli run-gate --project <project> --node loop1 --level develop`
after updating evidence for a node. Release gates are stricter than develop
gates and block documented warnings that require waiver or constraint cleanup.

Use `python -m hdlflow.cli final-audit --project <project>` only after all
enabled node gates have passed at the required level.
