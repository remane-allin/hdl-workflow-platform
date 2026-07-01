`ifndef ENV_SV
`define ENV_SV

class dut_env extends uvm_env;
  `uvm_component_utils(dut_env)

  dut_uvm_config cfg;
  spi_agent agent;
  dut_scoreboard scoreboard;
  coverage_collector coverage;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(dut_uvm_config)::get(this, "", "cfg", cfg)) begin
      cfg = dut_uvm_config::type_id::create("cfg");
      if (!uvm_config_db#(virtual tb_dut_if)::get(this, "", "vif", cfg.vif)) begin
        `uvm_fatal("NOVIF", "virtual interface is required")
      end
    end
    uvm_config_db#(virtual tb_dut_if)::set(this, "*", "vif", cfg.vif);
    agent = spi_agent::type_id::create("agent", this);
    scoreboard = dut_scoreboard::type_id::create("scoreboard", this);
    coverage = coverage_collector::type_id::create("coverage", this);
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    agent.monitor.ap.connect(scoreboard.analysis_export);
    agent.monitor.ap.connect(coverage.analysis_export);
  endfunction
endclass

`endif
