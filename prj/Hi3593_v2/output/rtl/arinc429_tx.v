//==============================================================================
// Module      : arinc429_tx
// File        : arinc429_tx.v
// Project     : Hi3593_v2
// Description : ARINC 429 transmit word scheduler and digital driver controls.
// Scope:
//   - Owns TX FIFO pop, parity insertion, bit-cell sequencing, TX1IN/TX0IN/SLP.
//   - Does not own FIFO storage or SPI/register decode.
// Spec Trace:
//   - REQ-TX-001, REQ-ARINC-001
// Notes:
//   - TX1IN/TX0IN drive an external HI-8592-class line driver.
//==============================================================================

module arinc429_tx (
    input  wire        ACLK,
    input  wire        reset,
    input  wire        tx_start_pulse,
    input  wire [7:0]  tx_control,
    input  wire        fifo_empty,
    input  wire [31:0] fifo_rdata,
    output reg         fifo_rd,
    output reg         TX1IN,
    output reg         TX0IN,
    output reg         SLP,
    output reg         busy
);

//------------------------------------------------------------------------------
// FSM And Datapath Signals
//------------------------------------------------------------------------------

localparam [1:0] ST_IDLE = 2'd0;
localparam [1:0] ST_LOAD = 2'd1;
localparam [1:0] ST_BIT  = 2'd2;
localparam [1:0] ST_GAP  = 2'd3;

reg [1:0]  state_cur;
reg [1:0]  state_nxt;
reg [31:0] word_q;
reg [5:0]  bit_count;
reg [8:0]  cell_count;
reg [8:0]  gap_count;
reg        bit_half;

wire tmode;
wire selftest;
wire tparity;
wire oddeven;
wire rate_low;
wire launch_request;
wire [8:0] data_half_limit;
wire [8:0] gap_limit;
wire parity_bit;
wire current_bit;

assign tmode           = tx_control[5];
assign selftest        = tx_control[4];
assign oddeven         = tx_control[3];
assign tparity         = tx_control[2];
assign rate_low        = tx_control[0];
assign launch_request  = (tx_start_pulse || tmode) && !fifo_empty && !busy;
assign data_half_limit = rate_low ? 9'd40 : 9'd5;
assign gap_limit       = rate_low ? 9'd320 : 9'd40;
assign parity_bit      = oddeven ? (^fifo_rdata[30:0]) : ~(^fifo_rdata[30:0]);
assign current_bit     = word_q[bit_count[4:0]];

//------------------------------------------------------------------------------
// State Register
//------------------------------------------------------------------------------

always @(posedge ACLK) begin
    if (reset) begin
        state_cur <= ST_IDLE;
    end
    else begin
        state_cur <= state_nxt;
    end
end

//------------------------------------------------------------------------------
// Next-State Decode
//------------------------------------------------------------------------------

always @(*) begin
    state_nxt = state_cur;
    case (state_cur)
        ST_IDLE: begin
            if (launch_request) begin
                state_nxt = ST_LOAD;
            end
            else begin
                state_nxt = ST_IDLE;
            end
        end
        ST_LOAD: begin
            state_nxt = ST_BIT;
        end
        ST_BIT: begin
            if ((bit_count == 6'd31) && bit_half && (cell_count == data_half_limit - 9'd1)) begin
                state_nxt = ST_GAP;
            end
            else begin
                state_nxt = ST_BIT;
            end
        end
        ST_GAP: begin
            if (gap_count == gap_limit - 9'd1) begin
                state_nxt = ST_IDLE;
            end
            else begin
                state_nxt = ST_GAP;
            end
        end
        default: begin
            state_nxt = ST_IDLE;
        end
    endcase
end

//------------------------------------------------------------------------------
// Output And Datapath Registers
//------------------------------------------------------------------------------

always @(posedge ACLK) begin
    if (reset) begin
        word_q     <= 32'd0;
        bit_count  <= 6'd0;
        cell_count <= 9'd0;
        gap_count  <= 9'd0;
        bit_half   <= 1'b0;
        fifo_rd    <= 1'b0;
        TX1IN      <= 1'b0;
        TX0IN      <= 1'b0;
        SLP        <= 1'b1;
        busy       <= 1'b0;
    end
    else begin
        fifo_rd <= 1'b0;
        SLP     <= !rate_low;

        case (state_cur)
            ST_IDLE: begin
                TX1IN      <= 1'b0;
                TX0IN      <= 1'b0;
                busy       <= 1'b0;
                bit_count  <= 6'd0;
                cell_count <= 9'd0;
                gap_count  <= 9'd0;
                bit_half   <= 1'b0;
            end
            ST_LOAD: begin
                fifo_rd    <= 1'b1;
                busy       <= 1'b1;
                bit_count  <= 6'd0;
                cell_count <= 9'd0;
                gap_count  <= 9'd0;
                bit_half   <= 1'b0;
                if (tparity) begin
                    word_q <= {parity_bit, fifo_rdata[30:0]};
                end
                else begin
                    word_q <= fifo_rdata;
                end
            end
            ST_BIT: begin
                busy <= 1'b1;
                if (selftest || bit_half) begin
                    TX1IN <= 1'b0;
                    TX0IN <= 1'b0;
                end
                else if (current_bit) begin
                    TX1IN <= 1'b1;
                    TX0IN <= 1'b0;
                end
                else begin
                    TX1IN <= 1'b0;
                    TX0IN <= 1'b1;
                end

                if (cell_count == data_half_limit - 9'd1) begin
                    cell_count <= 9'd0;
                    if (bit_half) begin
                        bit_half  <= 1'b0;
                        bit_count <= bit_count + 6'd1;
                    end
                    else begin
                        bit_half  <= 1'b1;
                        bit_count <= bit_count;
                    end
                end
                else begin
                    cell_count <= cell_count + 9'd1;
                    bit_half   <= bit_half;
                    bit_count  <= bit_count;
                end
            end
            ST_GAP: begin
                busy  <= 1'b1;
                TX1IN <= 1'b0;
                TX0IN <= 1'b0;
                if (gap_count == gap_limit - 9'd1) begin
                    gap_count <= 9'd0;
                end
                else begin
                    gap_count <= gap_count + 9'd1;
                end
            end
            default: begin
                word_q     <= 32'd0;
                bit_count  <= 6'd0;
                cell_count <= 9'd0;
                gap_count  <= 9'd0;
                bit_half   <= 1'b0;
                TX1IN      <= 1'b0;
                TX0IN      <= 1'b0;
                busy       <= 1'b0;
            end
        endcase
    end
end

endmodule
