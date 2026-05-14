# RKV-Style UVM Framework

Use this reference when the user wants a maintainable UVM framework, complains
that everything is combined in one package, or asks to follow an existing RKV
VIP-style layout.

## Target Layout

For a DUT or protocol prefix `<dut>`, use:

```text
05_Output/uvm/
  cfg/
    <dut>_uvm_defines.svh
    <dut>_uvm_config.sv
  agents/
    <protocol>/
      <dut>_<protocol>_item.sv
      <dut>_<protocol>_sequencer.sv
      <dut>_<protocol>_driver.sv
      <dut>_<protocol>_monitor.sv        # add when passive checking is useful
      <dut>_<protocol>_agent.sv
  cov/
    <dut>_coverage.sv
  env/
    <dut>_scoreboard.sv
    <dut>_virtual_sequencer.sv
    <dut>_env.sv
    <dut>_uvm_pkg.sv
  reg/
    <dut>_reg_model.sv          # optional, required for register-backed IP
    <dut>_reg_adapter.sv        # optional bus/RAL adapter
  seq_lib/
    elem_seqs/
      <dut>_<protocol>_base_sequence.sv
    <dut>_base_virtual_sequence.sv
    <dut>_<scenario>_virtual_sequence.sv
    <dut>_virtual_sequences.svh
  tests/
    <dut>_base_test.sv
    <dut>_<scenario>_test.sv
    <dut>_tests.svh
  tb/
    <dut>_<protocol>_if.sv
    tb_<dut>_uvm.sv
```

Keep root `05_Output/uvm/` free of implementation files except an optional short
project README. Remove old root-level monolithic files after updating scripts.

## Ownership Rules

- `cfg/`: virtual interfaces, active/passive settings, reset policy, timing knobs,
  and shared enums or defines.
- `agents/<protocol>/`: sequence item, sequencer, driver, monitor, and agent for
  one protocol or bus. The agent owns protocol activity, not global scenarios.
- `cov/`: UVM functional coverage model. Add meaningful coverpoints and cross
  coverage from monitor or agent analysis transactions; do not hide it in the
  scoreboard.
- `env/`: instantiate agents, scoreboard, coverage, virtual sequencer, and
  register model adapters. Connect analysis ports here.
- `reg/`: register model and bus adapter. Keep it optional for pure datapath
  designs, but include the directory in the Loop2 compile path.
- `seq_lib/`: virtual sequences own scenario intent and route element work to
  sub-sequencers. Put reusable helper tasks in the base virtual sequence.
- `tests/`: create config and env in the base test. Scenario tests select and
  start one top virtual sequence.
- `tb/`: interface tasks and the HDL top that instantiates the DUT and calls
  `run_test`.

## Package Pattern

Make `<dut>_uvm_pkg.sv` a thin include hub. It should import UVM, include macros,
then include files in dependency order:

```systemverilog
package <dut>_uvm_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"

  `include "<dut>_uvm_defines.svh"
  `include "<dut>_uvm_config.sv"

  `include "<dut>_<protocol>_item.sv"
  `include "<dut>_<protocol>_sequencer.sv"
  `include "<dut>_<protocol>_driver.sv"
  `include "<dut>_<protocol>_monitor.sv"
  `include "<dut>_<protocol>_agent.sv"

  `include "<dut>_reg_model.sv"
  `include "<dut>_reg_adapter.sv"

  `include "<dut>_scoreboard.sv"
  `include "<dut>_coverage.sv"
  `include "<dut>_virtual_sequencer.sv"
  `include "<dut>_env.sv"

  `include "<dut>_virtual_sequences.svh"
  `include "<dut>_tests.svh"
endpackage
```

Omit monitor include only for a first active-driver-only baseline bring-up, but
leave the agent boundary ready for a monitor.
Omit `reg_model` and `reg_adapter` includes only when `register_map.yaml` says
the design has no software-visible registers.

## Template Database

The local Test library registers this framework as:

- `uvm.rkv_style_framework`
- `uvm.rkv_i2c_reference_profile`

Use `hdlflow get-template-detail --workspace Test --id uvm.rkv_style_framework`
to retrieve the reusable template contract.

## Coverage Pattern

Create a dedicated coverage component in `cov/`, instantiate it in the env, and
connect agent or monitor analysis ports to it alongside the scoreboard. Prefer
cross coverage with verification meaning, such as:

- operation kind x access direction
- scenario x opcode group
- checked read x pass/fail result
- mode/config class x protocol operation

Print an explicit coverage summary in `report_phase`, and keep coverage holes
as review items unless a later targeted test closes them.

## Base Test Pattern

The base test should:

- create `<dut>_uvm_config`
- fetch required virtual interfaces from `uvm_config_db`
- set config into `env`
- create `<dut>_env`
- set timeout and report policy
- implement `run_top_virtual_sequence()` as a virtual empty task

Scenario tests should only create and start their top virtual sequence. Avoid
putting stimulus directly in the test body.

## Virtual Sequence Pattern

Use a `uvm_sequence`-based virtual sequence with:

- `` `uvm_declare_p_sequencer(<dut>_virtual_sequencer) ``
- `cfg` and virtual interface handles copied from `p_sequencer`
- common helpers in `<dut>_base_virtual_sequence`
- directed scenario sequences in separate files

For element operations, start sequence items on the relevant sub-sequencer or
use small element sequences. Keep scenario intent readable at the virtual
sequence level.

## Script Update Checklist

When refactoring from a monolithic UVM package:

1. Move interface and top into `tb/`.
2. Move package into `env/` and convert it to a thin include hub.
3. Add all new directories, including `cov/`, as `+incdir+` entries.
4. Compile in this order: interface, package, UVM top.
5. Update all `.do`, `.f`, Makefile, trace, and review paths.
6. Search for old root paths such as:
   - `05_Output/uvm/<dut>_uvm_pkg.sv`
   - `05_Output/uvm/<dut>_<protocol>_if.sv`
   - `05_Output/uvm/tb_<dut>_uvm.sv`
7. Remove stale root-level files and failed intermediate logs that are not
   current evidence.

## Handoff Gate

Before considering the refactor done:

- JSON/task metadata still parses if present.
- No source or trace file points to deleted UVM paths.
- Focused UVM baseline passes.
- Combined regression passes if the project has one.
- The latest evidence path in review or `memory/` files points to the newest passing
  regression or baseline log.
