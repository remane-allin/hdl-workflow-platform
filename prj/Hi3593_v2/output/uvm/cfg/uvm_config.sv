`ifndef DUT_UVM_CONFIG_SV
`define DUT_UVM_CONFIG_SV

class dut_uvm_config extends uvm_object;
  `uvm_object_utils(dut_uvm_config)

  virtual tb_dut_if vif;
  int unsigned seed_count;

  function new(string name = "dut_uvm_config");
    super.new(name);
    seed_count = 1;
  endfunction
endclass

`endif
