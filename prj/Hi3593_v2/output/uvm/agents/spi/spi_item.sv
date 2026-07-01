`ifndef SPI_ITEM_SV
`define SPI_ITEM_SV

class spi_item extends uvm_sequence_item;
  rand int scenario_code;
  rand bit [7:0] opcode;
  rand bit [31:0] data;
  int actual_code;
  int latency_cycles;
  string scenario_name;

  `uvm_object_utils_begin(spi_item)
    `uvm_field_int(scenario_code, UVM_DEFAULT)
    `uvm_field_int(opcode, UVM_HEX)
    `uvm_field_int(data, UVM_HEX)
    `uvm_field_int(actual_code, UVM_DEFAULT)
    `uvm_field_int(latency_cycles, UVM_DEFAULT)
    `uvm_field_string(scenario_name, UVM_DEFAULT)
  `uvm_object_utils_end

  function new(string name = "spi_item");
    super.new(name);
    scenario_code = 6;
    opcode = 8'h80;
    data = 32'h0;
    actual_code = 0;
    latency_cycles = 0;
    scenario_name = "opcode_matrix";
  endfunction
endclass

`endif
