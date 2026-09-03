// Module: instruction_scheduler
// Description: Loads and dispatches frozen V2 instruction descriptors.
// Scope: Eleven sequential descriptors, 1076 parameters, and 264 words.
// Spec Trace: REQ-EEG-CH16-001, REQ-EEG-RTL-COMPAT-001.
`timescale 1ns/1ps
`default_nettype none

module instruction_scheduler (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        load_valid,
    output wire        load_ready,
    input  wire [2:0]  load_type,
    input  wire [15:0] load_data,
    input  wire        load_last,
    input  wire        start_valid,
    output wire        start_ready,
    input  wire [1:0]  profile_select,
    input  wire [1:0]  instruction_version,
    input  wire        sample_loaded,
    output reg         op_valid,
    input  wire        op_ready,
    output reg  [3:0]  opcode,
    output reg  [7:0]  descriptor_index,
    output reg  [13:0] source_base,
    output reg  [13:0] destination_base,
    output reg  [10:0] parameter_base,
    input  wire        op_done,
    input  wire        op_error,
    output reg         all_done,
    output reg         busy,
    output reg         format_error,
    input  wire [10:0] parameter_read_address,
    output wire [63:0] parameter_read_data,
    output reg  [10:0] parameter_word_count,
    output reg  [8:0]  instruction_word_count,
    output reg  [4:0]  active_channels,
    output wire [12:0] expected_sample_words,
    output wire        channel_config_valid
);
    localparam PROFILE_STREAM_TDP = 2'b01;
    localparam VERSION_V2 = 2'b01;

    // Four parameter words share one 64-bit BRAM row. The two synchronous
    // read ports fetch adjacent rows and form an unaligned four-word window,
    // preserving the host's original 16-bit sequential load protocol.
    (* ram_style = "block" *)
    // Row 270 is an unused guard row for the speculative next request issued
    // while the final useful 64-bit window retires.  It does not increase the
    // physical two-RAMB36 implementation.
    reg [63:0] parameter_memory [0:270];
    reg [47:0] parameter_load_pack;
    reg [63:0] parameter_read_low_q;
    reg [63:0] parameter_read_high_q;
    reg [1:0] parameter_read_lane_q;
    reg [3:0] descriptor_opcode_memory [0:10];
    reg [13:0] descriptor_source_memory [0:10];
    reg [13:0] descriptor_destination_memory [0:10];
    reg [10:0] descriptor_parameter_memory [0:10];
    reg [10:0] descriptor_format_valid;
    reg [3:0] instruction_load_descriptor;
    reg [4:0] instruction_load_offset;
    reg [3:0] active_descriptor;
    reg waiting_for_operation;

    wire parameter_load_enable =
        rst_n &&
        load_valid &&
        load_ready &&
        (load_type == 3'b011) &&
        (parameter_word_count < 11'd1076);
    wire instruction_load_enable =
        rst_n &&
        load_valid &&
        load_ready &&
        (load_type == 3'b110) &&
        (instruction_word_count < 9'd264);
    wire descriptor_valid =
        (active_descriptor <= 4'd10) &&
        descriptor_format_valid[active_descriptor];
    wire [8:0] parameter_read_row = parameter_read_address[10:2];
    wire [127:0] parameter_read_window =
        {parameter_read_high_q, parameter_read_low_q};

    assign load_ready = !busy;
    assign expected_sample_words = {active_channels, 7'b0000000};
    assign channel_config_valid =
        (instruction_word_count == 9'd264) &&
        (descriptor_format_valid == 11'h7ff) &&
        (active_channels >= 5'd2) &&
        (active_channels <= 5'd16);
    assign start_ready =
        !busy &&
        sample_loaded &&
        (parameter_word_count == 11'd1076) &&
        (instruction_word_count == 9'd264) &&
        channel_config_valid &&
        (profile_select == PROFILE_STREAM_TDP) &&
        (instruction_version == VERSION_V2);
    assign parameter_read_data =
        parameter_read_window >> {parameter_read_lane_q, 4'b0000};

    always @(posedge clk) begin
        if (parameter_load_enable) begin
            case (parameter_word_count[1:0])
                2'd0: parameter_load_pack[15:0] <= load_data;
                2'd1: parameter_load_pack[31:16] <= load_data;
                2'd2: parameter_load_pack[47:32] <= load_data;
                2'd3: parameter_memory[parameter_word_count[10:2]] <=
                    {load_data, parameter_load_pack};
                default: begin end
            endcase
        end
        if (busy) begin
            parameter_read_low_q <= parameter_memory[parameter_read_row];
            parameter_read_lane_q <= parameter_read_address[1:0];
        end
    end

    always @(posedge clk) begin
        if (busy)
            parameter_read_high_q <= parameter_memory[parameter_read_row + 1'b1];
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            descriptor_format_valid <= 11'd0;
            instruction_load_descriptor <= 4'd0;
            instruction_load_offset <= 5'd0;
            active_channels <= 5'd0;
        end
        else if (instruction_load_enable) begin
            case (instruction_load_offset)
                5'd0: begin
                    descriptor_opcode_memory[instruction_load_descriptor] <=
                        load_data[7:4];
                    descriptor_format_valid[instruction_load_descriptor] <=
                        (load_data[15:12] == 4'hA) &&
                        (load_data[11:8] == 4'h2) &&
                        (load_data[7:4] == instruction_load_descriptor) &&
                        load_data[0] &&
                        ((instruction_load_descriptor == 4'd10) ?
                            load_data[3] : !load_data[3]);
                end
                5'd1:
                    descriptor_format_valid[instruction_load_descriptor] <=
                        descriptor_format_valid[instruction_load_descriptor] &&
                        (load_data[15:8] == 8'h16) &&
                        (load_data[7:0] == instruction_load_descriptor);
                5'd2: begin
                    descriptor_source_memory[instruction_load_descriptor] <=
                        {load_data[13],
                         load_data[12:11] |
                            {2{instruction_load_descriptor == 4'd0}},
                         load_data[10:0]};
                    descriptor_format_valid[instruction_load_descriptor] <=
                        descriptor_format_valid[instruction_load_descriptor] &&
                        (load_data[15:14] == 2'b00);
                end
                5'd4: begin
                    descriptor_destination_memory[
                        instruction_load_descriptor] <= load_data[13:0];
                    descriptor_format_valid[instruction_load_descriptor] <=
                        descriptor_format_valid[instruction_load_descriptor] &&
                        (load_data[15:14] == 2'b00);
                end
                5'd6: begin
                    descriptor_parameter_memory[
                        instruction_load_descriptor] <= load_data[10:0];
                    descriptor_format_valid[instruction_load_descriptor] <=
                        descriptor_format_valid[instruction_load_descriptor] &&
                        (load_data[15:11] == 5'b00000);
                end
                5'd12: begin
                    if (instruction_load_descriptor == 4'd0) begin
                        active_channels <= load_data[4:0];
                        descriptor_format_valid[0] <=
                            descriptor_format_valid[0] &&
                            (load_data[15:5] == 11'd0) &&
                            (load_data[4:0] >= 5'd2) &&
                            (load_data[4:0] <= 5'd16);
                    end
                    else if (instruction_load_descriptor <= 4'd4) begin
                        descriptor_format_valid[instruction_load_descriptor] <=
                            descriptor_format_valid[instruction_load_descriptor] &&
                            (load_data[15:5] == 11'd0) &&
                            (load_data[4:0] == active_channels);
                    end
                end
                5'd23:
                    descriptor_format_valid[instruction_load_descriptor] <=
                        descriptor_format_valid[instruction_load_descriptor] &&
                        (load_data[15:7] == 9'b0);
                default: begin end
            endcase

            if (instruction_load_offset == 5'd23) begin
                instruction_load_offset <= 5'd0;
                if (instruction_load_descriptor != 4'd10)
                    instruction_load_descriptor <=
                        instruction_load_descriptor + 1'b1;
            end
            else begin
                instruction_load_offset <= instruction_load_offset + 1'b1;
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            parameter_word_count <= 11'd0;
            instruction_word_count <= 9'd0;
            active_descriptor <= 4'd0;
            waiting_for_operation <= 1'b0;
            op_valid <= 1'b0;
            opcode <= 4'd0;
            descriptor_index <= 8'd0;
            source_base <= 14'd0;
            destination_base <= 14'd0;
            parameter_base <= 11'd0;
            all_done <= 1'b0;
            busy <= 1'b0;
            format_error <= 1'b0;
        end
        else begin
            all_done <= 1'b0;

            if (load_valid && load_ready) begin
                if (load_type == 3'b011) begin
                    if (parameter_word_count < 11'd1076) begin
                        parameter_word_count <= parameter_word_count + 1'b1;
                    end
                    else begin
                        format_error <= 1'b1;
                    end
                    if (load_last && parameter_word_count != 11'd1075)
                        format_error <= 1'b1;
                end
                else if (load_type == 3'b110) begin
                    if (instruction_word_count < 9'd264) begin
                        instruction_word_count <= instruction_word_count + 1'b1;
                    end
                    else begin
                        format_error <= 1'b1;
                    end
                    if (load_last && instruction_word_count != 9'd263)
                        format_error <= 1'b1;
                end
            end

            if (start_valid && !start_ready)
                format_error <= 1'b1;

            if (start_valid && start_ready) begin
                if (!descriptor_format_valid[0]) begin
                    busy <= 1'b0;
                    op_valid <= 1'b0;
                    format_error <= 1'b1;
                end
                else begin
                    busy <= 1'b1;
                    active_descriptor <= 4'd0;
                    waiting_for_operation <= 1'b0;
                    op_valid <= 1'b0;
                    format_error <= 1'b0;
                end
            end

            if (busy && !waiting_for_operation && !op_valid) begin
                if (!descriptor_valid) begin
                    format_error <= 1'b1;
                    busy <= 1'b0;
                end
                else begin
                    opcode <= descriptor_opcode_memory[active_descriptor];
                    descriptor_index <= {4'd0, active_descriptor};
                    source_base <=
                        descriptor_source_memory[active_descriptor];
                    destination_base <=
                        descriptor_destination_memory[active_descriptor];
                    parameter_base <=
                        descriptor_parameter_memory[active_descriptor];
                    op_valid <= 1'b1;
                end
            end

            if (op_valid && op_ready) begin
                op_valid <= 1'b0;
                waiting_for_operation <= 1'b1;
            end

            if (waiting_for_operation && (op_done || op_error)) begin
                waiting_for_operation <= 1'b0;
                if (op_error) begin
                    format_error <= 1'b1;
                    busy <= 1'b0;
                end
                else if (active_descriptor == 4'd10) begin
                    busy <= 1'b0;
                    all_done <= 1'b1;
                end
                else if (!descriptor_format_valid[active_descriptor + 1'b1]) begin
                    format_error <= 1'b1;
                    busy <= 1'b0;
                end
                else begin
                    active_descriptor <= active_descriptor + 1'b1;
                end
            end
        end
    end
endmodule
`default_nettype wire
