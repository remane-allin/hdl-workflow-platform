// Module: ps_bram_stream_reader
// Description: Converts shared PS BRAM words into the typed 16-bit stream.
// Scope: Bounded parameter, instruction, and sample load transactions.
// Spec Trace: IF-BRAM-DATA, REQ-EEG-CH16-001.
`timescale 1ns/1ps
`default_nettype none

module ps_bram_stream_reader (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        command_valid,
    output wire        command_ready,
    input  wire [31:0] start_address,
    input  wire [31:0] read_length,
    input  wire [2:0]  stream_type_select,
    output reg         ram_en,
    output reg  [31:0] ram_addr,
    output wire [3:0]  ram_we,
    output wire [31:0] ram_wr_data,
    input  wire [31:0] ram_rd_data,
    output reg         stream_valid,
    input  wire        stream_ready,
    output reg  [15:0] stream_data,
    output reg  [2:0]  stream_type,
    output reg         stream_last,
    output reg         busy,
    output reg         range_error
);
    localparam ST_IDLE = 3'd0;
    localparam ST_ISSUE = 3'd1;
    localparam ST_WAIT = 3'd2;
    localparam ST_CAPTURE = 3'd3;
    localparam ST_STREAM = 3'd4;

    reg [2:0] state;
    reg [31:0] word_index;
    reg [31:0] latched_length;
    reg [31:0] latched_address;
    reg [2:0] latched_type;

    assign command_ready = (state == ST_IDLE);
    assign ram_we = 4'b0000;
    assign ram_wr_data = 32'd0;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= ST_IDLE;
            word_index <= 32'd0;
            latched_length <= 32'd0;
            latched_address <= 32'd0;
            latched_type <= 3'd0;
            ram_en <= 1'b0;
            ram_addr <= 32'd0;
            stream_valid <= 1'b0;
            stream_data <= 16'd0;
            stream_type <= 3'd0;
            stream_last <= 1'b0;
            busy <= 1'b0;
            range_error <= 1'b0;
        end
        else begin
            ram_en <= 1'b0;
            case (state)
                ST_IDLE: begin
                    stream_valid <= 1'b0;
                    busy <= 1'b0;
                    if (command_valid) begin
                        if ((read_length == 0) ||
                            ((stream_type_select == 3'b101) && (read_length > 2048)) ||
                            ((stream_type_select == 3'b011) && (read_length > 1076)) ||
                            ((stream_type_select == 3'b110) && (read_length > 264))) begin
                            range_error <= 1'b1;
                        end
                        else begin
                            latched_length <= read_length;
                            latched_address <= start_address;
                            latched_type <= stream_type_select;
                            word_index <= 32'd0;
                            busy <= 1'b1;
                            state <= ST_ISSUE;
                        end
                    end
                end
                ST_ISSUE: begin
                    ram_en <= 1'b1;
                    ram_addr <= latched_address + (word_index << 2'd2);
                    state <= ST_WAIT;
                end
                ST_WAIT: begin
                    // The physical block-memory port is synchronous.  ram_en and
                    // ram_addr become visible to it after the ST_ISSUE edge; its
                    // registered read data becomes valid after this wait edge.
                    state <= ST_CAPTURE;
                end
                ST_CAPTURE: begin
                    stream_data <= ram_rd_data[15:0];
                    stream_type <= latched_type;
                    stream_last <= (word_index + 1'b1 == latched_length);
                    stream_valid <= 1'b1;
                    state <= ST_STREAM;
                end
                ST_STREAM: begin
                    if (stream_valid && stream_ready) begin
                        stream_valid <= 1'b0;
                        if (stream_last) begin
                            busy <= 1'b0;
                            state <= ST_IDLE;
                        end
                        else begin
                            word_index <= word_index + 1'b1;
                            state <= ST_ISSUE;
                        end
                    end
                end
                default: state <= ST_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
