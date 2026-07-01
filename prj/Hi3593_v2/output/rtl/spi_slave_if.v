//==============================================================================
// Module      : spi_slave_if
// File        : spi_slave_if.v
// Project     : Hi3593_v2
// Description : SPI mode 0 byte framing and SCK-domain command request source.
// Scope:
//   - Owns CS/SCK/SI/SO framing, opcode capture, variable byte transfers, and request hold.
//   - Does not own ACLK command CDC, register storage, FIFO storage, or ARINC timing.
// Spec Trace:
//   - REQ-SPI-001, REQ-SPI-002, REQ-INST-001, REQ-LABEL-001
// Notes:
//   - CS is active low; incomplete bytes are discarded on CS inactive.
//   - Read payloads are left-aligned in the 256-bit read_data bus after CDC response acknowledge.
//==============================================================================

module spi_slave_if (
    input  wire         SCK,
    input  wire         MR,
    input  wire         CS,
    input  wire         SI,
    input  wire [255:0] read_data,
    input  wire         spi_cmd_ack,
    output reg          SO,
    output reg          spi_cmd_req,
    output reg  [7:0]   spi_opcode,
    output reg  [255:0] spi_wdata,
    output reg  [5:0]   spi_byte_count,
    output reg          partial_discard
);

//------------------------------------------------------------------------------
// Internal Signals
//------------------------------------------------------------------------------

reg [2:0]   bit_count;
reg [7:0]   shift_in;
reg [255:0] shift_out;
reg [5:0]   expected_write_bytes;
reg [5:0]   expected_read_bytes;
reg         read_phase;
reg         write_phase;
reg         read_load_pending;
reg         read_wait_pending;
reg         cmd_pending;
reg         spi_cmd_ack_q;

wire [7:0] next_byte;
wire       spi_cmd_accepted;

assign next_byte = {shift_in[6:0], SI};
assign spi_cmd_accepted = (spi_cmd_ack != spi_cmd_ack_q);

function [5:0] write_byte_count_for_opcode;
    input [7:0] opcode;
    begin
        case (opcode)
            8'h08: write_byte_count_for_opcode = 6'd1;
            8'h0C: write_byte_count_for_opcode = 6'd4;
            8'h10: write_byte_count_for_opcode = 6'd1;
            8'h14: write_byte_count_for_opcode = 6'd32;
            8'h18: write_byte_count_for_opcode = 6'd3;
            8'h24: write_byte_count_for_opcode = 6'd1;
            8'h28: write_byte_count_for_opcode = 6'd32;
            8'h2C: write_byte_count_for_opcode = 6'd3;
            8'h34: write_byte_count_for_opcode = 6'd1;
            8'h38: write_byte_count_for_opcode = 6'd1;
            default: write_byte_count_for_opcode = 6'd0;
        endcase
    end
endfunction

function [5:0] read_byte_count_for_opcode;
    input [7:0] opcode;
    begin
        case (opcode)
            8'h80: read_byte_count_for_opcode = 6'd1;
            8'h84: read_byte_count_for_opcode = 6'd1;
            8'h90: read_byte_count_for_opcode = 6'd1;
            8'h94: read_byte_count_for_opcode = 6'd1;
            8'h98: read_byte_count_for_opcode = 6'd32;
            8'h9C: read_byte_count_for_opcode = 6'd3;
            8'hA0: read_byte_count_for_opcode = 6'd4;
            8'hA4: read_byte_count_for_opcode = 6'd3;
            8'hA8: read_byte_count_for_opcode = 6'd3;
            8'hAC: read_byte_count_for_opcode = 6'd3;
            8'hB0: read_byte_count_for_opcode = 6'd1;
            8'hB4: read_byte_count_for_opcode = 6'd1;
            8'hB8: read_byte_count_for_opcode = 6'd32;
            8'hBC: read_byte_count_for_opcode = 6'd3;
            8'hC0: read_byte_count_for_opcode = 6'd4;
            8'hC4: read_byte_count_for_opcode = 6'd3;
            8'hC8: read_byte_count_for_opcode = 6'd3;
            8'hCC: read_byte_count_for_opcode = 6'd3;
            8'hD0: read_byte_count_for_opcode = 6'd1;
            8'hD4: read_byte_count_for_opcode = 6'd1;
            default: read_byte_count_for_opcode = 6'd0;
        endcase
    end
endfunction

function opcode_is_read;
    input [7:0] opcode;
    begin
        opcode_is_read = (read_byte_count_for_opcode(opcode) != 6'd0) || (opcode == 8'hFF);
    end
endfunction

//------------------------------------------------------------------------------
// SPI Input Byte Framing
//------------------------------------------------------------------------------

