# 03_Loop2_UVM_Verify

Owns UVM environment, full regression, coverage, and bug closure.

- `05_Output/uvm/` - canonical editable UVM environment, agents, register model, sequences, and tests.
- `sim/` - UVM compile and regression scripts.
- `_runtime/` - disposable compile, wave, and log outputs.
- `bug_tracking/` - bug triage, root cause, fix evidence, and closure records.
- `coverage_tracking/` - coverage closure records and waivers.
- `05_Output/reports/loop2/` - final Loop2 reports.

RTL changes discovered in Loop2 are made in `05_Output/rtl` and must be rerun through Loop1 and Loop2.
