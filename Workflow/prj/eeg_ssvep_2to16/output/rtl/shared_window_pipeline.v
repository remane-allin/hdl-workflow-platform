// -----------------------------------------------------------------------------
// Module: shared_window_pipeline
// Description: Profile-independent SAME_PAD rolling window with one bounded
//              metadata look-ahead descriptor.
// Scope:
//   - Owns one APX-resident rolling window and reloads it through port A.
//   - Queues only the next descriptor metadata; sample payload is never
//     duplicated into a second 256-bit resident.
//   - Issues one tagged multiply-reduce request per cycle once primed.
//   - Owns no profile decode, parameter storage, accumulation, or retire path.
// Spec Trace: REQ-RRB-006, REQ-RRB-007, REQ-RRB-010, REQ-RRB-019
// -----------------------------------------------------------------------------

`timescale 1ns/1ps
`default_nettype none

module shared_window_pipeline (
    input  wire         clk,
    input  wire         reset_n,
    input  wire         start_valid,
    output reg          start_ready,
    input  wire [4:0]   start_lanes,
    input  wire [11:0]  start_output_count,
    input  wire [12:0]  start_source_base,
    input  wire [12:0]  start_source_stride,
    input  wire [15:0]  start_tag_base,
    input  wire         start_weight_select,
    input  wire         start_weight_zero,

    output reg          feature_read_a_valid,
    input  wire         feature_read_a_ready,
    output reg  [12:0]  feature_read_a_address,
    input  wire         feature_read_a_response_valid,
    input  wire [15:0]  feature_read_a_response_data,

    output reg          apx_request_valid,
    input  wire         apx_request_ready,
    output reg  [1:0]   apx_request_operation,
    output reg  [4:0]   apx_request_lanes,
    output reg  [15:0]  apx_request_tag,
    output reg          apx_window_shift,
    output reg  [15:0]  apx_window_sample,
    output reg          apx_weight_select,
    output reg          apx_weight_zero,
    output reg          window_resident_clear_valid,
    output reg          window_resident_seed_valid,
    output reg  [4:0]   window_resident_seed_lanes,
    output reg  [15:0]  window_resident_seed_data,
    input  wire         apx_reduce_valid,
    input  wire [15:0]  apx_reduce_tag,
    input  wire [15:0]  apx_reduce_result,
    output wire         result_valid,
    output wire [15:0]  result_tag,
    output wire [15:0]  result_data,
    output reg          done
);
    localparam [2:0] STATE_IDLE         = 3'd0;
    localparam [2:0] STATE_INITIAL_LOAD = 3'd1;
    localparam [2:0] STATE_FIRST_ISSUE  = 3'd2;
    localparam [2:0] STATE_STREAM       = 3'd3;
    localparam [2:0] STATE_WAIT_QUEUE   = 3'd4;
    localparam [1:0] APX_MULTIPLY_REDUCE = 2'd0;

    reg [2:0] state_q, state_d;
    reg [4:0] lanes_q, lanes_d;
    reg [11:0] output_count_q, output_count_d;
    reg [12:0] source_stride_q, source_stride_d;
    reg [15:0] tag_base_q, tag_base_d;
    reg weight_select_q, weight_select_d;
    reg weight_zero_q, weight_zero_d;

    reg [4:0] initial_word_count_q, initial_word_count_d;
    reg [4:0] load_issued_count_q, load_issued_count_d;
    reg [4:0] load_returned_count_q, load_returned_count_d;
    reg [12:0] load_next_address_q, load_next_address_d;
    reg load_waiting_q, load_waiting_d;

    reg sample_pending_q, sample_pending_d;
    reg sample_memory_q, sample_memory_d;
    reg [11:0] sample_output_index_q, sample_output_index_d;
    reg [15:0] sample_data_q, sample_data_d;
    reg sample_data_valid_q, sample_data_valid_d;
    reg [11:0] next_output_index_q, next_output_index_d;
    reg [12:0] next_sample_index_q, next_sample_index_d;
    reg [12:0] stream_next_address_q, stream_next_address_d;

    reg queue_valid_q, queue_valid_d;
    reg [4:0] queue_lanes_q, queue_lanes_d;
    reg [11:0] queue_output_count_q, queue_output_count_d;
    reg [12:0] queue_source_base_q, queue_source_base_d;
    reg [12:0] queue_source_stride_q, queue_source_stride_d;
    reg [15:0] queue_tag_base_q, queue_tag_base_d;
    reg queue_weight_select_q, queue_weight_select_d;
    reg queue_weight_zero_q, queue_weight_zero_d;

    reg [11:0] result_returned_count_q, result_returned_count_d;
    reg result_active_q, result_active_d;
    reg [11:0] result_output_count_q, result_output_count_d;
    reg result_pending_q, result_pending_d;
    reg [11:0] result_pending_count_q, result_pending_count_d;

    reg initial_issue;

    wire signed [13:0] signed_stride;
    wire raw_sample_valid;
    wire [15:0] raw_sample_data;
    wire sample_available;
    wire [15:0] selected_sample_data;
    wire load_response_complete;
    wire stream_apx_fire;
    wire stream_slot_available;
    wire schedule_stream_event;
    wire schedule_memory_read;
    wire start_fire;
    wire result_last_return;

    assign signed_stride = {source_stride_q[12], source_stride_q};
    assign raw_sample_valid = feature_read_a_response_valid;
    assign raw_sample_data = feature_read_a_response_data;
    assign sample_available = sample_pending_q &&
        (!sample_memory_q || sample_data_valid_q || raw_sample_valid);
    assign selected_sample_data = sample_memory_q ?
        (sample_data_valid_q ? sample_data_q : raw_sample_data) : 16'd0;
    assign load_response_complete = load_waiting_q &&
        feature_read_a_response_valid;
    assign stream_apx_fire = (state_q == STATE_STREAM) &&
        sample_available && apx_request_ready;
    assign stream_slot_available = !sample_pending_q || stream_apx_fire;
    assign schedule_stream_event = (state_q == STATE_STREAM) &&
        stream_slot_available &&
        (next_output_index_q < output_count_q) &&
        ((next_sample_index_q >= {1'b0, output_count_q}) ||
         feature_read_a_ready);
    assign schedule_memory_read = schedule_stream_event &&
        (next_sample_index_q < {1'b0, output_count_q});
    assign start_fire = start_valid && start_ready;
    assign result_last_return = apx_reduce_valid && result_active_q &&
        ((result_returned_count_q + 12'd1) >= result_output_count_q);
    assign result_valid = apx_reduce_valid;
    assign result_tag = apx_reduce_tag;
    assign result_data = apx_reduce_result;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            state_q <= STATE_IDLE;
            lanes_q <= 5'd0;
            output_count_q <= 12'd0;
            source_stride_q <= 13'd0;
            tag_base_q <= 16'd0;
            weight_select_q <= 1'b0;
            weight_zero_q <= 1'b0;
            initial_word_count_q <= 5'd0;
            load_issued_count_q <= 5'd0;
            load_returned_count_q <= 5'd0;
            load_next_address_q <= 13'd0;
            load_waiting_q <= 1'b0;
            sample_pending_q <= 1'b0;
            sample_memory_q <= 1'b0;
            sample_output_index_q <= 12'd0;
            sample_data_q <= 16'd0;
            sample_data_valid_q <= 1'b0;
            next_output_index_q <= 12'd0;
            next_sample_index_q <= 13'd0;
            stream_next_address_q <= 13'd0;
            queue_valid_q <= 1'b0;
            queue_lanes_q <= 5'd0;
            queue_output_count_q <= 12'd0;
            queue_source_base_q <= 13'd0;
            queue_source_stride_q <= 13'd0;
            queue_tag_base_q <= 16'd0;
            queue_weight_select_q <= 1'b0;
            queue_weight_zero_q <= 1'b0;
            result_returned_count_q <= 12'd0;
            result_active_q <= 1'b0;
            result_output_count_q <= 12'd0;
            result_pending_q <= 1'b0;
            result_pending_count_q <= 12'd0;
        end
        else begin
            state_q <= state_d;
            lanes_q <= lanes_d;
            output_count_q <= output_count_d;
            source_stride_q <= source_stride_d;
            tag_base_q <= tag_base_d;
            weight_select_q <= weight_select_d;
            weight_zero_q <= weight_zero_d;
            initial_word_count_q <= initial_word_count_d;
            load_issued_count_q <= load_issued_count_d;
            load_returned_count_q <= load_returned_count_d;
            load_next_address_q <= load_next_address_d;
            load_waiting_q <= load_waiting_d;
            sample_pending_q <= sample_pending_d;
            sample_memory_q <= sample_memory_d;
            sample_output_index_q <= sample_output_index_d;
            sample_data_q <= sample_data_d;
            sample_data_valid_q <= sample_data_valid_d;
            next_output_index_q <= next_output_index_d;
            next_sample_index_q <= next_sample_index_d;
            stream_next_address_q <= stream_next_address_d;
            queue_valid_q <= queue_valid_d;
            queue_lanes_q <= queue_lanes_d;
            queue_output_count_q <= queue_output_count_d;
            queue_source_base_q <= queue_source_base_d;
            queue_source_stride_q <= queue_source_stride_d;
            queue_tag_base_q <= queue_tag_base_d;
            queue_weight_select_q <= queue_weight_select_d;
            queue_weight_zero_q <= queue_weight_zero_d;
            result_returned_count_q <= result_returned_count_d;
            result_active_q <= result_active_d;
            result_output_count_q <= result_output_count_d;
            result_pending_q <= result_pending_d;
            result_pending_count_q <= result_pending_count_d;
        end
    end

    always @(*) begin
        state_d = state_q;
        lanes_d = lanes_q;
        output_count_d = output_count_q;
        source_stride_d = source_stride_q;
        tag_base_d = tag_base_q;
        weight_select_d = weight_select_q;
        weight_zero_d = weight_zero_q;
        initial_word_count_d = initial_word_count_q;
        load_issued_count_d = load_issued_count_q;
        load_returned_count_d = load_returned_count_q;
        load_next_address_d = load_next_address_q;
        load_waiting_d = load_waiting_q;
        sample_pending_d = sample_pending_q;
        sample_memory_d = sample_memory_q;
        sample_output_index_d = sample_output_index_q;
        sample_data_d = sample_data_q;
        sample_data_valid_d = sample_data_valid_q;
        next_output_index_d = next_output_index_q;
        next_sample_index_d = next_sample_index_q;
        stream_next_address_d = stream_next_address_q;
        queue_valid_d = queue_valid_q;
        queue_lanes_d = queue_lanes_q;
        queue_output_count_d = queue_output_count_q;
        queue_source_base_d = queue_source_base_q;
        queue_source_stride_d = queue_source_stride_q;
        queue_tag_base_d = queue_tag_base_q;
        queue_weight_select_d = queue_weight_select_q;
        queue_weight_zero_d = queue_weight_zero_q;
        result_returned_count_d = result_returned_count_q;
        result_active_d = result_active_q;
        result_output_count_d = result_output_count_q;
        result_pending_d = result_pending_q;
        result_pending_count_d = result_pending_count_q;

        if (result_last_return) begin
            if (result_pending_q) begin
                result_active_d = 1'b1;
                result_output_count_d = result_pending_count_q;
                result_returned_count_d = 12'd0;
                result_pending_d = 1'b0;
            end
            else begin
                result_returned_count_d = 12'd0;
                result_active_d = 1'b0;
            end
        end
        else if (apx_reduce_valid && result_active_q) begin
            result_returned_count_d = result_returned_count_q + 12'd1;
        end

        if (start_fire) begin
            if (state_q == STATE_IDLE) begin
                lanes_d = start_lanes;
                output_count_d = start_output_count;
                source_stride_d = start_source_stride;
                tag_base_d = start_tag_base;
                weight_select_d = start_weight_select;
                weight_zero_d = start_weight_zero;
                initial_word_count_d = start_lanes -
                    ((start_lanes - 5'd1) >> 1);
                load_issued_count_d = 5'd0;
                load_returned_count_d = 5'd0;
                load_next_address_d = start_source_base;
                load_waiting_d = 1'b0;
                sample_pending_d = 1'b0;
                sample_data_valid_d = 1'b0;
                result_returned_count_d = 12'd0;
                result_active_d = 1'b0;
                result_pending_d = 1'b0;
                state_d = STATE_INITIAL_LOAD;
            end
            else begin
                queue_valid_d = 1'b1;
                queue_lanes_d = start_lanes;
                queue_output_count_d = start_output_count;
                queue_source_base_d = start_source_base;
                queue_source_stride_d = start_source_stride;
                queue_tag_base_d = start_tag_base;
                queue_weight_select_d = start_weight_select;
                queue_weight_zero_d = start_weight_zero;
            end
        end

        if ((state_q == STATE_INITIAL_LOAD) && load_response_complete) begin
            load_returned_count_d = load_returned_count_q + 5'd1;
            load_waiting_d = 1'b0;
        end
        if ((state_q == STATE_INITIAL_LOAD) && initial_issue) begin
            load_issued_count_d = load_issued_count_q + 5'd1;
            load_waiting_d = 1'b1;
            load_next_address_d = load_next_address_q + signed_stride;
        end
        if ((state_q == STATE_INITIAL_LOAD) &&
            (load_issued_count_d >= initial_word_count_q) &&
            (load_returned_count_d >= initial_word_count_q) &&
            !load_waiting_d) begin
            state_d = STATE_FIRST_ISSUE;
        end

        case (state_q)
            STATE_FIRST_ISSUE: begin
                if (!result_pending_q && apx_request_ready) begin
                    if (!result_active_d) begin
                        result_active_d = 1'b1;
                        result_output_count_d = output_count_q;
                        result_returned_count_d = 12'd0;
                    end
                    else begin
                        result_pending_d = 1'b1;
                        result_pending_count_d = output_count_q;
                    end
                    if (output_count_q <= 12'd1) begin
                        state_d = STATE_WAIT_QUEUE;
                    end
                    else begin
                        sample_pending_d = 1'b0;
                        sample_data_valid_d = 1'b0;
                        next_output_index_d = 12'd1;
                        next_sample_index_d = {8'd0, initial_word_count_q};
                        stream_next_address_d = load_next_address_q;
                        state_d = STATE_STREAM;
                    end
                end
            end

            STATE_STREAM: begin
                if (sample_pending_q && sample_memory_q &&
                    raw_sample_valid && !sample_data_valid_q) begin
                    sample_data_d = raw_sample_data;
                    sample_data_valid_d = 1'b1;
                end
                if (stream_apx_fire) begin
                    sample_pending_d = 1'b0;
                    sample_data_valid_d = 1'b0;
                end
                if (schedule_stream_event) begin
                    sample_pending_d = 1'b1;
                    sample_memory_d = schedule_memory_read;
                    sample_output_index_d = next_output_index_q;
                    sample_data_d = 16'd0;
                    sample_data_valid_d = 1'b0;
                    next_output_index_d = next_output_index_q + 12'd1;
                    next_sample_index_d = next_sample_index_q + 13'd1;
                    stream_next_address_d = stream_next_address_q +
                        signed_stride;
                end
                if (stream_apx_fire &&
                    ((sample_output_index_q + 12'd1) >= output_count_q) &&
                    !schedule_stream_event) begin
                    state_d = STATE_WAIT_QUEUE;
                end
            end

            STATE_WAIT_QUEUE: begin
                // The queued payload is metadata only.  It becomes active by
                // reloading the single resident before any new APX command.
                if (queue_valid_d) begin
                    lanes_d = queue_lanes_d;
                    output_count_d = queue_output_count_d;
                    source_stride_d = queue_source_stride_d;
                    tag_base_d = queue_tag_base_d;
                    weight_select_d = queue_weight_select_d;
                    weight_zero_d = queue_weight_zero_d;
                    initial_word_count_d = queue_lanes_d -
                        ((queue_lanes_d - 5'd1) >> 1);
                    load_issued_count_d = 5'd0;
                    load_returned_count_d = 5'd0;
                    load_next_address_d = queue_source_base_d;
                    load_waiting_d = 1'b0;
                    sample_pending_d = 1'b0;
                    sample_data_valid_d = 1'b0;
                    queue_valid_d = 1'b0;
                    state_d = STATE_INITIAL_LOAD;
                end
                // Return completion crosses a register boundary before it
                // releases the issue FSM.  Using the registered state here
                // prevents the result counter/comparator from driving the
                // encoded state register in the same cycle.
                else if (!result_active_q && !result_pending_q) begin
                    state_d = STATE_IDLE;
                end
            end

            default: begin
            end
        endcase
    end

    always @(*) begin
        start_ready = (state_q == STATE_IDLE) ||
            (!queue_valid_q && !result_pending_q &&
             (state_q != STATE_INITIAL_LOAD));
        done = result_last_return;
        feature_read_a_valid = 1'b0;
        feature_read_a_address = 13'd0;
        apx_request_valid = 1'b0;
        apx_request_operation = APX_MULTIPLY_REDUCE;
        apx_request_lanes = lanes_q;
        apx_request_tag = tag_base_q;
        apx_window_shift = 1'b0;
        apx_window_sample = 16'd0;
        apx_weight_select = weight_select_q;
        apx_weight_zero = weight_zero_q;
        window_resident_clear_valid = 1'b0;
        window_resident_seed_valid = 1'b0;
        window_resident_seed_lanes = lanes_q;
        window_resident_seed_data = 16'd0;
        initial_issue = 1'b0;

        if ((state_q == STATE_INITIAL_LOAD) &&
            (load_issued_count_q == 5'd0) &&
            (load_returned_count_q == 5'd0)) begin
            window_resident_clear_valid = 1'b1;
        end

        if ((state_q == STATE_INITIAL_LOAD) && load_response_complete) begin
            window_resident_seed_valid = 1'b1;
            window_resident_seed_data = feature_read_a_response_data;
        end

        if ((state_q == STATE_INITIAL_LOAD) &&
            (!load_waiting_q || load_response_complete) &&
            (load_issued_count_q < initial_word_count_q) &&
            feature_read_a_ready) begin
            initial_issue = 1'b1;
            feature_read_a_valid = 1'b1;
            feature_read_a_address = load_next_address_q;
        end

        if (schedule_memory_read) begin
            feature_read_a_valid = 1'b1;
            feature_read_a_address = stream_next_address_q;
        end

        if ((state_q == STATE_FIRST_ISSUE) && !result_pending_q) begin
            apx_request_valid = 1'b1;
            apx_request_tag = tag_base_q;
        end
        else if ((state_q == STATE_STREAM) && sample_available) begin
            apx_request_valid = 1'b1;
            apx_request_tag = tag_base_q + {4'd0, sample_output_index_q};
            apx_window_shift = 1'b1;
            apx_window_sample = selected_sample_data;
        end
    end
endmodule
`default_nettype wire
