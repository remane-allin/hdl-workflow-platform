# Loop2 UVM Template

This scaffold follows the `Test` workflow skill policy and the HI3593 project example:
keep the environment spec-driven, use an RKV-style layout, and make the
scoreboard/reference model check legal behavior from `01_DocParse/structured_spec`
instead of mirroring a broken DUT.

Recommended ownership:

- `cfg/`: environment and agent configuration objects.
- `agents/<protocol>/`: protocol transaction, sequencer, driver, monitor, agent.
- `cov/`: functional coverage and coverage collectors.
- `env/`: package include hub, virtual sequencer, scoreboard, reference model, env.
- `reg/`: optional RAL model and register bus adapter.
- `seq_lib/`: deterministic functional and scenario virtual sequences.
- `seq_lib/elem_seqs/`: protocol or bus element sequences used by virtual sequences.
- `tests/`: base test, full functional test, scenario test, regression test.
- `tb/`: DUT interface and top-level UVM harness.
- `assertions/`: non-invasive SVA bind files.

Template files are source patterns only; they are not compiled and must not
remain under `05_Output/uvm/` in a Loop2-ready project. Generate real
project-specific sources before running
`03_Loop2_UVM_Verify/sim/uvm_full_functional.do` as an entry check, then
`03_Loop2_UVM_Verify/sim/regression.do` for final evidence.

The reusable framework is registered in the local template database:

- `uvm.rkv_style_framework`
- `uvm.rkv_i2c_reference_profile`

Use the RKV I2C reference as a framework profile only. Do not copy its TODO
scoreboard, coverage, config, or empty element sequences into a project as
closure-ready verification code.
