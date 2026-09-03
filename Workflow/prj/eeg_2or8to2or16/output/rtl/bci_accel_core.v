// Module: bci_accel_core
// Description: Integrates scheduling, memory, datapath, and classification.
// Scope: Frozen CH16_S128_BASE16_LEGACY_FP16 accelerator core.
// Spec Trace: REQ-EEG-ARCH-001, REQ-EEG-CH16-001,
//             REQ-EEG-V3-OPT-001, REQ-EEG-V3-OPT-002.
`timescale 1ns/1ps
`default_nettype none

module bci_accel_core (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        stream_valid,
    output wire        stream_ready,
    input  wire [15:0] stream_data,
    input  wire [2:0]  stream_type,
    input  wire        stream_last,
    input  wire        command_valid,
    output wire        command_ready,
    input  wire [1:0]  profile_select,
    input  wire [1:0]  instruction_version,
    output wire        busy,
    output wire [31:0] result,
    output wire        infer_done,
    output wire [3:0]  class_led,
    output wire        error,
    input  wire        clear_counters,
    input  wire        snapshot_counters,
    output reg  [31:0] total_cycles_snapshot,
    output reg  [31:0] memory_stalls_snapshot,
    output reg  [31:0] producer_stalls_snapshot,
    output reg  [31:0] consumer_stalls_snapshot,
    output reg  [31:0] mac_activity_snapshot,
    output reg  [31:0] tile_occupancy_snapshot,
    output wire        trace_write_valid,
    output wire [3:0]  trace_opcode,
    output wire [12:0] trace_write_address,
    output wire [15:0] trace_write_data,
    output wire        trace_write2_valid,
    output wire [12:0] trace_write2_address,
    output wire [15:0] trace_write2_data
);
    wire sample_stream_selected = (stream_type == 3'b101);
    wire scheduler_load_valid = stream_valid &&
        ((stream_type == 3'b011) || (stream_type == 3'b110));
    wire sample_ready;
    wire scheduler_load_ready;
    wire sample_loaded;
    wire [12:0] sample_count;
    wire [10:0] parameter_word_count;
    wire [8:0] instruction_word_count;
    wire [4:0] active_channels;
    wire [12:0] expected_sample_words;
    wire channel_config_valid;

    wire op_valid;
    wire op_ready;
    wire [3:0] opcode;
    wire [7:0] descriptor_index;
    wire [13:0] source_base;
    wire [13:0] destination_base;
    wire [10:0] parameter_base;
    wire op_done;
    wire op_error;
    wire all_done;
    wire scheduler_error;
    wire [10:0] parameter_read_address;
    wire [63:0] parameter_read_data;

    wire feature_read_enable;
    wire feature_read_pair_enable;
    wire feature_read_quad_enable;
    wire [12:0] feature_read_address;
    wire feature_read_valid;
    wire [15:0] feature_read_data;
    wire [15:0] feature_read_pair_data;
    wire [15:0] feature_read_quad_data2;
    wire [15:0] feature_read_quad_data3;
    wire [15:0] feature_read_oct_data4;
    wire [15:0] feature_read_oct_data5;
    wire [15:0] feature_read_oct_data6;
    wire [15:0] feature_read_oct_data7;
    wire feature_write_valid;
    wire feature_write_ready;
    wire [12:0] feature_write_address;
    wire [15:0] feature_write_data;
    wire feature_write2_valid;
    wire feature_write2_ready;
    wire [12:0] feature_write2_address;
    wire [15:0] feature_write2_data;
    reg feature_commit_valid;
    wire feature_commit_ready;
    reg [12:0] feature_commit_address;
    reg [15:0] feature_commit_data;
    reg feature_commit2_valid;
    wire feature_commit2_ready;
    reg [12:0] feature_commit2_address;
    reg [15:0] feature_commit2_data;
    wire feature_address_error;
    wire [31:0] feature_read_count;
    wire [31:0] feature_write_count;
    wire [31:0] collision_stall_count;

    // OP4 is the final consumer of FM0[6144:8191]. Reuse that released 2K
    // window as the next-sample staging area from OP5 onward; the fixed
    // physical sample window avoids a second buffer and bank-select state.
    // From OP5 onward the original sample window is dead.  The banked memory
    // returns dynamic backpressure only on a real read/write or write/write
    // bank conflict, allowing the next sample to overlap compute commits.
    wire sample_overlap_ready = busy &&
        (opcode >= 4'd5) && !op_ready;
    wire sample_stream_ready = sample_ready &&
        (!busy || sample_overlap_ready);
    wire sample_valid = stream_valid && sample_stream_selected &&
        sample_stream_ready;

    wire tile_clear;
    wire tile_write_valid;
    wire tile_write_ready;
    wire [7:0] tile_write_index;
    wire [15:0] tile_write_data;
    wire tile_write2_valid;
    wire [7:0] tile_write2_index;
    wire [15:0] tile_write2_data;
    wire tile_write3_valid;
    wire [7:0] tile_write3_index;
    wire [15:0] tile_write3_data;
    wire tile_write4_valid;
    wire [7:0] tile_write4_index;
    wire [15:0] tile_write4_data;
    wire [7:0] tile_read_base_index;
    wire [255:0] tile_read_window;
    wire [8:0] tile_live_count;
    wire [8:0] tile_maximum_occupancy;
    wire tile_overflow_error;

    wire score_valid;
    wire score_ready;
    wire [15:0] score_data;
    wire [3:0] score_index;
    wire score_last;
    wire class_count_error;
    wire mac_active;

    reg [31:0] total_cycles;
    reg [31:0] producer_stalls;
    reg [31:0] consumer_stalls;
    reg [31:0] mac_activity;

    // Keep the completed next-sample marker alive through command acceptance.
    // OP0 captures the selected physical bank on its own acceptance edge; only
    // then may the stream loader return to the low bank for a later sample.
    wire sample_reset = op_valid && op_ready && (opcode == 4'd0);

    assign stream_ready = sample_stream_selected ?
        sample_stream_ready : scheduler_load_ready;
    assign error = scheduler_error || op_error || feature_address_error ||
        tile_overflow_error || class_count_error;

    instruction_scheduler scheduler (
        .clk(clk),
        .rst_n(rst_n),
        .load_valid(scheduler_load_valid),
        .load_ready(scheduler_load_ready),
        .load_type(stream_type),
        .load_data(stream_data),
        .load_last(stream_last),
        .start_valid(command_valid),
        .start_ready(command_ready),
        .profile_select(profile_select),
        .instruction_version(instruction_version),
        .sample_loaded(sample_loaded),
        .op_valid(op_valid),
        .op_ready(op_ready),
        .opcode(opcode),
        .descriptor_index(descriptor_index),
        .source_base(source_base),
        .destination_base(destination_base),
        .parameter_base(parameter_base),
        .op_done(op_done),
        .op_error(op_error),
        .all_done(all_done),
        .busy(busy),
        .format_error(scheduler_error),
        .parameter_read_address(parameter_read_address),
        .parameter_read_data(parameter_read_data),
        .parameter_word_count(parameter_word_count),
        .instruction_word_count(instruction_word_count),
        .active_channels(active_channels),
        .expected_sample_words(expected_sample_words),
        .channel_config_valid(channel_config_valid)
    );

    feature_memory_subsystem feature_memory (
        .clk(clk),
        .rst_n(rst_n),
        .sample_valid(sample_valid),
        .sample_ready(sample_ready),
        .sample_data(stream_data),
        .sample_last(stream_last),
        .sample_reset(sample_reset),
        .expected_sample_words(expected_sample_words),
        .channel_config_valid(channel_config_valid),
        .sample_loaded(sample_loaded),
        .sample_count(sample_count),
        .read_enable(feature_read_enable),
        .read_pair_enable(feature_read_pair_enable),
        .read_quad_enable(feature_read_quad_enable),
        .read_address(feature_read_address),
        .read_valid(feature_read_valid),
        .read_data(feature_read_data),
        .read_pair_data(feature_read_pair_data),
        .read_quad_data2(feature_read_quad_data2),
        .read_quad_data3(feature_read_quad_data3),
        .read_oct_data4(feature_read_oct_data4),
        .read_oct_data5(feature_read_oct_data5),
        .read_oct_data6(feature_read_oct_data6),
        .read_oct_data7(feature_read_oct_data7),
        .write_valid(feature_commit_valid),
        .write_ready(feature_commit_ready),
        .write_address(feature_commit_address),
        .write_data(feature_commit_data),
        .write2_valid(feature_commit2_valid),
        .write2_ready(feature_commit2_ready),
        .write2_address(feature_commit2_address),
        .write2_data(feature_commit2_data),
        .address_error(feature_address_error),
        .read_count(feature_read_count),
        .write_count(feature_write_count),
        .collision_stall_count(collision_stall_count)
    );

    stream_tile_buffer tile_buffer (
        .clk(clk),
        .rst_n(rst_n),
        .clear(tile_clear),
        .write_valid(tile_write_valid),
        .write_index(tile_write_index),
        .write_data(tile_write_data),
        .write2_valid(tile_write2_valid),
        .write2_index(tile_write2_index),
        .write2_data(tile_write2_data),
        .write3_valid(tile_write3_valid),
        .write3_index(tile_write3_index),
        .write3_data(tile_write3_data),
        .write4_valid(tile_write4_valid),
        .write4_index(tile_write4_index),
        .write4_data(tile_write4_data),
        .write_ready(tile_write_ready),
        .read_base_index(tile_read_base_index),
        .read_window(tile_read_window),
        .live_count(tile_live_count),
        .maximum_occupancy(tile_maximum_occupancy),
        .overflow_error(tile_overflow_error)
    );

    conv_datapath datapath (
        .clk(clk),
        .rst_n(rst_n),
        .op_valid(op_valid),
        .op_ready(op_ready),
        .opcode(opcode),
        .source_base(source_base),
        .destination_base(destination_base),
        .parameter_base(parameter_base),
        .active_channels(active_channels),
        .parameter_read_address(parameter_read_address),
        .parameter_read_data(parameter_read_data),
        .feature_read_enable(feature_read_enable),
        .feature_read_pair_enable(feature_read_pair_enable),
        .feature_read_quad_enable(feature_read_quad_enable),
        .feature_read_address(feature_read_address),
        .feature_read_valid(feature_read_valid),
        .feature_read_data(feature_read_data),
        .feature_read_pair_data(feature_read_pair_data),
        .feature_read_quad_data2(feature_read_quad_data2),
        .feature_read_quad_data3(feature_read_quad_data3),
        .feature_read_oct_data4(feature_read_oct_data4),
        .feature_read_oct_data5(feature_read_oct_data5),
        .feature_read_oct_data6(feature_read_oct_data6),
        .feature_read_oct_data7(feature_read_oct_data7),
        .feature_write_valid(feature_write_valid),
        .feature_write_ready(feature_write_ready),
        .feature_write_address(feature_write_address),
        .feature_write_data(feature_write_data),
        .feature_write2_valid(feature_write2_valid),
        .feature_write2_ready(feature_write2_ready),
        .feature_write2_address(feature_write2_address),
        .feature_write2_data(feature_write2_data),
        .tile_clear(tile_clear),
        .tile_write_valid(tile_write_valid),
        .tile_write_ready(tile_write_ready),
        .tile_write_index(tile_write_index),
        .tile_write_data(tile_write_data),
        .tile_write2_valid(tile_write2_valid),
        .tile_write2_index(tile_write2_index),
        .tile_write2_data(tile_write2_data),
        .tile_write3_valid(tile_write3_valid),
        .tile_write3_index(tile_write3_index),
        .tile_write3_data(tile_write3_data),
        .tile_write4_valid(tile_write4_valid),
        .tile_write4_index(tile_write4_index),
        .tile_write4_data(tile_write4_data),
        .tile_read_base_index(tile_read_base_index),
        .tile_read_window(tile_read_window),
        .score_valid(score_valid),
        .score_ready(score_ready),
        .score_data(score_data),
        .score_index(score_index),
        .score_last(score_last),
        .op_done(op_done),
        .op_error(op_error),
        .mac_active(mac_active),
        .trace_write_valid(trace_write_valid),
        .trace_opcode(trace_opcode),
        .trace_write_address(trace_write_address),
        .trace_write_data(trace_write_data),
        .trace_write2_valid(trace_write2_valid),
        .trace_write2_address(trace_write2_address),
        .trace_write2_data(trace_write2_data)
    );

    assign feature_write_ready =
        !feature_commit_valid || feature_commit_ready;
    assign feature_write2_ready =
        !feature_commit2_valid || feature_commit2_ready;

    argmax_output argmax (
        .clk(clk),
        .rst_n(rst_n),
        .score_valid(score_valid),
        .score_ready(score_ready),
        .score_data(score_data),
        .class_index(score_index),
        .score_last(score_last),
        .result(result),
        .infer_done(infer_done),
        .class_led(class_led),
        .class_count_error(class_count_error)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            total_cycles <= 32'd0;
            producer_stalls <= 32'd0;
            consumer_stalls <= 32'd0;
            mac_activity <= 32'd0;
            feature_commit_valid <= 1'b0;
            feature_commit_address <= 13'd0;
            feature_commit_data <= 16'd0;
            feature_commit2_valid <= 1'b0;
            feature_commit2_address <= 13'd0;
            feature_commit2_data <= 16'd0;
            total_cycles_snapshot <= 32'd0;
            memory_stalls_snapshot <= 32'd0;
            producer_stalls_snapshot <= 32'd0;
            consumer_stalls_snapshot <= 32'd0;
            mac_activity_snapshot <= 32'd0;
            tile_occupancy_snapshot <= 32'd0;
        end
        else begin
            if (feature_write_ready) begin
                feature_commit_valid <= feature_write_valid;
                if (feature_write_valid) begin
                    feature_commit_address <= feature_write_address;
                    feature_commit_data <= feature_write_data;
                end
            end
            if (feature_write2_ready) begin
                feature_commit2_valid <= feature_write2_valid;
                if (feature_write2_valid) begin
                    feature_commit2_address <= feature_write2_address;
                    feature_commit2_data <= feature_write2_data;
                end
            end

            if (clear_counters) begin
                total_cycles <= 32'd0;
                producer_stalls <= 32'd0;
                consumer_stalls <= 32'd0;
                mac_activity <= 32'd0;
            end
            else begin
                if (busy && total_cycles != 32'hffff_ffff)
                    total_cycles <= total_cycles + 1'b1;
                if (feature_write_valid && !feature_write_ready &&
                    producer_stalls != 32'hffff_ffff)
                    producer_stalls <= producer_stalls + 1'b1;
                else if (feature_write2_valid && !feature_write2_ready &&
                         producer_stalls != 32'hffff_ffff)
                    producer_stalls <= producer_stalls + 1'b1;
                if (feature_read_enable && !feature_read_valid &&
                    consumer_stalls != 32'hffff_ffff)
                    consumer_stalls <= consumer_stalls + 1'b1;
                if (mac_active && mac_activity != 32'hffff_ffff)
                    mac_activity <= mac_activity + 1'b1;
            end

            if (snapshot_counters) begin
                total_cycles_snapshot <= total_cycles;
                memory_stalls_snapshot <= collision_stall_count;
                producer_stalls_snapshot <= producer_stalls;
                consumer_stalls_snapshot <= consumer_stalls;
                mac_activity_snapshot <= mac_activity;
                tile_occupancy_snapshot <= {23'd0, tile_maximum_occupancy};
            end
        end
    end
endmodule
`default_nettype wire
