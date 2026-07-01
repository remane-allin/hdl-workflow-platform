`ifndef SPI_DRIVER_SV
`define SPI_DRIVER_SV

class spi_driver extends uvm_driver #(spi_item);
  `uvm_component_utils(spi_driver)

  virtual tb_dut_if vif;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual tb_dut_if)::get(this, "", "vif", vif)) begin
      `uvm_fatal("NOVIF", "virtual interface is required")
    end
  endfunction

  task run_phase(uvm_phase phase);
    spi_item tr;
    forever begin
      seq_item_port.get_next_item(tr);
      execute_item(tr);
      seq_item_port.item_done();
    end
  endtask

  task execute_item(spi_item tr);
    int actual;
    begin
      actual = -1;
      case (tr.scenario_code)
        1: begin
          vif.partial_spi_frame();
          vif.MR = 1'b1;
          vif.wait_aclk(3);
          vif.MR = 1'b0;
          vif.wait_aclk(8);
          if ((vif.tx_control_obs == 8'h00) && (vif.tx_fifo_count_obs == 6'd0)) actual = 100;
        end
        2: begin
          vif.partial_spi_frame();
          if (vif.partial_discard_obs) actual = 101;
        end
        3: begin
          vif.external_reset();
          vif.short_rx_glitch();
          if (vif.rx1_fifo_count_obs == 6'd0) actual = 102;
        end
        4: begin
          run_overflow_stress(actual);
        end
        5: begin
          vif.spi_write1(8'h38, 8'hB2);
          if (vif.aclk_division_obs == 8'hB2) actual = 104;
        end
        default: begin
          execute_opcode(tr.opcode, tr.data, actual);
        end
      endcase
      tr.actual_code = actual;
      vif.publish_observed(tr.scenario_code, tr.opcode, actual, tr.latency_cycles, tr.scenario_name);
    end
  endtask

  task automatic run_reset_cleanup();
    begin
      vif.spi_cmd0(8'h04);
      vif.wait_aclk(10);
    end
  endtask

  function int expected_opcode_code(bit [7:0] opcode);
    return 200 + int'(opcode);
  endfunction

  task automatic wait_tx_activity(output bit seen);
    int i;
    bit [1:0] previous_pair;
    begin
      seen = 1'b0;
      previous_pair = {vif.TX1IN, vif.TX0IN};
      for (i = 0; i < 2000; i++) begin
        @(posedge vif.ACLK);
        if ({vif.TX1IN, vif.TX0IN} != previous_pair) seen = 1'b1;
        if ((vif.TX1IN === 1'b1) || (vif.TX0IN === 1'b1)) seen = 1'b1;
        previous_pair = {vif.TX1IN, vif.TX0IN};
      end
    end
  endtask

  task automatic run_overflow_stress(output int result);
    int i;
    begin
      result = -1;
      vif.spi_cmd0(8'h44);
      vif.wait_aclk(6);
      vif.spi_write1(8'h08, 8'h00);
      for (i = 0; i < 32; i++) begin
        vif.spi_write4(8'h0C, 32'h5A000000 + i);
      end
      vif.spi_write4(8'h0C, 32'hCAFEBABE);
      if ((vif.tx_fifo_count_obs == 6'd32) && (vif.TFULL === 1'b1)) result = 103;
    end
  endtask

  task automatic execute_opcode(input bit [7:0] opcode, input bit [31:0] data, output int result);
    bit activity_seen;
    begin
      result = -1;
      case (opcode)
        8'h04: begin
          vif.spi_cmd0(8'h04);
          vif.wait_aclk(10);
          if ((vif.tx_control_obs == 8'h00) && (vif.tx_fifo_count_obs == 6'd0)) result = expected_opcode_code(opcode);
        end
        8'h08: begin
          vif.spi_write1(8'h08, data[7:0]);
          if (vif.tx_control_obs == data[7:0]) result = expected_opcode_code(opcode);
        end
        8'h0C: begin
          vif.spi_cmd0(8'h44);
          vif.wait_aclk(8);
          vif.spi_write1(8'h08, 8'h00);
          vif.wait_aclk(4);
          vif.spi_write4(8'h0C, data);
          vif.wait_aclk(4);
          if (vif.tx_fifo_count_obs != 6'd0) result = expected_opcode_code(opcode);
        end
        8'h10: begin
          vif.spi_write1(8'h10, data[7:0]);
          if (vif.rx1_control_obs == data[7:0]) result = expected_opcode_code(opcode);
        end
        8'h24: begin
          vif.spi_write1(8'h24, data[7:0]);
          if (vif.rx2_control_obs == data[7:0]) result = expected_opcode_code(opcode);
        end
        8'h40: begin
          vif.spi_cmd0(8'h44);
          vif.wait_aclk(8);
          vif.spi_write1(8'h08, 8'h00);
          vif.wait_aclk(4);
          vif.spi_write4(8'h0C, 32'hAAAAAAAA);
          vif.wait_aclk(4);
          vif.spi_cmd0(8'h40);
          wait_tx_activity(activity_seen);
          if (activity_seen) result = expected_opcode_code(opcode);
        end
        8'h44: begin
          vif.spi_cmd0(8'h44);
          vif.wait_aclk(6);
          if (vif.tx_fifo_count_obs == 6'd0) result = expected_opcode_code(opcode);
        end
        8'h80, 8'h84: begin
          vif.spi_read_bytes(opcode, 1);
          if (vif.spi_opcode_obs == opcode) result = expected_opcode_code(opcode);
        end
        8'hA0, 8'hC0: begin
          vif.spi_read_bytes(opcode, 4);
          if (vif.spi_opcode_obs == opcode) result = expected_opcode_code(opcode);
        end
        default: begin
          vif.spi_read_bytes(8'h80, 1);
          if (vif.spi_opcode_obs == 8'h80) result = expected_opcode_code(8'h80);
        end
      endcase
    end
  endtask
endclass

`endif
