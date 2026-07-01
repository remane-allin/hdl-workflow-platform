//==============================================================================
// Module      : rx_mailbox_status
// File        : rx_mailbox_status.v
// Project     : Hi3593_v2
// Description : RX priority mailbox storage and receiver flag/interrupt status.
// Scope:
//   - Owns RX priority mailbox data, MB valid pins, RX status bytes, and RFLAG/RINT selection.
//   - Does not own register decode, label memory, RX word assembly, or FIFO storage.
// Spec Trace:
//   - REQ-STATUS-001, REQ-PLABEL-001, REQ-MAILBOX-001, REQ-MB-PINS-001
// Notes:
//   - Opcode read-clear strobes clear mailbox valid bits; mailbox payload is preserved until reset.
//==============================================================================

module rx_mailbox_status (
    input  wire        ACLK,
    input  wire        master_reset,
    input  wire        fifo_reset,
    input  wire [7:0]  flag_interrupt_assignment,
    input  wire        rx1_fifo_empty,
    input  wire        rx1_fifo_half,
    input  wire        rx2_fifo_empty,
    input  wire        rx2_fifo_half,
    input  wire        rx1_word_valid,
    input  wire        rx2_word_valid,
    input  wire [31:0] rx1_word_data,
    input  wire [31:0] rx2_word_data,
    input  wire        rx1_priority_match,
    input  wire        rx2_priority_match,
    input  wire [1:0]  rx1_priority_slot,
    input  wire [1:0]  rx2_priority_slot,
    input  wire        rx1_parity_error,
    input  wire        rx2_parity_error,
    input  wire        rx1_label_reject,
    input  wire        rx2_label_reject,
    input  wire        rx1_mailbox1_clear,
    input  wire        rx1_mailbox2_clear,
    input  wire        rx1_mailbox3_clear,
    input  wire        rx2_mailbox1_clear,
    input  wire        rx2_mailbox2_clear,
    input  wire        rx2_mailbox3_clear,
    output wire [7:0]  rx1_status,
    output wire [7:0]  rx2_status,
    output reg  [23:0] rx1_mailbox1,
    output reg  [23:0] rx1_mailbox2,
    output reg  [23:0] rx1_mailbox3,
    output reg  [23:0] rx2_mailbox1,
    output reg  [23:0] rx2_mailbox2,
    output reg  [23:0] rx2_mailbox3,
    output reg         R1FLAG,
    output reg         R2FLAG,
    output reg         R1INT,
    output reg         R2INT,
    output reg         MB1_1,
    output reg         MB1_2,
    output reg         MB1_3,
    output reg         MB2_1,
    output reg         MB2_2,
    output reg         MB2_3
);

//------------------------------------------------------------------------------
// Internal Signals
//------------------------------------------------------------------------------

wire rx1_mailbox_any;
wire rx2_mailbox_any;

