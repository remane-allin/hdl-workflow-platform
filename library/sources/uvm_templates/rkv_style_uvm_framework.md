# RKV-Style UVM Framework Template

## Use When

Use this template when Loop2 needs a maintainable UVM environment rather than a
directed testbench. It is the preferred structure for non-trivial protocols,
register-backed IP, bus bridges, DMA/FIFO blocks, and designs that need active
checking plus coverage.

## Directory Contract

```text
05_Output/uvm/
  cfg/
    PROJECT_uvm_defines.svh
    PROJECT_uvm_config.sv
  agents/
    PROTOCOL/
      PROJECT_PROTOCOL_item.sv
      PROJECT_PROTOCOL_sequencer.sv
      PROJECT_PROTOCOL_driver.sv
      PROJECT_PROTOCOL_monitor.sv
      PROJECT_PROTOCOL_agent.sv
  cov/
    PROJECT_coverage.sv
  env/
    PROJECT_scoreboard.sv
    PROJECT_virtual_sequencer.sv
    PROJECT_env.sv
    PROJECT_uvm_pkg.sv
  reg/
    PROJECT_reg_model.sv
    PROJECT_reg_adapter.sv
  seq_lib/
    elem_seqs/
      PROJECT_PROTOCOL_base_sequence.sv
    PROJECT_base_virtual_sequence.sv
    PROJECT_smoke_virtual_sequence.sv
    PROJECT_virtual_sequences.svh
  tests/
    PROJECT_base_test.sv
    PROJECT_smoke_test.sv
    PROJECT_full_regression_test.sv
    PROJECT_tests.svh
  tb/
    PROJECT_dut_if.sv
    tb_PROJECT_uvm.sv
  assertions/
    PROJECT_top_sva.sv
```

`reg/` is optional for pure datapath projects, but the directory and compile
path should exist so register-backed projects can add RAL without changing the
Loop2 harness.

## Package Pattern

`PROJECT_uvm_pkg.sv` is a thin include hub. It imports UVM, includes macros, and
then includes files in dependency order. It should not contain implementation
classes directly.

```systemverilog
package PROJECT_uvm_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"

  `include "PROJECT_uvm_defines.svh"
  `include "PROJECT_uvm_config.sv"

  `include "PROJECT_PROTOCOL_item.sv"
  `include "PROJECT_PROTOCOL_sequencer.sv"
  `include "PROJECT_PROTOCOL_driver.sv"
  `include "PROJECT_PROTOCOL_monitor.sv"
  `include "PROJECT_PROTOCOL_agent.sv"

  `include "PROJECT_reg_model.sv"
  `include "PROJECT_reg_adapter.sv"

  `include "PROJECT_coverage.sv"
  `include "PROJECT_scoreboard.sv"
  `include "PROJECT_virtual_sequencer.sv"
  `include "PROJECT_env.sv"
  `include "PROJECT_virtual_sequences.svh"
  `include "PROJECT_tests.svh"
endpackage
```

## Ownership Rules

- `cfg/` owns virtual interfaces, agent mode, timing knobs, reset policy, and
  shared enums or defines.
- `agents/<protocol>/` owns protocol item, sequencer, driver, monitor, and
  agent wiring. It does not own global test intent.
- `cov/` owns legal functional coverage. Coverage bins must map to spec intent.
- `env/` owns agent instantiation, scoreboard, coverage, virtual sequencer,
  RAL predictor/adapter hooks, and analysis connections.
- `reg/` owns RAL model and bus adapter when registers exist.
- `seq_lib/elem_seqs/` owns bus or protocol element sequences.
- `seq_lib/` owns scenario-level virtual sequences.
- `tests/` owns config creation and top virtual sequence selection.
- `tb/` owns clocks, resets, DUT instantiation, physical interface hookup, and
  `uvm_config_db` virtual-interface publication.

## Required Build Phases

Base test:

1. Create `PROJECT_uvm_config`.
2. Fetch every required virtual interface from `uvm_config_db`.
3. Create and optionally lock the RAL model.
4. Publish config to `env`.
5. Create `PROJECT_env`.
6. Set timeout and report policy.
7. Implement `run_top_virtual_sequence()` as a virtual task and let child tests
   select one virtual sequence.

Environment:

1. Get config.
2. Create agents, scoreboard, coverage, virtual sequencer, and optional RAL
   predictor/adapter.
3. Route sub-sequencers into the virtual sequencer.
4. Connect monitor analysis ports to scoreboard and coverage.
5. Route RAL map sequencer/adapter when registers exist.

Virtual sequence:

1. Use `` `uvm_declare_p_sequencer(PROJECT_virtual_sequencer) ``.
2. Copy cfg, vif, RAL, and sub-sequencer handles from `p_sequencer`.
3. Run deterministic legal scenarios first.
4. Keep reset callbacks and RAL reset behavior in the base virtual sequence.

## Loop2 Closure Requirements

The template is not closed by compile alone. Loop2 closure requires:

- UVM package and top compile.
- At least one deterministic baseline test.
- Scoreboard pass marker with non-zero checks.
- UVM error/fatal counts at zero.
- Functional coverage summary tied to legal requirements.
- Code coverage report or documented waiver.
- `01_DocParse/trace_matrix/req_to_test.yaml` links from requirements to
  sequences, scoreboards, coverage, and tests.

## Instantiate From The Project Template

New projects receive the project-local skeleton under `05_Output/uvm`. Rename
`.template` files to project-specific `.sv` or `.svh` files, replace
`PROJECT` and `PROTOCOL`, then implement protocol-specific logic from the
normalized spec. Do not report Loop2 PASS while `.template` files are still the
only UVM source.
