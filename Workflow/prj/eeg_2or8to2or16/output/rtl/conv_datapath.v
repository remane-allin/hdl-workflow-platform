// Module: conv_datapath
// Description: Executes the frozen eleven-operation EEG layer schedule.
// Scope: Runtime CH02..CH16 datapath with bit-exact legacy arithmetic.
// Spec Trace: REQ-EEG-FUNC-001, REQ-EEG-RTL-COMPAT-001,
//             REQ-EEG-V3-OPT-001, REQ-EEG-V3-OPT-002.
`timescale 1ns/1ps
`default_nettype none

module conv_datapath (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          op_valid,
    output wire          op_ready,
    input  wire [3:0]    opcode,
    input  wire [13:0]   source_base,
    input  wire [13:0]   destination_base,
    input  wire [10:0]   parameter_base,
    input  wire [4:0]    active_channels,
    output reg  [10:0]   parameter_read_address,
    input  wire [63:0]   parameter_read_data,
    output reg           feature_read_enable,
    output reg           feature_read_pair_enable,
    output reg           feature_read_quad_enable,
    output reg  [12:0]   feature_read_address,
    input  wire          feature_read_valid,
    input  wire [15:0]   feature_read_data,
    input  wire [15:0]   feature_read_pair_data,
    input  wire [15:0]   feature_read_quad_data2,
    input  wire [15:0]   feature_read_quad_data3,
    input  wire [15:0]   feature_read_oct_data4,
    input  wire [15:0]   feature_read_oct_data5,
    input  wire [15:0]   feature_read_oct_data6,
    input  wire [15:0]   feature_read_oct_data7,
    output reg           feature_write_valid,
    input  wire          feature_write_ready,
    output reg  [12:0]   feature_write_address,
    output reg  [15:0]   feature_write_data,
    output reg           feature_write2_valid,
    input  wire          feature_write2_ready,
    output reg  [12:0]   feature_write2_address,
    output reg  [15:0]   feature_write2_data,
    output reg           tile_clear,
    output reg           tile_write_valid,
    input  wire          tile_write_ready,
    output reg  [7:0]    tile_write_index,
    output reg  [15:0]   tile_write_data,
    output reg           tile_write2_valid,
    output reg  [7:0]    tile_write2_index,
    output reg  [15:0]   tile_write2_data,
    output reg           tile_write3_valid,
    output reg  [7:0]    tile_write3_index,
    output reg  [15:0]   tile_write3_data,
    output reg           tile_write4_valid,
    output reg  [7:0]    tile_write4_index,
    output reg  [15:0]   tile_write4_data,
    output reg  [7:0]    tile_read_base_index,
    input  wire [255:0]  tile_read_window,
    output reg           score_valid,
    input  wire          score_ready,
    output reg  [15:0]   score_data,
    output reg  [3:0]    score_index,
    output reg           score_last,
    output reg           op_done,
    output reg           op_error,
    output reg           mac_active,
    output reg           trace_write_valid,
    output reg  [3:0]    trace_opcode,
    output reg  [12:0]   trace_write_address,
    output reg  [15:0]   trace_write_data,
    output reg           trace_write2_valid,
    output reg  [12:0]   trace_write2_address,
    output reg  [15:0]   trace_write2_data
);
    localparam ST_IDLE            = 8'd0;
    localparam ST_SETUP           = 8'd1;
    localparam ST_PARAM_LOAD      = 8'd2;
    localparam ST_FEATURE_REQ     = 8'd3;
    localparam ST_FEATURE_WAIT    = 8'd4;
    localparam ST_OP0_ROW         = 8'd10;
    localparam ST_OP0_COMPUTE     = 8'd11;
    localparam ST_OP1_ROW         = 8'd12;
    localparam ST_OP1_PARAM       = 8'd13;
    localparam ST_OP1_COMPUTE     = 8'd14;
    localparam ST_OP2_ROW         = 8'd15;
    localparam ST_OP2_PARAM       = 8'd16;
    localparam ST_OP2_COMPUTE     = 8'd17;
    localparam ST_OP3_ROW         = 8'd18;
    localparam ST_OP3_PARAM       = 8'd19;
    localparam ST_OP3_COMPUTE     = 8'd20;
    localparam ST_OP4_PARAM       = 8'd21;
    localparam ST_OP4_SOURCE      = 8'd22;
    localparam ST_OP4_COMPUTE     = 8'd23;
    localparam ST_OP5_WINDOW      = 8'd24;
    localparam ST_OP5_COMPUTE     = 8'd25;
    localparam ST_OP6_PARAM       = 8'd26;
    localparam ST_OP6_ROW         = 8'd27;
    localparam ST_OP6_COMPUTE     = 8'd28;
    localparam ST_OP7_PARAM       = 8'd29;
    localparam ST_OP7_SOURCE      = 8'd30;
    localparam ST_OP7_COMPUTE     = 8'd31;
    localparam ST_OP8_WINDOW      = 8'd32;
    localparam ST_OP8_COMPUTE     = 8'd33;
    localparam ST_OP9_SOURCE      = 8'd34;
    localparam ST_OP9_PARAM       = 8'd35;
    localparam ST_OP9_COMPUTE     = 8'd36;
    localparam ST_OP10_SOURCE     = 8'd37;
    localparam ST_OP10_SCORE      = 8'd38;
    localparam ST_OP9_BIAS        = 8'd39;
    localparam ST_OP2_NEXT        = 8'd45;
    localparam ST_OP4_NEXT        = 8'd46;
    localparam ST_OP2_DRAIN       = 8'd47;

    reg [7:0] state;
    reg [7:0] return_state;
    reg [3:0] active_opcode;
    reg [12:0] source_physical_base;
    reg [12:0] destination_physical_base;
    reg [10:0] active_parameter_base;

    // Four aligned lane quartets replace the V1.0 sixteen-lane write
    // crossbar.  The total 2048 weight bits and the 256-bit read window are
    // unchanged, but each 64-bit parameter response writes one physical bank.
    (* ram_style = "distributed" *) reg [63:0] weight_quartet0 [0:7];
    (* ram_style = "distributed" *) reg [63:0] weight_quartet1 [0:7];
    (* ram_style = "distributed" *) reg [63:0] weight_quartet2 [0:7];
    (* ram_style = "distributed" *) reg [63:0] weight_quartet3 [0:7];
    reg [15:0] bias_bank [0:7];
    reg [10:0] parameter_load_base;
    reg [6:0] parameter_load_count;
    reg [6:0] parameter_load_index;
    reg parameter_load_strided;
    reg parameter_load_primed;
    reg [2:0] weight_read_group;
    reg [2:0] weight_read_group_upper;
    reg [2:0] bias_prefetch_group;
    reg [15:0] bias_word_q;
    reg [2:0] parameter_transfer_count;
    reg parameter_weight_write_enable;
    reg parameter_bias_write_enable;
    reg parameter_reverse_words;
    reg [1:0] parameter_weight_quartet;
    reg [2:0] parameter_write_group;
    reg [2:0] parameter_bias_write_group;
    reg [4:0] parameter_layout_offset;

    reg [12:0] load_current_address;
    reg [12:0] load_stride;
    reg [8:0] load_count;
    reg [8:0] load_index;
    reg [8:0] load_issue_index;
    reg [7:0] load_tile_base;
    reg load_dense_gather;

    reg [4:0] channel_counter;
    reg [7:0] time_counter;
    reg [3:0] input_feature_counter;
    reg [3:0] output_feature_counter;
    reg [3:0] class_counter;
    reg [15:0] dense_lower_result;
    reg [15:0] dense_pair_result;
    reg [15:0] op6_accumulator;
    reg [7:0] op6_issue_time_counter;
    reg op6_issue_complete;
    reg [3:0] pool_step;
    reg [15:0] pool_accumulator;
    reg [15:0] pool_prefetch_word0;
    reg [15:0] pool_prefetch_word1;
    reg [8:0] issue_index;
    reg [2:0] v3_issue_index;
    reg [8:0] retire_index;
    reg [4:0] op0_issue_channel_counter;
    reg op0_issue_complete;
    reg [1:0] op13_issue_feature_counter;
    reg op13_issue_complete;
    reg [7:0] op2_compute_tile_base;
    reg [7:0] op2_prefetch_tile_base;
    reg [12:0] op2_prefetch_address;
    reg [8:0] op2_prefetch_issue_index;
    reg [8:0] op2_prefetch_receive_index;
    reg op2_prefetch_active;
    reg op2_prefetch_started;
    reg [7:0] op4_compute_tile_base;
    reg [7:0] op4_prefetch_tile_base;
    reg [12:0] op4_prefetch_address;
    reg [4:0] op4_prefetch_issue_index;
    reg [4:0] op4_prefetch_receive_index;
    reg op4_prefetch_active;
    reg op4_prefetch_started;
    reg [3:0] v3_tag_write_pointer;
    reg [3:0] v3_tag_read_pointer;
    reg [4:0] v3_tag_count;
    // Tags and two cache lanes deliberately use spare FF capacity so the
    // total LUTRAM stays below the frozen 600-LUT budget.  The remaining six
    // cache lanes retain the denser distributed-RAM implementation.
    (* ram_style = "registers" *) reg [7:0] v3_tag_time [0:15];
    (* ram_style = "registers" *) reg [3:0] v3_tag_input_feature [0:15];
    (* ram_style = "registers" *) reg [2:0] v3_tag_group [0:15];
    reg [15:0] v3_retire_bias_lower_q;
    reg [15:0] v3_retire_bias_upper_q;
    reg v3_op4_post_valid;
    reg v3_op4_post2_valid;
    reg v3_pipeline_empty_q;
    reg v3_op4_post_split_q;
    reg [12:0] v3_op4_post_address_q;
    reg [12:0] v3_op4_post2_address_q;
    reg [15:0] v3_op4_post_full_data_q;
    reg [15:0] v3_op4_post_split_data_q;
    reg [15:0] v3_op4_post2_data_q;
    reg [255:0] v3_op4_odd_tile0;
    reg [255:0] v3_op4_odd_tile1;
    (* ram_style = "registers" *) reg [15:0] v3_op7_cache0 [0:31];
    (* ram_style = "registers" *) reg [15:0] v3_op7_cache1 [0:31];
    (* ram_style = "distributed" *) reg [15:0] v3_op7_cache2 [0:31];
    (* ram_style = "distributed" *) reg [15:0] v3_op7_cache3 [0:31];
    (* ram_style = "distributed" *) reg [15:0] v3_op7_cache4 [0:31];
    (* ram_style = "distributed" *) reg [15:0] v3_op7_cache5 [0:31];
    (* ram_style = "distributed" *) reg [15:0] v3_op7_cache6 [0:31];
    (* ram_style = "distributed" *) reg [15:0] v3_op7_cache7 [0:31];
    (* ram_style = "distributed" *) reg [15:0] partial_scratch [0:127];
    reg [15:0] partial_word_q;
    reg partial_result_valid_q;
    reg partial_result_final_q;
    reg [7:0] partial_result_index_q;
    reg [15:0] partial_result_data_q;

    reg [255:0] mac16_data_bus;
    reg [255:0] mac16_weight_bus;
    wire [15:0] mac16_result;
    wire mac16_output_valid;
    wire [15:0] mac8_result;
    wire [15:0] mac8_upper_result;
    wire mac8_output_valid;
    wire mac16_input_valid;
    wire [4:0] shared_prefetch_count;
    wire [4:0] last_active_channel = active_channels - 1'b1;
    wire [4:0] mac16_valid_lanes =
        (active_opcode == 4'd4) ? active_channels :
        (active_opcode == 4'd7) ? 5'd8 : 5'd16;
    wire [12:0] shared_prefetch_stride;
    wire load_quad_active;
    wire load_pair_active;
    wire [15:0] pool_selected_word;
    wire [15:0] pool_scaled;
    wire [15:0] partial_add_sum;
    wire [15:0] mac16_bias_sum;
    wire [15:0] v3_mac16_bias_sum;
    wire [15:0] op6_add_sum;
    wire [15:0] mac8_bias_sum;
    wire [15:0] mac8_upper_bias_sum;
    wire [15:0] pool_add_sum;
    wire [15:0] dense_pair_sum;
    wire [15:0] stream_dense_biased;
    wire [7:0] partial_prefetch_index =
        (mac16_output_valid && (retire_index != 9'd127)) ?
            retire_index[7:0] + 1'b1 : 8'd0;
    wire [15:0] partial_prefetch_value =
        partial_scratch[partial_prefetch_index];
    wire [15:0] bias_prefetch_value =
        bias_bank[bias_prefetch_group];
    wire partial_scratch_write_enable =
        partial_result_valid_q && !partial_result_final_q;
    wire [255:0] weight_lane_window = {
        weight_quartet3[weight_read_group],
        weight_quartet2[weight_read_group],
        weight_quartet1[weight_read_group],
        weight_quartet0[weight_read_group]
    };
    wire [255:0] weight_lane_window_upper = {
        weight_quartet3[weight_read_group_upper],
        weight_quartet2[weight_read_group_upper],
        weight_quartet1[weight_read_group_upper],
        weight_quartet0[weight_read_group_upper]
    };
    wire [4:0] op4_channel_group_count =
        (active_channels + 3'd3) >> 2;
    wire [8:0] op4_channel_load_count =
        {2'd0, op4_channel_group_count, 2'b00};
    // OP4 state already establishes the opcode; keep its low-channel choice
    // independent of the high-fanout opcode register on the retirement path.
    wire v3_op4_split8 = (active_channels <= 5'd8);
    wire v3_split8_mode =
        ((active_opcode == 4'd4) && v3_op4_split8) ||
        (active_opcode == 4'd7);
    wire [2:0] v3_issue_limit =
        (active_opcode == 4'd4) ? (v3_op4_split8 ? 3'd1 : 3'd2) :
        (active_opcode == 4'd7) ? 3'd4 : 3'd0;
    wire [7:0] v3_retire_time = v3_tag_time[v3_tag_read_pointer];
    wire [3:0] v3_retire_input_feature =
        v3_tag_input_feature[v3_tag_read_pointer];
    wire [2:0] v3_retire_group = v3_tag_group[v3_tag_read_pointer];
    wire [2:0] v3_issue_group =
        (active_opcode == 4'd4) ?
            (v3_op4_split8 ? 3'd0 : {2'd0, v3_issue_index[0]}) :
            v3_issue_index;
    wire [3:0] v3_bias_prefetch_pointer =
        v3_tag_read_pointer + 1'b1;
    reg [2:0] v3_bias_prefetch_group;
    wire v3_issue_fire = mac16_input_valid &&
        ((state == ST_OP4_COMPUTE) || (state == ST_OP7_COMPUTE));
    wire v3_issue_complete =
        (v3_issue_index >= v3_issue_limit) ||
        (v3_issue_fire &&
         ((v3_issue_index + 1'b1) >= v3_issue_limit));
    wire v3_retire_valid =
        ((state == ST_OP4_COMPUTE) &&
         (v3_op4_split8 ? mac8_output_valid : mac16_output_valid)) ||
        ((state == ST_OP7_COMPUTE) && mac8_output_valid);
    wire v3_op4_post_ready = !v3_op4_post_valid ||
        (feature_write_ready &&
         (!v3_op4_post2_valid || feature_write2_ready));
    wire v3_retire_fire = v3_retire_valid &&
        ((state == ST_OP4_COMPUTE) ? v3_op4_post_ready :
         (feature_write_ready &&
          (!feature_write2_valid || feature_write2_ready)));
    wire v3_prefetch_complete = !op4_prefetch_active ||
        (feature_read_valid && tile_write_ready &&
         (op4_prefetch_receive_index == (shared_prefetch_count - 1'b1)));
    wire [255:0] v3_op4_odd_window = op4_compute_tile_base[4] ?
        v3_op4_odd_tile1 : v3_op4_odd_tile0;
    wire [255:0] v3_op4_source_window = time_counter[0] ?
        v3_op4_odd_window : tile_read_window;
    wire [127:0] v3_op7_cache_window = {
        v3_op7_cache7[time_counter[4:0]],
        v3_op7_cache6[time_counter[4:0]],
        v3_op7_cache5[time_counter[4:0]],
        v3_op7_cache4[time_counter[4:0]],
        v3_op7_cache3[time_counter[4:0]],
        v3_op7_cache2[time_counter[4:0]],
        v3_op7_cache1[time_counter[4:0]],
        v3_op7_cache0[time_counter[4:0]]
    };
    wire [63:0] v3_oct_odd_quartet = {
        feature_read_oct_data7,
        feature_read_oct_data6,
        feature_read_oct_data5,
        feature_read_oct_data4
    };
    wire [63:0] parameter_weight_write_data = parameter_reverse_words ?
        {parameter_read_data[15:0], parameter_read_data[31:16],
         parameter_read_data[47:32], parameter_read_data[63:48]} :
        parameter_read_data;
    integer bus_index;

    assign op_ready = (state == ST_IDLE);
    assign shared_prefetch_count =
        (active_opcode == 4'd4) ? op4_channel_group_count :
        (active_opcode == 4'd5) ? 5'd4 : 5'd8;
    assign shared_prefetch_stride =
        (active_opcode == 4'd4) ? 13'd512 :
        (active_opcode == 4'd7) ? 13'd32 : 13'd1;
    assign load_quad_active =
        (state == ST_FEATURE_REQ) &&
        (active_opcode == 4'd4) &&
        (load_count == op4_channel_load_count) &&
        (load_stride == 13'd128);
    assign load_pair_active =
        (state == ST_FEATURE_REQ) &&
        !load_quad_active && !load_dense_gather &&
        (load_stride == 13'd1) && (load_count[0] == 1'b0);
    assign mac16_input_valid =
        ((state == ST_OP0_COMPUTE) && !op0_issue_complete) ||
        ((state == ST_OP2_COMPUTE) && (issue_index < 9'd128)) ||
        (((state == ST_OP1_COMPUTE) ||
          (state == ST_OP3_COMPUTE)) && !op13_issue_complete) ||
        ((state == ST_OP4_COMPUTE) &&
         (v3_issue_index < v3_issue_limit)) ||
        ((state == ST_OP6_COMPUTE) && !op6_issue_complete) ||
        ((state == ST_OP7_COMPUTE) &&
         (v3_issue_index < v3_issue_limit)) ||
        ((state == ST_OP9_COMPUTE) && (issue_index < 9'd2));
    assign pool_selected_word = tile_read_window[15:0];

    apx_mac16 mac16_inst (
        .clk(clk),
        .rst_n(rst_n),
        .input_valid(mac16_input_valid),
        .valid_lanes(mac16_valid_lanes),
        .split8_mode(v3_split8_mode),
        .data_bus(mac16_data_bus),
        .weight_bus(mac16_weight_bus),
        .output8_valid(mac8_output_valid),
        .result8(mac8_result),
        .result8_upper(mac8_upper_result),
        .output_valid(mac16_output_valid),
        .result(mac16_result)
    );

    apx_fp16_mul pool_scale_inst (
        .x(pool_accumulator),
        .y((active_opcode == 4'd5) ? 16'h3400 : 16'h3000),
        .product(pool_scaled)
    );

    // Operation-local post-process adders prevent mutually exclusive opcode
    // paths from being collapsed into a deep shared mux around one adder.
    apx_fp16_add partial_add_inst (
        .x(partial_word_q),
        .y(mac16_result),
        .sum(partial_add_sum)
    );

    apx_fp16_add mac16_bias_add_inst (
        .x(mac16_result),
        .y(bias_word_q),
        .sum(mac16_bias_sum)
    );

    apx_fp16_add v3_mac16_bias_add_inst (
        .x(mac16_result),
        .y(v3_retire_bias_lower_q),
        .sum(v3_mac16_bias_sum)
    );

    apx_fp16_add op6_add_inst (
        .x(op6_accumulator),
        .y(mac16_result),
        .sum(op6_add_sum)
    );

    apx_fp16_add mac8_bias_add_inst (
        .x(mac8_result),
        .y(v3_retire_bias_lower_q),
        .sum(mac8_bias_sum)
    );

    apx_fp16_add mac8_upper_bias_add_inst (
        .x(mac8_upper_result),
        .y(v3_retire_bias_upper_q),
        .sum(mac8_upper_bias_sum)
    );

    apx_fp16_add pool_add_inst (
        .x(pool_accumulator),
        // OP6 and pooling are mutually exclusive. Reuse the OP6 accumulator
        // as the registered pool-word boundary instead of adding another
        // sixteen flip-flops.
        .y(op6_accumulator),
        .sum(pool_add_sum)
    );

    apx_fp16_add dense_pair_add_inst (
        .x(dense_lower_result),
        .y(mac16_result),
        .sum(dense_pair_sum)
    );

    apx_fp16_add stream_dense_bias_add_inst (
        .x(dense_pair_result),
        .y(bias_bank[0]),
        .sum(stream_dense_biased)
    );

    always @* begin
        weight_read_group = 3'd0;
        case (active_opcode)
            4'd1: weight_read_group = {1'b0, op13_issue_feature_counter};
            4'd2: weight_read_group = input_feature_counter[2:0];
            4'd3: weight_read_group = {1'b0, op13_issue_feature_counter};
            4'd4: weight_read_group = v3_op4_split8 ?
                3'd0 : {2'd0, v3_issue_index[0]};
            4'd7: weight_read_group = {1'b0, v3_issue_index[1:0]};
            4'd9: weight_read_group = {2'd0, issue_index[0]};
            default: begin end
        endcase
    end

    always @* begin
        weight_read_group_upper = 3'd0;
        case (active_opcode)
            4'd4: weight_read_group_upper = 3'd1;
            4'd7: weight_read_group_upper =
                {1'b1, v3_issue_index[1:0]};
            default: begin end
        endcase
    end

    // Register bias selection one cycle before the corresponding MAC result.
    // This removes the opcode/counter -> bias-bank mux from the FP16 adder path.
    always @* begin
        bias_prefetch_group = 3'd0;
        case (state)
            ST_OP3_COMPUTE:
                if (mac16_output_valid && (retire_index == 9'd127) &&
                    (output_feature_counter != 4'd3))
                    bias_prefetch_group =
                        output_feature_counter[2:0] + 1'b1;
                else
                    bias_prefetch_group = output_feature_counter[2:0];
            ST_OP4_COMPUTE:
                if (mac16_output_valid && (retire_index != 9'd1))
                    bias_prefetch_group = 3'd1;
            ST_OP7_COMPUTE:
                if (mac8_output_valid && (retire_index != 9'd7))
                    bias_prefetch_group = retire_index[2:0] + 1'b1;
            default: begin end
        endcase
    end

    // Keep the bias for the FIFO head in a local register.  On a retirement
    // edge, prefetch the following tag so back-to-back MAC results retain
    // one-result-per-cycle throughput without a tag/bias mux on the FP path.
    always @* begin
        v3_bias_prefetch_group = v3_retire_group;
        if (v3_retire_fire) begin
            if (v3_tag_count > 5'd1)
                v3_bias_prefetch_group =
                    v3_tag_group[v3_bias_prefetch_pointer];
            else if (v3_issue_fire)
                v3_bias_prefetch_group = v3_issue_group;
        end
        else if ((v3_tag_count == 5'd0) && v3_issue_fire) begin
            v3_bias_prefetch_group = v3_issue_group;
        end
    end

    always @* begin
        if (active_opcode == 4'd7) begin
            if ((parameter_load_index == 7'd8) ||
                (parameter_load_index == 7'd17) ||
                (parameter_load_index == 7'd26) ||
                (parameter_load_index == 7'd35) ||
                (parameter_load_index == 7'd44) ||
                (parameter_load_index == 7'd53) ||
                (parameter_load_index == 7'd62) ||
                (parameter_load_index == 7'd71))
                parameter_transfer_count = 3'd1;
            else
                parameter_transfer_count = 3'd4;
        end
        else if (parameter_load_strided) begin
            if ((parameter_load_index == 7'd16) ||
                (parameter_load_index == 7'd33) ||
                (parameter_load_index == 7'd50) ||
                (parameter_load_index == 7'd67))
                parameter_transfer_count = 3'd1;
            else if ((parameter_load_index == 7'd15) ||
                     (parameter_load_index == 7'd32) ||
                     (parameter_load_index == 7'd49) ||
                     (parameter_load_index == 7'd66))
                parameter_transfer_count = 3'd2;
            else if ((parameter_load_index == 7'd14) ||
                     (parameter_load_index == 7'd31) ||
                     (parameter_load_index == 7'd48) ||
                     (parameter_load_index == 7'd65))
                parameter_transfer_count = 3'd3;
            else
                parameter_transfer_count = 3'd4;
        end
        else if ((active_opcode == 4'd4) &&
                 ((parameter_load_index == 7'd16) ||
                  (parameter_load_index == 7'd33)))
            parameter_transfer_count = 3'd1;
        else if ((active_opcode == 4'd9) &&
                 (parameter_load_index == 7'd32))
            parameter_transfer_count = 3'd1;
        else
            parameter_transfer_count = 3'd4;
    end

    always @* begin
        parameter_weight_write_enable = 1'b0;
        parameter_bias_write_enable = 1'b0;
        parameter_reverse_words = 1'b0;
        parameter_weight_quartet = 2'd0;
        parameter_write_group = 3'd0;
        parameter_bias_write_group = 3'd0;
        parameter_layout_offset = 5'd0;

        case (active_opcode)
            4'd0, 4'd1, 4'd2, 4'd6: begin
                parameter_weight_write_enable = 1'b1;
                parameter_weight_quartet = parameter_load_index[3:2];
                parameter_write_group = parameter_load_index[6:4];
            end
            4'd3, 4'd4: begin
                if (parameter_load_index < 7'd17) begin
                    parameter_write_group = 3'd0;
                    parameter_layout_offset = parameter_load_index[4:0];
                end
                else if (parameter_load_index < 7'd34) begin
                    parameter_write_group = 3'd1;
                    parameter_layout_offset = parameter_load_index - 7'd17;
                end
                else if (parameter_load_index < 7'd51) begin
                    parameter_write_group = 3'd2;
                    parameter_layout_offset = parameter_load_index - 7'd34;
                end
                else begin
                    parameter_write_group = 3'd3;
                    parameter_layout_offset = parameter_load_index - 7'd51;
                end
                parameter_bias_write_group = parameter_write_group;
                if (parameter_layout_offset == 5'd16)
                    parameter_bias_write_enable = 1'b1;
                else begin
                    parameter_weight_write_enable = 1'b1;
                    parameter_weight_quartet = parameter_layout_offset[3:2];
                end
            end
            4'd7: begin
                if (parameter_load_index < 7'd9) begin
                    parameter_write_group = 3'd0;
                    parameter_layout_offset = parameter_load_index[4:0];
                end
                else if (parameter_load_index < 7'd18) begin
                    parameter_write_group = 3'd1;
                    parameter_layout_offset = parameter_load_index - 7'd9;
                end
                else if (parameter_load_index < 7'd27) begin
                    parameter_write_group = 3'd2;
                    parameter_layout_offset = parameter_load_index - 7'd18;
                end
                else if (parameter_load_index < 7'd36) begin
                    parameter_write_group = 3'd3;
                    parameter_layout_offset = parameter_load_index - 7'd27;
                end
                else if (parameter_load_index < 7'd45) begin
                    parameter_write_group = 3'd4;
                    parameter_layout_offset = parameter_load_index - 7'd36;
                end
                else if (parameter_load_index < 7'd54) begin
                    parameter_write_group = 3'd5;
                    parameter_layout_offset = parameter_load_index - 7'd45;
                end
                else if (parameter_load_index < 7'd63) begin
                    parameter_write_group = 3'd6;
                    parameter_layout_offset = parameter_load_index - 7'd54;
                end
                else begin
                    parameter_write_group = 3'd7;
                    parameter_layout_offset = parameter_load_index - 7'd63;
                end
                parameter_bias_write_group = parameter_write_group;
                if (parameter_layout_offset == 5'd8)
                    parameter_bias_write_enable = 1'b1;
                else begin
                    parameter_weight_write_enable = 1'b1;
                    parameter_reverse_words = 1'b1;
                    parameter_weight_quartet =
                        (parameter_layout_offset == 5'd0) ? 2'd1 : 2'd0;
                end
            end
            4'd9: begin
                if (parameter_load_index == 7'd32) begin
                    parameter_bias_write_enable = 1'b1;
                    parameter_bias_write_group = 3'd0;
                end
                else begin
                    parameter_weight_write_enable = 1'b1;
                    parameter_weight_quartet = parameter_load_index[3:2];
                    parameter_write_group = parameter_load_index[4] ? 3'd1 : 3'd0;
                end
            end
            default: begin end
        endcase
    end

    always @(posedge clk) begin
        if ((state == ST_PARAM_LOAD) && parameter_load_primed) begin
            if (parameter_weight_write_enable) begin
                case (parameter_weight_quartet)
                    2'd0: weight_quartet0[parameter_write_group] <=
                        parameter_weight_write_data;
                    2'd1: weight_quartet1[parameter_write_group] <=
                        parameter_weight_write_data;
                    2'd2: weight_quartet2[parameter_write_group] <=
                        parameter_weight_write_data;
                    2'd3: weight_quartet3[parameter_write_group] <=
                        parameter_weight_write_data;
                    default: begin end
                endcase
            end
            if (parameter_bias_write_enable)
                bias_bank[parameter_bias_write_group] <=
                    parameter_read_data[15:0];
        end
    end

    always @(posedge clk) begin
        if (partial_scratch_write_enable)
            partial_scratch[partial_result_index_q] <=
                partial_result_data_q;
    end

    always @* begin
        mac16_data_bus = 256'd0;
        mac16_weight_bus = 256'd0;
        tile_read_base_index = 8'd0;

        if ((active_opcode <= 4'd3) || (active_opcode == 4'd6)) begin
            mac16_weight_bus = weight_lane_window;
            if ((active_opcode == 4'd6) &&
                (issue_index[3:0] != output_feature_counter))
                mac16_weight_bus = 256'd0;
            tile_read_base_index =
                ((active_opcode == 4'd6) ?
                    {issue_index[2:0], 5'b00000} : 8'd0) +
                ((active_opcode <= 4'd3) ?
                    ((active_opcode == 4'd0) ?
                        {op0_issue_channel_counter[0], 7'b0000000} :
                        op2_compute_tile_base) : 8'd0) +
                ((active_opcode == 4'd6) ?
                    op6_issue_time_counter : issue_index[7:0]) - 8'd7;
            for (bus_index = 0; bus_index < 16; bus_index = bus_index + 1) begin
                if ((((active_opcode == 4'd6) ?
                        op6_issue_time_counter : issue_index[7:0]) + bus_index >= 7) &&
                    (((active_opcode == 4'd6) ?
                        op6_issue_time_counter : issue_index[7:0]) + bus_index <
                        ((active_opcode == 4'd6) ? 39 : 135)))
                    mac16_data_bus[bus_index*16 +: 16] =
                        tile_read_window[bus_index*16 +: 16];
            end
        end
        else if (active_opcode == 4'd4) begin
            tile_read_base_index = op4_compute_tile_base;
            if (v3_op4_split8) begin
                mac16_weight_bus[127:0] = weight_lane_window[127:0];
                mac16_weight_bus[255:128] =
                    weight_lane_window_upper[127:0];
                for (bus_index = 0; bus_index < 8;
                     bus_index = bus_index + 1) begin
                    mac16_data_bus[bus_index*16 +: 16] =
                        v3_op4_source_window[bus_index*16 +: 16];
                    mac16_data_bus[(bus_index+8)*16 +: 16] =
                        v3_op4_source_window[bus_index*16 +: 16];
                end
            end
            else begin
                mac16_weight_bus = weight_lane_window;
                for (bus_index = 0; bus_index < 16;
                     bus_index = bus_index + 1) begin
                    mac16_data_bus[bus_index*16 +: 16] =
                        v3_op4_source_window[bus_index*16 +: 16];
                end
            end
        end
        else if (active_opcode == 4'd9) begin
            mac16_weight_bus = weight_lane_window;
            tile_read_base_index = issue_index[0] ? 8'd16 : 8'd0;
            for (bus_index = 0; bus_index < 16; bus_index = bus_index + 1) begin
                mac16_data_bus[bus_index*16 +: 16] =
                    tile_read_window[bus_index*16 +: 16];
            end
        end

        if (active_opcode == 4'd7) begin
            tile_read_base_index = op4_compute_tile_base;
            mac16_weight_bus[127:0] = weight_lane_window[127:0];
            mac16_weight_bus[255:128] =
                weight_lane_window_upper[127:0];
            for (bus_index = 0; bus_index < 8; bus_index = bus_index + 1) begin
                mac16_data_bus[bus_index*16 +: 16] =
                    v3_op7_cache_window[bus_index*16 +: 16];
                mac16_data_bus[(bus_index+8)*16 +: 16] =
                    v3_op7_cache_window[bus_index*16 +: 16];
            end
        end
        else if ((active_opcode == 4'd5) || (active_opcode == 4'd8)) begin
            if ((state == ST_OP5_COMPUTE) ||
                (state == ST_OP8_COMPUTE))
                tile_read_base_index = op4_compute_tile_base +
                    {4'd0, pool_step} + 8'd1;
            else
                tile_read_base_index = op4_compute_tile_base;
        end
    end

    reg [6:0] parameter_request_index;

    always @* begin
        parameter_request_index = parameter_load_index;
        if ((state == ST_PARAM_LOAD) &&
            parameter_load_primed)
            parameter_request_index =
                parameter_load_index + parameter_transfer_count;

        if (parameter_load_strided) begin
            if (parameter_request_index < 7'd17)
                parameter_read_address =
                    parameter_load_base + parameter_request_index;
            else if (parameter_request_index < 7'd34)
                parameter_read_address =
                    parameter_load_base + parameter_request_index + 7'd34;
            else if (parameter_request_index < 7'd51)
                parameter_read_address =
                    parameter_load_base + parameter_request_index + 7'd68;
            else
                parameter_read_address =
                    parameter_load_base + parameter_request_index + 7'd102;
        end
        else begin
            parameter_read_address =
                parameter_load_base + parameter_request_index;
        end
        feature_read_enable = 1'b0;
        feature_read_pair_enable = 1'b0;
        feature_read_quad_enable = 1'b0;
        feature_read_address = 13'd0;
        feature_write_valid = 1'b0;
        feature_write_address = 13'd0;
        feature_write_data = 16'd0;
        feature_write2_valid = 1'b0;
        feature_write2_address = 13'd0;
        feature_write2_data = 16'd0;
        tile_clear = 1'b0;
        tile_write_valid = 1'b0;
        tile_write_index = 8'd0;
        tile_write_data = 16'd0;
        tile_write2_valid = 1'b0;
        tile_write2_index = 8'd0;
        tile_write2_data = 16'd0;
        tile_write3_valid = 1'b0;
        tile_write3_index = 8'd0;
        tile_write3_data = 16'd0;
        tile_write4_valid = 1'b0;
        tile_write4_index = 8'd0;
        tile_write4_data = 16'd0;
        score_valid = 1'b0;
        score_data = 16'd0;
        score_index = class_counter;
        score_last = (class_counter == 4'd15);
        mac_active = 1'b0;

        if ((state == ST_FEATURE_REQ) &&
            (load_issue_index < load_count)) begin
            feature_read_enable = 1'b1;
            feature_read_address = load_current_address;
            feature_read_pair_enable = load_pair_active;
            feature_read_quad_enable = load_quad_active;
        end
        else if (((state == ST_OP0_COMPUTE) ||
                  (state == ST_OP1_COMPUTE) ||
                  (state == ST_OP2_COMPUTE) ||
                  (state == ST_OP3_COMPUTE)) &&
                 op2_prefetch_active &&
                 (op2_prefetch_issue_index < 9'd128)) begin
            feature_read_enable = 1'b1;
            feature_read_address = op2_prefetch_address;
            feature_read_pair_enable = 1'b1;
        end
        else if (((state == ST_OP4_COMPUTE) ||
                  (state == ST_OP5_COMPUTE) ||
                  (state == ST_OP7_COMPUTE) ||
                  (state == ST_OP8_COMPUTE) ||
                  (state == ST_OP4_NEXT)) &&
                 op4_prefetch_active &&
                 (op4_prefetch_issue_index < shared_prefetch_count)) begin
            feature_read_enable = 1'b1;
            feature_read_address = op4_prefetch_address;
            feature_read_pair_enable =
                (active_opcode == 4'd5) || (active_opcode == 4'd8);
            feature_read_quad_enable = (active_opcode == 4'd4);
        end

        if ((state == ST_FEATURE_REQ) && feature_read_valid) begin
            tile_write_valid = 1'b1;
            tile_write_index = load_tile_base + load_index[7:0];
            tile_write_data = feature_read_data;
            if (load_quad_active) begin
                tile_write2_valid = 1'b1;
                tile_write2_index = tile_write_index + 1'b1;
                tile_write2_data = feature_read_pair_data;
                tile_write3_valid = 1'b1;
                tile_write3_index = tile_write_index + 2'd2;
                tile_write3_data = feature_read_quad_data2;
                tile_write4_valid = 1'b1;
                tile_write4_index = tile_write_index + 2'd3;
                tile_write4_data = feature_read_quad_data3;
            end
            else if (load_pair_active) begin
                tile_write2_valid = 1'b1;
                tile_write2_index = tile_write_index + 1'b1;
                tile_write2_data = feature_read_pair_data;
            end
        end
        else if (((state == ST_OP0_COMPUTE) ||
                  (state == ST_OP1_COMPUTE) ||
                  (state == ST_OP2_COMPUTE) ||
                  (state == ST_OP3_COMPUTE)) &&
                 op2_prefetch_active && feature_read_valid) begin
            tile_write_valid = 1'b1;
            tile_write_index = op2_prefetch_tile_base +
                op2_prefetch_receive_index[7:0];
            tile_write_data = feature_read_data;
            tile_write2_valid = 1'b1;
            tile_write2_index = tile_write_index + 1'b1;
            tile_write2_data = feature_read_pair_data;
        end
        else if (((state == ST_OP4_COMPUTE) ||
                  (state == ST_OP5_COMPUTE) ||
                  (state == ST_OP7_COMPUTE) ||
                  (state == ST_OP8_COMPUTE) ||
                  (state == ST_OP4_NEXT)) &&
                 op4_prefetch_active && feature_read_valid) begin
            tile_write_valid = 1'b1;
            tile_write_index = op4_prefetch_tile_base +
                ((active_opcode == 4'd4) ?
                    {op4_prefetch_receive_index[2:0], 2'b00} :
                    ((active_opcode == 4'd5) || (active_opcode == 4'd8)) ?
                        op4_prefetch_receive_index[3:0] :
                        op4_prefetch_receive_index[3:0]);
            tile_write_data = feature_read_data;
            if (active_opcode == 4'd4) begin
                tile_write2_valid = 1'b1;
                tile_write2_index = tile_write_index + 1'b1;
                tile_write2_data = feature_read_pair_data;
                tile_write3_valid = 1'b1;
                tile_write3_index = tile_write_index + 2'd2;
                tile_write3_data = feature_read_quad_data2;
                tile_write4_valid = 1'b1;
                tile_write4_index = tile_write_index + 2'd3;
                tile_write4_data = feature_read_quad_data3;
            end
            else if ((active_opcode == 4'd5) ||
                     (active_opcode == 4'd8)) begin
                tile_write2_valid = 1'b1;
                tile_write2_index = tile_write_index + 1'b1;
                tile_write2_data = feature_read_pair_data;
            end
        end

        case (state)
            ST_OP0_ROW, ST_OP1_ROW, ST_OP2_ROW, ST_OP3_ROW,
            ST_OP4_SOURCE, ST_OP5_WINDOW, ST_OP6_ROW, ST_OP7_SOURCE,
            ST_OP8_WINDOW, ST_OP9_SOURCE, ST_OP10_SOURCE:
                tile_clear = (load_index == 0);
            ST_OP0_COMPUTE: begin
                mac_active = 1'b1;
                feature_write_valid = mac16_output_valid;
                feature_write_address = destination_physical_base +
                    channel_counter * 13'd128 + retire_index[7:0];
                feature_write_data = mac16_result;
            end
            ST_OP1_COMPUTE: begin
                mac_active = 1'b1;
                feature_write_valid = mac16_output_valid;
                feature_write_address = destination_physical_base +
                    output_feature_counter * 13'd2048 +
                    channel_counter * 13'd128 +
                    retire_index[7:0];
                feature_write_data = mac16_result;
            end
            ST_OP2_COMPUTE: begin
                mac_active = 1'b1;
                if (partial_result_valid_q && partial_result_final_q) begin
                    feature_write_valid = 1'b1;
                    feature_write_address = destination_physical_base +
                        channel_counter * 13'd128 + partial_result_index_q;
                    feature_write_data = partial_result_data_q;
                end
            end
            ST_OP2_DRAIN: begin
                if (partial_result_valid_q && partial_result_final_q) begin
                    feature_write_valid = 1'b1;
                    feature_write_address = destination_physical_base +
                        channel_counter * 13'd128 + partial_result_index_q;
                    feature_write_data = partial_result_data_q;
                end
            end
            ST_OP3_COMPUTE: begin
                mac_active = 1'b1;
                feature_write_valid = mac16_output_valid;
                feature_write_address = destination_physical_base +
                    output_feature_counter * 13'd2048 +
                    channel_counter * 13'd128 +
                    retire_index[7:0];
                feature_write_data = mac16_bias_sum[15] ?
                    16'h0000 : mac16_bias_sum;
            end
            ST_OP4_COMPUTE: begin
                mac_active = 1'b1;
                feature_write_valid = v3_op4_post_valid;
                feature_write_address = v3_op4_post_address_q;
                feature_write_data = v3_op4_post_split_q ?
                    v3_op4_post_split_data_q :
                    v3_op4_post_full_data_q;
                feature_write2_valid = v3_op4_post2_valid;
                feature_write2_address = v3_op4_post2_address_q;
                feature_write2_data = v3_op4_post2_data_q;
            end
            ST_OP5_COMPUTE: begin
                feature_write_valid = (pool_step == 4'd4);
                feature_write_address = destination_physical_base +
                    output_feature_counter * 13'd32 + time_counter;
                feature_write_data = pool_scaled;
            end
            ST_OP6_COMPUTE: begin
                mac_active = 1'b1;
                if ((retire_index == 9'd7) && mac16_output_valid) begin
                    feature_write_valid = 1'b1;
                    feature_write_address = destination_physical_base +
                        output_feature_counter * 13'd32 + time_counter;
                    feature_write_data = op6_add_sum;
                end
                else begin
                    feature_write_valid = 1'b0;
                end
            end
            ST_OP7_COMPUTE: begin
                mac_active = 1'b1;
                feature_write_valid = mac8_output_valid;
                feature_write_address = destination_physical_base +
                    v3_retire_group * 13'd32 + v3_retire_time;
                feature_write_data = mac8_bias_sum[15] ?
                    16'h0000 : mac8_bias_sum;
                feature_write2_valid = mac8_output_valid;
                feature_write2_address = destination_physical_base +
                    (v3_retire_group + 3'd4) * 13'd32 + v3_retire_time;
                feature_write2_data = mac8_upper_bias_sum[15] ?
                    16'h0000 : mac8_upper_bias_sum;
            end
            ST_OP8_COMPUTE: begin
                feature_write_valid = (pool_step == 4'd8);
                feature_write_address = destination_physical_base +
                    output_feature_counter * 13'd4 + time_counter;
                feature_write_data = pool_scaled;
            end
            ST_OP9_COMPUTE: begin
                mac_active = 1'b1;
            end
            ST_OP9_BIAS: begin
                feature_write_valid = 1'b1;
                feature_write_address = destination_physical_base +
                    class_counter;
                feature_write_data = stream_dense_biased;
            end
            ST_OP10_SCORE: begin
                score_valid = 1'b1;
                score_data = tile_read_window[15:0];
            end
            default: begin end
        endcase
    end

    // Keep cache and tag payload writes in reset-free synchronous processes.
    // Their validity is owned by resettable pointers/counters, so clearing the
    // payload bits is unnecessary and would prevent distributed-RAM inference.
    always @(posedge clk) begin
        if ((state == ST_OP6_COMPUTE) && mac16_output_valid &&
            (retire_index == 9'd7) && feature_write_ready) begin
            case (output_feature_counter[2:0])
                3'd0: v3_op7_cache0[time_counter[4:0]] <= op6_add_sum;
                3'd1: v3_op7_cache1[time_counter[4:0]] <= op6_add_sum;
                3'd2: v3_op7_cache2[time_counter[4:0]] <= op6_add_sum;
                3'd3: v3_op7_cache3[time_counter[4:0]] <= op6_add_sum;
                3'd4: v3_op7_cache4[time_counter[4:0]] <= op6_add_sum;
                3'd5: v3_op7_cache5[time_counter[4:0]] <= op6_add_sum;
                3'd6: v3_op7_cache6[time_counter[4:0]] <= op6_add_sum;
                3'd7: v3_op7_cache7[time_counter[4:0]] <= op6_add_sum;
                default: begin end
            endcase
        end
    end

    always @(posedge clk) begin
        if (v3_issue_fire) begin
            v3_tag_time[v3_tag_write_pointer] <= time_counter;
            v3_tag_input_feature[v3_tag_write_pointer] <=
                input_feature_counter;
            v3_tag_group[v3_tag_write_pointer] <= v3_issue_group;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= ST_IDLE;
            return_state <= ST_IDLE;
            active_opcode <= 4'd0;
            source_physical_base <= 13'd0;
            destination_physical_base <= 13'd0;
            active_parameter_base <= 11'd0;
            parameter_load_base <= 11'd0;
            parameter_load_count <= 7'd0;
            parameter_load_index <= 7'd0;
            parameter_load_strided <= 1'b0;
            parameter_load_primed <= 1'b0;
            load_current_address <= 13'd0;
            load_stride <= 13'd1;
            load_count <= 9'd0;
            load_index <= 9'd0;
            load_issue_index <= 9'd0;
            load_tile_base <= 8'd0;
            load_dense_gather <= 1'b0;
            channel_counter <= 5'd0;
            time_counter <= 8'd0;
            input_feature_counter <= 4'd0;
            output_feature_counter <= 4'd0;
            class_counter <= 4'd0;
            dense_lower_result <= 16'd0;
            dense_pair_result <= 16'd0;
            op6_accumulator <= 16'd0;
            op6_issue_time_counter <= 8'd0;
            op6_issue_complete <= 1'b0;
            pool_step <= 4'd0;
            pool_accumulator <= 16'd0;
            pool_prefetch_word0 <= 16'd0;
            pool_prefetch_word1 <= 16'd0;
            issue_index <= 9'd0;
            v3_issue_index <= 3'd0;
            retire_index <= 9'd0;
            op0_issue_channel_counter <= 5'd0;
            op0_issue_complete <= 1'b0;
            op13_issue_feature_counter <= 2'd0;
            op13_issue_complete <= 1'b0;
            op2_compute_tile_base <= 8'd0;
            op2_prefetch_tile_base <= 8'd128;
            op2_prefetch_address <= 13'd0;
            op2_prefetch_issue_index <= 9'd0;
            op2_prefetch_receive_index <= 9'd0;
            op2_prefetch_active <= 1'b0;
            op2_prefetch_started <= 1'b0;
            op4_compute_tile_base <= 8'd0;
            op4_prefetch_tile_base <= 8'd16;
            op4_prefetch_address <= 13'd0;
            op4_prefetch_issue_index <= 5'd0;
            op4_prefetch_receive_index <= 5'd0;
            op4_prefetch_active <= 1'b0;
            op4_prefetch_started <= 1'b0;
            v3_tag_write_pointer <= 4'd0;
            v3_tag_read_pointer <= 4'd0;
            v3_tag_count <= 5'd0;
            v3_retire_bias_lower_q <= 16'd0;
            v3_retire_bias_upper_q <= 16'd0;
            v3_op4_post_valid <= 1'b0;
            v3_op4_post2_valid <= 1'b0;
            v3_pipeline_empty_q <= 1'b0;
            v3_op4_post_split_q <= 1'b0;
            v3_op4_post_address_q <= 13'd0;
            v3_op4_post2_address_q <= 13'd0;
            v3_op4_post_full_data_q <= 16'd0;
            v3_op4_post_split_data_q <= 16'd0;
            v3_op4_post2_data_q <= 16'd0;
            v3_op4_odd_tile0 <= 256'd0;
            v3_op4_odd_tile1 <= 256'd0;
            partial_word_q <= 16'd0;
            partial_result_valid_q <= 1'b0;
            partial_result_final_q <= 1'b0;
            partial_result_index_q <= 8'd0;
            partial_result_data_q <= 16'd0;
            bias_word_q <= 16'd0;
            op_done <= 1'b0;
            op_error <= 1'b0;
            trace_write_valid <= 1'b0;
            trace_opcode <= 4'd0;
            trace_write_address <= 13'd0;
            trace_write_data <= 16'd0;
            trace_write2_valid <= 1'b0;
            trace_write2_address <= 13'd0;
            trace_write2_data <= 16'd0;
        end
        else begin
            op_done <= 1'b0;
            op_error <= 1'b0;
            trace_write_valid <= feature_write_valid && feature_write_ready;
            trace_opcode <= active_opcode;
            if (feature_write_valid && feature_write_ready) begin
                trace_write_address <= feature_write_address;
                trace_write_data <= feature_write_data;
            end
            trace_write2_valid <= feature_write2_valid && feature_write2_ready;
            if (feature_write2_valid && feature_write2_ready) begin
                trace_write2_address <= feature_write2_address;
                trace_write2_data <= feature_write2_data;
            end

            // OP4 reads all eight physical parity banks in one BRAM cycle.
            // The normal quad response fills the even-time tile while this
            // compact companion tile retains the adjacent odd-time quartet.
            if ((state == ST_FEATURE_REQ) && load_quad_active &&
                feature_read_valid && tile_write_ready) begin
                if (op4_compute_tile_base[4]) begin
                    case (load_index[3:2])
                        2'd0: v3_op4_odd_tile1[63:0] <=
                            v3_oct_odd_quartet;
                        2'd1: v3_op4_odd_tile1[127:64] <=
                            v3_oct_odd_quartet;
                        2'd2: v3_op4_odd_tile1[191:128] <=
                            v3_oct_odd_quartet;
                        2'd3: v3_op4_odd_tile1[255:192] <=
                            v3_oct_odd_quartet;
                        default: begin end
                    endcase
                end
                else begin
                    case (load_index[3:2])
                        2'd0: v3_op4_odd_tile0[63:0] <=
                            v3_oct_odd_quartet;
                        2'd1: v3_op4_odd_tile0[127:64] <=
                            v3_oct_odd_quartet;
                        2'd2: v3_op4_odd_tile0[191:128] <=
                            v3_oct_odd_quartet;
                        2'd3: v3_op4_odd_tile0[255:192] <=
                            v3_oct_odd_quartet;
                        default: begin end
                    endcase
                end
            end
            if ((state == ST_OP4_COMPUTE) && op4_prefetch_active &&
                feature_read_valid && tile_write_ready) begin
                if (op4_prefetch_tile_base[4]) begin
                    case (op4_prefetch_receive_index[1:0])
                        2'd0: v3_op4_odd_tile1[63:0] <=
                            v3_oct_odd_quartet;
                        2'd1: v3_op4_odd_tile1[127:64] <=
                            v3_oct_odd_quartet;
                        2'd2: v3_op4_odd_tile1[191:128] <=
                            v3_oct_odd_quartet;
                        2'd3: v3_op4_odd_tile1[255:192] <=
                            v3_oct_odd_quartet;
                        default: begin end
                    endcase
                end
                else begin
                    case (op4_prefetch_receive_index[1:0])
                        2'd0: v3_op4_odd_tile0[63:0] <=
                            v3_oct_odd_quartet;
                        2'd1: v3_op4_odd_tile0[127:64] <=
                            v3_oct_odd_quartet;
                        2'd2: v3_op4_odd_tile0[191:128] <=
                            v3_oct_odd_quartet;
                        2'd3: v3_op4_odd_tile0[255:192] <=
                            v3_oct_odd_quartet;
                        default: begin end
                    endcase
                end
            end

            // Register the V3 drain decision so feature-memory collision
            // readiness cannot feed either OP4 or OP7 completion logic in the
            // same cycle.  Activity explicitly clears the observation to
            // prevent a stale empty indication from the previous time step.
            if (state == ST_OP4_COMPUTE)
                v3_pipeline_empty_q <=
                    (v3_tag_count == 5'd0) &&
                    !v3_op4_post_valid &&
                    !v3_issue_fire &&
                    !v3_retire_valid;
            else if (state == ST_OP7_COMPUTE)
                v3_pipeline_empty_q <=
                    (v3_tag_count == 5'd0) &&
                    !v3_issue_fire &&
                    !v3_retire_valid;
            else
                v3_pipeline_empty_q <= 1'b0;

            case ({v3_issue_fire, v3_retire_fire})
                2'b10: v3_tag_count <= v3_tag_count + 1'b1;
                2'b01: v3_tag_count <= v3_tag_count - 1'b1;
                default: v3_tag_count <= v3_tag_count;
            endcase
            if (v3_issue_fire) begin
                v3_tag_write_pointer <= v3_tag_write_pointer + 1'b1;
            end
            if (v3_retire_fire)
                v3_tag_read_pointer <= v3_tag_read_pointer + 1'b1;

            if (state == ST_OP4_COMPUTE) begin
                if (v3_op4_post_ready) begin
                    v3_op4_post_valid <= v3_retire_valid;
                    v3_op4_post2_valid <=
                        v3_retire_valid && v3_op4_split8;
                    if (v3_retire_valid) begin
                        v3_op4_post_split_q <= v3_op4_split8;
                        v3_op4_post_address_q <=
                            destination_physical_base +
                            (v3_retire_input_feature * 5'd2 +
                             v3_retire_group) * 13'd128 +
                            v3_retire_time;
                        v3_op4_post2_address_q <=
                            destination_physical_base +
                            (v3_retire_input_feature * 5'd2 + 1'b1) *
                            13'd128 +
                            v3_retire_time;
                        v3_op4_post_full_data_q <=
                            v3_mac16_bias_sum[15] ?
                                16'h0000 : v3_mac16_bias_sum;
                        v3_op4_post_split_data_q <=
                            mac8_bias_sum[15] ? 16'h0000 : mac8_bias_sum;
                        v3_op4_post2_data_q <=
                            mac8_upper_bias_sum[15] ?
                                16'h0000 : mac8_upper_bias_sum;
                    end
                end
            end
            else begin
                v3_op4_post_valid <= 1'b0;
                v3_op4_post2_valid <= 1'b0;
            end

            if (v3_issue_fire || (v3_tag_count != 5'd0)) begin
                // OP7 always uses the tagged group pair.  Test the opcode
                // before the OP4 low-channel shortcut because
                // v3_op4_split8 depends only on active_channels and is also
                // true during 2..8-channel OP7 execution.
                if (active_opcode == 4'd7) begin
                    v3_retire_bias_lower_q <=
                        bias_bank[v3_bias_prefetch_group];
                    v3_retire_bias_upper_q <=
                        bias_bank[v3_bias_prefetch_group + 3'd4];
                end
                else if (v3_op4_split8) begin
                    v3_retire_bias_lower_q <= bias_bank[0];
                    v3_retire_bias_upper_q <= bias_bank[1];
                end
                else if (active_opcode == 4'd4) begin
                    v3_retire_bias_lower_q <=
                        bias_bank[v3_bias_prefetch_group];
                    v3_retire_bias_upper_q <= 16'd0;
                end
            end

            // Prefetch the next OP2 partial one cycle before it is consumed.
            // This keeps the accumulation at one word per cycle while breaking
            // the distributed-RAM read -> FP16 add -> RAM write path.
            if ((state == ST_OP2_COMPUTE) &&
                (input_feature_counter != 4'd0) &&
                (!mac16_output_valid || (retire_index != 9'd127)))
                partial_word_q <= partial_prefetch_value;

            if (state == ST_OP3_COMPUTE)
                bias_word_q <= bias_prefetch_value;
            else if ((state == ST_OP4_COMPUTE) &&
                     (!mac16_output_valid || (retire_index != 9'd1)))
                bias_word_q <= bias_prefetch_value;
            else if ((state == ST_OP7_COMPUTE) &&
                     (!mac8_output_valid || (retire_index != 9'd7)))
                bias_word_q <= bias_prefetch_value;

            // Pipeline OP2 accumulation before the scratch/feature writeback.
            // Consecutive results still retire at one word per cycle; only one
            // drain cycle is added after each 128-word row.
            if (partial_result_valid_q &&
                (!partial_result_final_q || feature_write_ready))
                partial_result_valid_q <= 1'b0;
            if ((state == ST_OP2_COMPUTE) && mac16_output_valid) begin
                partial_result_valid_q <= 1'b1;
                partial_result_final_q <=
                    (input_feature_counter == 4'd3);
                partial_result_index_q <= retire_index[7:0];
                partial_result_data_q <=
                    (input_feature_counter == 4'd0) ?
                        mac16_result : partial_add_sum;
            end

            // OP0..OP3 share the 128-word ping-pong loader.  Their compute
            // phases are mutually exclusive, so reusing the OP2 counters and
            // the second half of the tile buffer hides the next channel/row
            // read without duplicating storage or control state.
            if (((state == ST_OP0_COMPUTE) ||
                 (state == ST_OP1_COMPUTE) ||
                 (state == ST_OP2_COMPUTE) ||
                 (state == ST_OP3_COMPUTE)) && op2_prefetch_active) begin
                if (feature_read_enable) begin
                    op2_prefetch_issue_index <=
                        op2_prefetch_issue_index + 2'd2;
                    op2_prefetch_address <= op2_prefetch_address + 2'd2;
                end
                if (feature_read_valid && tile_write_ready) begin
                    if (op2_prefetch_receive_index >= 9'd126) begin
                        op2_prefetch_receive_index <= 9'd0;
                        op2_prefetch_active <= 1'b0;
                    end
                    else begin
                        op2_prefetch_receive_index <=
                            op2_prefetch_receive_index + 2'd2;
                    end
                end
            end
            if (((state == ST_OP4_COMPUTE) ||
                 (state == ST_OP5_COMPUTE) ||
                 (state == ST_OP7_COMPUTE) ||
                 (state == ST_OP8_COMPUTE) ||
                 (state == ST_OP4_NEXT)) && op4_prefetch_active) begin
                if (feature_read_enable) begin
                    op4_prefetch_issue_index <=
                        op4_prefetch_issue_index +
                        (((active_opcode == 4'd5) ||
                          (active_opcode == 4'd8)) ? 2'd2 : 1'b1);
                    op4_prefetch_address <=
                        op4_prefetch_address +
                        (((active_opcode == 4'd5) ||
                          (active_opcode == 4'd8)) ?
                            (shared_prefetch_stride << 1) :
                            shared_prefetch_stride);
                end
                if (feature_read_valid && tile_write_ready) begin
                    if (((active_opcode == 4'd5) ||
                         (active_opcode == 4'd8)) &&
                        (op4_prefetch_receive_index == 5'd0))
                        pool_prefetch_word0 <= feature_read_data;
                    if (((active_opcode == 4'd5) ||
                         (active_opcode == 4'd8)) &&
                        (op4_prefetch_receive_index == 5'd0))
                        pool_prefetch_word1 <= feature_read_pair_data;
                    if (op4_prefetch_receive_index ==
                        (shared_prefetch_count -
                         (((active_opcode == 4'd5) ||
                           (active_opcode == 4'd8)) ? 2'd2 : 1'b1))) begin
                        op4_prefetch_receive_index <= 5'd0;
                        op4_prefetch_active <= 1'b0;
                    end
                    else begin
                        op4_prefetch_receive_index <=
                            op4_prefetch_receive_index +
                            (((active_opcode == 4'd5) ||
                              (active_opcode == 4'd8)) ? 2'd2 : 1'b1);
                    end
                end
            end

            if (state == ST_IDLE) begin
                if (op_valid) begin
                    active_opcode <= opcode;
                    source_physical_base <= source_base[12:0];
                    destination_physical_base <= destination_base[12:0];
                    active_parameter_base <= parameter_base;
                    pool_step <= 4'd0;
                    state <= ST_SETUP;
                end
            end
            else if (state == ST_SETUP) begin
                channel_counter <= 5'd0;
                time_counter <= 8'd0;
                input_feature_counter <= 4'd0;
                output_feature_counter <= 4'd0;
                class_counter <= 4'd0;
                case (active_opcode)
                    4'd0: begin
                        parameter_load_base <= active_parameter_base;
                        parameter_load_count <= 7'd16;
                        parameter_load_index <= 7'd0;
                        parameter_load_strided <= 1'b0;
                        return_state <= ST_OP0_ROW;
                        state <= ST_PARAM_LOAD;
                    end
                    4'd1: begin
                        parameter_load_base <= active_parameter_base;
                        parameter_load_count <= 7'd64;
                        parameter_load_index <= 7'd0;
                        parameter_load_strided <= 1'b0;
                        return_state <= ST_OP1_ROW;
                        state <= ST_PARAM_LOAD;
                    end
                    4'd2: begin
                        parameter_load_base <= active_parameter_base;
                        parameter_load_count <= 7'd64;
                        parameter_load_index <= 7'd0;
                        parameter_load_strided <= 1'b0;
                        return_state <= ST_OP2_ROW;
                        state <= ST_PARAM_LOAD;
                    end
                    4'd3: begin
                        parameter_load_base <= active_parameter_base;
                        parameter_load_count <= 7'd68;
                        parameter_load_index <= 7'd0;
                        parameter_load_strided <= 1'b1;
                        return_state <= ST_OP3_ROW;
                        state <= ST_PARAM_LOAD;
                    end
                    4'd4: state <= ST_OP4_PARAM;
                    4'd5: state <= ST_OP5_WINDOW;
                    4'd6: state <= ST_OP6_ROW;
                    4'd7: state <= ST_OP7_PARAM;
                    4'd8: state <= ST_OP8_WINDOW;
                    4'd9: state <= ST_OP9_SOURCE;
                    4'd10: state <= ST_OP10_SOURCE;
                    default: begin
                        op_error <= 1'b1;
                        state <= ST_IDLE;
                    end
                endcase
            end
            else if (state == ST_PARAM_LOAD) begin
                if (!parameter_load_primed) begin
                    parameter_load_primed <= 1'b1;
                end
                else begin
                    if (parameter_load_index + parameter_transfer_count >=
                        parameter_load_count) begin
                        parameter_load_index <= 7'd0;
                        parameter_load_primed <= 1'b0;
                        issue_index <= 9'd0;
                        retire_index <= 9'd0;
                        state <= return_state;
                    end
                    else begin
                        parameter_load_index <=
                            parameter_load_index + parameter_transfer_count;
                    end
                end
            end
            else if (state == ST_FEATURE_REQ) begin
                if (feature_read_enable) begin
                    load_issue_index <= load_issue_index +
                        (load_quad_active ? 3'd4 :
                         load_pair_active ? 2'd2 : 1'b1);
                    if (load_dense_gather) begin
                        if (load_issue_index[2:0] == 3'd7)
                            load_current_address <=
                                load_current_address - 13'd27;
                        else
                            load_current_address <=
                                load_current_address + 13'd4;
                    end
                    else if (load_quad_active) begin
                        load_current_address <=
                        load_current_address + (load_stride << 2'd2);
                    end
                    else if (load_pair_active) begin
                        load_current_address <=
                            load_current_address + (load_stride << 1);
                    end
                    else begin
                        load_current_address <=
                            load_current_address + load_stride;
                    end
                end

                if (feature_read_valid && tile_write_ready) begin
                    if (load_index + (load_quad_active ? 3'd4 :
                                      load_pair_active ? 2'd2 : 1'b1) >=
                        load_count) begin
                        load_index <= 9'd0;
                        load_issue_index <= 9'd0;
                        issue_index <= 9'd0;
                        retire_index <= 9'd0;
                        if ((active_opcode == 4'd5) ||
                            (active_opcode == 4'd8)) begin
                            // Word zero has been resident since the first
                            // response in this window. Capture it while the
                            // final response retires and enter compute without
                            // a dedicated one-cycle PRIME state.
                            pool_accumulator <= tile_read_window[15:0];
                            op6_accumulator <= tile_read_window[31:16];
                            pool_step <= 4'd1;
                        end
                        state <= return_state;
                    end
                    else begin
                        load_index <= load_index +
                            (load_quad_active ? 3'd4 :
                             load_pair_active ? 2'd2 : 1'b1);
                    end
                end
            end
            else begin
                case (state)
                    ST_OP0_ROW: begin
                        load_current_address <= source_physical_base +
                            channel_counter * 13'd128;
                        load_stride <= 13'd1;
                        load_count <= 9'd128;
                        load_index <= 9'd0;
                        load_issue_index <= 9'd0;
                        load_tile_base <= 8'd0;
                        load_dense_gather <= 1'b0;
                        op2_compute_tile_base <= 8'd0;
                        op2_prefetch_active <= 1'b0;
                        op2_prefetch_started <= 1'b0;
                        op0_issue_channel_counter <= 5'd0;
                        op0_issue_complete <= 1'b0;
                        time_counter <= 8'd0;
                        return_state <= ST_OP0_COMPUTE;
                        state <= ST_FEATURE_REQ;
                    end
                    ST_OP0_COMPUTE: begin
                        if (!op2_prefetch_started &&
                            (channel_counter != last_active_channel)) begin
                            op2_prefetch_active <= 1'b1;
                            op2_prefetch_started <= 1'b1;
                            op2_prefetch_issue_index <= 9'd0;
                            op2_prefetch_receive_index <= 9'd0;
                            op2_prefetch_tile_base <=
                                op2_compute_tile_base ^ 8'd128;
                            op2_prefetch_address <=
                                source_physical_base +
                                (channel_counter + 1'b1) * 13'd128;
                        end
                        if (mac16_input_valid) begin
                            if (issue_index == 9'd127) begin
                                issue_index <= 9'd0;
                                if (op0_issue_channel_counter ==
                                    last_active_channel)
                                    op0_issue_complete <= 1'b1;
                                else
                                    op0_issue_channel_counter <=
                                        op0_issue_channel_counter + 1'b1;
                            end
                            else begin
                                issue_index <= issue_index + 1'b1;
                            end
                        end
                        if (mac16_output_valid && feature_write_ready) begin
                            if (retire_index == 9'd127) begin
                                retire_index <= 9'd0;
                                time_counter <= 8'd0;
                            if (channel_counter == last_active_channel) begin
                                op_done <= 1'b1;
                                state <= ST_IDLE;
                            end
                            else begin
                                channel_counter <= channel_counter + 1'b1;
                                op2_compute_tile_base <=
                                    op2_compute_tile_base ^ 8'd128;
                                op2_prefetch_started <= 1'b0;
                                state <= op2_prefetch_active ?
                                    ST_OP2_NEXT : ST_OP0_COMPUTE;
                            end
                        end
                            else retire_index <= retire_index + 1'b1;
                        end
                    end
                    ST_OP1_ROW: begin
                        load_current_address <= source_physical_base +
                            channel_counter * 13'd128;
                        load_stride <= 13'd1;
                        load_count <= 9'd128;
                        load_index <= 9'd0;
                        load_issue_index <= 9'd0;
                        load_tile_base <= 8'd0;
                        load_dense_gather <= 1'b0;
                        op2_compute_tile_base <= 8'd0;
                        op2_prefetch_active <= 1'b0;
                        op2_prefetch_started <= 1'b0;
                        output_feature_counter <= 4'd0;
                        op13_issue_feature_counter <= 2'd0;
                        op13_issue_complete <= 1'b0;
                        return_state <= ST_OP1_COMPUTE;
                        state <= ST_FEATURE_REQ;
                    end
                    ST_OP1_PARAM: begin
                        parameter_load_base <= active_parameter_base +
                            output_feature_counter * 11'd16;
                        parameter_load_count <= 7'd16;
                        parameter_load_index <= 7'd0;
                        parameter_load_strided <= 1'b0;
                        time_counter <= 8'd0;
                        return_state <= ST_OP1_COMPUTE;
                        state <= ST_PARAM_LOAD;
                    end
                    ST_OP1_COMPUTE: begin
                        if (!op2_prefetch_started &&
                            (channel_counter != last_active_channel)) begin
                            op2_prefetch_active <= 1'b1;
                            op2_prefetch_started <= 1'b1;
                            op2_prefetch_issue_index <= 9'd0;
                            op2_prefetch_receive_index <= 9'd0;
                            op2_prefetch_tile_base <=
                                op2_compute_tile_base ^ 8'd128;
                            op2_prefetch_address <=
                                source_physical_base +
                                (channel_counter + 1'b1) * 13'd128;
                        end
                        if (mac16_input_valid) begin
                            if (issue_index == 9'd127) begin
                                issue_index <= 9'd0;
                                if (op13_issue_feature_counter == 2'd3)
                                    op13_issue_complete <= 1'b1;
                                else
                                    op13_issue_feature_counter <=
                                        op13_issue_feature_counter + 1'b1;
                            end
                            else begin
                                issue_index <= issue_index + 1'b1;
                            end
                        end
                        if (mac16_output_valid && feature_write_ready) begin
                            if (retire_index == 9'd127) begin
                                retire_index <= 9'd0;
                                time_counter <= 8'd0;
                            if (output_feature_counter == 4'd3) begin
                                if (channel_counter == last_active_channel) begin
                                    op_done <= 1'b1;
                                    state <= ST_IDLE;
                                end
                                else begin
                                    channel_counter <= channel_counter + 1'b1;
                                    output_feature_counter <= 4'd0;
                                    op13_issue_feature_counter <= 2'd0;
                                    op13_issue_complete <= 1'b0;
                                    op2_compute_tile_base <=
                                        op2_compute_tile_base ^ 8'd128;
                                    op2_prefetch_started <= 1'b0;
                                    state <= op2_prefetch_active ?
                                        ST_OP2_NEXT : ST_OP1_COMPUTE;
                                end
                            end
                            else begin
                                output_feature_counter <= output_feature_counter + 1'b1;
                            end
                        end
                            else retire_index <= retire_index + 1'b1;
                        end
                    end
                    ST_OP2_ROW: begin
                        load_current_address <= source_physical_base +
                            input_feature_counter * 13'd2048 +
                            channel_counter * 13'd128;
                        load_stride <= 13'd1;
                        load_count <= 9'd128;
                        load_index <= 9'd0;
                        load_issue_index <= 9'd0;
                        load_tile_base <= 8'd0;
                        load_dense_gather <= 1'b0;
                        op2_compute_tile_base <= 8'd0;
                        op2_prefetch_active <= 1'b0;
                        op2_prefetch_started <= 1'b0;
                        return_state <= ST_OP2_COMPUTE;
                        state <= ST_FEATURE_REQ;
                    end
                    ST_OP2_PARAM: begin
                        parameter_load_base <= active_parameter_base +
                            input_feature_counter * 11'd16;
                        parameter_load_count <= 7'd16;
                        parameter_load_index <= 7'd0;
                        parameter_load_strided <= 1'b0;
                        time_counter <= 8'd0;
                        return_state <= ST_OP2_COMPUTE;
                        state <= ST_PARAM_LOAD;
                    end
                    ST_OP2_COMPUTE: begin
                        if (!op2_prefetch_started &&
                            !((input_feature_counter == 4'd3) &&
                              (channel_counter == last_active_channel))) begin
                            op2_prefetch_active <= 1'b1;
                            op2_prefetch_started <= 1'b1;
                            op2_prefetch_issue_index <= 9'd0;
                            op2_prefetch_receive_index <= 9'd0;
                            op2_prefetch_tile_base <=
                                op2_compute_tile_base ^ 8'd128;
                            if (input_feature_counter == 4'd3)
                                op2_prefetch_address <=
                                    source_physical_base +
                                    (channel_counter + 1'b1) * 13'd128;
                            else
                                op2_prefetch_address <=
                                    source_physical_base +
                                    (input_feature_counter + 1'b1) *
                                    13'd2048 + channel_counter * 13'd128;
                        end
                        if (mac16_input_valid)
                            issue_index <= issue_index + 1'b1;
                        if (mac16_output_valid) begin
                            if (retire_index == 9'd127) begin
                                issue_index <= 9'd0;
                                retire_index <= 9'd0;
                                time_counter <= 8'd0;
                                state <= ST_OP2_DRAIN;
                            end
                            else retire_index <= retire_index + 1'b1;
                        end
                    end
                    ST_OP2_DRAIN: begin
                        if (partial_result_valid_q &&
                            (!partial_result_final_q ||
                             feature_write_ready)) begin
                            if (input_feature_counter == 4'd3) begin
                                input_feature_counter <= 4'd0;
                                if (channel_counter == last_active_channel) begin
                                    op_done <= 1'b1;
                                    state <= ST_IDLE;
                                end
                                else begin
                                    channel_counter <= channel_counter + 1'b1;
                                    op2_compute_tile_base <=
                                        op2_compute_tile_base ^ 8'd128;
                                    op2_prefetch_started <= 1'b0;
                                    state <= op2_prefetch_active ?
                                        ST_OP2_NEXT : ST_OP2_COMPUTE;
                                end
                            end
                            else begin
                                input_feature_counter <=
                                    input_feature_counter + 1'b1;
                                op2_compute_tile_base <=
                                    op2_compute_tile_base ^ 8'd128;
                                op2_prefetch_started <= 1'b0;
                                state <= op2_prefetch_active ?
                                    ST_OP2_NEXT : ST_OP2_COMPUTE;
                            end
                        end
                    end
                    ST_OP2_NEXT: begin
                        if (!op2_prefetch_active)
                            state <= ST_OP2_COMPUTE;
                    end
                    ST_OP3_ROW: begin
                        load_current_address <= source_physical_base +
                            channel_counter * 13'd128;
                        load_stride <= 13'd1;
                        load_count <= 9'd128;
                        load_index <= 9'd0;
                        load_issue_index <= 9'd0;
                        load_tile_base <= 8'd0;
                        load_dense_gather <= 1'b0;
                        op2_compute_tile_base <= 8'd0;
                        op2_prefetch_active <= 1'b0;
                        op2_prefetch_started <= 1'b0;
                        output_feature_counter <= 4'd0;
                        op13_issue_feature_counter <= 2'd0;
                        op13_issue_complete <= 1'b0;
                        return_state <= ST_OP3_COMPUTE;
                        state <= ST_FEATURE_REQ;
                    end
                    ST_OP3_PARAM: begin
                        parameter_load_base <= active_parameter_base +
                            output_feature_counter * 11'd51;
                        parameter_load_count <= 7'd17;
                        parameter_load_index <= 7'd0;
                        parameter_load_strided <= 1'b0;
                        time_counter <= 8'd0;
                        return_state <= ST_OP3_COMPUTE;
                        state <= ST_PARAM_LOAD;
                    end
                    ST_OP3_COMPUTE: begin
                        if (!op2_prefetch_started &&
                            (channel_counter != last_active_channel)) begin
                            op2_prefetch_active <= 1'b1;
                            op2_prefetch_started <= 1'b1;
                            op2_prefetch_issue_index <= 9'd0;
                            op2_prefetch_receive_index <= 9'd0;
                            op2_prefetch_tile_base <=
                                op2_compute_tile_base ^ 8'd128;
                            op2_prefetch_address <=
                                source_physical_base +
                                (channel_counter + 1'b1) * 13'd128;
                        end
                        if (mac16_input_valid) begin
                            if (issue_index == 9'd127) begin
                                issue_index <= 9'd0;
                                if (op13_issue_feature_counter == 2'd3)
                                    op13_issue_complete <= 1'b1;
                                else
                                    op13_issue_feature_counter <=
                                        op13_issue_feature_counter + 1'b1;
                            end
                            else begin
                                issue_index <= issue_index + 1'b1;
                            end
                        end
                        if (mac16_output_valid && feature_write_ready) begin
                            if (retire_index == 9'd127) begin
                                retire_index <= 9'd0;
                                time_counter <= 8'd0;
                            if (output_feature_counter == 4'd3) begin
                                if (channel_counter == last_active_channel) begin
                                    op_done <= 1'b1;
                                    state <= ST_IDLE;
                                end
                                else begin
                                    channel_counter <= channel_counter + 1'b1;
                                    output_feature_counter <= 4'd0;
                                    op13_issue_feature_counter <= 2'd0;
                                    op13_issue_complete <= 1'b0;
                                    op2_compute_tile_base <=
                                        op2_compute_tile_base ^ 8'd128;
                                    op2_prefetch_started <= 1'b0;
                                    state <= op2_prefetch_active ?
                                        ST_OP2_NEXT : ST_OP3_COMPUTE;
                                end
                            end
                            else begin
                                output_feature_counter <= output_feature_counter + 1'b1;
                            end
                        end
                            else retire_index <= retire_index + 1'b1;
                        end
                    end
                    ST_OP4_PARAM: begin
                        parameter_load_base <= active_parameter_base +
                            input_feature_counter * 11'd51;
                        parameter_load_count <= 7'd34;
                        parameter_load_index <= 7'd0;
                        parameter_load_strided <= 1'b0;
                        time_counter <= 8'd0;
                        return_state <= ST_OP4_SOURCE;
                        state <= ST_PARAM_LOAD;
                    end
                    ST_OP4_SOURCE: begin
                        load_current_address <= source_physical_base +
                            input_feature_counter * 13'd2048 + time_counter;
                        load_stride <= 13'd128;
                        load_count <= op4_channel_load_count;
                        load_index <= 9'd0;
                        load_issue_index <= 9'd0;
                        load_tile_base <= 8'd0;
                        load_dense_gather <= 1'b0;
                        op4_compute_tile_base <= 8'd0;
                        v3_issue_index <= 3'd0;
                        op4_prefetch_active <= 1'b0;
                        op4_prefetch_started <= 1'b0;
                        v3_tag_write_pointer <= 4'd0;
                        v3_tag_read_pointer <= 4'd0;
                        v3_tag_count <= 5'd0;
                        return_state <= ST_OP4_COMPUTE;
                        state <= ST_FEATURE_REQ;
                    end
                    ST_OP4_COMPUTE: begin
                        if (!op4_prefetch_started &&
                            !time_counter[0] &&
                            (time_counter < 8'd126)) begin
                            op4_prefetch_active <= 1'b1;
                            op4_prefetch_started <= 1'b1;
                            op4_prefetch_issue_index <= 5'd0;
                            op4_prefetch_receive_index <= 5'd0;
                            op4_prefetch_tile_base <=
                                op4_compute_tile_base ^ 8'd16;
                            op4_prefetch_address <=
                                source_physical_base +
                                input_feature_counter * 13'd2048 +
                                time_counter + 2'd2;
                        end
                        if (mac16_input_valid)
                            v3_issue_index <= v3_issue_index + 1'b1;
                        if (v3_issue_complete) begin
                            if (time_counter == 8'd127) begin
                                if (v3_pipeline_empty_q) begin
                                    v3_issue_index <= 3'd0;
                                    retire_index <= 9'd0;
                                    if (input_feature_counter == 4'd3) begin
                                        op_done <= 1'b1;
                                        state <= ST_IDLE;
                                    end
                                    else begin
                                        input_feature_counter <=
                                            input_feature_counter + 1'b1;
                                        state <= ST_OP4_PARAM;
                                    end
                                end
                            end
                            else if (!time_counter[0]) begin
                                // The odd partner was returned beside the
                                // current even time and is already resident.
                                time_counter <= time_counter + 1'b1;
                                v3_issue_index <= 3'd0;
                            end
                            else if (v3_prefetch_complete) begin
                                time_counter <= time_counter + 1'b1;
                                v3_issue_index <= 3'd0;
                                op4_compute_tile_base <=
                                    op4_compute_tile_base ^ 8'd16;
                                if (time_counter < 8'd125) begin
                                    // Relaunch on the same edge that retires
                                    // the previous pair, using the tile that
                                    // just became free as the next target.
                                    op4_prefetch_active <= 1'b1;
                                    op4_prefetch_started <= 1'b1;
                                    op4_prefetch_issue_index <= 5'd0;
                                    op4_prefetch_receive_index <= 5'd0;
                                    op4_prefetch_tile_base <=
                                        op4_compute_tile_base;
                                    op4_prefetch_address <=
                                        source_physical_base +
                                        input_feature_counter * 13'd2048 +
                                        time_counter + 2'd3;
                                end
                            end
                        end
                    end
                    ST_OP4_NEXT: begin
                        // The final BRAM response is committed at this edge;
                        // launch the next compute state immediately instead of
                        // spending an extra cycle observing active deasserted.
                        if (!op4_prefetch_active ||
                            (feature_read_valid && tile_write_ready &&
                             (op4_prefetch_receive_index ==
                              (shared_prefetch_count -
                               (((active_opcode == 4'd5) ||
                                 (active_opcode == 4'd8)) ? 2'd2 : 1'b1))))) begin
                            if ((active_opcode == 4'd5) ||
                                (active_opcode == 4'd8)) begin
                                pool_accumulator <= pool_prefetch_word0;
                                op6_accumulator <= pool_prefetch_word1;
                                pool_step <= 4'd1;
                            end
                            case (active_opcode)
                                4'd5: state <= ST_OP5_COMPUTE;
                                4'd7: state <= ST_OP7_COMPUTE;
                                4'd8: state <= ST_OP8_COMPUTE;
                                default: state <= ST_OP4_COMPUTE;
                            endcase
                        end
                    end
                    ST_OP5_WINDOW: begin
                        load_current_address <= source_physical_base +
                            output_feature_counter * 13'd128 +
                            time_counter * 13'd4;
                        load_stride <= 13'd1;
                        load_count <= 9'd4;
                        load_index <= 9'd0;
                        load_issue_index <= 9'd0;
                        load_tile_base <= 8'd0;
                        load_dense_gather <= 1'b0;
                        op4_compute_tile_base <= 8'd0;
                        op4_prefetch_active <= 1'b0;
                        op4_prefetch_started <= 1'b0;
                        return_state <= ST_OP5_COMPUTE;
                        state <= ST_FEATURE_REQ;
                    end
                    ST_OP5_COMPUTE: begin
                        if (!op4_prefetch_started &&
                            !((output_feature_counter == 4'd7) &&
                              (time_counter == 8'd31))) begin
                            op4_prefetch_active <= 1'b1;
                            op4_prefetch_started <= 1'b1;
                            op4_prefetch_issue_index <= 5'd0;
                            op4_prefetch_receive_index <= 5'd0;
                            op4_prefetch_tile_base <=
                                op4_compute_tile_base ^ 8'd16;
                            if (time_counter == 8'd31)
                                op4_prefetch_address <=
                                    source_physical_base +
                                    (output_feature_counter + 1'b1) * 13'd128;
                            else
                                op4_prefetch_address <=
                                    source_physical_base +
                                    output_feature_counter * 13'd128 +
                                    (time_counter + 1'b1) * 13'd4;
                        end
                        if (pool_step == 4'd4) begin
                            if (feature_write_ready) begin
                                pool_step <= 4'd0;
                                if (time_counter == 8'd31) begin
                                    time_counter <= 8'd0;
                                    if (output_feature_counter == 4'd7) begin
                                        op_done <= 1'b1;
                                        state <= ST_IDLE;
                                    end
                                    else begin
                                        output_feature_counter <=
                                            output_feature_counter + 1'b1;
                                        pool_accumulator <= pool_prefetch_word0;
                                        op6_accumulator <= pool_prefetch_word1;
                                        pool_step <= 4'd1;
                                        op4_compute_tile_base <=
                                            op4_compute_tile_base ^ 8'd16;
                                        op4_prefetch_started <= 1'b0;
                                        state <= op4_prefetch_active ?
                                            ST_OP4_NEXT : ST_OP5_COMPUTE;
                                    end
                                end
                                else begin
                                    time_counter <= time_counter + 1'b1;
                                    pool_accumulator <= pool_prefetch_word0;
                                    op6_accumulator <= pool_prefetch_word1;
                                    pool_step <= 4'd1;
                                    op4_compute_tile_base <=
                                        op4_compute_tile_base ^ 8'd16;
                                    op4_prefetch_started <= 1'b0;
                                    state <= op4_prefetch_active ?
                                        ST_OP4_NEXT : ST_OP5_COMPUTE;
                                end
                            end
                        end
                        else if (pool_step == 4'd0) begin
                            pool_accumulator <= op6_accumulator;
                            op6_accumulator <= pool_selected_word;
                            pool_step <= 4'd1;
                        end
                        else begin
                            pool_accumulator <= pool_add_sum;
                            op6_accumulator <= pool_selected_word;
                            pool_step <= pool_step + 1'b1;
                        end
                    end
                    ST_OP6_PARAM: begin
                        parameter_load_base <= active_parameter_base +
                            output_feature_counter * 11'd16;
                        parameter_load_count <= 7'd16;
                        parameter_load_index <= 7'd0;
                        parameter_load_strided <= 1'b0;
                        time_counter <= 8'd0;
                        op6_issue_time_counter <= 8'd0;
                        op6_issue_complete <= 1'b0;
                        input_feature_counter <= 4'd0;
                        return_state <= ST_OP6_COMPUTE;
                        state <= ST_PARAM_LOAD;
                    end
                    ST_OP6_ROW: begin
                        load_current_address <= source_physical_base;
                        load_stride <= 13'd1;
                        load_count <= 9'd256;
                        load_index <= 9'd0;
                        load_issue_index <= 9'd0;
                        load_tile_base <= 8'd0;
                        load_dense_gather <= 1'b0;
                        output_feature_counter <= 4'd0;
                        return_state <= ST_OP6_PARAM;
                        state <= ST_FEATURE_REQ;
                    end
                    ST_OP6_COMPUTE: begin
                        // Keep the shared MAC pipeline full across all 32 time
                        // points for one output feature.  Retirement keeps its
                        // own time counter, so only a weight change drains the
                        // pipeline instead of every eight-input accumulation.
                        if (mac16_input_valid) begin
                            if (issue_index == 9'd7) begin
                                issue_index <= 9'd0;
                                if (op6_issue_time_counter == 8'd31)
                                    op6_issue_complete <= 1'b1;
                                else
                                    op6_issue_time_counter <=
                                        op6_issue_time_counter + 1'b1;
                            end
                            else begin
                                issue_index <= issue_index + 1'b1;
                            end
                        end
                        if (mac16_output_valid &&
                            ((retire_index != 9'd7) ||
                             feature_write_ready)) begin
                            if (retire_index == 9'd0)
                                op6_accumulator <= mac16_result;
                            else
                                op6_accumulator <= op6_add_sum;

                            if (retire_index == 9'd7) begin
                            retire_index <= 9'd0;
                            input_feature_counter <= 4'd0;
                            if (time_counter == 8'd31) begin
                                if (output_feature_counter == 4'd7) begin
                                    op_done <= 1'b1;
                                    state <= ST_IDLE;
                                end
                                else begin
                                    output_feature_counter <= output_feature_counter + 1'b1;
                                    state <= ST_OP6_PARAM;
                                end
                            end
                            else begin
                                time_counter <= time_counter + 1'b1;
                            end
                        end
                        else begin
                                retire_index <= retire_index + 1'b1;
                                input_feature_counter <=
                                    retire_index[3:0] + 1'b1;
                            end
                        end
                    end
                    ST_OP7_PARAM: begin
                        parameter_load_base <= active_parameter_base;
                        parameter_load_count <= 7'd72;
                        parameter_load_index <= 7'd0;
                        parameter_load_strided <= 1'b0;
                        return_state <= ST_OP7_SOURCE;
                        state <= ST_PARAM_LOAD;
                    end
                    ST_OP7_SOURCE: begin
                        // OP6 populated the time-major local cache, so OP7
                        // enters compute without a feature-memory gather.
                        time_counter <= 8'd0;
                        op4_compute_tile_base <= 8'd0;
                        v3_issue_index <= 3'd0;
                        op4_prefetch_active <= 1'b0;
                        op4_prefetch_started <= 1'b0;
                        v3_tag_write_pointer <= 4'd0;
                        v3_tag_read_pointer <= 4'd0;
                        v3_tag_count <= 5'd0;
                        output_feature_counter <= 4'd0;
                        state <= ST_OP7_COMPUTE;
                    end
                    ST_OP7_COMPUTE: begin
                        if (mac16_input_valid)
                            v3_issue_index <= v3_issue_index + 1'b1;
                        if (v3_issue_complete) begin
                            if (time_counter == 8'd31) begin
                                if (v3_pipeline_empty_q) begin
                                    v3_issue_index <= 3'd0;
                                    retire_index <= 9'd0;
                                    output_feature_counter <= 4'd0;
                                    op_done <= 1'b1;
                                    state <= ST_IDLE;
                                end
                            end
                            else begin
                                time_counter <= time_counter + 1'b1;
                                v3_issue_index <= 3'd0;
                            end
                        end
                    end
                    ST_OP8_WINDOW: begin
                        load_current_address <= source_physical_base +
                            output_feature_counter * 13'd32 +
                            time_counter * 13'd8;
                        load_stride <= 13'd1;
                        load_count <= 9'd8;
                        load_index <= 9'd0;
                        load_issue_index <= 9'd0;
                        load_tile_base <= 8'd0;
                        load_dense_gather <= 1'b0;
                        op4_compute_tile_base <= 8'd0;
                        op4_prefetch_active <= 1'b0;
                        op4_prefetch_started <= 1'b0;
                        return_state <= ST_OP8_COMPUTE;
                        state <= ST_FEATURE_REQ;
                    end
                    ST_OP8_COMPUTE: begin
                        if (!op4_prefetch_started &&
                            !((output_feature_counter == 4'd7) &&
                              (time_counter == 8'd3))) begin
                            op4_prefetch_active <= 1'b1;
                            op4_prefetch_started <= 1'b1;
                            op4_prefetch_issue_index <= 5'd0;
                            op4_prefetch_receive_index <= 5'd0;
                            op4_prefetch_tile_base <=
                                op4_compute_tile_base ^ 8'd16;
                            if (time_counter == 8'd3)
                                op4_prefetch_address <=
                                    source_physical_base +
                                    (output_feature_counter + 1'b1) * 13'd32;
                            else
                                op4_prefetch_address <=
                                    source_physical_base +
                                    output_feature_counter * 13'd32 +
                                    (time_counter + 1'b1) * 13'd8;
                        end
                        if (pool_step == 4'd8) begin
                            if (feature_write_ready) begin
                                pool_step <= 4'd0;
                                if (time_counter == 8'd3) begin
                                    time_counter <= 8'd0;
                                    if (output_feature_counter == 4'd7) begin
                                        op_done <= 1'b1;
                                        state <= ST_IDLE;
                                    end
                                    else begin
                                        output_feature_counter <=
                                            output_feature_counter + 1'b1;
                                        pool_accumulator <= pool_prefetch_word0;
                                        op6_accumulator <= pool_prefetch_word1;
                                        pool_step <= 4'd1;
                                        op4_compute_tile_base <=
                                            op4_compute_tile_base ^ 8'd16;
                                        op4_prefetch_started <= 1'b0;
                                        state <= op4_prefetch_active ?
                                            ST_OP4_NEXT : ST_OP8_COMPUTE;
                                    end
                                end
                                else begin
                                    time_counter <= time_counter + 1'b1;
                                    pool_accumulator <= pool_prefetch_word0;
                                    op6_accumulator <= pool_prefetch_word1;
                                    pool_step <= 4'd1;
                                    op4_compute_tile_base <=
                                        op4_compute_tile_base ^ 8'd16;
                                    op4_prefetch_started <= 1'b0;
                                    state <= op4_prefetch_active ?
                                        ST_OP4_NEXT : ST_OP8_COMPUTE;
                                end
                            end
                        end
                        else if (pool_step == 4'd0) begin
                            pool_accumulator <= op6_accumulator;
                            op6_accumulator <= pool_selected_word;
                            pool_step <= 4'd1;
                        end
                        else begin
                            pool_accumulator <= pool_add_sum;
                            op6_accumulator <= pool_selected_word;
                            pool_step <= pool_step + 1'b1;
                        end
                    end
                    ST_OP9_SOURCE: begin
                        load_current_address <= source_physical_base;
                        load_stride <= 13'd1;
                        load_count <= 9'd32;
                        load_index <= 9'd0;
                        load_issue_index <= 9'd0;
                        load_tile_base <= 8'd0;
                        load_dense_gather <= 1'b1;
                        return_state <= ST_OP9_PARAM;
                        state <= ST_FEATURE_REQ;
                    end
                    ST_OP9_PARAM: begin
                        parameter_load_base <= active_parameter_base +
                            class_counter * 11'd33;
                        parameter_load_count <= 7'd33;
                        parameter_load_index <= 7'd0;
                        parameter_load_strided <= 1'b0;
                        return_state <= ST_OP9_COMPUTE;
                        state <= ST_PARAM_LOAD;
                    end
                    ST_OP9_COMPUTE: begin
                        if (mac16_input_valid)
                            issue_index <= issue_index + 1'b1;
                        if (mac16_output_valid) begin
                            if (retire_index == 9'd0) begin
                                dense_lower_result <= mac16_result;
                                retire_index <= 9'd1;
                            end
                            else begin
                                dense_pair_result <= dense_pair_sum;
                                state <= ST_OP9_BIAS;
                            end
                        end
                    end
                    ST_OP9_BIAS: if (feature_write_ready) begin
                        issue_index <= 9'd0;
                        retire_index <= 9'd0;
                        if (class_counter == 4'd15) begin
                            op_done <= 1'b1;
                            state <= ST_IDLE;
                        end
                        else begin
                            class_counter <= class_counter + 1'b1;
                            state <= ST_OP9_PARAM;
                        end
                    end
                    ST_OP10_SOURCE: begin
                        load_current_address <= source_physical_base +
                            class_counter;
                        load_stride <= 13'd1;
                        load_count <= 9'd1;
                        load_index <= 9'd0;
                        load_issue_index <= 9'd0;
                        load_tile_base <= 8'd0;
                        load_dense_gather <= 1'b0;
                        return_state <= ST_OP10_SCORE;
                        state <= ST_FEATURE_REQ;
                    end
                    ST_OP10_SCORE: if (score_ready) begin
                        if (class_counter == 4'd15) begin
                            op_done <= 1'b1;
                            state <= ST_IDLE;
                        end
                        else begin
                            class_counter <= class_counter + 1'b1;
                            state <= ST_OP10_SOURCE;
                        end
                    end
                    default: begin
                        op_error <= 1'b1;
                        state <= ST_IDLE;
                    end
                endcase
            end
        end
    end
endmodule
`default_nettype wire
