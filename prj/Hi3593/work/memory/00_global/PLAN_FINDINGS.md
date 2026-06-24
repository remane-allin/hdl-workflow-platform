# Plan Findings

## 2026-05-27 Requirements Ready Rerun

- Temporary parsed evidence directory `work/docparse/parsed/local_text` was removed; MinerU high-precision evidence remains authoritative.
- Review findings use `verified` for closed high-severity items under the current checker.
- Trace matrices now use `links`, matching the current gate schema.
- Four prior questions were closed or marked not blocking for DocParse.

## 2026-06-16 UVM Structured Planning

- UVM planning authority is `work/docparse/verification/uvm_plan.yaml` plus `work/docparse/trace_matrix/req_to_uvm_intent.yaml`.
- The generated user-facing UVM plan is `output/docs/test/verification_plan.md`; sidecar Markdown plans under `output/tb`, `output/uvm`, or `work/docparse/verification` are forbidden.
- `work/docparse/doc_projection.yaml` must continue to project `uvm_plan.yaml` and `req_to_uvm_intent.yaml` into the verification plan before Loop2 implementation starts.

## 2026-06-24 Loop1 RX Decode Gap

- Latest Loop1 gate PASS proves the deterministic prototype RX event path only: RX input event -> generated prototype word -> RX FIFO -> SPI SO readback.
- `arinc429_rx.v` still uses event-level word injection and does not implement documented RIN1A/RIN1B symbol decode, bit-cell timing, 32-bit word assembly, RFLIP, or parity marking.
- Treat `work/memory/02_loop1/rx_decode_gap_20260624.md` as an open gap before claiming true ARINC RX decode or final RX signoff.
