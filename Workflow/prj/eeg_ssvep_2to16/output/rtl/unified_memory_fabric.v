//==============================================================================
// Module      : unified_memory_fabric
// Description : Single feature-memory bank/port owner.
// Scope:
//   - Arbitrates service fill, rolling-window reads, and retire commits once.
//   - Freezes read-response ownership when a bank request is sampled.
//   - Keeps every ordinary payload at or below one 128-bit beat.
//   - Owns no descriptor, profile, arithmetic, or loop control.
// Spec Trace:
//   - REQ-RRB-005, REQ-RRB-007, REQ-RRB-012, REQ-RRB-019
//   - MOD-MEMORY-FABRIC, IF-FEATURE-MEMORY
//==============================================================================
`timescale 1ns/1ps
`default_nettype none

module unified_memory_fabric (
    input  wire         clk,
    input  wire         reset_n,

    input  wire [3:0]   service_a_valid,
    input  wire [43:0]  service_a_address,
    input  wire [3:0]   service_b_valid,
    input  wire [43:0]  service_b_address,
    output wire [3:0]   service_a_response_valid,
    output wire [63:0]  service_a_response_data,
    output wire [3:0]   service_b_response_valid,
    output wire [63:0]  service_b_response_data,

    input  wire         window_a_valid,
    input  wire [12:0]  window_a_address,
    output wire         window_a_response_valid,
    output reg  [15:0]  window_a_response_data,

    input  wire [3:0]   retire_a_valid,
    input  wire [51:0]  retire_a_address,
    input  wire [63:0]  retire_a_data,
    input  wire [3:0]   retire_b_valid,
    input  wire [51:0]  retire_b_address,
    input  wire [63:0]  retire_b_data,

    output reg  [3:0]   memory_a_valid,
    output reg  [3:0]   memory_a_write,
    output reg  [51:0]  memory_a_address,
    output reg  [63:0]  memory_a_write_data,
    output reg  [3:0]   memory_b_valid,
    output reg  [3:0]   memory_b_write,
    output reg  [51:0]  memory_b_address,
    output reg  [63:0]  memory_b_write_data,
    input  wire [3:0]   memory_a_response_valid,
    input  wire [63:0]  memory_a_response_data,
    input  wire [3:0]   memory_b_response_valid,
    input  wire [63:0]  memory_b_response_data
);
    reg [3:0] selected_a_window;
    reg [3:0] response_a_window_q;
    integer bank;

    assign service_a_response_valid = memory_a_response_valid &
        ~response_a_window_q;
    assign service_a_response_data = memory_a_response_data;
    assign service_b_response_valid = memory_b_response_valid;
    assign service_b_response_data = memory_b_response_data;
    assign window_a_response_valid =
        |(memory_a_response_valid & response_a_window_q);

    always @(*) begin
        window_a_response_data = 16'd0;
        for (bank = 0; bank < 4; bank = bank + 1) begin
            if (memory_a_response_valid[bank] &&
                response_a_window_q[bank])
                window_a_response_data =
                    memory_a_response_data[bank*16 +: 16];
        end
    end

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            response_a_window_q <= 4'd0;
        end
        else begin
            response_a_window_q <= selected_a_window;
        end
    end

    always @(*) begin
        selected_a_window = 4'd0;
        memory_a_valid = service_a_valid;
        memory_a_write = 4'd0;
        memory_a_write_data = 64'd0;
        memory_a_address[12:0] = {service_a_address[10:0], 2'd0};
        memory_a_address[25:13] = {service_a_address[21:11], 2'd1};
        memory_a_address[38:26] = {service_a_address[32:22], 2'd2};
        memory_a_address[51:39] = {service_a_address[43:33], 2'd3};
        memory_b_valid = service_b_valid;
        memory_b_write = 4'd0;
        memory_b_write_data = 64'd0;
        memory_b_address[12:0] = {service_b_address[10:0], 2'd0};
        memory_b_address[25:13] = {service_b_address[21:11], 2'd1};
        memory_b_address[38:26] = {service_b_address[32:22], 2'd2};
        memory_b_address[51:39] = {service_b_address[43:33], 2'd3};

        if (window_a_valid) begin
            memory_a_valid[window_a_address[1:0]] = 1'b1;
            memory_a_write[window_a_address[1:0]] = 1'b0;
            memory_a_address[window_a_address[1:0]*13 +: 13] =
                window_a_address;
            selected_a_window[window_a_address[1:0]] = 1'b1;
        end
        for (bank = 0; bank < 4; bank = bank + 1) begin
            if (retire_a_valid[bank]) begin
                memory_a_valid[bank] = 1'b1;
                memory_a_write[bank] = 1'b1;
                memory_a_address[bank*13 +: 13] =
                    retire_a_address[bank*13 +: 13];
                memory_a_write_data[bank*16 +: 16] =
                    retire_a_data[bank*16 +: 16];
                selected_a_window[bank] = 1'b0;
            end
            if (retire_b_valid[bank]) begin
                memory_b_valid[bank] = 1'b1;
                memory_b_write[bank] = 1'b1;
                memory_b_address[bank*13 +: 13] =
                    retire_b_address[bank*13 +: 13];
                memory_b_write_data[bank*16 +: 16] =
                    retire_b_data[bank*16 +: 16];
            end
        end
    end
endmodule
`default_nettype wire
