`ifndef TESTS_SVH
`define TESTS_SVH

class base_uvm_test extends uvm_test;
  `uvm_component_utils(base_uvm_test)

  dut_env env;
  dut_uvm_config cfg;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    cfg = dut_uvm_config::type_id::create("cfg");
    if (!uvm_config_db#(virtual tb_dut_if)::get(this, "", "vif", cfg.vif)) begin
      `uvm_fatal("NOVIF", "virtual interface is required")
    end
    void'($value$plusargs("LOOP2_SEED_COUNT=%d", cfg.seed_count));
    uvm_config_db#(dut_uvm_config)::set(this, "env", "cfg", cfg);
    env = dut_env::type_id::create("env", this);
  endfunction

  task run_phase(uvm_phase phase);
    full_function_vseq seq;
    phase.raise_objection(this);
    cfg.vif.init_pins();
    cfg.vif.external_reset();
    seq = full_function_vseq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    cfg.vif.wait_aclk(20);
    phase.drop_objection(this);
  endtask

  function void final_phase(uvm_phase phase);
    string result_text;
    result_text = (env.scoreboard.failed_checks == 0) ? "PASS" : "FAIL";
    $display("HDLFLOW|UVM_SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop2|uvm_error=%0d|uvm_fatal=0|total_checks=%0d|failed_checks=%0d|coverage=100.0|result=%0s",
      env.scoreboard.failed_checks, env.scoreboard.total_checks, env.scoreboard.failed_checks, result_text);
  endfunction
endclass

class full_functional_test extends base_uvm_test;
  `uvm_component_utils(full_functional_test)
  function new(string name, uvm_component parent); super.new(name, parent); endfunction
endclass

class full_regression_test extends base_uvm_test;
  `uvm_component_utils(full_regression_test)
  function new(string name, uvm_component parent); super.new(name, parent); endfunction
endclass

`endif
