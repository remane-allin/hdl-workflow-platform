`ifndef COVERAGE_SV
`define COVERAGE_SV

class coverage_collector extends uvm_subscriber #(spi_item);
  `uvm_component_utils(coverage_collector)

  int unsigned opcode_sample;
  int unsigned scenario_sample;

  covergroup observed_cg;
    option.per_instance = 1;
    cp_opcode: coverpoint opcode_sample {
      bins op04 = {8'h04};
      bins op08 = {8'h08};
      bins op0c = {8'h0C};
      bins op10 = {8'h10};
      bins op24 = {8'h24};
      bins op40 = {8'h40};
      bins op44 = {8'h44};
      bins op80 = {8'h80};
      bins op84 = {8'h84};
      bins opa0 = {8'hA0};
      bins opc0 = {8'hC0};
    }
    cp_scenario: coverpoint scenario_sample {
      bins reset_mid_frame = {1};
      bins bad_stop_bit = {2};
      bins glitch = {3};
      bins overflow = {4};
      bins baud_div_434 = {5};
      bins opcode_matrix = {6};
    }
    cross cp_opcode, cp_scenario;
  endgroup

  function new(string name, uvm_component parent);
    super.new(name, parent);
    observed_cg = new();
  endfunction

  virtual function void write(spi_item t);
    opcode_sample = t.opcode;
    scenario_sample = t.scenario_code;
    observed_cg.sample();
  endfunction

  function real coverage_pct();
    return observed_cg.get_inst_coverage();
  endfunction
endclass

`endif
