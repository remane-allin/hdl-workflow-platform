`timescale 1ns/1ps

module tb_uvm;
  import uvm_pkg::*;
  import dut_uvm_pkg::*;

  bit ACLK;
  tb_dut_if tb_if(ACLK);

  hi3593_v2_top dut (
    .ACLK(ACLK),
    .MR(tb_if.MR),
    .CS(tb_if.CS),
    .SCK(tb_if.SCK),
    .SI(tb_if.SI),
    .SO(tb_if.SO),
    .OUT1A(tb_if.OUT1A),
    .OUT1B(tb_if.OUT1B),
    .OUT2A(tb_if.OUT2A),
    .OUT2B(tb_if.OUT2B),
    .TX1IN(tb_if.TX1IN),
    .TX0IN(tb_if.TX0IN),
    .SLP(tb_if.SLP),
    .TEMPTY(tb_if.TEMPTY),
    .TFULL(tb_if.TFULL),
    .R1FLAG(tb_if.R1FLAG),
    .R2FLAG(tb_if.R2FLAG),
    .R1INT(tb_if.R1INT),
    .R2INT(tb_if.R2INT),
    .MB1_1(tb_if.MB1_1),
    .MB1_2(tb_if.MB1_2),
    .MB1_3(tb_if.MB1_3),
    .MB2_1(tb_if.MB2_1),
    .MB2_2(tb_if.MB2_2),
    .MB2_3(tb_if.MB2_3)
  );

  initial begin
    ACLK = 1'b0;
    forever #5 ACLK = ~ACLK;
  end

  always @(*) begin
    tb_if.tx_control_obs = dut.u_reg_ctrl.tx_control;
    tb_if.rx1_control_obs = dut.u_reg_ctrl.rx1_control;
    tb_if.rx2_control_obs = dut.u_reg_ctrl.rx2_control;
    tb_if.aclk_division_obs = dut.u_reg_ctrl.aclk_division;
    tb_if.spi_opcode_obs = dut.u_spi_if.spi_opcode;
    tb_if.tx_fifo_count_obs = dut.tx_fifo_count;
    tb_if.rx1_fifo_count_obs = dut.rx1_fifo_count;
    tb_if.partial_discard_obs = dut.u_spi_if.partial_discard;
    tb_if.tx_busy_obs = dut.tx_busy;
  end

  initial begin
    tb_if.init_pins();
    uvm_config_db#(virtual tb_dut_if)::set(null, "*", "vif", tb_if);
    run_test();
  end
endmodule
