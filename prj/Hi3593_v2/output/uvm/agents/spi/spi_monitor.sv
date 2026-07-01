`ifndef SPI_MONITOR_SV
`define SPI_MONITOR_SV

class spi_monitor extends uvm_component;
  `uvm_component_utils(spi_monitor)

  virtual tb_dut_if vif;
  uvm_analysis_port #(spi_item) ap;

  function new(string name, uvm_component parent);
    super.new(name, parent);
    ap = new("ap", this);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual tb_dut_if)::get(this, "", "vif", vif)) begin
      `uvm_fatal("NOVIF", "virtual interface is required")
    end
  endfunction

  task run_phase(uvm_phase phase);
    spi_item observed;
    forever begin
      @(posedge vif.ACLK);
      if (vif.mon_valid) begin
        observed = spi_item::type_id::create("observed", this);
        observed.scenario_code = vif.mon_scenario_code;
        observed.opcode = vif.mon_opcode;
        observed.actual_code = vif.mon_actual_code;
        observed.latency_cycles = vif.mon_latency;
        observed.scenario_name = vif.mon_scenario_name;
        ap.write(observed);
        wait (vif.mon_valid == 1'b0);
      end
    end
  endtask
endclass

`endif
