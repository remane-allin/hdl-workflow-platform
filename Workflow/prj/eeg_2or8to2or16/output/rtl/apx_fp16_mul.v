// Module: apx_fp16_mul
// Description: Bit-exact legacy approximate FP16 multiplier.
// Scope: Frozen EEG arithmetic primitive used by the convolution datapath.
// Spec Trace: REQ-EEG-RTL-COMPAT-001, REQ-EEG-FUNC-001.
`timescale 1ns/1ps
`default_nettype none

module apx_fp16_mul (
    input  wire [15:0] x,
    input  wire [15:0] y,
    output reg  [15:0] product
);
    reg sign_result;
    reg [4:0] exp_x;
    reg [4:0] exp_y;
    reg [4:0] exp_result;
    reg [5:0] exp_temp;
    reg [9:0] mant_x;
    reg [9:0] mant_y;
    reg [10:0] hidden_x;
    reg [10:0] hidden_y;
    reg [7:0] high_x;
    reg [7:0] high_y;
    reg [2:0] low_x;
    reg [2:0] low_y;
    reg [3:0] low_sum;
    reg [2:0] prod_x_low;
    reg [2:0] prod_y_low;
    reg [3:0] prod_low_sum;
    (* use_dsp = "no" *) reg [15:0] prod_high;
    reg [11:0] mant_temp;
    reg [9:0] mant_result;
    reg [4:0] bias;

    always @* begin
        exp_x = x[14:10];
        exp_y = y[14:10];
        mant_x = x[9:0];
        mant_y = y[9:0];
        sign_result = x[15] ^ y[15];
        hidden_x = {1'b1, mant_x};
        hidden_y = {1'b1, mant_y};
        high_x = hidden_x[10:3];
        high_y = hidden_y[10:3];
        low_x = hidden_x[2:0];
        low_y = hidden_y[2:0];
        low_sum = low_x + low_y;
        prod_x_low = {3{high_x[6]}} & low_x;
        prod_y_low = {3{high_y[6]}} & low_y;
        prod_low_sum = prod_x_low + prod_y_low;
        prod_high = high_x * high_y;
        mant_temp = prod_high[15:4] + low_sum + prod_low_sum;
        bias = mant_temp[11] ? 5'd14 : 5'd15;
        mant_result = mant_temp[11] ? mant_temp[10:1] : mant_temp[9:0];
        exp_temp = exp_x + exp_y;
        if (exp_temp < bias)
            exp_result = 5'd0;
        else if ((exp_temp - bias) > 31)
            exp_result = 5'd31;
        else
            exp_result = exp_temp - bias;
        product = {sign_result, exp_result, mant_result};
    end
endmodule
`default_nettype wire
