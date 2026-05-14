# HDL Project Template

This template uses a linear, numbered pipeline layout.

## Node Contract

- `00_SPEC` is the only raw input source.
- `01_DocParse` owns parsing, normalized specs, decomposition, and trace matrices.
- `02_Loop1_RTL_TB` owns RTL and directed TB bring-up.
- `03_Loop2_UVM_Verify` owns UVM, coverage, and bug closure.
- `04_Loop3_FPGA_Prototype` owns FPGA implementation and board evidence.
- `05_Output` owns the canonical editable source trees and signed, gate-approved deliverables.
- `memory` owns indexed archive memory, local transient memory, and recovery records.
- `change_control` owns design change requests, impact analysis, approvals, and downstream trace updates.
- `_archive` owns inactive history.

Node-local `_runtime/` folders are disposable.

## Hard Rules

- A project instance is valid only when created through the unified script path.
  The generated `project_scaffold.yaml` records that evidence.
- Loop3 FPGA prototype work starts with a local library/database preflight report.
- Loop3 PS_PL plans must pass `validate-prototype-plan` before BD, XDC, Vitis, or boot-image generation.
- Loop1 simulation entry is `02_Loop1_RTL_TB/sim/rtl_functional.do`.
- Loop2 simulation entries are under `03_Loop2_UVM_Verify/sim/`.
- Vivado artifacts live under `05_Output/fpga/vivado/`.
- Vitis artifacts live under `05_Output/fpga/vitis/`.
