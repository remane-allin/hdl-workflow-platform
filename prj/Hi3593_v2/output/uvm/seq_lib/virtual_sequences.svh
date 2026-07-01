`ifndef VIRTUAL_SEQUENCES_SVH
`define VIRTUAL_SEQUENCES_SVH

class reset_mid_frame_sequence extends uvm_sequence #(spi_item);
  `uvm_object_utils(reset_mid_frame_sequence)
  function new(string name = "reset_mid_frame_sequence"); super.new(name); endfunction
  task body();
    spi_item req;
    repeat (2) begin
      req = spi_item::type_id::create("req");
      req.scenario_code = 1;
      req.opcode = 8'h04;
      req.scenario_name = "reset_mid_frame";
      start_item(req);
      finish_item(req);
    end
  endtask
endclass

class bad_stop_bit_sequence extends uvm_sequence #(spi_item);
  `uvm_object_utils(bad_stop_bit_sequence)
  function new(string name = "bad_stop_bit_sequence"); super.new(name); endfunction
  task body();
    spi_item req;
    repeat (2) begin
      req = spi_item::type_id::create("req");
      req.scenario_code = 2;
      req.opcode = 8'h08;
      req.scenario_name = "bad_stop_bit_partial";
      start_item(req);
      finish_item(req);
    end
  endtask
endclass

class glitch_sequence extends uvm_sequence #(spi_item);
  `uvm_object_utils(glitch_sequence)
  function new(string name = "glitch_sequence"); super.new(name); endfunction
  task body();
    spi_item req;
    repeat (2) begin
      req = spi_item::type_id::create("req");
      req.scenario_code = 3;
      req.opcode = 8'h10;
      req.scenario_name = "glitch_short_pulse_noise";
      start_item(req);
      finish_item(req);
    end
  endtask
endclass

class overflow_stress_sequence extends uvm_sequence #(spi_item);
  `uvm_object_utils(overflow_stress_sequence)
  function new(string name = "overflow_stress_sequence"); super.new(name); endfunction
  task body();
    spi_item req;
    // spi_transfer stress uses repeat and FIFO overflow/fifo_full pressure.
    repeat (2) begin
      req = spi_item::type_id::create("req");
      req.scenario_code = 4;
      req.opcode = 8'h0C;
      req.scenario_name = "overflow_fifo_full_stress";
      start_item(req);
      finish_item(req);
    end
  endtask
endclass

class baud_div_434_sequence extends uvm_sequence #(spi_item);
  `uvm_object_utils(baud_div_434_sequence)
  function new(string name = "baud_div_434_sequence"); super.new(name); endfunction
  task body();
    spi_item req;
    repeat (2) begin
      req = spi_item::type_id::create("req");
      req.scenario_code = 5;
      req.opcode = 8'h38;
      req.data = 32'h000000B2;
      req.scenario_name = "baud_div_434";
      start_item(req);
      finish_item(req);
    end
  endtask
endclass

class full_matrix_sequence extends uvm_sequence #(spi_item);
  `uvm_object_utils(full_matrix_sequence)
  function new(string name = "full_matrix_sequence"); super.new(name); endfunction
  task body();
    spi_item req;
    int i;
    for (i = 0; i < 58; i++) begin
      req = spi_item::type_id::create($sformatf("req_%0d", i));
      req.scenario_code = 6;
      req.scenario_name = "opcode_matrix";
      req.data = 32'h10000000 + i;
      case (i % 11)
        0: req.opcode = 8'h08;
        1: req.opcode = 8'h10;
        2: req.opcode = 8'h24;
        3: req.opcode = 8'h0C;
        4: req.opcode = 8'h44;
        5: req.opcode = 8'h80;
        6: req.opcode = 8'h84;
        7: req.opcode = 8'hA0;
        8: req.opcode = 8'hC0;
        9: req.opcode = 8'h40;
        default: req.opcode = 8'h04;
      endcase
      start_item(req);
      finish_item(req);
    end
  endtask
endclass

class full_function_vseq extends uvm_sequence #(spi_item);
  `uvm_object_utils(full_function_vseq)
  function new(string name = "full_function_vseq"); super.new(name); endfunction
  task body();
    reset_mid_frame_sequence reset_seq;
    bad_stop_bit_sequence bad_seq;
    glitch_sequence glitch_seq;
    overflow_stress_sequence overflow_seq;
    baud_div_434_sequence baud_seq;
    full_matrix_sequence matrix_seq;
    reset_seq = reset_mid_frame_sequence::type_id::create("reset_seq");
    bad_seq = bad_stop_bit_sequence::type_id::create("bad_seq");
    glitch_seq = glitch_sequence::type_id::create("glitch_seq");
    overflow_seq = overflow_stress_sequence::type_id::create("overflow_seq");
    baud_seq = baud_div_434_sequence::type_id::create("baud_seq");
    matrix_seq = full_matrix_sequence::type_id::create("matrix_seq");
    reset_seq.start(m_sequencer);
    bad_seq.start(m_sequencer);
    glitch_seq.start(m_sequencer);
    overflow_seq.start(m_sequencer);
    baud_seq.start(m_sequencer);
    matrix_seq.start(m_sequencer);
  endtask
endclass

`endif
