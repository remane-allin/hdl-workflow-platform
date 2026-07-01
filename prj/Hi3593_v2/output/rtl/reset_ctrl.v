//==============================================================================
// Module      : reset_ctrl
// File        : reset_ctrl.v
// Project     : Hi3593_v2
// Description : Reset request merger for MR, opcode 0x04, and opcode 0x44.
// Scope:
//   - Owns MR synchronization and reset pulse classification.
//   - Does not own register fields, FIFO storage, or protocol decode.
// Spec Trace:
//   - REQ-RST-001, REQ-RST-002
// Notes:
//   - MR is the only top-level reset pin; opcode 0x04 is internal.
//==============================================================================

module reset_ctrl (
    input  wire ACLK,
    input  wire MR,
    input  wire opcode_04_pulse,
    input  wire opcode_44_pulse,
    output reg  master_reset,
    output reg  fifo_reset
);

//------------------------------------------------------------------------------
// Reset Pulse Ownership
//------------------------------------------------------------------------------

always @(posedge ACLK or posedge MR) begin
    if (MR) begin
        master_reset <= 1'b1;
        fifo_reset   <= 1'b1;
    end
    else begin
        if (opcode_04_pulse) begin
            master_reset <= 1'b1;
        end
        else begin
            master_reset <= 1'b0;
        end

        if (opcode_04_pulse || opcode_44_pulse) begin
            fifo_reset <= 1'b1;
        end
        else begin
            fifo_reset <= 1'b0;
        end
    end
end

endmodule
