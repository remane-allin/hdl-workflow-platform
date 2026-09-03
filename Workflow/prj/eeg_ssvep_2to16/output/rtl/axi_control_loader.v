//==============================================================================
// Module      : axi_control_loader
// File        : axi_control_loader.v
// Project     : profile-programmable shared BCI accelerator
// Description : AXI4-Lite slave and fixed profile-independent window decoder.
// Scope:
//   - Owns one-outstanding AXI write/read protocol state and control registers.
//   - Does not decode signal identity, descriptor legality, or model dimensions.
// Spec Trace:
//   - REQ-RRB-003, REQ-RRB-008, REQ-RRB-021, REQ-RRB-024
// Notes:
//   - Program, parameter, and frame windows use trusted full-width 64-bit writes.
//   - Result reads return one ordered FP16 word in bits 15:0 and last in bit 16.
//==============================================================================

`timescale 1ns/1ps
`default_nettype none

module axi_control_loader (
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
    input  wire        s_axi_rready,
    output wire        start_valid,
    input  wire        start_ready,
    input  wire        busy,
    input  wire        done,
    output wire        program_load_valid,
    input  wire        program_load_ready,
    output wire [8:0]  program_load_address,
    output wire [63:0] program_load_data,
    output wire        parameter_load_valid,
    input  wire        parameter_load_ready,
    output wire [8:0]  parameter_load_address,
    output wire [63:0] parameter_load_data,
    output reg         frame_begin,
    output wire [1:0]  frame_page,
    output wire [63:0] frame_config,
    output wire        frame_valid,
    input  wire        frame_ready,
    output wire [63:0] frame_data,
    input  wire        frame_complete,
    input  wire [8:0]  frame_beat_count,
    input  wire        result_valid,
    output wire        result_ready,
    input  wire [15:0] result_data,
    input  wire        result_last
);
    localparam [15:0] ADDR_CONTROL       = 16'h0000;
    localparam [15:0] ADDR_STATUS        = 16'h0008;
    localparam [15:0] ADDR_PROGRAM_LEN   = 16'h0010;
    localparam [15:0] ADDR_RESULT_LEN    = 16'h0018;
    localparam [15:0] ADDR_FRAME_PAGE    = 16'h0020;
    localparam [15:0] ADDR_FRAME_FORMAT  = 16'h0028;

    localparam [3:0] WINDOW_CONTROL      = 4'h0;
    localparam [3:0] WINDOW_PROGRAM      = 4'h1;
    localparam [3:0] WINDOW_PARAMETER    = 4'h2;
    localparam [3:0] WINDOW_FRAME        = 4'h3;
    localparam [3:0] WINDOW_RESULT       = 4'h4;

    reg         write_address_pending_q;
    reg  [15:0] write_address_q;
    reg         write_data_pending_q;
    reg  [63:0] write_data_q;
    reg  [7:0]  write_strobe_q;
    reg         write_response_valid_q;
    reg  [9:0]  program_length_q;
    reg  [9:0]  result_length_q;
    reg  [1:0]  frame_page_q;
    reg  [63:0] frame_config_q;
    reg         done_sticky_q;
    reg         result_read_pending_q;
    reg         read_response_valid_q;
    reg  [63:0] read_response_data_q;

    wire        write_request;
    wire [3:0]  write_window;
    reg         write_can_complete;
    wire        write_accept;
    wire        write_control;
    wire        read_result_window;
    wire        read_accept;

    function [63:0] merge_write_strobes;
        input [63:0] current_value;
        input [63:0] write_value;
        input [7:0]  write_strobes;
        integer byte_index;
        begin
            merge_write_strobes = current_value;
            for (byte_index = 0; byte_index < 8;
                 byte_index = byte_index + 1) begin
                if (write_strobes[byte_index]) begin
                    merge_write_strobes[byte_index*8 +: 8] =
                        write_value[byte_index*8 +: 8];
                end
                else begin
                    merge_write_strobes[byte_index*8 +: 8] =
                        current_value[byte_index*8 +: 8];
                end
            end
        end
    endfunction

    assign s_axi_awready = ~write_address_pending_q &
                           ~write_response_valid_q;
    assign s_axi_wready = ~write_data_pending_q &
                          ~write_response_valid_q;
    assign s_axi_bresp = 2'b00;
    assign s_axi_bvalid = write_response_valid_q;

    assign write_request = write_address_pending_q &
                           write_data_pending_q &
                           ~write_response_valid_q;
    assign write_window = write_address_q[15:12];
    assign write_control = write_window == WINDOW_CONTROL;
    assign write_accept = write_request & write_can_complete;

    assign program_load_valid = write_request &
                                (write_window == WINDOW_PROGRAM);
    assign program_load_address = write_address_q[11:3];
    assign program_load_data = write_data_q;
    assign parameter_load_valid = write_request &
                                  (write_window == WINDOW_PARAMETER);
    assign parameter_load_address = write_address_q[11:3];
    assign parameter_load_data = write_data_q;
    assign frame_valid = write_request &
                         (write_window == WINDOW_FRAME);
    assign frame_data = write_data_q;

    assign start_valid = write_accept & write_control &
                         (write_address_q == ADDR_CONTROL) &
                         write_data_q[0] & start_ready & frame_complete;
    assign frame_page = frame_page_q;
    assign frame_config = frame_config_q;

    always @(*) begin
        write_can_complete = 1'b1;
        case (write_window)
            WINDOW_CONTROL: begin
                if ((write_address_q == ADDR_FRAME_PAGE) ||
                    (write_address_q == ADDR_FRAME_FORMAT)) begin
                    write_can_complete = start_ready;
                end
                else begin
                    write_can_complete = 1'b1;
                end
            end
            WINDOW_PROGRAM: begin
                write_can_complete = program_load_ready;
            end
            WINDOW_PARAMETER: begin
                write_can_complete = parameter_load_ready;
            end
            WINDOW_FRAME: begin
                write_can_complete = frame_ready;
            end
            default: begin
                write_can_complete = 1'b1;
            end
        endcase
    end

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            write_address_pending_q <= 1'b0;
            write_address_q <= 16'd0;
            write_data_pending_q <= 1'b0;
            write_data_q <= 64'd0;
            write_strobe_q <= 8'd0;
        end
        else begin
            if (write_accept) begin
                write_address_pending_q <= 1'b0;
                write_data_pending_q <= 1'b0;
            end
            else begin
                if (s_axi_awvalid && s_axi_awready) begin
                    write_address_pending_q <= 1'b1;
                    write_address_q <= s_axi_awaddr;
                end
                else begin
                    write_address_pending_q <= write_address_pending_q;
                    write_address_q <= write_address_q;
                end

                if (s_axi_wvalid && s_axi_wready) begin
                    write_data_pending_q <= 1'b1;
                    write_data_q <= s_axi_wdata;
                    write_strobe_q <= s_axi_wstrb;
                end
                else begin
                    write_data_pending_q <= write_data_pending_q;
                    write_data_q <= write_data_q;
                    write_strobe_q <= write_strobe_q;
                end
            end
        end
    end

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            done_sticky_q <= 1'b0;
        end
        else begin
            if (start_valid) begin
                done_sticky_q <= 1'b0;
            end
            else if (done) begin
                done_sticky_q <= 1'b1;
            end
            else begin
                done_sticky_q <= done_sticky_q;
            end
        end
    end

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            write_response_valid_q <= 1'b0;
        end
        else begin
            if (write_response_valid_q && s_axi_bready) begin
                write_response_valid_q <= 1'b0;
            end
            else if (write_accept) begin
                write_response_valid_q <= 1'b1;
            end
            else begin
                write_response_valid_q <= write_response_valid_q;
            end
        end
    end

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            program_length_q <= 10'd0;
            result_length_q <= 10'd0;
            frame_page_q <= 2'd0;
            frame_config_q <= 64'd0;
            frame_begin <= 1'b0;
        end
        else begin
            frame_begin <= 1'b0;
            if (write_accept && write_control) begin
                case (write_address_q)
                    ADDR_PROGRAM_LEN: begin
                        program_length_q <= merge_write_strobes(
                            {54'd0, program_length_q}, write_data_q,
                            write_strobe_q);
                    end
                    ADDR_RESULT_LEN: begin
                        result_length_q <= merge_write_strobes(
                            {54'd0, result_length_q}, write_data_q,
                            write_strobe_q);
                    end
                    ADDR_FRAME_PAGE: begin
                        frame_page_q <= merge_write_strobes(
                            {62'd0, frame_page_q}, write_data_q,
                            write_strobe_q);
                        frame_begin <= 1'b1;
                    end
                    ADDR_FRAME_FORMAT: begin
                        frame_config_q <= merge_write_strobes(
                            frame_config_q, write_data_q, write_strobe_q);
                        frame_begin <= 1'b1;
                    end
                    default: begin
                        program_length_q <= program_length_q;
                        result_length_q <= result_length_q;
                        frame_page_q <= frame_page_q;
                        frame_config_q <= frame_config_q;
                    end
                endcase
            end
            else begin
                program_length_q <= program_length_q;
                result_length_q <= result_length_q;
                frame_page_q <= frame_page_q;
                frame_config_q <= frame_config_q;
            end
        end
    end

    assign read_result_window = s_axi_araddr[15:12] == WINDOW_RESULT;
    assign s_axi_arready = ~result_read_pending_q &
                           ~read_response_valid_q;
    assign read_accept = s_axi_arvalid & s_axi_arready;
    assign result_ready = result_read_pending_q &
                          ~read_response_valid_q;
    assign s_axi_rdata = read_response_data_q;
    assign s_axi_rresp = 2'b00;
    assign s_axi_rvalid = read_response_valid_q;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            result_read_pending_q <= 1'b0;
            read_response_valid_q <= 1'b0;
            read_response_data_q <= 64'd0;
        end
        else begin
            if (read_response_valid_q && s_axi_rready) begin
                read_response_valid_q <= 1'b0;
            end
            else if (result_read_pending_q && result_valid) begin
                read_response_valid_q <= 1'b1;
            end
            else if (read_accept && !read_result_window) begin
                read_response_valid_q <= 1'b1;
            end
            else begin
                read_response_valid_q <= read_response_valid_q;
            end

            if (result_read_pending_q && result_valid) begin
                read_response_data_q <=
                    {47'd0, result_last, result_data};
            end
            else if (read_accept && !read_result_window) begin
                case (s_axi_araddr)
                    ADDR_STATUS: begin
                        read_response_data_q <=
                            {48'd0, frame_beat_count, 4'd0,
                             frame_complete, done_sticky_q, busy};
                    end
                    ADDR_PROGRAM_LEN: begin
                        read_response_data_q <=
                            {54'd0, program_length_q};
                    end
                    ADDR_RESULT_LEN: begin
                        read_response_data_q <=
                            {54'd0, result_length_q};
                    end
                    ADDR_FRAME_PAGE: begin
                        read_response_data_q <=
                            {62'd0, frame_page_q};
                    end
                    ADDR_FRAME_FORMAT: begin
                        read_response_data_q <= frame_config_q;
                    end
                    default: begin
                        read_response_data_q <= 64'd0;
                    end
                endcase
            end
            else begin
                read_response_data_q <= read_response_data_q;
            end

            if (result_read_pending_q && result_valid) begin
                result_read_pending_q <= 1'b0;
            end
            else if (read_accept && read_result_window) begin
                result_read_pending_q <= 1'b1;
            end
            else begin
                result_read_pending_q <= result_read_pending_q;
            end
        end
    end
endmodule
`default_nettype wire
