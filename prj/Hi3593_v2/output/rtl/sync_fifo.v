//==============================================================================
// Module      : sync_fifo
// File        : sync_fifo.v
// Project     : Hi3593_v2
// Description : 32-entry by 32-bit FIFO with selectable full-write policy.
// Scope:
//   - Owns FIFO storage, pointers, count, status, and overflow observation.
//   - Does not own SPI opcodes, register fields, or ARINC bit timing.
// Spec Trace:
//   - REQ-FIFO-001
// Notes:
//   - OVERWRITE_ON_FULL=1 keeps count full and replaces location 31.
//==============================================================================

module sync_fifo #(
    parameter OVERWRITE_ON_FULL = 0
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        clear,
    input  wire        wr_en,
    input  wire        rd_en,
    input  wire [31:0] wr_data,
    output reg  [31:0] rd_data,
    output wire        empty,
    output wire        half,
    output wire        full,
    output reg  [5:0]  count,
    output reg         overflow_seen
);

//------------------------------------------------------------------------------
// Internal Signals
//------------------------------------------------------------------------------

reg [31:0] mem [0:31];
reg [4:0]  wr_ptr;
reg [4:0]  rd_ptr;

wire do_read;
wire do_write_normal;
wire do_write_overwrite;

assign empty = (count == 6'd0);
assign half  = (count >= 6'd16);
assign full  = (count == 6'd32);

assign do_read            = rd_en && !empty;
assign do_write_normal    = wr_en && !full;
assign do_write_overwrite = wr_en && full && (OVERWRITE_ON_FULL != 0);

//------------------------------------------------------------------------------
// Storage And Status
//------------------------------------------------------------------------------

always @(posedge clk) begin
    if (rst) begin
        wr_ptr        <= 5'd0;
        rd_ptr        <= 5'd0;
        count         <= 6'd0;
        rd_data       <= 32'd0;
        overflow_seen <= 1'b0;
    end
    else if (clear) begin
        wr_ptr        <= 5'd0;
        rd_ptr        <= 5'd0;
        count         <= 6'd0;
        rd_data       <= 32'd0;
        overflow_seen <= 1'b0;
    end
    else begin
        if (do_read) begin
            rd_data <= mem[rd_ptr];
            rd_ptr  <= rd_ptr + 5'd1;
        end
        else begin
            rd_data <= rd_data;
            rd_ptr  <= rd_ptr;
        end

        if (do_write_normal) begin
            mem[wr_ptr] <= wr_data;
            wr_ptr      <= wr_ptr + 5'd1;
        end
        else if (do_write_overwrite) begin
            mem[5'd31]     <= wr_data;
            wr_ptr         <= wr_ptr;
            overflow_seen  <= 1'b1;
        end
        else begin
            wr_ptr        <= wr_ptr;
            overflow_seen <= overflow_seen;
        end

        if (do_write_normal && !do_read) begin
            count <= count + 6'd1;
        end
        else if (!do_write_normal && do_read) begin
            count <= count - 6'd1;
        end
        else begin
            count <= count;
        end
    end
end

endmodule
