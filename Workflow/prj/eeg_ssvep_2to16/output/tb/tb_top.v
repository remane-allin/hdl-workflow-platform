`timescale 1ns/1ps
// Sole directed Verilog testbench authority.
// Mechanically consolidated from the reviewed P012 modules; module behavior is unchanged.

// ---- BEGIN banked_local_state_2r1w_tb.v ----
`timescale 1ns/1ps

module banked_local_state_2r1w_tb;
    reg clk;
    reg [2:0] read0_index;
    reg [2:0] read1_index;
    wire [127:0] even_read0_data;
    wire [127:0] even_read1_data;
    wire [127:0] odd_read0_data;
    wire [127:0] odd_read1_data;
    reg write_enable;
    reg write_dual_bank;
    reg write_bank;
    reg [2:0] write_index;
    reg [7:0] write_mask;
    reg [127:0] write_even_data;
    reg [127:0] write_odd_data;
    integer checks;
    integer failures;

    banked_local_state_2r1w dut (
        .clk(clk),
        .read0_index(read0_index),
        .even_read0_data(even_read0_data),
        .read1_index(read1_index),
        .even_read1_data(even_read1_data),
        .odd_read0_data(odd_read0_data),
        .odd_read1_data(odd_read1_data),
        .write_enable(write_enable),
        .write_dual_bank(write_dual_bank),
        .write_bank(write_bank),
        .write_index(write_index),
        .write_mask(write_mask),
        .write_even_data(write_even_data),
        .write_odd_data(write_odd_data)
    );

    always #5 clk = ~clk;

    task check128;
        input [127:0] actual;
        input [127:0] expected;
        input [8*48-1:0] label;
        begin
            checks = checks + 1;
            if (actual !== expected) begin
                failures = failures + 1;
                $display("CHECK_FAIL|%0s|actual=%032h|expected=%032h",
                         label, actual, expected);
            end
        end
    endtask

    initial begin
        clk = 1'b0;
        checks = 0;
        failures = 0;
        read0_index = 3'd0;
        read1_index = 3'd1;
        write_enable = 1'b0;
        write_dual_bank = 1'b0;
        write_bank = 1'b0;
        write_index = 3'd0;
        write_mask = 8'd0;
        write_even_data = 128'd0;
        write_odd_data = 128'd0;

        #1;
        check128(even_read0_data, 128'd0, "resetless INIT even row0");
        check128(odd_read0_data, 128'd0, "resetless INIT odd row0");

        write_enable = 1'b1;
        write_dual_bank = 1'b1;
        write_index = 3'd0;
        write_mask = 8'hFF;
        write_even_data = 128'h00112233445566778899AABBCCDDEEFF;
        write_odd_data = 128'hFFEEDDCCBBAA99887766554433221100;
        @(posedge clk);
        check128(even_read0_data, 128'd0, "read-old even at write edge");
        check128(odd_read0_data, 128'd0, "read-old odd at write edge");
        #1;
        check128(even_read0_data,
                 128'h00112233445566778899AABBCCDDEEFF,
                 "even full write");
        check128(odd_read0_data,
                 128'hFFEEDDCCBBAA99887766554433221100,
                 "odd full write");

        write_dual_bank = 1'b0;
        write_bank = 1'b0;
        write_index = 3'd1;
        write_mask = 8'hFF;
        write_even_data = 128'h0123456789ABCDEFFEDCBA9876543210;
        @(posedge clk);
        #1;
        check128(even_read0_data,
                 128'h00112233445566778899AABBCCDDEEFF,
                 "dual read port row0");
        check128(even_read1_data,
                 128'h0123456789ABCDEFFEDCBA9876543210,
                 "dual read port row1");

        write_index = 3'd0;
        write_mask = 8'b00100101;
        write_even_data = 128'hAAAABBBBCCCCDDDDEEEEFFFF11112222;
        @(posedge clk);
        #1;
        check128(even_read0_data,
                 128'h00112233CCCC66778899FFFFCCDD2222,
                 "FP16 lane masked write");

        write_even_data = {8{16'h5A3C}};
        write_mask = 8'b00010000;
        @(posedge clk);
        #1;
        check128(even_read0_data,
                 128'h00112233CCCC5A3C8899FFFFCCDD2222,
                 "narrow word write expands at RAM boundary");

        write_enable = 1'b0;
        read1_index = 3'd0;
        #1;
        check128(even_read1_data, even_read0_data,
                 "same-bank independent read ports");
        check128(odd_read0_data,
                 128'hFFEEDDCCBBAA99887766554433221100,
                 "even/odd banks independent");

        $display("TASK_SUMMARY|name=banked_local_state_2r1w|checks=%0d|failed=%0d",
                 checks, failures);
        if (failures == 0)
            $display("TASK_END|name=banked_local_state_2r1w|status=PASS");
        else
            $display("TASK_END|name=banked_local_state_2r1w|status=FAIL");
        $finish;
    end
endmodule
// ---- END banked_local_state_2r1w_tb.v ----

// ---- BEGIN unified_memory_fabric_tb.v ----
`timescale 1ns/1ps

module unified_memory_fabric_tb;
    reg clk;
    reg reset_n;
    reg [3:0] service_a_valid;
    reg [43:0] service_a_address;
    reg [3:0] service_b_valid;
    reg [43:0] service_b_address;
    wire [3:0] service_a_response_valid;
    wire [63:0] service_a_response_data;
    wire [3:0] service_b_response_valid;
    wire [63:0] service_b_response_data;
    reg window_a_valid;
    reg [12:0] window_a_address;
    wire window_a_response_valid;
    wire [15:0] window_a_response_data;
    reg [3:0] retire_a_valid;
    reg [51:0] retire_a_address;
    reg [63:0] retire_a_data;
    reg [3:0] retire_b_valid;
    reg [51:0] retire_b_address;
    reg [63:0] retire_b_data;
    wire [3:0] memory_a_valid;
    wire [3:0] memory_a_write;
    wire [51:0] memory_a_address;
    wire [63:0] memory_a_write_data;
    wire [3:0] memory_b_valid;
    wire [3:0] memory_b_write;
    wire [51:0] memory_b_address;
    wire [63:0] memory_b_write_data;
    reg [3:0] memory_a_response_valid;
    reg [63:0] memory_a_response_data;
    reg [3:0] memory_b_response_valid;
    reg [63:0] memory_b_response_data;
    integer checks;
    integer failures;

    unified_memory_fabric dut (
        .clk(clk), .reset_n(reset_n),
        .service_a_valid(service_a_valid),
        .service_a_address(service_a_address),
        .service_b_valid(service_b_valid),
        .service_b_address(service_b_address),
        .service_a_response_valid(service_a_response_valid),
        .service_a_response_data(service_a_response_data),
        .service_b_response_valid(service_b_response_valid),
        .service_b_response_data(service_b_response_data),
        .window_a_valid(window_a_valid),
        .window_a_address(window_a_address),
        .window_a_response_valid(window_a_response_valid),
        .window_a_response_data(window_a_response_data),
        .retire_a_valid(retire_a_valid),
        .retire_a_address(retire_a_address),
        .retire_a_data(retire_a_data),
        .retire_b_valid(retire_b_valid),
        .retire_b_address(retire_b_address),
        .retire_b_data(retire_b_data),
        .memory_a_valid(memory_a_valid),
        .memory_a_write(memory_a_write),
        .memory_a_address(memory_a_address),
        .memory_a_write_data(memory_a_write_data),
        .memory_b_valid(memory_b_valid),
        .memory_b_write(memory_b_write),
        .memory_b_address(memory_b_address),
        .memory_b_write_data(memory_b_write_data),
        .memory_a_response_valid(memory_a_response_valid),
        .memory_a_response_data(memory_a_response_data),
        .memory_b_response_valid(memory_b_response_valid),
        .memory_b_response_data(memory_b_response_data)
    );

    always #5 clk = ~clk;

    task check1;
        input actual;
        input expected;
        input [8*48-1:0] label;
        begin
            checks = checks + 1;
            if (actual !== expected) begin
                failures = failures + 1;
                $display("CHECK_FAIL|%0s|actual=%b|expected=%b",
                         label, actual, expected);
            end
        end
    endtask

    task check13;
        input [12:0] actual;
        input [12:0] expected;
        input [8*48-1:0] label;
        begin
            checks = checks + 1;
            if (actual !== expected) begin
                failures = failures + 1;
                $display("CHECK_FAIL|%0s|actual=%h|expected=%h",
                         label, actual, expected);
            end
        end
    endtask

    initial begin
        clk = 1'b0;
        reset_n = 1'b0;
        checks = 0;
        failures = 0;
        service_a_valid = 4'd0;
        service_a_address = 44'd0;
        service_b_valid = 4'd0;
        service_b_address = 44'd0;
        window_a_valid = 1'b0;
        window_a_address = 13'd0;
        retire_a_valid = 4'd0;
        retire_a_address = 52'd0;
        retire_a_data = 64'd0;
        retire_b_valid = 4'd0;
        retire_b_address = 52'd0;
        retire_b_data = 64'd0;
        memory_a_response_valid = 4'd0;
        memory_a_response_data = 64'd0;
        memory_b_response_valid = 4'd0;
        memory_b_response_data = 64'd0;
        repeat (2) @(posedge clk);
        reset_n = 1'b1;

        service_a_valid = 4'b0010;
        service_a_address[21:11] = 11'h155;
        #1;
        check1(memory_a_valid[1], 1'b1, "service owns bank1");
        check1(memory_a_write[1], 1'b0, "service read command");
        check13(memory_a_address[25:13], {11'h155, 2'd1},
                "service address decode");
        @(posedge clk);
        service_a_valid = 4'd0;
        memory_a_response_valid = 4'b0010;
        memory_a_response_data[31:16] = 16'h1234;
        #1;
        check1(service_a_response_valid[1], 1'b1,
               "service response ownership frozen");
        check1(window_a_response_valid, 1'b0,
               "service response not delivered to window");
        @(posedge clk);
        memory_a_response_valid = 4'd0;

        window_a_valid = 1'b1;
        window_a_address = 13'h10A;
        #1;
        check1(memory_a_valid[2], 1'b1, "window owns selected bank");
        check13(memory_a_address[38:26], 13'h10A,
                "window address preserved");
        @(posedge clk);
        window_a_valid = 1'b0;
        memory_a_response_valid = 4'b0100;
        memory_a_response_data[47:32] = 16'hBEEF;
        #1;
        check1(window_a_response_valid, 1'b1,
               "window response ownership frozen");
        checks = checks + 1;
        if (window_a_response_data !== 16'hBEEF) begin
            failures = failures + 1;
            $display("CHECK_FAIL|window response lane|actual=%h|expected=BEEF",
                     window_a_response_data);
        end
        check1(service_a_response_valid[2], 1'b0,
               "window response masked from service");
        @(posedge clk);
        memory_a_response_valid = 4'd0;

        service_a_valid = 4'b0001;
        window_a_valid = 1'b1;
        window_a_address = 13'h080;
        retire_a_valid = 4'b0001;
        retire_a_address[12:0] = 13'h040;
        retire_a_data[15:0] = 16'hCAFE;
        #1;
        check1(memory_a_valid[0], 1'b1, "retire command valid");
        check1(memory_a_write[0], 1'b1, "retire priority over reads");
        check13(memory_a_address[12:0], 13'h040,
                "retire address priority");
        checks = checks + 1;
        if (memory_a_write_data[15:0] !== 16'hCAFE) begin
            failures = failures + 1;
            $display("CHECK_FAIL|retire data|actual=%h|expected=CAFE",
                     memory_a_write_data[15:0]);
        end

        $display("TASK_SUMMARY|name=unified_memory_fabric|checks=%0d|failed=%0d",
                 checks, failures);
        if (failures == 0)
            $display("TASK_END|name=unified_memory_fabric|status=PASS");
        else
            $display("TASK_END|name=unified_memory_fabric|status=FAIL");
        $finish;
    end
endmodule
// ---- END unified_memory_fabric_tb.v ----

// ---- BEGIN shared_kernel_step_sequencer_tb.v ----
`timescale 1ns/1ps

module shared_kernel_step_sequencer_tb;
    reg [1:0] operator_select;
    reg [4:0] step_index;
    reg service_request_fire;
    reg apx_request_fire;
    reg [10:0] completion_events;
    reg retire_complete;
    reg scalar_request_fire;
    wire retire_phase;
    wire transition_valid;
    wire advance;
    wire [4:0] next_step_index;
    integer checks;
    integer failures;

    shared_kernel_step_sequencer dut (
        .operator_select(operator_select),
        .step_index(step_index),
        .service_request_fire(service_request_fire),
        .apx_request_fire(apx_request_fire),
        .completion_events(completion_events),
        .retire_complete(retire_complete),
        .scalar_request_fire(scalar_request_fire),
        .retire_phase(retire_phase),
        .transition_valid(transition_valid),
        .advance(advance),
        .next_step_index(next_step_index)
    );

    task clear_events;
        begin
            service_request_fire = 1'b0;
            apx_request_fire = 1'b0;
            completion_events = 11'd0;
            retire_complete = 1'b0;
            scalar_request_fire = 1'b0;
        end
    endtask

    task check_step;
        input expected_valid;
        input expected_retire;
        input expected_advance;
        input [4:0] expected_next;
        input [8*48-1:0] label;
        begin
            #1;
            checks = checks + 4;
            if (transition_valid !== expected_valid) begin
                failures = failures + 1;
                $display("CHECK_FAIL|%0s transition", label);
            end
            if (retire_phase !== expected_retire) begin
                failures = failures + 1;
                $display("CHECK_FAIL|%0s retire", label);
            end
            if (advance !== expected_advance) begin
                failures = failures + 1;
                $display("CHECK_FAIL|%0s advance", label);
            end
            if (next_step_index !== expected_next) begin
                failures = failures + 1;
                $display("CHECK_FAIL|%0s next actual=%0d expected=%0d",
                         label, next_step_index, expected_next);
            end
        end
    endtask

    initial begin
        checks = 0;
        failures = 0;
        operator_select = 2'd0;
        step_index = 5'd4;
        clear_events;
        check_step(1'b1, 1'b0, 1'b0, 5'd5,
                   "pairwise service wait");
        service_request_fire = 1'b1;
        check_step(1'b1, 1'b0, 1'b1, 5'd5,
                   "pairwise service event");

        clear_events;
        step_index = 5'd11;
        check_step(1'b1, 1'b0, 1'b0, 5'd27,
                   "unrelated completion absent");
        completion_events[1] = 1'b1;
        check_step(1'b1, 1'b0, 1'b1, 5'd27,
                   "product E000 event accepted");

        clear_events;
        step_index = 5'd21;
        completion_events[10] = 1'b1;
        check_step(1'b1, 1'b0, 1'b1, 5'd22,
                   "post-add E1xx event accepted");

        clear_events;
        step_index = 5'd13;
        check_step(1'b0, 1'b1, 1'b0, 5'd13,
                   "retire owner has no implicit transition");

        operator_select = 2'd2;
        step_index = 5'd20;
        clear_events;
        check_step(1'b1, 1'b1, 1'b0, 5'd21,
                   "backsub retire wait");
        retire_complete = 1'b1;
        check_step(1'b1, 1'b1, 1'b1, 5'd21,
                   "backsub retire completion");

        operator_select = 2'd3;
        step_index = 5'd19;
        clear_events;
        check_step(1'b0, 1'b0, 1'b0, 5'd19,
                   "autonomous recurrence absent from common table");

        operator_select = 2'd1;
        step_index = 5'd31;
        clear_events;
        check_step(1'b0, 1'b0, 1'b0, 5'd31,
                   "unmapped step statically inert");

        $display("TASK_SUMMARY|name=shared_kernel_step_sequencer|checks=%0d|failed=%0d",
                 checks, failures);
        if (failures == 0)
            $display("TASK_END|name=shared_kernel_step_sequencer|status=PASS");
        else
            $display("TASK_END|name=shared_kernel_step_sequencer|status=FAIL");
        $finish;
    end
endmodule
// ---- END shared_kernel_step_sequencer_tb.v ----

// ---- BEGIN apx_cluster_direct_tb.v ----
//==============================================================================
// Module      : apx_cluster_direct_tb
// File        : apx_cluster_direct_tb.v
// Project     : eeg_ssvep_2to16
// Description : Vector multiply/add/reduce and pair-port arbitration checks.
// Scope:
//   - Checks direct vector addition for one through sixteen outputs.
//   - Checks vector multiply returns products without entering the add tree.
//   - Checks direct reduction for one through sixteen input terms and verifies
//     that a multiplier response has priority on the shared first adder level.
// Spec Trace:
//   - REQ-RRB-006, REQ-RRB-011, REQ-RRB-012
//   - MOD-APX, IF-APX, AS-APX-LATENCY, CV-APX-MODE
// Notes:
//   - Expected reductions use an independent adjacent-pairwise scoreboard.
//==============================================================================
`timescale 1ns/1ps

module apx_cluster_direct_tb;
    localparam [1:0] OP_MULTIPLY_REDUCE = 2'd0;
    localparam [1:0] OP_ADD_VECTOR = 2'd1;
    localparam [1:0] OP_REDUCE_VECTOR = 2'd2;
    localparam [1:0] OP_MULTIPLY_VECTOR = 2'd3;

    reg clk;
    reg reset_n;
    reg request_valid;
    wire request_ready;
    reg [1:0] request_operation;
    reg [4:0] request_lanes;
    reg [15:0] request_tag;
    reg [255:0] operand_a_bus;
    reg [255:0] operand_b_bus;
    reg parallel_add_valid;
    wire parallel_add_ready;
    reg [4:0] parallel_add_lanes;
    reg [15:0] parallel_add_tag;
    reg parallel_prefetch_valid;
    reg parallel_operand_a_pair;
    reg [191:0] parallel_prefetch_operand_b_bus;
    wire product_valid;
    wire [15:0] product_tag;
    wire [255:0] product_bus;
    wire pair_valid;
    wire [15:0] pair_tag;
    wire [255:0] pair_bus;
    wire reduce_valid;
    wire [15:0] reduce_tag;
    wire [15:0] reduce_result;

    reg [255:0] expected_pair_bus;
    reg [127:0] pair_level;
    reg [63:0] quad_level;
    reg [31:0] oct_level;
    reg [15:0] expected_reduce;
    integer lane_index;
    integer lane_count;
    integer response_index;
    integer check_count;
    integer failure_count;
    integer random_seed;
    reg test_complete;
    reg test_passed;

    function [15:0] reference_add;
        input [15:0] operand_x;
        input [15:0] operand_y;
        reg operand_x_is_large;
        reg sign_result;
        reg [4:0] exponent_base;
        reg [4:0] exponent_delta;
        reg [4:0] exponent_result;
        reg [10:0] mantissa_large;
        reg [10:0] mantissa_small;
        reg [10:0] mantissa_aligned;
        reg [11:0] mantissa;
        reg [3:0] alignment_shift;
        reg [3:0] normalization_shift;
        reg normalize_up;
        begin
            operand_x_is_large =
                (operand_x[14:10] > operand_y[14:10]) ||
                ((operand_x[14:10] == operand_y[14:10]) &&
                (operand_x[9:0] > operand_y[9:0]));
            if (operand_x_is_large) begin
                exponent_base = operand_x[14:10];
                exponent_delta = operand_x[14:10] - operand_y[14:10];
                mantissa_large = {1'b1, operand_x[9:0]};
                mantissa_small = {1'b1, operand_y[9:0]};
                sign_result = operand_x[15];
            end
            else begin
                exponent_base = operand_y[14:10];
                exponent_delta = operand_y[14:10] - operand_x[14:10];
                mantissa_large = {1'b1, operand_y[9:0]};
                mantissa_small = {1'b1, operand_x[9:0]};
                sign_result = (operand_x[15] ^ operand_y[15]) ?
                    operand_y[15] : operand_x[15];
            end
            alignment_shift = (exponent_delta > 5'd10) ?
                4'd11 : exponent_delta[3:0];
            mantissa_aligned = mantissa_small >> alignment_shift;
            if (operand_x[15] ^ operand_y[15]) begin
                mantissa = {1'b0, mantissa_large} -
                    {1'b0, mantissa_aligned};
            end
            else begin
                mantissa = {1'b0, mantissa_large} +
                    {1'b0, mantissa_aligned};
            end
            normalize_up = 1'b0;
            normalization_shift = 4'd10;
            casez (mantissa)
                12'b1???????????: begin normalize_up = 1'b1; normalization_shift = 4'd1; end
                12'b01??????????: begin normalization_shift = 4'd0; end
                12'b001?????????: begin normalization_shift = 4'd1; end
                12'b0001????????: begin normalization_shift = 4'd2; end
                12'b00001???????: begin normalization_shift = 4'd3; end
                12'b000001??????: begin normalization_shift = 4'd4; end
                12'b0000001?????: begin normalization_shift = 4'd5; end
                12'b00000001????: begin normalization_shift = 4'd6; end
                12'b000000001???: begin normalization_shift = 4'd7; end
                12'b0000000001??: begin normalization_shift = 4'd8; end
                12'b00000000001?: begin normalization_shift = 4'd9; end
                default: begin normalization_shift = 4'd10; end
            endcase
            if (normalize_up) begin
                exponent_result = (exponent_base == 5'd31) ?
                    5'd31 : exponent_base + 5'd1;
                reference_add = {
                    sign_result,
                    exponent_result,
                    mantissa[10:1]
                };
            end
            else begin
                exponent_result = (exponent_base <= normalization_shift) ?
                    5'd0 : exponent_base - normalization_shift;
                reference_add = {
                    sign_result,
                    exponent_result,
                    mantissa[9:0] << normalization_shift
                };
            end
        end
    endfunction

    always #5 clk = ~clk;

    apx_cluster dut (
        .clk(clk),
        .reset_n(reset_n),
        .request_valid(request_valid),
        .request_ready(request_ready),
        .busy(),
        .request_operation(request_operation),
        .request_add_vector(request_operation == OP_ADD_VECTOR),
        .request_lanes(request_lanes),
        .request_tag(request_tag),
        .operand_a_low_beat(operand_a_bus[127:0]),
        .operand_a_high_beat(operand_a_bus[255:128]),
        .operand_b_low_beat(operand_b_bus[127:0]),
        .operand_b_high_beat(operand_b_bus[255:128]),
        .narrow_operand_a_low_beat(128'd0),
        .narrow_operand_a_high_beat(64'd0),
        .narrow_operand_b_low_beat(128'd0),
        .narrow_operand_b_high_beat(64'd0),
        .request_operand_a_select(2'd0),
        .request_operand_b_select(2'd0),
        .request_operand_a_negate(1'b0),
        .request_operand_b_negate(1'b0),
        .request_operand_b_scalar(1'b0),
        .request_operand_b_scalar_value(16'd0),
        .request_window_operand(1'b0),
        .request_window_shift(1'b0),
        .request_window_sample(16'd0),
        .window_resident_clear_valid(1'b0),
        .window_resident_seed_valid(1'b0),
        .window_resident_seed_lanes(5'd0),
        .window_resident_seed_data(16'd0),
        .parallel_add_valid(parallel_add_valid),
        .parallel_add_ready(parallel_add_ready),
        .parallel_add_lanes(parallel_add_lanes),
        .parallel_add_tag(parallel_add_tag),
        .parallel_prefetch_valid(parallel_prefetch_valid),
        .parallel_operand_a_pair(parallel_operand_a_pair),
        .parallel_prefetch_b_low_beat(
            parallel_prefetch_operand_b_bus[127:0]),
        .parallel_prefetch_b_high_beat(
            parallel_prefetch_operand_b_bus[191:128]),
        .post_add_valid(1'b0),
        .post_add_ready(),
        .post_add_operand_x(16'd0),
        .post_add_operand_y(16'd0),
        .post_add_tag(16'd0),
        .post_add_result_valid(),
        .post_add_result_tag(),
        .post_add_result(),
        .post_add_pre_valid(),
        .post_add_pre_tag(),
        .product_valid(product_valid),
        .product_pre_valid(),
        .product_tag(product_tag),
        .product_pre_tag(),
        .product_slot_low_beat(product_bus[127:0]),
        .product_slot_high_beat(product_bus[255:128]),
        .pair_valid(pair_valid),
        .pair_pre_valid(),
        .pair_tag(pair_tag),
        .pair_pre_tag(),
        .pair_slot_low_beat(pair_bus[127:0]),
        .pair_slot_high_beat(pair_bus[255:128]),
        .reduce_valid(reduce_valid),
        .reduce_pre_valid(),
        .reduce_tag(reduce_tag),
        .reduce_pre_tag(),
        .reduce_result(reduce_result)
    );

    task check_condition;
        input condition;
        input [8*96-1:0] message;
        begin
            check_count = check_count + 1;
            if (!condition) begin
                $display("FAIL check=%0d time=%0t %0s", check_count, $time,
                    message);
                failure_count = failure_count + 1;
            end
        end
    endtask

    initial begin
        clk = 1'b0;
        reset_n = 1'b0;
        request_valid = 1'b0;
        request_operation = OP_MULTIPLY_REDUCE;
        request_lanes = 5'd0;
        request_tag = 16'd0;
        operand_a_bus = 256'd0;
        operand_b_bus = 256'd0;
        parallel_add_valid = 1'b0;
        parallel_add_lanes = 5'd12;
        parallel_add_tag = 16'd0;
        parallel_prefetch_valid = 1'b0;
        parallel_operand_a_pair = 1'b0;
        parallel_prefetch_operand_b_bus = 192'd0;
        check_count = 0;
        failure_count = 0;
        test_complete = 1'b0;
        test_passed = 1'b0;
        $display("HDLFLOW|TASK_BEGIN|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P4_APX_CURRENT_SOURCE|requirement_id=REQ-RRB-006");
        random_seed = 32'h48a6c217;

        repeat (4) @(negedge clk);
        reset_n = 1'b1;

        // The first legal request after reset must see deterministic control
        // pipeline state and must be accepted without a flush cycle.
        request_operation = OP_ADD_VECTOR;
        request_lanes = 5'd1;
        request_tag = 16'h50f0;
        operand_a_bus[15:0] = 16'h3c00;
        operand_b_bus[15:0] = 16'h3c00;
        request_valid = 1'b1;
        #1;
        check_condition(request_ready === 1'b1,
            "first request after reset must be deterministically ready");
        @(negedge clk);
        request_valid = 1'b0;
        while (!(pair_valid && (pair_tag == 16'h50f0))) begin
            @(negedge clk);
        end
        check_condition(pair_bus[15:0] == 16'h4000,
            "first request after reset result mismatch");

        // Direct vector add reuses all reduction-tree adders without a
        // multiply pass. Every legal lane count is checked independently.
        for (lane_count = 1; lane_count <= 16;
             lane_count = lane_count + 1) begin
            @(negedge clk);
            request_operation = OP_ADD_VECTOR;
            request_lanes = lane_count;
            request_tag = 16'h5100 + lane_count;
            expected_pair_bus = 256'd0;
            for (lane_index = 0; lane_index < 16;
                 lane_index = lane_index + 1) begin
                operand_a_bus[lane_index*16 +: 16] = $random(random_seed);
                operand_b_bus[lane_index*16 +: 16] = $random(random_seed);
                if (lane_index < lane_count) begin
                    expected_pair_bus[lane_index*16 +: 16] = reference_add(
                        operand_a_bus[lane_index*16 +: 16],
                        operand_b_bus[lane_index*16 +: 16]
                    );
                end
            end
            request_valid = 1'b1;
            #1;
            check_condition(request_ready,
                "legal direct-add request must be ready");
            @(negedge clk);
            request_valid = 1'b0;
            while (!(pair_valid && (pair_tag == 16'h5100 + lane_count))) begin
                @(negedge clk);
            end
            for (lane_index = 0; lane_index < lane_count;
                 lane_index = lane_index + 1) begin
                check_condition(
                    pair_bus[lane_index*16 +: 16] ==
                        expected_pair_bus[lane_index*16 +: 16],
                    "direct-add result vector mismatch");
            end
        end

        // Direct reduction bypasses multiplication and preserves the frozen
        // adjacent-pairwise order for every input count.
        for (lane_count = 1; lane_count <= 16;
             lane_count = lane_count + 1) begin
            @(negedge clk);
            request_operation = OP_REDUCE_VECTOR;
            request_lanes = lane_count;
            request_tag = 16'h5200 + lane_count;
            pair_level = 128'd0;
            quad_level = 64'd0;
            oct_level = 32'd0;
            for (lane_index = 0; lane_index < 16;
                 lane_index = lane_index + 1) begin
                operand_a_bus[lane_index*16 +: 16] = $random(random_seed);
            end
            for (lane_index = 0; lane_index < 8;
                 lane_index = lane_index + 1) begin
                if ((lane_index*2+1) < lane_count) begin
                    pair_level[lane_index*16 +: 16] = reference_add(
                        operand_a_bus[(lane_index*2)*16 +: 16],
                        operand_a_bus[(lane_index*2+1)*16 +: 16]
                    );
                end
                else begin
                    pair_level[lane_index*16 +: 16] =
                        operand_a_bus[(lane_index*2)*16 +: 16];
                end
            end
            for (lane_index = 0; lane_index < 4;
                 lane_index = lane_index + 1) begin
                if ((lane_index*4+2) < lane_count) begin
                    quad_level[lane_index*16 +: 16] = reference_add(
                        pair_level[(lane_index*2)*16 +: 16],
                        pair_level[(lane_index*2+1)*16 +: 16]
                    );
                end
                else begin
                    quad_level[lane_index*16 +: 16] =
                        pair_level[(lane_index*2)*16 +: 16];
                end
            end
            for (lane_index = 0; lane_index < 2;
                 lane_index = lane_index + 1) begin
                if ((lane_index*8+4) < lane_count) begin
                    oct_level[lane_index*16 +: 16] = reference_add(
                        quad_level[(lane_index*2)*16 +: 16],
                        quad_level[(lane_index*2+1)*16 +: 16]
                    );
                end
                else begin
                    oct_level[lane_index*16 +: 16] =
                        quad_level[(lane_index*2)*16 +: 16];
                end
            end
            expected_reduce = (lane_count > 8) ?
                reference_add(oct_level[15:0], oct_level[31:16]) :
                oct_level[15:0];
            request_valid = 1'b1;
            #1;
            check_condition(request_ready,
                "legal direct-reduce request must be ready");
            @(negedge clk);
            request_valid = 1'b0;
            while (!(reduce_valid && (reduce_tag == 16'h5200 + lane_count))) begin
                @(negedge clk);
            end
            check_condition(reduce_result == expected_reduce,
                "direct-reduce result mismatch");
        end

        // A multiplier result and a new direct operation need the same first
        // adder level.  The APX-local elastic ingress accepts one command while
        // the tree is occupied and issues it when the pair port becomes free.
        // This keeps the wide operands behind the physical APX boundary instead
        // of propagating the tree collision through the execution engine.
        @(negedge clk);
        request_operation = OP_MULTIPLY_REDUCE;
        request_lanes = 5'd1;
        request_tag = 16'h5300;
        operand_a_bus[15:0] = 16'h3c00;
        operand_b_bus[15:0] = 16'h3c00;
        request_valid = 1'b1;
        @(negedge clk);
        request_valid = 1'b0;
        while (!product_valid) begin
            @(negedge clk);
        end
        request_operation = OP_ADD_VECTOR;
        request_lanes = 5'd1;
        request_tag = 16'h5301;
        operand_a_bus[15:0] = 16'h3c00;
        operand_b_bus[15:0] = 16'h3c00;
        request_valid = 1'b1;
        #1;
        check_condition(request_ready,
            "empty APX ingress must accept a collision-bound request");
        @(negedge clk);
        request_valid = 1'b0;
        while (!(pair_valid && (pair_tag == 16'h5301))) begin
            @(negedge clk);
        end
        check_condition(pair_bus[15:0] == reference_add(16'h3c00, 16'h3c00),
            "stalled direct request must execute exactly once");
        while (!(reduce_valid && (reduce_tag == 16'h5300))) begin
            @(negedge clk);
        end

        // Vector multiply must expose all products while leaving the shared
        // add tree available for an immediately following vector add.
        @(negedge clk);
        request_operation = OP_MULTIPLY_VECTOR;
        request_lanes = 5'd16;
        request_tag = 16'h5400;
        operand_a_bus = {16{16'h3c00}};
        operand_b_bus = {16{16'h3c00}};
        request_valid = 1'b1;
        #1;
        check_condition(request_ready,
            "vector multiply request must be accepted");
        @(negedge clk);
        request_valid = 1'b0;
        while (!(product_valid && (product_tag == 16'h5400))) begin
            @(negedge clk);
        end
        for (lane_index = 0; lane_index < 16;
             lane_index = lane_index + 1) begin
            check_condition(product_bus[lane_index*16 +: 16] == 16'h3c00,
                "vector multiply product mismatch");
        end

        request_operation = OP_ADD_VECTOR;
        request_lanes = 5'd16;
        request_tag = 16'h5401;
        operand_a_bus = product_bus;
        operand_b_bus = {16{16'h3c00}};
        request_valid = 1'b1;
        #1;
        check_condition(request_ready,
            "vector multiply response must not reserve the add tree");
        @(negedge clk);
        request_valid = 1'b0;
        while (!(pair_valid && (pair_tag == 16'h5401))) begin
            if (pair_valid && (pair_tag == 16'h5400)) begin
                check_condition(1'b0,
                    "vector multiply must not emit a pair response");
            end
            @(negedge clk);
        end
        for (lane_index = 0; lane_index < 16;
             lane_index = lane_index + 1) begin
            check_condition(pair_bus[lane_index*16 +: 16] == 16'h4000,
                "vector multiply follow-on add mismatch");
        end

        // Non-unit operands catch exponent/mantissa stage skew that an
        // all-1.0 vector cannot expose.
        @(negedge clk);
        request_operation = OP_MULTIPLY_VECTOR;
        request_lanes = 5'd16;
        request_tag = 16'h5402;
        operand_a_bus = {16{16'h3555}};
        operand_b_bus = {16{16'h3a00}};
        request_valid = 1'b1;
        #1;
        check_condition(request_ready,
            "non-unit vector multiply request must be accepted");
        @(negedge clk);
        request_valid = 1'b0;
        while (!(product_valid && (product_tag == 16'h5402))) begin
            @(negedge clk);
        end
        for (lane_index = 0; lane_index < 16;
             lane_index = lane_index + 1) begin
            check_condition(product_bus[lane_index*16 +: 16] == 16'h33fd,
                "non-unit vector multiply product mismatch");
        end

        // Both FP16 exponents sum above 31.  This locks the six-bit exponent
        // addition and prevents a silent wrap in the multiplier front end.
        @(negedge clk);
        request_operation = OP_MULTIPLY_VECTOR;
        request_lanes = 5'd16;
        request_tag = 16'h5403;
        operand_a_bus = {16{16'h4000}};
        operand_b_bus = {16{16'h4000}};
        request_valid = 1'b1;
        #1;
        check_condition(request_ready,
            "exponent-carry vector multiply request must be accepted");
        @(negedge clk);
        request_valid = 1'b0;
        while (!(product_valid && (product_tag == 16'h5403))) begin
            @(negedge clk);
        end
        for (lane_index = 0; lane_index < 16;
             lane_index = lane_index + 1) begin
            check_condition(product_bus[lane_index*16 +: 16] == 16'h4400,
                "exponent-carry vector multiply product mismatch");
        end

        // Four changing requests are accepted on consecutive cycles.  The
        // response stream must preserve both tag order and operand pairing.
        @(negedge clk);
        request_tag = 16'h5410;
        operand_a_bus = {16{16'h3800}};
        operand_b_bus = {16{16'h3800}};
        request_valid = 1'b1;
        #1;
        check_condition(request_ready,
            "back-to-back vector multiply request 0 must be accepted");
        @(negedge clk);
        request_tag = 16'h5411;
        operand_a_bus = {16{16'h4000}};
        operand_b_bus = {16{16'h3800}};
        #1;
        check_condition(request_ready,
            "back-to-back vector multiply request 1 must be accepted");
        @(negedge clk);
        request_tag = 16'h5412;
        operand_a_bus = {16{16'h4200}};
        operand_b_bus = {16{16'h3800}};
        #1;
        check_condition(request_ready,
            "back-to-back vector multiply request 2 must be accepted");
        @(negedge clk);
        request_tag = 16'h5413;
        operand_a_bus = {16{16'hbc00}};
        operand_b_bus = {16{16'h4000}};
        #1;
        check_condition(request_ready,
            "back-to-back vector multiply request 3 must be accepted");
        @(negedge clk);
        request_valid = 1'b0;
        response_index = 0;
        while (response_index < 4) begin
            if (product_valid) begin
                case (response_index)
                    0: begin
                        check_condition(product_tag == 16'h5410,
                            "back-to-back product tag 0 mismatch");
                        check_condition(product_bus[15:0] == 16'h3400,
                            "back-to-back product data 0 mismatch");
                    end
                    1: begin
                        check_condition(product_tag == 16'h5411,
                            "back-to-back product tag 1 mismatch");
                        check_condition(product_bus[15:0] == 16'h3c00,
                            "back-to-back product data 1 mismatch");
                    end
                    2: begin
                        check_condition(product_tag == 16'h5412,
                            "back-to-back product tag 2 mismatch");
                        check_condition(product_bus[15:0] == 16'h3e00,
                            "back-to-back product data 2 mismatch");
                    end
                    default: begin
                        check_condition(product_tag == 16'h5413,
                            "back-to-back product tag 3 mismatch");
                        check_condition(product_bus[15:0] == 16'hc000,
                            "back-to-back product data 3 mismatch");
                    end
                endcase
                response_index = response_index + 1;
            end
            @(negedge clk);
        end

        // The vector multipliers and direct add tree are independent physical
        // resources.  Seed the registered product source and prefetch the
        // recurrence B packet, then accept a new multiply command alongside
        // the twelve-lane recurrence add supported by the shared overlay.
        @(negedge clk);
        request_operation = OP_MULTIPLY_VECTOR;
        request_lanes = 5'd12;
        request_tag = 16'h54f0;
        operand_a_bus = {16{16'h3c00}};
        operand_b_bus = {16{16'h3c00}};
        request_valid = 1'b1;
        @(negedge clk);
        request_valid = 1'b0;
        while (!(product_valid && (product_tag == 16'h54f0))) begin
            @(negedge clk);
        end
        parallel_prefetch_operand_b_bus = {12{16'h3c00}};
        parallel_prefetch_valid = 1'b1;
        @(negedge clk);
        parallel_prefetch_valid = 1'b0;

        @(negedge clk);
        request_operation = OP_MULTIPLY_VECTOR;
        request_lanes = 5'd12;
        request_tag = 16'h5500;
        parallel_add_tag = 16'h5501;
        operand_a_bus = {16{16'h3c00}};
        operand_b_bus = {16{16'h3c00}};
        request_valid = 1'b1;
        parallel_add_valid = 1'b1;
        #1;
        check_condition(request_ready,
            "parallel vector multiply must be ready");
        check_condition(parallel_add_ready,
            "parallel vector add must be ready beside multiply");
        @(negedge clk);
        request_valid = 1'b0;
        parallel_add_valid = 1'b0;
        while (!(pair_valid && (pair_tag == 16'h5501))) begin
            @(negedge clk);
        end
        for (lane_index = 0; lane_index < 12;
             lane_index = lane_index + 1) begin
            check_condition(pair_bus[lane_index*16 +: 16] == 16'h4000,
                "parallel vector-add result mismatch");
        end
        while (!(product_valid && (product_tag == 16'h5500))) begin
            @(negedge clk);
        end
        for (lane_index = 0; lane_index < 12;
             lane_index = lane_index + 1) begin
            check_condition(product_bus[lane_index*16 +: 16] == 16'h3c00,
                "parallel vector-multiply result mismatch");
        end

        if (failure_count != 0) begin
            $display("FAIL apx_cluster_direct_tb checks=%0d errors=%0d",
                check_count, failure_count);
            $display("HDLFLOW|TASK_END|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P4_APX_CURRENT_SOURCE|result=FAIL");
            test_complete = 1'b1;
            test_passed = 1'b0;
            $finish;
        end
        $display("PASS apx_cluster_direct_tb checks=%0d errors=0", check_count);
        $display("HDLFLOW|TASK_END|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P4_APX_CURRENT_SOURCE|result=PASS");
        test_complete = 1'b1;
        test_passed = 1'b1;
        $finish;
    end

    initial begin
        repeat (3000) @(negedge clk);
        $display("FAIL apx_cluster_direct_tb timeout");
        $fatal(1);
        $finish;
    end
endmodule
// ---- END apx_cluster_direct_tb.v ----

// ---- BEGIN shared_operand_tile_service_tb.v ----
// -----------------------------------------------------------------------------
// Module: shared_operand_tile_service_tb
// Purpose: Directed verification of the sole direct-bank operand gather path.
// Requirements: REQ-RRB-005, REQ-RRB-007, REQ-RRB-010, REQ-RRB-011,
//               REQ-RRB-019, REQ-RRB-022
// -----------------------------------------------------------------------------

`timescale 1ns/1ps

module shared_operand_tile_service_tb;
    reg clk;
    reg reset_n;
    reg request_valid;
    wire request_ready;
    reg [1:0] request_space;
    reg [12:0] request_base;
    reg [9:0] request_lane_stride;
    reg [4:0] request_lanes;
    reg request_negate;
    reg request_fast_feature;
    reg [11:0] request_repeat_count;
    reg [12:0] request_repeat_stride;
    reg [8:0] constant_base_row;

    wire [3:0] feature_read_a_valid;
    wire [43:0] feature_read_a_address;
    wire [3:0] feature_read_b_valid;
    wire [43:0] feature_read_b_address;
    reg [3:0] feature_read_a_response_valid;
    reg [63:0] feature_read_a_response_data;
    reg [3:0] feature_read_b_response_valid;
    reg [63:0] feature_read_b_response_data;
    wire parameter_read_valid;
    wire [8:0] parameter_read_address;
    reg parameter_read_response_valid;
    reg [63:0] parameter_read_response_data;
    wire program_read_valid;
    wire [8:0] program_read_address;
    reg program_read_response_valid;
    reg [63:0] program_read_response_data;

    wire response_valid;
    reg response_ready;
    wire response_last;
    wire response_half;
    wire [127:0] response_data;
    reg [127:0] response_lower_data;
    wire [255:0] response_tile_data;

    integer pass_count;
    integer fail_count;
    integer feature_issue_cycles;
    integer dual_port_issue_cycles;
    integer parameter_issue_count;
    integer program_issue_count;
    integer bank_index;
    integer scalar_index;
    integer scalar_previous_time;
    integer fast_previous_time;
    reg test_complete;
    reg test_passed;

    assign response_tile_data = response_half ?
        {response_data, response_lower_data} :
        {128'd0, response_data};

    function [15:0] feature_value;
        input [12:0] logical_address;
        begin
            feature_value = 16'h1000 + logical_address;
        end
    endfunction

    function [15:0] parameter_value;
        input [12:0] logical_address;
        begin
            parameter_value = 16'h3000 + logical_address;
        end
    endfunction

    function [15:0] program_value;
        input [12:0] logical_address;
        begin
            program_value = 16'h5000 + logical_address;
        end
    endfunction

    function [63:0] packed_parameter_row;
        input [8:0] row_address;
        reg [12:0] word_base;
        begin
            word_base = {row_address, 2'b00};
            packed_parameter_row = {
                parameter_value(word_base + 13'd3),
                parameter_value(word_base + 13'd2),
                parameter_value(word_base + 13'd1),
                parameter_value(word_base)
            };
        end
    endfunction

    function [63:0] packed_program_row;
        input [8:0] row_address;
        input [8:0] constant_base;
        reg [12:0] word_base;
        begin
            word_base = {(row_address - constant_base), 2'b00};
            packed_program_row = {
                program_value(word_base + 13'd3),
                program_value(word_base + 13'd2),
                program_value(word_base + 13'd1),
                program_value(word_base)
            };
        end
    endfunction

    function [255:0] expected_tile;
        input [15:0] prefix;
        input [12:0] base_address;
        input signed [9:0] lane_stride;
        input [4:0] lane_count;
        input negate_enable;
        integer lane_index;
        reg signed [13:0] address_value;
        reg [15:0] word_value;
        begin
            expected_tile = 256'd0;
            for (lane_index = 0; lane_index < 16;
                 lane_index = lane_index + 1) begin
                if (lane_index < lane_count) begin
                    address_value = $signed({1'b0, base_address}) +
                        lane_index * lane_stride;
                    word_value = prefix + address_value[12:0];
                    if (negate_enable) begin
                        word_value = word_value ^ 16'h8000;
                    end
                    expected_tile[lane_index*16 +: 16] = word_value;
                end
            end
        end
    endfunction

    task record_check;
        input [8*48-1:0] test_id;
        input [8*16-1:0] requirement_id;
        input [255:0] expected;
        input [255:0] actual;
        begin
            if (actual === expected) begin
                pass_count = pass_count + 1;
                $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=%0s|txn_id=p5_operand_%0d|requirement_id=%0s|operation_id=P5_DIRECT_OPERAND|sent=1|expected=%h|actual=%h|latency_cycles=1|observed_interface=module_boundary|evidence_type=blackbox|check_role=primary|result=PASS", test_id, pass_count + fail_count, requirement_id, expected, actual);
            end
            else begin
                fail_count = fail_count + 1;
                $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=%0s|txn_id=p5_operand_%0d|requirement_id=%0s|operation_id=P5_DIRECT_OPERAND|sent=1|expected=%h|actual=%h|latency_cycles=1|observed_interface=module_boundary|evidence_type=blackbox|check_role=primary|result=FAIL", test_id, pass_count + fail_count, requirement_id, expected, actual);
            end
        end
    endtask

    task send_request;
        input [1:0] space;
        input [12:0] base_address;
        input [9:0] lane_stride;
        input [4:0] lane_count;
        input negate_enable;
        input fast_feature;
        begin
            @(negedge clk);
            request_space = space;
            request_base = base_address;
            request_lane_stride = lane_stride;
            request_lanes = lane_count;
            request_negate = negate_enable;
            request_fast_feature = fast_feature;
            request_repeat_count = 12'd1;
            request_repeat_stride = 13'd0;
            request_valid = 1'b1;
            while (request_ready !== 1'b1) begin
                @(negedge clk);
            end
            @(negedge clk);
            request_valid = 1'b0;
        end
    endtask

    shared_operand_tile_service u_dut (
        .clk(clk),
        .reset_n(reset_n),
        .request_valid(request_valid),
        .request_ready(request_ready),
        .request_space(request_space),
        .request_base(request_base),
        .request_lane_stride(request_lane_stride),
        .request_lanes(request_lanes),
        .request_negate(request_negate),
        .request_fast_feature(request_fast_feature),
        .request_repeat_count(request_repeat_count),
        .request_repeat_stride(request_repeat_stride),
        .fast_issue_allowed(1'b1),
        .constant_base_row(constant_base_row),
        .feature_read_a_valid(feature_read_a_valid),
        .feature_read_a_address(feature_read_a_address),
        .feature_read_b_valid(feature_read_b_valid),
        .feature_read_b_address(feature_read_b_address),
        .feature_read_a_response_valid(feature_read_a_response_valid),
        .feature_read_a_response_data(feature_read_a_response_data),
        .feature_read_b_response_valid(feature_read_b_response_valid),
        .feature_read_b_response_data(feature_read_b_response_data),
        .parameter_read_valid(parameter_read_valid),
        .parameter_read_address(parameter_read_address),
        .parameter_read_response_valid(parameter_read_response_valid),
        .parameter_read_response_data(parameter_read_response_data),
        .program_read_valid(program_read_valid),
        .program_read_address(program_read_address),
        .program_read_response_valid(program_read_response_valid),
        .program_read_response_data(program_read_response_data),
        .response_valid(response_valid),
        .response_ready(response_ready),
        .response_last(response_last),
        .response_half(response_half),
        .response_data(response_data)
    );

    always #5 clk = ~clk;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            feature_read_a_response_valid <= 4'd0;
            feature_read_a_response_data <= 64'd0;
            feature_read_b_response_valid <= 4'd0;
            feature_read_b_response_data <= 64'd0;
            parameter_read_response_valid <= 1'b0;
            parameter_read_response_data <= 64'd0;
            program_read_response_valid <= 1'b0;
            program_read_response_data <= 64'd0;
            feature_issue_cycles <= 0;
            dual_port_issue_cycles <= 0;
            parameter_issue_count <= 0;
            program_issue_count <= 0;
            response_lower_data <= 128'd0;
        end
        else begin
            feature_read_a_response_valid <= feature_read_a_valid;
            feature_read_b_response_valid <= feature_read_b_valid;
            parameter_read_response_valid <= parameter_read_valid;
            program_read_response_valid <= program_read_valid;
            for (bank_index = 0; bank_index < 4;
                 bank_index = bank_index + 1) begin
                feature_read_a_response_data[bank_index*16 +: 16] <=
                    feature_value({feature_read_a_address[
                        bank_index*11 +: 11], bank_index[1:0]});
                feature_read_b_response_data[bank_index*16 +: 16] <=
                    feature_value({feature_read_b_address[
                        bank_index*11 +: 11], bank_index[1:0]});
            end
            if ((feature_read_a_valid != 4'd0) ||
                (feature_read_b_valid != 4'd0)) begin
                feature_issue_cycles <= feature_issue_cycles + 1;
            end
            if ((feature_read_a_valid & feature_read_b_valid) != 4'd0) begin
                dual_port_issue_cycles <= dual_port_issue_cycles + 1;
            end
            if (parameter_read_valid) begin
                parameter_read_response_data <=
                    packed_parameter_row(parameter_read_address);
                parameter_issue_count <= parameter_issue_count + 1;
            end
            if (program_read_valid) begin
                program_read_response_data <= packed_program_row(
                    program_read_address, constant_base_row);
                program_issue_count <= program_issue_count + 1;
            end
            if (response_valid && response_ready && !response_half) begin
                response_lower_data <= response_data;
            end
        end
    end

    initial begin
        clk = 1'b0;
        reset_n = 1'b0;
        request_valid = 1'b0;
        request_space = 2'd0;
        request_base = 13'd0;
        request_lane_stride = 10'd0;
        request_lanes = 5'd0;
        request_negate = 1'b0;
        request_fast_feature = 1'b0;
        request_repeat_count = 12'd1;
        request_repeat_stride = 13'd0;
        constant_base_row = 9'd80;
        response_ready = 1'b1;
        pass_count = 0;
        fail_count = 0;
        test_complete = 1'b0;
        test_passed = 1'b0;

        $display("HDLFLOW|TASK_BEGIN|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P5_DIRECT_OPERAND|requirement_id=REQ-RRB-019");
        repeat (4) @(negedge clk);
        reset_n = 1'b1;

        send_request(2'd0, 13'd32, 9'd1, 5'd16, 1'b0, 1'b1);
        wait ((response_valid === 1'b1) && (response_last === 1'b1));
        record_check("feature_contiguous_16", "REQ-RRB-007",
                     expected_tile(16'h1000, 13'd32, 9'sd1, 5'd16, 1'b0),
                     response_tile_data);
        record_check("feature_aligned_fast_cycles", "REQ-RRB-019",
                     256'd2, feature_issue_cycles);
        @(negedge clk);

        // Two trusted aligned tiles must use a response/request relay.  The
        // second tile may spend only the two physical BRAM issue cycles plus
        // the two registered 128-bit response beats behind the first lower
        // beat.
        send_request(2'd0, 13'd96, 9'd1, 5'd16, 1'b0, 1'b1);
        wait ((response_valid === 1'b1) && (response_half === 1'b0));
        fast_previous_time = $time;
        @(negedge clk);
        request_space = 2'd0;
        request_base = 13'd112;
        request_lane_stride = 9'd1;
        request_lanes = 5'd16;
        request_negate = 1'b0;
        request_fast_feature = 1'b1;
        request_valid = 1'b1;
        while (request_ready !== 1'b1)
            @(negedge clk);
        @(negedge clk);
        request_valid = 1'b0;
        wait ((response_valid === 1'b1) && (response_last === 1'b1));
        record_check("fast_chain_data", "REQ-RRB-007",
                     expected_tile(16'h1000, 13'd112, 9'sd1,
                                   5'd16, 1'b0),
                     response_tile_data);
        record_check("fast_chain_terminal_gap_bounded", "REQ-RRB-019",
                     256'd1,
                     {255'd0, (($time - fast_previous_time) <= 40)});
        @(negedge clk);

        feature_issue_cycles = 0;
        dual_port_issue_cycles = 0;
        send_request(2'd0, 13'd64, 9'd4, 5'd4, 1'b0, 1'b0);
        wait ((response_valid === 1'b1) && (response_last === 1'b1));
        record_check("same_bank_serial_gather", "REQ-RRB-019",
                     expected_tile(16'h1000, 13'd64, 9'sd4, 5'd4, 1'b0),
                     response_tile_data);
        record_check("slow_gather_uses_single_port", "REQ-RRB-019",
                     256'd0, dual_port_issue_cycles);
        @(negedge clk);

        feature_issue_cycles = 0;
        send_request(2'd1, 13'd15, -10'sd1, 5'd8, 1'b1, 1'b0);
        wait ((response_valid === 1'b1) && (response_last === 1'b1));
        record_check("frame_negative_stride", "REQ-RRB-010",
                     expected_tile(16'h1000, 13'd15, -10'sd1, 5'd8, 1'b1),
                     response_tile_data);
        @(negedge clk);

        send_request(2'd0, 13'd32, 10'd256, 5'd6, 1'b0, 1'b0);
        wait ((response_valid === 1'b1) && (response_last === 1'b1));
        record_check("feature_positive_256_stride", "REQ-RRB-010",
                     expected_tile(16'h1000, 13'd32, 10'sd256,
                                   5'd6, 1'b0),
                     response_tile_data);
        @(negedge clk);

        send_request(2'd2, 13'd5, 9'd1, 5'd16, 1'b0, 1'b0);
        wait ((response_valid === 1'b1) && (response_last === 1'b1));
        record_check("parameter_four_word_rows", "REQ-RRB-005",
                     expected_tile(16'h3000, 13'd5, 9'sd1, 5'd16, 1'b0),
                     response_tile_data);
        record_check("parameter_chunk_local_rows", "REQ-RRB-019",
                     256'd8, parameter_issue_count);
        @(negedge clk);

        send_request(2'd3, 13'd2, 9'd2, 5'd7, 1'b0, 1'b0);
        wait ((response_valid === 1'b1) && (response_last === 1'b1));
        record_check("program_constant_offset", "REQ-RRB-005",
                     expected_tile(16'h5000, 13'd2, 9'sd2, 5'd7, 1'b0),
                     response_tile_data);
        record_check("program_affine_single_slot_reads", "REQ-RRB-022",
                     256'd7, program_issue_count);
        @(negedge clk);

        send_request(2'd2, 13'd9, 9'd0, 5'd16, 1'b0, 1'b0);
        wait ((response_valid === 1'b1) && (response_half === 1'b0));
        response_ready = 1'b0;
        repeat (3) begin
            @(negedge clk);
            record_check("lower_beat_stable_under_stall", "REQ-RRB-019",
                         {128'd0, {8{16'h3009}}},
                         {128'd0, response_data});
            record_check("lower_valid_held_under_stall", "REQ-RRB-019",
                         256'd1, {255'd0, response_valid});
            record_check("lower_half_tag_under_stall", "REQ-RRB-019",
                         256'd0, {255'd0, response_half});
        end
        response_ready = 1'b1;
        @(negedge clk);
        wait ((response_valid === 1'b1) && (response_half === 1'b1));
        response_ready = 1'b0;
        repeat (3) begin
            @(negedge clk);
            record_check("upper_beat_stable_under_stall", "REQ-RRB-019",
                         {128'd0, {8{16'h3009}}},
                         {128'd0, response_data});
            record_check("upper_last_held_under_stall", "REQ-RRB-019",
                         256'd1, {255'd0, response_last});
            record_check("upper_half_tag_under_stall", "REQ-RRB-019",
                         256'd1, {255'd0, response_half});
        end
        response_ready = 1'b1;
        @(negedge clk);
        record_check("returns_to_ready", "REQ-RRB-019",
                     256'd1, {255'd0, request_ready});

        // General affine gathers must accept the next request in the same
        // cycle that the current response is consumed.  Otherwise every
        // pool/spatial/pointwise source tile pays an avoidable IDLE bubble.
        send_request(2'd0, 13'd100, 9'd1, 5'd4, 1'b0, 1'b0);
        wait ((response_valid === 1'b1) && (response_last === 1'b1));
        @(negedge clk);
        request_space = 2'd0;
        request_base = 13'd200;
        request_lane_stride = 9'd1;
        request_lanes = 5'd4;
        request_negate = 1'b0;
        request_fast_feature = 1'b0;
        request_valid = 1'b1;
        record_check("general_response_chain_ready", "REQ-RRB-019",
                     256'd1, {255'd0, request_ready});
        while (request_ready !== 1'b1)
            @(negedge clk);
        @(negedge clk);
        request_valid = 1'b0;
        wait ((response_valid === 1'b1) && (response_last === 1'b1));
        record_check("general_response_chain_data", "REQ-RRB-007",
                     expected_tile(16'h1000, 13'd200, 9'sd1,
                                   5'd4, 1'b0),
                     response_tile_data);
        @(negedge clk);

        // A trusted one-lane fast-feature stream is issued as one affine
        // repeated request.  The service owns the per-cycle address advance
        // and marks only the fourth response as terminal.
        @(negedge clk);
        request_space = 2'd0;
        request_base = 13'd400;
        request_lane_stride = 9'd1;
        request_lanes = 5'd1;
        request_negate = 1'b0;
        request_fast_feature = 1'b1;
        request_repeat_count = 12'd4;
        request_repeat_stride = 13'd1;
        request_valid = 1'b1;
        while (request_ready !== 1'b1)
            @(negedge clk);
        @(negedge clk);
        request_valid = 1'b0;
        scalar_previous_time = 0;
        for (scalar_index = 0; scalar_index < 4;
             scalar_index = scalar_index + 1) begin
            wait (response_valid === 1'b1);
            if (scalar_index != 0) begin
                record_check("scalar_stream_response_gap",
                             "REQ-RRB-019", 256'd1,
                             {255'd0,
                              (($time - scalar_previous_time) == 10)});
            end
            record_check("scalar_stream_data", "REQ-RRB-007",
                         expected_tile(16'h1000,
                                       13'd400 + scalar_index,
                                       9'sd1, 5'd1, 1'b0),
                         response_data);
            record_check("scalar_stream_last", "REQ-RRB-019",
                         {255'd0, (scalar_index == 3)},
                         {255'd0, response_last});
            scalar_previous_time = $time;
            @(negedge clk);
        end
        request_repeat_count = 12'd1;
        request_repeat_stride = 13'd0;

        $display("HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P5_DIRECT_OPERAND|passes=%0d|failures=%0d|result=%0s", pass_count, fail_count, (fail_count == 0) ? "PASS" : "FAIL");
        $display("HDLFLOW|TASK_END|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P5_DIRECT_OPERAND|result=%0s", (fail_count == 0) ? "PASS" : "FAIL");
        test_complete = 1'b1;
        test_passed = (fail_count == 0);
        if (fail_count != 0) begin
            $fatal(1, "P5 direct operand service test failed");
        end
        $finish;
    end

    initial begin
        #200000;
        $display("HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P5_DIRECT_OPERAND|passes=%0d|failures=%0d|result=TIMEOUT", pass_count, fail_count + 1);
        $fatal(1, "P5 direct operand service test timeout");
    end
endmodule
// ---- END shared_operand_tile_service_tb.v ----

// ---- BEGIN shared_window_pipeline_tb.v ----
// -----------------------------------------------------------------------------
// Module: shared_window_pipeline_tb
// Purpose: Directed P5 verification of one profile-independent SAME_PAD dot
//          stream using logical feature ports and the shared APX cluster.
// Requirements: REQ-RRB-006, REQ-RRB-007, REQ-RRB-010, REQ-RRB-019
// -----------------------------------------------------------------------------

`timescale 1ns/1ps

module shared_window_pipeline_tb;
    reg clk;
    reg reset_n;
    reg start_valid;
    wire start_ready;
    reg [4:0] start_lanes;
    reg [11:0] start_output_count;
    reg [12:0] start_source_base;
    reg [12:0] start_source_stride;
    reg [15:0] start_tag_base;
    reg [255:0] start_weight_tile;

    wire feature_read_a_valid;
    wire [12:0] feature_read_a_address;
    reg feature_read_a_response_valid;
    reg [15:0] feature_read_a_response_data;

    wire apx_request_valid;
    wire apx_request_ready;
    wire [1:0] apx_request_operation;
    wire [4:0] apx_request_lanes;
    wire [15:0] apx_request_tag;
    wire apx_window_shift;
    wire [15:0] apx_window_sample;
    wire window_resident_clear_valid;
    wire window_resident_seed_valid;
    wire [4:0] window_resident_seed_lanes;
    wire [15:0] window_resident_seed_data;
    wire apx_weight_select;
    wire apx_weight_zero;
    wire [255:0] apx_operand_b_bus;
    wire apx_reduce_valid;
    wire [15:0] apx_reduce_tag;
    wire [15:0] apx_reduce_result;
    wire result_valid;
    wire [15:0] result_tag;
    wire [15:0] result_data;
    wire done;

    integer pass_count;
    integer fail_count;
    integer cycle_count;
    integer initial_issue_cycles;
    integer resident_clear_count;
    integer resident_seed_count;
    integer result_count;
    integer done_count;
    integer first_done_cycle;
    integer prior_issue_cycle;
    integer steady_issue_gap_max;
    integer first_sequence_last_issue_cycle;
    integer second_sequence_first_issue_cycle;
    reg [15:0] actual_results [0:15];
    reg [15:0] actual_tags [0:15];
    reg test_complete;
    reg test_passed;

    function [15:0] feature_word;
        input [12:0] address;
        begin
            case (address)
                13'd100: feature_word = 16'h3c00;
                13'd104: feature_word = 16'h4000;
                13'd108: feature_word = 16'h4200;
                13'd112: feature_word = 16'h4400;
                13'd116: feature_word = 16'h4500;
                13'd120: feature_word = 16'h4600;
                13'd124: feature_word = 16'h4700;
                13'd128: feature_word = 16'h4800;
                13'd200: feature_word = 16'h3c00;
                13'd204: feature_word = 16'h4000;
                13'd208: feature_word = 16'h4200;
                13'd212: feature_word = 16'h4400;
                13'd216: feature_word = 16'h4500;
                13'd220: feature_word = 16'h4600;
                13'd224: feature_word = 16'h4700;
                13'd228: feature_word = 16'h4800;
                default: feature_word = 16'h0000;
            endcase
        end
    endfunction

    task record_check;
        input [8*48-1:0] test_id;
        input [8*16-1:0] requirement_id;
        input [63:0] expected;
        input [63:0] actual;
        begin
            if (actual === expected) begin
                pass_count = pass_count + 1;
                $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=%0s|txn_id=p5_window_%0d|requirement_id=%0s|operation_id=P5_SHARED_WINDOW|sent=1|expected=%h|actual=%h|latency_cycles=1|observed_interface=module_boundary|evidence_type=blackbox|check_role=primary|result=PASS", test_id, pass_count + fail_count, requirement_id, expected, actual);
            end
            else begin
                fail_count = fail_count + 1;
                $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=%0s|txn_id=p5_window_%0d|requirement_id=%0s|operation_id=P5_SHARED_WINDOW|sent=1|expected=%h|actual=%h|latency_cycles=1|observed_interface=module_boundary|evidence_type=blackbox|check_role=primary|result=FAIL", test_id, pass_count + fail_count, requirement_id, expected, actual);
            end
        end
    endtask

    shared_window_pipeline u_dut (
        .clk(clk),
        .reset_n(reset_n),
        .start_valid(start_valid),
        .start_ready(start_ready),
        .start_lanes(start_lanes),
        .start_output_count(start_output_count),
        .start_source_base(start_source_base),
        .start_source_stride(start_source_stride),
        .start_tag_base(start_tag_base),
        .start_weight_select(1'b0),
        .start_weight_zero(1'b0),
        .feature_read_a_valid(feature_read_a_valid),
        .feature_read_a_ready(1'b1),
        .feature_read_a_address(feature_read_a_address),
        .feature_read_a_response_valid(feature_read_a_response_valid),
        .feature_read_a_response_data(feature_read_a_response_data),
        .apx_request_valid(apx_request_valid),
        .apx_request_ready(apx_request_ready),
        .apx_request_operation(apx_request_operation),
        .apx_request_lanes(apx_request_lanes),
        .apx_request_tag(apx_request_tag),
        .apx_window_shift(apx_window_shift),
        .apx_window_sample(apx_window_sample),
        .apx_weight_select(apx_weight_select),
        .apx_weight_zero(apx_weight_zero),
        .window_resident_clear_valid(window_resident_clear_valid),
        .window_resident_seed_valid(window_resident_seed_valid),
        .window_resident_seed_lanes(window_resident_seed_lanes),
        .window_resident_seed_data(window_resident_seed_data),
        .apx_reduce_valid(apx_reduce_valid),
        .apx_reduce_tag(apx_reduce_tag),
        .apx_reduce_result(apx_reduce_result),
        .result_valid(result_valid),
        .result_tag(result_tag),
        .result_data(result_data),
        .done(done)
    );

    assign apx_operand_b_bus = apx_weight_zero ? 256'd0 :
        start_weight_tile;

    apx_cluster u_apx_cluster (
        .clk(clk),
        .reset_n(reset_n),
        .request_valid(apx_request_valid),
        .request_ready(apx_request_ready),
        .busy(),
        .request_operation(apx_request_operation),
        .request_add_vector(1'b0),
        .request_lanes(apx_request_lanes),
        .request_tag(apx_request_tag),
        .operand_a_low_beat(128'd0),
        .operand_a_high_beat(128'd0),
        .operand_b_low_beat(apx_operand_b_bus[127:0]),
        .operand_b_high_beat(apx_operand_b_bus[255:128]),
        .narrow_operand_a_low_beat(128'd0),
        .narrow_operand_a_high_beat(64'd0),
        .narrow_operand_b_low_beat(128'd0),
        .narrow_operand_b_high_beat(64'd0),
        .request_operand_a_select(2'd0),
        .request_operand_b_select(2'd0),
        .request_operand_a_negate(1'b0),
        .request_operand_b_negate(1'b0),
        .request_operand_b_scalar(1'b0),
        .request_operand_b_scalar_value(16'd0),
        .request_window_operand(apx_request_valid),
        .request_window_shift(apx_window_shift),
        .request_window_sample(apx_window_sample),
        .window_resident_clear_valid(window_resident_clear_valid),
        .window_resident_seed_valid(window_resident_seed_valid),
        .window_resident_seed_lanes(window_resident_seed_lanes),
        .window_resident_seed_data(window_resident_seed_data),
        .parallel_add_valid(1'b0),
        .parallel_add_ready(),
        .parallel_add_lanes(5'd0),
        .parallel_add_tag(16'd0),
        .parallel_prefetch_valid(1'b0),
        .parallel_operand_a_pair(1'b0),
        .parallel_prefetch_b_low_beat(128'd0),
        .parallel_prefetch_b_high_beat(64'd0),
        .post_add_valid(1'b0),
        .post_add_ready(),
        .post_add_operand_x(16'd0),
        .post_add_operand_y(16'd0),
        .post_add_tag(16'd0),
        .post_add_result_valid(),
        .post_add_result_tag(),
        .post_add_result(),
        .post_add_pre_valid(),
        .post_add_pre_tag(),
        .product_valid(),
        .product_pre_valid(),
        .product_tag(),
        .product_pre_tag(),
        .product_slot_low_beat(),
        .product_slot_high_beat(),
        .pair_valid(),
        .pair_pre_valid(),
        .pair_tag(),
        .pair_pre_tag(),
        .pair_slot_low_beat(),
        .pair_slot_high_beat(),
        .reduce_valid(apx_reduce_valid),
        .reduce_pre_valid(),
        .reduce_tag(apx_reduce_tag),
        .reduce_pre_tag(),
        .reduce_result(apx_reduce_result)
    );

    always #5 clk = ~clk;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            feature_read_a_response_valid <= 1'b0;
            feature_read_a_response_data <= 16'd0;
            cycle_count <= 0;
            initial_issue_cycles <= 0;
            resident_clear_count <= 0;
            resident_seed_count <= 0;
            result_count <= 0;
            done_count <= 0;
            first_done_cycle <= 0;
            prior_issue_cycle <= -1;
            steady_issue_gap_max <= 0;
            first_sequence_last_issue_cycle <= -1;
            second_sequence_first_issue_cycle <= -1;
        end
        else begin
            cycle_count <= cycle_count + 1;
            feature_read_a_response_valid <= feature_read_a_valid;
            feature_read_a_response_data <=
                feature_word(feature_read_a_address);
            if (feature_read_a_valid &&
                (result_count == 0) && (prior_issue_cycle < 0)) begin
                initial_issue_cycles <= initial_issue_cycles + 1;
            end
            if (window_resident_clear_valid)
                resident_clear_count <= resident_clear_count + 1;
            if (window_resident_seed_valid)
                resident_seed_count <= resident_seed_count + 1;
            if (apx_request_valid && apx_request_ready) begin
                if ((apx_request_tag > (start_tag_base + 16'd1)) &&
                    (prior_issue_cycle >= 0) &&
                    ((cycle_count - prior_issue_cycle) >
                     steady_issue_gap_max)) begin
                    steady_issue_gap_max <= cycle_count - prior_issue_cycle;
                end
                prior_issue_cycle <= cycle_count;
                if (apx_request_tag == 16'h1207)
                    first_sequence_last_issue_cycle <= cycle_count;
                if (apx_request_tag == 16'h1300)
                    second_sequence_first_issue_cycle <= cycle_count;
            end
            if (result_valid) begin
                actual_results[result_count] <= result_data;
                actual_tags[result_count] <= result_tag;
                result_count <= result_count + 1;
            end
            if (done) begin
                done_count <= done_count + 1;
                if (done_count == 0)
                    first_done_cycle <= cycle_count;
            end
        end
    end

    initial begin
        clk = 1'b0;
        reset_n = 1'b0;
        start_valid = 1'b0;
        start_lanes = 5'd0;
        start_output_count = 12'd0;
        start_source_base = 13'd0;
        start_source_stride = 13'd0;
        start_tag_base = 16'd0;
        start_weight_tile = 256'd0;
        pass_count = 0;
        fail_count = 0;
        test_complete = 1'b0;
        test_passed = 1'b0;

        $display("HDLFLOW|TASK_BEGIN|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P5_SHARED_WINDOW|requirement_id=REQ-RRB-019");
        repeat (4) @(negedge clk);
        reset_n = 1'b1;
        repeat (2) @(negedge clk);

        start_lanes = 5'd5;
        start_output_count = 12'd8;
        start_source_base = 13'd100;
        start_source_stride = 13'd4;
        start_tag_base = 16'h1200;
        start_weight_tile = 256'd0;
        start_weight_tile[47:32] = 16'h3c00;
        start_valid = 1'b1;
        @(negedge clk);
        start_valid = 1'b0;

        // A second independent sequence is offered as soon as the producer
        // exposes capacity.  Only its metadata may be queued; its samples must
        // reload the one shared resident after the first issue stream ends.
        wait (start_ready === 1'b1);
        @(negedge clk);
        start_source_base = 13'd200;
        start_tag_base = 16'h1300;
        start_valid = 1'b1;
        @(negedge clk);
        start_valid = 1'b0;

        wait (done_count == 2);
        @(posedge clk);
        @(negedge clk);
        record_check("all_results_returned", "REQ-RRB-006", 64'd16,
                     result_count);
        record_check("ordered_initial_sample_stream", "REQ-RRB-019", 64'd3,
                     initial_issue_cycles);
        record_check("single_resident_reloaded", "REQ-RRB-019", 64'd1,
                     resident_clear_count >= 2);
        record_check("both_seed_streams_loaded", "REQ-RRB-019", 64'd6,
                     resident_seed_count);
        record_check("steady_one_dot_per_cycle", "REQ-RRB-006", 64'd1,
                     steady_issue_gap_max);
        record_check("bounded_first_sequence_cycles", "REQ-RRB-019", 64'd1,
                     first_done_cycle <= 32);
        record_check("queued_sequence_issue_gap", "REQ-RRB-019", 64'd1,
                     (second_sequence_first_issue_cycle -
                      first_sequence_last_issue_cycle) <= 10);
        record_check("bounded_two_sequence_cycles", "REQ-RRB-019", 64'd1,
                     cycle_count <= 55);
        $display("P5_WINDOW_SEQUENCE_CYCLES first=%0d total=%0d issue_gap=%0d",
                 first_done_cycle, cycle_count,
                 second_sequence_first_issue_cycle -
                 first_sequence_last_issue_cycle);
        record_check("result0_center", "REQ-RRB-010", 64'h3c00,
                     actual_results[0]);
        record_check("result1_center", "REQ-RRB-010", 64'h4000,
                     actual_results[1]);
        record_check("result2_center", "REQ-RRB-010", 64'h4200,
                     actual_results[2]);
        record_check("result3_center", "REQ-RRB-010", 64'h4400,
                     actual_results[3]);
        record_check("result4_center", "REQ-RRB-010", 64'h4500,
                     actual_results[4]);
        record_check("result5_center", "REQ-RRB-010", 64'h4600,
                     actual_results[5]);
        record_check("result6_center", "REQ-RRB-010", 64'h4700,
                     actual_results[6]);
        record_check("result7_center", "REQ-RRB-010", 64'h4800,
                     actual_results[7]);
        record_check("first_tag", "REQ-RRB-006", 64'h1200,
                     actual_tags[0]);
        record_check("last_tag", "REQ-RRB-006", 64'h1207,
                     actual_tags[7]);
        record_check("queued_first_tag", "REQ-RRB-006", 64'h1300,
                     actual_tags[8]);
        record_check("queued_last_tag", "REQ-RRB-006", 64'h1307,
                     actual_tags[15]);
        record_check("returns_to_ready", "REQ-RRB-019", 64'd1,
                     start_ready);

        $display("HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P5_SHARED_WINDOW|passes=%0d|failures=%0d|result=%0s", pass_count, fail_count, (fail_count == 0) ? "PASS" : "FAIL");
        $display("HDLFLOW|TASK_END|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P5_SHARED_WINDOW|result=%0s", (fail_count == 0) ? "PASS" : "FAIL");
        test_complete = 1'b1;
        test_passed = (fail_count == 0);
        $finish;
    end

    initial begin
        #2000000;
        $display("P5_WINDOW_TIMEOUT state=%0d lanes=%0d outputs=%0d issued=%0d returned=%0d pending=%0d next_output=%0d next_sample=%0d result_count=%0d prior_issue=%0d apx_valid=%0d apx_ready=%0d reduce_valid=%0d reduce_tag=%h", u_dut.state_q, u_dut.lanes_q, u_dut.output_count_q, u_dut.load_issued_count_q, u_dut.load_returned_count_q, u_dut.sample_pending_q, u_dut.next_output_index_q, u_dut.next_sample_index_q, result_count, prior_issue_cycle, apx_request_valid, apx_request_ready, apx_reduce_valid, apx_reduce_tag);
        $display("HDLFLOW|TASK_END|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P5_SHARED_WINDOW|result=FAIL");
        test_complete = 1'b1;
        test_passed = 1'b0;
        $finish;
    end
endmodule
// ---- END shared_window_pipeline_tb.v ----

// ---- BEGIN ingress_retire_tb.v ----
// -----------------------------------------------------------------------------
// Module: ingress_retire_tb
// Purpose: Directed P3 verification for packed frame ingress, direct four-bank
//          placement, aligned eight-word retire, scalar-tail reuse, and result
//          stream backpressure.
// Requirements: REQ-RRB-009, REQ-RRB-010, REQ-RRB-012, REQ-RRB-020,
//               REQ-RRB-023, REQ-RRB-024
// -----------------------------------------------------------------------------

`timescale 1ns/1ps

module ingress_retire_tb;
    reg clk;
    reg reset_n;
    reg session_busy;
    reg frame_begin;
    reg [1:0] frame_page;
    reg [63:0] frame_config;
    reg frame_valid;
    wire frame_ready;
    reg [63:0] frame_data;
    wire frame_complete;
    wire [8:0] frame_beat_count;

    wire [3:0] ingress_write_valid;
    wire [51:0] ingress_write_address;
    wire [63:0] ingress_write_data;

    reg retire_valid;
    wire retire_ready;
    reg retire_result;
    reg retire_last;
    reg [12:0] retire_destination_base;
    reg [3:0] retire_word_count;
    reg [7:0] retire_lane_mask;
    reg retire_word_mode;
    reg [15:0] retire_word_data;
    reg [127:0] retire_lane_data;
    wire retire_ack;

    reg packet_last_q;
    reg [12:0] packet_destination_q;
    reg [3:0] packet_word_count_q;
    reg [7:0] packet_lane_mask_q;
    reg [127:0] packet_data_q;
    wire retire_accept;
    wire retire_full_commit;
    wire [1:0] retire_state;

    wire [3:0] retire_a_valid;
    wire [51:0] retire_a_address;
    wire [63:0] retire_a_data;
    wire [3:0] retire_b_valid;
    wire [51:0] retire_b_address;
    wire [63:0] retire_b_data;

    wire result_valid;
    reg result_ready;
    wire [15:0] result_data;
    wire result_last;
    wire result_packet_done;

    assign retire_accept = retire_valid && retire_ready;
    assign retire_full_commit = (retire_word_count == 4'd8) &&
        (retire_destination_base[2:0] == 3'd0);
    assign retire_state = retire_result ? 2'd2 :
        (((retire_word_count == 4'd1) || retire_full_commit) ?
         2'd3 : 2'd1);

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            packet_last_q <= 1'b0;
            packet_destination_q <= 13'd0;
            packet_word_count_q <= 4'd0;
            packet_lane_mask_q <= 8'd0;
            packet_data_q <= 128'd0;
        end
        else if (retire_accept) begin
            packet_last_q <= retire_last;
            packet_destination_q <= retire_destination_base;
            packet_word_count_q <= retire_word_count;
            packet_lane_mask_q <= retire_lane_mask;
            packet_data_q <= retire_word_mode ?
                {112'd0, retire_word_data} : retire_lane_data;
        end
    end

    reg [3:0] probe_a_valid;
    reg [51:0] probe_a_address;
    reg [3:0] probe_b_valid;
    reg [51:0] probe_b_address;

    wire [3:0] memory_a_valid;
    wire [3:0] memory_a_write;
    wire [51:0] memory_a_address;
    wire [63:0] memory_a_write_data;
    wire [3:0] memory_a_response_valid;
    wire [63:0] memory_a_response_data;
    wire [3:0] memory_b_valid;
    wire [3:0] memory_b_write;
    wire [51:0] memory_b_address;
    wire [63:0] memory_b_write_data;
    wire [3:0] memory_b_response_valid;
    wire [63:0] memory_b_response_data;

    integer pass_count;
    integer fail_count;
    integer ack_count;
    integer frame_index;
    integer stream_ready_count;
    integer stream_ack_start;
    reg [15:0] held_result_data;
    reg held_result_last;
    reg test_complete;
    reg test_passed;

    assign memory_a_valid = ingress_write_valid | retire_a_valid | probe_a_valid;
    assign memory_a_write = ingress_write_valid | retire_a_valid;
    assign memory_a_address[12:0] = ingress_write_valid[0] ?
                                    ingress_write_address[12:0] :
                                    (retire_a_valid[0] ?
                                     retire_a_address[12:0] :
                                     probe_a_address[12:0]);
    assign memory_a_address[25:13] = ingress_write_valid[1] ?
                                     ingress_write_address[25:13] :
                                     (retire_a_valid[1] ?
                                      retire_a_address[25:13] :
                                      probe_a_address[25:13]);
    assign memory_a_address[38:26] = ingress_write_valid[2] ?
                                     ingress_write_address[38:26] :
                                     (retire_a_valid[2] ?
                                      retire_a_address[38:26] :
                                      probe_a_address[38:26]);
    assign memory_a_address[51:39] = ingress_write_valid[3] ?
                                     ingress_write_address[51:39] :
                                     (retire_a_valid[3] ?
                                      retire_a_address[51:39] :
                                      probe_a_address[51:39]);
    assign memory_a_write_data[15:0] = ingress_write_valid[0] ?
                                       ingress_write_data[15:0] :
                                       retire_a_data[15:0];
    assign memory_a_write_data[31:16] = ingress_write_valid[1] ?
                                        ingress_write_data[31:16] :
                                        retire_a_data[31:16];
    assign memory_a_write_data[47:32] = ingress_write_valid[2] ?
                                        ingress_write_data[47:32] :
                                        retire_a_data[47:32];
    assign memory_a_write_data[63:48] = ingress_write_valid[3] ?
                                        ingress_write_data[63:48] :
                                        retire_a_data[63:48];

    assign memory_b_valid = retire_b_valid | probe_b_valid;
    assign memory_b_write = retire_b_valid;
    assign memory_b_address[12:0] = retire_b_valid[0] ?
                                    retire_b_address[12:0] :
                                    probe_b_address[12:0];
    assign memory_b_address[25:13] = retire_b_valid[1] ?
                                     retire_b_address[25:13] :
                                     probe_b_address[25:13];
    assign memory_b_address[38:26] = retire_b_valid[2] ?
                                     retire_b_address[38:26] :
                                     probe_b_address[38:26];
    assign memory_b_address[51:39] = retire_b_valid[3] ?
                                     retire_b_address[51:39] :
                                     probe_b_address[51:39];
    assign memory_b_write_data = retire_b_data;

    frame_ingress_adapter u_frame_ingress (
        .clk(clk),
        .reset_n(reset_n),
        .session_busy(session_busy),
        .frame_begin(frame_begin),
        .frame_page(frame_page),
        .frame_config(frame_config),
        .frame_valid(frame_valid),
        .frame_ready(frame_ready),
        .frame_data(frame_data),
        .frame_complete(frame_complete),
        .frame_beat_count(frame_beat_count),
        .bank0_write_valid(ingress_write_valid[0]),
        .bank0_write_address(ingress_write_address[12:0]),
        .bank0_write_data(ingress_write_data[15:0]),
        .bank1_write_valid(ingress_write_valid[1]),
        .bank1_write_address(ingress_write_address[25:13]),
        .bank1_write_data(ingress_write_data[31:16]),
        .bank2_write_valid(ingress_write_valid[2]),
        .bank2_write_address(ingress_write_address[38:26]),
        .bank2_write_data(ingress_write_data[47:32]),
        .bank3_write_valid(ingress_write_valid[3]),
        .bank3_write_address(ingress_write_address[51:39]),
        .bank3_write_data(ingress_write_data[63:48])
    );

    unified_retire u_unified_retire (
        .clk(clk),
        .reset_n(reset_n),
        .retire_valid(retire_valid),
        .retire_ready(retire_ready),
        .retire_state(retire_state),
        .packet_last(packet_last_q),
        .packet_destination_base(packet_destination_q),
        .packet_word_count(packet_word_count_q),
        .packet_lane_mask(packet_lane_mask_q),
        .packet_data(packet_data_q),
        .retire_ack(retire_ack),
        .bank_a_write_valid(retire_a_valid),
        .bank_a_write_address(retire_a_address),
        .bank_a_write_data(retire_a_data),
        .bank_b_write_valid(retire_b_valid),
        .bank_b_write_address(retire_b_address),
        .bank_b_write_data(retire_b_data),
        .result_valid(result_valid),
        .result_ready(result_ready),
        .result_data(result_data),
        .result_last(result_last),
        .result_packet_done(result_packet_done)
    );

    feature_memory_subsystem u_feature_memory (
        .clk(clk),
        .reset_n(reset_n),
        .bank0_a_valid(memory_a_valid[0]),
        .bank0_a_write(memory_a_write[0]),
        .bank0_a_address(memory_a_address[12:0]),
        .bank0_a_write_data(memory_a_write_data[15:0]),
        .bank0_a_response_valid(memory_a_response_valid[0]),
        .bank0_a_response_data(memory_a_response_data[15:0]),
        .bank1_a_valid(memory_a_valid[1]),
        .bank1_a_write(memory_a_write[1]),
        .bank1_a_address(memory_a_address[25:13]),
        .bank1_a_write_data(memory_a_write_data[31:16]),
        .bank1_a_response_valid(memory_a_response_valid[1]),
        .bank1_a_response_data(memory_a_response_data[31:16]),
        .bank2_a_valid(memory_a_valid[2]),
        .bank2_a_write(memory_a_write[2]),
        .bank2_a_address(memory_a_address[38:26]),
        .bank2_a_write_data(memory_a_write_data[47:32]),
        .bank2_a_response_valid(memory_a_response_valid[2]),
        .bank2_a_response_data(memory_a_response_data[47:32]),
        .bank3_a_valid(memory_a_valid[3]),
        .bank3_a_write(memory_a_write[3]),
        .bank3_a_address(memory_a_address[51:39]),
        .bank3_a_write_data(memory_a_write_data[63:48]),
        .bank3_a_response_valid(memory_a_response_valid[3]),
        .bank3_a_response_data(memory_a_response_data[63:48]),
        .bank0_b_valid(memory_b_valid[0]),
        .bank0_b_write(memory_b_write[0]),
        .bank0_b_address(memory_b_address[12:0]),
        .bank0_b_write_data(memory_b_write_data[15:0]),
        .bank0_b_response_valid(memory_b_response_valid[0]),
        .bank0_b_response_data(memory_b_response_data[15:0]),
        .bank1_b_valid(memory_b_valid[1]),
        .bank1_b_write(memory_b_write[1]),
        .bank1_b_address(memory_b_address[25:13]),
        .bank1_b_write_data(memory_b_write_data[31:16]),
        .bank1_b_response_valid(memory_b_response_valid[1]),
        .bank1_b_response_data(memory_b_response_data[31:16]),
        .bank2_b_valid(memory_b_valid[2]),
        .bank2_b_write(memory_b_write[2]),
        .bank2_b_address(memory_b_address[38:26]),
        .bank2_b_write_data(memory_b_write_data[47:32]),
        .bank2_b_response_valid(memory_b_response_valid[2]),
        .bank2_b_response_data(memory_b_response_data[47:32]),
        .bank3_b_valid(memory_b_valid[3]),
        .bank3_b_write(memory_b_write[3]),
        .bank3_b_address(memory_b_address[51:39]),
        .bank3_b_write_data(memory_b_write_data[63:48]),
        .bank3_b_response_valid(memory_b_response_valid[3]),
        .bank3_b_response_data(memory_b_response_data[63:48])
    );

    always #5 clk = ~clk;

    always @(posedge clk) begin
        if (!reset_n) begin
            ack_count <= 0;
        end
        else if (retire_ack) begin
            ack_count <= ack_count + 1;
        end
    end

    task record_check;
        input [8*40-1:0] test_id;
        input [8*16-1:0] requirement_id;
        input [63:0] expected;
        input [63:0] actual;
        begin
            if (actual === expected) begin
                pass_count = pass_count + 1;
                $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=%0s|txn_id=p3_%0d|requirement_id=%0s|operation_id=P3_INGRESS_RETIRE|sent=1|expected=%h|actual=%h|latency_cycles=1|observed_interface=module_boundary|evidence_type=blackbox|check_role=primary|result=PASS", test_id, pass_count + fail_count, requirement_id, expected, actual);
            end
            else begin
                fail_count = fail_count + 1;
                $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=%0s|txn_id=p3_%0d|requirement_id=%0s|operation_id=P3_INGRESS_RETIRE|sent=1|expected=%h|actual=%h|latency_cycles=1|observed_interface=module_boundary|evidence_type=blackbox|check_role=primary|result=FAIL", test_id, pass_count + fail_count, requirement_id, expected, actual);
            end
        end
    endtask

    task probe_all_a;
        input [51:0] addresses;
        input [63:0] expected;
        begin
            @(negedge clk);
            probe_a_valid = 4'hF;
            probe_a_address = addresses;
            @(negedge clk);
            probe_a_valid = 4'h0;
            wait (memory_a_response_valid === 4'hF);
            #1 record_check("bank_scoreboard_a", "REQ-RRB-020", expected,
                            memory_a_response_data);
        end
    endtask

    task probe_all_b;
        input [51:0] addresses;
        input [63:0] expected;
        begin
            @(negedge clk);
            probe_b_valid = 4'hF;
            probe_b_address = addresses;
            @(negedge clk);
            probe_b_valid = 4'h0;
            wait (memory_b_response_valid === 4'hF);
            #1 record_check("bank_scoreboard_b", "REQ-RRB-020", expected,
                            memory_b_response_data);
        end
    endtask

    task send_retire_packet;
        input result_select;
        input last_select;
        input [12:0] base_address;
        input [3:0] count;
        input [7:0] mask;
        input [127:0] data;
        begin
            @(negedge clk);
            retire_valid = 1'b1;
            retire_result = result_select;
            retire_last = last_select;
            retire_destination_base = base_address;
            retire_word_count = count;
            retire_lane_mask = mask;
            retire_word_mode = 1'b0;
            retire_word_data = data[15:0];
            retire_lane_data = data;
            while (retire_ready !== 1'b1) begin
                @(negedge clk);
            end
            @(negedge clk);
            retire_valid = 1'b0;
        end
    endtask

    initial begin
        clk = 1'b0;
        reset_n = 1'b0;
        session_busy = 1'b0;
        frame_begin = 1'b0;
        frame_page = 2'd0;
        frame_config = 64'd0;
        frame_valid = 1'b0;
        frame_data = 64'd0;
        retire_valid = 1'b0;
        retire_result = 1'b0;
        retire_last = 1'b0;
        retire_destination_base = 13'd0;
        retire_word_count = 4'd0;
        retire_lane_mask = 8'd0;
        retire_word_mode = 1'b0;
        retire_word_data = 16'd0;
        retire_lane_data = 128'd0;
        result_ready = 1'b0;
        probe_a_valid = 4'd0;
        probe_a_address = 52'd0;
        probe_b_valid = 4'd0;
        probe_b_address = 52'd0;
        pass_count = 0;
        fail_count = 0;
        ack_count = 0;
        stream_ready_count = 0;
        stream_ack_start = 0;
        test_complete = 1'b0;
        test_passed = 1'b0;

        $display("HDLFLOW|TASK_BEGIN|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P3_INGRESS_RETIRE|requirement_id=REQ-RRB-020");
        $display("HDLFLOW|WAVE_MARK|schema=hdlflow_event_v1|version=1|stage=loop1|marker=p3_reset_begin|cycle=0");

        repeat (4) @(negedge clk);
        reset_n = 1'b1;

        session_busy = 1'b1;
        #1 record_check("frame_busy_backpressure", "REQ-RRB-009", 64'd0,
                        {63'd0, frame_ready});
        session_busy = 1'b0;
        frame_page = 2'd3;
        @(negedge clk);
        frame_begin = 1'b1;
        @(negedge clk);
        frame_begin = 1'b0;

        for (frame_index = 0; frame_index < 512; frame_index = frame_index + 1) begin
            frame_data = {16'hD003 ^ frame_index[15:0],
                          16'hD002 ^ frame_index[15:0],
                          16'hD001 ^ frame_index[15:0],
                          16'hD000 ^ frame_index[15:0]};
            frame_valid = 1'b1;
            @(negedge clk);
        end
        frame_valid = 1'b0;
        #1 record_check("frame_512_complete", "REQ-RRB-009", 64'd1,
                        {63'd0, frame_complete});
        record_check("frame_counter_wrap", "REQ-RRB-009", 64'd0,
                     {55'd0, frame_beat_count});

        probe_all_b({13'd6147, 13'd6146, 13'd6145, 13'd6144},
                    64'hD003_D002_D001_D000);
        probe_all_b({13'd8191, 13'd8190, 13'd8189, 13'd8188},
                    {16'hD003 ^ 16'd511, 16'hD002 ^ 16'd511,
                     16'hD001 ^ 16'd511, 16'hD000 ^ 16'd511});

        @(negedge clk);
        retire_valid = 1'b1;
        retire_result = 1'b0;
        retire_last = 1'b0;
        retire_destination_base = 13'd0;
        retire_word_count = 4'd8;
        retire_lane_mask = 8'hFF;
        retire_lane_data = {16'hA007, 16'hA006, 16'hA005, 16'hA004,
                            16'hA003, 16'hA002, 16'hA001, 16'hA000};
        @(negedge clk);
        retire_destination_base = 13'd8;
        retire_lane_data = {16'hB007, 16'hB006, 16'hB005, 16'hB004,
                            16'hB003, 16'hB002, 16'hB001, 16'hB000};
        @(negedge clk);
        retire_valid = 1'b0;
        repeat (2) @(negedge clk);
        record_check("two_aligned_ack_cycles", "REQ-RRB-010", 64'd2,
                     ack_count);

        probe_all_a({13'd3, 13'd2, 13'd1, 13'd0},
                    64'hA003_A002_A001_A000);
        probe_all_b({13'd7, 13'd6, 13'd5, 13'd4},
                    64'hA007_A006_A005_A004);
        probe_all_a({13'd11, 13'd10, 13'd9, 13'd8},
                    64'hB003_B002_B001_B000);
        probe_all_b({13'd15, 13'd14, 13'd13, 13'd12},
                    64'hB007_B006_B005_B004);

        send_retire_packet(1'b0, 1'b0, 13'd17, 4'd5, 8'h1F,
            {48'd0, 16'hE005, 16'hE004, 16'hE003,
             16'hE002, 16'hE001});
        wait (retire_ack === 1'b1);
        probe_all_a({13'd19, 13'd18, 13'd17, 13'd20},
                    64'hE003_E002_E001_E004);
        @(negedge clk);
        probe_a_valid = 4'b0010;
        probe_a_address[25:13] = 13'd21;
        @(negedge clk);
        probe_a_valid = 4'd0;
        wait (memory_a_response_valid[1] === 1'b1);
        #1 record_check("scalar_tail_last", "REQ-RRB-020",
                        64'h0000_0000_0000_E005,
                        {48'd0, memory_a_response_data[31:16]});

        stream_ack_start = ack_count;
        @(negedge clk);
        retire_valid = 1'b1;
        retire_result = 1'b0;
        retire_last = 1'b0;
        retire_word_count = 4'd1;
        retire_lane_mask = 8'h01;
        retire_word_mode = 1'b1;
        for (frame_index = 0; frame_index < 8;
             frame_index = frame_index + 1) begin
            retire_destination_base = 13'd32 + frame_index[12:0];
            retire_word_data = 16'h5100 + frame_index[15:0];
            #1;
            if (retire_ready === 1'b1)
                stream_ready_count = stream_ready_count + 1;
            @(negedge clk);
        end
        retire_valid = 1'b0;
        retire_word_mode = 1'b0;
        repeat (2) @(negedge clk);
        record_check("scalar_stream_ready_each_cycle", "REQ-RRB-010",
                     64'd8, stream_ready_count);
        record_check("scalar_stream_ack_each_cycle", "REQ-RRB-010",
                     64'd8, ack_count - stream_ack_start);
        probe_all_b({13'd35, 13'd34, 13'd33, 13'd32},
                    64'h5103_5102_5101_5100);
        probe_all_b({13'd39, 13'd38, 13'd37, 13'd36},
                    64'h5107_5106_5105_5104);

        send_retire_packet(1'b1, 1'b1, 13'd0, 4'd4, 8'h0F,
            {64'd0, 16'h3C00, 16'h4000, 16'h4200, 16'h4400});
        wait (result_valid === 1'b1);
        held_result_data = result_data;
        held_result_last = result_last;
        repeat (3) begin
            @(posedge clk);
            #1 record_check("result_stable_data", "REQ-RRB-012",
                            {48'd0, held_result_data}, {48'd0, result_data});
            record_check("result_stable_last", "REQ-RRB-012",
                         {63'd0, held_result_last}, {63'd0, result_last});
        end

        record_check("result_lane0", "REQ-RRB-012",
                     64'h0000_0000_0000_4400, {48'd0, result_data});
        result_ready = 1'b1;
        @(posedge clk);
        #1 record_check("result_lane1", "REQ-RRB-012",
                        64'h0000_0000_0000_4200, {48'd0, result_data});
        @(posedge clk);
        #1 record_check("result_lane2", "REQ-RRB-012",
                        64'h0000_0000_0000_4000, {48'd0, result_data});
        @(posedge clk);
        #1 record_check("result_lane3", "REQ-RRB-012",
                        64'h0000_0000_0000_3C00, {48'd0, result_data});
        record_check("result_last_final_lane", "REQ-RRB-012", 64'd1,
                     {63'd0, result_last});
        @(posedge clk);
        @(negedge clk);
        result_ready = 1'b0;
        wait (retire_ack === 1'b1);

        $display("HDLFLOW|WAVE_MARK|schema=hdlflow_event_v1|version=1|stage=loop1|marker=p3_done|passes=%0d|failures=%0d", pass_count, fail_count);
        $display("HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P3_INGRESS_RETIRE|passes=%0d|failures=%0d|result=%0s", pass_count, fail_count, (fail_count == 0) ? "PASS" : "FAIL");
        $display("HDLFLOW|TASK_END|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P3_INGRESS_RETIRE|result=%0s", (fail_count == 0) ? "PASS" : "FAIL");
        test_complete = 1'b1;
        test_passed = (fail_count == 0);
        if (fail_count != 0) begin
            $fatal(1, "P3 ingress/retire directed test failed");
        end
        $finish;
    end

    initial begin
        #100000;
        $display("HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P3_INGRESS_RETIRE|passes=%0d|failures=%0d|result=TIMEOUT", pass_count, fail_count + 1);
        $fatal(1, "P3 ingress/retire directed test timeout");
    end
endmodule
// ---- END ingress_retire_tb.v ----

// ---- BEGIN descriptor_execution_engine_tb.v ----
// -----------------------------------------------------------------------------
// Module: descriptor_execution_engine_tb
// Purpose: P5 integration test for descriptor decode, two-slot weight prefetch,
//          SAME_PAD, gather dot products, ordered pool scaling, raw COPY, one
//          shared APX cluster, and one ordered retirement path.
// Requirements: REQ-RRB-005, REQ-RRB-006, REQ-RRB-010, REQ-RRB-019,
//               REQ-RRB-020, REQ-RRB-022
// -----------------------------------------------------------------------------

`timescale 1ns/1ps

module descriptor_execution_engine_tb;
    reg clk;
    reg reset_n;
    reg descriptor_valid;
    wire descriptor_ready;
    reg [8:0] descriptor_pc;
    reg [63:0] descriptor_base;
    reg [63:0] descriptor_ext0;
    reg [63:0] descriptor_ext1;
    reg [63:0] descriptor_ext2;
    wire descriptor_complete;
    wire busy;

    wire parameter_read_valid;
    wire [8:0] parameter_read_address;
    reg parameter_read_response_valid;
    reg [63:0] parameter_read_response_data;
    wire program_read_valid;
    wire [8:0] program_read_address;
    reg program_read_response_valid;
    reg [63:0] program_read_response_data;

    wire [3:0] feature_a_valid;
    wire [3:0] feature_a_write;
    wire [51:0] feature_a_address;
    wire [63:0] feature_a_write_data;
    reg [3:0] feature_a_response_valid;
    reg [63:0] feature_a_response_data;
    wire [3:0] feature_b_valid;
    wire [3:0] feature_b_write;
    wire [51:0] feature_b_address;
    wire [63:0] feature_b_write_data;
    reg [3:0] feature_b_response_valid;
    reg [63:0] feature_b_response_data;

    wire result_valid;
    reg result_ready;
    wire [15:0] result_data;
    wire result_last;

    reg [15:0] feature_memory [0:8191];
    reg [15:0] parameter_memory [0:63];
    integer pass_count;
    integer fail_count;
    integer cycle_count;
    integer feature_write_count;
    integer parameter_read_count;
    integer overlapped_prefetch_count;
    integer apx_request_count;
    integer complete_count;
    integer descriptor_start_cycle;
    integer last_descriptor_latency;
    integer index;
    integer group_index;
    integer i0_index;
    integer i1_index;
    integer i2_index;
    integer bank;
    integer write_offset;
    integer write_count_before;
    integer apx_count_before;
    integer result_word_count;
    integer result_last_count;
    integer result_count_before;
    reg [15:0] result_words [0:31];
    reg [15:0] stalled_result_data;
    reg stalled_result_last;
    integer write_cycle [0:127];
    reg test_complete;
    reg test_passed;
    reg generic_primitives_complete;

    function [63:0] pack_operand;
        input [1:0] space;
        input [12:0] base_address;
        input [12:0] stride0;
        input [12:0] stride1;
        input [12:0] stride2;
        input [8:0] lane_stride;
        input negate;
        begin
            pack_operand = {space, base_address, stride0, stride1,
                            stride2, lane_stride, negate};
        end
    endfunction

    task record_check;
        input [8*48-1:0] test_id;
        input [8*16-1:0] requirement_id;
        input [63:0] expected;
        input [63:0] actual;
        begin
            if (actual === expected) begin
                pass_count = pass_count + 1;
                $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=%0s|txn_id=p5_engine_%0d|requirement_id=%0s|operation_id=P5_DESCRIPTOR_ENGINE|sent=1|expected=%h|actual=%h|latency_cycles=1|observed_interface=module_boundary|evidence_type=blackbox|check_role=primary|result=PASS", test_id, pass_count + fail_count, requirement_id, expected, actual);
            end
            else begin
                fail_count = fail_count + 1;
                $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=%0s|txn_id=p5_engine_%0d|requirement_id=%0s|operation_id=P5_DESCRIPTOR_ENGINE|sent=1|expected=%h|actual=%h|latency_cycles=1|observed_interface=module_boundary|evidence_type=blackbox|check_role=primary|result=FAIL", test_id, pass_count + fail_count, requirement_id, expected, actual);
            end
        end
    endtask

    task send_descriptor;
        input [8:0] pc;
        input [63:0] base_word;
        input [63:0] ext0_word;
        input [63:0] ext1_word;
        input [63:0] ext2_word;
        begin
            @(negedge clk);
            descriptor_pc = pc;
            descriptor_base = base_word;
            descriptor_ext0 = ext0_word;
            descriptor_ext1 = ext1_word;
            descriptor_ext2 = ext2_word;
            descriptor_valid = 1'b1;
            while (descriptor_ready !== 1'b1)
                @(negedge clk);
            @(negedge clk);
            descriptor_valid = 1'b0;
            wait (descriptor_complete === 1'b1);
            @(posedge clk);
            @(negedge clk);
        end
    endtask

    descriptor_execution_engine u_dut (
        .clk(clk),
        .reset_n(reset_n),
        .descriptor_valid(descriptor_valid),
        .descriptor_ready(descriptor_ready),
        .descriptor_pc(descriptor_pc),
        .descriptor_base(descriptor_base),
        .descriptor_ext0(descriptor_ext0),
        .descriptor_ext1(descriptor_ext1),
        .descriptor_ext2(descriptor_ext2),
        .descriptor_complete(descriptor_complete),
        .busy(busy),
        .parameter_read_valid(parameter_read_valid),
        .parameter_read_address(parameter_read_address),
        .parameter_read_response_valid(parameter_read_response_valid),
        .parameter_read_response_data(parameter_read_response_data),
        .program_read_valid(program_read_valid),
        .program_read_address(program_read_address),
        .program_read_response_valid(program_read_response_valid),
        .program_read_response_data(program_read_response_data),
        .bank0_a_valid(feature_a_valid[0]),
        .bank0_a_write(feature_a_write[0]),
        .bank0_a_address(feature_a_address[12:0]),
        .bank0_a_write_data(feature_a_write_data[15:0]),
        .bank0_a_response_valid(feature_a_response_valid[0]),
        .bank0_a_response_data(feature_a_response_data[15:0]),
        .bank1_a_valid(feature_a_valid[1]),
        .bank1_a_write(feature_a_write[1]),
        .bank1_a_address(feature_a_address[25:13]),
        .bank1_a_write_data(feature_a_write_data[31:16]),
        .bank1_a_response_valid(feature_a_response_valid[1]),
        .bank1_a_response_data(feature_a_response_data[31:16]),
        .bank2_a_valid(feature_a_valid[2]),
        .bank2_a_write(feature_a_write[2]),
        .bank2_a_address(feature_a_address[38:26]),
        .bank2_a_write_data(feature_a_write_data[47:32]),
        .bank2_a_response_valid(feature_a_response_valid[2]),
        .bank2_a_response_data(feature_a_response_data[47:32]),
        .bank3_a_valid(feature_a_valid[3]),
        .bank3_a_write(feature_a_write[3]),
        .bank3_a_address(feature_a_address[51:39]),
        .bank3_a_write_data(feature_a_write_data[63:48]),
        .bank3_a_response_valid(feature_a_response_valid[3]),
        .bank3_a_response_data(feature_a_response_data[63:48]),
        .bank0_b_valid(feature_b_valid[0]),
        .bank0_b_write(feature_b_write[0]),
        .bank0_b_address(feature_b_address[12:0]),
        .bank0_b_write_data(feature_b_write_data[15:0]),
        .bank0_b_response_valid(feature_b_response_valid[0]),
        .bank0_b_response_data(feature_b_response_data[15:0]),
        .bank1_b_valid(feature_b_valid[1]),
        .bank1_b_write(feature_b_write[1]),
        .bank1_b_address(feature_b_address[25:13]),
        .bank1_b_write_data(feature_b_write_data[31:16]),
        .bank1_b_response_valid(feature_b_response_valid[1]),
        .bank1_b_response_data(feature_b_response_data[31:16]),
        .bank2_b_valid(feature_b_valid[2]),
        .bank2_b_write(feature_b_write[2]),
        .bank2_b_address(feature_b_address[38:26]),
        .bank2_b_write_data(feature_b_write_data[47:32]),
        .bank2_b_response_valid(feature_b_response_valid[2]),
        .bank2_b_response_data(feature_b_response_data[47:32]),
        .bank3_b_valid(feature_b_valid[3]),
        .bank3_b_write(feature_b_write[3]),
        .bank3_b_address(feature_b_address[51:39]),
        .bank3_b_write_data(feature_b_write_data[63:48]),
        .bank3_b_response_valid(feature_b_response_valid[3]),
        .bank3_b_response_data(feature_b_response_data[63:48]),
        .result_valid(result_valid),
        .result_ready(result_ready),
        .result_data(result_data),
        .result_last(result_last)
    );

    always #5 clk = ~clk;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            cycle_count <= 0;
            feature_write_count <= 0;
            parameter_read_count <= 0;
            overlapped_prefetch_count <= 0;
            apx_request_count <= 0;
            complete_count <= 0;
            result_word_count <= 0;
            result_last_count <= 0;
            descriptor_start_cycle <= 0;
            last_descriptor_latency <= 0;
            parameter_read_response_valid <= 1'b0;
            parameter_read_response_data <= 64'd0;
            program_read_response_valid <= 1'b0;
            program_read_response_data <= 64'd0;
            feature_a_response_valid <= 4'd0;
            feature_a_response_data <= 64'd0;
            feature_b_response_valid <= 4'd0;
            feature_b_response_data <= 64'd0;
        end
        else begin
            cycle_count <= cycle_count + 1;
            write_offset = 0;
            if (descriptor_valid && descriptor_ready)
                descriptor_start_cycle <= cycle_count;
            if (descriptor_complete) begin
                complete_count <= complete_count + 1;
                last_descriptor_latency <=
                    cycle_count - descriptor_start_cycle;
            end
            if (u_dut.apx_request_valid && u_dut.apx_request_ready)
                apx_request_count <= apx_request_count + 1;
            if (result_valid && result_ready) begin
                result_words[result_word_count] <= result_data;
                result_word_count <= result_word_count + 1;
                if (result_last)
                    result_last_count <= result_last_count + 1;
            end
            parameter_read_response_valid <= parameter_read_valid;
            parameter_read_response_data <= {
                parameter_memory[{parameter_read_address, 2'b11}],
                parameter_memory[{parameter_read_address, 2'b10}],
                parameter_memory[{parameter_read_address, 2'b01}],
                parameter_memory[{parameter_read_address, 2'b00}]
            };
            program_read_response_valid <= program_read_valid;
            program_read_response_data <=
                (program_read_address == 9'd12) ?
                {48'd0, 16'h3400} : 64'd0;
            if (parameter_read_valid) begin
                parameter_read_count <= parameter_read_count + 1;
                if (u_dut.state_q == u_dut.STATE_WINDOW_RUN)
                    overlapped_prefetch_count <=
                        overlapped_prefetch_count + 1;
            end
            for (bank = 0; bank < 4; bank = bank + 1) begin
                feature_a_response_valid[bank] <=
                    feature_a_valid[bank] && !feature_a_write[bank];
                feature_b_response_valid[bank] <=
                    feature_b_valid[bank] && !feature_b_write[bank];
                if (feature_a_valid[bank] && !feature_a_write[bank])
                    feature_a_response_data[bank*16 +: 16] <=
                        feature_memory[feature_a_address[bank*13 +: 13]];
                if (feature_b_valid[bank] && !feature_b_write[bank])
                    feature_b_response_data[bank*16 +: 16] <=
                        feature_memory[feature_b_address[bank*13 +: 13]];
                if (feature_a_valid[bank] && feature_a_write[bank]) begin
                    feature_memory[feature_a_address[bank*13 +: 13]] <=
                        feature_a_write_data[bank*16 +: 16];
                    write_cycle[feature_write_count + write_offset] <=
                        cycle_count;
                    write_offset = write_offset + 1;
                end
                if (feature_b_valid[bank] && feature_b_write[bank]) begin
                    feature_memory[feature_b_address[bank*13 +: 13]] <=
                        feature_b_write_data[bank*16 +: 16];
                    write_cycle[feature_write_count + write_offset] <=
                        cycle_count;
                    write_offset = write_offset + 1;
                end
            end
            feature_write_count <= feature_write_count + write_offset;
        end
    end

    initial begin
        clk = 1'b0;
        reset_n = 1'b0;
        descriptor_valid = 1'b0;
        descriptor_pc = 9'd0;
        descriptor_base = 64'd0;
        descriptor_ext0 = 64'd0;
        descriptor_ext1 = 64'd0;
        descriptor_ext2 = 64'd0;
        result_ready = 1'b1;
        pass_count = 0;
        fail_count = 0;
        test_complete = 1'b0;
        test_passed = 1'b0;
        generic_primitives_complete = 1'b0;
        for (index = 0; index < 8192; index = index + 1)
            feature_memory[index] = 16'd0;
        for (index = 0; index < 64; index = index + 1)
            parameter_memory[index] = 16'd0;
        for (index = 0; index < 8; index = index + 1) begin
            feature_memory[100 + index*4] = 16'h3c00;
            feature_memory[164 + index*4] = 16'h3c00;
        end
        parameter_memory[2] = 16'h3c00;
        parameter_memory[7] = 16'h4000;

        $display("HDLFLOW|TASK_BEGIN|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P5_DESCRIPTOR_ENGINE|requirement_id=REQ-RRB-019");
        repeat (4) @(negedge clk);
        reset_n = 1'b1;

        send_descriptor(9'd0,
            {4'h0, 2'd1, 4'd1, 6'd0, 12'd16, 12'd10,
             12'd2048, 12'd16},
            {33'd0, 9'd12, 22'd0}, 64'd0, 64'd0);

        send_descriptor(9'd2,
            {4'h1, 2'd3, 4'd3, 6'b000010, 12'd2, 12'd8,
             12'd1, 12'd5},
            pack_operand(2'd0, 13'd100, 13'd64, 13'd4,
                         13'd0, 9'd4, 1'b0),
            pack_operand(2'd2, 13'd0, 13'd5, 13'd0,
                         13'd0, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd200, 13'd16, 13'd1,
                         13'd0, 9'd0, 1'b0));

        record_check("two_descriptors_complete", "REQ-RRB-022", 64'd2,
                     complete_count);
        record_check("sixteen_scalar_writes", "REQ-RRB-010", 64'd16,
                     feature_write_count);
        record_check("scheduled_parameter_rows", "REQ-RRB-019", 64'd5,
                     parameter_read_count);
        record_check("second_weight_prefetched", "REQ-RRB-019", 64'd1,
                     overlapped_prefetch_count > 0);
        record_check("weight_slot_switched", "REQ-RRB-019", 64'd1,
                     u_dut.active_weight_slot_q);
        for (index = 0; index < 8; index = index + 1) begin
            record_check("sequence0_result", "REQ-RRB-006", 64'h3c00,
                         feature_memory[200 + index]);
            record_check("sequence1_result", "REQ-RRB-006", 64'h4000,
                         feature_memory[216 + index]);
        end
        record_check("sequence0_startup_gap_bounded", "REQ-RRB-019", 64'd1,
                     (write_cycle[1] - write_cycle[0]) <= 2);
        for (index = 2; index < 8; index = index + 1)
            record_check("sequence0_write_each_cycle", "REQ-RRB-010", 64'd1,
                         write_cycle[index] - write_cycle[index-1]);
        record_check("sequence1_startup_gap_bounded", "REQ-RRB-019", 64'd1,
                     (write_cycle[9] - write_cycle[8]) <= 2);
        for (index = 10; index < 16; index = index + 1)
            record_check("sequence1_write_each_cycle", "REQ-RRB-010", 64'd1,
                         write_cycle[index] - write_cycle[index-1]);
        record_check("engine_returns_ready", "REQ-RRB-019", 64'd1,
                     descriptor_ready);

        for (index = 0; index < 8; index = index + 1) begin
            feature_memory[400 + index*4] = 16'h3c00;
            feature_memory[464 + index*4] = 16'h3c00;
        end
        parameter_memory[18] = 16'h3c00;
        parameter_memory[23] = 16'h4000;
        parameter_memory[26] = 16'hc400;
        send_descriptor(9'd6,
            {4'h1, 2'd3, 4'd3, 6'b001110, 12'd1, 12'd8,
             12'd2, 12'd5},
            pack_operand(2'd0, 13'd400, 13'd0, 13'd4,
                         13'd64, 9'd4, 1'b0),
            pack_operand(2'd2, 13'd16, 13'd0, 13'd0,
                         13'd5, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd600, 13'd0, 13'd1,
                         13'd0, 9'd0, 1'b0));

        record_check("three_descriptors_complete", "REQ-RRB-022", 64'd3,
                     complete_count);
        record_check("multiplane_writes_only_final_sum", "REQ-RRB-010",
                     64'd24, feature_write_count);
        record_check("bias_tail_parameter_fetched", "REQ-RRB-019",
                     64'd11, parameter_read_count);
        for (index = 0; index < 8; index = index + 1)
            record_check("bias_then_relu_result", "REQ-RRB-006",
                         64'h0000, feature_memory[600 + index]);
        for (index = 17; index < 24; index = index + 1)
            record_check("multiplane_aligned_same_cycle", "REQ-RRB-010",
                         64'd0, write_cycle[index] - write_cycle[16]);

        for (index = 0; index < 8; index = index + 1) begin
            feature_memory[700 + index*4] = 16'h3c00;
            feature_memory[764 + index*4] = 16'h3c00;
        end
        parameter_memory[34] = 16'h3c00;
        parameter_memory[37] = 16'hc000;
        parameter_memory[40] = 16'h4000;
        parameter_memory[43] = 16'hbc00;
        send_descriptor(9'd10,
            {4'h1, 2'd3, 4'd3, 6'b001110, 12'd2, 12'd8,
             12'd1, 12'd5},
            pack_operand(2'd0, 13'd700, 13'd64, 13'd4,
                         13'd0, 9'd4, 1'b0),
            pack_operand(2'd2, 13'd32, 13'd6, 13'd0,
                         13'd5, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd800, 13'd16, 13'd1,
                         13'd0, 9'd0, 1'b0));

        record_check("four_descriptors_complete", "REQ-RRB-022", 64'd4,
                     complete_count);
        record_check("two_bias_groups_write_once", "REQ-RRB-010", 64'd40,
                     feature_write_count);
        for (index = 0; index < 8; index = index + 1) begin
            record_check("bias_group0_relu_result", "REQ-RRB-006",
                         64'h0000, feature_memory[800 + index]);
            record_check("bias_group1_result", "REQ-RRB-006",
                         64'h3c00, feature_memory[816 + index]);
        end

        for (index = 0; index < 4; index = index + 1) begin
            feature_memory[1000 + index] = 16'h3c00;
            feature_memory[1004 + index] = 16'h3800;
            feature_memory[1016 + index] = 16'h4000;
            feature_memory[1020 + index] = 16'h3c00;
            parameter_memory[48 + index] = 16'h3c00;
            parameter_memory[53 + index] = 16'h3800;
        end
        parameter_memory[52] = 16'hc000;
        parameter_memory[57] = 16'hbc00;
        write_count_before = feature_write_count;
        send_descriptor(9'd14,
            {4'h1, 2'd3, 4'd3, 6'b001100, 12'd2, 12'd2,
             12'd1, 12'd4},
            pack_operand(2'd0, 13'd1000, 13'd16, 13'd4,
                         13'd0, 9'd1, 1'b0),
            pack_operand(2'd2, 13'd48, 13'd5, 13'd0,
                         13'd4, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd904, 13'd8, 13'd1,
                         13'd0, 9'd0, 1'b0));

        record_check("gather_two_groups_write_once", "REQ-RRB-010", 64'd4,
                     feature_write_count - write_count_before);
        record_check("gather_group0_sample0", "REQ-RRB-006", 64'h4000,
                     feature_memory[904]);
        record_check("gather_group0_sample1_relu", "REQ-RRB-006", 64'h0000,
                     feature_memory[905]);
        record_check("gather_group1_sample0", "REQ-RRB-006", 64'h4200,
                     feature_memory[912]);
        record_check("gather_group1_sample1", "REQ-RRB-006", 64'h3c00,
                     feature_memory[913]);

        for (index = 0; index < 4; index = index + 1) begin
            feature_memory[1100 + index] = 16'h3c00;
            feature_memory[1108 + index] = 16'h4000;
            parameter_memory[index] = 16'h3c00;
            parameter_memory[4 + index] = 16'h3800;
        end
        parameter_memory[8] = 16'hc000;
        write_count_before = feature_write_count;
        send_descriptor(9'd18,
            {4'h1, 2'd3, 4'd3, 6'b000100, 12'd1, 12'd1,
             12'd2, 12'd4},
            pack_operand(2'd0, 13'd1100, 13'd0, 13'd0,
                         13'd8, 9'd1, 1'b0),
            pack_operand(2'd2, 13'd0, 13'd0, 13'd0,
                         13'd4, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd960, 13'd0, 13'd1,
                         13'd0, 9'd0, 1'b0));

        record_check("dense_partial_chunk_write_once", "REQ-RRB-010", 64'd1,
                     feature_write_count - write_count_before);
        record_check("dense_two_plane_bias_result", "REQ-RRB-006", 64'h4600,
                     feature_memory[960]);

        for (index = 0; index < 4; index = index + 1) begin
            feature_memory[1200 + index] = 16'h0000;
            feature_memory[1204 + index] = 16'h3c00;
        end
        feature_memory[1208] = 16'h3c00;
        feature_memory[1209] = 16'h4000;
        feature_memory[1210] = 16'h4200;
        feature_memory[1211] = 16'h4400;
        feature_memory[1212] = 16'h33c8;
        feature_memory[1213] = 16'h378c;
        feature_memory[1214] = 16'h3534;
        feature_memory[1215] = 16'h34a8;
        write_count_before = feature_write_count;
        send_descriptor(9'd22,
            {4'h1, 2'd3, 4'd4, 6'b000001, 12'd1, 12'd4,
             12'd4, 12'd1},
            pack_operand(2'd0, 13'd1200, 13'd0, 13'd4,
                         13'd1, 9'd1, 1'b0),
            pack_operand(2'd3, 13'd0, 13'd0, 13'd0,
                         13'd0, 9'd0, 1'b0),
            pack_operand(2'd0, 13'd984, 13'd0, 13'd1,
                         13'd0, 9'd0, 1'b0));

        record_check("pool_descriptor_complete", "REQ-RRB-022", 64'd7,
                     complete_count);
        record_check("pool_writes_once", "REQ-RRB-010", 64'd4,
                     feature_write_count - write_count_before);
        record_check("pool_zero_ordered_scale", "REQ-RRB-006", 64'h0000,
                     feature_memory[984]);
        record_check("pool_ones_average", "REQ-RRB-006", 64'h3c00,
                     feature_memory[985]);
        record_check("pool_ramp_average", "REQ-RRB-006", 64'h4100,
                     feature_memory[986]);
        record_check("pool_preserves_raw_scalar", "REQ-RRB-006", 64'h3553,
                     feature_memory[987]);
        $display("P5_POOL_SCALAR_LATENCY cycles=%0d",
                 last_descriptor_latency);

        // A vectorized pool result may target sample-major storage.  Its
        // destination stride must be honored after scaling instead of writing
        // each eight-word result as one contiguous channel-major burst.
        for (i0_index = 0; i0_index < 2; i0_index = i0_index + 1)
            for (i1_index = 0; i1_index < 4; i1_index = i1_index + 1)
                for (i2_index = 0; i2_index < 4;
                     i2_index = i2_index + 1)
                    feature_memory[1500 + i0_index*16 +
                                   i1_index*4 + i2_index] =
                        i0_index ? 16'h4000 : 16'h3c00;
        write_count_before = feature_write_count;
        send_descriptor(9'd22,
            {4'h1, 2'd3, 4'd4, 6'b000001, 12'd2, 12'd4,
             12'd4, 12'd1},
            pack_operand(2'd0, 13'd1500, 13'd16, 13'd4,
                         13'd1, 9'd1, 1'b0),
            pack_operand(2'd3, 13'd0, 13'd0, 13'd0,
                         13'd0, 9'd0, 1'b0),
            pack_operand(2'd0, 13'd1560, 13'd1, 13'd2,
                         13'd0, 9'd0, 1'b0));
        record_check("pool_strided_writes_once", "REQ-RRB-010", 64'd8,
                     feature_write_count - write_count_before);
        for (i1_index = 0; i1_index < 4; i1_index = i1_index + 1) begin
            record_check("pool_strided_row0", "REQ-RRB-006", 16'h3c00,
                         feature_memory[1560 + i1_index*2]);
            record_check("pool_strided_row1", "REQ-RRB-006", 16'h4000,
                         feature_memory[1561 + i1_index*2]);
        end

        for (index = 0; index < 32; index = index + 1)
            feature_memory[1300 + index] = 16'h3000 + index;
        write_count_before = feature_write_count;
        apx_count_before = apx_request_count;
        send_descriptor(9'd26,
            {4'h1, 2'd3, 4'd1, 6'd0, 12'd4, 12'd1,
             12'd1, 12'd8},
            pack_operand(2'd0, 13'd1300, 13'd8, 13'd0,
                         13'd0, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd0, 13'd0, 13'd0,
                         13'd0, 9'd0, 1'b0),
            pack_operand(2'd0, 13'd1400, 13'd8, 13'd0,
                         13'd0, 9'd1, 1'b0));

        record_check("copy_descriptor_complete", "REQ-RRB-022", 64'd9,
                     complete_count);
        record_check("copy_writes_exactly_once", "REQ-RRB-010", 64'd32,
                     feature_write_count - write_count_before);
        record_check("copy_bypasses_apx", "REQ-RRB-019", 64'd0,
                     apx_request_count - apx_count_before);
        for (group_index = 0; group_index < 4;
             group_index = group_index + 1)
            for (index = 0; index < 8; index = index + 1)
                record_check("copy_contiguous_word", "REQ-RRB-006",
                             16'h3000 + group_index*8 + index,
                             feature_memory[1400 + group_index*8 + index]);

        for (i0_index = 0; i0_index < 2; i0_index = i0_index + 1)
            for (i1_index = 0; i1_index < 2; i1_index = i1_index + 1)
                for (i2_index = 0; i2_index < 2;
                     i2_index = i2_index + 1)
                    for (index = 0; index < 8; index = index + 1)
                        feature_memory[1600 + i0_index*64 +
                                       i1_index*32 + i2_index*8 + index] =
                            16'h5000 + i0_index*32 + i1_index*16 +
                            i2_index*8 + index;
        write_count_before = feature_write_count;
        apx_count_before = apx_request_count;
        // The compiler lowers a strided 2x2x2 layout into four flat COPY
        // descriptors.  Each descriptor moves two aligned eight-word tiles;
        // the PL never carries the nested-layout branch machinery.
        for (i0_index = 0; i0_index < 2; i0_index = i0_index + 1)
            for (i1_index = 0; i1_index < 2; i1_index = i1_index + 1)
                send_descriptor(9'd30 + (i0_index*2 + i1_index)*4,
                    {4'h1, 2'd3, 4'd1, 6'd0, 12'd2, 12'd1,
                     12'd1, 12'd8},
                    pack_operand(2'd0,
                                 13'd1600 + i0_index*64 + i1_index*32,
                                 13'd8, 13'd0, 13'd0, 9'd1, 1'b0),
                    pack_operand(2'd0, 13'd0, 13'd0, 13'd0,
                                 13'd0, 9'd0, 1'b0),
                    pack_operand(2'd0,
                                 13'd2048 + i0_index*64 + i1_index*32,
                                 13'd8, 13'd0, 13'd0, 9'd1, 1'b0));

        record_check("copy_compiler_split_descriptors_complete",
                     "REQ-RRB-022", 64'd13, complete_count);
        record_check("copy_nested_writes_exactly_once", "REQ-RRB-010",
                     64'd64, feature_write_count - write_count_before);
        record_check("copy_nested_bypasses_apx", "REQ-RRB-019", 64'd0,
                     apx_request_count - apx_count_before);
        for (i0_index = 0; i0_index < 2; i0_index = i0_index + 1)
            for (i1_index = 0; i1_index < 2; i1_index = i1_index + 1)
                for (i2_index = 0; i2_index < 2;
                     i2_index = i2_index + 1)
                    for (index = 0; index < 8; index = index + 1)
                        record_check("copy_nested_strided_word",
                                     "REQ-RRB-006",
                                     16'h5000 + i0_index*32 +
                                     i1_index*16 + i2_index*8 + index,
                                     feature_memory[2048 + i0_index*64 +
                                         i1_index*32 + i2_index*8 +
                                         index]);

        // The current EEG program lowers COPY to four contiguous eight-word
        // microtiles.  Its measured engine latency must preserve at least the
        // 1,000-cycle full-program planning margin.
        for (index = 0; index < 32; index = index + 1)
            feature_memory[1800 + index] = 16'h6000 + index;
        write_count_before = feature_write_count;
        apx_count_before = apx_request_count;
        send_descriptor(9'd46,
            {4'h1, 2'd3, 4'd1, 6'd0, 12'd4, 12'd1,
             12'd1, 12'd8},
            pack_operand(2'd0, 13'd1800, 13'd8, 13'd0,
                         13'd0, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd0, 13'd0, 13'd0,
                         13'd0, 9'd0, 1'b0),
            pack_operand(2'd0, 13'd1904, 13'd8, 13'd0,
                         13'd0, 9'd1, 1'b0));

        record_check("copy_eeg_latency_bounded", "REQ-RRB-019", 64'd1,
                     last_descriptor_latency <= 14);
        $display("P5_COPY_EEG_LATENCY cycles=%0d",
                 last_descriptor_latency);
        record_check("copy_eeg_writes_exactly_once", "REQ-RRB-010", 64'd32,
                     feature_write_count - write_count_before);
        record_check("copy_eeg_bypasses_apx", "REQ-RRB-019", 64'd0,
                     apx_request_count - apx_count_before);
        for (index = 0; index < 32; index = index + 1)
            record_check("copy_eeg_contiguous_word", "REQ-RRB-006",
                         16'h6000 + index, feature_memory[1904 + index]);

        // OP-EMIT mode zero streams programmed FEATURE words through the
        // same unified retire owner.  Backpressure must hold data stable and
        // descriptor completion must wait for the final accepted word.
        for (index = 0; index < 16; index = index + 1)
            feature_memory[2200 + index] = 16'h7000 + index;
        write_count_before = feature_write_count;
        result_count_before = result_word_count;
        result_ready = 1'b0;
        fork
            begin
                send_descriptor(9'd50,
                    {4'h2, 2'd1, 4'd0, 6'd0, 12'd16, 12'd1,
                     12'd16, 12'd0},
                    pack_operand(2'd0, 13'd2200, 13'd16, 13'd1,
                                 13'd0, 9'd0, 1'b0),
                    64'd0, 64'd0);
            end
            begin
                wait (result_valid === 1'b1);
                @(negedge clk);
                stalled_result_data = result_data;
                stalled_result_last = result_last;
                repeat (3) @(negedge clk);
                record_check("emit_stall_holds_data", "REQ-RRB-010",
                             stalled_result_data, result_data);
                record_check("emit_stall_holds_last", "REQ-RRB-010",
                             stalled_result_last, result_last);
                result_ready = 1'b1;
            end
        join

        record_check("emit_descriptor_complete", "REQ-RRB-022", 64'd15,
                     complete_count);
        record_check("emit_does_not_write_feature", "REQ-RRB-010", 64'd0,
                     feature_write_count - write_count_before);
        record_check("emit_word_count", "REQ-RRB-012", 64'd16,
                     result_word_count - result_count_before);
        record_check("emit_exactly_one_last", "REQ-RRB-012", 64'd1,
                     result_last_count);
        for (index = 0; index < 16; index = index + 1)
            record_check("emit_result_word", "REQ-RRB-012",
                         16'h7000 + index,
                         result_words[result_count_before + index]);

        // Measure the unstalled current EEG 16-logit case against the cycle
        // ledger.  The second eight-word read must overlap first-packet drain.
        for (index = 0; index < 16; index = index + 1)
            feature_memory[2304 + index] = 16'h7100 + index;
        result_count_before = result_word_count;
        send_descriptor(9'd52,
            {4'h2, 2'd1, 4'd0, 6'd0, 12'd16, 12'd1,
             12'd16, 12'd0},
            pack_operand(2'd0, 13'd2304, 13'd16, 13'd1,
                         13'd0, 9'd0, 1'b0),
            64'd0, 64'd0);
        record_check("emit_eeg_latency_bounded", "REQ-RRB-019", 64'd1,
                     last_descriptor_latency <= 22);
        $display("P5_EMIT_EEG_LATENCY cycles=%0d",
                 last_descriptor_latency);
        record_check("emit_eeg_word_count", "REQ-RRB-012", 64'd16,
                     result_word_count - result_count_before);
        record_check("emit_eeg_first_word", "REQ-RRB-012", 16'h7100,
                     result_words[result_count_before]);
        record_check("emit_eeg_last_word", "REQ-RRB-012", 16'h710f,
                     result_words[result_count_before + 15]);

        // GROUP_DIAGONAL is a semantic mask, not permission to drop the
        // inactive APX zero-weight planes.  The frozen approximate multiplier
        // produces small non-zero terms for subnormal inputs multiplied by a
        // zero transport word, so every source plane must retain program order.
        feature_memory[2500] = 16'h23f6;
        feature_memory[2501] = 16'h1fc5;
        feature_memory[2508] = 16'h238e;
        feature_memory[2509] = 16'h1a4f;
        parameter_memory[0] = 16'h2956;
        parameter_memory[1] = 16'h2e4b;
        parameter_memory[2] = 16'h2a6d;
        parameter_memory[3] = 16'h2ede;
        parameter_memory[4] = 16'h3ed1;
        parameter_memory[5] = 16'h3b20;
        write_count_before = feature_write_count;
        send_descriptor(9'd54,
            {4'h1, 2'd3, 4'd3, 6'b010010, 12'd2, 12'd2,
             12'd2, 12'd3},
            pack_operand(2'd0, 13'd2500, 13'd0, 13'd1,
                         13'd8, 9'd0, 1'b0),
            pack_operand(2'd2, 13'd0, 13'd3, 13'd0,
                         13'd0, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd2600, 13'd8, 13'd1,
                         13'd0, 9'd0, 1'b0));
        record_check("group_diagonal_writes_once", "REQ-RRB-010", 64'd4,
                     feature_write_count - write_count_before);
        record_check("group_diagonal_row0_sample0", "REQ-RRB-006",
                     16'h1846, feature_memory[2600]);
        record_check("group_diagonal_row0_sample1", "REQ-RRB-006",
                     16'h1677, feature_memory[2601]);
        record_check("group_diagonal_row1_sample0", "REQ-RRB-006",
                     16'h272f, feature_memory[2608]);
        record_check("group_diagonal_row1_sample1", "REQ-RRB-006",
                     16'h1f35, feature_memory[2609]);
        record_check("group_diagonal_latency", "REQ-RRB-023",
                     64'd1, last_descriptor_latency <= 113);
        $display("P5_GROUP_DIAGONAL_LATENCY cycles=%0d",
                 last_descriptor_latency);

        // A long gather stream must not consume a stale bias while the
        // operand service is occupied by source tiles.  Bias readiness is a
        // start condition for scalar post-add, not an APX-latency accident.
        for (index = 0; index < 128; index = index + 1)
            feature_memory[3200 + index] = 16'h3c00;
        for (index = 0; index < 8; index = index + 1)
            parameter_memory[index] = 16'h3c00;
        parameter_memory[8] = 16'hc400;
        write_count_before = feature_write_count;
        send_descriptor(9'd54,
            {4'h1, 2'd3, 4'd3, 6'b001100, 12'd1, 12'd16,
             12'd1, 12'd8},
            pack_operand(2'd0, 13'd3200, 13'd0, 13'd8,
                         13'd0, 9'd1, 1'b0),
            pack_operand(2'd2, 13'd0, 13'd0, 13'd0,
                         13'd8, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd3500, 13'd0, 13'd1,
                         13'd0, 9'd0, 1'b0));
        record_check("gather_bias_stream_writes_once", "REQ-RRB-010",
                     64'd16,
                     feature_write_count - write_count_before);
        for (index = 0; index < 16; index = index + 1)
            record_check("gather_bias_stream_result", "REQ-RRB-006",
                         16'h4400, feature_memory[3500 + index]);
        // An aligned, unit-stride feature tile must use the trusted dual-port
        // memory slice path.  The bound deliberately fails if this descriptor
        // falls back to the four-lane affine gather FSM.
        record_check("gather_bias_stream_latency", "REQ-RRB-023",
                     64'd1, last_descriptor_latency <= 90);
        $display("P5_GATHER_BIAS_LATENCY cycles=%0d",
                 last_descriptor_latency);

        // A later accumulation plane must not drain the complete APX pipeline
        // after every eight results.  One pending result chunk is sufficient
        // because the vector add returns before the next eight-result chunk.
        for (index = 0; index < 16; index = index + 1) begin
            feature_memory[2800 + index] = 16'h3c00;
            feature_memory[2832 + index] = 16'h4000;
        end
        parameter_memory[0] = 16'h3c00;
        parameter_memory[1] = 16'h3c00;
        write_count_before = feature_write_count;
        send_descriptor(9'd54,
            {4'h1, 2'd3, 4'd3, 6'b000010, 12'd1, 12'd16,
             12'd2, 12'd1},
            pack_operand(2'd0, 13'd2800, 13'd0, 13'd1,
                         13'd32, 9'd1, 1'b0),
            pack_operand(2'd2, 13'd0, 13'd0, 13'd0,
                         13'd1, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd2904, 13'd0, 13'd1,
                         13'd0, 9'd0, 1'b0));
        record_check("two_plane_stream_writes_once", "REQ-RRB-010", 64'd16,
                     feature_write_count - write_count_before);
        for (index = 0; index < 16; index = index + 1)
            record_check("two_plane_stream_result", "REQ-RRB-006",
                         16'h4200, feature_memory[2904 + index]);
        record_check("two_plane_stream_latency", "REQ-RRB-023", 64'd1,
                     last_descriptor_latency <= 85);
        $display("P5_TWO_PLANE_LATENCY cycles=%0d",
                 last_descriptor_latency);

        // A tile-pair WINDOW_DOT must consume both output dot products from
        // the entry-generation source tile before either overlapping result
        // can corrupt the second output's read.
        for (index = 0; index < 4; index = index + 1) begin
            feature_memory[2400 + index] = 16'h3c00;
            feature_memory[2404 + index] = 16'h4000;
            parameter_memory[index] = 16'h3c00;
            parameter_memory[5 + index] = 16'h3800;
        end
        parameter_memory[4] = 16'h0000;
        parameter_memory[9] = 16'h0000;
        write_count_before = feature_write_count;
        send_descriptor(9'd54,
            {4'h1, 2'd3, 4'd3, 6'b001101, 12'd2, 12'd2,
             12'd1, 12'd4},
            pack_operand(2'd0, 13'd2400, 13'd0, 13'd4,
                         13'd0, 9'd1, 1'b0),
            pack_operand(2'd2, 13'd0, 13'd5, 13'd0,
                         13'd4, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd2400, 13'd2, 13'd1,
                         13'd0, 9'd0, 1'b0));
        record_check("tile_pair_writes_exactly_once", "REQ-RRB-010",
                     64'd4, feature_write_count - write_count_before);
        record_check("tile_pair_output0_sample0", "REQ-RRB-006",
                     16'h4400, feature_memory[2400]);
        record_check("tile_pair_output0_sample1", "REQ-RRB-006",
                     16'h4800, feature_memory[2401]);
        record_check("tile_pair_output1_sample0", "REQ-RRB-006",
                     16'h4000, feature_memory[2402]);
        record_check("tile_pair_output1_sample1", "REQ-RRB-006",
                     16'h4400, feature_memory[2403]);
        // EEG pooling reduces four scalar planes into sixteen outputs.  This
        // exposes per-eight-word add/scale bubbles without changing ordering.
        for (i1_index = 0; i1_index < 16; i1_index = i1_index + 1)
            for (i2_index = 0; i2_index < 4;
                 i2_index = i2_index + 1)
                feature_memory[3600 + i1_index*4 + i2_index] =
                    16'h3c00;
        write_count_before = feature_write_count;
        send_descriptor(9'd22,
            {4'h1, 2'd3, 4'd4, 6'b000001, 12'd1, 12'd16,
             12'd4, 12'd1},
            pack_operand(2'd0, 13'd3600, 13'd0, 13'd4,
                         13'd1, 9'd1, 1'b0),
            pack_operand(2'd3, 13'd0, 13'd0, 13'd0,
                         13'd0, 9'd0, 1'b0),
            pack_operand(2'd0, 13'd5000, 13'd0, 13'd1,
                         13'd0, 9'd0, 1'b0));
        record_check("pool_overlap_writes_once", "REQ-RRB-010", 64'd16,
                     feature_write_count - write_count_before);
        for (index = 0; index < 16; index = index + 1)
            record_check("pool_overlap_result", "REQ-RRB-006", 16'h3c00,
                         feature_memory[5000 + index]);
        // Registered APX and operand-command ownership remove the wide
        // control-to-data and response-to-address paths.  The accepted
        // architecture budget allows at most ten percent over the prior
        // 106-cycle bound.
        record_check("pool_overlap_latency_bounded", "REQ-RRB-023",
                     64'd1, last_descriptor_latency <= 116);
        $display("P5_POOL_OVERLAP_LATENCY cycles=%0d",
                 last_descriptor_latency);

        // Consecutive SAME_PAD output channels may intentionally share one
        // resident kernel and bias when the descriptor's weight stride is
        // zero.  The engine must overlap their windows without changing the
        // visible write order or relying on an EEG-specific profile branch.
        for (i0_index = 0; i0_index < 4; i0_index = i0_index + 1)
            for (i1_index = 0; i1_index < 32; i1_index = i1_index + 1)
                feature_memory[5200 + i0_index*128 + i1_index*4] =
                    16'h3c00;
        for (index = 48; index < 54; index = index + 1)
            parameter_memory[index] = 16'h0000;
        parameter_memory[50] = 16'h3c00;
        parameter_memory[53] = 16'h3c00;
        write_count_before = feature_write_count;
        send_descriptor(9'd58,
            {4'h1, 2'd3, 4'd3, 6'b001110, 12'd4, 12'd32,
             12'd1, 12'd5},
            pack_operand(2'd0, 13'd5200, 13'd128, 13'd4,
                         13'd0, 9'd4, 1'b0),
            pack_operand(2'd2, 13'd48, 13'd0, 13'd0,
                         13'd5, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd6000, 13'd64, 13'd1,
                         13'd0, 9'd0, 1'b0));
        record_check("shared_bias_kernel_writes_once", "REQ-RRB-010",
                     64'd128, feature_write_count - write_count_before);
        for (i0_index = 0; i0_index < 4; i0_index = i0_index + 1)
            for (i1_index = 0; i1_index < 32; i1_index = i1_index + 1)
                record_check("shared_bias_kernel_result", "REQ-RRB-006",
                             16'h4000,
                             feature_memory[6000 + i0_index*64 + i1_index]);
        record_check("shared_bias_kernel_latency", "REQ-RRB-023",
                     64'd1, last_descriptor_latency <= 194);
        $display("P5_SHARED_BIAS_KERNEL_LATENCY cycles=%0d",
                 last_descriptor_latency);

        // Pair mode writes back into the generation source region.  All
        // sixteen source tiles in a block must be consumed before buffered
        // bias results retire, while the bias arithmetic itself overlaps the
        // multiply-reduce stream.
        for (i1_index = 0; i1_index < 16; i1_index = i1_index + 1)
            for (index = 0; index < 4; index = index + 1)
                feature_memory[7000 + i1_index*4 + index] = 16'h3c00;
        for (index = 0; index < 4; index = index + 1) begin
            parameter_memory[index] = 16'h3c00;
            parameter_memory[5 + index] = 16'h3800;
        end
        parameter_memory[4] = 16'h0000;
        parameter_memory[9] = 16'h0000;
        write_count_before = feature_write_count;
        send_descriptor(9'd62,
            {4'h1, 2'd3, 4'd3, 6'b001101, 12'd2, 12'd16,
             12'd1, 12'd4},
            pack_operand(2'd0, 13'd7000, 13'd0, 13'd4,
                         13'd0, 9'd1, 1'b0),
            pack_operand(2'd2, 13'd0, 13'd5, 13'd0,
                         13'd4, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd7000, 13'd16, 13'd1,
                         13'd0, 9'd0, 1'b0));
        record_check("pair_block_buffered_writes_once", "REQ-RRB-010",
                     64'd32, feature_write_count - write_count_before);
        for (index = 0; index < 16; index = index + 1) begin
            record_check("pair_block_output0", "REQ-RRB-006", 16'h4400,
                         feature_memory[7000 + index]);
            record_check("pair_block_output1", "REQ-RRB-006", 16'h4000,
                         feature_memory[7016 + index]);
        end
        record_check("pair_block_buffered_latency", "REQ-RRB-023",
                     64'd1, last_descriptor_latency <= 138);
        $display("P5_PAIR_BLOCK_BUFFERED_LATENCY cycles=%0d",
                 last_descriptor_latency);

        for (i1_index = 0; i1_index < 32; i1_index = i1_index + 1)
            for (index = 0; index < 4; index = index + 1)
                feature_memory[7200 + i1_index*4 + index] = 16'h3c00;
        write_count_before = feature_write_count;
        send_descriptor(9'd66,
            {4'h1, 2'd3, 4'd3, 6'b001101, 12'd2, 12'd32,
             12'd1, 12'd4},
            pack_operand(2'd0, 13'd7200, 13'd0, 13'd4,
                         13'd0, 9'd1, 1'b0),
            pack_operand(2'd2, 13'd0, 13'd5, 13'd0,
                         13'd4, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd7200, 13'd32, 13'd1,
                         13'd0, 9'd0, 1'b0));
        record_check("pair_two_blocks_writes_once", "REQ-RRB-010",
                     64'd64, feature_write_count - write_count_before);
        for (index = 0; index < 32; index = index + 1) begin
            record_check("pair_two_blocks_output0", "REQ-RRB-006",
                         16'h4400, feature_memory[7200 + index]);
            record_check("pair_two_blocks_output1", "REQ-RRB-006",
                         16'h4000, feature_memory[7232 + index]);
        end
        record_check("pair_two_blocks_latency", "REQ-RRB-023",
                     64'd1, last_descriptor_latency <= 254);
        $display("P5_PAIR_TWO_BLOCKS_LATENCY cycles=%0d",
                 last_descriptor_latency);

        for (i1_index = 0; i1_index < 20; i1_index = i1_index + 1)
            for (index = 0; index < 4; index = index + 1)
                feature_memory[7400 + i1_index*4 + index] = 16'h3c00;
        write_count_before = feature_write_count;
        send_descriptor(9'd70,
            {4'h1, 2'd3, 4'd3, 6'b001101, 12'd2, 12'd20,
             12'd1, 12'd4},
            pack_operand(2'd0, 13'd7400, 13'd0, 13'd4,
                         13'd0, 9'd1, 1'b0),
            pack_operand(2'd2, 13'd0, 13'd5, 13'd0,
                         13'd4, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd7400, 13'd20, 13'd1,
                         13'd0, 9'd0, 1'b0));
        record_check("pair_partial_tail_writes_once", "REQ-RRB-010",
                     64'd40, feature_write_count - write_count_before);
        for (index = 0; index < 20; index = index + 1) begin
            record_check("pair_partial_tail_output0", "REQ-RRB-006",
                         16'h4400, feature_memory[7400 + index]);
            record_check("pair_partial_tail_output1", "REQ-RRB-006",
                         16'h4000, feature_memory[7420 + index]);
        end
        record_check("pair_partial_tail_latency", "REQ-RRB-023",
                     64'd1, last_descriptor_latency <= 209);
        $display("P5_PAIR_PARTIAL_TAIL_LATENCY cycles=%0d",
                 last_descriptor_latency);

        // VECTOR_ADD reuses the shared APX add-vector path.  Both operands
        // are fetched through the operand service, so this test proves the
        // descriptor decode, FEATURE-space second operand, optional negate,
        // APX result, and unified retirement path as one black-box flow.
        for (index = 0; index < 8; index = index + 1) begin
            feature_memory[7800 + index] = 16'h3c00;
            feature_memory[7816 + index] = 16'h4000;
            feature_memory[7848 + index] = 16'h3c00;
            feature_memory[7864 + index] = 16'h3800;
        end
        write_count_before = feature_write_count;
        send_descriptor(9'd74,
            {4'h1, 2'd3, 4'd13, 6'd0, 12'd1, 12'd1,
             12'd1, 12'd8},
            pack_operand(2'd0, 13'd7800, 13'd0, 13'd0,
                         13'd0, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd7816, 13'd0, 13'd0,
                         13'd0, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd7832, 13'd0, 13'd0,
                         13'd0, 9'd1, 1'b0));
        record_check("vector_add_writes_once", "REQ-RRB-010",
                     64'd8, feature_write_count - write_count_before);
        for (index = 0; index < 8; index = index + 1)
            record_check("vector_add_feature_result", "REQ-RRB-006",
                         16'h4200, feature_memory[7832 + index]);

        write_count_before = feature_write_count;
        send_descriptor(9'd78,
            {4'h1, 2'd3, 4'd13, 6'd0, 12'd1, 12'd1,
             12'd1, 12'd8},
            pack_operand(2'd0, 13'd7848, 13'd0, 13'd0,
                         13'd0, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd7864, 13'd0, 13'd0,
                         13'd0, 9'd1, 1'b1),
            pack_operand(2'd0, 13'd7880, 13'd0, 13'd0,
                         13'd0, 9'd1, 1'b0));
        record_check("vector_subtract_writes_once", "REQ-RRB-010",
                     64'd8, feature_write_count - write_count_before);
        for (index = 0; index < 8; index = index + 1)
            record_check("vector_subtract_feature_result", "REQ-RRB-006",
                         16'h3800, feature_memory[7880 + index]);

        // The software-lowered TRI_SOLVE path issues one 8-lane VECTOR_ADD
        // descriptor across 32 outer tiles and broadcasts the row scalar.
        // Exercise that exact shape so the generic outer-loop address update
        // and resident-B reuse are proven before the specialized controllers
        // are removed.
        for (index = 0; index < 256; index = index + 1) begin
            feature_memory[2700 + index] = 16'h3c00;
            feature_memory[3000 + index] = 16'h0000;
        end
        feature_memory[2990] = 16'h4000;
        write_count_before = feature_write_count;
        send_descriptor(9'd79,
            {4'h1, 2'd3, 4'd13, 6'd0, 12'd32, 12'd1,
             12'd1, 12'd8},
            pack_operand(2'd0, 13'd2700, 13'd8, 13'd0,
                         13'd0, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd2990, 13'd0, 13'd0,
                         13'd0, 9'd0, 1'b0),
            pack_operand(2'd0, 13'd3000, 13'd8, 13'd0,
                         13'd0, 9'd1, 1'b0));
        record_check("vector_add_outer32_writes", "REQ-RRB-010",
                     64'd256, feature_write_count - write_count_before);
        for (index = 0; index < 256; index = index + 1)
            record_check("vector_add_outer32_result", "REQ-RRB-006",
                         16'h4200, feature_memory[3000 + index]);

        // The compiler tiles the logical 16-lane whitening multiply into two
        // independent 8-lane descriptors.  PL sees one bounded arithmetic
        // tile and never owns a lower/upper phase selector.
        for (index = 0; index < 256; index = index + 1) begin
            feature_memory[2000 + index] = 16'h3c00;
            feature_memory[2400 + index] = 16'h0000;
        end
        feature_memory[2300] = 16'h4000;
        write_count_before = feature_write_count;
        send_descriptor(9'd80,
            {4'h1, 2'd3, 4'd2, 6'b000001, 12'd16, 12'd1,
             12'd1, 12'd8},
            pack_operand(2'd0, 13'd2000, 13'd16, 13'd0,
                         13'd0, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd2300, 13'd0, 13'd0,
                         13'd0, 9'd0, 1'b0),
            pack_operand(2'd0, 13'd2400, 13'd16, 13'd0,
                         13'd0, 9'd1, 1'b0));
        send_descriptor(9'd84,
            {4'h1, 2'd3, 4'd2, 6'b000001, 12'd16, 12'd1,
             12'd1, 12'd8},
            pack_operand(2'd0, 13'd2008, 13'd16, 13'd0,
                         13'd0, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd2300, 13'd0, 13'd0,
                         13'd0, 9'd0, 1'b0),
            pack_operand(2'd0, 13'd2408, 13'd16, 13'd0,
                         13'd0, 9'd1, 1'b0));
        record_check("ewise_outer16_writes", "REQ-RRB-010",
                     64'd256, feature_write_count - write_count_before);
        for (index = 0; index < 256; index = index + 1)
            record_check("ewise_outer16_result", "REQ-RRB-006",
                         16'h4000, feature_memory[2400 + index]);
        generic_primitives_complete = 1'b1;

        // WINDOW_DOT flag bit 5 changes only the encoded 9'h100 lane-stride
        // token into an internal +256 stride.  All six noncontiguous FEATURE
        // words must participate in the dot product; reading a signed -256
        // or a contiguous layout cannot produce the expected result.
        for (index = 0; index < 6; index = index + 1) begin
            feature_memory[300 + index*256] = 16'h3c00;
            parameter_memory[48 + index] = 16'h3c00;
        end
        write_count_before = feature_write_count;
        send_descriptor(9'd82,
            {4'h1, 2'd3, 4'd3, 6'b100000, 12'd1, 12'd1,
             12'd1, 12'd6},
            pack_operand(2'd0, 13'd300, 13'd0, 13'd0,
                         13'd0, 9'h100, 1'b0),
            pack_operand(2'd2, 13'd48, 13'd0, 13'd0,
                         13'd0, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd7900, 13'd0, 13'd0,
                         13'd0, 9'd1, 1'b0));
        record_check("window_dot_stride256_writes_once", "REQ-RRB-010",
                     64'd1, feature_write_count - write_count_before);
        record_check("window_dot_stride256_result", "REQ-RRB-006",
                     16'h4600, feature_memory[7900]);

        // REC2 is a descriptor-driven six-channel recurrence, not a named
        // SSVEP branch.  With one sample, zero history, unit coefficients,
        // unit cosine, and zero sine, every bin must retire source+j0.  The
        // test covers the 16-phase shared-APX schedule and 24-word channel
        // stride through only module-boundary memory transactions.
        for (index = 0; index < 12; index = index + 1) begin
            parameter_memory[index] = 16'h3c00;
            parameter_memory[12 + index] = 16'h3c00;
            parameter_memory[24 + index] = 16'h0000;
        end
        for (i0_index = 0; i0_index < 6; i0_index = i0_index + 1)
            feature_memory[500 + i0_index*16] = 16'h4000;
        write_count_before = feature_write_count;
        send_descriptor(9'd86,
            {4'h1, 2'd3, 4'd9, 6'd0, 12'd6, 12'd1,
             12'd1, 12'd12},
            pack_operand(2'd0, 13'd500, 13'd16, 13'd1,
                         13'd0, 9'd0, 1'b0),
            pack_operand(2'd2, 13'd0, 13'd0, 13'd0,
                         13'd0, 9'd1, 1'b0),
            pack_operand(2'd0, 13'd1000, 13'd24, 13'd0,
                         13'd0, 9'd2, 1'b0));
        record_check("rec2_one_sample_writes_once", "REQ-RRB-010",
                     64'd144, feature_write_count - write_count_before);
        for (i0_index = 0; i0_index < 6; i0_index = i0_index + 1)
            for (index = 0; index < 12; index = index + 1) begin
                record_check("rec2_one_sample_real", "REQ-RRB-006",
                             16'h4000,
                             feature_memory[1000 + i0_index*24 +
                                            index*2]);
                record_check("rec2_one_sample_imag", "REQ-RRB-006",
                             16'h8000,
                             feature_memory[1001 + i0_index*24 +
                                            index*2]);
            end

        $display("HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P5_DESCRIPTOR_ENGINE|passes=%0d|failures=%0d|result=%0s", pass_count, fail_count, (fail_count == 0) ? "PASS" : "FAIL");
        $display("HDLFLOW|TASK_END|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P5_DESCRIPTOR_ENGINE|result=%0s", (fail_count == 0) ? "PASS" : "FAIL");
        test_complete = 1'b1;
        test_passed = (fail_count == 0);
        if (fail_count != 0)
            $fatal(1, "P5 descriptor execution engine test failed");
        $finish;
    end

    initial begin
        #2000000;
        $display("P5_TIMEOUT_DEBUG engine_state=%0d service_state=%0d issue=%0d receive=%0d source_pending=%0d request_valid=%0d request_ready=%0d response_valid=%0d response_ready=%0d fast_waiting=%0d chunk_index=%0d lanes=%0d",
                 u_dut.state_q, u_dut.u_operand_service.state_q,
                 u_dut.gather_issue_count_q, u_dut.gather_result_count_q,
                 u_dut.gather_source_pending_q, u_dut.service_request_valid,
                 u_dut.service_request_ready, u_dut.service_response_valid,
                 u_dut.service_response_ready,
                 u_dut.u_operand_service.fast_waiting_q,
                 u_dut.u_operand_service.chunk_base_index_q,
                 u_dut.u_operand_service.service_lanes_q);
        $display("HDLFLOW|TASK_END|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P5_DESCRIPTOR_ENGINE|result=FAIL");
        test_complete = 1'b1;
        test_passed = 1'b0;
        $fatal(1, "P5 descriptor execution engine timeout");
    end
endmodule
// ---- END descriptor_execution_engine_tb.v ----

// ---- BEGIN shared_bci_accel_core_tb.v ----
// -----------------------------------------------------------------------------
// Module: shared_bci_accel_core_tb
// Purpose: End-to-end P5 proof that one software-loaded program, parameter
//          image, and frame execute through the shared production hierarchy.
// Requirements: REQ-RRB-003, REQ-RRB-005, REQ-RRB-006, REQ-RRB-007,
//               REQ-RRB-008, REQ-RRB-019, REQ-RRB-020, REQ-RRB-022
// -----------------------------------------------------------------------------

`timescale 1ns/1ps

module shared_bci_accel_core_tb;
    reg clk;
    reg reset_n;
    reg start_valid;
    wire start_ready;
    wire busy;
    wire done;

    reg program_load_valid;
    wire program_load_ready;
    reg [8:0] program_load_address;
    reg [63:0] program_load_data;
    reg parameter_load_valid;
    wire parameter_load_ready;
    reg [8:0] parameter_load_address;
    reg [63:0] parameter_load_data;

    reg frame_begin;
    reg [1:0] frame_page;
    reg [63:0] frame_config;
    reg frame_valid;
    wire frame_ready;
    reg [63:0] frame_data;
    wire frame_complete;
    wire [8:0] frame_beat_count;

    wire result_valid;
    reg result_ready;
    wire [15:0] result_data;
    wire result_last;

    reg [63:0] program_rows [0:8];
    reg [63:0] parameter_rows [0:8];
    reg [63:0] frame_rows [0:511];
    reg [15:0] expected_words [0:1];
    reg [15:0] observed_words [0:1];
    reg [15:0] held_result;
    integer index;
    integer result_count;
    integer last_count;
    integer pass_count;
    integer fail_count;
    integer timeout_cycles;
    reg test_complete;
    reg test_passed;

    task record_check;
        input [8*48-1:0] test_id;
        input [8*16-1:0] requirement_id;
        input [63:0] expected;
        input [63:0] actual;
        begin
            if (actual === expected) begin
                pass_count = pass_count + 1;
                $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=%0s|txn_id=p5_core_%0d|requirement_id=%0s|operation_id=P5_SHARED_CORE|sent=1|expected=%h|actual=%h|latency_cycles=1|observed_interface=module_boundary|evidence_type=blackbox|check_role=primary|result=PASS", test_id, pass_count + fail_count, requirement_id, expected, actual);
            end
            else begin
                fail_count = fail_count + 1;
                $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=%0s|txn_id=p5_core_%0d|requirement_id=%0s|operation_id=P5_SHARED_CORE|sent=1|expected=%h|actual=%h|latency_cycles=1|observed_interface=module_boundary|evidence_type=blackbox|check_role=primary|result=FAIL", test_id, pass_count + fail_count, requirement_id, expected, actual);
            end
        end
    endtask

    task load_program_row;
        input [8:0] address;
        input [63:0] data;
        begin
            @(negedge clk);
            program_load_address = address;
            program_load_data = data;
            program_load_valid = 1'b1;
            while (program_load_ready !== 1'b1)
                @(negedge clk);
            @(negedge clk);
            program_load_valid = 1'b0;
        end
    endtask

    task load_parameter_row;
        input [8:0] address;
        input [63:0] data;
        begin
            @(negedge clk);
            parameter_load_address = address;
            parameter_load_data = data;
            parameter_load_valid = 1'b1;
            while (parameter_load_ready !== 1'b1)
                @(negedge clk);
            @(negedge clk);
            parameter_load_valid = 1'b0;
        end
    endtask

    shared_bci_accel_core u_dut (
        .clk(clk),
        .reset_n(reset_n),
        .start_valid(start_valid),
        .start_ready(start_ready),
        .busy(busy),
        .done(done),
        .program_load_valid(program_load_valid),
        .program_load_ready(program_load_ready),
        .program_load_address(program_load_address),
        .program_load_data(program_load_data),
        .parameter_load_valid(parameter_load_valid),
        .parameter_load_ready(parameter_load_ready),
        .parameter_load_address(parameter_load_address),
        .parameter_load_data(parameter_load_data),
        .frame_begin(frame_begin),
        .frame_page(frame_page),
        .frame_config(frame_config),
        .frame_valid(frame_valid),
        .frame_ready(frame_ready),
        .frame_data(frame_data),
        .frame_complete(frame_complete),
        .frame_beat_count(frame_beat_count),
        .result_valid(result_valid),
        .result_ready(result_ready),
        .result_data(result_data),
        .result_last(result_last)
    );

    always #5 clk = ~clk;

    always @(posedge clk) begin
        if (!reset_n) begin
            result_count <= 0;
            last_count <= 0;
        end
        else if (result_valid && result_ready) begin
            if (result_count < 2)
                observed_words[result_count] <= result_data;
            result_count <= result_count + 1;
            if (result_last)
                last_count <= last_count + 1;
        end
    end

    initial begin
        clk = 1'b0;
        reset_n = 1'b0;
        start_valid = 1'b0;
        program_load_valid = 1'b0;
        program_load_address = 9'd0;
        program_load_data = 64'd0;
        parameter_load_valid = 1'b0;
        parameter_load_address = 9'd0;
        parameter_load_data = 64'd0;
        frame_begin = 1'b0;
        frame_page = 2'd3;
        frame_config = 64'd0;
        frame_valid = 1'b0;
        frame_data = 64'd0;
        result_ready = 1'b1;
        result_count = 0;
        last_count = 0;
        pass_count = 0;
        fail_count = 0;
        timeout_cycles = 0;
        test_complete = 1'b0;
        test_passed = 1'b0;
        observed_words[0] = 16'd0;
        observed_words[1] = 16'd0;

        $display("HDLFLOW|TASK_BEGIN|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P5_SHARED_CORE|requirement_id=REQ-RRB-006|operation_id=P5_SHARED_CORE");

        $readmemh("input/sources/verification_data/loop1/vectors/r5/synthetic_program.hex", program_rows);
        $readmemh("input/sources/verification_data/loop1/vectors/r5/synthetic_parameter_rows.hex", parameter_rows);
        $readmemh("input/sources/verification_data/loop1/vectors/r5/synthetic_frame_rows.hex", frame_rows);
        $readmemh("input/sources/verification_data/loop1/vectors/r5/synthetic_expected.hex", expected_words);

        repeat (4) @(posedge clk);
        reset_n = 1'b1;
        repeat (2) @(posedge clk);

        record_check("idle_accepts_loads", "REQ-RRB-003",
                     64'd1, {63'd0, program_load_ready});
        for (index = 0; index < 9; index = index + 1)
            load_program_row(index[8:0], program_rows[index]);
        for (index = 0; index < 9; index = index + 1)
            load_parameter_row(index[8:0], parameter_rows[index]);

        @(negedge clk);
        frame_begin = 1'b1;
        @(negedge clk);
        frame_begin = 1'b0;
        for (index = 0; index < 512; index = index + 1) begin
            frame_data = frame_rows[index];
            frame_valid = 1'b1;
            while (frame_ready !== 1'b1)
                @(negedge clk);
            @(negedge clk);
        end
        frame_valid = 1'b0;
        record_check("frame_512_beats_complete", "REQ-RRB-008",
                     64'd1, {63'd0, frame_complete});

        @(negedge clk);
        start_valid = 1'b1;
        while (start_ready !== 1'b1)
            @(negedge clk);
        @(negedge clk);
        start_valid = 1'b0;

        wait (busy === 1'b1);
        @(negedge clk);
        program_load_valid = 1'b1;
        program_load_address = 9'd0;
        program_load_data = 64'hdead_beef_dead_beef;
        record_check("busy_blocks_program_write", "REQ-RRB-003",
                     64'd0, {63'd0, program_load_ready});
        @(negedge clk);
        program_load_valid = 1'b0;

        wait (result_valid === 1'b1);
        result_ready = 1'b0;
        held_result = result_data;
        repeat (3) begin
            @(negedge clk);
            record_check("result_stable_under_stall", "REQ-RRB-022",
                         {48'd0, held_result}, {48'd0, result_data});
        end
        result_ready = 1'b1;

        while ((done !== 1'b1) && (timeout_cycles < 2000)) begin
            @(posedge clk);
            timeout_cycles = timeout_cycles + 1;
        end
        record_check("session_done", "REQ-RRB-005",
                     64'd1, {63'd0, done});
        repeat (2) @(posedge clk);
        record_check("result_word_count", "REQ-RRB-022",
                     64'd2, result_count);
        record_check("result_last_once", "REQ-RRB-022",
                     64'd1, last_count);
        record_check("synthetic_result_0", "REQ-RRB-006",
                     {48'd0, expected_words[0]},
                     {48'd0, observed_words[0]});
        record_check("synthetic_result_1", "REQ-RRB-006",
                     {48'd0, expected_words[1]},
                     {48'd0, observed_words[1]});

        test_complete = 1'b1;
        test_passed = (fail_count == 0);
        if (test_passed) begin
            $display("HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=p5_shared_core|txn_id=p5_core_summary|requirement_id=REQ-RRB-006|operation_id=P5_SHARED_CORE|sent=%0d|expected=%0d|actual=%0d|latency_cycles=%0d|observed_interface=module_boundary|evidence_type=blackbox|check_role=primary|result=PASS", pass_count, pass_count, pass_count, timeout_cycles);
            $display("HDLFLOW|TASK_END|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P5_SHARED_CORE|requirement_id=REQ-RRB-006|operation_id=P5_SHARED_CORE|result=PASS");
            $display("TASK_END PASS");
        end
        else begin
            $display("HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=p5_shared_core|txn_id=p5_core_summary|requirement_id=REQ-RRB-006|operation_id=P5_SHARED_CORE|sent=%0d|expected=0|actual=%0d|latency_cycles=%0d|observed_interface=module_boundary|evidence_type=blackbox|check_role=primary|result=FAIL", pass_count + fail_count, fail_count, timeout_cycles);
            $display("HDLFLOW|TASK_END|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P5_SHARED_CORE|requirement_id=REQ-RRB-006|operation_id=P5_SHARED_CORE|result=FAIL");
            $display("TASK_END FAIL");
        end
        $stop;
    end
endmodule
// ---- END shared_bci_accel_core_tb.v ----

// ---- BEGIN shared_bci_accel_top_tb.v ----
//==============================================================================
// Module      : shared_bci_accel_top_tb
// File        : shared_bci_accel_top_tb.v
// Description : AXI4-Lite full-top directed regression using the synthetic
//               third-profile image and independent expected result words.
// Requirements: REQ-RRB-003, REQ-RRB-004, REQ-RRB-021, REQ-RRB-024
//==============================================================================

`timescale 1ns/1ps

module shared_bci_accel_top_tb;
    reg         clk;
    reg         reset_n;
    reg  [15:0] s_axi_awaddr;
    reg         s_axi_awvalid;
    wire        s_axi_awready;
    reg  [63:0] s_axi_wdata;
    reg  [7:0]  s_axi_wstrb;
    reg         s_axi_wvalid;
    wire        s_axi_wready;
    wire [1:0]  s_axi_bresp;
    wire        s_axi_bvalid;
    reg         s_axi_bready;
    reg  [15:0] s_axi_araddr;
    reg         s_axi_arvalid;
    wire        s_axi_arready;
    wire [63:0] s_axi_rdata;
    wire [1:0]  s_axi_rresp;
    wire        s_axi_rvalid;
    reg         s_axi_rready;

    reg [63:0] program_rows [0:8];
    reg [63:0] parameter_rows [0:8];
    reg [63:0] frame_rows [0:511];
    reg [15:0] expected_words [0:1];
    reg [63:0] read_value;
    reg [63:0] held_value;
    integer index;
    integer pass_count;
    integer fail_count;
    integer timeout_cycles;
    reg test_complete;
    reg test_passed;

    shared_bci_accel_top u_dut (
        .clk(clk),
        .reset_n(reset_n),
        .s_axi_awaddr(s_axi_awaddr),
        .s_axi_awvalid(s_axi_awvalid),
        .s_axi_awready(s_axi_awready),
        .s_axi_wdata(s_axi_wdata),
        .s_axi_wstrb(s_axi_wstrb),
        .s_axi_wvalid(s_axi_wvalid),
        .s_axi_wready(s_axi_wready),
        .s_axi_bresp(s_axi_bresp),
        .s_axi_bvalid(s_axi_bvalid),
        .s_axi_bready(s_axi_bready),
        .s_axi_araddr(s_axi_araddr),
        .s_axi_arvalid(s_axi_arvalid),
        .s_axi_arready(s_axi_arready),
        .s_axi_rdata(s_axi_rdata),
        .s_axi_rresp(s_axi_rresp),
        .s_axi_rvalid(s_axi_rvalid),
        .s_axi_rready(s_axi_rready)
    );

    always #5 clk = ~clk;

    task record_check;
        input [8*48-1:0] test_id;
        input [8*16-1:0] requirement_id;
        input [63:0] expected;
        input [63:0] actual;
        begin
            if (actual === expected) begin
                pass_count = pass_count + 1;
                $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=%0s|txn_id=axi_top_%0d|requirement_id=%0s|operation_id=AXI_FULL_TOP|sent=1|expected=%h|actual=%h|latency_cycles=1|observed_interface=axi_lite|evidence_type=blackbox|check_role=primary|result=PASS", test_id, pass_count + fail_count, requirement_id, expected, actual);
            end
            else begin
                fail_count = fail_count + 1;
                $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=%0s|txn_id=axi_top_%0d|requirement_id=%0s|operation_id=AXI_FULL_TOP|sent=1|expected=%h|actual=%h|latency_cycles=1|observed_interface=axi_lite|evidence_type=blackbox|check_role=primary|result=FAIL", test_id, pass_count + fail_count, requirement_id, expected, actual);
            end
        end
    endtask

    task axi_write_issue;
        input [15:0] address;
        input [63:0] data;
        input integer address_delay;
        input integer data_delay;
        integer local_cycle;
        integer address_done;
        integer data_done;
        begin
            address_done = 0;
            data_done = 0;
            local_cycle = 0;
            @(negedge clk);
            s_axi_awaddr = address;
            s_axi_wdata = data;
            s_axi_wstrb = 8'hff;
            s_axi_bready = 1'b0;
            while ((address_done == 0) || (data_done == 0)) begin
                if ((address_done == 0) &&
                    (local_cycle >= address_delay))
                    s_axi_awvalid = 1'b1;
                if ((data_done == 0) &&
                    (local_cycle >= data_delay))
                    s_axi_wvalid = 1'b1;
                @(posedge clk);
                if (s_axi_awvalid && s_axi_awready)
                    address_done = 1;
                if (s_axi_wvalid && s_axi_wready)
                    data_done = 1;
                @(negedge clk);
                if (address_done != 0)
                    s_axi_awvalid = 1'b0;
                if (data_done != 0)
                    s_axi_wvalid = 1'b0;
                local_cycle = local_cycle + 1;
            end
        end
    endtask

    task axi_write_response;
        begin
            while (s_axi_bvalid !== 1'b1)
                @(negedge clk);
            record_check("axi_write_response", "REQ-RRB-021",
                         64'd0, {62'd0, s_axi_bresp});
            s_axi_bready = 1'b1;
            @(posedge clk);
            @(negedge clk);
            s_axi_bready = 1'b0;
        end
    endtask

    task axi_write;
        input [15:0] address;
        input [63:0] data;
        input integer address_delay;
        input integer data_delay;
        begin
            axi_write_issue(address, data, address_delay, data_delay);
            axi_write_response;
        end
    endtask

    task axi_read;
        input [15:0] address;
        input integer response_stall_cycles;
        output [63:0] data;
        integer stall_index;
        integer read_timeout;
        begin
            @(negedge clk);
            s_axi_araddr = address;
            s_axi_arvalid = 1'b1;
            s_axi_rready = 1'b0;
            read_timeout = 0;
            while ((s_axi_arready !== 1'b1) &&
                   (read_timeout < 5000)) begin
                @(negedge clk);
                read_timeout = read_timeout + 1;
            end
            if (s_axi_arready !== 1'b1) begin
                record_check("axi_read_address_timeout", "REQ-RRB-021",
                             64'd1, 64'd0);
                $display("AXI_READ_TIMEOUT address=%h busy=%b done=%b result_valid=%b retire_state=%0d engine_state=%0d",
                         address,
                         u_dut.u_shared_bci_accel_core.busy,
                         u_dut.u_shared_bci_accel_core.done,
                         u_dut.u_shared_bci_accel_core.result_valid,
                         u_dut.u_shared_bci_accel_core.u_execution_engine.u_unified_retire.state_q,
                         u_dut.u_shared_bci_accel_core.u_execution_engine.state_q);
                data = 64'hffff_ffff_ffff_ffff;
                s_axi_arvalid = 1'b0;
                disable axi_read;
            end
            @(posedge clk);
            @(negedge clk);
            s_axi_arvalid = 1'b0;
            while (s_axi_rvalid !== 1'b1)
                @(negedge clk);
            held_value = s_axi_rdata;
            for (stall_index = 0;
                 stall_index < response_stall_cycles;
                 stall_index = stall_index + 1) begin
                @(negedge clk);
                record_check("axi_read_stable", "REQ-RRB-021",
                             held_value, s_axi_rdata);
            end
            data = s_axi_rdata;
            record_check("axi_read_response", "REQ-RRB-021",
                         64'd0, {62'd0, s_axi_rresp});
            s_axi_rready = 1'b1;
            @(posedge clk);
            @(negedge clk);
            s_axi_rready = 1'b0;
        end
    endtask

    initial begin
        clk = 1'b0;
        reset_n = 1'b0;
        s_axi_awaddr = 16'd0;
        s_axi_awvalid = 1'b0;
        s_axi_wdata = 64'd0;
        s_axi_wstrb = 8'd0;
        s_axi_wvalid = 1'b0;
        s_axi_bready = 1'b0;
        s_axi_araddr = 16'd0;
        s_axi_arvalid = 1'b0;
        s_axi_rready = 1'b0;
        pass_count = 0;
        fail_count = 0;
        timeout_cycles = 0;
        test_complete = 1'b0;
        test_passed = 1'b0;
        read_value = 64'd0;
        held_value = 64'd0;

        $display("HDLFLOW|TASK_BEGIN|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=AXI_FULL_TOP|requirement_id=REQ-RRB-021|operation_id=AXI_FULL_TOP");

        $readmemh("input/sources/verification_data/loop1/vectors/r5/synthetic_program.hex",
                  program_rows);
        $readmemh("input/sources/verification_data/loop1/vectors/r5/synthetic_parameter_rows.hex",
                  parameter_rows);
        $readmemh("input/sources/verification_data/loop1/vectors/r5/synthetic_frame_rows.hex",
                  frame_rows);
        $readmemh("input/sources/verification_data/loop1/vectors/r5/synthetic_expected.hex",
                  expected_words);

        repeat (4) @(posedge clk);
        reset_n = 1'b1;
        repeat (2) @(posedge clk);

        axi_write(16'h0010, 64'd9, 0, 2);
        axi_write(16'h0018, 64'd2, 2, 0);
        axi_read(16'h0010, 0, read_value);
        record_check("program_length_readback", "REQ-RRB-021",
                     64'd9, read_value);
        axi_read(16'h0018, 0, read_value);
        record_check("result_length_readback", "REQ-RRB-021",
                     64'd2, read_value);

        axi_write(16'h0020, 64'd3, 1, 0);
        axi_write(16'h0028, 64'd0, 0, 1);
        axi_read(16'h0020, 0, read_value);
        record_check("frame_page_readback", "REQ-RRB-024",
                     64'd3, read_value);

        for (index = 0; index < 9; index = index + 1)
            axi_write(16'h1000 + index*8, program_rows[index], 0, 0);
        for (index = 0; index < 9; index = index + 1)
            axi_write(16'h2000 + index*8, parameter_rows[index], 0, 0);
        for (index = 0; index < 512; index = index + 1)
            axi_write(16'h3000 + index*8, frame_rows[index], 0, 0);

        axi_read(16'h0008, 0, read_value);
        record_check("axi_frame_complete", "REQ-RRB-021",
                     64'd1, {63'd0, read_value[2]});

        axi_write(16'h0000, 64'd1, 0, 0);
        repeat (3) @(negedge clk);
        axi_read(16'h0008, 0, read_value);
        record_check("axi_session_busy", "REQ-RRB-003",
                     64'd1, {63'd0, read_value[0]});

        axi_write(16'h0000, 64'd1, 0, 0);
        record_check("start_while_busy_rejected", "REQ-RRB-003",
                     64'd1,
                     {63'd0, u_dut.u_shared_bci_accel_core.busy});

        axi_write_issue(16'h0020, 64'd0, 1, 0);
        repeat (3) @(negedge clk);
        record_check("busy_frame_config_backpressured", "REQ-RRB-024",
                     64'd0, {63'd0, s_axi_bvalid});
        axi_read(16'h0020, 0, read_value);
        record_check("busy_frame_page_stable", "REQ-RRB-024",
                     64'd3, read_value);

        record_check("busy_load_ready_blocked", "REQ-RRB-021",
                     64'd0,
                     {63'd0,
                      u_dut.u_shared_bci_accel_core.program_load_ready});

        axi_read(16'h4000, 3, read_value);
        record_check("synthetic_result_0", "REQ-RRB-004",
                     {48'd0, expected_words[0]},
                     {48'd0, read_value[15:0]});
        record_check("result_0_not_last", "REQ-RRB-021",
                     64'd0, {63'd0, read_value[16]});
        axi_read(16'h4008, 0, read_value);
        record_check("synthetic_result_1", "REQ-RRB-004",
                     {48'd0, expected_words[1]},
                     {48'd0, read_value[15:0]});
        record_check("result_1_last", "REQ-RRB-021",
                     64'd1, {63'd0, read_value[16]});

        axi_write_response;
        axi_read(16'h0020, 0, read_value);
        record_check("deferred_frame_page_applied", "REQ-RRB-024",
                     64'd0, read_value);

        read_value = 64'd0;
        timeout_cycles = 0;
        while ((read_value[1] !== 1'b1) &&
               (timeout_cycles < 100)) begin
            axi_read(16'h0008, 0, read_value);
            timeout_cycles = timeout_cycles + 1;
        end
        record_check("done_sticky_readback", "REQ-RRB-021",
                     64'd1, {63'd0, read_value[1]});
        record_check("idle_after_completion", "REQ-RRB-003",
                     64'd0, {63'd0, read_value[0]});

        repeat (4) @(negedge clk);
        axi_read(16'h0008, 0, read_value);
        record_check("no_queued_restart_after_busy_start", "REQ-RRB-003",
                     64'd0, {63'd0, read_value[0]});

        for (index = 0; index < 9; index = index + 1)
            axi_write(16'h1000 + index*8, program_rows[index], 0, 0);
        for (index = 0; index < 9; index = index + 1)
            axi_write(16'h2000 + index*8, parameter_rows[index], 0, 0);
        for (index = 0; index < 512; index = index + 1)
            axi_write(16'h3000 + index*8, frame_rows[index], 0, 0);

        axi_read(16'h0008, 0, read_value);
        record_check("second_frame_complete", "REQ-RRB-021",
                     64'd1, {63'd0, read_value[2]});

        axi_write(16'h0000, 64'd1, 0, 0);
        repeat (3) @(negedge clk);
        axi_read(16'h0008, 0, read_value);
        record_check("second_session_busy", "REQ-RRB-003",
                     64'd1, {63'd0, read_value[0]});
        record_check("done_cleared_on_second_start", "REQ-RRB-021",
                     64'd0, {63'd0, read_value[1]});

        axi_read(16'h4000, 1, read_value);
        record_check("second_frame_result_0", "REQ-RRB-004",
                     {48'd0, expected_words[0]},
                     {48'd0, read_value[15:0]});
        record_check("second_result_0_not_last", "REQ-RRB-021",
                     64'd0, {63'd0, read_value[16]});
        axi_read(16'h4008, 0, read_value);
        record_check("second_frame_result_1", "REQ-RRB-004",
                     {48'd0, expected_words[1]},
                     {48'd0, read_value[15:0]});
        record_check("second_result_1_last", "REQ-RRB-021",
                     64'd1, {63'd0, read_value[16]});

        read_value = 64'd0;
        timeout_cycles = 0;
        while ((read_value[1] !== 1'b1) &&
               (timeout_cycles < 100)) begin
            axi_read(16'h0008, 0, read_value);
            timeout_cycles = timeout_cycles + 1;
        end
        record_check("second_done_sticky_readback", "REQ-RRB-021",
                     64'd1, {63'd0, read_value[1]});
        record_check("second_idle_after_completion", "REQ-RRB-003",
                     64'd0, {63'd0, read_value[0]});

        test_complete = 1'b1;
        test_passed = fail_count == 0;
        if (test_passed) begin
            $display("HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=axi_full_top|txn_id=axi_top_summary|requirement_id=REQ-RRB-021|operation_id=AXI_FULL_TOP|sent=%0d|expected=%0d|actual=%0d|latency_cycles=%0d|observed_interface=axi_lite|evidence_type=blackbox|check_role=primary|result=PASS", pass_count, pass_count, pass_count, timeout_cycles);
            $display("HDLFLOW|TASK_END|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=AXI_FULL_TOP|requirement_id=REQ-RRB-021|operation_id=AXI_FULL_TOP|result=PASS");
            $display("TASK_END PASS");
        end
        else begin
            $display("HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=axi_full_top|txn_id=axi_top_summary|requirement_id=REQ-RRB-021|operation_id=AXI_FULL_TOP|sent=%0d|expected=0|actual=%0d|latency_cycles=%0d|observed_interface=axi_lite|evidence_type=blackbox|check_role=primary|result=FAIL", pass_count + fail_count, fail_count, timeout_cycles);
            $display("HDLFLOW|TASK_END|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=AXI_FULL_TOP|requirement_id=REQ-RRB-021|operation_id=AXI_FULL_TOP|result=FAIL");
            $display("TASK_END FAIL");
        end
        $stop;
    end
endmodule
// ---- END shared_bci_accel_top_tb.v ----

// ---- BEGIN shared_bci_accel_ssvep_tb.v ----
// -----------------------------------------------------------------------------
// Module: shared_bci_accel_ssvep_tb
// Purpose: Full 100-trial P012 SSVEP regression through the production core.
// Requirements: REQ-RRB-002, REQ-RRB-003, REQ-RRB-009, REQ-RRB-010,
//               REQ-RRB-012, REQ-RRB-019, REQ-RRB-023
// -----------------------------------------------------------------------------

`timescale 1ns/1ps

module shared_bci_accel_ssvep_tb;
    localparam integer SSVEP_TRIALS = 100;
    localparam integer SSVEP_PROGRAM_ROWS = 47;
    localparam integer SSVEP_PARAMETER_ROWS = 136;
    localparam integer SSVEP_FRAME_ROWS = 512;
    localparam integer SSVEP_RESULTS = 4;
    localparam integer SSVEP_CYCLE_MAX = 20000;
    localparam integer SSVEP_WATCHDOG_MAX = 100000;

    reg clk;
    reg reset_n;
    reg start_valid;
    wire start_ready;
    wire busy;
    wire done;
    reg program_load_valid;
    wire program_load_ready;
    reg [8:0] program_load_address;
    reg [63:0] program_load_data;
    reg parameter_load_valid;
    wire parameter_load_ready;
    reg [8:0] parameter_load_address;
    reg [63:0] parameter_load_data;
    reg frame_begin;
    reg [1:0] frame_page;
    reg [63:0] frame_config;
    reg frame_valid;
    wire frame_ready;
    reg [63:0] frame_data;
    wire frame_complete;
    wire [8:0] frame_beat_count;
    wire result_valid;
    reg result_ready;
    wire [15:0] result_data;
    wire result_last;

    reg [63:0] program_rows [0:SSVEP_PROGRAM_ROWS-1];
    reg [63:0] parameter_rows [0:SSVEP_PARAMETER_ROWS-1];
    reg [63:0] frame_rows [0:SSVEP_TRIALS*SSVEP_FRAME_ROWS-1];
    reg [15:0] expected_logits [0:SSVEP_TRIALS*SSVEP_RESULTS-1];
    reg [15:0] expected_predictions [0:SSVEP_TRIALS-1];
    reg [15:0] labels [0:SSVEP_TRIALS-1];
    reg [15:0] actual_logits [0:SSVEP_RESULTS-1];
    reg [15:0] expected_scale [0:1535];
    reg [15:0] expected_covariance [0:41];
    reg [15:0] expected_factor_inverse [0:41];
    reg [15:0] expected_white [0:1535];
    reg [15:0] expected_rec [0:143];
    reg [15:0] expected_projection [0:95];
    reg [15:0] expected_energy [0:47];
    reg [15:0] expected_feature_logits [0:3];

    integer index;
    integer trial;
    integer trial_start;
    integer trial_limit;
    integer current_trial;
    integer trial_result_count;
    integer trial_last_count;
    integer total_result_count;
    integer cycle_count;
    integer total_compute_cycles;
    integer maximum_compute_cycles;
    integer descriptor_last_cycle;
    integer actual_prediction;
    integer label_correct_count;
    integer pass_count;
    integer fail_count;
    integer checkpoint_index;
    integer checkpoint_mismatches;
    integer checkpoint_pass_count;
    integer checkpoint_fail_count;
    reg checkpoint_pending;
    reg [8:0] checkpoint_pc;
    reg test_complete;
    reg test_passed;

    task record_check;
        input [8*48-1:0] test_id;
        input [8*16-1:0] requirement_id;
        input [63:0] expected;
        input [63:0] actual;
        begin
            if (actual === expected) begin
                pass_count = pass_count + 1;
                $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=%0s|txn_id=p7_ssvep_%0d|requirement_id=%0s|operation_id=P007_SSVEP_100_TRIALS|sent=1|expected=%h|actual=%h|latency_cycles=%0d|observed_interface=module_boundary|evidence_type=blackbox|check_role=primary|result=PASS", test_id, pass_count + fail_count, requirement_id, expected, actual, cycle_count);
            end
            else begin
                fail_count = fail_count + 1;
                $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=%0s|txn_id=p7_ssvep_%0d|requirement_id=%0s|operation_id=P007_SSVEP_100_TRIALS|sent=1|expected=%h|actual=%h|latency_cycles=%0d|observed_interface=module_boundary|evidence_type=blackbox|check_role=primary|result=FAIL", test_id, pass_count + fail_count, requirement_id, expected, actual, cycle_count);
            end
        end
    endtask

    task record_checkpoint;
        input [8*48-1:0] checkpoint_id;
        input integer mismatch_count;
        begin
            if (mismatch_count == 0) begin
                checkpoint_pass_count = checkpoint_pass_count + 1;
                $display("P007_CHECKPOINT id=%0s mismatches=0 result=PASS",
                         checkpoint_id);
            end
            else begin
                checkpoint_fail_count = checkpoint_fail_count + 1;
                $display("P007_CHECKPOINT id=%0s mismatches=%0d result=FAIL",
                         checkpoint_id, mismatch_count);
            end
        end
    endtask

    task load_program_row;
        input [8:0] address;
        input [63:0] data;
        begin
            @(negedge clk);
            program_load_address = address;
            program_load_data = data;
            program_load_valid = 1'b1;
            while (program_load_ready !== 1'b1)
                @(negedge clk);
            @(negedge clk);
            program_load_valid = 1'b0;
        end
    endtask

    task load_parameter_row;
        input [8:0] address;
        input [63:0] data;
        begin
            @(negedge clk);
            parameter_load_address = address;
            parameter_load_data = data;
            parameter_load_valid = 1'b1;
            while (parameter_load_ready !== 1'b1)
                @(negedge clk);
            @(negedge clk);
            parameter_load_valid = 1'b0;
        end
    endtask

    function fp16_greater;
        input [15:0] left;
        input [15:0] right;
        begin
            if (left == right)
                fp16_greater = 1'b0;
            else if (left[15] != right[15])
                fp16_greater = right[15];
            else if (!left[15])
                fp16_greater = left[14:0] > right[14:0];
            else
                fp16_greater = left[14:0] < right[14:0];
        end
    endfunction

    function [15:0] read_feature_word;
        input [12:0] logical_address;
        begin
            case (logical_address[1:0])
                2'd0: read_feature_word =
                    u_dut.u_feature_memory.u_feature_bank0_bmg.memory[
                        logical_address[12:2]];
                2'd1: read_feature_word =
                    u_dut.u_feature_memory.u_feature_bank1_bmg.memory[
                        logical_address[12:2]];
                2'd2: read_feature_word =
                    u_dut.u_feature_memory.u_feature_bank2_bmg.memory[
                        logical_address[12:2]];
                default: read_feature_word =
                    u_dut.u_feature_memory.u_feature_bank3_bmg.memory[
                        logical_address[12:2]];
            endcase
        end
    endfunction

    shared_bci_accel_core u_dut (
        .clk(clk), .reset_n(reset_n),
        .start_valid(start_valid), .start_ready(start_ready),
        .busy(busy), .done(done),
        .program_load_valid(program_load_valid),
        .program_load_ready(program_load_ready),
        .program_load_address(program_load_address),
        .program_load_data(program_load_data),
        .parameter_load_valid(parameter_load_valid),
        .parameter_load_ready(parameter_load_ready),
        .parameter_load_address(parameter_load_address),
        .parameter_load_data(parameter_load_data),
        .frame_begin(frame_begin), .frame_page(frame_page),
        .frame_config(frame_config),
        .frame_valid(frame_valid), .frame_ready(frame_ready),
        .frame_data(frame_data), .frame_complete(frame_complete),
        .frame_beat_count(frame_beat_count),
        .result_valid(result_valid), .result_ready(result_ready),
        .result_data(result_data), .result_last(result_last)
    );

    always #5 clk = ~clk;

    always @(posedge clk) begin
        if (reset_n && result_valid && result_ready) begin
            if ((current_trial >= 0) &&
                (trial_result_count < SSVEP_RESULTS)) begin
                actual_logits[trial_result_count] = result_data;
                record_check("ssvep_logit", "REQ-RRB-009",
                             {48'd0, expected_logits[
                                 current_trial*SSVEP_RESULTS +
                                 trial_result_count]},
                             {48'd0, result_data});
            end
            trial_result_count = trial_result_count + 1;
            total_result_count = total_result_count + 1;
            if (result_last)
                trial_last_count = trial_last_count + 1;
        end
    end

    always @(negedge clk or negedge reset_n) begin
        if (!reset_n) begin
            checkpoint_pending <= 1'b0;
            checkpoint_pc <= 9'd0;
        end
        else begin
            checkpoint_pending <= u_dut.descriptor_complete;
            if (u_dut.descriptor_complete)
                checkpoint_pc <= u_dut.descriptor_pc;
            if (checkpoint_pending &&
                (current_trial == trial_start)) begin
                checkpoint_mismatches = 0;
                case (checkpoint_pc)
                    9'd2: begin
                        for (checkpoint_index = 0;
                             checkpoint_index < 42;
                             checkpoint_index = checkpoint_index + 1)
                            if (read_feature_word(13'd1536 +
                                checkpoint_index) !==
                                expected_covariance[checkpoint_index]) begin
                                if (checkpoint_mismatches < 16)
                                    $display("P007_COV_MISMATCH index=%0d expected=%04h actual=%04h",
                                             checkpoint_index,
                                             expected_covariance[
                                                 checkpoint_index],
                                             read_feature_word(13'd1536 +
                                                 checkpoint_index));
                                checkpoint_mismatches =
                                    checkpoint_mismatches + 1;
                            end
                        record_checkpoint("pc002_covariance",
                                          checkpoint_mismatches);
                    end
                    9'd6: begin
                        for (checkpoint_index = 0;
                             checkpoint_index < 42;
                             checkpoint_index = checkpoint_index + 1)
                            if (read_feature_word(13'd1578 +
                                checkpoint_index) !==
                                expected_factor_inverse[checkpoint_index])
                                checkpoint_mismatches =
                                    checkpoint_mismatches + 1;
                        record_checkpoint("pc006_factor_inverse",
                                          checkpoint_mismatches);
                    end
                    9'd10: begin
                        for (checkpoint_index = 0;
                             checkpoint_index < 1536;
                             checkpoint_index = checkpoint_index + 1)
                            if (read_feature_word(13'd1664 +
                                checkpoint_index) !==
                                expected_white[checkpoint_index]) begin
                                if (checkpoint_mismatches < 32)
                                    $display("P007_WHITE_MISMATCH index=%0d expected=%04h actual=%04h",
                                             checkpoint_index,
                                             expected_white[checkpoint_index],
                                             read_feature_word(13'd1664 +
                                                 checkpoint_index));
                                checkpoint_mismatches =
                                    checkpoint_mismatches + 1;
                            end
                        record_checkpoint("pc010_white",
                                          checkpoint_mismatches);
                    end
                    9'd14: begin
                        for (checkpoint_index = 0;
                             checkpoint_index < 144;
                             checkpoint_index = checkpoint_index + 1)
                            if (read_feature_word(13'd3200 +
                                checkpoint_index) !==
                                expected_rec[checkpoint_index]) begin
                                if (checkpoint_mismatches < 16)
                                    $display("P007_REC_MISMATCH index=%0d expected=%04h actual=%04h",
                                             checkpoint_index,
                                             expected_rec[checkpoint_index],
                                             read_feature_word(13'd3200 +
                                                 checkpoint_index));
                                checkpoint_mismatches =
                                    checkpoint_mismatches + 1;
                            end
                        record_checkpoint("pc014_rec",
                                          checkpoint_mismatches);
                    end
                    9'd18: begin
                        for (checkpoint_index = 0;
                             checkpoint_index < 96;
                             checkpoint_index = checkpoint_index + 1)
                            if (read_feature_word(13'd3344 +
                                checkpoint_index) !==
                                expected_projection[checkpoint_index]) begin
                                if (checkpoint_mismatches < 20)
                                    $display("P007_PROJECTION_MISMATCH index=%0d expected=%04h actual=%04h",
                                             checkpoint_index,
                                             expected_projection[
                                                 checkpoint_index],
                                             read_feature_word(13'd3344 +
                                                 checkpoint_index));
                                checkpoint_mismatches =
                                    checkpoint_mismatches + 1;
                            end
                        record_checkpoint("pc018_projection",
                                          checkpoint_mismatches);
                    end
                    9'd30: begin
                        for (checkpoint_index = 0;
                             checkpoint_index < 48;
                             checkpoint_index = checkpoint_index + 1)
                            if (read_feature_word(13'd3440 +
                                checkpoint_index) !==
                                expected_energy[checkpoint_index])
                                checkpoint_mismatches =
                                    checkpoint_mismatches + 1;
                        record_checkpoint("pc030_energy",
                                          checkpoint_mismatches);
                    end
                    9'd34: begin
                        for (checkpoint_index = 0;
                             checkpoint_index < 4;
                             checkpoint_index = checkpoint_index + 1)
                            if (read_feature_word(13'd3488 +
                                checkpoint_index) !==
                                expected_feature_logits[checkpoint_index])
                                checkpoint_mismatches =
                                    checkpoint_mismatches + 1;
                        record_checkpoint("pc034_logits",
                                          checkpoint_mismatches);
                    end
                    default: begin
                        checkpoint_mismatches = 0;
                    end
                endcase
            end
        end
    end

    always @(posedge clk) begin
        if (reset_n && u_dut.descriptor_complete &&
            (current_trial == trial_start)) begin
            $display("P007_DESCRIPTOR_CYCLES pc=%0d total=%0d delta=%0d",
                     u_dut.descriptor_pc, cycle_count,
                     cycle_count - descriptor_last_cycle);
            descriptor_last_cycle = cycle_count;
        end
    end

    initial begin
        clk = 1'b0;
        reset_n = 1'b0;
        start_valid = 1'b0;
        program_load_valid = 1'b0;
        program_load_address = 9'd0;
        program_load_data = 64'd0;
        parameter_load_valid = 1'b0;
        parameter_load_address = 9'd0;
        parameter_load_data = 64'd0;
        frame_begin = 1'b0;
        frame_page = 2'd3;
        frame_config = 64'h0000_001A_5800_4011;
        frame_valid = 1'b0;
        frame_data = 64'd0;
        result_ready = 1'b1;
        current_trial = -1;
        trial_start = 0;
        trial_limit = SSVEP_TRIALS;
        trial_result_count = 0;
        trial_last_count = 0;
        total_result_count = 0;
        cycle_count = 0;
        total_compute_cycles = 0;
        maximum_compute_cycles = 0;
        descriptor_last_cycle = 0;
        label_correct_count = 0;
        pass_count = 0;
        fail_count = 0;
        checkpoint_pending = 1'b0;
        checkpoint_pc = 9'd0;
        checkpoint_pass_count = 0;
        checkpoint_fail_count = 0;
        test_complete = 1'b0;
        test_passed = 1'b0;
        if ($value$plusargs("TRIAL_LIMIT=%d", trial_limit)) begin
            if ((trial_limit < 1) || (trial_limit > SSVEP_TRIALS)) begin
                $display("ERROR: TRIAL_LIMIT must be between 1 and %0d",
                         SSVEP_TRIALS);
                $finish;
            end
        end
        if ($value$plusargs("TRIAL_START=%d", trial_start)) begin
            if ((trial_start < 0) ||
                (trial_start >= SSVEP_TRIALS)) begin
                $display("ERROR: TRIAL_START must be between 0 and %0d",
                         SSVEP_TRIALS - 1);
                $finish;
            end
        end
        if ((trial_start + trial_limit) > SSVEP_TRIALS) begin
            $display("ERROR: TRIAL_START + TRIAL_LIMIT exceeds %0d",
                     SSVEP_TRIALS);
            $finish;
        end
        for (index = 0; index < SSVEP_RESULTS; index = index + 1)
            actual_logits[index] = 16'd0;

        $display("HDLFLOW|TASK_BEGIN|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P007_SSVEP_100_TRIALS|requirement_id=REQ-RRB-009|operation_id=P007_SSVEP_100_TRIALS");
        $readmemh("input/sources/verification_data/loop1/vectors/r7/ssvep_program.hex", program_rows);
        $readmemh("input/sources/verification_data/loop1/vectors/r7/ssvep_parameter_rows.hex", parameter_rows);
        $readmemh("input/sources/verification_data/loop1/vectors/r7/ssvep_frame_rows.hex", frame_rows);
        $readmemh("input/sources/verification_data/loop1/vectors/r7/ssvep_expected_logits.hex", expected_logits);
        $readmemh("input/sources/verification_data/loop1/vectors/r7/ssvep_expected_predictions.hex", expected_predictions);
        $readmemh("input/sources/verification_data/loop1/vectors/r7/ssvep_labels.hex", labels);
        $readmemh("input/sources/verification_data/loop1/vectors/r7/ssvep_checkpoint_ingress_scale.hex", expected_scale);
        $readmemh("input/sources/verification_data/loop1/vectors/r7/ssvep_checkpoint_pc002_covariance.hex", expected_covariance);
        $readmemh("input/sources/verification_data/loop1/vectors/r7/ssvep_checkpoint_pc006_factor_inverse.hex", expected_factor_inverse);
        $readmemh("input/sources/verification_data/loop1/vectors/r7/ssvep_checkpoint_pc010_white.hex", expected_white);
        $readmemh("input/sources/verification_data/loop1/vectors/r7/ssvep_checkpoint_pc014_rec.hex", expected_rec);
        $readmemh("input/sources/verification_data/loop1/vectors/r7/ssvep_checkpoint_pc018_projection.hex", expected_projection);
        $readmemh("input/sources/verification_data/loop1/vectors/r7/ssvep_checkpoint_pc030_energy.hex", expected_energy);
        $readmemh("input/sources/verification_data/loop1/vectors/r7/ssvep_checkpoint_pc034_logits.hex", expected_feature_logits);

        repeat (4) @(posedge clk);
        reset_n = 1'b1;
        repeat (2) @(posedge clk);
        for (index = 0; index < SSVEP_PROGRAM_ROWS; index = index + 1)
            load_program_row(index[8:0], program_rows[index]);
        for (index = 0; index < SSVEP_PARAMETER_ROWS; index = index + 1)
            load_parameter_row(index[8:0], parameter_rows[index]);

        for (trial = trial_start;
             trial < (trial_start + trial_limit);
             trial = trial + 1) begin
            @(negedge clk);
            current_trial = trial;
            trial_result_count = 0;
            trial_last_count = 0;
            cycle_count = 0;
            descriptor_last_cycle = 0;
            for (index = 0; index < SSVEP_RESULTS; index = index + 1)
                actual_logits[index] = 16'd0;

            frame_begin = 1'b1;
            @(negedge clk);
            frame_begin = 1'b0;
            for (index = 0; index < SSVEP_FRAME_ROWS; index = index + 1) begin
                frame_data = frame_rows[trial*SSVEP_FRAME_ROWS + index];
                frame_valid = 1'b1;
                while (frame_ready !== 1'b1)
                    @(negedge clk);
                @(negedge clk);
            end
            frame_valid = 1'b0;
            while (frame_complete !== 1'b1)
                @(negedge clk);
            record_check("ssvep_frame_complete", "REQ-RRB-019",
                         64'd1, {63'd0, frame_complete});
            if (trial == trial_start) begin
                checkpoint_mismatches = 0;
                for (checkpoint_index = 0;
                     checkpoint_index < 1536;
                     checkpoint_index = checkpoint_index + 1)
                    if (read_feature_word(checkpoint_index) !==
                        expected_scale[checkpoint_index])
                        checkpoint_mismatches =
                            checkpoint_mismatches + 1;
                record_checkpoint("ingress_scale",
                                  checkpoint_mismatches);
            end

            @(negedge clk);
            start_valid = 1'b1;
            while (start_ready !== 1'b1)
                @(negedge clk);
            @(negedge clk);
            start_valid = 1'b0;
            while ((done !== 1'b1) &&
                   (cycle_count < SSVEP_WATCHDOG_MAX)) begin
                @(posedge clk);
                cycle_count = cycle_count + 1;
            end

            if (done !== 1'b1)
                $display("P007_SSVEP_TIMEOUT trial=%0d controller_state=%0d pc=%0d engine_state=%0d",
                         trial,
                         u_dut.u_descriptor_controller.u_program_control_unit.state_q,
                         u_dut.u_descriptor_controller.u_program_control_unit.pc_q,
                         u_dut.u_execution_engine.state_q);

            record_check("ssvep_session_done", "REQ-RRB-005",
                         64'd1, {63'd0, done});
            record_check("ssvep_cycle_budget", "REQ-RRB-010",
                         64'd1, {63'd0, cycle_count <= SSVEP_CYCLE_MAX});
            record_check("ssvep_result_count", "REQ-RRB-012",
                         SSVEP_RESULTS, trial_result_count);
            record_check("ssvep_result_last_once", "REQ-RRB-012",
                         64'd1, trial_last_count);

            actual_prediction = 0;
            for (index = 1; index < SSVEP_RESULTS; index = index + 1)
                if (fp16_greater(actual_logits[index],
                                 actual_logits[actual_prediction]))
                    actual_prediction = index;
            record_check("ssvep_argmax", "REQ-RRB-009",
                         {48'd0, expected_predictions[trial]},
                         actual_prediction);
            if (actual_prediction == labels[trial])
                label_correct_count = label_correct_count + 1;
            total_compute_cycles = total_compute_cycles + cycle_count;
            if (cycle_count > maximum_compute_cycles)
                maximum_compute_cycles = cycle_count;
            @(posedge clk);
        end

        if ((trial_start == 0) && (trial_limit == SSVEP_TRIALS)) begin
            record_check("ssvep_400_logits", "REQ-RRB-009",
                         SSVEP_TRIALS*SSVEP_RESULTS,
                         total_result_count);
            record_check("ssvep_reference_accuracy", "REQ-RRB-009",
                         64'd92, label_correct_count);
        end
        else begin
            record_check("ssvep_diagnostic_logits", "REQ-RRB-009",
                         trial_limit*SSVEP_RESULTS, total_result_count);
        end

        test_complete = 1'b1;
        test_passed = (fail_count == 0) &&
            (checkpoint_fail_count == 0);
        if (test_passed) begin
            $display("HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=p7_ssvep_100_trials|txn_id=p7_ssvep_summary|requirement_id=REQ-RRB-009|operation_id=P007_SSVEP_100_TRIALS|sent=%0d|expected=%0d|actual=%0d|latency_cycles=%0d|observed_interface=module_boundary|evidence_type=blackbox|check_role=primary|result=PASS", pass_count, pass_count, pass_count, maximum_compute_cycles);
            $display("P007_SSVEP_METRICS trials=%0d logits=%0d correct=%0d max_cycles=%0d total_cycles=%0d", trial_limit, total_result_count, label_correct_count, maximum_compute_cycles, total_compute_cycles);
            $display("HDLFLOW|TASK_END|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P007_SSVEP_100_TRIALS|requirement_id=REQ-RRB-009|operation_id=P007_SSVEP_100_TRIALS|result=PASS");
            $display("TASK_END PASS");
        end
        else begin
            $display("HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=p7_ssvep_100_trials|txn_id=p7_ssvep_summary|requirement_id=REQ-RRB-009|operation_id=P007_SSVEP_100_TRIALS|sent=%0d|expected=0|actual=%0d|latency_cycles=%0d|observed_interface=module_boundary|evidence_type=blackbox|check_role=primary|result=FAIL", pass_count + fail_count, fail_count, maximum_compute_cycles);
            $display("HDLFLOW|TASK_END|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P007_SSVEP_100_TRIALS|requirement_id=REQ-RRB-009|operation_id=P007_SSVEP_100_TRIALS|result=FAIL");
            $display("TASK_END FAIL");
        end
        // Completion is consumed by the single formal tb_top below.
    end
endmodule
// ---- END shared_bci_accel_ssvep_tb.v ----

// ---- BEGIN shared_bci_accel_eeg_tb.v ----
// -----------------------------------------------------------------------------
// Module: shared_bci_accel_eeg_tb
// Purpose: Full-program P5 EEG regression through the production hierarchy.
// Requirements: REQ-RRB-005, REQ-RRB-006, REQ-RRB-012, REQ-RRB-019,
//               REQ-RRB-022, REQ-RRB-023
// -----------------------------------------------------------------------------

`timescale 1ns/1ps

module shared_bci_accel_eeg_tb;
    localparam integer EEG_CYCLE_MAX = 41800;

    reg clk;
    reg reset_n;
    reg start_valid;
    wire start_ready;
    wire busy;
    wire done;
    reg program_load_valid;
    wire program_load_ready;
    reg [8:0] program_load_address;
    reg [63:0] program_load_data;
    reg parameter_load_valid;
    wire parameter_load_ready;
    reg [8:0] parameter_load_address;
    reg [63:0] parameter_load_data;
    reg frame_begin;
    reg [1:0] frame_page;
    reg [63:0] frame_config;
    reg frame_valid;
    wire frame_ready;
    reg [63:0] frame_data;
    wire frame_complete;
    wire [8:0] frame_beat_count;
    wire result_valid;
    reg result_ready;
    wire [15:0] result_data;
    wire result_last;

    reg [63:0] program_rows [0:85];
    reg [63:0] parameter_rows [0:280];
    reg [63:0] frame_rows [0:511];
    reg [15:0] expected_logits [0:15];
    reg [15:0] expected_op0 [0:2047];
    reg [15:0] expected_op1 [0:8191];
    reg [15:0] expected_op2 [0:2047];
    reg [15:0] expected_op3 [0:8191];
    reg [15:0] expected_op4 [0:1023];
    reg [15:0] expected_op5 [0:255];
    reg [15:0] expected_op6 [0:255];
    reg [15:0] expected_op7 [0:255];
    reg [15:0] expected_op8 [0:31];
    integer index;
    integer result_count;
    integer last_count;
    integer cycle_count;
    integer pass_count;
    integer fail_count;
    integer checkpoint_index;
    integer checkpoint_row;
    integer checkpoint_sample;
    integer checkpoint_plane;
    integer checkpoint_mismatches;
    integer checkpoint_failure_count;
    integer checkpoint_limit;
    reg checkpoint_pending;
    reg [8:0] checkpoint_pc;
    reg test_complete;
    reg test_passed;

    task record_check;
        input [8*48-1:0] test_id;
        input [8*16-1:0] requirement_id;
        input [63:0] expected;
        input [63:0] actual;
        begin
            if (actual === expected) begin
                pass_count = pass_count + 1;
                $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=%0s|txn_id=p5_eeg_%0d|requirement_id=%0s|operation_id=P5_EEG_FULL_PROGRAM|sent=1|expected=%h|actual=%h|latency_cycles=%0d|observed_interface=module_boundary|evidence_type=blackbox|check_role=primary|result=PASS", test_id, pass_count + fail_count, requirement_id, expected, actual, cycle_count);
            end
            else begin
                fail_count = fail_count + 1;
                $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=%0s|txn_id=p5_eeg_%0d|requirement_id=%0s|operation_id=P5_EEG_FULL_PROGRAM|sent=1|expected=%h|actual=%h|latency_cycles=%0d|observed_interface=module_boundary|evidence_type=blackbox|check_role=primary|result=FAIL", test_id, pass_count + fail_count, requirement_id, expected, actual, cycle_count);
            end
        end
    endtask

    task record_checkpoint_failure;
        input [8*40-1:0] checkpoint_id;
        input integer mismatch_count;
        begin
            if (mismatch_count != 0) begin
                checkpoint_failure_count = checkpoint_failure_count + 1;
                $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=%0s|txn_id=p5_eeg_checkpoint|requirement_id=REQ-RRB-006|operation_id=P5_EEG_FULL_PROGRAM|sent=1|expected=0|actual=%0d|latency_cycles=%0d|observed_interface=feature_memory|evidence_type=whitebox|check_role=diagnostic|result=FAIL", checkpoint_id, mismatch_count, cycle_count);
            end
        end
    endtask

    task load_program_row;
        input [8:0] address;
        input [63:0] data;
        begin
            @(negedge clk);
            program_load_address = address;
            program_load_data = data;
            program_load_valid = 1'b1;
            while (program_load_ready !== 1'b1)
                @(negedge clk);
            @(negedge clk);
            program_load_valid = 1'b0;
        end
    endtask

    task load_parameter_row;
        input [8:0] address;
        input [63:0] data;
        begin
            @(negedge clk);
            parameter_load_address = address;
            parameter_load_data = data;
            parameter_load_valid = 1'b1;
            while (parameter_load_ready !== 1'b1)
                @(negedge clk);
            @(negedge clk);
            parameter_load_valid = 1'b0;
        end
    endtask

    function [15:0] read_feature_word;
        input [12:0] logical_address;
        begin
            case (logical_address[1:0])
                2'd0: read_feature_word =
                    u_dut.u_feature_memory.u_feature_bank0_bmg.memory[
                        logical_address[12:2]];
                2'd1: read_feature_word =
                    u_dut.u_feature_memory.u_feature_bank1_bmg.memory[
                        logical_address[12:2]];
                2'd2: read_feature_word =
                    u_dut.u_feature_memory.u_feature_bank2_bmg.memory[
                        logical_address[12:2]];
                default: read_feature_word =
                    u_dut.u_feature_memory.u_feature_bank3_bmg.memory[
                        logical_address[12:2]];
            endcase
        end
    endfunction

    shared_bci_accel_core u_dut (
        .clk(clk), .reset_n(reset_n),
        .start_valid(start_valid), .start_ready(start_ready),
        .busy(busy), .done(done),
        .program_load_valid(program_load_valid),
        .program_load_ready(program_load_ready),
        .program_load_address(program_load_address),
        .program_load_data(program_load_data),
        .parameter_load_valid(parameter_load_valid),
        .parameter_load_ready(parameter_load_ready),
        .parameter_load_address(parameter_load_address),
        .parameter_load_data(parameter_load_data),
        .frame_begin(frame_begin), .frame_page(frame_page),
        .frame_config(frame_config),
        .frame_valid(frame_valid), .frame_ready(frame_ready),
        .frame_data(frame_data), .frame_complete(frame_complete),
        .frame_beat_count(frame_beat_count),
        .result_valid(result_valid), .result_ready(result_ready),
        .result_data(result_data), .result_last(result_last)
    );

    always #5 clk = ~clk;

    // Descriptor completion acknowledges retire acceptance. The BMG write is
    // externally observable one clock later, so checkpoint the committed
    // architectural state on the following falling edge.
    always @(negedge clk or negedge reset_n) begin
        if (!reset_n) begin
            checkpoint_pending <= 1'b0;
            checkpoint_pc <= 9'd0;
        end
        else begin
            checkpoint_pending <= u_dut.descriptor_complete;
            if (u_dut.descriptor_complete)
                checkpoint_pc <= u_dut.descriptor_pc;
        end
    end

    // Sample at the falling edge so the final feature-memory write committed
    // on descriptor_complete is visible before checkpoint comparison.
    always @(negedge clk) begin
        if (reset_n && u_dut.descriptor_valid && u_dut.descriptor_ready)
            $display("P5_EEG_DESCRIPTOR_BEGIN pc=%0d cycle=%0d opcode=%0h mode=%0h",
                     u_dut.descriptor_pc, cycle_count,
                     u_dut.descriptor_base[63:60],
                     u_dut.descriptor_base[57:54]);
        if (reset_n && u_dut.descriptor_complete)
            $display("P5_EEG_DESCRIPTOR_COMPLETE pc=%0d cycle=%0d",
                     u_dut.descriptor_pc, cycle_count);
        if (reset_n && checkpoint_pending &&
            (checkpoint_pc == 9'd2)) begin
            checkpoint_mismatches = 0;
            checkpoint_index = 0;
            for (checkpoint_sample = 0; checkpoint_sample < 128;
                 checkpoint_sample = checkpoint_sample + 1) begin
                for (checkpoint_row = 0; checkpoint_row < 16;
                     checkpoint_row = checkpoint_row + 1) begin
                    if (read_feature_word(13'd6144 +
                        checkpoint_sample*16 + checkpoint_row) !==
                        expected_op0[checkpoint_row*128 +
                                     checkpoint_sample])
                        checkpoint_mismatches = checkpoint_mismatches + 1;
                    checkpoint_index = checkpoint_index + 1;
                end
            end
            $display("P5_EEG_CHECKPOINT descriptor=1 mismatches=%0d",
                     checkpoint_mismatches);
            record_checkpoint_failure("eeg_checkpoint_descriptor_1",
                                      checkpoint_mismatches);
        end
        if (reset_n && checkpoint_pending &&
            (checkpoint_pc == 9'd18)) begin
            checkpoint_mismatches = 0;
            checkpoint_index = 0;
            for (checkpoint_plane = 0; checkpoint_plane < 4;
                 checkpoint_plane = checkpoint_plane + 1) begin
                for (checkpoint_sample = 0; checkpoint_sample < 128;
                     checkpoint_sample = checkpoint_sample + 1) begin
                    for (checkpoint_row = 0; checkpoint_row < 16;
                         checkpoint_row = checkpoint_row + 1) begin
                        if (read_feature_word(checkpoint_plane*2048 +
                            checkpoint_sample*16 + checkpoint_row) !==
                            expected_op1[checkpoint_plane*2048 +
                                         checkpoint_row*128 +
                                         checkpoint_sample])
                            checkpoint_mismatches =
                                checkpoint_mismatches + 1;
                        checkpoint_index = checkpoint_index + 1;
                    end
                end
            end
            $display("P5_EEG_CHECKPOINT descriptor=5 mismatches=%0d",
                     checkpoint_mismatches);
            record_checkpoint_failure("eeg_checkpoint_descriptor_5",
                                      checkpoint_mismatches);
        end
        if (reset_n && checkpoint_pending &&
            (checkpoint_pc == 9'd22)) begin
            checkpoint_mismatches = 0;
            checkpoint_index = 0;
            for (checkpoint_sample = 0; checkpoint_sample < 128;
                 checkpoint_sample = checkpoint_sample + 1) begin
                for (checkpoint_row = 0; checkpoint_row < 16;
                     checkpoint_row = checkpoint_row + 1) begin
                    if (read_feature_word(checkpoint_sample*16 +
                        checkpoint_row) !==
                        expected_op2[checkpoint_row*128 +
                                     checkpoint_sample]) begin
                        if (checkpoint_mismatches < 16)
                            $display("P5_EEG_OP2_MISMATCH row=%0d sample=%0d expected=%04h actual=%04h",
                                     checkpoint_row, checkpoint_sample,
                                     expected_op2[checkpoint_row*128 +
                                                  checkpoint_sample],
                                     read_feature_word(
                                         checkpoint_sample*16 +
                                         checkpoint_row));
                        checkpoint_mismatches = checkpoint_mismatches + 1;
                    end
                    checkpoint_index = checkpoint_index + 1;
                end
            end
            $display("P5_EEG_CHECKPOINT descriptor=6 mismatches=%0d",
                     checkpoint_mismatches);
            record_checkpoint_failure("eeg_checkpoint_descriptor_6",
                                      checkpoint_mismatches);
        end
        if (reset_n && checkpoint_pending &&
            (checkpoint_pc == 9'd26)) begin
            checkpoint_mismatches = 0;
            for (checkpoint_sample = 0; checkpoint_sample < 128;
                 checkpoint_sample = checkpoint_sample + 1) begin
                for (checkpoint_row = 0; checkpoint_row < 16;
                     checkpoint_row = checkpoint_row + 1) begin
                    if (read_feature_word(13'd2048 +
                        checkpoint_sample*16 + checkpoint_row) !==
                        expected_op3[2048 + checkpoint_row*128 +
                                     checkpoint_sample])
                        checkpoint_mismatches = checkpoint_mismatches + 1;
                end
            end
            $display("P5_EEG_CHECKPOINT descriptor=7 mismatches=%0d",
                     checkpoint_mismatches);
            record_checkpoint_failure("eeg_checkpoint_descriptor_7",
                                      checkpoint_mismatches);
        end
        if (reset_n && checkpoint_pending &&
            (checkpoint_pc == 9'd38)) begin
            checkpoint_mismatches = 0;
            for (checkpoint_plane = 0; checkpoint_plane < 4;
                 checkpoint_plane = checkpoint_plane + 1) begin
                for (checkpoint_sample = 0; checkpoint_sample < 128;
                     checkpoint_sample = checkpoint_sample + 1) begin
                    for (checkpoint_row = 0; checkpoint_row < 16;
                         checkpoint_row = checkpoint_row + 1) begin
                        if (read_feature_word(checkpoint_plane*2048 +
                            checkpoint_sample*16 + checkpoint_row) !==
                            expected_op3[checkpoint_plane*2048 +
                                         checkpoint_row*128 +
                                         checkpoint_sample])
                            checkpoint_mismatches =
                                checkpoint_mismatches + 1;
                    end
                end
            end
            $display("P5_EEG_CHECKPOINT descriptor=10 mismatches=%0d",
                     checkpoint_mismatches);
            record_checkpoint_failure("eeg_checkpoint_descriptor_10",
                                      checkpoint_mismatches);
        end
        if (reset_n && checkpoint_pending &&
            ((checkpoint_pc == 9'd42) ||
             (checkpoint_pc == 9'd46) ||
             (checkpoint_pc == 9'd50) ||
             (checkpoint_pc == 9'd54))) begin
            checkpoint_mismatches = 0;
            if (checkpoint_pc == 9'd42)
                checkpoint_limit = 256;
            else if (checkpoint_pc == 9'd46)
                checkpoint_limit = 512;
            else if (checkpoint_pc == 9'd50)
                checkpoint_limit = 768;
            else
                checkpoint_limit = 1024;
            for (checkpoint_index = 0;
                 checkpoint_index < checkpoint_limit;
                 checkpoint_index = checkpoint_index + 1) begin
                if (read_feature_word(checkpoint_index) !==
                    expected_op4[checkpoint_index]) begin
                    if (checkpoint_mismatches < 16)
                        $display("P5_EEG_OP4_MISMATCH pc=%0d index=%0d expected=%h actual=%h",
                                 checkpoint_pc, checkpoint_index,
                                 expected_op4[checkpoint_index],
                                 read_feature_word(checkpoint_index));
                    checkpoint_mismatches = checkpoint_mismatches + 1;
                end
            end
            $display("P5_EEG_CHECKPOINT pc=%0d op4_words=%0d mismatches=%0d",
                     checkpoint_pc, checkpoint_limit,
                     checkpoint_mismatches);
            record_checkpoint_failure("eeg_checkpoint_op4_partial",
                                      checkpoint_mismatches);
        end
        if (reset_n && checkpoint_pending &&
            (checkpoint_pc == 9'd58)) begin
            checkpoint_mismatches = 0;
            for (checkpoint_sample = 0; checkpoint_sample < 32;
                 checkpoint_sample = checkpoint_sample + 1) begin
                for (checkpoint_row = 0; checkpoint_row < 8;
                     checkpoint_row = checkpoint_row + 1) begin
                    if (read_feature_word(13'd4096 +
                        checkpoint_sample*8 + checkpoint_row) !==
                        expected_op5[checkpoint_row*32 +
                                     checkpoint_sample]) begin
                        if (checkpoint_mismatches < 16)
                            $display("P5_EEG_OP5_MISMATCH row=%0d sample=%0d expected=%h actual=%h",
                                     checkpoint_row, checkpoint_sample,
                                     expected_op5[checkpoint_row*32 +
                                                  checkpoint_sample],
                                     read_feature_word(13'd4096 +
                                         checkpoint_sample*8 +
                                         checkpoint_row));
                        checkpoint_mismatches = checkpoint_mismatches + 1;
                    end
                end
            end
            $display("P5_EEG_CHECKPOINT descriptor=15 mismatches=%0d",
                     checkpoint_mismatches);
            record_checkpoint_failure("eeg_checkpoint_descriptor_15",
                                      checkpoint_mismatches);
        end
        if (reset_n && checkpoint_pending &&
            (checkpoint_pc == 9'd62)) begin
            checkpoint_mismatches = 0;
            for (checkpoint_sample = 0; checkpoint_sample < 32;
                 checkpoint_sample = checkpoint_sample + 1) begin
                for (checkpoint_row = 0; checkpoint_row < 8;
                     checkpoint_row = checkpoint_row + 1) begin
                    if (read_feature_word(13'd512 +
                        checkpoint_sample*8 + checkpoint_row) !==
                        expected_op6[checkpoint_row*32 +
                                     checkpoint_sample]) begin
                        if (checkpoint_mismatches < 16)
                            $display("P5_EEG_OP6_MISMATCH row=%0d sample=%0d expected=%h actual=%h",
                                     checkpoint_row, checkpoint_sample,
                                     expected_op6[checkpoint_row*32 +
                                                  checkpoint_sample],
                                     read_feature_word(13'd512 +
                                         checkpoint_sample*8 +
                                         checkpoint_row));
                        checkpoint_mismatches = checkpoint_mismatches + 1;
                    end
                end
            end
            $display("P5_EEG_CHECKPOINT descriptor=16 mismatches=%0d",
                     checkpoint_mismatches);
            record_checkpoint_failure("eeg_checkpoint_descriptor_16",
                                      checkpoint_mismatches);
        end
        if (reset_n && checkpoint_pending &&
            (checkpoint_pc == 9'd66)) begin
            checkpoint_mismatches = 0;
            for (checkpoint_sample = 0; checkpoint_sample < 32;
                 checkpoint_sample = checkpoint_sample + 1) begin
                for (checkpoint_row = 0; checkpoint_row < 8;
                     checkpoint_row = checkpoint_row + 1) begin
                    if (read_feature_word(checkpoint_sample*8 +
                        checkpoint_row) !==
                        expected_op7[checkpoint_row*32 +
                                     checkpoint_sample])
                        checkpoint_mismatches = checkpoint_mismatches + 1;
                end
            end
            $display("P5_EEG_CHECKPOINT descriptor=17 mismatches=%0d",
                     checkpoint_mismatches);
            record_checkpoint_failure("eeg_checkpoint_descriptor_17",
                                      checkpoint_mismatches);
        end
        if (reset_n && checkpoint_pending &&
            (checkpoint_pc == 9'd70)) begin
            checkpoint_mismatches = 0;
            for (checkpoint_sample = 0; checkpoint_sample < 4;
                 checkpoint_sample = checkpoint_sample + 1) begin
                for (checkpoint_row = 0; checkpoint_row < 8;
                     checkpoint_row = checkpoint_row + 1) begin
                    if (read_feature_word(13'd768 +
                        checkpoint_sample*8 + checkpoint_row) !==
                        expected_op8[checkpoint_row*4 +
                                     checkpoint_sample])
                        checkpoint_mismatches = checkpoint_mismatches + 1;
                end
            end
            $display("P5_EEG_CHECKPOINT descriptor=18 mismatches=%0d",
                     checkpoint_mismatches);
            record_checkpoint_failure("eeg_checkpoint_descriptor_18",
                                      checkpoint_mismatches);
        end
        if (reset_n && checkpoint_pending &&
            (checkpoint_pc == 9'd78)) begin
            checkpoint_mismatches = 0;
            for (checkpoint_index = 0; checkpoint_index < 16;
                 checkpoint_index = checkpoint_index + 1)
                if (read_feature_word(checkpoint_index) !==
                    expected_logits[checkpoint_index])
                    checkpoint_mismatches = checkpoint_mismatches + 1;
            $display("P5_EEG_CHECKPOINT descriptor=20 mismatches=%0d",
                     checkpoint_mismatches);
            record_checkpoint_failure("eeg_checkpoint_descriptor_20",
                                      checkpoint_mismatches);
        end
        if (reset_n && result_valid && result_ready) begin
            if (result_count < 16) begin
                record_check("eeg_logit", "REQ-RRB-006",
                             {48'd0, expected_logits[result_count]},
                             {48'd0, result_data});
            end
            result_count = result_count + 1;
            if (result_last)
                last_count = last_count + 1;
        end
    end

    initial begin
        clk = 1'b0;
        reset_n = 1'b0;
        start_valid = 1'b0;
        program_load_valid = 1'b0;
        program_load_address = 9'd0;
        program_load_data = 64'd0;
        parameter_load_valid = 1'b0;
        parameter_load_address = 9'd0;
        parameter_load_data = 64'd0;
        frame_begin = 1'b0;
        frame_page = 2'd0;
        frame_config = 64'd0;
        frame_valid = 1'b0;
        frame_data = 64'd0;
        result_ready = 1'b1;
        result_count = 0;
        last_count = 0;
        cycle_count = 0;
        pass_count = 0;
        fail_count = 0;
        checkpoint_failure_count = 0;
        test_complete = 1'b0;
        test_passed = 1'b0;

        $display("HDLFLOW|TASK_BEGIN|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P5_EEG_FULL_PROGRAM|requirement_id=REQ-RRB-006|operation_id=P5_EEG_FULL_PROGRAM");

        $readmemh("input/sources/verification_data/loop1/vectors/r5/eeg_bank_aware_program.hex", program_rows);
        $readmemh("input/sources/verification_data/loop1/vectors/r5/eeg_bank_aware_parameter_rows.hex", parameter_rows);
        $readmemh("input/sources/verification_data/loop1/vectors/r5/eeg_frame_rows.hex", frame_rows);
        $readmemh("input/sources/verification_data/loop1/vectors/r5/eeg_expected_logits.hex", expected_logits);
        $readmemh("input/sources/verification_data/loop1/eeg_reference/op00_temporal_1.hex", expected_op0);
        $readmemh("input/sources/verification_data/loop1/eeg_reference/op01_temporal_2.hex", expected_op1);
        $readmemh("input/sources/verification_data/loop1/eeg_reference/op02_temporal_3_sum.hex", expected_op2);
        $readmemh("input/sources/verification_data/loop1/eeg_reference/op03_temporal_4_bn_relu.hex", expected_op3);
        $readmemh("input/sources/verification_data/loop1/eeg_reference/op04_spatial_dw_bn_relu.hex", expected_op4);
        $readmemh("input/sources/verification_data/loop1/eeg_reference/op05_avgpool_4.hex", expected_op5);
        $readmemh("input/sources/verification_data/loop1/eeg_reference/op06_separable_dw.hex", expected_op6);
        $readmemh("input/sources/verification_data/loop1/eeg_reference/op07_pointwise_bn_relu.hex", expected_op7);
        $readmemh("input/sources/verification_data/loop1/eeg_reference/op08_avgpool_8.hex", expected_op8);

        repeat (4) @(posedge clk);
        reset_n = 1'b1;
        repeat (2) @(posedge clk);
        for (index = 0; index < 86; index = index + 1)
            load_program_row(index[8:0], program_rows[index]);
        for (index = 0; index < 281; index = index + 1)
            load_parameter_row(index[8:0], parameter_rows[index]);

        @(negedge clk);
        frame_begin = 1'b1;
        @(negedge clk);
        frame_begin = 1'b0;
        for (index = 0; index < 512; index = index + 1) begin
            frame_data = frame_rows[index];
            frame_valid = 1'b1;
            while (frame_ready !== 1'b1)
                @(negedge clk);
            @(negedge clk);
        end
        frame_valid = 1'b0;
        record_check("eeg_frame_complete", "REQ-RRB-019",
                     64'd1, {63'd0, frame_complete});

        @(negedge clk);
        start_valid = 1'b1;
        while (start_ready !== 1'b1)
            @(negedge clk);
        @(negedge clk);
        start_valid = 1'b0;
        while ((done !== 1'b1) && (cycle_count < 100000)) begin
            @(posedge clk);
            cycle_count = cycle_count + 1;
        end

        if (done !== 1'b1) begin
            $display("P5_EEG_TIMEOUT controller_state=%0d pc=%0d engine_state=%0d i0=%0d i2=%0d gather_issue=%0d gather_result=%0d chunk=%0d pending=%0d block=%0d retire_active=%0d",
                     u_dut.u_descriptor_controller.u_program_control_unit.state_q,
                     u_dut.u_descriptor_controller.u_program_control_unit.pc_q,
                     u_dut.u_execution_engine.state_q,
                     u_dut.u_execution_engine.sequence_i0_q,
                     u_dut.u_execution_engine.sequence_i2_q,
                     u_dut.u_execution_engine.gather_issue_count_q,
                     u_dut.u_execution_engine.gather_result_count_q,
                     u_dut.u_execution_engine.chunk_index_q,
                     u_dut.u_execution_engine.accumulation_add_pending_q,
                     u_dut.u_execution_engine.window_issue_block_q,
                     u_dut.u_execution_engine.retire_stream_active_q);
        end

        record_check("eeg_session_done", "REQ-RRB-005",
                     64'd1, {63'd0, done});
        record_check("eeg_cycle_budget", "REQ-RRB-023",
                     64'd1, {63'd0, cycle_count <= EEG_CYCLE_MAX});
        repeat (2) @(posedge clk);
        record_check("eeg_result_count", "REQ-RRB-012",
                     64'd16, result_count);
        record_check("eeg_result_last_once", "REQ-RRB-012",
                     64'd1, last_count);

        test_complete = 1'b1;
        test_passed = (fail_count == 0) &&
                      (checkpoint_failure_count == 0);
        if (test_passed) begin
            $display("HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=p5_eeg_full_program|txn_id=p5_eeg_summary|requirement_id=REQ-RRB-006|operation_id=P5_EEG_FULL_PROGRAM|sent=%0d|expected=%0d|actual=%0d|latency_cycles=%0d|observed_interface=module_boundary|evidence_type=blackbox|check_role=primary|result=PASS", pass_count, pass_count, pass_count, cycle_count);
            $display("HDLFLOW|TASK_END|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P5_EEG_FULL_PROGRAM|requirement_id=REQ-RRB-006|operation_id=P5_EEG_FULL_PROGRAM|result=PASS");
            $display("TASK_END PASS");
        end
        else begin
            $display("HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=p5_eeg_full_program|txn_id=p5_eeg_summary|requirement_id=REQ-RRB-006|operation_id=P5_EEG_FULL_PROGRAM|sent=%0d|expected=0|actual=%0d|latency_cycles=%0d|observed_interface=module_boundary|evidence_type=blackbox|check_role=primary|result=FAIL", pass_count + fail_count, fail_count, cycle_count);
            $display("HDLFLOW|TASK_END|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=P5_EEG_FULL_PROGRAM|requirement_id=REQ-RRB-006|operation_id=P5_EEG_FULL_PROGRAM|result=FAIL");
            $display("TASK_END FAIL");
        end
        // Completion is consumed by the single formal tb_top below.
    end
endmodule
// ---- END shared_bci_accel_eeg_tb.v ----

// One formal top exercises both mutually exclusive program modes against
// independent instances, then emits the Workflow verification contract once.
module tb_top;
    shared_bci_accel_eeg_tb eeg_case();
    shared_bci_accel_ssvep_tb ssvep_case();

    initial begin
        wait ((eeg_case.test_complete === 1'b1) &&
              (ssvep_case.test_complete === 1'b1));
        #1;
        if ((eeg_case.test_passed === 1'b1) &&
            (ssvep_case.test_passed === 1'b1)) begin
            $display("WF_INFO|case=VER-P2-EEG|purpose=shared_engine_eeg_mode|input=approved_eeg_program_parameters_and_frame|expected=16_bit_exact_logits|actual=16_bit_exact_logits_cycles_%0d|result=PASS", eeg_case.cycle_count);
            $display("WF_INFO|case=VER-P2-SSVEP|purpose=shared_engine_ssvep_mode|input=100_approved_ssvep_trials|expected=400_bit_exact_logits_and_predictions|actual=400_bit_exact_logits_and_predictions|result=PASS");
            $display("WF_INFO|case=VER-P2-SSVEP-CYCLES|purpose=ssvep_single_trial_cycle_budget|input=accepted_start_to_done|expected=max_cycles_le_20000|actual=max_cycles_%0d|result=PASS", ssvep_case.maximum_compute_cycles);
            $display("WF_SUMMARY|total=3|pass=3|fail=0");
        end
        else begin
            $display("WF_ERROR|case=VER-P2-MODES|message=eeg_or_ssvep_mode_failed");
            $display("WF_INFO|case=VER-P2-EEG|purpose=shared_engine_eeg_mode|input=approved_eeg_program_parameters_and_frame|expected=16_bit_exact_logits|actual=mode_failure|result=FAIL");
            $display("WF_INFO|case=VER-P2-SSVEP|purpose=shared_engine_ssvep_mode|input=100_approved_ssvep_trials|expected=400_bit_exact_logits_and_predictions|actual=mode_failure|result=FAIL");
            $display("WF_INFO|case=VER-P2-SSVEP-CYCLES|purpose=ssvep_single_trial_cycle_budget|input=accepted_start_to_done|expected=max_cycles_le_20000|actual=max_cycles_%0d|result=FAIL", ssvep_case.maximum_compute_cycles);
            $display("WF_SUMMARY|total=3|pass=0|fail=3");
        end
        $finish;
    end
endmodule
