// -----------------------------------------------------------------------------
// Module: frame_ingress_adapter
// Description: Loads packed FP16 frame beats before START.  A software-owned
//              configuration word optionally transposes time-major input into
//              channel-major storage and applies one shared scalar scale.
// Scope: Profile-independent, page/configuration-driven frame loading.
// Spec Trace: REQ-RRB-008, REQ-RRB-009, REQ-RRB-020, REQ-RRB-021,
//             REQ-RRB-024
// -----------------------------------------------------------------------------

`default_nettype none

module frame_ingress_adapter (
    input  wire        clk,
    input  wire        reset_n,
    input  wire        session_busy,
    input  wire        frame_begin,
    input  wire [1:0]  frame_page,
    input  wire [63:0] frame_config,
    input  wire        frame_valid,
    output wire        frame_ready,
    input  wire [63:0] frame_data,
    output reg         frame_complete,
    output reg  [8:0]  frame_beat_count,
    output wire        bank0_write_valid,
    output wire [12:0] bank0_write_address,
    output wire [15:0] bank0_write_data,
    output wire        bank1_write_valid,
    output wire [12:0] bank1_write_address,
    output wire [15:0] bank1_write_data,
    output wire        bank2_write_valid,
    output wire [12:0] bank2_write_address,
    output wire [15:0] bank2_write_data,
    output wire        bank3_write_valid,
    output wire [12:0] bank3_write_address,
    output wire [15:0] bank3_write_data
);
    reg [63:0] frame_config_q;
    reg [63:0] transform_beat_q;
    reg        transform_pending_q;
    reg        transform_draining_q;
    reg        transform_beat_last_q;
    reg [1:0]  transform_lane_q;
    reg [4:0]  transform_channel_q;
    reg [8:0]  transform_sample_q;
    reg [12:0] transform_channel_base_q;
    reg [3:0]  transform_valid_pipe_q;
    reg [3:0]  transform_last_pipe_q;
    reg [12:0] transform_address_d0_q;
    reg [12:0] transform_address_d1_q;
    reg [12:0] transform_address_d2_q;
    reg [12:0] transform_address_d3_q;
    reg [15:0] transform_data_d0_q;
    reg [15:0] transform_data_d1_q;
    reg [15:0] transform_data_d2_q;
    reg [15:0] transform_data_d3_q;

    wire frame_transform_enabled;
    wire frame_scale_enabled;
    wire [4:0] frame_channel_count;
    wire [4:0] frame_selected_channel_count;
    wire [8:0] frame_sample_count;
    wire [1:0] frame_destination_page;
    wire [15:0] frame_scale;
    wire direct_accept;
    wire transform_accept;
    wire transform_issue;
    wire transform_last_issue;
    wire transform_write_issue;
    wire transform_last_write;
    wire transform_output_valid;
    wire [15:0] transform_source_word;
    wire [12:0] transform_source_address;
    wire scale_output_valid;
    wire [15:0] scale_output_word;
    wire [15:0] transform_output_word;
    wire [1:0] transform_output_bank;

    // frame_config is a trusted PS register image held stable for one frame:
    // [0] transform, [5:1] input channels, [14:6] samples/channel,
    // [16:15] destination page, [32:17] FP16 scale, [33] scale enable,
    // [38:34] selected leading channels written to the destination.
    assign frame_transform_enabled = frame_config_q[0];
    assign frame_channel_count = frame_config_q[5:1];
    assign frame_sample_count = frame_config_q[14:6];
    assign frame_destination_page = frame_config_q[16:15];
    assign frame_scale = frame_config_q[32:17];
    assign frame_scale_enabled = frame_config_q[33];
    assign frame_selected_channel_count = frame_config_q[38:34];

    assign frame_ready = ~session_busy &&
        (!frame_transform_enabled ||
         (!transform_pending_q && !transform_draining_q));
    assign direct_accept = frame_valid && frame_ready &&
        !frame_transform_enabled;
    assign transform_accept = frame_valid && frame_ready &&
        frame_transform_enabled;
    assign transform_issue = frame_transform_enabled &&
        transform_pending_q;
    assign transform_last_issue = transform_issue &&
        transform_beat_last_q &&
        (transform_lane_q == 2'd3);
    assign transform_write_issue = transform_issue &&
        (transform_channel_q < frame_selected_channel_count);
    assign transform_last_write = transform_write_issue &&
        ((transform_channel_q + 5'd1) >=
         frame_selected_channel_count) &&
        ((transform_sample_q + 9'd1) >= frame_sample_count);
    assign transform_source_word =
        transform_beat_q[transform_lane_q*16 +: 16];
    assign transform_source_address =
        {frame_destination_page, 11'd0} +
        transform_channel_base_q + {4'd0, transform_sample_q};
    assign transform_output_valid = frame_scale_enabled ?
        scale_output_valid : transform_valid_pipe_q[3];
    assign transform_output_word = frame_scale_enabled ?
        scale_output_word : transform_data_d3_q;
    assign transform_output_bank = transform_address_d3_q[1:0];

    apx_fp16_mul_pipe u_frame_scale (
        .clk(clk),
        .reset_n(reset_n),
        .input_valid(transform_write_issue && frame_scale_enabled),
        .operand_x(transform_source_word),
        .operand_y(frame_scale),
        .output_valid(scale_output_valid),
        .product(scale_output_word)
    );

    assign bank0_write_valid = direct_accept ||
        (transform_output_valid && (transform_output_bank == 2'd0));
    assign bank1_write_valid = direct_accept ||
        (transform_output_valid && (transform_output_bank == 2'd1));
    assign bank2_write_valid = direct_accept ||
        (transform_output_valid && (transform_output_bank == 2'd2));
    assign bank3_write_valid = direct_accept ||
        (transform_output_valid && (transform_output_bank == 2'd3));

    assign bank0_write_address = frame_transform_enabled ?
        transform_address_d3_q : {frame_page, frame_beat_count, 2'd0};
    assign bank1_write_address = frame_transform_enabled ?
        transform_address_d3_q : {frame_page, frame_beat_count, 2'd1};
    assign bank2_write_address = frame_transform_enabled ?
        transform_address_d3_q : {frame_page, frame_beat_count, 2'd2};
    assign bank3_write_address = frame_transform_enabled ?
        transform_address_d3_q : {frame_page, frame_beat_count, 2'd3};

    assign bank0_write_data = frame_transform_enabled ?
        transform_output_word : frame_data[15:0];
    assign bank1_write_data = frame_transform_enabled ?
        transform_output_word : frame_data[31:16];
    assign bank2_write_data = frame_transform_enabled ?
        transform_output_word : frame_data[47:32];
    assign bank3_write_data = frame_transform_enabled ?
        transform_output_word : frame_data[63:48];

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            frame_complete <= 1'b0;
            frame_beat_count <= 9'd0;
            frame_config_q <= 64'd0;
            transform_beat_q <= 64'd0;
            transform_pending_q <= 1'b0;
            transform_draining_q <= 1'b0;
            transform_beat_last_q <= 1'b0;
            transform_lane_q <= 2'd0;
            transform_channel_q <= 5'd0;
            transform_sample_q <= 9'd0;
            transform_channel_base_q <= 13'd0;
            transform_valid_pipe_q <= 4'd0;
            transform_last_pipe_q <= 4'd0;
            transform_address_d0_q <= 13'd0;
            transform_address_d1_q <= 13'd0;
            transform_address_d2_q <= 13'd0;
            transform_address_d3_q <= 13'd0;
            transform_data_d0_q <= 16'd0;
            transform_data_d1_q <= 16'd0;
            transform_data_d2_q <= 16'd0;
            transform_data_d3_q <= 16'd0;
        end
        else begin
            transform_valid_pipe_q <= {
                transform_valid_pipe_q[2:0], transform_write_issue};
            transform_last_pipe_q <= {
                transform_last_pipe_q[2:0], transform_last_write};
            transform_address_d3_q <= transform_address_d2_q;
            transform_address_d2_q <= transform_address_d1_q;
            transform_address_d1_q <= transform_address_d0_q;
            transform_data_d3_q <= transform_data_d2_q;
            transform_data_d2_q <= transform_data_d1_q;
            transform_data_d1_q <= transform_data_d0_q;
            if (transform_write_issue) begin
                transform_address_d0_q <= transform_source_address;
                transform_data_d0_q <= transform_source_word;
            end

            if (frame_begin) begin
                frame_complete <= 1'b0;
                frame_beat_count <= 9'd0;
                frame_config_q <= frame_config;
                transform_pending_q <= 1'b0;
                transform_draining_q <= 1'b0;
                transform_beat_last_q <= 1'b0;
                transform_lane_q <= 2'd0;
                transform_channel_q <= 5'd0;
                transform_sample_q <= 9'd0;
                transform_channel_base_q <= 13'd0;
                transform_valid_pipe_q <= 4'd0;
                transform_last_pipe_q <= 4'd0;
            end
            else begin
                if (direct_accept) begin
                    if (frame_beat_count == 9'd511) begin
                        frame_complete <= 1'b1;
                        frame_beat_count <= 9'd0;
                    end
                    else begin
                        frame_beat_count <= frame_beat_count + 9'd1;
                    end
                end

                if (transform_accept) begin
                    transform_beat_q <= frame_data;
                    transform_pending_q <= 1'b1;
                    transform_beat_last_q <=
                        frame_beat_count == 9'd511;
                    transform_lane_q <= 2'd0;
                    if (frame_beat_count != 9'd511)
                        frame_beat_count <= frame_beat_count + 9'd1;
                end

                if (transform_issue) begin
                    if (transform_last_issue) begin
                        transform_pending_q <= 1'b0;
                        transform_draining_q <= 1'b1;
                        transform_lane_q <= 2'd0;
                    end
                    else if (transform_lane_q == 2'd3) begin
                        transform_pending_q <= 1'b0;
                        transform_lane_q <= 2'd0;
                    end
                    else begin
                        transform_lane_q <= transform_lane_q + 2'd1;
                    end

                    if ((transform_channel_q + 5'd1) >=
                        frame_channel_count) begin
                        transform_channel_q <= 5'd0;
                        transform_channel_base_q <= 13'd0;
                        transform_sample_q <= transform_sample_q + 9'd1;
                    end
                    else begin
                        transform_channel_q <= transform_channel_q + 5'd1;
                        transform_channel_base_q <=
                            transform_channel_base_q +
                            {4'd0, frame_sample_count};
                    end
                end

                if (transform_output_valid &&
                    transform_last_pipe_q[3]) begin
                    frame_complete <= 1'b1;
                    frame_beat_count <= 9'd0;
                    transform_draining_q <= 1'b0;
                end
            end
        end
    end
endmodule
`default_nettype wire
