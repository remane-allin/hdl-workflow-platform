//==============================================================================
// Module      : descriptor_controller
// File        : descriptor_controller.v
// Project     : eeg_ssvep_2to16
// Description : Stable descriptor-fetch boundary for the shared accelerator.
// Scope:
//   - Wraps the sole program-control owner behind the core-facing interface.
//   - Hides loop-index outputs that are internal to program execution.
//   - Does not decode operations, data payloads, or signal profiles.
// Spec Trace:
//   - REQ-RRB-006, REQ-RRB-011, REQ-RRB-012
//   - MOD-DESCRIPTOR-CONTROL, IF-DESCRIPTOR
//==============================================================================
`timescale 1ns/1ps
`default_nettype none

module descriptor_controller (
    input  wire        clk,
    input  wire        reset_n,
    input  wire        start,
    output wire        busy,
    output wire        done,
    output wire        program_read_valid,
    output wire [8:0]  program_read_address,
    input  wire        program_read_response_valid,
    input  wire [63:0] program_read_response_data,
    output wire        descriptor_valid,
    input  wire        descriptor_ready,
    output wire [8:0]  descriptor_pc,
    output wire [63:0] descriptor_base,
    output wire [63:0] descriptor_ext0,
    output wire [63:0] descriptor_ext1,
    output wire [63:0] descriptor_ext2,
    input  wire        descriptor_complete
);
    wire [11:0] unused_loop_index0;
    wire [11:0] unused_loop_index1;
    wire [11:0] unused_loop_index2;

    program_control_unit u_program_control_unit (
        .clk(clk),
        .reset_n(reset_n),
        .start(start),
        .busy(busy),
        .done(done),
        .program_read_valid(program_read_valid),
        .program_read_address(program_read_address),
        .program_read_response_valid(program_read_response_valid),
        .program_read_response_data(program_read_response_data),
        .descriptor_valid(descriptor_valid),
        .descriptor_ready(descriptor_ready),
        .descriptor_pc(descriptor_pc),
        .descriptor_base(descriptor_base),
        .descriptor_ext0(descriptor_ext0),
        .descriptor_ext1(descriptor_ext1),
        .descriptor_ext2(descriptor_ext2),
        .loop_index0(unused_loop_index0),
        .loop_index1(unused_loop_index1),
        .loop_index2(unused_loop_index2),
        .descriptor_complete(descriptor_complete)
    );
endmodule
`default_nettype wire
