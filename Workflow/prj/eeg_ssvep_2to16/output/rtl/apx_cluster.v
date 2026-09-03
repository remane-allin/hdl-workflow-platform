//==============================================================================
// Module      : apx_cluster
// File        : apx_cluster.v
// Project     : eeg_ssvep_2to16
// Description : Shared APX multiply, vector-multiply, add, and reduction pipe.
// Scope:
//   - Owns one bounded APX arithmetic pipeline and its fixed-latency taps.
//   - Does not decode descriptors, generate addresses, retire data, or branch
//     on EEG, SSVEP, or any future signal profile.
// Spec Trace:
//   - REQ-RRB-006, REQ-RRB-011, REQ-RRB-012
//   - MOD-APX, IF-APX, DF-APX-SHARED, LAT-APX
// Notes:
//   - Multiply taps return at 4/7/10/13/16 cycles.
//   - Multiply, reduce, and program-issued vector adds consume the same A/B
//     operand packet; vector adds share the eight pair adders.  A 16-lane add
//     is issued as lower/upper halves and returned as one ordered packet.
//   - The parallel-add interface shares the pair adders with program-issued
//     vector adds; command acceptance keeps the two paths mutually exclusive.
//   - Vector-multiply returns product_bus without occupying the reduction tree.
//   - Reduction taps return at 3/6/9/12 cycles.
//   - Adjacent-pairwise ordering is preserved for every lane count 1..16.
//==============================================================================
`timescale 1ns/1ps
`default_nettype none

