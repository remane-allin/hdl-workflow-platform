// -----------------------------------------------------------------------------
// Module: unified_retire
// Description: Single ordered retire owner for aligned eight-word feature
//              writes, serialized scalar tails, and backpressured result words.
// Scope: Profile-independent commit boundary shared by every execution action.
// Spec Trace: REQ-RRB-010, REQ-RRB-012, REQ-RRB-019, REQ-RRB-020,
//             REQ-RRB-023
// -----------------------------------------------------------------------------

`default_nettype none

module unified_retire (
    input  wire         clk,
    input  wire         reset_n,
    input  wire         retire_valid,
    output wire         retire_ready,
    input  wire [1:0]   retire_state,
    input  wire         packet_last,
    input  wire [12:0]  packet_destination_base,
    input  wire [3:0]   packet_word_count,
    input  wire [7:0]   packet_lane_mask,
    input  wire [127:0] packet_data,
    output wire         retire_ack,

    output reg  [3:0]   bank_a_write_valid,
    output reg  [51:0]  bank_a_write_address,
    output reg  [63:0]  bank_a_write_data,
    output reg  [3:0]   bank_b_write_valid,
    output reg  [51:0]  bank_b_write_address,
    output reg  [63:0]  bank_b_write_data,

    output reg          result_valid,
    input  wire         result_ready,
    output reg  [15:0]  result_data,
    output reg          result_last,
    output wire         result_packet_done
);
    localparam [1:0] STATE_IDLE   = 2'd0;
    localparam [1:0] STATE_TAIL   = 2'd1;
    localparam [1:0] STATE_RESULT = 2'd2;
    localparam [1:0] STATE_COMMIT = 2'd3;

    reg [1:0] state_q;
    reg [3:0] word_index_q;
    reg ack_q;

    reg [12:0] tail_address;
    reg [15:0] selected_word;

    wire packet_accept = retire_valid && retire_ready;

    assign retire_ready = (state_q == STATE_IDLE) ||
        (state_q == STATE_COMMIT);
    assign retire_ack = ack_q;
    assign result_packet_done = (state_q == STATE_RESULT) &&
        result_ready &&
        ((word_index_q + 4'd1) >= packet_word_count);

    // The execution engine owns the one physical retire transaction slot.
    // This module owns only the ordered drain state and index, so no second
    // 128-bit packet register or cross-module payload mux is synthesized.
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            state_q <= STATE_IDLE;
            word_index_q <= 4'd0;
            ack_q <= 1'b0;
        end
        else begin
            ack_q <= 1'b0;

            if (packet_accept) begin
                word_index_q <= 4'd0;
            end

            case (state_q)
                STATE_IDLE: begin
                    if (packet_accept)
                        state_q <= retire_state;
                end

                STATE_COMMIT: begin
                    // The registered packet is committed during this cycle.
                    // A new packet may be chained into the same slot at the
                    // edge, while ack_q still identifies the old packet.
                    ack_q <= 1'b1;
                    if (packet_accept)
                        state_q <= retire_state;
                    else
                        state_q <= STATE_IDLE;
                end

                STATE_TAIL: begin
                    if ((word_index_q + 4'd1) >= packet_word_count) begin
                        ack_q <= 1'b1;
                        state_q <= STATE_IDLE;
                    end
                    else begin
                        word_index_q <= word_index_q + 4'd1;
                    end
                end

                STATE_RESULT: begin
                    if (result_ready) begin
                        if ((word_index_q + 4'd1) >= packet_word_count) begin
                            ack_q <= 1'b1;
                            state_q <= STATE_IDLE;
                        end
                        else begin
                            word_index_q <= word_index_q + 4'd1;
                        end
                    end
                end

                default: state_q <= STATE_IDLE;
            endcase
        end
    end

    always @(*) begin
        case (word_index_q[2:0])
            3'd0: selected_word = packet_data[15:0];
            3'd1: selected_word = packet_data[31:16];
            3'd2: selected_word = packet_data[47:32];
            3'd3: selected_word = packet_data[63:48];
            3'd4: selected_word = packet_data[79:64];
            3'd5: selected_word = packet_data[95:80];
            3'd6: selected_word = packet_data[111:96];
            default: selected_word = packet_data[127:112];
        endcase
    end

    // Full commits are guaranteed aligned by the accepted command.  Expanding
    // the fixed low address bits avoids eight replicated 13-bit adders.
    always @(*) begin
        bank_a_write_valid = 4'd0;
        bank_a_write_address = 52'd0;
        bank_a_write_data = 64'd0;
        bank_b_write_valid = 4'd0;
        bank_b_write_address = 52'd0;
        bank_b_write_data = 64'd0;
        result_valid = 1'b0;
        result_data = 16'd0;
        result_last = 1'b0;
        tail_address = packet_destination_base + {9'd0, word_index_q};

        if ((state_q == STATE_COMMIT) &&
            (packet_word_count == 4'd8)) begin
            bank_a_write_valid = packet_lane_mask[3:0];
            bank_a_write_address[12:0] =
                {packet_destination_base[12:3], 3'd0};
            bank_a_write_address[25:13] =
                {packet_destination_base[12:3], 3'd1};
            bank_a_write_address[38:26] =
                {packet_destination_base[12:3], 3'd2};
            bank_a_write_address[51:39] =
                {packet_destination_base[12:3], 3'd3};
            bank_a_write_data = packet_data[63:0];
            bank_b_write_valid = packet_lane_mask[7:4];
            bank_b_write_address[12:0] =
                {packet_destination_base[12:3], 3'd4};
            bank_b_write_address[25:13] =
                {packet_destination_base[12:3], 3'd5};
            bank_b_write_address[38:26] =
                {packet_destination_base[12:3], 3'd6};
            bank_b_write_address[51:39] =
                {packet_destination_base[12:3], 3'd7};
            bank_b_write_data = packet_data[127:64];
        end
        else if ((state_q == STATE_COMMIT) &&
                 (packet_word_count == 4'd1)) begin
            case (packet_destination_base[1:0])
                2'd0: begin
                    bank_b_write_valid[0] = packet_lane_mask[0];
                    bank_b_write_address[12:0] = packet_destination_base;
                    bank_b_write_data[15:0] = packet_data[15:0];
                end
                2'd1: begin
                    bank_b_write_valid[1] = packet_lane_mask[0];
                    bank_b_write_address[25:13] = packet_destination_base;
                    bank_b_write_data[31:16] = packet_data[15:0];
                end
                2'd2: begin
                    bank_b_write_valid[2] = packet_lane_mask[0];
                    bank_b_write_address[38:26] = packet_destination_base;
                    bank_b_write_data[47:32] = packet_data[15:0];
                end
                default: begin
                    bank_b_write_valid[3] = packet_lane_mask[0];
                    bank_b_write_address[51:39] = packet_destination_base;
                    bank_b_write_data[63:48] = packet_data[15:0];
                end
            endcase
        end
        else if (state_q == STATE_TAIL) begin
            case (tail_address[1:0])
                2'd0: begin
                    bank_a_write_valid[0] = packet_lane_mask[word_index_q];
                    bank_a_write_address[12:0] = tail_address;
                    bank_a_write_data[15:0] = selected_word;
                end
                2'd1: begin
                    bank_a_write_valid[1] = packet_lane_mask[word_index_q];
                    bank_a_write_address[25:13] = tail_address;
                    bank_a_write_data[31:16] = selected_word;
                end
                2'd2: begin
                    bank_a_write_valid[2] = packet_lane_mask[word_index_q];
                    bank_a_write_address[38:26] = tail_address;
                    bank_a_write_data[47:32] = selected_word;
                end
                default: begin
                    bank_a_write_valid[3] = packet_lane_mask[word_index_q];
                    bank_a_write_address[51:39] = tail_address;
                    bank_a_write_data[63:48] = selected_word;
                end
            endcase
        end
        else if (state_q == STATE_RESULT) begin
            result_valid = 1'b1;
            result_data = selected_word;
            result_last = packet_last &&
                ((word_index_q + 4'd1) >= packet_word_count);
        end
    end
endmodule
`default_nettype wire
