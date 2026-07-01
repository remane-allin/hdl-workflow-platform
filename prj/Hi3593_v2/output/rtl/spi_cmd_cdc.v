//==============================================================================
// Module      : spi_cmd_cdc
// File        : spi_cmd_cdc.v
// Project     : Hi3593_v2
// Description : Bundled request/acknowledge CDC for SPI command transactions.
// Scope:
//   - Owns SCK-to-ACLK command event synchronization and ACLK-to-SCK readback hold.
//   - Does not own SPI bit framing, register side effects, or readback decode.
// Spec Trace:
//   - REQ-SPI-001, REQ-SPI-002
// Notes:
//   - Command and readback buses are held stable until the paired toggle handshake completes.
//==============================================================================

module spi_cmd_cdc (
    input  wire         ACLK,
    input  wire         SCK,
    input  wire         MR,
    input  wire         sck_cmd_req,
    input  wire [7:0]   sck_opcode,
    input  wire [255:0] sck_wdata,
    input  wire [255:0] read_data_aclk,
    output reg          sck_cmd_ack,
    output reg  [255:0] read_data_sck,
    output reg          aclk_cmd_valid,
    output reg  [7:0]   aclk_opcode,
    output reg  [255:0] aclk_wdata
);

//------------------------------------------------------------------------------
// Internal Signals
//------------------------------------------------------------------------------

localparam [0:0] ST_IDLE = 1'b0;
localparam [0:0] ST_RESP = 1'b1;

reg [2:0]   req_sync;
reg [2:0]   ack_sync;
reg         req_seen;
reg         ack_seen_sck;
reg         ack_toggle_aclk;
reg         state_cur;
reg [255:0] read_data_hold;

wire req_event_aclk;
wire ack_event_sck;

assign req_event_aclk = (req_sync[2] != req_seen);
assign ack_event_sck  = (ack_sync[2] != ack_seen_sck);

//------------------------------------------------------------------------------
// ACLK Command Capture And Response Toggle
//------------------------------------------------------------------------------

always @(posedge ACLK or posedge MR) begin
    if (MR) begin
        req_sync        <= 3'b000;
        req_seen        <= 1'b0;
        ack_toggle_aclk <= 1'b0;
        state_cur       <= ST_IDLE;
        aclk_cmd_valid  <= 1'b0;
        aclk_opcode     <= 8'd0;
        aclk_wdata      <= 256'd0;
        read_data_hold  <= 256'd0;
    end
    else begin
        req_sync       <= {req_sync[1:0], sck_cmd_req};
        aclk_cmd_valid <= 1'b0;

        case (state_cur)
            ST_IDLE: begin
                if (req_event_aclk) begin
                    req_seen        <= req_sync[2];
                    aclk_opcode     <= sck_opcode;
                    aclk_wdata      <= sck_wdata;
                    aclk_cmd_valid  <= 1'b1;
                    state_cur       <= ST_RESP;
                end
                else begin
                    req_seen        <= req_seen;
                    aclk_opcode     <= aclk_opcode;
                    aclk_wdata      <= aclk_wdata;
                    state_cur       <= ST_IDLE;
                end
                read_data_hold  <= read_data_hold;
                ack_toggle_aclk <= ack_toggle_aclk;
            end
            ST_RESP: begin
                read_data_hold  <= read_data_aclk;
                ack_toggle_aclk <= ~ack_toggle_aclk;
                req_seen        <= req_seen;
                aclk_opcode     <= aclk_opcode;
                aclk_wdata      <= aclk_wdata;
                state_cur       <= ST_IDLE;
            end
            default: begin
                req_seen        <= req_seen;
                aclk_opcode     <= aclk_opcode;
                aclk_wdata      <= aclk_wdata;
                read_data_hold  <= read_data_hold;
                ack_toggle_aclk <= ack_toggle_aclk;
                state_cur       <= ST_IDLE;
            end
        endcase
    end
end

//------------------------------------------------------------------------------
// SCK Response Capture
//------------------------------------------------------------------------------

always @(posedge SCK or posedge MR) begin
    if (MR) begin
        ack_sync      <= 3'b000;
        ack_seen_sck  <= 1'b0;
        sck_cmd_ack   <= 1'b0;
        read_data_sck <= 256'd0;
    end
    else begin
        ack_sync <= {ack_sync[1:0], ack_toggle_aclk};
        if (ack_event_sck) begin
            ack_seen_sck  <= ack_sync[2];
            sck_cmd_ack   <= ack_sync[2];
            read_data_sck <= read_data_hold;
        end
        else begin
            ack_seen_sck  <= ack_seen_sck;
            sck_cmd_ack   <= sck_cmd_ack;
            read_data_sck <= read_data_sck;
        end
    end
end

endmodule
