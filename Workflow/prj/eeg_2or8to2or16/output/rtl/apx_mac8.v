// Module: apx_mac8
// Description: Registered eight-input approximate FP16 MAC pipeline.
// Scope: Frozen EEG separable arithmetic with legacy reduction ordering.
// Spec Trace: REQ-EEG-RTL-COMPAT-001, REQ-EEG-FUNC-001.
`timescale 1ns/1ps
`default_nettype none

module apx_mac8 (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         input_valid,
    input  wire [127:0] data_bus,
    input  wire [127:0] weight_bus,
    output reg          output_valid,
    output reg  [15:0]  result
);
    reg [127:0] data_bus_q;
    reg [127:0] weight_bus_q;
    reg [127:0] product_bus_q;
    reg [63:0] sum2_bus_q;
    reg [31:0] sum4_bus_q;
    reg input_valid_q;
    reg product_valid_q;
    reg sum2_valid_q;
    reg sum4_valid_q;
    wire [127:0] product_bus_comb;
    wire [63:0] sum2_bus_comb;
    wire [31:0] sum4_bus_comb;
    wire [15:0] result_comb;
    genvar index;

    generate
        for (index = 0; index < 8; index = index + 1) begin : gen_mul
            apx_fp16_mul mul_inst (
                .x(data_bus_q[index*16 +: 16]),
                .y(weight_bus_q[index*16 +: 16]),
                .product(product_bus_comb[index*16 +: 16])
            );
        end
        for (index = 0; index < 4; index = index + 1) begin : gen_add2
            apx_fp16_add add_inst (
                .x(product_bus_q[(index*2)*16 +: 16]),
                .y(product_bus_q[(index*2+1)*16 +: 16]),
                .sum(sum2_bus_comb[index*16 +: 16])
            );
        end
        for (index = 0; index < 2; index = index + 1) begin : gen_add4
            apx_fp16_add add_inst (
                .x(sum2_bus_q[(index*2)*16 +: 16]),
                .y(sum2_bus_q[(index*2+1)*16 +: 16]),
                .sum(sum4_bus_comb[index*16 +: 16])
            );
        end
    endgenerate

    apx_fp16_add add8 (
        .x(sum4_bus_q[15:0]),
        .y(sum4_bus_q[31:16]),
        .sum(result_comb)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            data_bus_q <= 128'd0;
            weight_bus_q <= 128'd0;
            product_bus_q <= 128'd0;
            sum2_bus_q <= 64'd0;
            sum4_bus_q <= 32'd0;
            input_valid_q <= 1'b0;
            product_valid_q <= 1'b0;
            sum2_valid_q <= 1'b0;
            sum4_valid_q <= 1'b0;
            output_valid <= 1'b0;
            result <= 16'd0;
        end
        else begin
            input_valid_q <= input_valid;
            product_valid_q <= input_valid_q;
            sum2_valid_q <= product_valid_q;
            sum4_valid_q <= sum2_valid_q;
            output_valid <= sum4_valid_q;

            if (input_valid) begin
                data_bus_q <= data_bus;
                weight_bus_q <= weight_bus;
            end
            else begin
                data_bus_q <= data_bus_q;
                weight_bus_q <= weight_bus_q;
            end

            if (input_valid_q) begin
                product_bus_q <= product_bus_comb;
            end
            else begin
                product_bus_q <= product_bus_q;
            end

            if (product_valid_q) begin
                sum2_bus_q <= sum2_bus_comb;
            end
            else begin
                sum2_bus_q <= sum2_bus_q;
            end

            if (sum2_valid_q) begin
                sum4_bus_q <= sum4_bus_comb;
            end
            else begin
                sum4_bus_q <= sum4_bus_q;
            end

            if (sum4_valid_q) begin
                result <= result_comb;
            end
            else begin
                result <= result;
            end
        end
    end
endmodule
`default_nettype wire
