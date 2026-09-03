//==============================================================================
// Module      : apx_fp16_mul_pipe
// File        : apx_fp16_mul_pipe.v
// Project     : eeg_ssvep_2to16
// Description : Four-stage bit-exact approximate FP16 multiplier pipeline.
// Scope:
//   - Owns APX multiplier decode, product, correction, and packing registers.
//   - Does not select compute modes, addresses, destinations, or profiles.
// Spec Trace:
//   - REQ-RRB-006, REQ-RRB-011, REQ-RRB-012
//   - DF-APX-SHARED, LAT-APX
// Notes:
//   - Accepts one operand pair per cycle and has a four-cycle dependency path.
//   - The 8x8 mantissa product is forced into LUT fabric; DSP use is forbidden.
//==============================================================================
`timescale 1ns/1ps
`default_nettype none

module apx_fp16_mul_pipe (
    input  wire        clk,
    input  wire        reset_n,
    input  wire        input_valid,
    input  wire [15:0] operand_x,
    input  wire [15:0] operand_y,
    output reg         output_valid,
    output reg  [15:0] product
);
    reg        decode_valid_q;
    reg        decode_sign_q;
    reg [5:0]  decode_exponent_q;
    reg [7:0]  decode_high_x_q;
    reg [7:0]  decode_high_y_q;
    reg [3:0]  decode_low_sum_q;
    reg [3:0]  decode_correction_sum_q;

    reg        product_valid_q;
    reg        product_sign_q;
    reg [5:0]  product_exponent_q;
    (* use_dsp = "no" *) reg [15:0] product_high_q;
    reg [3:0]  product_low_sum_q;
    reg [3:0]  product_correction_sum_q;

    reg        correction_valid_q;
    reg        correction_sign_q;
    reg [5:0]  correction_exponent_q;
    reg [11:0] correction_mantissa_q;

    wire [10:0] hidden_x;
    wire [10:0] hidden_y;
    wire [2:0] low_x;
    wire [2:0] low_y;
    wire [2:0] correction_x;
    wire [2:0] correction_y;
    reg  [4:0] packed_exponent;
    reg  [4:0] packed_bias;
    reg  [9:0] packed_mantissa;

    assign hidden_x = {1'b1, operand_x[9:0]};
    assign hidden_y = {1'b1, operand_y[9:0]};
    assign low_x = hidden_x[2:0];
    assign low_y = hidden_y[2:0];
    assign correction_x = {3{hidden_x[9]}} & low_x;
    assign correction_y = {3{hidden_y[9]}} & low_y;

    always @(*) begin
        if (correction_mantissa_q[11]) begin
            packed_bias = 5'd14;
            packed_mantissa = correction_mantissa_q[10:1];
        end
        else begin
            packed_bias = 5'd15;
            packed_mantissa = correction_mantissa_q[9:0];
        end

        if (correction_exponent_q < packed_bias) begin
            packed_exponent = 5'd0;
        end
        else if ((correction_exponent_q - packed_bias) > 6'd31) begin
            packed_exponent = 5'd31;
        end
        else begin
            packed_exponent = correction_exponent_q - packed_bias;
        end
    end

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            decode_valid_q <= 1'b0;
            decode_sign_q <= 1'b0;
            decode_exponent_q <= 6'd0;
            decode_high_x_q <= 8'd0;
            decode_high_y_q <= 8'd0;
            decode_low_sum_q <= 4'd0;
            decode_correction_sum_q <= 4'd0;
            product_valid_q <= 1'b0;
            product_sign_q <= 1'b0;
            product_exponent_q <= 6'd0;
            product_high_q <= 16'd0;
            product_low_sum_q <= 4'd0;
            product_correction_sum_q <= 4'd0;
            correction_valid_q <= 1'b0;
            correction_sign_q <= 1'b0;
            correction_exponent_q <= 6'd0;
            correction_mantissa_q <= 12'd0;
            output_valid <= 1'b0;
            product <= 16'd0;
        end
        else begin
            decode_valid_q <= input_valid;
            product_valid_q <= decode_valid_q;
            correction_valid_q <= product_valid_q;
            output_valid <= correction_valid_q;

            if (input_valid) begin
                decode_sign_q <= operand_x[15] ^ operand_y[15];
                decode_exponent_q <= operand_x[14:10] + operand_y[14:10];
                decode_high_x_q <= hidden_x[10:3];
                decode_high_y_q <= hidden_y[10:3];
                decode_low_sum_q <= low_x + low_y;
                decode_correction_sum_q <= correction_x + correction_y;
            end
            else begin
                decode_sign_q <= decode_sign_q;
                decode_exponent_q <= decode_exponent_q;
                decode_high_x_q <= decode_high_x_q;
                decode_high_y_q <= decode_high_y_q;
                decode_low_sum_q <= decode_low_sum_q;
                decode_correction_sum_q <= decode_correction_sum_q;
            end

            if (decode_valid_q) begin
                product_sign_q <= decode_sign_q;
                product_exponent_q <= decode_exponent_q;
                product_high_q <= decode_high_x_q * decode_high_y_q;
                product_low_sum_q <= decode_low_sum_q;
                product_correction_sum_q <= decode_correction_sum_q;
            end
            else begin
                product_sign_q <= product_sign_q;
                product_exponent_q <= product_exponent_q;
                product_high_q <= product_high_q;
                product_low_sum_q <= product_low_sum_q;
                product_correction_sum_q <= product_correction_sum_q;
            end

            if (product_valid_q) begin
                correction_sign_q <= product_sign_q;
                correction_exponent_q <= product_exponent_q;
                correction_mantissa_q <= product_high_q[15:4] +
                    product_low_sum_q + product_correction_sum_q;
            end
            else begin
                correction_sign_q <= correction_sign_q;
                correction_exponent_q <= correction_exponent_q;
                correction_mantissa_q <= correction_mantissa_q;
            end

            if (correction_valid_q) begin
                product <= {
                    correction_sign_q,
                    packed_exponent,
                    packed_mantissa
                };
            end
            else begin
                product <= product;
            end
        end
    end
endmodule
`default_nettype wire