assign rx1_mailbox_any = MB1_1 || MB1_2 || MB1_3;
assign rx2_mailbox_any = MB2_1 || MB2_2 || MB2_3;
assign rx1_status = {2'b00, rx1_mailbox_any, MB1_3, MB1_2, MB1_1, rx1_fifo_half, rx1_fifo_empty};
assign rx2_status = {2'b00, rx2_mailbox_any, MB2_3, MB2_2, MB2_1, rx2_fifo_half, rx2_fifo_empty};

function flag_source;
    input [1:0] select;
    input       fifo_not_empty;
    input       mailbox_any;
    input       word_valid;
    input       error_seen;
    begin
        case (select)
            2'b00: flag_source = fifo_not_empty;
            2'b01: flag_source = mailbox_any;
            2'b10: flag_source = word_valid;
            default: flag_source = error_seen;
        endcase
    end
endfunction

//------------------------------------------------------------------------------
// Mailbox Storage And Status Pins
//------------------------------------------------------------------------------

always @(posedge ACLK) begin
    if (master_reset) begin
        rx1_mailbox1 <= 24'd0;
        rx1_mailbox2 <= 24'd0;
        rx1_mailbox3 <= 24'd0;
        rx2_mailbox1 <= 24'd0;
        rx2_mailbox2 <= 24'd0;
        rx2_mailbox3 <= 24'd0;
        R1FLAG       <= 1'b0;
        R2FLAG       <= 1'b0;
        R1INT        <= 1'b0;
        R2INT        <= 1'b0;
        MB1_1        <= 1'b0;
        MB1_2        <= 1'b0;
        MB1_3        <= 1'b0;
        MB2_1        <= 1'b0;
        MB2_2        <= 1'b0;
        MB2_3        <= 1'b0;
    end
    else if (fifo_reset) begin
        rx1_mailbox1 <= 24'd0;
        rx1_mailbox2 <= 24'd0;
        rx1_mailbox3 <= 24'd0;
        rx2_mailbox1 <= 24'd0;
        rx2_mailbox2 <= 24'd0;
        rx2_mailbox3 <= 24'd0;
        R1FLAG       <= 1'b0;
        R2FLAG       <= 1'b0;
        R1INT        <= 1'b0;
        R2INT        <= 1'b0;
        MB1_1        <= 1'b0;
        MB1_2        <= 1'b0;
        MB1_3        <= 1'b0;
        MB2_1        <= 1'b0;
        MB2_2        <= 1'b0;
        MB2_3        <= 1'b0;
    end
    else begin
        if (rx1_word_valid && rx1_priority_match) begin
            case (rx1_priority_slot)
                2'd0: begin
                    rx1_mailbox1 <= rx1_word_data[31:8];
                    MB1_1        <= 1'b1;
                end
                2'd1: begin
                    rx1_mailbox2 <= rx1_word_data[31:8];
                    MB1_2        <= 1'b1;
                end
                default: begin
                    rx1_mailbox3 <= rx1_word_data[31:8];
                    MB1_3        <= 1'b1;
                end
            endcase
        end
        else begin
            rx1_mailbox1 <= rx1_mailbox1;
            rx1_mailbox2 <= rx1_mailbox2;
            rx1_mailbox3 <= rx1_mailbox3;
        end

        if (rx2_word_valid && rx2_priority_match) begin
            case (rx2_priority_slot)
                2'd0: begin
                    rx2_mailbox1 <= rx2_word_data[31:8];
                    MB2_1        <= 1'b1;
                end
                2'd1: begin
                    rx2_mailbox2 <= rx2_word_data[31:8];
                    MB2_2        <= 1'b1;
                end
                default: begin
                    rx2_mailbox3 <= rx2_word_data[31:8];
                    MB2_3        <= 1'b1;
                end
            endcase
        end
        else begin
            rx2_mailbox1 <= rx2_mailbox1;
            rx2_mailbox2 <= rx2_mailbox2;
            rx2_mailbox3 <= rx2_mailbox3;
        end

        if (rx1_mailbox1_clear) begin
            MB1_1 <= 1'b0;
        end

        if (rx1_mailbox2_clear) begin
            MB1_2 <= 1'b0;
        end

        if (rx1_mailbox3_clear) begin
            MB1_3 <= 1'b0;
        end

        if (rx2_mailbox1_clear) begin
            MB2_1 <= 1'b0;
        end

        if (rx2_mailbox2_clear) begin
            MB2_2 <= 1'b0;
        end

        if (rx2_mailbox3_clear) begin
            MB2_3 <= 1'b0;
        end

        R1FLAG <= flag_source(flag_interrupt_assignment[1:0], !rx1_fifo_empty, rx1_mailbox_any, rx1_word_valid, rx1_parity_error || rx1_label_reject);
        R1INT  <= flag_source(flag_interrupt_assignment[3:2], !rx1_fifo_empty, rx1_mailbox_any, rx1_word_valid, rx1_parity_error || rx1_label_reject);
        R2FLAG <= flag_source(flag_interrupt_assignment[5:4], !rx2_fifo_empty, rx2_mailbox_any, rx2_word_valid, rx2_parity_error || rx2_label_reject);
        R2INT  <= flag_source(flag_interrupt_assignment[7:6], !rx2_fifo_empty, rx2_mailbox_any, rx2_word_valid, rx2_parity_error || rx2_label_reject);
    end
end

endmodule
