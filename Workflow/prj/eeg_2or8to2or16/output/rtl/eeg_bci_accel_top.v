// Module: eeg_bci_accel_top
// Description: Top-level AXI-Lite, shared-BRAM, accelerator integration.
// Scope: Frozen STREAM_TDP/V2 external interface for the 16-channel profile.
// Spec Trace: REQ-EEG-ARCH-001, IF-AXI-CTRL, IF-BRAM-DATA.
`timescale 1ns/1ps
`default_nettype none

module eeg_bci_accel_top #(
    parameter C_S00_AXI_ADDR_WIDTH = 6
) (
    input  wire                              s00_axi_aclk,
    input  wire                              s00_axi_aresetn,
    input  wire [C_S00_AXI_ADDR_WIDTH-1:0]   s00_axi_awaddr,
    input  wire                              s00_axi_awvalid,
    output wire                              s00_axi_awready,
    input  wire [31:0]                       s00_axi_wdata,
    input  wire [3:0]                        s00_axi_wstrb,
    input  wire                              s00_axi_wvalid,
    output wire                              s00_axi_wready,
    output wire [1:0]                        s00_axi_bresp,
    output wire                              s00_axi_bvalid,
    input  wire                              s00_axi_bready,
    input  wire [C_S00_AXI_ADDR_WIDTH-1:0]   s00_axi_araddr,
    input  wire                              s00_axi_arvalid,
    output wire                              s00_axi_arready,
    output wire [31:0]                       s00_axi_rdata,
    output wire [1:0]                        s00_axi_rresp,
    output wire                              s00_axi_rvalid,
    input  wire                              s00_axi_rready,
    output wire                              ram_clk,
    output wire                              ram_rst,
    output wire                              ram_en,
    output wire [31:0]                       ram_addr,
    output wire [3:0]                        ram_we,
    output wire [31:0]                       ram_wr_data,
    input  wire [31:0]                       ram_rd_data,
    output wire                              infer_done,
    output wire [3:0]                        class_led
);
    wire [31:0] start_address;
    wire [31:0] read_length;
    wire [2:0] iport_state;
    wire [1:0] profile_select;
    wire [1:0] instruction_version;
    wire reader_command_valid;
    wire reader_command_ready;
    wire core_command_valid;
    wire core_command_ready;
    wire clear_counters;
    wire snapshot_counters;
    wire reader_busy;
    wire reader_error;
    wire stream_valid;
    wire stream_ready;
    wire [15:0] stream_data;
    wire [2:0] stream_type;
    wire stream_last;
    wire core_busy;
    wire [31:0] result;
    wire [31:0] total_cycles;
    wire [31:0] memory_stalls;
    wire [31:0] producer_stalls;
    wire [31:0] consumer_stalls;
    wire [31:0] mac_activity;
    wire [31:0] tile_occupancy;
    wire core_error;

    eeg_bci_clock_reset_bridge clock_reset_bridge (
        .axi_clock(s00_axi_aclk),
        .axi_reset_n(s00_axi_aresetn),
        .ram_clock(ram_clk),
        .ram_reset(ram_rst)
    );

    axi_lite_control #(
        .ADDR_WIDTH(C_S00_AXI_ADDR_WIDTH)
    ) control (
        .clk(s00_axi_aclk),
        .rst_n(s00_axi_aresetn),
        .s_axi_awaddr(s00_axi_awaddr),
        .s_axi_awvalid(s00_axi_awvalid),
        .s_axi_awready(s00_axi_awready),
        .s_axi_wdata(s00_axi_wdata),
        .s_axi_wstrb(s00_axi_wstrb),
        .s_axi_wvalid(s00_axi_wvalid),
        .s_axi_wready(s00_axi_wready),
        .s_axi_bresp(s00_axi_bresp),
        .s_axi_bvalid(s00_axi_bvalid),
        .s_axi_bready(s00_axi_bready),
        .s_axi_araddr(s00_axi_araddr),
        .s_axi_arvalid(s00_axi_arvalid),
        .s_axi_arready(s00_axi_arready),
        .s_axi_rdata(s00_axi_rdata),
        .s_axi_rresp(s00_axi_rresp),
        .s_axi_rvalid(s00_axi_rvalid),
        .s_axi_rready(s00_axi_rready),
        .start_address(start_address),
        .read_length(read_length),
        .iport_state(iport_state),
        .profile_select(profile_select),
        .instruction_version(instruction_version),
        .reader_command_valid(reader_command_valid),
        .reader_command_ready(reader_command_ready),
        .core_command_valid(core_command_valid),
        .core_command_ready(core_command_ready),
        .clear_counters(clear_counters),
        .snapshot_counters(snapshot_counters),
        .reader_busy(reader_busy),
        .core_busy(core_busy),
        .classification_result(result),
        .accelerator_error(reader_error || core_error),
        .total_cycles(total_cycles),
        .memory_stalls(memory_stalls),
        .producer_stalls(producer_stalls),
        .consumer_stalls(consumer_stalls),
        .mac_activity(mac_activity),
        .tile_occupancy(tile_occupancy)
    );

    ps_bram_stream_reader reader (
        .clk(s00_axi_aclk),
        .rst_n(s00_axi_aresetn),
        .command_valid(reader_command_valid),
        .command_ready(reader_command_ready),
        .start_address(start_address),
        .read_length(read_length),
        .stream_type_select(iport_state),
        .ram_en(ram_en),
        .ram_addr(ram_addr),
        .ram_we(ram_we),
        .ram_wr_data(ram_wr_data),
        .ram_rd_data(ram_rd_data),
        .stream_valid(stream_valid),
        .stream_ready(stream_ready),
        .stream_data(stream_data),
        .stream_type(stream_type),
        .stream_last(stream_last),
        .busy(reader_busy),
        .range_error(reader_error)
    );

    bci_accel_core core (
        .clk(s00_axi_aclk),
        .rst_n(s00_axi_aresetn),
        .stream_valid(stream_valid),
        .stream_ready(stream_ready),
        .stream_data(stream_data),
        .stream_type(stream_type),
        .stream_last(stream_last),
        .command_valid(core_command_valid),
        .command_ready(core_command_ready),
        .profile_select(profile_select),
        .instruction_version(instruction_version),
        .busy(core_busy),
        .result(result),
        .infer_done(infer_done),
        .class_led(class_led),
        .error(core_error),
        .clear_counters(clear_counters),
        .snapshot_counters(snapshot_counters),
        .total_cycles_snapshot(total_cycles),
        .memory_stalls_snapshot(memory_stalls),
        .producer_stalls_snapshot(producer_stalls),
        .consumer_stalls_snapshot(consumer_stalls),
        .mac_activity_snapshot(mac_activity),
        .tile_occupancy_snapshot(tile_occupancy),
        .trace_write_valid(),
        .trace_opcode(),
        .trace_write_address(),
        .trace_write_data(),
        .trace_write2_valid(),
        .trace_write2_address(),
        .trace_write2_data()
    );
endmodule
`default_nettype wire
