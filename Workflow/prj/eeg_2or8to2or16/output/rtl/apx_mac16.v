// Module: apx_mac16
// Description: Registered sixteen-input approximate FP16 MAC pipeline.
// Scope: Frozen EEG convolution arithmetic with legacy reduction ordering.
// Spec Trace: REQ-EEG-RTL-COMPAT-001, REQ-EEG-FUNC-001,
//             REQ-EEG-V3-OPT-002.
`timescale 1ns/1ps
`default_nettype none

module apx_mac16 (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         input_valid,
    input  wire [4:0]   valid_lanes,
    input  wire         split8_mode,
    input  wire [255:0] data_bus,
    input  wire [255:0] weight_bus,
    output reg          output8_valid,
    output reg  [15:0]  result8,
    output reg  [15:0]  result8_upper,
    output reg          output_valid,
    output reg  [15:0]  result
);
    reg [255:0] data_bus_q;
    reg [255:0] weight_bus_q;
    reg [255:0] product_bus_q;
    reg [127:0] sum2_bus_q;
    reg [63:0] sum4_bus_q;
    reg [31:0] sum8_bus_q;
    reg [15:0] input_lane_valid_q;
    reg [15:0] product_lane_valid_q;
    reg [7:0] sum2_lane_valid_q;
    reg [3:0] sum4_lane_valid_q;
    reg [1:0] sum8_lane_valid_q;
    reg input_valid_q;
    reg product_valid_q;
    reg sum2_valid_q;
    reg sum4_valid_q;
    reg sum8_valid_q;
    wire [255:0] product_bus_comb;
    wire [127:0] sum2_bus_comb;
    wire [63:0] sum4_bus_comb;
    wire [31:0] sum8_bus_comb;
    wire [15:0] result_comb;
    wire [15:0] input_lane_valid_comb;
    genvar index;

    generate
        for (index = 0; index < 8; index = index + 1) begin : gen_lane_valid
            assign input_lane_valid_comb[index] = (valid_lanes > index);
            assign input_lane_valid_comb[index + 8] = split8_mode ?
                (valid_lanes > index) : (valid_lanes > (index + 8));
        end
    endgenerate

    generate
        for (index = 0; index < 16; index = index + 1) begin : gen_mul
            apx_fp16_mul mul_inst (
                .x(data_bus_q[index*16 +: 16]),
                .y(weight_bus_q[index*16 +: 16]),
                .product(product_bus_comb[index*16 +: 16])
            );
        end
        for (index = 0; index < 8; index = index + 1) begin : gen_add2
            wire [15:0] add_result;
            apx_fp16_add add_inst (
                .x(product_bus_q[(index*2)*16 +: 16]),
                .y(product_bus_q[(index*2+1)*16 +: 16]),
                .sum(add_result)
            );
            assign sum2_bus_comb[index*16 +: 16] =
                product_lane_valid_q[index*2+1] ? add_result :
                product_bus_q[(index*2)*16 +: 16];
        end
        for (index = 0; index < 4; index = index + 1) begin : gen_add4
            wire [15:0] add_result;
            apx_fp16_add add_inst (
                .x(sum2_bus_q[(index*2)*16 +: 16]),
                .y(sum2_bus_q[(index*2+1)*16 +: 16]),
                .sum(add_result)
            );
            assign sum4_bus_comb[index*16 +: 16] =
                sum2_lane_valid_q[index*2+1] ? add_result :
                sum2_bus_q[(index*2)*16 +: 16];
        end
        for (index = 0; index < 2; index = index + 1) begin : gen_add8
            wire [15:0] add_result;
            apx_fp16_add add_inst (
                .x(sum4_bus_q[(index*2)*16 +: 16]),
                .y(sum4_bus_q[(index*2+1)*16 +: 16]),
                .sum(add_result)
            );
            assign sum8_bus_comb[index*16 +: 16] =
                sum4_lane_valid_q[index*2+1] ? add_result :
                sum4_bus_q[(index*2)*16 +: 16];
        end
    endgenerate

    apx_fp16_add add16 (
        .x(sum8_bus_q[15:0]),
        .y(sum8_bus_q[31:16]),
        .sum(result_comb)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            data_bus_q <= 256'd0;
            weight_bus_q <= 256'd0;
            product_bus_q <= 256'd0;
            sum2_bus_q <= 128'd0;
            sum4_bus_q <= 64'd0;
            sum8_bus_q <= 32'd0;
            input_lane_valid_q <= 16'd0;
            product_lane_valid_q <= 16'd0;
            sum2_lane_valid_q <= 8'd0;
            sum4_lane_valid_q <= 4'd0;
            sum8_lane_valid_q <= 2'd0;
            input_valid_q <= 1'b0;
            product_valid_q <= 1'b0;
            sum2_valid_q <= 1'b0;
            sum4_valid_q <= 1'b0;
            sum8_valid_q <= 1'b0;
            output8_valid <= 1'b0;
            result8 <= 16'd0;
            result8_upper <= 16'd0;
            output_valid <= 1'b0;
            result <= 16'd0;
        end
        else begin
            input_valid_q <= input_valid;
            product_valid_q <= input_valid_q;
            sum2_valid_q <= product_valid_q;
            sum4_valid_q <= sum2_valid_q;
            sum8_valid_q <= sum4_valid_q;
            output8_valid <= sum4_valid_q;
            output_valid <= sum8_valid_q;

            if (input_valid) begin
                data_bus_q <= data_bus;
                weight_bus_q <= weight_bus;
                input_lane_valid_q <= input_lane_valid_comb;
            end
            else begin
                data_bus_q <= data_bus_q;
                weight_bus_q <= weight_bus_q;
            end

            if (input_valid_q) begin
                product_bus_q <= product_bus_comb;
                product_lane_valid_q <= input_lane_valid_q;
            end
            else begin
                product_bus_q <= product_bus_q;
            end

            if (product_valid_q) begin
                sum2_bus_q <= sum2_bus_comb;
                sum2_lane_valid_q <= {
                    product_lane_valid_q[14] | product_lane_valid_q[15],
                    product_lane_valid_q[12] | product_lane_valid_q[13],
                    product_lane_valid_q[10] | product_lane_valid_q[11],
                    product_lane_valid_q[8] | product_lane_valid_q[9],
                    product_lane_valid_q[6] | product_lane_valid_q[7],
                    product_lane_valid_q[4] | product_lane_valid_q[5],
                    product_lane_valid_q[2] | product_lane_valid_q[3],
                    product_lane_valid_q[0] | product_lane_valid_q[1]
                };
            end
            else begin
                sum2_bus_q <= sum2_bus_q;
            end

            if (sum2_valid_q) begin
                sum4_bus_q <= sum4_bus_comb;
                sum4_lane_valid_q <= {
                    sum2_lane_valid_q[6] | sum2_lane_valid_q[7],
                    sum2_lane_valid_q[4] | sum2_lane_valid_q[5],
                    sum2_lane_valid_q[2] | sum2_lane_valid_q[3],
                    sum2_lane_valid_q[0] | sum2_lane_valid_q[1]
                };
            end
            else begin
                sum4_bus_q <= sum4_bus_q;
            end

            if (sum4_valid_q) begin
                sum8_bus_q <= sum8_bus_comb;
                sum8_lane_valid_q <= {
                    sum4_lane_valid_q[2] | sum4_lane_valid_q[3],
                    sum4_lane_valid_q[0] | sum4_lane_valid_q[1]
                };
                result8 <= sum8_bus_comb[15:0];
                result8_upper <= sum8_bus_comb[31:16];
            end
            else begin
                sum8_bus_q <= sum8_bus_q;
                result8 <= result8;
                result8_upper <= result8_upper;
            end

            if (sum8_valid_q) begin
                result <= sum8_lane_valid_q[1] ?
                    result_comb : sum8_bus_q[15:0];
            end
            else begin
                result <= result;
            end
        end
    end
endmodule
`default_nettype wire
