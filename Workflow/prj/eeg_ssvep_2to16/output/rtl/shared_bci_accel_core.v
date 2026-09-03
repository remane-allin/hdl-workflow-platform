// -----------------------------------------------------------------------------
// Module: shared_bci_accel_core
// Description: Profile-independent shared accelerator core. Software loads one
//              trusted program image, parameter image, and 2048-word frame;
//              one descriptor controller then owns one execution overlay.
// Scope:
//   - No EEG/SSVEP profile decode or parallel profile-specific datapaths.
//   - Six RAMB36 storage boundary: program, parameter, and four feature banks.
//   - AXI-independent ready/valid boundary for later PS wrapper integration.
// Spec Trace: REQ-RRB-003, REQ-RRB-005, REQ-RRB-006, REQ-RRB-007,
//             REQ-RRB-008, REQ-RRB-019, REQ-RRB-020, REQ-RRB-022
// -----------------------------------------------------------------------------

`timescale 1ns/1ps
`default_nettype none

module shared_bci_accel_core (
    input  wire        clk,
    input  wire        reset_n,
    input  wire        start_valid,
    output wire        start_ready,
    output wire        busy,
    output wire        done,
    input  wire        program_load_valid,
    output wire        program_load_ready,
    input  wire [8:0]  program_load_address,
    input  wire [63:0] program_load_data,
    input  wire        parameter_load_valid,
    output wire        parameter_load_ready,
    input  wire [8:0]  parameter_load_address,
    input  wire [63:0] parameter_load_data,
    input  wire        frame_begin,
    input  wire [1:0]  frame_page,
    input  wire [63:0] frame_config,
    input  wire        frame_valid,
    output wire        frame_ready,
    input  wire [63:0] frame_data,
    output wire        frame_complete,
    output wire [8:0]  frame_beat_count,
    output wire        result_valid,
    input  wire        result_ready,
    output wire [15:0] result_data,
    output wire        result_last
);
    wire controller_busy;
    wire controller_done;
    wire session_busy;
    wire controller_start;
    wire controller_program_read_valid;
    wire [8:0] controller_program_read_address;
    wire engine_program_read_valid;
    wire [8:0] engine_program_read_address;
    wire program_read_valid;
    wire [8:0] program_read_address;
    wire program_read_response_valid;
    wire [63:0] program_read_response_data;
    wire engine_parameter_read_valid;
    wire [8:0] engine_parameter_read_address;
    wire parameter_read_response_valid;
    wire [63:0] parameter_read_response_data;
    wire descriptor_valid;
    wire descriptor_ready;
    wire [8:0] descriptor_pc;
    wire [63:0] descriptor_base;
    wire [63:0] descriptor_ext0;
    wire [63:0] descriptor_ext1;
    wire [63:0] descriptor_ext2;
    wire descriptor_complete;
    wire engine_busy;
    wire [3:0] ingress_write_valid;
    wire [51:0] ingress_write_address;
    wire [63:0] ingress_write_data;
    wire [3:0] engine_bank_a_valid;
    wire [3:0] engine_bank_a_write;
    wire [51:0] engine_bank_a_address;
    wire [63:0] engine_bank_a_write_data;
    wire [3:0] engine_bank_b_valid;
    wire [3:0] engine_bank_b_write;
    wire [51:0] engine_bank_b_address;
    wire [63:0] engine_bank_b_write_data;
    wire [3:0] feature_bank_a_valid;
    wire [3:0] feature_bank_a_write;
    wire [51:0] feature_bank_a_address;
    wire [63:0] feature_bank_a_write_data;
    wire [3:0] feature_bank_a_response_valid;
    wire [63:0] feature_bank_a_response_data;
    wire [3:0] feature_bank_b_response_valid;
    wire [63:0] feature_bank_b_response_data;

    assign session_busy = controller_busy | controller_done;
    assign controller_start = start_valid & start_ready;
    assign start_ready = ~session_busy;
    assign busy = controller_busy;
    assign done = controller_done;

    // Controller fetch and engine constant reads are mutually exclusive by
    // descriptor protocol. Priority is explicit so the boundary stays local.
    assign program_read_valid = engine_program_read_valid |
                                controller_program_read_valid;
    assign program_read_address = engine_program_read_valid ?
                                  engine_program_read_address :
                                  controller_program_read_address;

    // Port A is frame ingress while idle and execution traffic in a session.
    assign feature_bank_a_valid = session_busy ?
                                  engine_bank_a_valid : ingress_write_valid;
    assign feature_bank_a_write = session_busy ?
                                  engine_bank_a_write : ingress_write_valid;
    assign feature_bank_a_address = session_busy ?
                                    engine_bank_a_address :
                                    ingress_write_address;
    assign feature_bank_a_write_data = session_busy ?
                                       engine_bank_a_write_data :
                                       ingress_write_data;

    program_memory_wrapper u_program_memory (
        .clk(clk), .reset_n(reset_n), .session_busy(session_busy),
        .load_valid(program_load_valid), .load_ready(program_load_ready),
        .load_address(program_load_address), .load_data(program_load_data),
        .read_valid(program_read_valid), .read_address(program_read_address),
        .read_response_valid(program_read_response_valid),
        .read_response_data(program_read_response_data)
    );

    parameter_memory_wrapper u_parameter_memory (
        .clk(clk), .reset_n(reset_n), .session_busy(session_busy),
        .load_valid(parameter_load_valid), .load_ready(parameter_load_ready),
        .load_address(parameter_load_address), .load_data(parameter_load_data),
        .read_valid(engine_parameter_read_valid),
        .read_address(engine_parameter_read_address),
        .read_response_valid(parameter_read_response_valid),
        .read_response_data(parameter_read_response_data)
    );

    frame_ingress_adapter u_frame_ingress (
        .clk(clk), .reset_n(reset_n), .session_busy(session_busy),
        .frame_begin(frame_begin), .frame_page(frame_page),
        .frame_config(frame_config),
        .frame_valid(frame_valid), .frame_ready(frame_ready),
        .frame_data(frame_data), .frame_complete(frame_complete),
        .frame_beat_count(frame_beat_count),
        .bank0_write_valid(ingress_write_valid[0]),
        .bank0_write_address(ingress_write_address[12:0]),
        .bank0_write_data(ingress_write_data[15:0]),
        .bank1_write_valid(ingress_write_valid[1]),
        .bank1_write_address(ingress_write_address[25:13]),
        .bank1_write_data(ingress_write_data[31:16]),
        .bank2_write_valid(ingress_write_valid[2]),
        .bank2_write_address(ingress_write_address[38:26]),
        .bank2_write_data(ingress_write_data[47:32]),
        .bank3_write_valid(ingress_write_valid[3]),
        .bank3_write_address(ingress_write_address[51:39]),
        .bank3_write_data(ingress_write_data[63:48])
    );

    descriptor_controller u_descriptor_controller (
        .clk(clk), .reset_n(reset_n), .start(controller_start),
        .busy(controller_busy), .done(controller_done),
        .program_read_valid(controller_program_read_valid),
        .program_read_address(controller_program_read_address),
        .program_read_response_valid(program_read_response_valid),
        .program_read_response_data(program_read_response_data),
        .descriptor_valid(descriptor_valid),
        .descriptor_ready(descriptor_ready), .descriptor_pc(descriptor_pc),
        .descriptor_base(descriptor_base), .descriptor_ext0(descriptor_ext0),
        .descriptor_ext1(descriptor_ext1), .descriptor_ext2(descriptor_ext2),
        .descriptor_complete(descriptor_complete)
    );

    descriptor_execution_engine u_execution_engine (
        .clk(clk), .reset_n(reset_n),
        .descriptor_valid(descriptor_valid),
        .descriptor_ready(descriptor_ready), .descriptor_pc(descriptor_pc),
        .descriptor_base(descriptor_base), .descriptor_ext0(descriptor_ext0),
        .descriptor_ext1(descriptor_ext1), .descriptor_ext2(descriptor_ext2),
        .descriptor_complete(descriptor_complete), .busy(engine_busy),
        .parameter_read_valid(engine_parameter_read_valid),
        .parameter_read_address(engine_parameter_read_address),
        .parameter_read_response_valid(parameter_read_response_valid),
        .parameter_read_response_data(parameter_read_response_data),
        .program_read_valid(engine_program_read_valid),
        .program_read_address(engine_program_read_address),
        .program_read_response_valid(program_read_response_valid),
        .program_read_response_data(program_read_response_data),
        .bank0_a_valid(engine_bank_a_valid[0]),
        .bank0_a_write(engine_bank_a_write[0]),
        .bank0_a_address(engine_bank_a_address[12:0]),
        .bank0_a_write_data(engine_bank_a_write_data[15:0]),
        .bank0_a_response_valid(feature_bank_a_response_valid[0]),
        .bank0_a_response_data(feature_bank_a_response_data[15:0]),
        .bank1_a_valid(engine_bank_a_valid[1]),
        .bank1_a_write(engine_bank_a_write[1]),
        .bank1_a_address(engine_bank_a_address[25:13]),
        .bank1_a_write_data(engine_bank_a_write_data[31:16]),
        .bank1_a_response_valid(feature_bank_a_response_valid[1]),
        .bank1_a_response_data(feature_bank_a_response_data[31:16]),
        .bank2_a_valid(engine_bank_a_valid[2]),
        .bank2_a_write(engine_bank_a_write[2]),
        .bank2_a_address(engine_bank_a_address[38:26]),
        .bank2_a_write_data(engine_bank_a_write_data[47:32]),
        .bank2_a_response_valid(feature_bank_a_response_valid[2]),
        .bank2_a_response_data(feature_bank_a_response_data[47:32]),
        .bank3_a_valid(engine_bank_a_valid[3]),
        .bank3_a_write(engine_bank_a_write[3]),
        .bank3_a_address(engine_bank_a_address[51:39]),
        .bank3_a_write_data(engine_bank_a_write_data[63:48]),
        .bank3_a_response_valid(feature_bank_a_response_valid[3]),
        .bank3_a_response_data(feature_bank_a_response_data[63:48]),
        .bank0_b_valid(engine_bank_b_valid[0]),
        .bank0_b_write(engine_bank_b_write[0]),
        .bank0_b_address(engine_bank_b_address[12:0]),
        .bank0_b_write_data(engine_bank_b_write_data[15:0]),
        .bank0_b_response_valid(feature_bank_b_response_valid[0]),
        .bank0_b_response_data(feature_bank_b_response_data[15:0]),
        .bank1_b_valid(engine_bank_b_valid[1]),
        .bank1_b_write(engine_bank_b_write[1]),
        .bank1_b_address(engine_bank_b_address[25:13]),
        .bank1_b_write_data(engine_bank_b_write_data[31:16]),
        .bank1_b_response_valid(feature_bank_b_response_valid[1]),
        .bank1_b_response_data(feature_bank_b_response_data[31:16]),
        .bank2_b_valid(engine_bank_b_valid[2]),
        .bank2_b_write(engine_bank_b_write[2]),
        .bank2_b_address(engine_bank_b_address[38:26]),
        .bank2_b_write_data(engine_bank_b_write_data[47:32]),
        .bank2_b_response_valid(feature_bank_b_response_valid[2]),
        .bank2_b_response_data(feature_bank_b_response_data[47:32]),
        .bank3_b_valid(engine_bank_b_valid[3]),
        .bank3_b_write(engine_bank_b_write[3]),
        .bank3_b_address(engine_bank_b_address[51:39]),
        .bank3_b_write_data(engine_bank_b_write_data[63:48]),
        .bank3_b_response_valid(feature_bank_b_response_valid[3]),
        .bank3_b_response_data(feature_bank_b_response_data[63:48]),
        .result_valid(result_valid), .result_ready(result_ready),
        .result_data(result_data), .result_last(result_last)
    );

    feature_memory_subsystem u_feature_memory (
        .clk(clk), .reset_n(reset_n),
        .bank0_a_valid(feature_bank_a_valid[0]),
        .bank0_a_write(feature_bank_a_write[0]),
        .bank0_a_address(feature_bank_a_address[12:0]),
        .bank0_a_write_data(feature_bank_a_write_data[15:0]),
        .bank0_a_response_valid(feature_bank_a_response_valid[0]),
        .bank0_a_response_data(feature_bank_a_response_data[15:0]),
        .bank1_a_valid(feature_bank_a_valid[1]),
        .bank1_a_write(feature_bank_a_write[1]),
        .bank1_a_address(feature_bank_a_address[25:13]),
        .bank1_a_write_data(feature_bank_a_write_data[31:16]),
        .bank1_a_response_valid(feature_bank_a_response_valid[1]),
        .bank1_a_response_data(feature_bank_a_response_data[31:16]),
        .bank2_a_valid(feature_bank_a_valid[2]),
        .bank2_a_write(feature_bank_a_write[2]),
        .bank2_a_address(feature_bank_a_address[38:26]),
        .bank2_a_write_data(feature_bank_a_write_data[47:32]),
        .bank2_a_response_valid(feature_bank_a_response_valid[2]),
        .bank2_a_response_data(feature_bank_a_response_data[47:32]),
        .bank3_a_valid(feature_bank_a_valid[3]),
        .bank3_a_write(feature_bank_a_write[3]),
        .bank3_a_address(feature_bank_a_address[51:39]),
        .bank3_a_write_data(feature_bank_a_write_data[63:48]),
        .bank3_a_response_valid(feature_bank_a_response_valid[3]),
        .bank3_a_response_data(feature_bank_a_response_data[63:48]),
        .bank0_b_valid(engine_bank_b_valid[0]),
        .bank0_b_write(engine_bank_b_write[0]),
        .bank0_b_address(engine_bank_b_address[12:0]),
        .bank0_b_write_data(engine_bank_b_write_data[15:0]),
        .bank0_b_response_valid(feature_bank_b_response_valid[0]),
        .bank0_b_response_data(feature_bank_b_response_data[15:0]),
        .bank1_b_valid(engine_bank_b_valid[1]),
        .bank1_b_write(engine_bank_b_write[1]),
        .bank1_b_address(engine_bank_b_address[25:13]),
        .bank1_b_write_data(engine_bank_b_write_data[31:16]),
        .bank1_b_response_valid(feature_bank_b_response_valid[1]),
        .bank1_b_response_data(feature_bank_b_response_data[31:16]),
        .bank2_b_valid(engine_bank_b_valid[2]),
        .bank2_b_write(engine_bank_b_write[2]),
        .bank2_b_address(engine_bank_b_address[38:26]),
        .bank2_b_write_data(engine_bank_b_write_data[47:32]),
        .bank2_b_response_valid(feature_bank_b_response_valid[2]),
        .bank2_b_response_data(feature_bank_b_response_data[47:32]),
        .bank3_b_valid(engine_bank_b_valid[3]),
        .bank3_b_write(engine_bank_b_write[3]),
        .bank3_b_address(engine_bank_b_address[51:39]),
        .bank3_b_write_data(engine_bank_b_write_data[63:48]),
        .bank3_b_response_valid(feature_bank_b_response_valid[3]),
        .bank3_b_response_data(feature_bank_b_response_data[63:48])
    );
endmodule
`default_nettype wire
