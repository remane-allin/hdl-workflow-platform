//==============================================================================
// Module      : shared_kernel_step_sequencer
// Project     : eeg_ssvep_2to16
// Description : Profile-independent compound-command step projection.
// Scope:
//   - Decodes the control fields consumed from the canonical 64-bit step word.
//   - Observes only registered, predecoded completion events.
//   - Owns the fixed transitions shared by Gram, factorization, and solve.
//   - The table is hardware-local; it is not PS-loaded CPU-style microcode.
// Spec Trace:
//   - REQ-RRB-002, REQ-RRB-006, REQ-RRB-011, REQ-RRB-023
//   - MOD-SHARED-STEP, IF-COMMAND-EVENT
//==============================================================================
`timescale 1ns/1ps
`default_nettype none

module shared_kernel_step_sequencer (
    input  wire [1:0]  operator_select,
    input  wire [4:0]  step_index,

    input  wire        service_request_fire,
    input  wire        apx_request_fire,
    input  wire [10:0] completion_events,
    input  wire        retire_complete,
    input  wire        scalar_request_fire,

    output wire        retire_phase,
    output wire        transition_valid,
    output wire        advance,
    output wire [4:0]  next_step_index
);
    localparam [1:0] OPERATOR_PAIRWISE_STAT = 2'd0;
    localparam [1:0] OPERATOR_TRIANGULAR    = 2'd1;
    localparam [1:0] OPERATOR_BACKSUB       = 2'd2;

    localparam [4:0] EVENT_NONE            = 5'd0;
    localparam [4:0] EVENT_ALWAYS          = 5'd1;
    localparam [4:0] EVENT_SERVICE_REQUEST = 5'd2;
    localparam [4:0] EVENT_APX_REQUEST     = 5'd3;
    localparam [4:0] EVENT_PRODUCT_B001    = 5'd4;
    localparam [4:0] EVENT_PRODUCT_E000    = 5'd5;
    localparam [4:0] EVENT_PRODUCT_E003    = 5'd6;
    localparam [4:0] EVENT_PRODUCT_E004    = 5'd7;
    localparam [4:0] EVENT_PRODUCT_F400    = 5'd8;
    localparam [4:0] EVENT_PAIR_D202       = 5'd9;
    localparam [4:0] EVENT_REDUCE_E002     = 5'd10;
    localparam [4:0] EVENT_REDUCE_D200     = 5'd11;
    localparam [4:0] EVENT_POST_ADD_E001   = 5'd12;
    localparam [4:0] EVENT_POST_ADD_E005   = 5'd13;
    localparam [4:0] EVENT_POST_ADD_E1XX   = 5'd14;
    localparam [4:0] EVENT_RETIRE          = 5'd15;
    localparam [4:0] EVENT_SCALAR_REQUEST  = 5'd16;

    // Only retire owner, decoded completion event, and next PC affect control.
    // APX tags are predecoded at the registered result boundary, so they can
    // never enter this table or the phase-register D cone.
    reg [10:0] step_projection;
    reg step_entry_valid;
    reg event_fire;

    wire [6:0] step_table_address = {operator_select, step_index};
    wire projected_retire = step_projection[10];
    wire [4:0] wait_event = step_projection[9:5];
    wire [4:0] projected_next = step_projection[4:0];

    assign retire_phase = step_entry_valid && projected_retire;
    assign transition_valid = step_entry_valid &&
        (wait_event != EVENT_NONE);
    assign next_step_index = transition_valid ? projected_next : step_index;
    assign advance = transition_valid && event_fire;

    function [10:0] project_step;
        input retire_owner;
        input [4:0] event_kind;
        input [4:0] next_index;
        begin
            project_step = {retire_owner, event_kind, next_index};
        end
    endfunction

    always @(*) begin
        step_projection = 11'd0;
        step_entry_valid = 1'b1;
        case (step_table_address)
            // Pairwise-statistics template.
            {OPERATOR_PAIRWISE_STAT, 5'd3},
            {OPERATOR_PAIRWISE_STAT, 5'd13},
            {OPERATOR_PAIRWISE_STAT, 5'd14},
            {OPERATOR_PAIRWISE_STAT, 5'd22}:
                step_projection = project_step(
                    1'b1, EVENT_NONE, 5'd0);
            {OPERATOR_PAIRWISE_STAT, 5'd23}:
                step_projection = project_step(
                    1'b0, EVENT_ALWAYS, 5'd1);
            {OPERATOR_PAIRWISE_STAT, 5'd1}:
                step_projection = project_step(
                    1'b0, EVENT_APX_REQUEST, 5'd2);
            {OPERATOR_PAIRWISE_STAT, 5'd2}:
                step_projection = project_step(
                    1'b0, EVENT_PRODUCT_B001, 5'd3);
            {OPERATOR_PAIRWISE_STAT, 5'd4}:
                step_projection = project_step(
                    1'b0, EVENT_SERVICE_REQUEST, 5'd5);
            {OPERATOR_PAIRWISE_STAT, 5'd6}:
                step_projection = project_step(
                    1'b0, EVENT_SERVICE_REQUEST, 5'd7);
            {OPERATOR_PAIRWISE_STAT, 5'd10}:
                step_projection = project_step(
                    1'b0, EVENT_APX_REQUEST, 5'd11);
            {OPERATOR_PAIRWISE_STAT, 5'd11}:
                step_projection = project_step(
                    1'b0, EVENT_PRODUCT_E000, 5'd27);
            {OPERATOR_PAIRWISE_STAT, 5'd27}:
                step_projection = project_step(
                    1'b0, EVENT_SCALAR_REQUEST, 5'd12);
            {OPERATOR_PAIRWISE_STAT, 5'd12}:
                step_projection = project_step(
                    1'b0, EVENT_POST_ADD_E001, 5'd13);
            {OPERATOR_PAIRWISE_STAT, 5'd25}:
                step_projection = project_step(
                    1'b0, EVENT_ALWAYS, 5'd15);
            {OPERATOR_PAIRWISE_STAT, 5'd15}:
                step_projection = project_step(
                    1'b0, EVENT_APX_REQUEST, 5'd16);
            {OPERATOR_PAIRWISE_STAT, 5'd16}:
                step_projection = project_step(
                    1'b0, EVENT_REDUCE_E002, 5'd28);
            {OPERATOR_PAIRWISE_STAT, 5'd28}:
                step_projection = project_step(
                    1'b0, EVENT_APX_REQUEST, 5'd17);
            {OPERATOR_PAIRWISE_STAT, 5'd17}:
                step_projection = project_step(
                    1'b0, EVENT_PRODUCT_E003, 5'd29);
            {OPERATOR_PAIRWISE_STAT, 5'd29}:
                step_projection = project_step(
                    1'b0, EVENT_APX_REQUEST, 5'd18);
            {OPERATOR_PAIRWISE_STAT, 5'd18}:
                step_projection = project_step(
                    1'b0, EVENT_PRODUCT_E004, 5'd30);
            {OPERATOR_PAIRWISE_STAT, 5'd30}:
                step_projection = project_step(
                    1'b0, EVENT_SCALAR_REQUEST, 5'd19);
            {OPERATOR_PAIRWISE_STAT, 5'd19}:
                step_projection = project_step(
                    1'b0, EVENT_POST_ADD_E005, 5'd31);
            {OPERATOR_PAIRWISE_STAT, 5'd31}:
                step_projection = project_step(
                    1'b0, EVENT_ALWAYS, 5'd20);
            {OPERATOR_PAIRWISE_STAT, 5'd20}:
                step_projection = project_step(
                    1'b0, EVENT_SCALAR_REQUEST, 5'd21);
            {OPERATOR_PAIRWISE_STAT, 5'd21}:
                step_projection = project_step(
                    1'b0, EVENT_POST_ADD_E1XX, 5'd22);

            // Triangular-update template.
            {OPERATOR_TRIANGULAR, 5'd24}:
                step_projection = project_step(
                    1'b1, EVENT_NONE, 5'd0);
            {OPERATOR_TRIANGULAR, 5'd0}:
                step_projection = project_step(
                    1'b0, EVENT_SERVICE_REQUEST, 5'd1);
            {OPERATOR_TRIANGULAR, 5'd3}:
                step_projection = project_step(
                    1'b0, EVENT_SERVICE_REQUEST, 5'd4);
            {OPERATOR_TRIANGULAR, 5'd7}:
                step_projection = project_step(
                    1'b0, EVENT_APX_REQUEST, 5'd8);
            {OPERATOR_TRIANGULAR, 5'd8}:
                step_projection = project_step(
                    1'b0, EVENT_REDUCE_D200, 5'd9);
            {OPERATOR_TRIANGULAR, 5'd9}:
                step_projection = project_step(
                    1'b0, EVENT_APX_REQUEST, 5'd10);
            {OPERATOR_TRIANGULAR, 5'd18}:
                step_projection = project_step(
                    1'b0, EVENT_APX_REQUEST, 5'd19);
            {OPERATOR_TRIANGULAR, 5'd19}:
                step_projection = project_step(
                    1'b0, EVENT_PAIR_D202, 5'd20);

            // Back-substitution template.
            {OPERATOR_BACKSUB, 5'd20}:
                step_projection = project_step(
                    1'b1, EVENT_RETIRE, 5'd21);
            {OPERATOR_BACKSUB, 5'd21}:
                step_projection = project_step(
                    1'b1, EVENT_NONE, 5'd0);
            {OPERATOR_BACKSUB, 5'd0}:
                step_projection = project_step(
                    1'b0, EVENT_SERVICE_REQUEST, 5'd1);
            {OPERATOR_BACKSUB, 5'd2}:
                step_projection = project_step(
                    1'b0, EVENT_SERVICE_REQUEST, 5'd3);
            {OPERATOR_BACKSUB, 5'd4}:
                step_projection = project_step(
                    1'b0, EVENT_SERVICE_REQUEST, 5'd5);
            {OPERATOR_BACKSUB, 5'd8}:
                step_projection = project_step(
                    1'b0, EVENT_APX_REQUEST, 5'd9);
            {OPERATOR_BACKSUB, 5'd10}:
                step_projection = project_step(
                    1'b0, EVENT_APX_REQUEST, 5'd11);
            {OPERATOR_BACKSUB, 5'd12}:
                step_projection = project_step(
                    1'b0, EVENT_APX_REQUEST, 5'd13);
            {OPERATOR_BACKSUB, 5'd14}:
                step_projection = project_step(
                    1'b0, EVENT_APX_REQUEST, 5'd15);
            {OPERATOR_BACKSUB, 5'd16}:
                step_projection = project_step(
                    1'b0, EVENT_APX_REQUEST, 5'd17);
            {OPERATOR_BACKSUB, 5'd18}:
                step_projection = project_step(
                    1'b0, EVENT_APX_REQUEST, 5'd19);
            {OPERATOR_BACKSUB, 5'd19}:
                step_projection = project_step(
                    1'b0, EVENT_PRODUCT_F400, 5'd20);
            default: begin
                step_projection = 11'd0;
                step_entry_valid = 1'b0;
            end
        endcase
    end

    always @(*) begin
        case (wait_event)
            EVENT_ALWAYS:
                event_fire = 1'b1;
            EVENT_SERVICE_REQUEST:
                event_fire = service_request_fire;
            EVENT_APX_REQUEST:
                event_fire = apx_request_fire;
            EVENT_PRODUCT_B001:
                event_fire = completion_events[0];
            EVENT_PRODUCT_E000:
                event_fire = completion_events[1];
            EVENT_PRODUCT_E003:
                event_fire = completion_events[2];
            EVENT_PRODUCT_E004:
                event_fire = completion_events[3];
            EVENT_PRODUCT_F400:
                event_fire = completion_events[4];
            EVENT_PAIR_D202:
                event_fire = completion_events[5];
            EVENT_REDUCE_E002:
                event_fire = completion_events[6];
            EVENT_REDUCE_D200:
                event_fire = completion_events[7];
            EVENT_POST_ADD_E001:
                event_fire = completion_events[8];
            EVENT_POST_ADD_E005:
                event_fire = completion_events[9];
            EVENT_POST_ADD_E1XX:
                event_fire = completion_events[10];
            EVENT_RETIRE:
                event_fire = retire_complete;
            EVENT_SCALAR_REQUEST:
                event_fire = scalar_request_fire;
            default:
                event_fire = 1'b0;
        endcase
    end
endmodule
`default_nettype wire
