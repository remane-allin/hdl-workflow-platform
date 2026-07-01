//==============================================================================
// Module      : arinc429_rx
// File        : arinc429_rx.v
// Project     : Hi3593_v2
// Description : ARINC 429 decoded receiver logic sampler and word assembler.
// Scope:
//   - Owns OUTA/OUTB sampling, 32-bit word assembly, label filtering, and accepted-word pulse.
//   - Does not own RX FIFO storage or register-file storage.
// Spec Trace:
//   - REQ-RX-001, REQ-ARINC-001
// Notes:
//   - OUTA/OUTB are decoded logic from an external HI-8450-class receiver.
//==============================================================================

module arinc429_rx (
    input  wire        ACLK,
    input  wire        reset,
    input  wire        OUTA,
    input  wire        OUTB,
    input  wire [7:0]  rx_control,
    input  wire [255:0] label_memory,
    input  wire [23:0] priority_labels,
    output reg         rx_word_valid,
    output reg  [31:0] rx_word_data,
    output reg         priority_match,
    output reg  [1:0]  priority_slot,
    output reg         parity_error,
    output reg         label_reject
);

//------------------------------------------------------------------------------
// FSM And Datapath Signals
//------------------------------------------------------------------------------

localparam [1:0] ST_WAIT_ACTIVITY = 2'd0;
localparam [1:0] ST_SAMPLE        = 2'd1;
localparam [1:0] ST_DONE          = 2'd2;

reg [1:0]  state_cur;
reg [1:0]  state_nxt;
reg [31:0] shift_word;
reg [5:0]  bit_count;

wire non_null;
wire sample_bit;
wire parity_enable;
wire label_filter_enable;
wire priority_filter_enable;
wire parity_ok;
wire label_allowed;
wire [7:0] assembled_label;
wire priority_match_next;
wire [1:0] priority_slot_next;

assign non_null            = OUTA ^ OUTB;
assign sample_bit          = OUTA && !OUTB;
assign parity_enable       = rx_control[3];
assign label_filter_enable = rx_control[2];
assign priority_filter_enable = rx_control[1];
assign parity_ok           = ~(^shift_word);
assign assembled_label     = shift_word[7:0];
assign label_allowed       = !label_filter_enable || label_memory[assembled_label];
assign priority_match_next = priority_filter_enable && label_allowed &&
                             ((assembled_label == priority_labels[7:0]) ||
                              (assembled_label == priority_labels[15:8]) ||
                              (assembled_label == priority_labels[23:16]));
assign priority_slot_next  = (assembled_label == priority_labels[7:0])  ? 2'd0 :
                             (assembled_label == priority_labels[15:8]) ? 2'd1 :
                             (assembled_label == priority_labels[23:16]) ? 2'd2 :
                             2'd0;

//------------------------------------------------------------------------------
// State Register
//------------------------------------------------------------------------------

always @(posedge ACLK) begin
    if (reset) begin
        state_cur <= ST_WAIT_ACTIVITY;
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
        ST_WAIT_ACTIVITY: begin
            if (non_null) begin
                state_nxt = ST_SAMPLE;
            end
            else begin
                state_nxt = ST_WAIT_ACTIVITY;
            end
        end
        ST_SAMPLE: begin
            if (bit_count == 6'd31 && non_null) begin
                state_nxt = ST_DONE;
            end
            else begin
                state_nxt = ST_SAMPLE;
            end
        end
        ST_DONE: begin
            state_nxt = ST_WAIT_ACTIVITY;
        end
        default: begin
            state_nxt = ST_WAIT_ACTIVITY;
        end
    endcase
end

//------------------------------------------------------------------------------
// Word Assembly And Filtering
//------------------------------------------------------------------------------

always @(posedge ACLK) begin
    if (reset) begin
        shift_word     <= 32'd0;
        bit_count      <= 6'd0;
        rx_word_valid  <= 1'b0;
        rx_word_data   <= 32'd0;
        priority_match <= 1'b0;
        priority_slot  <= 2'd0;
        parity_error   <= 1'b0;
        label_reject   <= 1'b0;
    end
    else begin
        rx_word_valid <= 1'b0;

        case (state_cur)
            ST_WAIT_ACTIVITY: begin
                bit_count      <= 6'd0;
                priority_match <= 1'b0;
                priority_slot  <= 2'd0;
                parity_error   <= 1'b0;
                label_reject   <= 1'b0;
                if (non_null) begin
                    shift_word[0] <= sample_bit;
                    bit_count     <= 6'd1;
                end
                else begin
                    shift_word <= shift_word;
                    bit_count  <= bit_count;
                end
            end
            ST_SAMPLE: begin
                if (non_null) begin
                    shift_word[bit_count[4:0]] <= sample_bit;
                    if (bit_count == 6'd31) begin
                        bit_count <= bit_count;
                    end
                    else begin
                        bit_count <= bit_count + 6'd1;
                    end
                end
                else begin
                    shift_word <= shift_word;
                    bit_count  <= bit_count;
                end
            end
            ST_DONE: begin
                parity_error   <= parity_enable && !parity_ok;
                label_reject   <= !label_allowed;
                priority_match <= priority_match_next;
                priority_slot  <= priority_slot_next;
                if ((!parity_enable || parity_ok) && label_allowed) begin
                    rx_word_valid <= 1'b1;
                    rx_word_data  <= shift_word;
                end
                else begin
                    rx_word_valid <= 1'b0;
                    rx_word_data  <= rx_word_data;
                end
                bit_count <= 6'd0;
            end
            default: begin
                shift_word     <= 32'd0;
                bit_count      <= 6'd0;
                rx_word_valid  <= 1'b0;
                priority_match <= 1'b0;
                priority_slot  <= 2'd0;
                parity_error   <= 1'b0;
                label_reject   <= 1'b0;
            end
        endcase
    end
end

endmodule
