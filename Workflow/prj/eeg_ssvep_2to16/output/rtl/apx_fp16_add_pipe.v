//==============================================================================
// Module      : apx_fp16_add_pipe
// File        : apx_fp16_add_pipe.v
// Project     : eeg_ssvep_2to16
// Description : Three-stage bit-exact approximate FP16 add/bypass pipeline.
// Scope:
//   - Owns magnitude select, alignment, add/subtract, and packing registers.
//   - Does not select compute modes, addresses, destinations, or profiles.
// Spec Trace:
//   - REQ-RRB-006, REQ-RRB-011, REQ-RRB-012
//   - DF-APX-SHARED, LAT-APX
// Notes:
//   - use_operand_y low forwards operand_x through the same three-cycle pipe.
//   - Arithmetic order is the frozen adjacent-pairwise APX golden order.
//==============================================================================
`timescale 1ns/1ps
`default_nettype none

module apx_fp16_add_pipe (
    input  wire        clk,
    input  wire        reset_n,
    input  wire        input_valid,
    input  wire        use_operand_y,
    input  wire [15:0] operand_x,
    input  wire [15:0] operand_y,
    output reg         output_valid,
    output reg  [15:0] sum
);
    reg        select_valid_q;
    reg        select_bypass_q;
    reg        select_sign_q;
    reg        select_different_sign_q;
    reg [4:0]  select_exponent_base_q;
    reg [4:0]  select_exponent_delta_q;
    reg [10:0] select_mantissa_large_q;
    reg [10:0] select_mantissa_small_q;
    reg [15:0] select_bypass_value_q;

    reg        align_valid_q;
    reg        align_bypass_q;
    reg        align_sign_q;
    reg [4:0]  align_exponent_base_q;
    reg [11:0] align_mantissa_q;
    reg [15:0] align_bypass_value_q;

    wire [3:0]  alignment_shift;
    wire [10:0] aligned_mantissa;
    wire [11:0] combined_mantissa;
    wire        operand_x_is_large;
    reg  [3:0]  normalization_shift;
    reg         normalize_up;
    reg  [4:0]  packed_exponent;
    reg  [9:0]  packed_mantissa;

    assign alignment_shift = (select_exponent_delta_q > 5'd10) ?
        4'd11 : select_exponent_delta_q[3:0];
    assign operand_x_is_large =
        (operand_x[14:10] > operand_y[14:10]) ||
        ((operand_x[14:10] == operand_y[14:10]) &&
        (operand_x[9:0] > operand_y[9:0]));
    assign aligned_mantissa =
        select_mantissa_small_q >> alignment_shift;
    assign combined_mantissa = select_different_sign_q ?
        ({1'b0, select_mantissa_large_q} - {1'b0, aligned_mantissa}) :
        ({1'b0, select_mantissa_large_q} + {1'b0, aligned_mantissa});

    always @(*) begin
        normalize_up = 1'b0;
        normalization_shift = 4'd10;
        if (align_mantissa_q[11]) begin
            normalize_up = 1'b1;
            normalization_shift = 4'd1;
        end
        else if (align_mantissa_q[10]) begin
            normalization_shift = 4'd0;
        end
        else if (align_mantissa_q[9]) begin
            normalization_shift = 4'd1;
        end
        else if (align_mantissa_q[8]) begin
            normalization_shift = 4'd2;
        end
        else if (align_mantissa_q[7]) begin
            normalization_shift = 4'd3;
        end
        else if (align_mantissa_q[6]) begin
            normalization_shift = 4'd4;
        end
        else if (align_mantissa_q[5]) begin
            normalization_shift = 4'd5;
        end
        else if (align_mantissa_q[4]) begin
            normalization_shift = 4'd6;
        end
        else if (align_mantissa_q[3]) begin
            normalization_shift = 4'd7;
        end
        else if (align_mantissa_q[2]) begin
            normalization_shift = 4'd8;
        end
        else if (align_mantissa_q[1]) begin
            normalization_shift = 4'd9;
        end

        if (normalize_up) begin
            packed_mantissa = align_mantissa_q[10:1];
            if (align_exponent_base_q == 5'd31) begin
                packed_exponent = 5'd31;
            end
            else begin
                packed_exponent = align_exponent_base_q + 5'd1;
            end
        end
        else begin
            packed_mantissa = align_mantissa_q[9:0] <<
                normalization_shift;
            if (align_exponent_base_q <= normalization_shift) begin
                packed_exponent = 5'd0;
            end
            else begin
                packed_exponent = align_exponent_base_q -
                    normalization_shift;
            end
        end
    end

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            select_valid_q <= 1'b0;
            select_bypass_q <= 1'b0;
            select_sign_q <= 1'b0;
            select_different_sign_q <= 1'b0;
            select_exponent_base_q <= 5'd0;
            select_exponent_delta_q <= 5'd0;
            select_mantissa_large_q <= 11'd0;
            select_mantissa_small_q <= 11'd0;
            select_bypass_value_q <= 16'd0;
            align_valid_q <= 1'b0;
            align_bypass_q <= 1'b0;
            align_sign_q <= 1'b0;
            align_exponent_base_q <= 5'd0;
            align_mantissa_q <= 12'd0;
            align_bypass_value_q <= 16'd0;
            output_valid <= 1'b0;
            sum <= 16'd0;
        end
        else begin
            select_valid_q <= input_valid;
            align_valid_q <= select_valid_q;
            output_valid <= align_valid_q;

            if (input_valid) begin
                select_bypass_q <= !use_operand_y;
                select_bypass_value_q <= operand_x;
                select_different_sign_q <= operand_x[15] ^ operand_y[15];
                if (operand_x_is_large) begin
                    select_exponent_base_q <= operand_x[14:10];
                    select_exponent_delta_q <=
                        operand_x[14:10] - operand_y[14:10];
                    select_mantissa_large_q <= {1'b1, operand_x[9:0]};
                    select_mantissa_small_q <= {1'b1, operand_y[9:0]};
                    select_sign_q <= operand_x[15];
                end
                else begin
                    select_exponent_base_q <= operand_y[14:10];
                    select_exponent_delta_q <=
                        operand_y[14:10] - operand_x[14:10];
                    select_mantissa_large_q <= {1'b1, operand_y[9:0]};
                    select_mantissa_small_q <= {1'b1, operand_x[9:0]};
                    if (operand_x[15] ^ operand_y[15]) begin
                        select_sign_q <= operand_y[15];
                    end
                    else begin
                        select_sign_q <= operand_x[15];
                    end
                end
            end
            else begin
                select_bypass_q <= select_bypass_q;
                select_bypass_value_q <= select_bypass_value_q;
                select_different_sign_q <= select_different_sign_q;
                select_exponent_base_q <= select_exponent_base_q;
                select_exponent_delta_q <= select_exponent_delta_q;
                select_mantissa_large_q <= select_mantissa_large_q;
                select_mantissa_small_q <= select_mantissa_small_q;
                select_sign_q <= select_sign_q;
            end

            if (select_valid_q) begin
                align_bypass_q <= select_bypass_q;
                align_bypass_value_q <= select_bypass_value_q;
                align_sign_q <= select_sign_q;
                align_exponent_base_q <= select_exponent_base_q;
                align_mantissa_q <= combined_mantissa;
            end
            else begin
                align_bypass_q <= align_bypass_q;
                align_bypass_value_q <= align_bypass_value_q;
                align_sign_q <= align_sign_q;
                align_exponent_base_q <= align_exponent_base_q;
                align_mantissa_q <= align_mantissa_q;
            end

            if (align_valid_q) begin
                if (align_bypass_q) begin
                    sum <= align_bypass_value_q;
                end
                else begin
                    sum <= {align_sign_q, packed_exponent, packed_mantissa};
                end
            end
            else begin
                sum <= sum;
            end
        end
    end
endmodule
`default_nettype wire
