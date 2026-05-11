# HDL Project Template

This template uses a linear, numbered pipeline layout.

## Node Contract

- `00_SPEC` is the only raw input source.
- `01_DocParse` owns parsing, normalized specs, decomposition, and trace matrices.
- `02_Loop1_RTL_TB` owns RTL and directed TB bring-up.
- `03_Loop2_UVM_Verify` owns UVM, coverage, and bug closure.
- `04_Loop3_FPGA_Prototype` owns FPGA implementation and board evidence.
- `05_Output` owns the canonical editable source trees and signed, gate-approved deliverables.
- `_archive` owns inactive history.

Node-local `_runtime/` folders are disposable.
