# work/loop2_uvm

Owns UVM environment, full regression, coverage, and bug closure.

- `output/uvm/` - canonical editable UVM environment, agents, register model, sequences, and tests.
- `sim/` - UVM compile and regression scripts.
- `_runtime/` - disposable compile, wave, and log outputs.
- `bug_tracking/` - bug triage, root cause, fix evidence, and closure records.
- `coverage_tracking/` - coverage closure records and waivers.
- `output/reports/loop2/` - final Loop2 reports.
- `output/reports/loop2/preflight/database_preflight.md` - generated
  template-library preflight evidence. Build it with
  `python -m engine.hdlflow.cli loop2-database-preflight --workspace . --project prj/<project_name>`.
- `_runtime/loop2_bindings.sqlite` - generated requirement-to-UVM/evidence
  binding database. Build it with
  `python -m engine.hdlflow.cli loop2-build-bindings --workspace . --project prj/<project_name>`.

RTL changes discovered in Loop2 are made in `output/rtl` and must be rerun through Loop1 and Loop2.
