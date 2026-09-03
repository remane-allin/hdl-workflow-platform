//==============================================================================
// Module      : program_control_unit
// File        : program_control_unit.v
// Project     : eeg_ssvep_2to16
// Description : Program fetch/decode controller with one PC owner and three
//               reusable counted-loop contexts.
// Scope:
//   - Fetches trusted descriptors and owns program counter/loop state.
//   - Emits one descriptor transaction and waits for registered completion.
//   - Does not decode EEG, SSVEP, or any future signal profile.
// Spec Trace:
//   - REQ-RRB-006, REQ-RRB-011, REQ-RRB-012
//   - MOD-PROGRAM-CONTROL, IF-DESCRIPTOR
//
//
// Instruction classes (base[63:60]):
//   0x0 CONFIG      - issued to the execution layer, then jumps to ext0[12:4]
//   0x1 EXEC        - issued, then advances after completion
//   0x2 EMIT        - issued, then advances after completion
//   0x3 LOOP_SETUP  - internal, one extension row
//   0x4 LOOP_END    - internal, repeats the selected loop context
//   0x5 BRANCH      - internal, one extension row containing target PC
//   0x6 WAIT        - issued; the execution layer defines the waited event
//   0xF END         - terminates the session without issue
//
// LOOP_SETUP extension:
//   [ 8: 0] body PC
//   [20: 9] trip count
//   [32:21] initial loop index
//   [44:33] loop-index step
// The selected loop context is base[55:54].  Context value 3 aliases context
// 2 so the physical counter bank remains exactly three entries.
//
// BRANCH uses base[57:54] as condition and base[49:48] as loop selector:
//   0 always, 1 selected loop active, 2 selected loop complete, 3 never.
// Target PC is ext0[8:0].
//==============================================================================

`timescale 1ns/1ps
`default_nettype none