always @(posedge SCK or posedge MR or posedge CS) begin
    if (MR) begin
        spi_cmd_req          <= 1'b0;
        spi_opcode           <= 8'd0;
        spi_wdata            <= 256'd0;
        spi_byte_count       <= 6'd0;
        partial_discard      <= 1'b0;
        bit_count            <= 3'd0;
        shift_in             <= 8'd0;
        expected_write_bytes <= 6'd0;
        expected_read_bytes  <= 6'd0;
        read_phase           <= 1'b0;
        write_phase          <= 1'b0;
        read_load_pending    <= 1'b0;
        read_wait_pending    <= 1'b0;
        cmd_pending          <= 1'b0;
        spi_cmd_ack_q        <= 1'b0;
    end
    else if (CS) begin
        spi_cmd_ack_q        <= spi_cmd_ack;
        if (spi_cmd_accepted) begin
            cmd_pending <= 1'b0;
            if (read_wait_pending) begin
                read_phase        <= (expected_read_bytes != 6'd0);
                read_load_pending <= (expected_read_bytes != 6'd0);
                read_wait_pending <= 1'b0;
            end
            else begin
                read_phase        <= 1'b0;
                read_load_pending <= 1'b0;
                read_wait_pending <= 1'b0;
            end
        end
        else begin
            cmd_pending       <= cmd_pending;
            read_phase        <= 1'b0;
            read_load_pending <= 1'b0;
            read_wait_pending <= read_wait_pending;
        end
        spi_wdata            <= spi_wdata;
        spi_opcode           <= spi_opcode;
        spi_byte_count       <= 6'd0;
        expected_write_bytes <= 6'd0;
        expected_read_bytes  <= expected_read_bytes;
        shift_in             <= 8'd0;
        write_phase          <= 1'b0;
        if (bit_count != 3'd0) begin
            partial_discard <= 1'b1;
        end
        else begin
            partial_discard <= partial_discard;
        end
        bit_count <= 3'd0;
    end
    else begin
        spi_cmd_ack_q <= spi_cmd_ack;
        if (spi_cmd_accepted) begin
            cmd_pending <= 1'b0;
            if (read_wait_pending) begin
                read_phase        <= (expected_read_bytes != 6'd0);
                read_load_pending <= (expected_read_bytes != 6'd0);
                read_wait_pending <= 1'b0;
            end
            else begin
                read_phase        <= read_phase;
                read_load_pending <= read_load_pending;
                read_wait_pending <= read_wait_pending;
            end
        end
        else begin
            cmd_pending       <= cmd_pending;
            read_load_pending <= 1'b0;
            read_wait_pending <= read_wait_pending;
        end
        partial_discard <= partial_discard;
        shift_in        <= next_byte;

        if (bit_count == 3'd7) begin
            bit_count <= 3'd0;
            if (cmd_pending || read_wait_pending) begin
                spi_byte_count <= spi_byte_count;
            end
            else if ((spi_byte_count == 6'd0) && !read_phase && !write_phase) begin
                spi_opcode           <= next_byte;
                spi_wdata            <= 256'd0;
                spi_byte_count       <= 6'd0;
                expected_write_bytes <= write_byte_count_for_opcode(next_byte);
                expected_read_bytes  <= read_byte_count_for_opcode(next_byte);
                if (opcode_is_read(next_byte)) begin
                    read_phase        <= 1'b0;
                    write_phase       <= 1'b0;
                    read_load_pending <= 1'b0;
                    read_wait_pending <= (read_byte_count_for_opcode(next_byte) != 6'd0);
                    if (!cmd_pending) begin
                        spi_cmd_req <= ~spi_cmd_req;
                    end
                    else begin
                        spi_cmd_req <= spi_cmd_req;
                    end
                    cmd_pending      <= 1'b1;
                end
                else if (write_byte_count_for_opcode(next_byte) == 6'd0) begin
                    read_phase        <= 1'b0;
                    write_phase       <= 1'b0;
                    read_load_pending <= 1'b0;
                    read_wait_pending <= 1'b0;
                    if (!cmd_pending) begin
                        spi_cmd_req <= ~spi_cmd_req;
                    end
                    else begin
                        spi_cmd_req <= spi_cmd_req;
                    end
                    cmd_pending      <= 1'b1;
                end
                else begin
                    read_phase        <= 1'b0;
                    write_phase       <= 1'b1;
                    read_load_pending <= 1'b0;
                    read_wait_pending <= 1'b0;
                end
            end
            else if (write_phase) begin
                spi_wdata      <= {spi_wdata[247:0], next_byte};
                spi_byte_count <= spi_byte_count + 6'd1;
                if ((spi_byte_count + 6'd1) == expected_write_bytes) begin
                    write_phase     <= 1'b0;
                    if (!cmd_pending) begin
                        spi_cmd_req <= ~spi_cmd_req;
                    end
                    else begin
                        spi_cmd_req <= spi_cmd_req;
                    end
                    cmd_pending    <= 1'b1;
                end
                else begin
                    write_phase   <= 1'b1;
                end
                read_phase        <= read_phase;
                read_load_pending <= read_load_pending;
            end
            else begin
                spi_byte_count    <= spi_byte_count + 6'd1;
                read_phase        <= ((spi_byte_count + 6'd1) < expected_read_bytes);
                read_load_pending <= 1'b0;
            end
        end
        else begin
            bit_count <= bit_count + 3'd1;
        end
    end
end

//------------------------------------------------------------------------------
// SPI Mode 0 Read Shift-Out
//------------------------------------------------------------------------------

always @(negedge SCK or posedge MR or posedge CS) begin
    if (MR) begin
        SO        <= 1'b0;
        shift_out <= 256'd0;
    end
    else if (CS) begin
        SO        <= 1'b0;
        shift_out <= 256'd0;
    end
    else if (read_load_pending) begin
        SO        <= read_data[255];
        shift_out <= {read_data[254:0], 1'b0};
    end
    else if (read_phase) begin
        SO        <= shift_out[255];
        shift_out <= {shift_out[254:0], 1'b0};
    end
    else begin
        SO        <= 1'b0;
        shift_out <= shift_out;
    end
end

endmodule
