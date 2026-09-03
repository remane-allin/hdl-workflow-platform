//==============================================================================
// Module      : shared_bci_accel_top
// File        : shared_bci_accel_top.v
// Project     : profile-programmable shared BCI accelerator
// Description : Hierarchy-only AXI4-Lite integration top.
// Scope:
//   - Connects the fixed-window AXI loader to one reusable execution core.
//   - Contains no protocol, profile, scheduling, storage, or arithmetic logic.
// Spec Trace:
//   - REQ-RRB-003, REQ-RRB-019, REQ-RRB-021, REQ-RRB-023, REQ-RRB-024
// Notes:
//   - One synchronous accel_clk domain; reset_n is active low.
//==============================================================================

`timescale 1ns/1ps
`default_nettype none

module shared_bci_accel_top (
    input  wire        clk,
    input  wire        reset_n,
    input  wire [15:0] s_axi_awaddr,
    input  wire        s_axi_awvalid,
    output wire        s_axi_awready,
    input  wire [63:0] s_axi_wdata,
    input  wire [7:0]  s_axi_wstrb,
    input  wire        s_axi_wvalid,
    output wire        s_axi_wready,
    output wire [1:0]  s_axi_bresp,
    output wire        s_axi_bvalid,
    input  wire        s_axi_bready,
    input  wire [15:0] s_axi_araddr,
    input  wire        s_axi_arvalid,
    output wire        s_axi_arready,
    output wire [63:0] s_axi_rdata,
    output wire [1:0]  s_axi_rresp,
    output wire        s_axi_rvalid,
    input  wire        s_axi_rready
);
    wire        core_start_valid;
    wire        core_start_ready;
    wire        core_busy;
    wire        core_done;
    wire        core_program_load_valid;
    wire        core_program_load_ready;
    wire [8:0]  core_program_load_address;
    wire [63:0] core_program_load_data;
    wire        core_parameter_load_valid;
    wire        core_parameter_load_ready;
    wire [8:0]  core_parameter_load_address;
    wire [63:0] core_parameter_load_data;
    wire        core_frame_begin;
    wire [1:0]  core_frame_page;
    wire [63:0] core_frame_config;
    wire        core_frame_valid;
    wire        core_frame_ready;
    wire [63:0] core_frame_data;
    wire        core_frame_complete;
    wire [8:0]  core_frame_beat_count;
    wire        core_result_valid;
    wire        core_result_ready;
    wire [15:0] core_result_data;
    wire        core_result_last;

    axi_control_loader u_axi_control_loader (
        .clk(clk),
        .reset_n(reset_n),
        .s_axi_awaddr(s_axi_awaddr),
        .s_axi_awvalid(s_axi_awvalid),
        .s_axi_awready(s_axi_awready),
        .s_axi_wdata(s_axi_wdata),
        .s_axi_wstrb(s_axi_wstrb),
        .s_axi_wvalid(s_axi_wvalid),
        .s_axi_wready(s_axi_wready),
        .s_axi_bresp(s_axi_bresp),
        .s_axi_bvalid(s_axi_bvalid),
        .s_axi_bready(s_axi_bready),
        .s_axi_araddr(s_axi_araddr),
        .s_axi_arvalid(s_axi_arvalid),
        .s_axi_arready(s_axi_arready),
        .s_axi_rdata(s_axi_rdata),
        .s_axi_rresp(s_axi_rresp),
        .s_axi_rvalid(s_axi_rvalid),
        .s_axi_rready(s_axi_rready),
        .start_valid(core_start_valid),
        .start_ready(core_start_ready),
        .busy(core_busy),
        .done(core_done),
        .program_load_valid(core_program_load_valid),
        .program_load_ready(core_program_load_ready),
        .program_load_address(core_program_load_address),
        .program_load_data(core_program_load_data),
        .parameter_load_valid(core_parameter_load_valid),
        .parameter_load_ready(core_parameter_load_ready),
        .parameter_load_address(core_parameter_load_address),
        .parameter_load_data(core_parameter_load_data),
        .frame_begin(core_frame_begin),
        .frame_page(core_frame_page),
        .frame_config(core_frame_config),
        .frame_valid(core_frame_valid),
        .frame_ready(core_frame_ready),
        .frame_data(core_frame_data),
        .frame_complete(core_frame_complete),
        .frame_beat_count(core_frame_beat_count),
        .result_valid(core_result_valid),
        .result_ready(core_result_ready),
        .result_data(core_result_data),
        .result_last(core_result_last)
    );

    shared_bci_accel_core u_shared_bci_accel_core (
        .clk(clk),
        .reset_n(reset_n),
        .start_valid(core_start_valid),
        .start_ready(core_start_ready),
        .busy(core_busy),
        .done(core_done),
        .program_load_valid(core_program_load_valid),
        .program_load_ready(core_program_load_ready),
        .program_load_address(core_program_load_address),
        .program_load_data(core_program_load_data),
        .parameter_load_valid(core_parameter_load_valid),
        .parameter_load_ready(core_parameter_load_ready),
        .parameter_load_address(core_parameter_load_address),
        .parameter_load_data(core_parameter_load_data),
        .frame_begin(core_frame_begin),
        .frame_page(core_frame_page),
        .frame_config(core_frame_config),
        .frame_valid(core_frame_valid),
        .frame_ready(core_frame_ready),
        .frame_data(core_frame_data),
        .frame_complete(core_frame_complete),
        .frame_beat_count(core_frame_beat_count),
        .result_valid(core_result_valid),
        .result_ready(core_result_ready),
        .result_data(core_result_data),
        .result_last(core_result_last)
    );
endmodule
`default_nettype wire
