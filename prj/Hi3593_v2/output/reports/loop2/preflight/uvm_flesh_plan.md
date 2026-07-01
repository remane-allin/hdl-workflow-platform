# UVM Database Flesh Plan

- project: Hi3593_v2
- library_db: `G:/Codex_Workflow/Test_new/lib/local/library.sqlite`
- purpose: turn the RKV/template skeleton into project-specific UVM implementation using local UVM guide evidence

## Implementation Targets

- `output/uvm/cfg/uvm_config.sv`: config object, virtual interface handles, plus `uvm_config_db` get/set ownership.
- `output/uvm/tb/tb_dut_if.sv` and `output/uvm/tb/tb_uvm.sv`: concrete interface wiring and top-level config_db publication.
- `output/uvm/agents/*`: item, driver, monitor, sequencer, and agent classes completed per protocol signals.
- `output/uvm/seq_lib/virtual_sequences.svh` and `output/uvm/tests/tests.svh`: reset, legal, error, stress, and coverage-closing scenarios.
- `output/uvm/env/scoreboard.sv`: analysis connections, reference model, ordering rules, and mismatch reporting.
- `output/uvm/cov/coverage.sv`: monitor-sampled covergroups and scenario bins tied to requirements.
- `output/uvm/env/uvm_pkg.sv`: explicit compile order and package exports for all real UVM sources.

## Guide Retrieval

### configuration_and_virtual_interfaces

- query: `uvm_config_db virtual interface`
- status: PASS
- chunk: local_uvm_method_notes.v1.chunk_0001 | local_uvm_method_notes.v1 | configuration_and_virtual_interfaces
  - use_for: cfg object, tb interface binding, config_db get/set checks
  - preview: Use uvm_config_db to publish and retrieve virtual interface handles. The top module sets the virtual interface before run_test, and the config object or test retrieves it for the driver and monitor.

### agent_driver_monitor_sequencer

- query: `uvm agent driver monitor sequencer`
- status: PASS
- chunk: local_uvm_method_notes.v1.chunk_0002 | local_uvm_method_notes.v1 | agent_driver_monitor_sequencer
  - use_for: agent internals and transaction flow
  - preview: A UVM agent contains a sequencer, driver, monitor, and analysis port connections. The driver consumes sequence items from the sequencer and the monitor or driver publishes observed transactions for checking.

### sequences_and_virtual_sequences

- query: `uvm_sequence virtual sequence sequencer`
- status: PASS
- chunk: local_uvm_method_notes.v1.chunk_0003 | local_uvm_method_notes.v1 | sequences_and_virtual_sequences
  - use_for: seq_lib and test scenario layering
  - preview: A uvm_sequence creates transaction items and starts them on a sequencer. Virtual sequence layering coordinates reset, legal traffic, stress traffic, and scenario selection across agents.

### scoreboard_and_analysis

- query: `scoreboard analysis port analysis export`
- status: PASS
- chunk: local_uvm_method_notes.v1.chunk_0004 | local_uvm_method_notes.v1 | scoreboard_and_analysis
  - use_for: analysis ports, expected/actual queues, scoreboard connections
  - preview: A scoreboard receives observed transactions through an analysis port or analysis export. It compares expected and actual data, reports mismatches, and prints a final scoreboard pass marker only when all checked traffi...

### coverage_and_sampling

- query: `functional coverage covergroup monitor sampling`
- status: PASS
- chunk: local_uvm_method_notes.v1.chunk_0005 | local_uvm_method_notes.v1 | coverage_and_sampling
  - use_for: monitor-owned sampling and coverage closure
  - preview: Functional coverage should use a covergroup with monitor sampling or scoreboard sampling from observed traffic. The coverage collector subscribes to analysis traffic and samples legal scenario bins from checked transa...

### ral_and_adapter

- query: `uvm_reg_adapter register model bus item`
- status: PASS
- chunk: local_uvm_method_notes.v1.chunk_0006 | local_uvm_method_notes.v1 | ral_and_adapter
  - use_for: register model, adapter, and bus transaction conversion when CSRs exist
  - preview: A uvm_reg_adapter converts register model bus operations into protocol bus item transactions. Register tests can share the same bus item type and scoreboard path as ordinary command traffic.

## Example Retrieval

### uvm_config_db

- status: PASS
- example: local_uvm_method_notes.v1.example_0001 | local_uvm_method_notes.v1 | page 1
  - caption: uvm_config_db virtual interface publication
  - code_preview: uvm_config_db#(virtual dut_if)::set(null, "uvm_test_top", "vif", tb_vif);

### uvm_analysis_port

- status: PASS
- example: local_uvm_method_notes.v1.example_0002 | local_uvm_method_notes.v1 | page 1
  - caption: uvm_analysis_port transaction publication
  - code_preview: uvm_analysis_port#(spi_item) ap; ap = new("ap", this); ap.write(item);

### uvm_sequence

- status: PASS
- example: local_uvm_method_notes.v1.example_0003 | local_uvm_method_notes.v1 | page 1
  - caption: uvm_sequence item start and finish
  - code_preview: class legal_sequence extends uvm_sequence#(spi_item); task body(); start_item(req); finish_item(req); endtask endclass
- example: local_uvm_method_notes.v1.example_0004 | local_uvm_method_notes.v1 | page 1
  - caption: uvm_reg_adapter converts register bus item
  - code_preview: class csr_adapter extends uvm_reg_adapter; virtual function uvm_sequence_item reg2bus(const ref uvm_reg_bus_op rw); endfunction endclass

### uvm_reg_adapter

- status: PASS
- example: local_uvm_method_notes.v1.example_0004 | local_uvm_method_notes.v1 | page 1
  - caption: uvm_reg_adapter converts register bus item
  - code_preview: class csr_adapter extends uvm_reg_adapter; virtual function uvm_sequence_item reg2bus(const ref uvm_reg_bus_op rw); endfunction endclass

## Closure Rule

- Do not close Loop2 with template-shaped files only.
- Every real UVM file listed above must either implement the relevant mechanism or explain why the project does not need it in the Loop2 exit report.
- The final UVM regression remains the authority for behavior; this plan is methodology and implementation provenance.

result: PASS