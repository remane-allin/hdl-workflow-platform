// -----------------------------------------------------------------------------
// Module: shared_operand_tile_service
// Description: Profile-independent operand transfer engine.
// Scope:
//   - Implements three physical transfer forms only:
//       1. trusted aligned feature tiles through both feature ports;
//       2. contiguous 64-bit parameter/program rows;
//       3. one-word affine streams for every irregular access.
//   - Uses one ordered response buffer and one request owner for all forms.
//   - Trusts request_fast_feature; descriptor scheduling owns its alignment.
//   - Owns no profile branch, legality checker, key remapper, or arithmetic.
// Spec Trace: REQ-RRB-005, REQ-RRB-007, REQ-RRB-010, REQ-RRB-011,
//             REQ-RRB-019, REQ-RRB-022
// -----------------------------------------------------------------------------

`timescale 1ns/1ps
`default_nettype none

module shared_operand_tile_service (
    input  wire         clk,
    input  wire         reset_n,
    input  wire         request_valid,
    output reg          request_ready,
    input  wire [1:0]   request_space,
    input  wire [12:0]  request_base,
    input  wire [9:0]   request_lane_stride,
    input  wire [4:0]   request_lanes,
    input  wire         request_negate,
    input  wire         request_fast_feature,
    input  wire [11:0]  request_repeat_count,
    input  wire [12:0]  request_repeat_stride,
    input  wire         fast_issue_allowed,
    input  wire [8:0]   constant_base_row,

    output reg  [3:0]   feature_read_a_valid,
    output reg  [43:0]  feature_read_a_address,
    output reg  [3:0]   feature_read_b_valid,
    output reg  [43:0]  feature_read_b_address,
    input  wire [3:0]   feature_read_a_response_valid,
    input  wire [63:0]  feature_read_a_response_data,
    input  wire [3:0]   feature_read_b_response_valid,
    input  wire [63:0]  feature_read_b_response_data,

    output reg          parameter_read_valid,
    output reg  [8:0]   parameter_read_address,
    input  wire         parameter_read_response_valid,
    input  wire [63:0]  parameter_read_response_data,
    output reg          program_read_valid,
    output reg  [8:0]   program_read_address,
    input  wire         program_read_response_valid,
    input  wire [63:0]  program_read_response_data,

    output reg          response_valid,
    input  wire         response_ready,
    output reg          response_last,
    output reg          response_half,
    output reg  [127:0] response_data
);
    localparam [1:0] SPACE_FEATURE = 2'd0;
    localparam [1:0] STATE_IDLE = 2'd0;
    localparam [1:0] STATE_FETCH = 2'd1;
    localparam [1:0] STATE_HOLD = 2'd2;
    localparam [1:0] STATE_SCALAR = 2'd3;

    reg [1:0] state_q;
    reg [1:0] state_d;
    reg [1:0] space_q;
    reg [1:0] space_d;
    reg [4:0] service_lanes_q;
    reg [4:0] service_lanes_d;
    reg [4:0] response_lanes_q;
    reg [4:0] response_lanes_d;
    reg broadcast_q;
    reg broadcast_d;
    reg [9:0] lane_stride_q;
    reg [9:0] lane_stride_d;
    reg negate_q;
    reg negate_d;
    reg fast_feature_q;
    reg fast_feature_d;
    reg fast_waiting_q;
    reg fast_waiting_d;
    reg fast_response_upper_q;
    reg fast_response_upper_d;
    reg [8:0] constant_base_row_q;
    reg [8:0] constant_base_row_d;

    reg [4:0] chunk_base_index_q;
    reg [4:0] chunk_base_index_d;
    reg [12:0] chunk_base_address_q;
    reg [12:0] chunk_base_address_d;
    reg [3:0] chunk_mask_q;
    reg [3:0] chunk_mask_d;
    reg [3:0] pending_mask_q;
    reg [3:0] pending_mask_d;
    reg [3:0] returned_mask_q;
    reg [3:0] returned_mask_d;
    reg [63:0] response_chunk0_q;
    reg [63:0] response_chunk0_d;
    reg [63:0] response_chunk1_q;
    reg [63:0] response_chunk1_d;
    reg [63:0] response_chunk2_q;
    reg [63:0] response_chunk2_d;
    reg [63:0] response_chunk3_q;
    reg [63:0] response_chunk3_d;
    reg response_half_q;
    reg response_half_d;

    reg feature_inflight_q;
    reg feature_inflight_d;
    reg [1:0] feature_inflight_slot_q;
    reg [1:0] feature_inflight_slot_d;
    reg [1:0] feature_inflight_bank_q;
    reg [1:0] feature_inflight_bank_d;
    reg row_inflight_q;
    reg row_inflight_d;
    reg [3:0] row_tag_mask_q;
    reg [3:0] row_tag_mask_d;
    reg [7:0] row_tag_word_select_q;
    reg [7:0] row_tag_word_select_d;

    reg [12:0] scalar_repeat_stride_q;
    reg [12:0] scalar_repeat_stride_d;
    reg [11:0] scalar_issue_remaining_q;
    reg [11:0] scalar_issue_remaining_d;
    reg scalar_inflight_q;
    reg scalar_inflight_d;
    reg scalar_inflight_last_q;
    reg scalar_inflight_last_d;
    reg [1:0] scalar_inflight_bank_q;
    reg [1:0] scalar_inflight_bank_d;
    reg scalar_hold_valid_q;
    reg scalar_hold_valid_d;
    reg [15:0] scalar_hold_data_q;
    reg [15:0] scalar_hold_data_d;
    reg scalar_hold_last_q;
    reg scalar_hold_last_d;

    reg feature_issue_event;
    reg [1:0] feature_issue_slot;
    reg [1:0] feature_issue_bank;
    reg row_issue_event;
    reg [3:0] row_issue_mask;
    reg [7:0] row_issue_word_select;
    reg fast_issue_event;
    reg fast_issue_upper;
    reg [1:0] pending_slot_work;
    reg [12:0] slot_address_work;
    reg [1:0] slot_bank_work;
    reg [8:0] row_address_work;
    reg [15:0] feature_return_data;
    reg [15:0] slot_return_data0;
    reg [15:0] slot_return_data1;
    reg [15:0] slot_return_data2;
    reg [15:0] slot_return_data3;
    reg [3:0] return_mask_work;

    wire feature_space;
    wire row_response_valid;
    wire [63:0] row_response_data;
    wire request_is_broadcast;
    wire [4:0] accepted_service_lanes;
    wire [11:0] accepted_repeat_count;
    wire request_is_stream_scalar;
    wire scalar_request_accept;
    wire scalar_stream_issue;
    wire scalar_response_valid;
    wire [15:0] scalar_response_raw;
    wire [15:0] scalar_response_value;
    wire scalar_direct_response_valid;
    wire scalar_output_valid;
    wire [15:0] scalar_output_data;
    wire scalar_output_last;
    wire scalar_output_fire;
    wire fast_response_complete;
    wire [63:0] fast_response_a_value;
    wire [63:0] fast_response_b_value;
    wire [12:0] fast_second_base;
    wire [12:0] request_fast_second_base;
    wire fast_direct_accept;
    wire fast_lower_beat_valid;
    wire feature_response_event;
    wire row_response_event;
    wire hold_terminal_beat;
    wire request_port_available;
    wire request_chain_allowed;
    wire [4:0] next_chunk_base_index;
    wire [12:0] next_chunk_base_address;
    wire [3:0] next_chunk_mask;

    function [3:0] chunk_mask_for;
        input [4:0] lane_count;
        input [4:0] base_index;
        reg [4:0] remaining;
        begin
            remaining = lane_count - base_index;
            if (remaining >= 5'd4) chunk_mask_for = 4'hF;
            else if (remaining == 5'd3) chunk_mask_for = 4'h7;
            else if (remaining == 5'd2) chunk_mask_for = 4'h3;
            else if (remaining == 5'd1) chunk_mask_for = 4'h1;
            else chunk_mask_for = 4'h0;
        end
    endfunction

    function [12:0] affine_slot_address;
        input [12:0] base_address;
        input [9:0] stride_value;
        input [1:0] slot_value;
        reg signed [13:0] base_extended;
        reg signed [13:0] stride_extended;
        reg signed [13:0] result_value;
        begin
            base_extended = {1'b0, base_address};
            stride_extended = {{4{stride_value[9]}}, stride_value};
            case (slot_value)
                2'd0: result_value = base_extended;
                2'd1: result_value = base_extended + stride_extended;
                2'd2: result_value = base_extended +
                    (stride_extended <<< 1);
                default: result_value = base_extended + stride_extended +
                    (stride_extended <<< 1);
            endcase
            affine_slot_address = result_value[12:0];
        end
    endfunction

    function [15:0] select_feature_word;
        input [63:0] bank_data;
        input [1:0] bank_select;
        begin
            case (bank_select)
                2'd0: select_feature_word = bank_data[15:0];
                2'd1: select_feature_word = bank_data[31:16];
                2'd2: select_feature_word = bank_data[47:32];
                default: select_feature_word = bank_data[63:48];
            endcase
        end
    endfunction

    function [15:0] select_row_word;
        input [63:0] row_data;
        input [1:0] word_select;
        begin
            case (word_select)
                2'd0: select_row_word = row_data[15:0];
                2'd1: select_row_word = row_data[31:16];
                2'd2: select_row_word = row_data[47:32];
                default: select_row_word = row_data[63:48];
            endcase
        end
    endfunction

    function [15:0] maybe_negate;
        input [15:0] value;
        input negate_enable;
        begin
            maybe_negate = negate_enable ? value ^ 16'h8000 : value;
        end
    endfunction

    assign feature_space = ~space_q[1];
    assign row_response_valid = space_q[0] ?
        program_read_response_valid : parameter_read_response_valid;
    assign row_response_data = space_q[0] ?
        program_read_response_data : parameter_read_response_data;
    assign request_is_broadcast = request_lane_stride == 10'd0;
    assign accepted_service_lanes = request_is_broadcast ?
        5'd1 : request_lanes;
    assign accepted_repeat_count = request_repeat_count == 12'd0 ?
        12'd1 : request_repeat_count;
    assign request_is_stream_scalar = request_fast_feature &&
        (request_lanes == 5'd1) && !request_space[1];
    assign scalar_request_accept = request_valid && request_ready &&
        request_is_stream_scalar;
    assign scalar_stream_issue = (state_q == STATE_SCALAR) &&
        (scalar_issue_remaining_q != 12'd0) && response_ready &&
        fast_issue_allowed;
    assign scalar_response_valid =
        feature_read_a_response_valid[scalar_inflight_bank_q];
    assign scalar_response_raw = select_feature_word(
        feature_read_a_response_data, scalar_inflight_bank_q);
    assign scalar_response_value = maybe_negate(
        scalar_response_raw, negate_q);
    assign scalar_direct_response_valid = (state_q == STATE_SCALAR) &&
        scalar_inflight_q && scalar_response_valid;
    assign scalar_output_valid = scalar_hold_valid_q ||
        scalar_direct_response_valid;
    assign scalar_output_data = scalar_hold_valid_q ?
        scalar_hold_data_q : scalar_response_value;
    assign scalar_output_last = scalar_hold_valid_q ?
        scalar_hold_last_q : scalar_inflight_last_q;
    assign scalar_output_fire = scalar_output_valid && response_ready;

    assign fast_response_complete = fast_waiting_q &&
        (&feature_read_a_response_valid) &&
        (&feature_read_b_response_valid);
    assign fast_response_a_value = feature_read_a_response_data ^
        (negate_q ? 64'h8000800080008000 : 64'd0);
    assign fast_response_b_value = feature_read_b_response_data ^
        (negate_q ? 64'h8000800080008000 : 64'd0);
    assign fast_second_base = chunk_base_address_q + 13'd4;
    assign request_fast_second_base = request_base + 13'd4;
    assign fast_lower_beat_valid = (state_q == STATE_FETCH) &&
        fast_feature_q && fast_waiting_q && fast_response_upper_q &&
        fast_response_complete;
    assign hold_terminal_beat = (response_lanes_q <= 5'd8) ||
        response_half_q;
    assign request_port_available = !request_valid || request_space[1] ||
        fast_issue_allowed;
    assign request_chain_allowed = !request_is_stream_scalar;
    assign fast_direct_accept = request_valid && request_ready &&
        request_fast_feature && !request_space[1] &&
        (request_lanes != 5'd1) && fast_issue_allowed;
    assign feature_response_event = feature_inflight_q &&
        feature_read_a_response_valid[feature_inflight_bank_q];
    assign row_response_event = row_inflight_q && row_response_valid;
    assign next_chunk_base_index = chunk_base_index_q + 5'd4;
    assign next_chunk_base_address = chunk_base_address_q +
        ({{3{lane_stride_q[9]}}, lane_stride_q} << 5'd2);
    assign next_chunk_mask = chunk_mask_for(
        service_lanes_q, next_chunk_base_index);

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            state_q <= STATE_IDLE;
            space_q <= SPACE_FEATURE;
            service_lanes_q <= 5'd0;
            response_lanes_q <= 5'd0;
            broadcast_q <= 1'b0;
            lane_stride_q <= 10'd0;
            negate_q <= 1'b0;
            fast_feature_q <= 1'b0;
            fast_waiting_q <= 1'b0;
            fast_response_upper_q <= 1'b0;
            constant_base_row_q <= 9'd0;
            chunk_base_index_q <= 5'd0;
            chunk_base_address_q <= 13'd0;
            chunk_mask_q <= 4'd0;
            pending_mask_q <= 4'd0;
            returned_mask_q <= 4'd0;
            response_chunk0_q <= 64'd0;
            response_chunk1_q <= 64'd0;
            response_chunk2_q <= 64'd0;
            response_chunk3_q <= 64'd0;
            response_half_q <= 1'b0;
            feature_inflight_q <= 1'b0;
            feature_inflight_slot_q <= 2'd0;
            feature_inflight_bank_q <= 2'd0;
            row_inflight_q <= 1'b0;
            row_tag_mask_q <= 4'd0;
            row_tag_word_select_q <= 8'd0;
            scalar_repeat_stride_q <= 13'd0;
            scalar_issue_remaining_q <= 12'd0;
            scalar_inflight_q <= 1'b0;
            scalar_inflight_last_q <= 1'b0;
            scalar_inflight_bank_q <= 2'd0;
            scalar_hold_valid_q <= 1'b0;
            scalar_hold_data_q <= 16'd0;
            scalar_hold_last_q <= 1'b0;
        end
        else begin
            state_q <= state_d;
            space_q <= space_d;
            service_lanes_q <= service_lanes_d;
            response_lanes_q <= response_lanes_d;
            broadcast_q <= broadcast_d;
            lane_stride_q <= lane_stride_d;
            negate_q <= negate_d;
            fast_feature_q <= fast_feature_d;
            fast_waiting_q <= fast_waiting_d;
            fast_response_upper_q <= fast_response_upper_d;
            constant_base_row_q <= constant_base_row_d;
            chunk_base_index_q <= chunk_base_index_d;
            chunk_base_address_q <= chunk_base_address_d;
            chunk_mask_q <= chunk_mask_d;
            pending_mask_q <= pending_mask_d;
            returned_mask_q <= returned_mask_d;
            response_chunk0_q <= response_chunk0_d;
            response_chunk1_q <= response_chunk1_d;
            response_chunk2_q <= response_chunk2_d;
            response_chunk3_q <= response_chunk3_d;
            response_half_q <= response_half_d;
            feature_inflight_q <= feature_inflight_d;
            feature_inflight_slot_q <= feature_inflight_slot_d;
            feature_inflight_bank_q <= feature_inflight_bank_d;
            row_inflight_q <= row_inflight_d;
            row_tag_mask_q <= row_tag_mask_d;
            row_tag_word_select_q <= row_tag_word_select_d;
            scalar_repeat_stride_q <= scalar_repeat_stride_d;
            scalar_issue_remaining_q <= scalar_issue_remaining_d;
            scalar_inflight_q <= scalar_inflight_d;
            scalar_inflight_last_q <= scalar_inflight_last_d;
            scalar_inflight_bank_q <= scalar_inflight_bank_d;
            scalar_hold_valid_q <= scalar_hold_valid_d;
            scalar_hold_data_q <= scalar_hold_data_d;
            scalar_hold_last_q <= scalar_hold_last_d;
        end
    end

    always @(*) begin
        state_d = state_q;
        space_d = space_q;
        service_lanes_d = service_lanes_q;
        response_lanes_d = response_lanes_q;
        broadcast_d = broadcast_q;
        lane_stride_d = lane_stride_q;
        negate_d = negate_q;
        fast_feature_d = fast_feature_q;
        fast_waiting_d = fast_waiting_q;
        fast_response_upper_d = fast_response_upper_q;
        constant_base_row_d = constant_base_row_q;
        chunk_base_index_d = chunk_base_index_q;
        chunk_base_address_d = chunk_base_address_q;
        chunk_mask_d = chunk_mask_q;
        pending_mask_d = pending_mask_q;
        returned_mask_d = returned_mask_q;
        response_chunk0_d = response_chunk0_q;
        response_chunk1_d = response_chunk1_q;
        response_chunk2_d = response_chunk2_q;
        response_chunk3_d = response_chunk3_q;
        response_half_d = response_half_q;
        feature_inflight_d = feature_inflight_q;
        feature_inflight_slot_d = feature_inflight_slot_q;
        feature_inflight_bank_d = feature_inflight_bank_q;
        row_inflight_d = row_inflight_q;
        row_tag_mask_d = row_tag_mask_q;
        row_tag_word_select_d = row_tag_word_select_q;
        scalar_repeat_stride_d = scalar_repeat_stride_q;
        scalar_issue_remaining_d = scalar_issue_remaining_q;
        scalar_inflight_d = scalar_inflight_q;
        scalar_inflight_last_d = scalar_inflight_last_q;
        scalar_inflight_bank_d = scalar_inflight_bank_q;
        scalar_hold_valid_d = scalar_hold_valid_q;
        scalar_hold_data_d = scalar_hold_data_q;
        scalar_hold_last_d = scalar_hold_last_q;

        return_mask_work = 4'd0;
        feature_return_data = select_feature_word(
            feature_read_a_response_data, feature_inflight_bank_q);
        slot_return_data0 = maybe_negate(
            select_row_word(row_response_data,
                row_tag_word_select_q[1:0]), negate_q);
        slot_return_data1 = maybe_negate(
            select_row_word(row_response_data,
                row_tag_word_select_q[3:2]), negate_q);
        slot_return_data2 = maybe_negate(
            select_row_word(row_response_data,
                row_tag_word_select_q[5:4]), negate_q);
        slot_return_data3 = maybe_negate(
            select_row_word(row_response_data,
                row_tag_word_select_q[7:6]), negate_q);

        if (fast_response_complete) begin
            if (fast_response_upper_q) begin
                response_chunk2_d = fast_response_a_value;
                response_chunk3_d = fast_response_b_value;
            end
            else begin
                response_chunk0_d = fast_response_a_value;
                response_chunk1_d = fast_response_b_value;
            end
        end
        else if (feature_response_event) begin
            return_mask_work[feature_inflight_slot_q] = 1'b1;
            case (chunk_base_index_q[3:2])
                2'd0: case (feature_inflight_slot_q)
                    2'd0: response_chunk0_d[15:0] =
                        maybe_negate(feature_return_data, negate_q);
                    2'd1: response_chunk0_d[31:16] =
                        maybe_negate(feature_return_data, negate_q);
                    2'd2: response_chunk0_d[47:32] =
                        maybe_negate(feature_return_data, negate_q);
                    default: response_chunk0_d[63:48] =
                        maybe_negate(feature_return_data, negate_q);
                endcase
                2'd1: case (feature_inflight_slot_q)
                    2'd0: response_chunk1_d[15:0] =
                        maybe_negate(feature_return_data, negate_q);
                    2'd1: response_chunk1_d[31:16] =
                        maybe_negate(feature_return_data, negate_q);
                    2'd2: response_chunk1_d[47:32] =
                        maybe_negate(feature_return_data, negate_q);
                    default: response_chunk1_d[63:48] =
                        maybe_negate(feature_return_data, negate_q);
                endcase
                2'd2: case (feature_inflight_slot_q)
                    2'd0: response_chunk2_d[15:0] =
                        maybe_negate(feature_return_data, negate_q);
                    2'd1: response_chunk2_d[31:16] =
                        maybe_negate(feature_return_data, negate_q);
                    2'd2: response_chunk2_d[47:32] =
                        maybe_negate(feature_return_data, negate_q);
                    default: response_chunk2_d[63:48] =
                        maybe_negate(feature_return_data, negate_q);
                endcase
                default: case (feature_inflight_slot_q)
                    2'd0: response_chunk3_d[15:0] =
                        maybe_negate(feature_return_data, negate_q);
                    2'd1: response_chunk3_d[31:16] =
                        maybe_negate(feature_return_data, negate_q);
                    2'd2: response_chunk3_d[47:32] =
                        maybe_negate(feature_return_data, negate_q);
                    default: response_chunk3_d[63:48] =
                        maybe_negate(feature_return_data, negate_q);
                endcase
            endcase
        end
        else if (row_response_event) begin
            return_mask_work = row_tag_mask_q;
            case (chunk_base_index_q[3:2])
                2'd0: begin
                    if (row_tag_mask_q[0]) response_chunk0_d[15:0] =
                        slot_return_data0;
                    if (row_tag_mask_q[1]) response_chunk0_d[31:16] =
                        slot_return_data1;
                    if (row_tag_mask_q[2]) response_chunk0_d[47:32] =
                        slot_return_data2;
                    if (row_tag_mask_q[3]) response_chunk0_d[63:48] =
                        slot_return_data3;
                end
                2'd1: begin
                    if (row_tag_mask_q[0]) response_chunk1_d[15:0] =
                        slot_return_data0;
                    if (row_tag_mask_q[1]) response_chunk1_d[31:16] =
                        slot_return_data1;
                    if (row_tag_mask_q[2]) response_chunk1_d[47:32] =
                        slot_return_data2;
                    if (row_tag_mask_q[3]) response_chunk1_d[63:48] =
                        slot_return_data3;
                end
                2'd2: begin
                    if (row_tag_mask_q[0]) response_chunk2_d[15:0] =
                        slot_return_data0;
                    if (row_tag_mask_q[1]) response_chunk2_d[31:16] =
                        slot_return_data1;
                    if (row_tag_mask_q[2]) response_chunk2_d[47:32] =
                        slot_return_data2;
                    if (row_tag_mask_q[3]) response_chunk2_d[63:48] =
                        slot_return_data3;
                end
                default: begin
                    if (row_tag_mask_q[0]) response_chunk3_d[15:0] =
                        slot_return_data0;
                    if (row_tag_mask_q[1]) response_chunk3_d[31:16] =
                        slot_return_data1;
                    if (row_tag_mask_q[2]) response_chunk3_d[47:32] =
                        slot_return_data2;
                    if (row_tag_mask_q[3]) response_chunk3_d[63:48] =
                        slot_return_data3;
                end
            endcase
        end

        if (broadcast_q && (return_mask_work != 4'd0)) begin
            if (feature_response_event)
                feature_return_data = maybe_negate(
                    feature_return_data, negate_q);
            else
                feature_return_data = slot_return_data0;
            response_chunk0_d = {4{feature_return_data}};
            response_chunk1_d = {4{feature_return_data}};
            response_chunk2_d = {4{feature_return_data}};
            response_chunk3_d = {4{feature_return_data}};
        end

        case (state_q)
            STATE_IDLE: begin
                if (request_valid && request_ready) begin
                    space_d = request_space;
                    service_lanes_d = accepted_service_lanes;
                    response_lanes_d = request_lanes;
                    broadcast_d = request_is_broadcast;
                    lane_stride_d = request_lane_stride;
                    negate_d = request_negate;
                    fast_feature_d = request_fast_feature;
                    fast_waiting_d = fast_direct_accept;
                    fast_response_upper_d = 1'b0;
                    constant_base_row_d = constant_base_row;
                    chunk_base_index_d = fast_direct_accept ? 5'd8 : 5'd0;
                    chunk_base_address_d = fast_direct_accept ?
                        request_base + 13'd8 : request_base;
                    chunk_mask_d = chunk_mask_for(
                        accepted_service_lanes, 5'd0);
                    pending_mask_d = chunk_mask_for(
                        accepted_service_lanes, 5'd0);
                    returned_mask_d = 4'd0;
                    response_chunk0_d = 64'd0;
                    response_chunk1_d = 64'd0;
                    response_chunk2_d = 64'd0;
                    response_chunk3_d = 64'd0;
                    response_half_d = 1'b0;
                    feature_inflight_d = 1'b0;
                    row_inflight_d = 1'b0;
                    scalar_hold_valid_d = 1'b0;
                    if (request_is_stream_scalar) begin
                        scalar_repeat_stride_d = request_repeat_stride;
                        scalar_issue_remaining_d =
                            accepted_repeat_count - 12'd1;
                        scalar_inflight_d = 1'b1;
                        scalar_inflight_last_d =
                            accepted_repeat_count == 12'd1;
                        scalar_inflight_bank_d = request_base[1:0];
                        chunk_base_address_d = request_base +
                            request_repeat_stride;
                        state_d = STATE_SCALAR;
                    end
                    else begin
                        scalar_inflight_d = 1'b0;
                        state_d = STATE_FETCH;
                    end
                end
            end

            STATE_FETCH: begin
                if (fast_feature_q) begin
                    if (fast_response_complete) begin
                        fast_waiting_d = 1'b0;
                        if (fast_response_upper_q ||
                            (chunk_base_index_q >= service_lanes_q)) begin
                            response_half_d = fast_lower_beat_valid &&
                                response_ready;
                            state_d = STATE_HOLD;
                        end
                    end
                    if (fast_issue_event) begin
                        fast_waiting_d = 1'b1;
                        fast_response_upper_d = fast_issue_upper;
                        chunk_base_index_d = chunk_base_index_q + 5'd8;
                        chunk_base_address_d = chunk_base_address_q + 13'd8;
                    end
                end
                else begin
                    if (feature_response_event)
                        feature_inflight_d = 1'b0;
                    if (row_response_event)
                        row_inflight_d = 1'b0;
                    if (feature_issue_event) begin
                        feature_inflight_d = 1'b1;
                        feature_inflight_slot_d = feature_issue_slot;
                        feature_inflight_bank_d = feature_issue_bank;
                        pending_mask_d[feature_issue_slot] = 1'b0;
                    end
                    if (row_issue_event) begin
                        row_inflight_d = 1'b1;
                        row_tag_mask_d = row_issue_mask;
                        row_tag_word_select_d = row_issue_word_select;
                        pending_mask_d = pending_mask_d & ~row_issue_mask;
                    end
                    returned_mask_d = returned_mask_q | return_mask_work;
                    if (((returned_mask_q | return_mask_work) ==
                         chunk_mask_q) && (chunk_mask_q != 4'd0)) begin
                        feature_inflight_d = 1'b0;
                        row_inflight_d = 1'b0;
                        if (next_chunk_base_index >= service_lanes_q) begin
                            response_half_d = 1'b0;
                            state_d = STATE_HOLD;
                        end
                        else begin
                            chunk_base_index_d = next_chunk_base_index;
                            chunk_base_address_d = next_chunk_base_address;
                            chunk_mask_d = next_chunk_mask;
                            pending_mask_d = next_chunk_mask;
                            returned_mask_d = 4'd0;
                        end
                    end
                end
            end

            STATE_HOLD: begin
                if (response_ready) begin
                    if (!hold_terminal_beat) begin
                        response_half_d = 1'b1;
                    end
                    else if (request_valid && request_ready) begin
                        space_d = request_space;
                        service_lanes_d = accepted_service_lanes;
                        response_lanes_d = request_lanes;
                        broadcast_d = request_is_broadcast;
                        lane_stride_d = request_lane_stride;
                        negate_d = request_negate;
                        fast_feature_d = request_fast_feature;
                        fast_waiting_d = fast_direct_accept;
                        fast_response_upper_d = 1'b0;
                        constant_base_row_d = constant_base_row;
                        chunk_base_index_d = fast_direct_accept ?
                            5'd8 : 5'd0;
                        chunk_base_address_d = fast_direct_accept ?
                            request_base + 13'd8 : request_base;
                        chunk_mask_d = chunk_mask_for(
                            accepted_service_lanes, 5'd0);
                        pending_mask_d = chunk_mask_for(
                            accepted_service_lanes, 5'd0);
                        returned_mask_d = 4'd0;
                        response_chunk0_d = 64'd0;
                        response_chunk1_d = 64'd0;
                        response_chunk2_d = 64'd0;
                        response_chunk3_d = 64'd0;
                        response_half_d = 1'b0;
                        feature_inflight_d = 1'b0;
                        row_inflight_d = 1'b0;
                        scalar_hold_valid_d = 1'b0;
                        if (request_is_stream_scalar) begin
                            scalar_repeat_stride_d = request_repeat_stride;
                            scalar_issue_remaining_d =
                                accepted_repeat_count - 12'd1;
                            scalar_inflight_d = 1'b1;
                            scalar_inflight_last_d =
                                accepted_repeat_count == 12'd1;
                            scalar_inflight_bank_d = request_base[1:0];
                            chunk_base_address_d = request_base +
                                request_repeat_stride;
                            state_d = STATE_SCALAR;
                        end
                        else begin
                            scalar_inflight_d = 1'b0;
                            state_d = STATE_FETCH;
                        end
                    end
                    else begin
                        state_d = STATE_IDLE;
                    end
                end
            end

            STATE_SCALAR: begin
                scalar_inflight_d = scalar_stream_issue;
                if (scalar_stream_issue) begin
                    scalar_issue_remaining_d =
                        scalar_issue_remaining_q - 12'd1;
                    scalar_inflight_last_d =
                        scalar_issue_remaining_q == 12'd1;
                    scalar_inflight_bank_d = chunk_base_address_q[1:0];
                    chunk_base_address_d = chunk_base_address_q +
                        scalar_repeat_stride_q;
                end
                if (scalar_direct_response_valid && !response_ready) begin
                    scalar_hold_valid_d = 1'b1;
                    scalar_hold_data_d = scalar_response_value;
                    scalar_hold_last_d = scalar_inflight_last_q;
                end
                else if (scalar_hold_valid_q && response_ready) begin
                    scalar_hold_valid_d = 1'b0;
                end
                if (scalar_output_fire && scalar_output_last) begin
                    scalar_inflight_d = 1'b0;
                    scalar_hold_valid_d = 1'b0;
                    state_d = STATE_IDLE;
                end
            end

            default: state_d = STATE_IDLE;
        endcase
    end

    always @(*) begin
        request_ready = ((state_q == STATE_IDLE) &&
                         request_port_available) ||
            ((state_q == STATE_HOLD) && response_ready &&
             hold_terminal_beat && request_chain_allowed &&
             request_port_available);
        response_valid = (state_q == STATE_HOLD) ||
            fast_lower_beat_valid ||
            ((state_q == STATE_SCALAR) && scalar_output_valid);
        response_last = (state_q == STATE_SCALAR) ?
            scalar_output_last :
            (fast_lower_beat_valid ? 1'b0 : hold_terminal_beat);
        response_half = (state_q == STATE_HOLD) ? response_half_q : 1'b0;
        response_data = (state_q == STATE_SCALAR) ?
            {112'd0, scalar_output_data} :
            ((state_q == STATE_HOLD) && response_half_q ?
             {response_chunk3_q, response_chunk2_q} :
             {response_chunk1_q, response_chunk0_q});

        feature_read_a_valid = 4'd0;
        feature_read_a_address = 44'd0;
        feature_read_b_valid = 4'd0;
        feature_read_b_address = 44'd0;
        parameter_read_valid = 1'b0;
        parameter_read_address = 9'd0;
        program_read_valid = 1'b0;
        program_read_address = 9'd0;
        feature_issue_event = 1'b0;
        feature_issue_slot = 2'd0;
        feature_issue_bank = 2'd0;
        row_issue_event = 1'b0;
        row_issue_mask = 4'd0;
        row_issue_word_select = 8'd0;
        fast_issue_event = 1'b0;
        fast_issue_upper = chunk_base_index_q[3];
        pending_slot_work = 2'd0;
        slot_address_work = 13'd0;
        slot_bank_work = 2'd0;
        row_address_work = 9'd0;

        casez (pending_mask_q)
            4'b???1: pending_slot_work = 2'd0;
            4'b??10: pending_slot_work = 2'd1;
            4'b?100: pending_slot_work = 2'd2;
            default: pending_slot_work = 2'd3;
        endcase

        if (scalar_request_accept) begin
            feature_read_a_valid[request_base[1:0]] = 1'b1;
            feature_read_a_address[
                request_base[1:0]*11 +: 11] = request_base[12:2];
        end
        else if (scalar_stream_issue) begin
            feature_read_a_valid[chunk_base_address_q[1:0]] = 1'b1;
            feature_read_a_address[
                chunk_base_address_q[1:0]*11 +: 11] =
                chunk_base_address_q[12:2];
        end
        else if (fast_direct_accept) begin
            feature_read_a_valid = 4'hF;
            feature_read_a_address = {4{request_base[12:2]}};
            feature_read_b_valid = 4'hF;
            feature_read_b_address =
                {4{request_fast_second_base[12:2]}};
        end
        else if ((state_q == STATE_FETCH) && feature_space &&
                 fast_feature_q &&
                 (chunk_base_index_q < service_lanes_q) &&
                 fast_issue_allowed &&
                 (!fast_waiting_q || fast_response_complete)) begin
            fast_issue_event = 1'b1;
            feature_read_a_valid = 4'hF;
            feature_read_a_address = {4{chunk_base_address_q[12:2]}};
            feature_read_b_valid = 4'hF;
            feature_read_b_address = {4{fast_second_base[12:2]}};
        end
        else if ((state_q == STATE_FETCH) && feature_space &&
                 !fast_feature_q && (pending_mask_q != 4'd0) &&
                 (!feature_inflight_q || feature_response_event) &&
                 fast_issue_allowed) begin
            slot_address_work = affine_slot_address(
                chunk_base_address_q, lane_stride_q, pending_slot_work);
            slot_bank_work = slot_address_work[1:0];
            feature_issue_event = 1'b1;
            feature_issue_slot = pending_slot_work;
            feature_issue_bank = slot_bank_work;
            feature_read_a_valid[slot_bank_work] = 1'b1;
            feature_read_a_address[slot_bank_work*11 +: 11] =
                slot_address_work[12:2];
        end
        else if ((state_q == STATE_FETCH) && !feature_space &&
                 (pending_mask_q != 4'd0) &&
                 (!row_inflight_q || row_response_event)) begin
            slot_address_work = affine_slot_address(
                chunk_base_address_q, lane_stride_q, pending_slot_work);
            row_address_work = slot_address_work[10:2];
            row_issue_event = 1'b1;
            if (lane_stride_q == 10'd1) begin
                case (chunk_base_address_q[1:0])
                    2'd0: row_issue_mask = pending_mask_q;
                    2'd1: row_issue_mask =
                        (pending_slot_work == 2'd0) ?
                        (pending_mask_q & 4'b0111) : pending_mask_q;
                    2'd2: row_issue_mask =
                        (pending_slot_work == 2'd0) ?
                        (pending_mask_q & 4'b0011) : pending_mask_q;
                    default: row_issue_mask =
                        (pending_slot_work == 2'd0) ?
                        (pending_mask_q & 4'b0001) : pending_mask_q;
                endcase
                case (chunk_base_address_q[1:0])
                    2'd0: row_issue_word_select =
                        {2'd3, 2'd2, 2'd1, 2'd0};
                    2'd1: row_issue_word_select =
                        {2'd0, 2'd3, 2'd2, 2'd1};
                    2'd2: row_issue_word_select =
                        {2'd1, 2'd0, 2'd3, 2'd2};
                    default: row_issue_word_select =
                        {2'd2, 2'd1, 2'd0, 2'd3};
                endcase
            end
            else begin
                row_issue_mask[pending_slot_work] = 1'b1;
                case (pending_slot_work)
                    2'd0: row_issue_word_select[1:0] =
                        slot_address_work[1:0];
                    2'd1: row_issue_word_select[3:2] =
                        slot_address_work[1:0];
                    2'd2: row_issue_word_select[5:4] =
                        slot_address_work[1:0];
                    default: row_issue_word_select[7:6] =
                        slot_address_work[1:0];
                endcase
            end
            if (!space_q[0]) begin
                parameter_read_valid = 1'b1;
                parameter_read_address = row_address_work;
            end
            else begin
                program_read_valid = 1'b1;
                program_read_address = constant_base_row_q +
                    row_address_work;
            end
        end
    end
endmodule
`default_nettype wire
