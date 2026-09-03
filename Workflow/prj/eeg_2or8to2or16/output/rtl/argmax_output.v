// Module: argmax_output
// Description: Selects the signed FP16 maximum from sixteen class scores.
// Scope: Frozen class-result, LED, and one-cycle completion interface.
// Spec Trace: REQ-EEG-FUNC-001, REQ-EEG-LED-001.
`timescale 1ns/1ps
`default_nettype none

module argmax_output (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        score_valid,
    output wire        score_ready,
    input  wire [15:0] score_data,
    input  wire [3:0]  class_index,
    input  wire        score_last,
    output reg  [31:0] result,
    output reg         infer_done,
    output reg  [3:0]  class_led,
    output reg         class_count_error
);
    reg [15:0] maximum_score;
    reg [3:0] maximum_index;
    reg [4:0] accepted_count;
    reg candidate_greater;

    assign score_ready = 1'b1;

    always @* begin
        candidate_greater = 1'b0;
        if (!score_data[15] && maximum_score[15])
            candidate_greater = 1'b1;
        else if (score_data[15] == maximum_score[15]) begin
            if (!score_data[15])
                candidate_greater = score_data[14:0] > maximum_score[14:0];
            else
                candidate_greater = score_data[14:0] < maximum_score[14:0];
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            maximum_score <= 16'd0;
            maximum_index <= 4'd0;
            accepted_count <= 5'd0;
            result <= 32'd0;
            infer_done <= 1'b0;
            class_led <= 4'd0;
            class_count_error <= 1'b0;
        end
        else begin
            infer_done <= 1'b0;
            if (score_valid && score_ready) begin
                if (accepted_count == 0) begin
                    maximum_score <= score_data;
                    maximum_index <= class_index;
                end
                else if (candidate_greater) begin
                    maximum_score <= score_data;
                    maximum_index <= class_index;
                end

                if (score_last) begin
                    if ((accepted_count != 15) || (class_index != 15))
                        class_count_error <= 1'b1;
                    if (accepted_count == 0 || candidate_greater) begin
                        result <= {28'd0, class_index};
                        class_led <= class_index;
                    end
                    else begin
                        result <= {28'd0, maximum_index};
                        class_led <= maximum_index;
                    end
                    infer_done <= 1'b1;
                    accepted_count <= 5'd0;
                end
                else begin
                    accepted_count <= accepted_count + 1'b1;
                end
            end
        end
    end
endmodule
`default_nettype wire
