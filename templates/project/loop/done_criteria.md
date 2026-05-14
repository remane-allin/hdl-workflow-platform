# Done Criteria

These are the stop conditions for the numbered `Test` three-loop HDL flow.

## Loop1

1. RTL/TB compile has zero error and zero unwaived blocking warning.
2. Directed functional simulation passes with a self-checking pass marker.
3. No open critical or major Loop1 bug remains.
4. Requirement-to-RTL and requirement-to-test trace is updated.
5. `05_Output/reports/loop1/` contains the current evidence.

## Loop2

1. `loop2-database-preflight` creates `05_Output/reports/loop2/preflight/database_preflight.md`
   from `library/.local/library.sqlite` and finds the required UVM template entries.
2. `03_Loop2_UVM_Verify/sim/compile.do` passes.
3. `uvm_baseline.do` compiles the project UVM package and runs a deterministic baseline.
4. `regression.do` passes with zero `UVM_ERROR`, zero `UVM_FATAL`, and zero assertion failure.
5. The scoreboard/reference model is derived from `01_DocParse/structured_spec`, not from current DUT quirks.
6. Code, functional, and requirement coverage meet `config/flow_policy.yaml` or have approved waivers.
7. Bug closure evidence records root cause, changed files, selected tests, and regression evidence.
8. `loop2-build-bindings` creates `03_Loop2_UVM_Verify/_runtime/loop2_bindings.sqlite`
   from the current requirement, UVM, and evidence artifacts.
9. `05_Output/reports/loop2/` contains the current evidence.

Directed RTL/TB regression is supporting evidence only. It cannot close Loop2
without UVM compile, UVM baseline, UVM regression, scoreboard, coverage, and
trace evidence.

## Loop3

1. Loop2 exit is PASS before FPGA implementation starts.
2. Vivado synthesis and implementation pass.
3. Timing and DRC meet `config/flow_policy.yaml` or have approved waivers.
4. Board smoke/prototype evidence is captured under `05_Output/reports/loop3/`.
5. If RTL changed during Loop3, Loop1 and Loop2 reran before final signoff.
