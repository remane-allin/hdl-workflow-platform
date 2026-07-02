`timescale 1ns/1ps

`ifndef TB_DUT_IF_SV
`define TB_DUT_IF_SV

interface tb_dut_if(input bit ACLK);
  logic MR;
  logic CS;
  logic SCK;
  logic SI;
  logic SO;
  logic OUT1A;
  logic OUT1B;
  logic OUT2A;
  logic OUT2B;
  logic TX1IN;
  logic TX0IN;
  logic SLP;
  logic TEMPTY;
  logic TFULL;
  logic R1FLAG;
  logic R2FLAG;
  logic R1INT;
  logic R2INT;
  logic MB1_1;
  logic MB1_2;
  logic MB1_3;
  logic MB2_1;
  logic MB2_2;
  logic MB2_3;

  logic [7:0] tx_control_obs;
  logic [7:0] rx1_control_obs;
  logic [7:0] rx2_control_obs;
  logic [7:0] aclk_division_obs;
  logic [7:0] spi_opcode_obs;
  logic [5:0] tx_fifo_count_obs;
  logic [5:0] rx1_fifo_count_obs;
  logic partial_discard_obs;
  logic tx_busy_obs;

  bit mon_valid;
  int mon_scenario_code;
  bit [7:0] mon_opcode;
  int mon_actual_code;
  int mon_latency;
  string mon_scenario_name;

  task init_pins();
    MR = 1'b1;
    CS = 1'b1;
    SCK = 1'b0;
    SI = 1'b0;
    OUT1A = 1'b0;
    OUT1B = 1'b0;
    OUT2A = 1'b0;
    OUT2B = 1'b0;
    mon_valid = 1'b0;
    mon_scenario_code = 0;
    mon_opcode = 8'h00;
    mon_actual_code = 0;
    mon_latency = 0;
    mon_scenario_name = "idle";
  endtask

  task wait_aclk(input int cycles);
    int i;
    begin
      for (i = 0; i < cycles; i++) begin
        @(posedge ACLK);
      end
    end
  endtask

  task external_reset();
    begin
      MR = 1'b1;
      CS = 1'b1;
      SCK = 1'b0;
      SI = 1'b0;
      wait_aclk(5);
      MR = 1'b0;
      wait_aclk(8);
    end
  endtask

  task spi_begin();
    begin
      SCK = 1'b0;
      SI = 1'b0;
      CS = 1'b0;
      #21;
    end
  endtask

  task spi_send_byte(input bit [7:0] value);
    int bit_index;
    begin
      for (bit_index = 0; bit_index < 8; bit_index++) begin
        SI = value[7 - bit_index];
        #13;
        SCK = 1'b1;
        #13;
        SCK = 1'b0;
        #7;
      end
    end
  endtask

  task spi_finish();
    begin
      wait_aclk(3);
      CS = 1'b1;
      SI = 1'b0;
      SCK = 1'b0;
      wait_aclk(4);
    end
  endtask

  task spi_cmd0(input bit [7:0] opcode);
    begin
      spi_begin();
      spi_send_byte(opcode);
      spi_finish();
    end
  endtask

  task spi_write1(input bit [7:0] opcode, input bit [7:0] data0);
    begin
      spi_begin();
      spi_send_byte(opcode);
      spi_send_byte(data0);
      spi_finish();
    end
  endtask

  task spi_write4(input bit [7:0] opcode, input bit [31:0] data_word);
    begin
      spi_begin();
      spi_send_byte(opcode);
      spi_send_byte(data_word[31:24]);
      spi_send_byte(data_word[23:16]);
      spi_send_byte(data_word[15:8]);
      spi_send_byte(data_word[7:0]);
      spi_finish();
    end
  endtask

  task spi_read_bytes(input bit [7:0] opcode, input int byte_count);
    int byte_index;
    begin
      spi_begin();
      spi_send_byte(opcode);
      for (byte_index = 0; byte_index < byte_count; byte_index++) begin
        spi_send_byte(8'h00);
      end
      spi_finish();
    end
  endtask

  task partial_spi_frame();
    begin
      spi_begin();
      SI = 1'b1; #13; SCK = 1'b1; #13; SCK = 1'b0; #7;
      SI = 1'b0; #13; SCK = 1'b1; #13; SCK = 1'b0; #7;
      SI = 1'b1; #13; SCK = 1'b1; #13; SCK = 1'b0; #7;
      CS = 1'b1;
      wait_aclk(4);
    end
  endtask

  task short_rx_glitch();
    begin
      @(negedge ACLK);
      OUT1A = 1'b1;
      OUT1B = 1'b0;
      #2;
      OUT1A = 1'b0;
      OUT1B = 1'b0;
      wait_aclk(6);
    end
  endtask

  task publish_observed(input int scenario_code, input bit [7:0] opcode, input int actual_code, input int latency, input string scenario_name);
    begin
      mon_scenario_code = scenario_code;
      mon_opcode = opcode;
      mon_actual_code = actual_code;
      mon_latency = latency;
      mon_scenario_name = scenario_name;
      mon_valid = 1'b1;
      @(posedge ACLK);
      @(posedge ACLK);
      mon_valid = 1'b0;
      @(posedge ACLK);
    end
  endtask
endinterface

`endif
