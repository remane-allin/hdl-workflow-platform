# RKV I2C Reference Profile

## Source

Reference directory:

```text
rkv_v2pro_i2c-RKV_I2C_TB_00/rkv_i2c_tb
```

The reference is useful for framework shape, but it contains many TODOs and
empty element sequences. Treat it as an architectural profile, not as a source
tree to copy into projects.

## Reusable Structure

The reference uses these layers:

```text
agents/lvc_apb3/      APB VIP
agents/lvc_i2c/       I2C VIP
cfg/                  top configuration
cov/                  coverage model
env/                  env, scoreboard, virtual sequencer, package
reg/                  generated RAL model
seq_lib/              virtual sequences
seq_lib/elem_seqs/    APB and I2C element sequences
tb/                   top-level interface and UVM testbench
tests/                base test and scenario tests
sim/                  flist, do script, Makefile
```

## Positive Patterns To Reuse

- Keep a thin top package include hub in `env/rkv_i2c_pkg.sv`.
- Split protocol VIPs from the project env.
- Use a top config object to carry APB/I2C/RAL configuration.
- Use a virtual sequencer to route APB and I2C sub-sequencers.
- Keep RAL in `reg/` and include it before env/sequence code.
- Put APB and I2C element sequences under `seq_lib/elem_seqs/`.
- Put clock/reset/DUT/open-drain bus hookup in `tb/rkv_i2c_tb.sv`.
- Publish virtual interfaces from HDL top to UVM with `uvm_config_db`.
- Use `sim/rkv_i2c.flist` for RTL and compile UVM in dependency order.

## Gaps Not To Copy Blindly

- `rkv_i2c_env.sv` declares agents, scoreboard, coverage, RAL, adapter, and
  predictor, but does not create/connect them.
- `rkv_i2c_scoreboard.sv` is empty.
- `rkv_i2c_cgm.sv` is empty.
- `rkv_i2c_config.sv` has TODO configuration tasks.
- Some element sequence files are empty.
- `tb/rkv_i2c_tb.sv` calls `run_test("rkv_i2c_quick_reg_access_test")` directly
  even though the sim script also passes `+UVM_TESTNAME`. Project templates
  should prefer `run_test();` and let scripts select tests.

## Database Decision

The Test template database preserves the RKV framework shape, but project
templates must be filled with spec-derived behavior:

- actual monitor analysis ports,
- non-empty scoreboard checks,
- legal functional coverage,
- deterministic virtual sequences,
- RAL map and adapter connections when registers exist,
- final Loop2 reports with fresh ModelSim evidence.
