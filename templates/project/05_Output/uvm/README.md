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
- `seq_lib/`: deterministic smoke and scenario virtual sequences.
- `seq_lib/elem_seqs/`: protocol or bus element sequences used by virtual sequences.
- `tests/`: base test, smoke test, baseline test, regression test.
- `tb/`: DUT interface and top-level UVM harness.
- `assertions/`: non-invasive SVA bind files.

Files with `.template` suffix are not compiled directly. Instantiate them with
project-specific names, module names, interfaces, transactions, and tests before
running `03_Loop2_UVM_Verify/sim/uvm_baseline.do`.

The reusable framework is registered in the local template database:

- `uvm.rkv_style_framework`
- `uvm.rkv_i2c_reference_profile`

Use the RKV I2C reference as a framework profile only. Do not copy its TODO
scoreboard, coverage, config, or empty element sequences into a project as
closure-ready verification code.
