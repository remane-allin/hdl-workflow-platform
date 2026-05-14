# 01_DocParse

Owns document parsing and requirement processing.

- `structured_spec/` - normalized structured specs.
- `req_decompose/` - decomposed features, tasks, and acceptance checks.
- `parsed/mineru/` - retained MinerU parser output when source documents are ingested.
- `review/` - assumption logs and spec diffs before they become RTL/TB/UVM behavior.
- `trace_matrix/` - requirement-to-RTL/test/result trace matrices.

Do not edit `structured_spec/` to match a broken implementation. Loop1 and
Loop2 must treat these files as the source of intent.