module apx_cluster (
    input  wire         clk,
    input  wire         reset_n,
    input  wire         request_valid,
    output wire         request_ready,
    output wire         busy,
    input  wire [1:0]   request_operation,
    input  wire         request_add_vector,
    input  wire [4:0]   request_lanes,
    input  wire [15:0]  request_tag,
    input  wire [127:0] operand_a_low_beat,
    input  wire [127:0] operand_a_high_beat,
    input  wire [127:0] operand_b_low_beat,
    input  wire [127:0] operand_b_high_beat,
    input  wire [127:0] narrow_operand_a_low_beat,
    input  wire [63:0]  narrow_operand_a_high_beat,
    input  wire [127:0] narrow_operand_b_low_beat,
    input  wire [63:0]  narrow_operand_b_high_beat,
    input  wire [7:0]   request_operand_a_select,
    input  wire [7:0]   request_operand_b_select,
    input  wire [3:0]   request_operand_a_negate,
    input  wire [3:0]   request_operand_b_negate,
    input  wire [3:0]   request_operand_b_scalar,
    input  wire [15:0]  request_operand_b_scalar_value,
    input  wire         request_window_operand,
    input  wire         request_window_shift,
    input  wire [15:0]  request_window_sample,
    input  wire         window_resident_clear_valid,
    input  wire         window_resident_seed_valid,
    input  wire [4:0]   window_resident_seed_lanes,
    input  wire [15:0]  window_resident_seed_data,
    input  wire         parallel_add_valid,
    output wire         parallel_add_ready,
    input  wire [4:0]   parallel_add_lanes,
    input  wire [15:0]  parallel_add_tag,
    input  wire         parallel_prefetch_valid,
    input  wire         parallel_operand_a_pair,
    input  wire [127:0] parallel_prefetch_b_low_beat,
    input  wire [63:0]  parallel_prefetch_b_high_beat,
    input  wire         post_add_valid,
    output wire         post_add_ready,
    input  wire [15:0]  post_add_operand_x,
    input  wire [15:0]  post_add_operand_y,
    input  wire [15:0]  post_add_tag,
    output wire         post_add_result_valid,
    output wire [15:0]  post_add_result_tag,
    output wire [15:0]  post_add_result,
    output wire         post_add_pre_valid,
    output wire [15:0]  post_add_pre_tag,
    output wire         product_valid,
    output wire         product_pre_valid,
    output wire [15:0]  product_tag,
    output wire [15:0]  product_pre_tag,
    output wire [127:0] product_slot_low_beat,
    output wire [127:0] product_slot_high_beat,
    output wire         pair_valid,
    output wire         pair_pre_valid,
    output wire [15:0]  pair_tag,
    output wire [15:0]  pair_pre_tag,
    output wire [127:0] pair_slot_low_beat,
    output wire [127:0] pair_slot_high_beat,
    output wire         reduce_valid,
    output wire         reduce_pre_valid,
    output wire [15:0]  reduce_tag,
    output wire [15:0]  reduce_pre_tag,
    output wire [15:0]  reduce_result
);
    localparam [1:0] OP_MULTIPLY_REDUCE = 2'd0;
    localparam [1:0] OP_ADD_VECTOR = 2'd1;
    localparam [1:0] OP_REDUCE_VECTOR = 2'd2;
    localparam [1:0] OP_MULTIPLY_VECTOR = 2'd3;
    localparam [1:0] OPERAND_EXTERNAL = 2'd0;
    localparam [1:0] OPERAND_PRODUCT = 2'd1;
    localparam [1:0] OPERAND_PAIR = 2'd2;
    localparam [1:0] OPERAND_NARROW = 2'd3;

    // Module boundaries carry registered 128-bit beats.  The arithmetic
    // cluster reconstructs its 16-lane tile only inside this hierarchy; the
    // 256-bit product/pair nets never appear as external ports.
    wire [255:0] operand_a_bus = {
        operand_a_high_beat, operand_a_low_beat
    };
    wire [255:0] operand_b_bus = {
        operand_b_high_beat, operand_b_low_beat
    };
    wire [255:0] narrow_operand_a_bus = {
        64'd0, narrow_operand_a_high_beat, narrow_operand_a_low_beat
    };
    wire [255:0] narrow_operand_b_bus = {
        64'd0, narrow_operand_b_high_beat, narrow_operand_b_low_beat
    };
    wire [191:0] parallel_prefetch_operand_b_bus = {
        parallel_prefetch_b_high_beat, parallel_prefetch_b_low_beat
    };
    wire [255:0] product_bus;
    wire [255:0] pair_bus;

    assign product_slot_low_beat = product_bus[127:0];
    assign product_slot_high_beat = product_bus[255:128];
    assign pair_slot_low_beat = pair_bus[127:0];
    assign pair_slot_high_beat = pair_bus[255:128];

    wire issue_fire;
    wire request_accept;
    wire direct_issue_ready;
    wire multiply_issue;
    wire direct_issue;
    wire direct_add_issue;
    wire wide_add_first_issue;
    wire wide_add_second_issue;
    wire parallel_add_issue;
    wire add_tree_issue_ready;
    wire direct_reduce_issue;
    wire direct_request;
    wire direct_pending_issue;
    wire direct_live_issue;
    wire direct_command_issue;
    wire direct_command_add_vector;
    wire [4:0] direct_command_lanes;
    wire [15:0] direct_command_tag;
    wire [255:0] direct_command_operand_a;
    wire [255:0] direct_command_operand_b;
    wire product_reduce_valid;
    wire [15:0] request_mask;
    wire [15:0] direct_request_mask;
    wire [15:0] multiplier_valid;
    wire [7:0] pair_adder_valid;
    wire [3:0] quad_adder_valid;
    wire [1:0] oct_adder_valid;
    wire pair_input_valid;
    wire [15:0] pair_input_tag;
    wire [7:0] pair_input_mask;
    wire [127:0] pair_operand_x_bus;
    wire [127:0] pair_operand_y_bus;
    wire [127:0] pair_sum_bus;
    wire [7:0] pair_use_operand_y;
    wire [127:0] selected_direct_add_operand_a;
    wire [127:0] selected_direct_add_operand_b;
    wire [255:0] selected_request_operand_a;
    wire [255:0] selected_request_operand_b;
    reg direct_pending_valid_q;
    reg direct_pending_add_vector_q;
    reg [4:0] direct_pending_lanes_q;
    reg [15:0] direct_pending_tag_q;
    reg [255:0] direct_pending_operand_a_q;
    reg [255:0] direct_pending_operand_b_q;
    reg [255:0] window_resident_q;
    wire [255:0] shifted_window_resident;
    wire window_request_accept;
    wire [191:0] selected_parallel_operand_a_bus;
    reg [191:0] parallel_prefetch_operand_b_q;
    reg [191:0] parallel_operand_a_q;
    reg [191:0] parallel_operand_b_q;
    reg parallel_issue_q;
    reg [4:0] parallel_lanes_q;
    reg [15:0] parallel_tag_q;
    wire [7:0] selected_direct_add_mask;
    wire [15:0] selected_direct_add_tag;
    reg wide_add_pending_q;
    reg [127:0] wide_add_operand_a_q;
    reg [127:0] wide_add_operand_b_q;
    reg [4:0] wide_add_lanes_q;
    reg [15:0] wide_add_tag_q;
    reg [2:0] wide_add_lower_pipe_q;
    reg [2:0] wide_add_upper_pipe_q;
    reg [127:0] wide_add_lower_result_q;
    wire pair_raw_valid;
    wire wide_add_lower_return;
    wire wide_add_upper_return;
    wire quad_valid;
    wire oct_valid;
    wire pair_reduce_valid;
    wire quad_reduce_valid;
    wire oct_reduce_valid;
    wire reduce_adder_raw_valid;
    wire [63:0] quad_bus;
    wire [31:0] oct_bus;
    wire [15:0] reduce_adder_sum;
    wire [15:0] direct_lane15_sum;
    wire direct_lane15_valid;
    wire post_add_issue;
    reg post_add_valid_q;
    reg [15:0] post_add_operand_x_q;
    reg [15:0] post_add_operand_y_q;
    reg [15:0] post_add_input_tag_q;
    reg [2:0] post_add_pipe_q;
    reg [15:0] post_add_tag_d0_q;
    reg [15:0] post_add_tag_d1_q;
    reg [15:0] post_add_tag_d2_q;
    reg [15:0] product_mask_d0_q;
    reg [15:0] product_mask_d1_q;
    reg [15:0] product_mask_d2_q;
    reg [15:0] product_mask_d3_q;
    (* shreg_extract = "yes" *) reg [3:0] product_reduce_pipe_q;
    reg [7:0] pair_mask_d0_q;
    reg [7:0] pair_mask_d1_q;
    reg [7:0] pair_mask_d2_q;
    reg [3:0] quad_mask_d0_q;
    reg [3:0] quad_mask_d1_q;
    reg [3:0] quad_mask_d2_q;
    reg [1:0] oct_mask_d0_q;
    reg [1:0] oct_mask_d1_q;
    reg [1:0] oct_mask_d2_q;
    reg [15:0] tag_d0_q;
    reg [15:0] tag_d1_q;
    reg [15:0] tag_d2_q;
    reg [15:0] tag_d3_q;
    reg [15:0] pair_tag_d0_q;
    reg [15:0] pair_tag_d1_q;
    reg [15:0] pair_tag_d2_q;
    reg [15:0] quad_tag_d0_q;
    reg [15:0] quad_tag_d1_q;
    reg [15:0] quad_tag_d2_q;
    reg [15:0] oct_tag_d0_q;
    reg [15:0] oct_tag_d1_q;
    reg [15:0] oct_tag_d2_q;
    reg [15:0] reduce_tag_d0_q;
    reg [15:0] reduce_tag_d1_q;
    reg [15:0] reduce_tag_d2_q;
    (* shreg_extract = "yes" *) reg [2:0] pair_reduce_pipe_q;
    (* shreg_extract = "yes" *) reg [3:0] product_vector_pipe_q;
    (* shreg_extract = "yes" *) reg [2:0] pair_vector_pipe_q;
    reg quad_reduce_d0_q;
    reg quad_reduce_d1_q;
    reg quad_reduce_d2_q;
    reg oct_reduce_d0_q;
    reg oct_reduce_d1_q;
    reg oct_reduce_d2_q;
    reg final_reduce_d0_q;
    reg final_reduce_d1_q;
    reg final_reduce_d2_q;
    genvar lane;
    genvar source_group;

    function [255:0] shift_window_resident;
        input [255:0] current_window;
        input [15:0] new_sample;
        input [4:0] lane_count;
        reg [255:0] shifted;
        begin
            shifted = current_window >> 5'd16;
            case (lane_count)
                5'd1: shifted[15:0] = new_sample;
                5'd2: shifted[31:16] = new_sample;
                5'd3: shifted[47:32] = new_sample;
                5'd4: shifted[63:48] = new_sample;
                5'd5: shifted[79:64] = new_sample;
                5'd6: shifted[95:80] = new_sample;
                5'd7: shifted[111:96] = new_sample;
                5'd8: shifted[127:112] = new_sample;
                5'd9: shifted[143:128] = new_sample;
                5'd10: shifted[159:144] = new_sample;
                5'd11: shifted[175:160] = new_sample;
                5'd12: shifted[191:176] = new_sample;
                5'd13: shifted[207:192] = new_sample;
                5'd14: shifted[223:208] = new_sample;
                5'd15: shifted[239:224] = new_sample;
                default: shifted[255:240] = new_sample;
            endcase
            shift_window_resident = shifted;
        end
    endfunction

    assign shifted_window_resident = shift_window_resident(
        window_resident_q, request_window_sample, request_lanes);
    assign window_request_accept = request_accept &&
        request_window_operand;

    // Four 64-bit source quadrants preserve the existing issue cycle while
    // preventing one descriptor control bit from spanning all sixteen FP16
    // lanes.  The descriptor boundary supplies independently registered
    // copies, and each copy terminates inside its four-lane quadrant.
    generate
        for (source_group = 0; source_group < 4;
             source_group = source_group + 1) begin : gen_source_select
            reg [63:0] selected_operand_a;
            reg [63:0] selected_operand_b;

            always @(*) begin
                if (request_window_operand)
                    selected_operand_a = request_window_shift ?
                        shifted_window_resident[
                            source_group*64 +: 64] :
                        window_resident_q[source_group*64 +: 64];
                else begin
                    case (request_operand_a_select[
                          source_group*2 +: 2])
                        OPERAND_PRODUCT:
                            selected_operand_a = product_bus[
                                source_group*64 +: 64];
                        OPERAND_PAIR:
                            selected_operand_a = pair_bus[
                                source_group*64 +: 64];
                        OPERAND_NARROW:
                            selected_operand_a = narrow_operand_a_bus[
                                source_group*64 +: 64];
                        default:
                            selected_operand_a = operand_a_bus[
                                source_group*64 +: 64];
                    endcase
                end
                if (request_operand_a_negate[source_group])
                    selected_operand_a = selected_operand_a ^
                        {4{16'h8000}};
            end

            always @(*) begin
                case (request_operand_b_select[
                      source_group*2 +: 2])
                    OPERAND_PRODUCT:
                        selected_operand_b = product_bus[
                            source_group*64 +: 64];
                    OPERAND_PAIR:
                        selected_operand_b = pair_bus[
                            source_group*64 +: 64];
                    OPERAND_NARROW:
                        selected_operand_b =
                            request_operand_b_scalar[source_group] ?
                            {4{request_operand_b_scalar_value}} :
                            narrow_operand_b_bus[
                                source_group*64 +: 64];
                    default:
                        selected_operand_b = operand_b_bus[
                            source_group*64 +: 64];
                endcase
                if (request_operand_b_negate[source_group])
                    selected_operand_b = selected_operand_b ^
                        {4{16'h8000}};
            end

            assign selected_request_operand_a[
                source_group*64 +: 64] = selected_operand_a;
            assign selected_request_operand_b[
                source_group*64 +: 64] = selected_operand_b;
        end
    endgenerate

    // The rolling window is one APX-local resident.  Queued descriptors retain
    // metadata only and reload this resident before their first issue, so a
    // second 256-bit bank and its global slot-select network are unnecessary.
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n)
            window_resident_q <= 256'd0;
        else begin
            if (window_resident_clear_valid)
                window_resident_q <= 256'd0;
            if (window_resident_seed_valid)
                window_resident_q <= shift_window_resident(
                    window_resident_q,
                    window_resident_seed_data,
                    window_resident_seed_lanes);
            if (window_request_accept && request_window_shift)
                window_resident_q <= shifted_window_resident;
        end
    end

    assign selected_parallel_operand_a_bus = parallel_operand_a_pair ?
        pair_bus[191:0] : product_bus[191:0];

    assign direct_request = request_add_vector ||
        (request_operation == OP_REDUCE_VECTOR);
    assign add_tree_issue_ready =
        !(product_reduce_valid || pair_reduce_valid ||
          quad_reduce_valid || oct_reduce_valid);
    assign direct_issue_ready = !wide_add_pending_q &&
        add_tree_issue_ready;
    // Multiply traffic consumes the registered descriptor head directly.
    // Direct add/reduce traffic does the same when the tree is free; only an
    // actual collision occupies the existing APX-local pending operands.
    assign request_ready = !direct_pending_valid_q;
    assign request_accept = request_valid && request_ready;
    assign issue_fire = request_accept;
    // A descriptor boundary may be crossed only when no command or result
    // token remains anywhere in the shared arithmetic overlay.  The two
    // terminal-only marker pipes cover vector multiply/add latency; the
    // existing reduction and post-add markers cover every other path.
    assign busy = wide_add_pending_q || post_add_valid_q ||
        request_valid || direct_pending_valid_q || parallel_issue_q ||
        (|wide_add_lower_pipe_q) || (|wide_add_upper_pipe_q) ||
        (|product_vector_pipe_q) || (|pair_vector_pipe_q) ||
        (|product_reduce_pipe_q) || (|pair_reduce_pipe_q) ||
        (|post_add_pipe_q) ||
        quad_reduce_d0_q || quad_reduce_d1_q || quad_reduce_d2_q ||
        oct_reduce_d0_q || oct_reduce_d1_q || oct_reduce_d2_q ||
        final_reduce_d0_q || final_reduce_d1_q || final_reduce_d2_q ||
        (|multiplier_valid) || (|pair_adder_valid) ||
        (|quad_adder_valid) || (|oct_adder_valid) ||
        reduce_adder_raw_valid || direct_lane15_valid;
    assign multiply_issue = issue_fire && !direct_request &&
        ((request_operation == OP_MULTIPLY_REDUCE) ||
            (request_operation == OP_MULTIPLY_VECTOR));
    assign direct_pending_issue = direct_pending_valid_q &&
        direct_issue_ready;
    assign direct_live_issue = request_accept && direct_request &&
        direct_issue_ready;
    assign direct_command_issue = direct_pending_issue || direct_live_issue;
    assign direct_command_add_vector = direct_pending_valid_q ?
        direct_pending_add_vector_q : request_add_vector;
    assign direct_command_lanes = direct_pending_valid_q ?
        direct_pending_lanes_q : request_lanes;
    assign direct_command_tag = direct_pending_valid_q ?
        direct_pending_tag_q : request_tag;
    assign direct_command_operand_a = direct_pending_valid_q ?
        direct_pending_operand_a_q : selected_request_operand_a;
    assign direct_command_operand_b = direct_pending_valid_q ?
        direct_pending_operand_b_q : selected_request_operand_b;
    assign direct_reduce_issue = direct_command_issue &&
        !direct_command_add_vector;
    assign wide_add_first_issue = direct_command_issue &&
        direct_command_add_vector && direct_request_mask[8];
    assign wide_add_second_issue = wide_add_pending_q;
    assign direct_add_issue =
        (direct_command_issue && direct_command_add_vector) ||
        wide_add_second_issue;
    assign direct_issue = direct_add_issue || direct_reduce_issue;
    // The recurrence overlay captures one bounded twelve-lane operand packet
    // before it reaches the shared reduction adders.  The register boundary
    // removes the global scratch/product/pair combinational cone without
    // duplicating twelve FP16 adders.  The original pair/quad tree still
    // accepts one registered recurrence packet per cycle.
    assign parallel_add_ready = !wide_add_pending_q &&
        add_tree_issue_ready &&
        !direct_pending_valid_q && !(request_valid && direct_request);
    assign parallel_add_issue = parallel_add_valid &&
        parallel_add_ready;
    // One elastic command slot separates scratch/control selection from the
    // FP adder.  It can accept a new scalar command while the previous one is
    // issued, so the steady-state rate remains one command per cycle.
    assign post_add_issue = post_add_valid_q && !direct_add_issue &&
        !parallel_add_issue;
    assign post_add_ready = !post_add_valid_q || post_add_issue;
    assign post_add_result_valid = direct_lane15_valid &&
        post_add_pipe_q[2];
    assign post_add_result_tag = post_add_tag_d2_q;
    assign post_add_result = direct_lane15_sum;
    assign post_add_pre_valid = post_add_pipe_q[1];
    assign post_add_pre_tag = post_add_tag_d1_q;
    assign product_reduce_valid = product_valid &&
        product_reduce_pipe_q[3];
    assign pair_input_valid = product_reduce_valid || direct_issue ||
        parallel_issue_q;
    assign pair_input_tag = product_reduce_valid ? product_tag :
        (wide_add_second_issue ? wide_add_tag_q :
        (parallel_issue_q ? parallel_tag_q :
         selected_direct_add_tag));
    assign selected_direct_add_operand_a = wide_add_second_issue ?
        wide_add_operand_a_q : (parallel_issue_q ?
        parallel_operand_a_q[127:0] :
        direct_command_operand_a[127:0]);
    assign selected_direct_add_operand_b =
        wide_add_second_issue ? wide_add_operand_b_q :
        (parallel_issue_q ? parallel_operand_b_q[127:0] :
         direct_command_operand_b[127:0]);
    assign selected_direct_add_tag = wide_add_second_issue ?
        wide_add_tag_q : direct_command_tag;
    assign product_valid = multiplier_valid[0];
    assign product_pre_valid = product_mask_d2_q[0];
    assign product_pre_tag = tag_d2_q;
    assign pair_raw_valid = pair_adder_valid[0];
    assign wide_add_lower_return = pair_raw_valid &&
        wide_add_lower_pipe_q[2];
    assign wide_add_upper_return = pair_raw_valid &&
        wide_add_upper_pipe_q[2];
    assign pair_valid = pair_raw_valid && !wide_add_lower_return;
    assign pair_pre_valid = pair_mask_d1_q[0];
    assign pair_pre_tag = pair_tag_d1_q;
    assign quad_valid = quad_adder_valid[0];
    assign oct_valid = oct_adder_valid[0];
    assign pair_reduce_valid = pair_valid && pair_reduce_pipe_q[2];
    assign quad_reduce_valid = quad_valid && quad_reduce_d2_q;
    assign oct_reduce_valid = oct_valid && oct_reduce_d2_q;
    assign reduce_valid = reduce_adder_raw_valid && final_reduce_d2_q;
    assign reduce_pre_valid = final_reduce_d1_q;
    assign product_tag = tag_d3_q;
    assign pair_tag = pair_tag_d2_q;
    assign reduce_tag = reduce_tag_d2_q;
    assign reduce_pre_tag = reduce_tag_d1_q;
    assign pair_bus = wide_add_upper_return ?
        {pair_sum_bus, wide_add_lower_result_q} :
        {{direct_lane15_sum, reduce_adder_sum, oct_bus, quad_bus},
         pair_sum_bus};

    generate
        for (lane = 0; lane < 16; lane = lane + 1) begin : gen_command_mask
            assign request_mask[lane] = request_lanes > lane;
            assign direct_request_mask[lane] =
                direct_command_lanes > lane;
        end
        for (lane = 0; lane < 8; lane = lane + 1) begin : gen_direct_add_mask
            assign selected_direct_add_mask[lane] =
                wide_add_second_issue ?
                    (wide_add_lanes_q > (lane + 8)) :
                 (parallel_issue_q ? (parallel_lanes_q > lane) :
                  (direct_command_lanes > lane));
        end
        for (lane = 0; lane < 16; lane = lane + 1) begin : gen_multiply
            apx_fp16_mul_pipe multiplier_inst (
                .clk(clk),
                .reset_n(reset_n),
                .input_valid(multiply_issue),
                .operand_x(selected_request_operand_a[lane*16 +: 16]),
                .operand_y(selected_request_operand_b[lane*16 +: 16]),
                .output_valid(multiplier_valid[lane]),
                .product(product_bus[lane*16 +: 16])
            );
        end
        for (lane = 0; lane < 8; lane = lane + 1) begin : gen_pair_add
            assign pair_operand_x_bus[lane*16 +: 16] = product_reduce_valid ?
                product_bus[(lane*2)*16 +: 16] :
                (direct_add_issue || parallel_issue_q) ?
                    selected_direct_add_operand_a[lane*16 +: 16] :
                    selected_request_operand_a[(lane*2)*16 +: 16];
            assign pair_operand_y_bus[lane*16 +: 16] = product_reduce_valid ?
                product_bus[(lane*2+1)*16 +: 16] :
                (direct_add_issue || parallel_issue_q) ?
                    selected_direct_add_operand_b[lane*16 +: 16] :
                    selected_request_operand_a[(lane*2+1)*16 +: 16];
            assign pair_use_operand_y[lane] = product_reduce_valid ?
                product_mask_d3_q[lane*2+1] :
                (direct_add_issue || parallel_issue_q) ?
                    selected_direct_add_mask[lane] :
                    direct_request_mask[lane*2+1];
            assign pair_input_mask[lane] = product_reduce_valid ?
                (product_mask_d3_q[lane*2] |
                    product_mask_d3_q[lane*2+1]) :
                (direct_add_issue || parallel_issue_q) ?
                    selected_direct_add_mask[lane] :
                    (direct_request_mask[lane*2] |
                     direct_request_mask[lane*2+1]);
            apx_fp16_add_pipe pair_adder_inst (
                .clk(clk),
                .reset_n(reset_n),
                .input_valid(pair_input_valid),
                .use_operand_y(pair_use_operand_y[lane]),
                .operand_x(pair_operand_x_bus[lane*16 +: 16]),
                .operand_y(pair_operand_y_bus[lane*16 +: 16]),
                .output_valid(pair_adder_valid[lane]),
                .sum(pair_sum_bus[lane*16 +: 16])
            );
        end
        for (lane = 0; lane < 4; lane = lane + 1) begin : gen_quad_add
            apx_fp16_add_pipe quad_adder_inst (
                .clk(clk),
                .reset_n(reset_n),
                .input_valid(pair_reduce_valid ||
                    (parallel_issue_q &&
                     (parallel_lanes_q > (lane + 8)))),
                .use_operand_y(parallel_issue_q ? 1'b1 :
                    pair_mask_d2_q[lane*2+1]),
                .operand_x(parallel_issue_q ?
                    parallel_operand_a_q[(lane+8)*16 +: 16] :
                    pair_sum_bus[(lane*2)*16 +: 16]),
                .operand_y(parallel_issue_q ?
                    parallel_operand_b_q[(lane+8)*16 +: 16] :
                    pair_sum_bus[(lane*2+1)*16 +: 16]),
                .output_valid(quad_adder_valid[lane]),
                .sum(quad_bus[lane*16 +: 16])
            );
        end
        for (lane = 0; lane < 2; lane = lane + 1) begin : gen_oct_add
            apx_fp16_add_pipe oct_adder_inst (
                .clk(clk),
                .reset_n(reset_n),
                .input_valid(quad_reduce_valid),
                .use_operand_y(quad_mask_d2_q[lane*2+1]),
                .operand_x(quad_bus[(lane*2)*16 +: 16]),
                .operand_y(quad_bus[(lane*2+1)*16 +: 16]),
                .output_valid(oct_adder_valid[lane]),
                .sum(oct_bus[lane*16 +: 16])
            );
        end
    endgenerate

    apx_fp16_add_pipe reduce_adder_inst (
        .clk(clk),
        .reset_n(reset_n),
        .input_valid(oct_reduce_valid),
        .use_operand_y(oct_mask_d2_q[1]),
        .operand_x(oct_bus[15:0]),
        .operand_y(oct_bus[31:16]),
        .output_valid(reduce_adder_raw_valid),
        .sum(reduce_adder_sum)
    );

    apx_fp16_add_pipe direct_lane15_adder_inst (
        .clk(clk),
        .reset_n(reset_n),
        .input_valid(post_add_issue),
        .use_operand_y(1'b1),
        .operand_x(post_add_operand_x_q),
        .operand_y(post_add_operand_y_q),
        .output_valid(direct_lane15_valid),
        .sum(direct_lane15_sum)
    );

    assign reduce_result = reduce_adder_sum;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            direct_pending_valid_q <= 1'b0;
            product_mask_d0_q <= 16'd0;
            product_mask_d1_q <= 16'd0;
            product_mask_d2_q <= 16'd0;
            product_mask_d3_q <= 16'd0;
            pair_mask_d0_q <= 8'd0;
            pair_mask_d1_q <= 8'd0;
            pair_mask_d2_q <= 8'd0;
            quad_mask_d0_q <= 4'd0;
            quad_mask_d1_q <= 4'd0;
            quad_mask_d2_q <= 4'd0;
            oct_mask_d0_q <= 2'd0;
            oct_mask_d1_q <= 2'd0;
            oct_mask_d2_q <= 2'd0;
            tag_d0_q <= 16'd0;
            tag_d1_q <= 16'd0;
            tag_d2_q <= 16'd0;
            tag_d3_q <= 16'd0;
            pair_tag_d0_q <= 16'd0;
            pair_tag_d1_q <= 16'd0;
            pair_tag_d2_q <= 16'd0;
            quad_tag_d0_q <= 16'd0;
            quad_tag_d1_q <= 16'd0;
            quad_tag_d2_q <= 16'd0;
            oct_tag_d0_q <= 16'd0;
            oct_tag_d1_q <= 16'd0;
            oct_tag_d2_q <= 16'd0;
            reduce_tag_d0_q <= 16'd0;
            reduce_tag_d1_q <= 16'd0;
            reduce_tag_d2_q <= 16'd0;
            quad_reduce_d0_q <= 1'b0;
            quad_reduce_d1_q <= 1'b0;
            quad_reduce_d2_q <= 1'b0;
            oct_reduce_d0_q <= 1'b0;
            oct_reduce_d1_q <= 1'b0;
            oct_reduce_d2_q <= 1'b0;
            final_reduce_d0_q <= 1'b0;
            final_reduce_d1_q <= 1'b0;
            final_reduce_d2_q <= 1'b0;
            wide_add_pending_q <= 1'b0;
            wide_add_operand_a_q <= 128'd0;
            wide_add_operand_b_q <= 128'd0;
            wide_add_lanes_q <= 5'd0;
            wide_add_tag_q <= 16'd0;
            wide_add_lower_pipe_q <= 3'd0;
            wide_add_upper_pipe_q <= 3'd0;
            wide_add_lower_result_q <= 128'd0;
            parallel_prefetch_operand_b_q <= 192'd0;
            parallel_operand_a_q <= 192'd0;
            parallel_operand_b_q <= 192'd0;
            parallel_issue_q <= 1'b0;
            parallel_lanes_q <= 5'd0;
            parallel_tag_q <= 16'd0;
            post_add_valid_q <= 1'b0;
            post_add_operand_x_q <= 16'd0;
            post_add_operand_y_q <= 16'd0;
            post_add_input_tag_q <= 16'd0;
            post_add_pipe_q <= 3'd0;
            post_add_tag_d0_q <= 16'd0;
            post_add_tag_d1_q <= 16'd0;
            post_add_tag_d2_q <= 16'd0;
        end
        else begin
            if (direct_pending_issue)
                direct_pending_valid_q <= 1'b0;
            if (request_accept && direct_request && !direct_issue_ready) begin
                direct_pending_valid_q <= 1'b1;
                direct_pending_add_vector_q <= request_add_vector;
                direct_pending_lanes_q <= request_lanes;
                direct_pending_tag_q <= request_tag;
                direct_pending_operand_a_q <= selected_request_operand_a;
                direct_pending_operand_b_q <= selected_request_operand_b;
            end
            if (parallel_prefetch_valid)
                parallel_prefetch_operand_b_q <=
                    parallel_prefetch_operand_b_bus;
            parallel_issue_q <= parallel_add_issue;
            if (parallel_add_issue) begin
                parallel_operand_a_q <= selected_parallel_operand_a_bus;
                parallel_operand_b_q <= parallel_prefetch_operand_b_q;
                parallel_lanes_q <= parallel_add_lanes;
                parallel_tag_q <= parallel_add_tag;
            end
            if (wide_add_first_issue) begin
                wide_add_pending_q <= 1'b1;
                wide_add_operand_a_q <=
                    direct_command_operand_a[255:128];
                wide_add_operand_b_q <=
                    direct_command_operand_b[255:128];
                wide_add_lanes_q <= direct_command_lanes;
                wide_add_tag_q <= direct_command_tag;
            end
            else if (wide_add_second_issue) begin
                wide_add_pending_q <= 1'b0;
            end
            wide_add_lower_pipe_q <= {
                wide_add_lower_pipe_q[1:0], wide_add_first_issue
            };
            wide_add_upper_pipe_q <= {
                wide_add_upper_pipe_q[1:0], wide_add_second_issue
            };
            if (wide_add_lower_return)
                wide_add_lower_result_q <= pair_sum_bus;
            if (post_add_ready) begin
                post_add_valid_q <= post_add_valid;
                if (post_add_valid) begin
                    post_add_operand_x_q <= post_add_operand_x;
                    post_add_operand_y_q <= post_add_operand_y;
                    post_add_input_tag_q <= post_add_tag;
                end
            end
            post_add_pipe_q <= {post_add_pipe_q[1:0], post_add_issue};
            if (post_add_issue)
                post_add_tag_d0_q <= post_add_input_tag_q;
            else
                post_add_tag_d0_q <= 16'd0;
            post_add_tag_d1_q <= post_add_tag_d0_q;
            post_add_tag_d2_q <= post_add_tag_d1_q;
            if (multiply_issue) begin
                product_mask_d0_q <= request_mask;
                tag_d0_q <= request_tag;
            end
            else begin
                product_mask_d0_q <= 16'd0;
                tag_d0_q <= 16'd0;
            end
            product_mask_d1_q <= product_mask_d0_q;
            product_mask_d2_q <= product_mask_d1_q;
            product_mask_d3_q <= product_mask_d2_q;
            tag_d1_q <= tag_d0_q;
            tag_d2_q <= tag_d1_q;
            tag_d3_q <= tag_d2_q;

            if (pair_input_valid) begin
                pair_mask_d0_q <= pair_input_mask;
                pair_tag_d0_q <= pair_input_tag;
            end
            else begin
                pair_mask_d0_q <= 8'd0;
                pair_tag_d0_q <= 16'd0;
            end
            pair_mask_d1_q <= pair_mask_d0_q;
            pair_mask_d2_q <= pair_mask_d1_q;
            pair_tag_d1_q <= pair_tag_d0_q;
            pair_tag_d2_q <= pair_tag_d1_q;
            if (pair_reduce_valid) begin
                quad_mask_d0_q <= {
                    pair_mask_d2_q[6] | pair_mask_d2_q[7],
                    pair_mask_d2_q[4] | pair_mask_d2_q[5],
                    pair_mask_d2_q[2] | pair_mask_d2_q[3],
                    pair_mask_d2_q[0] | pair_mask_d2_q[1]
                };
                quad_tag_d0_q <= pair_tag;
            end
            else begin
                quad_mask_d0_q <= 4'd0;
                quad_tag_d0_q <= 16'd0;
            end
            quad_mask_d1_q <= quad_mask_d0_q;
            quad_mask_d2_q <= quad_mask_d1_q;
            quad_tag_d1_q <= quad_tag_d0_q;
            quad_tag_d2_q <= quad_tag_d1_q;
            quad_reduce_d0_q <= pair_reduce_valid;
            quad_reduce_d1_q <= quad_reduce_d0_q;
            quad_reduce_d2_q <= quad_reduce_d1_q;

            if (quad_reduce_valid) begin
                oct_mask_d0_q <= {
                    quad_mask_d2_q[2] | quad_mask_d2_q[3],
                    quad_mask_d2_q[0] | quad_mask_d2_q[1]
                };
                oct_tag_d0_q <= quad_tag_d2_q;
            end
            else begin
                oct_mask_d0_q <= 2'd0;
                oct_tag_d0_q <= 16'd0;
            end
            oct_mask_d1_q <= oct_mask_d0_q;
            oct_mask_d2_q <= oct_mask_d1_q;
            oct_tag_d1_q <= oct_tag_d0_q;
            oct_tag_d2_q <= oct_tag_d1_q;
            oct_reduce_d0_q <= quad_reduce_valid;
            oct_reduce_d1_q <= oct_reduce_d0_q;
            oct_reduce_d2_q <= oct_reduce_d1_q;

            if (oct_reduce_valid) begin
                reduce_tag_d0_q <= oct_tag_d2_q;
            end
            else begin
                reduce_tag_d0_q <= 16'd0;
            end
            reduce_tag_d1_q <= reduce_tag_d0_q;
            reduce_tag_d2_q <= reduce_tag_d1_q;
            final_reduce_d0_q <= oct_reduce_valid;
            final_reduce_d1_q <= final_reduce_d0_q;
            final_reduce_d2_q <= final_reduce_d1_q;
        end
    end

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            product_reduce_pipe_q <= 4'd0;
            pair_reduce_pipe_q <= 3'd0;
            product_vector_pipe_q <= 4'd0;
            pair_vector_pipe_q <= 3'd0;
        end
        else begin
            product_reduce_pipe_q <= {
                product_reduce_pipe_q[2:0],
                multiply_issue &&
                    (request_operation == OP_MULTIPLY_REDUCE)
            };
            pair_reduce_pipe_q <= {
                pair_reduce_pipe_q[1:0],
                product_reduce_valid ||
                    direct_reduce_issue
            };
            product_vector_pipe_q <= {
                product_vector_pipe_q[2:0],
                multiply_issue &&
                    (request_operation == OP_MULTIPLY_VECTOR)
            };
            pair_vector_pipe_q <= {
                pair_vector_pipe_q[1:0],
                direct_add_issue || parallel_issue_q
            };
        end
    end
endmodule
`default_nettype wire