module program_control_unit (
    input  wire        clk,
    input  wire        reset_n,
    input  wire        start,
    output reg         busy,
    output reg         done,
    output reg         program_read_valid,
    output reg  [8:0]  program_read_address,
    input  wire        program_read_response_valid,
    input  wire [63:0] program_read_response_data,
    output reg         descriptor_valid,
    input  wire        descriptor_ready,
    output reg  [8:0]  descriptor_pc,
    output reg  [63:0] descriptor_base,
    output reg  [63:0] descriptor_ext0,
    output reg  [63:0] descriptor_ext1,
    output reg  [63:0] descriptor_ext2,
    output wire [11:0] loop_index0,
    output wire [11:0] loop_index1,
    output wire [11:0] loop_index2,
    input  wire        descriptor_complete
);
    localparam [3:0] OPCODE_CONFIG     = 4'h0;
    localparam [3:0] OPCODE_LOOP_SETUP = 4'h3;
    localparam [3:0] OPCODE_LOOP_END   = 4'h4;
    localparam [3:0] OPCODE_BRANCH     = 4'h5;
    localparam [3:0] OPCODE_END        = 4'hf;

    localparam [3:0] STATE_IDLE           = 4'd0;
    localparam [3:0] STATE_FETCH_BASE_REQ = 4'd1;
    localparam [3:0] STATE_WAIT_BASE      = 4'd2;
    localparam [3:0] STATE_FETCH_EXT_REQ  = 4'd3;
    localparam [3:0] STATE_WAIT_EXT       = 4'd4;
    localparam [3:0] STATE_EXECUTE        = 4'd5;
    localparam [3:0] STATE_ISSUE          = 4'd6;
    localparam [3:0] STATE_WAIT_COMPLETE  = 4'd7;
    localparam [3:0] STATE_DONE           = 4'd8;

    reg [3:0]  state_q;
    reg [8:0]  pc_q;
    reg [63:0] base_q;
    reg [63:0] ext0_q;
    reg [63:0] ext1_q;
    reg [63:0] ext2_q;
    reg [1:0]  extension_count_q;
    reg [1:0]  extension_index_q;

    reg [11:0] loop_value_q [0:2];
    reg [11:0] loop_remaining_q [0:2];
    reg [11:0] loop_step_q [0:2];
    reg [8:0]  loop_body_pc_q [0:2];

    wire [3:0] opcode = base_q[63:60];
    wire [8:0] sequential_pc = pc_q + 9'd1 +
                               {7'd0, extension_count_q};
    wire [1:0] raw_loop_select = base_q[55:54];
    wire [1:0] branch_loop_select = base_q[49:48];
    wire [1:0] loop_select = (raw_loop_select == 2'd3) ?
                             2'd2 : raw_loop_select;
    wire [1:0] branch_select = (branch_loop_select == 2'd3) ?
                               2'd2 : branch_loop_select;
    wire branch_taken =
        (base_q[57:54] == 4'd0) ? 1'b1 :
        (base_q[57:54] == 4'd1) ?
            (loop_remaining_q[branch_select] != 12'd0) :
        (base_q[57:54] == 4'd2) ?
            (loop_remaining_q[branch_select] == 12'd0) : 1'b0;

    assign loop_index0 = loop_value_q[0];
    assign loop_index1 = loop_value_q[1];
    assign loop_index2 = loop_value_q[2];

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            state_q <= STATE_IDLE;
            pc_q <= 9'd0;
            base_q <= 64'd0;
            ext0_q <= 64'd0;
            ext1_q <= 64'd0;
            ext2_q <= 64'd0;
            extension_count_q <= 2'd0;
            extension_index_q <= 2'd0;
            loop_value_q[0] <= 12'd0;
            loop_value_q[1] <= 12'd0;
            loop_value_q[2] <= 12'd0;
            loop_remaining_q[0] <= 12'd0;
            loop_remaining_q[1] <= 12'd0;
            loop_remaining_q[2] <= 12'd0;
            loop_step_q[0] <= 12'd0;
            loop_step_q[1] <= 12'd0;
            loop_step_q[2] <= 12'd0;
            loop_body_pc_q[0] <= 9'd0;
            loop_body_pc_q[1] <= 9'd0;
            loop_body_pc_q[2] <= 9'd0;
        end
        else begin
            case (state_q)
                STATE_IDLE: begin
                    if (start) begin
                        pc_q <= 9'd0;
                        loop_value_q[0] <= 12'd0;
                        loop_value_q[1] <= 12'd0;
                        loop_value_q[2] <= 12'd0;
                        loop_remaining_q[0] <= 12'd0;
                        loop_remaining_q[1] <= 12'd0;
                        loop_remaining_q[2] <= 12'd0;
                        loop_step_q[0] <= 12'd0;
                        loop_step_q[1] <= 12'd0;
                        loop_step_q[2] <= 12'd0;
                        loop_body_pc_q[0] <= 9'd0;
                        loop_body_pc_q[1] <= 9'd0;
                        loop_body_pc_q[2] <= 9'd0;
                        state_q <= STATE_FETCH_BASE_REQ;
                    end
                end

                STATE_FETCH_BASE_REQ: begin
                    state_q <= STATE_WAIT_BASE;
                end

                STATE_WAIT_BASE: begin
                    if (program_read_response_valid) begin
                        base_q <= program_read_response_data;
                        ext0_q <= 64'd0;
                        ext1_q <= 64'd0;
                        ext2_q <= 64'd0;
                        extension_count_q <=
                            program_read_response_data[59:58];
                        extension_index_q <= 2'd0;
                        if (program_read_response_data[63:60] == OPCODE_END)
                            state_q <= STATE_DONE;
                        else if (program_read_response_data[59:58] == 2'd0)
                            state_q <= STATE_EXECUTE;
                        else
                            state_q <= STATE_FETCH_EXT_REQ;
                    end
                end

                STATE_FETCH_EXT_REQ: begin
                    state_q <= STATE_WAIT_EXT;
                end

                STATE_WAIT_EXT: begin
                    if (program_read_response_valid) begin
                        case (extension_index_q)
                            2'd0: ext0_q <= program_read_response_data;
                            2'd1: ext1_q <= program_read_response_data;
                            default: ext2_q <= program_read_response_data;
                        endcase
                        if ((extension_index_q + 2'd1) >=
                            extension_count_q) begin
                            state_q <= STATE_EXECUTE;
                        end
                        else begin
                            extension_index_q <= extension_index_q + 2'd1;
                            state_q <= STATE_FETCH_EXT_REQ;
                        end
                    end
                end

                STATE_EXECUTE: begin
                    case (opcode)
                        OPCODE_LOOP_SETUP: begin
                            loop_body_pc_q[loop_select] <= ext0_q[8:0];
                            loop_remaining_q[loop_select] <= ext0_q[20:9];
                            loop_value_q[loop_select] <= ext0_q[32:21];
                            loop_step_q[loop_select] <= ext0_q[44:33];
                            pc_q <= sequential_pc;
                            state_q <= STATE_FETCH_BASE_REQ;
                        end

                        OPCODE_LOOP_END: begin
                            if (loop_remaining_q[loop_select] > 12'd1) begin
                                loop_remaining_q[loop_select] <=
                                    loop_remaining_q[loop_select] - 12'd1;
                                loop_value_q[loop_select] <=
                                    loop_value_q[loop_select] +
                                    loop_step_q[loop_select];
                                pc_q <= loop_body_pc_q[loop_select];
                            end
                            else begin
                                loop_remaining_q[loop_select] <= 12'd0;
                                pc_q <= sequential_pc;
                            end
                            state_q <= STATE_FETCH_BASE_REQ;
                        end

                        OPCODE_BRANCH: begin
                            pc_q <= branch_taken ? ext0_q[8:0] : sequential_pc;
                            state_q <= STATE_FETCH_BASE_REQ;
                        end

                        default: begin
                            state_q <= STATE_ISSUE;
                        end
                    endcase
                end

                STATE_ISSUE: begin
                    if (descriptor_ready)
                        state_q <= STATE_WAIT_COMPLETE;
                end

                STATE_WAIT_COMPLETE: begin
                    if (descriptor_complete) begin
                        if (opcode == OPCODE_CONFIG)
                            pc_q <= ext0_q[12:4];
                        else
                            pc_q <= sequential_pc;
                        state_q <= STATE_FETCH_BASE_REQ;
                    end
                end

                STATE_DONE: begin
                    state_q <= STATE_IDLE;
                end

                default: begin
                    state_q <= STATE_IDLE;
                end
            endcase
        end
    end

    always @(*) begin
        busy = 1'b1;
        done = 1'b0;
        program_read_valid = 1'b0;
        program_read_address = pc_q;
        descriptor_valid = 1'b0;
        descriptor_pc = pc_q;
        descriptor_base = base_q;
        descriptor_ext0 = ext0_q;
        descriptor_ext1 = ext1_q;
        descriptor_ext2 = ext2_q;

        case (state_q)
            STATE_IDLE: busy = 1'b0;
            STATE_FETCH_BASE_REQ: begin
                program_read_valid = 1'b1;
                program_read_address = pc_q;
            end
            STATE_FETCH_EXT_REQ: begin
                program_read_valid = 1'b1;
                program_read_address = pc_q + 9'd1 +
                                       {7'd0, extension_index_q};
            end
            STATE_ISSUE: descriptor_valid = 1'b1;
            STATE_DONE: begin
                busy = 1'b0;
                done = 1'b1;
            end
            default: begin
            end
        endcase
    end
endmodule
`default_nettype wire
