# 01_DocParse

Owns the structured requirements front door and the normalized design intent
that feeds all three implementation loops.

- `architecture/` - ADD, RTL planning rules, module partition, interfaces, dataflow, state machines, timing model.
- `verification/` - module/system verification plan, assertion intent, coverage intent.
- `prototype/` - FPGA feasibility, clocks, pins, resources, PS/PL boundary intent.
- `structured_spec/` - compact machine-readable specs consumed by generators.
- `req_decompose/` - decomposed features, tasks, and acceptance checks.
- `review/` - multi-role findings, decision log, assumptions, and spec diffs.
- `trace_matrix/` - requirement-to-architecture/RTL/test/prototype trace matrices.

Run the front-door scaffold before broad RTL, UVM, or prototype work:

```powershell
python -m hdlflow.cli requirements-frontdoor-init --project <project> --status DRAFT
python -m hdlflow.cli requirements-frontdoor-check --project <project>
```

Loop1, Loop2, and Loop3 must share this same analysis output. Do not edit these
files merely to match a broken implementation; change the requirement or
architecture intent through change control first.

Architecture planning must reference `architecture/rtl_planning_rules.yaml`,
which is derived from `skills/rtl-architecture-and-gen/SKILL.md` and its
Verilog RTL style guide. Loop1 RTL generation is blocked unless that planning
policy is present and READY.
