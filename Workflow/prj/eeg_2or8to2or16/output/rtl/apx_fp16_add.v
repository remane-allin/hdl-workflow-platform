// Module: apx_fp16_add
// Description: Bit-exact resource-optimized legacy approximate FP16 adder.
// Scope: Frozen EEG arithmetic primitive used by the convolution datapath.
// Spec Trace: REQ-EEG-RTL-COMPAT-001, REQ-EEG-FUNC-001.
`timescale 1ns/1ps
`default_nettype none

module apx_fp16_add (
    input  wire [15:0] x,
    input  wire [15:0] y,
    output reg  [15:0] sum
);
    reg sign_sum;
    reg sign_large;
    reg [4:0] exp_x;
    reg [4:0] exp_y;
    reg [4:0] exp_base;
    reg [4:0] exp_delta;
    reg [4:0] exp_sum;
    reg [9:0] mant_x;
    reg [9:0] mant_y;
    reg [9:0] mant_sum;
    reg [10:0] mant_large;
    reg [10:0] mant_small;
    reg [10:0] mant_aligned;
    reg [11:0] mant_temp;
    reg [3:0] align_shift;
    reg [3:0] normalize_shift;
    reg add_normalize;

    always @* begin
        exp_x = x[14:10];
        exp_y = y[14:10];
        mant_x = x[9:0];
        mant_y = y[9:0];

        if (exp_x > exp_y) begin
            exp_base = exp_x;
            exp_delta = exp_x - exp_y;
            mant_large = {1'b1, mant_x};
            mant_small = {1'b1, mant_y};
            sign_large = x[15];
        end
        else if (exp_x < exp_y) begin
            exp_base = exp_y;
            exp_delta = exp_y - exp_x;
            mant_large = {1'b1, mant_y};
            mant_small = {1'b1, mant_x};
            sign_large = y[15];
        end
        else if (mant_x > mant_y) begin
            exp_base = exp_x;
            exp_delta = 5'd0;
            mant_large = {1'b1, mant_x};
            mant_small = {1'b1, mant_y};
            sign_large = x[15];
        end
        else begin
            exp_base = exp_y;
            exp_delta = 5'd0;
            mant_large = {1'b1, mant_y};
            mant_small = {1'b1, mant_x};
            sign_large = y[15];
        end

        align_shift = (exp_delta > 5'd10) ?
            4'd11 : exp_delta[3:0];
        mant_aligned = mant_small >> align_shift;

        if (x[15] ^ y[15]) begin
            mant_temp = {1'b0, mant_large} -
                {1'b0, mant_aligned};
            sign_sum = sign_large;
        end
        else begin
            mant_temp = {1'b0, mant_large} +
                {1'b0, mant_aligned};
            sign_sum = x[15];
        end

        add_normalize = 1'b0;
        casez (mant_temp)
            12'b1???????????: begin
                normalize_shift = 4'd1;
                add_normalize = 1'b1;
            end
            12'b01??????????: normalize_shift = 4'd0;
            12'b001?????????: normalize_shift = 4'd1;
            12'b0001????????: normalize_shift = 4'd2;
            12'b00001???????: normalize_shift = 4'd3;
            12'b000001??????: normalize_shift = 4'd4;
            12'b0000001?????: normalize_shift = 4'd5;
            12'b00000001????: normalize_shift = 4'd6;
            12'b000000001???: normalize_shift = 4'd7;
            12'b0000000001??: normalize_shift = 4'd8;
            12'b00000000001?: normalize_shift = 4'd9;
            default: normalize_shift = 4'd10;
        endcase

        if (add_normalize) begin
            mant_sum = mant_temp[10:1];
            exp_sum = (exp_base == 5'd31) ?
                5'd31 : exp_base + 1'b1;
        end
        else begin
            mant_sum = mant_temp[9:0] << normalize_shift;
            exp_sum = (exp_base <= normalize_shift) ?
                5'd0 : exp_base - normalize_shift;
        end

        sum = {sign_sum, exp_sum, mant_sum};
    end
endmodule
`default_nettype wire
