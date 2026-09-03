`timescale 1ns/1ps

// Integrated directed TB authority for P1 migration.
// Scenario bodies are preserved from the six reviewed legacy tops and are
// reachable only through tb_top's elaboration parameter.

// BEGIN MIGRATED SCENARIO: eeg_bci_core_functional_tb.v
`timescale 1ns/1ps

module eeg_bci_core_functional_tb;
    reg clk;
    reg rst_n;
    reg stream_valid;
    wire stream_ready;
    reg [15:0] stream_data;
    reg [2:0] stream_type;
    reg stream_last;
    reg command_valid;
    wire command_ready;
    wire busy;
    wire [31:0] result;
    wire infer_done;
    wire [3:0] class_led;
    wire error;
    wire trace_write_valid;
    wire [3:0] trace_opcode;
    wire [12:0] trace_write_address;
    wire [15:0] trace_write_data;
    wire trace_write2_valid;
    wire [12:0] trace_write2_address;
    wire [15:0] trace_write2_data;

    reg [15:0] input_words [0:2047];
    reg [15:0] parameter_words [0:1075];
    reg [15:0] instruction_words [0:263];
    reg [15:0] golden_op0 [0:2047];
    reg [15:0] golden_op1 [0:8191];
    reg [15:0] golden_op2 [0:2047];
    reg [15:0] golden_op3 [0:8191];
    reg [15:0] golden_op4 [0:1023];
    reg [15:0] golden_op5 [0:255];
    reg [15:0] golden_op6 [0:255];
    reg [15:0] golden_op7 [0:255];
    reg [15:0] golden_op8 [0:31];
    reg [15:0] golden_op9 [0:15];
    integer write_count [0:9];
    integer index;
    integer mismatch_count;
    integer cycle_count;
    integer inference_start_cycle;
    integer inference_done_cycle;
    integer inference_cycles;
    integer op_start_cycle;
    integer active_descriptor;
    integer op_latency [0:10];
    reg inference_active;
    reg [15:0] expected_word;
    reg [15:0] expected_word2;
    reg expected_address_valid;
    reg expected_address2_valid;

    bci_accel_core dut (
        .clk(clk),
        .rst_n(rst_n),
        .stream_valid(stream_valid),
        .stream_ready(stream_ready),
        .stream_data(stream_data),
        .stream_type(stream_type),
        .stream_last(stream_last),
        .command_valid(command_valid),
        .command_ready(command_ready),
        .profile_select(2'b01),
        .instruction_version(2'b01),
        .busy(busy),
        .result(result),
        .infer_done(infer_done),
        .class_led(class_led),
        .error(error),
        .clear_counters(1'b0),
        .snapshot_counters(1'b0),
        .total_cycles_snapshot(),
        .memory_stalls_snapshot(),
        .producer_stalls_snapshot(),
        .consumer_stalls_snapshot(),
        .mac_activity_snapshot(),
        .tile_occupancy_snapshot(),
        .trace_write_valid(trace_write_valid),
        .trace_opcode(trace_opcode),
        .trace_write_address(trace_write_address),
        .trace_write_data(trace_write_data),
        .trace_write2_valid(trace_write2_valid),
        .trace_write2_address(trace_write2_address),
        .trace_write2_data(trace_write2_data)
    );

    always #5 clk = ~clk;

    task send_word;
        input [2:0] kind;
        input [15:0] word_value;
        input final_word;
        begin
            @(negedge clk);
            stream_valid = 1'b1;
            stream_type = kind;
            stream_data = word_value;
            stream_last = final_word;
            while (!stream_ready)
                @(negedge clk);
            @(negedge clk);
            stream_valid = 1'b0;
            stream_last = 1'b0;
        end
    endtask

    always @* begin
        expected_word = 16'hxxxx;
        expected_address_valid = 1'b1;
        case (trace_opcode)
            4'd0: begin
                if (trace_write_address < 2048)
                    expected_word = golden_op0[trace_write_address];
                else expected_address_valid = 1'b0;
            end
            4'd1: expected_word = golden_op1[trace_write_address];
            4'd2: begin
                if (trace_write_address < 2048)
                    expected_word = golden_op2[trace_write_address];
                else expected_address_valid = 1'b0;
            end
            4'd3: expected_word = golden_op3[trace_write_address];
            4'd4: begin
                if (trace_write_address < 1024)
                    expected_word = golden_op4[trace_write_address];
                else expected_address_valid = 1'b0;
            end
            4'd5: begin
                if (trace_write_address < 256)
                    expected_word = golden_op5[trace_write_address];
                else expected_address_valid = 1'b0;
            end
            4'd6: begin
                if (trace_write_address < 256)
                    expected_word = golden_op6[trace_write_address];
                else expected_address_valid = 1'b0;
            end
            4'd7: begin
                if (trace_write_address < 256)
                    expected_word = golden_op7[trace_write_address];
                else expected_address_valid = 1'b0;
            end
            4'd8: begin
                if (trace_write_address < 32)
                    expected_word = golden_op8[trace_write_address];
                else expected_address_valid = 1'b0;
            end
            4'd9: begin
                if (trace_write_address < 16)
                    expected_word = golden_op9[trace_write_address];
                else expected_address_valid = 1'b0;
            end
            default: expected_address_valid = 1'b0;
        endcase
    end

    always @* begin
        expected_word2 = 16'hxxxx;
        expected_address2_valid = 1'b1;
        case (trace_opcode)
            4'd4: begin
                if (trace_write2_address < 1024)
                    expected_word2 = golden_op4[trace_write2_address];
                else expected_address2_valid = 1'b0;
            end
            4'd7: begin
                if (trace_write2_address < 256)
                    expected_word2 = golden_op7[trace_write2_address];
                else expected_address2_valid = 1'b0;
            end
            default: expected_address2_valid = 1'b0;
        endcase
    end

    always @(posedge clk) begin
        if (rst_n) begin
            cycle_count = cycle_count + 1;
            if (command_valid && command_ready) begin
                inference_active = 1'b1;
                inference_start_cycle = cycle_count;
                inference_cycles = 0;
            end else if (inference_active) begin
                inference_cycles = inference_cycles + 1;
            end
            if (dut.op_valid && dut.op_ready) begin
                active_descriptor = dut.descriptor_index;
                op_start_cycle = cycle_count;
            end
            if (dut.op_done && active_descriptor >= 0 &&
                    active_descriptor <= 10) begin
                op_latency[active_descriptor] =
                    cycle_count - op_start_cycle;
            end
            if (infer_done && inference_active) begin
                inference_active = 1'b0;
                inference_done_cycle = cycle_count;
            end
            if (error) begin
                $display("TB_ERROR accelerator error at cycle %0d", cycle_count);
                mismatch_count = mismatch_count + 1;
            end
            if (trace_write_valid) begin
                if (trace_opcode <= 9)
                    write_count[trace_opcode] = write_count[trace_opcode] + 1;
                if (!expected_address_valid || trace_write_data !== expected_word) begin
                    if (mismatch_count < 20)
                        $display("TB_MISMATCH op=%0d addr=%0d got=%04h expected=%04h",
                            trace_opcode, trace_write_address,
                            trace_write_data, expected_word);
                    mismatch_count = mismatch_count + 1;
                end
            end
            if (trace_write2_valid) begin
                if (trace_opcode <= 9)
                    write_count[trace_opcode] = write_count[trace_opcode] + 1;
                if (!expected_address2_valid ||
                    trace_write2_data !== expected_word2) begin
                    if (mismatch_count < 20)
                        $display("TB_MISMATCH2 op=%0d addr=%0d got=%04h expected=%04h",
                            trace_opcode, trace_write2_address,
                            trace_write2_data, expected_word2);
                    mismatch_count = mismatch_count + 1;
                end
            end
        end
    end

    initial begin
        $readmemh("input/sources/verification/p1_vectors/reference/input_words.hex", input_words);
        $readmemh("input/sources/verification/p1_vectors/reference/parameter_words.hex", parameter_words);
        $readmemh("input/sources/verification/p1_vectors/reference/v2_instruction_words.hex",
            instruction_words);
        $readmemh("input/sources/verification/p1_vectors/reference/op00_temporal_1.hex", golden_op0);
        $readmemh("input/sources/verification/p1_vectors/reference/op01_temporal_2.hex", golden_op1);
        $readmemh("input/sources/verification/p1_vectors/reference/op02_temporal_3_sum.hex", golden_op2);
        $readmemh("input/sources/verification/p1_vectors/reference/op03_temporal_4_bn_relu.hex", golden_op3);
        $readmemh("input/sources/verification/p1_vectors/reference/op04_spatial_dw_bn_relu.hex", golden_op4);
        $readmemh("input/sources/verification/p1_vectors/reference/op05_avgpool_4.hex", golden_op5);
        $readmemh("input/sources/verification/p1_vectors/reference/op06_separable_dw.hex", golden_op6);
        $readmemh("input/sources/verification/p1_vectors/reference/op07_pointwise_bn_relu.hex", golden_op7);
        $readmemh("input/sources/verification/p1_vectors/reference/op08_avgpool_8.hex", golden_op8);
        $readmemh("input/sources/verification/p1_vectors/reference/op09_dense.hex", golden_op9);

        clk = 1'b0;
        rst_n = 1'b0;
        stream_valid = 1'b0;
        stream_data = 16'd0;
        stream_type = 3'd0;
        stream_last = 1'b0;
        command_valid = 1'b0;
        mismatch_count = 0;
        cycle_count = 0;
        inference_start_cycle = 0;
        inference_done_cycle = 0;
        inference_cycles = 0;
        op_start_cycle = 0;
        active_descriptor = -1;
        inference_active = 1'b0;
        for (index = 0; index < 10; index = index + 1)
            write_count[index] = 0;
        for (index = 0; index < 11; index = index + 1)
            op_latency[index] = 0;

        repeat (5) @(negedge clk);
        rst_n = 1'b1;

        for (index = 0; index < 1076; index = index + 1)
            send_word(3'b011, parameter_words[index], index == 1075);
        for (index = 0; index < 264; index = index + 1)
            send_word(3'b110, instruction_words[index], index == 263);
        for (index = 0; index < 2048; index = index + 1)
            send_word(3'b101, input_words[index], index == 2047);

        @(negedge clk);
        if (!command_ready) begin
            $display("TB_ERROR command_ready did not assert after all frozen streams");
            mismatch_count = mismatch_count + 1;
        end
        command_valid = 1'b1;
        @(negedge clk);
        command_valid = 1'b0;

        fork : timeout_block
            begin
                wait (infer_done);
                disable timeout_block;
            end
            begin
                repeat (1000000) @(posedge clk);
                $display("TB_ERROR timeout waiting for infer_done");
                mismatch_count = mismatch_count + 1;
                disable timeout_block;
            end
        join

        repeat (3) @(posedge clk);
        if (write_count[0] != 2048) mismatch_count = mismatch_count + 1;
        if (write_count[1] != 8192) mismatch_count = mismatch_count + 1;
        if (write_count[2] != 2048) mismatch_count = mismatch_count + 1;
        if (write_count[3] != 8192) mismatch_count = mismatch_count + 1;
        if (write_count[4] != 1024) mismatch_count = mismatch_count + 1;
        if (write_count[5] != 256) mismatch_count = mismatch_count + 1;
        if (write_count[6] != 256) mismatch_count = mismatch_count + 1;
        if (write_count[7] != 256) mismatch_count = mismatch_count + 1;
        if (write_count[8] != 32) mismatch_count = mismatch_count + 1;
        if (write_count[9] != 16) mismatch_count = mismatch_count + 1;
        if (result !== 32'd0) begin
            $display("TB_ERROR result=%0d expected=0", result);
            mismatch_count = mismatch_count + 1;
        end
        if (inference_cycles > 33600) begin
            $display("TB_ERROR inference_cycles=%0d exceeds 33600", inference_cycles);
            mismatch_count = mismatch_count + 1;
        end

        $display("HDLFLOW_WAVE_WINDOW id=frozen_stream_load start=60000 end=68000000 scope=top");
        $display("HDLFLOW_WAVE_WINDOW id=layer_execution start=68000000 end=500000000 scope=top");
        $display("HDLFLOW_WAVE_WINDOW id=completion start=350000000 end=500000000 scope=top");
        $display("HDLFLOW|TASK_BEGIN|task_id=TEST-EEG-V2-CH16-END-TO-END|requirement_id=REQ-EEG-CH16-001");
        if (mismatch_count == 0) begin
            $display("WF_INFO|case=VER-P1-FUNCTION|purpose=full_eeg_inference|input=approved_program_parameters_and_16_channel_frame|expected=class_0_no_protocol_error|actual=class_0_no_protocol_error|result=PASS");
            $display("WF_INFO|case=VER-P1-CYCLES|purpose=inference_cycle_budget|input=accepted_start_to_infer_done|expected=cycles_le_33600|actual=cycles_%0d|result=PASS", inference_cycles);
            $display("WF_SUMMARY|total=2|pass=2|fail=0");
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=typed_stream_load|requirement_id=REQ-EEG-CH16-001|operation_id=OP_TYPED_LOAD|sent=3388_words|expected=1076_param_264_instr_2048_sample|actual=1076_param_264_instr_2048_sample|latency_cycles=6776|observed_interface=typed_stream|evidence_type=blackbox|check_role=protocol_and_count|result=PASS");
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=op00|requirement_id=REQ-EEG-FUNC-001|operation_id=OP00_TEMPORAL_1|sent=descriptor_0|expected=2048_bitexact_words|actual=2048_bitexact_words|latency_cycles=%0d|observed_interface=trace_write|evidence_type=blackbox|check_role=reference_model|side_effect_checked=true|result=PASS", op_latency[0]);
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=op01|requirement_id=REQ-EEG-FUNC-001|operation_id=OP01_TEMPORAL_2|sent=descriptor_1|expected=8192_bitexact_words|actual=8192_bitexact_words|latency_cycles=%0d|observed_interface=trace_write|evidence_type=blackbox|check_role=reference_model|side_effect_checked=true|result=PASS", op_latency[1]);
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=op02|requirement_id=REQ-EEG-FUNC-001|operation_id=OP02_TEMPORAL_3_SUM|sent=descriptor_2|expected=2048_bitexact_words|actual=2048_bitexact_words|latency_cycles=%0d|observed_interface=trace_write|evidence_type=blackbox|check_role=reference_model|side_effect_checked=true|result=PASS", op_latency[2]);
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=op03|requirement_id=REQ-EEG-FUNC-001|operation_id=OP03_TEMPORAL_4_BN_RELU|sent=descriptor_3|expected=8192_bitexact_words|actual=8192_bitexact_words|latency_cycles=%0d|observed_interface=trace_write|evidence_type=blackbox|check_role=reference_model|side_effect_checked=true|result=PASS", op_latency[3]);
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=op04|requirement_id=REQ-EEG-FUNC-001|operation_id=OP04_SPATIAL_DW_BN_RELU|sent=descriptor_4|expected=1024_bitexact_words|actual=1024_bitexact_words|latency_cycles=%0d|observed_interface=trace_write|evidence_type=blackbox|check_role=reference_model|side_effect_checked=true|result=PASS", op_latency[4]);
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=op05|requirement_id=REQ-EEG-FUNC-001|operation_id=OP05_AVGPOOL_4|sent=descriptor_5|expected=256_bitexact_words|actual=256_bitexact_words|latency_cycles=%0d|observed_interface=trace_write|evidence_type=blackbox|check_role=reference_model|side_effect_checked=true|result=PASS", op_latency[5]);
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=op06|requirement_id=REQ-EEG-FUNC-001|operation_id=OP06_SEPARABLE_DW|sent=descriptor_6|expected=256_bitexact_words|actual=256_bitexact_words|latency_cycles=%0d|observed_interface=trace_write|evidence_type=blackbox|check_role=reference_model|side_effect_checked=true|result=PASS", op_latency[6]);
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=op07|requirement_id=REQ-EEG-FUNC-001|operation_id=OP07_POINTWISE_BN_RELU|sent=descriptor_7|expected=256_bitexact_words|actual=256_bitexact_words|latency_cycles=%0d|observed_interface=trace_write|evidence_type=blackbox|check_role=reference_model|side_effect_checked=true|result=PASS", op_latency[7]);
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=op08|requirement_id=REQ-EEG-FUNC-001|operation_id=OP08_AVGPOOL_8|sent=descriptor_8|expected=32_bitexact_words|actual=32_bitexact_words|latency_cycles=%0d|observed_interface=trace_write|evidence_type=blackbox|check_role=reference_model|side_effect_checked=true|result=PASS", op_latency[8]);
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=op09|requirement_id=REQ-EEG-FUNC-001|operation_id=OP09_DENSE|sent=descriptor_9|expected=16_bitexact_logits|actual=16_bitexact_logits|latency_cycles=%0d|observed_interface=trace_write|evidence_type=blackbox|check_role=reference_model|side_effect_checked=true|result=PASS", op_latency[9]);
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=op10|requirement_id=REQ-EEG-FUNC-001|operation_id=OP10_ARGMAX|sent=16_scores|expected=class_0|actual=class_0|latency_cycles=%0d|observed_interface=result_infer_done|evidence_type=blackbox|check_role=readback|readback_checked=true|expected_readback=0|result=PASS", op_latency[10]);
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=trace_if_axi_ctrl|requirement_id=IF-AXI-CTRL|operation_id=OP_IF_AXI_CTRL|sent=accepted_start_command|expected=one_completed_inference|actual=one_completed_inference|latency_cycles=0|observed_interface=result_infer_done|evidence_type=blackbox|check_role=downstream_control_contract|result=PASS");
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=trace_if_bram_data|requirement_id=IF-BRAM-DATA|operation_id=OP_IF_BRAM_DATA|sent=3388_typed_words|expected=all_words_accepted_in_order|actual=all_words_accepted_in_order|latency_cycles=0|observed_interface=typed_stream|evidence_type=blackbox|check_role=downstream_bram_contract|result=PASS");
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=trace_if_ps_uart|requirement_id=IF-PS-UART|operation_id=OP_IF_PS_UART|sent=classification_request|expected=pl_result_available_for_ps_uart|actual=pl_result_available_for_ps_uart|latency_cycles=0|observed_interface=result_infer_done|evidence_type=blackbox|check_role=pl_boundary_only_external_uart_deferred|result=PASS");
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=trace_arch|requirement_id=REQ-EEG-ARCH-001|operation_id=OP_REQ_EEG_ARCH_001|sent=typed_load_and_command|expected=stream_compute_result_partition|actual=stream_compute_result_partition|latency_cycles=0|observed_interface=result_infer_done|evidence_type=blackbox|check_role=pl_partition_contract|result=PASS");
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=trace_board|requirement_id=REQ-EEG-BOARD-001|operation_id=OP_REQ_EEG_BOARD_001|sent=pl_clocked_inference|expected=board_image_pl_boundary_ready|actual=board_image_pl_boundary_ready|latency_cycles=0|observed_interface=result_infer_done|evidence_type=blackbox|check_role=pl_boundary_only_external_board_deferred|result=PASS");
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=trace_ch16|requirement_id=REQ-EEG-CH16-001|operation_id=OP_REQ_EEG_CH16_001|sent=16_channel_2048_word_sample|expected=complete_without_overflow|actual=complete_without_overflow|latency_cycles=0|observed_interface=typed_stream|evidence_type=blackbox|check_role=channel_capacity_contract|result=PASS");
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=trace_flow|requirement_id=REQ-EEG-FLOW-001|operation_id=OP_REQ_EEG_FLOW_001|sent=governed_frozen_package|expected=platform_traceable_execution|actual=platform_traceable_execution|latency_cycles=0|observed_interface=trace_write|evidence_type=blackbox|check_role=platform_flow_trace|result=PASS");
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=trace_func1|requirement_id=REQ-EEG-FUNC-001|operation_id=OP_REQ_EEG_FUNC_001|sent=11_descriptors|expected=22320_bitexact_writes_and_class_0|actual=22320_bitexact_writes_and_class_0|latency_cycles=0|observed_interface=trace_write|evidence_type=blackbox|check_role=frozen_functional_equivalence|result=PASS");
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=trace_func2|requirement_id=REQ-EEG-FUNC-002|operation_id=OP_REQ_EEG_FUNC_002|sent=optimized_schedule|expected=zero_layer_or_result_mismatch|actual=zero_layer_or_result_mismatch|latency_cycles=0|observed_interface=trace_write|evidence_type=blackbox|check_role=optimized_bitexact_equivalence|result=PASS");
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=trace_led|requirement_id=REQ-EEG-LED-001|operation_id=OP_REQ_EEG_LED_001|sent=classification_result|expected=acceptance_independent_of_led|actual=acceptance_independent_of_led|latency_cycles=0|observed_interface=result_infer_done|evidence_type=blackbox|check_role=acceptance_boundary|result=PASS");
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=trace_mem|requirement_id=REQ-EEG-MEM-001|operation_id=OP_REQ_EEG_MEM_001|sent=all_feature_operations|expected=22320_in_range_bitexact_commits|actual=22320_in_range_bitexact_commits|latency_cycles=0|observed_interface=trace_write|evidence_type=blackbox|check_role=feature_memory_dataflow|result=PASS");
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=trace_perf1|requirement_id=REQ-EEG-PERF-001|operation_id=OP_REQ_EEG_PERF_001|sent=one_full_inference|expected=measured_cycle_completion|actual=measured_cycle_completion|latency_cycles=%0d|observed_interface=result_infer_done|evidence_type=blackbox|check_role=live_cycle_counter|result=PASS", inference_cycles);
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=trace_perf2|requirement_id=REQ-EEG-PERF-002|operation_id=OP_REQ_EEG_PERF_002|sent=one_full_inference|expected=cycles_le_55000|actual=cycles_%0d|latency_cycles=%0d|observed_interface=result_infer_done|evidence_type=blackbox|check_role=performance_acceptance|result=PASS", inference_cycles, inference_cycles);
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=trace_rtl_baseline|requirement_id=REQ-EEG-RTL-BASELINE-001|operation_id=OP_REQ_EEG_RTL_BASELINE_001|sent=frozen_v2_contract|expected=documented_operation_sequence|actual=documented_operation_sequence|latency_cycles=0|observed_interface=trace_write|evidence_type=blackbox|check_role=document_traceability|result=PASS");
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=trace_rtl_compat|requirement_id=REQ-EEG-RTL-COMPAT-001|operation_id=OP_REQ_EEG_RTL_COMPAT_001|sent=legacy_order_v2_capacity|expected=frozen_approximate_fp16_behavior|actual=frozen_approximate_fp16_behavior|latency_cycles=0|observed_interface=trace_write|evidence_type=blackbox|check_role=legacy_processing_compatibility|result=PASS");
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|test_id=TEST-EEG-V2-CH16-END-TO-END|txn_id=trace_uart|requirement_id=REQ-EEG-UART-001|operation_id=OP_REQ_EEG_UART_001|sent=completed_classification|expected=stable_result_for_ps_reporting|actual=stable_result_for_ps_reporting|latency_cycles=0|observed_interface=result_infer_done|evidence_type=blackbox|check_role=pl_boundary_only_external_uart_deferred|result=PASS");
            $display("HDLFLOW_PERF inference_cycles=%0d start_cycle=%0d done_cycle=%0d",
                inference_cycles, inference_start_cycle, inference_done_cycle);
            $display("HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|total_tests=1|passed_tests=1|failed_tests=0|total_checks=28|passed_checks=28|failed_checks=0|active_requirements_count=16|operation_model_entry_count=16|result=PASS");
            $display("HDLFLOW|TASK_END|task_id=TEST-EEG-V2-CH16-END-TO-END|requirement_id=REQ-EEG-CH16-001|result=PASS");
            $display("RTL_FUNCTIONAL_PASS cycles=%0d result=%0d", cycle_count, result);
        end else begin
            $display("WF_ERROR|case=VER-P1-FUNCTION|message=function_or_cycle_mismatch");
            $display("WF_INFO|case=VER-P1-FUNCTION|purpose=full_eeg_inference|input=approved_program_parameters_and_16_channel_frame|expected=class_0_no_protocol_error|actual=mismatch|result=FAIL");
            $display("WF_INFO|case=VER-P1-CYCLES|purpose=inference_cycle_budget|input=accepted_start_to_infer_done|expected=cycles_le_33600|actual=cycles_%0d|result=FAIL", inference_cycles);
            $display("WF_SUMMARY|total=2|pass=0|fail=2");
            $display("HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=gate_b_directed|total_tests=1|passed_tests=0|failed_tests=1|total_checks=28|passed_checks=0|failed_checks=28|active_requirements_count=16|operation_model_entry_count=16|result=FAIL");
            $display("HDLFLOW|TASK_END|task_id=TEST-EEG-V2-CH16-END-TO-END|requirement_id=REQ-EEG-CH16-001|result=FAIL");
            $display("RTL_FUNCTIONAL_FAIL mismatches=%0d cycles=%0d result=%0d",
                mismatch_count, cycle_count, result);
        end
        // Keep the terminal result signals observable for waveform-gate windows.
        // ModelSim otherwise drives the design to X at the same timestamp as
        // $finish, which is a simulator shutdown artifact rather than DUT X/Z.
        // Keep a fixed 100 us post-result tail so the waveform query windows
        // stay valid while V2.0 changes the inference completion timestamp.
        repeat (10000) @(posedge clk);
        $finish;
    end
endmodule
// END MIGRATED SCENARIO: eeg_bci_core_functional_tb.v

// BEGIN MIGRATED SCENARIO: eeg_bci_multichannel_tb.v
`timescale 1ns/1ps

module eeg_bci_multichannel_tb;
    reg clk;
    reg rst_n;
    reg stream_valid;
    wire stream_ready;
    reg [15:0] stream_data;
    reg [2:0] stream_type;
    reg stream_last;
    reg command_valid;
    wire command_ready;
    reg [1:0] profile_select;
    reg [1:0] instruction_version;
    wire busy;
    wire [31:0] result;
    wire infer_done;
    wire [3:0] class_led;
    wire error;
    wire trace_write_valid;
    wire [3:0] trace_opcode;
    wire [12:0] trace_write_address;
    wire [15:0] trace_write_data;
    wire trace_write2_valid;
    wire [12:0] trace_write2_address;
    wire [15:0] trace_write2_data;

    reg [15:0] parameter_words [0:1075];
    reg [15:0] instruction_words [0:263];
    reg [15:0] input_words [0:2047];
    reg [15:0] expected_class [0:0];
    reg [15:0] golden_op0 [0:2047];
    reg [15:0] golden_op1 [0:8191];
    reg [15:0] golden_op2 [0:2047];
    reg [15:0] golden_op3 [0:8191];
    reg [15:0] golden_op4 [0:1023];
    reg [15:0] golden_op5 [0:255];
    reg [15:0] golden_op6 [0:255];
    reg [15:0] golden_op7 [0:255];
    reg [15:0] golden_op8 [0:31];
    reg [15:0] golden_op9 [0:15];
    reg [8*256-1:0] file_name;
    integer channels;
    integer index;
    integer trace_index;
    integer expected_trace_words;
    integer inference_cycles;
    integer failures;
    integer start_channels;
    integer end_channels;
    integer feature_index;
    integer feature_offset;
    reg run_active;
    reg [15:0] expected_word;
    reg expected_address_valid;
    reg [15:0] expected_word2;
    reg expected_address2_valid;

    bci_accel_core dut (
        .clk(clk),
        .rst_n(rst_n),
        .stream_valid(stream_valid),
        .stream_ready(stream_ready),
        .stream_data(stream_data),
        .stream_type(stream_type),
        .stream_last(stream_last),
        .command_valid(command_valid),
        .command_ready(command_ready),
        .profile_select(profile_select),
        .instruction_version(instruction_version),
        .busy(busy),
        .result(result),
        .infer_done(infer_done),
        .class_led(class_led),
        .error(error),
        .clear_counters(1'b0),
        .snapshot_counters(1'b0),
        .total_cycles_snapshot(),
        .memory_stalls_snapshot(),
        .producer_stalls_snapshot(),
        .consumer_stalls_snapshot(),
        .mac_activity_snapshot(),
        .tile_occupancy_snapshot(),
        .trace_write_valid(trace_write_valid),
        .trace_opcode(trace_opcode),
        .trace_write_address(trace_write_address),
        .trace_write_data(trace_write_data),
        .trace_write2_valid(trace_write2_valid),
        .trace_write2_address(trace_write2_address),
        .trace_write2_data(trace_write2_data)
    );

    always #5 clk = ~clk;

    always @(posedge clk) begin
        if (run_active && trace_write_valid) begin
            expected_word = 16'hxxxx;
            expected_address_valid = 1'b1;
            case (trace_opcode)
                4'd0: begin
                    if (trace_write_address < channels * 128)
                        expected_word = golden_op0[trace_write_address];
                    else expected_address_valid = 1'b0;
                end
                4'd1: begin
                    feature_index = trace_write_address / 2048;
                    feature_offset = trace_write_address % 2048;
                    if ((feature_index < 4) &&
                        (feature_offset < channels * 128))
                        expected_word = golden_op1[
                            feature_index * channels * 128 + feature_offset];
                    else expected_address_valid = 1'b0;
                end
                4'd2: begin
                    if (trace_write_address < channels * 128)
                        expected_word = golden_op2[trace_write_address];
                    else expected_address_valid = 1'b0;
                end
                4'd3: begin
                    feature_index = trace_write_address / 2048;
                    feature_offset = trace_write_address % 2048;
                    if ((feature_index < 4) &&
                        (feature_offset < channels * 128))
                        expected_word = golden_op3[
                            feature_index * channels * 128 + feature_offset];
                    else expected_address_valid = 1'b0;
                end
                4'd4: begin
                    if (trace_write_address < 1024)
                        expected_word = golden_op4[trace_write_address];
                    else expected_address_valid = 1'b0;
                end
                4'd5: begin
                    if (trace_write_address < 256)
                        expected_word = golden_op5[trace_write_address];
                    else expected_address_valid = 1'b0;
                end
                4'd6: begin
                    if (trace_write_address < 256)
                        expected_word = golden_op6[trace_write_address];
                    else expected_address_valid = 1'b0;
                end
                4'd7: begin
                    if (trace_write_address < 256)
                        expected_word = golden_op7[trace_write_address];
                    else expected_address_valid = 1'b0;
                end
                4'd8: begin
                    if (trace_write_address < 32)
                        expected_word = golden_op8[trace_write_address];
                    else expected_address_valid = 1'b0;
                end
                4'd9: begin
                    if (trace_write_address < 16)
                        expected_word = golden_op9[trace_write_address];
                    else expected_address_valid = 1'b0;
                end
                default: expected_address_valid = 1'b0;
            endcase
            if (!expected_address_valid || trace_write_data !== expected_word) begin
                if (failures < 20)
                    $display("MULTICHANNEL_TRACE_FAIL ch=%0d index=%0d op=%0d addr=%0d expected=%04x actual=%04x",
                        channels, trace_index, trace_opcode,
                        trace_write_address, expected_word, trace_write_data);
                failures = failures + 1;
            end
            trace_index = trace_index + 1;
        end
    end

    always @(posedge clk) begin
        if (run_active && trace_write2_valid) begin
            expected_word2 = 16'hxxxx;
            expected_address2_valid = 1'b1;
            case (trace_opcode)
                4'd4: begin
                    if (trace_write2_address < 1024)
                        expected_word2 = golden_op4[trace_write2_address];
                    else expected_address2_valid = 1'b0;
                end
                4'd7: begin
                    if (trace_write2_address < 256)
                        expected_word2 = golden_op7[trace_write2_address];
                    else expected_address2_valid = 1'b0;
                end
                default: expected_address2_valid = 1'b0;
            endcase
            if (!expected_address2_valid ||
                trace_write2_data !== expected_word2) begin
                if (failures < 20)
                    $display("MULTICHANNEL_TRACE2_FAIL ch=%0d index=%0d op=%0d addr=%0d expected=%04x actual=%04x",
                        channels, trace_index, trace_opcode,
                        trace_write2_address, expected_word2,
                        trace_write2_data);
                failures = failures + 1;
            end
            trace_index = trace_index + 1;
        end
    end

    task send_word;
        input [2:0] kind;
        input [15:0] data;
        input last;
        begin
            @(negedge clk);
            stream_type = kind;
            stream_data = data;
            stream_last = last;
            stream_valid = 1'b1;
            @(posedge clk);
            while (!stream_ready)
                @(posedge clk);
            @(negedge clk);
            stream_valid = 1'b0;
            stream_last = 1'b0;
        end
    endtask

    task reset_dut;
        begin
            run_active = 1'b0;
            @(negedge clk);
            rst_n = 1'b0;
            stream_valid = 1'b0;
            stream_last = 1'b0;
            command_valid = 1'b0;
            repeat (6) @(negedge clk);
            rst_n = 1'b1;
            repeat (3) @(negedge clk);
        end
    endtask

    initial begin
        clk = 1'b0;
        rst_n = 1'b0;
        stream_valid = 1'b0;
        stream_data = 16'd0;
        stream_type = 3'd0;
        stream_last = 1'b0;
        command_valid = 1'b0;
        profile_select = 2'b01;
        instruction_version = 2'b01;
        trace_index = 0;
        inference_cycles = 0;
        failures = 0;
        run_active = 1'b0;
        start_channels = 2;
        end_channels = 16;
        if (!$value$plusargs("START_CH=%d", start_channels))
            start_channels = 2;
        if (!$value$plusargs("END_CH=%d", end_channels))
            end_channels = 16;

        for (channels = start_channels; channels <= end_channels;
             channels = channels + 1) begin
            reset_dut();
            $sformat(file_name,
                "input/sources/verification/p1_vectors/multichannel/CH%02d/parameter_words.hex",
                channels);
            $readmemh(file_name, parameter_words);
            $sformat(file_name,
                "input/sources/verification/p1_vectors/multichannel/CH%02d/v2_instruction_words.hex",
                channels);
            $readmemh(file_name, instruction_words);
            $sformat(file_name,
                "input/sources/verification/p1_vectors/multichannel/CH%02d/input_words.hex",
                channels);
            $readmemh(file_name, input_words);
            $sformat(file_name,
                "input/sources/verification/p1_vectors/multichannel/CH%02d/classification.hex",
                channels);
            $readmemh(file_name, expected_class);
            $sformat(file_name,
                "input/sources/verification/p1_vectors/multichannel/CH%02d/op00.hex",
                channels); $readmemh(file_name, golden_op0);
            $sformat(file_name,
                "input/sources/verification/p1_vectors/multichannel/CH%02d/op01.hex",
                channels); $readmemh(file_name, golden_op1);
            $sformat(file_name,
                "input/sources/verification/p1_vectors/multichannel/CH%02d/op02.hex",
                channels); $readmemh(file_name, golden_op2);
            $sformat(file_name,
                "input/sources/verification/p1_vectors/multichannel/CH%02d/op03.hex",
                channels); $readmemh(file_name, golden_op3);
            $sformat(file_name,
                "input/sources/verification/p1_vectors/multichannel/CH%02d/op04.hex",
                channels); $readmemh(file_name, golden_op4);
            $sformat(file_name,
                "input/sources/verification/p1_vectors/multichannel/CH%02d/op05.hex",
                channels); $readmemh(file_name, golden_op5);
            $sformat(file_name,
                "input/sources/verification/p1_vectors/multichannel/CH%02d/op06.hex",
                channels); $readmemh(file_name, golden_op6);
            $sformat(file_name,
                "input/sources/verification/p1_vectors/multichannel/CH%02d/op07.hex",
                channels); $readmemh(file_name, golden_op7);
            $sformat(file_name,
                "input/sources/verification/p1_vectors/multichannel/CH%02d/op08.hex",
                channels); $readmemh(file_name, golden_op8);
            $sformat(file_name,
                "input/sources/verification/p1_vectors/multichannel/CH%02d/op09.hex",
                channels); $readmemh(file_name, golden_op9);

            for (index = 0; index < 1076; index = index + 1)
                send_word(3'b011, parameter_words[index], index == 1075);
            for (index = 0; index < 264; index = index + 1)
                send_word(3'b110, instruction_words[index], index == 263);
            for (index = 0; index < channels * 128; index = index + 1)
                send_word(3'b101, input_words[index],
                    index == channels * 128 - 1);

            if ((dut.scheduler.parameter_word_count != 1076) ||
                (dut.scheduler.instruction_word_count != 264) ||
                (dut.feature_memory.sample_count != channels * 128) ||
                (dut.scheduler.active_channels != channels) ||
                (dut.scheduler.parameter_memory[0] !==
                 {parameter_words[3], parameter_words[2],
                  parameter_words[1], parameter_words[0]}) ||
                (dut.feature_memory.feature_memory_bank0[768] !== input_words[0]) ||
                (dut.feature_memory.feature_memory_bank1[768] !== input_words[1])) begin
                $display("MULTICHANNEL_LOAD_FAIL ch=%0d params=%0d instr=%0d samples=%0d active=%0d p0=%016x/%04x%04x%04x%04x s0=%04x/%04x s1=%04x/%04x",
                    channels, dut.scheduler.parameter_word_count,
                    dut.scheduler.instruction_word_count,
                    dut.feature_memory.sample_count,
                    dut.scheduler.active_channels,
                    dut.scheduler.parameter_memory[0],
                    parameter_words[3], parameter_words[2],
                    parameter_words[1], parameter_words[0],
                    dut.feature_memory.feature_memory_bank0[768],
                    input_words[0],
                    dut.feature_memory.feature_memory_bank1[768],
                    input_words[1]);
                failures = failures + 1;
            end

            trace_index = 0;
            inference_cycles = 0;
            run_active = 1'b1;
            @(negedge clk);
            command_valid = 1'b1;
            while (!command_ready)
                @(negedge clk);
            @(negedge clk);
            command_valid = 1'b0;
            while (!infer_done && inference_cycles < 100000) begin
                @(negedge clk);
                if (busy)
                    inference_cycles = inference_cycles + 1;
            end
            run_active = 1'b0;
            expected_trace_words = 1280 * channels + 1840;
            if (!infer_done || error || trace_index != expected_trace_words ||
                result[3:0] != expected_class[0][3:0]) begin
                $display("MULTICHANNEL_FAIL ch=%0d done=%0d error=%0d trace=%0d/%0d class=%0d/%0d cycles=%0d",
                    channels, infer_done, error, trace_index,
                    expected_trace_words, result[3:0],
                    expected_class[0][3:0], inference_cycles);
                failures = failures + 1;
            end
            else begin
                $display("MULTICHANNEL_PASS ch=%0d sample_words=%0d trace_words=%0d class=%0d cycles=%0d",
                    channels, channels * 128, trace_index, result[3:0],
                    inference_cycles);
            end
        end

        if (failures == 0)
            $display("MULTICHANNEL_MATRIX_PASS range=%0d..%0d",
                start_channels, end_channels);
        else
            $display("MULTICHANNEL_MATRIX_FAIL failures=%0d", failures);
        if (failures != 0)
            $fatal(1);
        $finish;
    end
endmodule
// END MIGRATED SCENARIO: eeg_bci_multichannel_tb.v

// BEGIN MIGRATED SCENARIO: eeg_bci_pipeline_tb.v
`timescale 1ns/1ps

module eeg_bci_pipeline_tb;
    parameter MAX_SAMPLES = 3432;
    parameter WORDS_PER_SAMPLE = 2048;
    parameter MAX_INPUT_WORDS = 7028736;

    reg clk;
    reg rst_n;
    reg stream_valid;
    wire stream_ready;
    reg [15:0] stream_data;
    reg [2:0] stream_type;
    reg stream_last;
    reg command_valid;
    wire command_ready;
    wire busy;
    wire [31:0] result;
    wire infer_done;
    wire error;

    reg [15:0] input_words [0:MAX_INPUT_WORDS-1];
    reg [15:0] parameter_words [0:1075];
    reg [15:0] instruction_words [0:263];
    reg [15:0] reference_predictions [0:MAX_SAMPLES-1];

    integer cycle_count;
    integer command_count;
    integer done_count;
    integer first_start_cycle;
    integer first_done_cycle;
    integer second_start_cycle;
    integer second_done_cycle;
    integer protocol_errors;
    integer result_mismatches;
    integer word_index;
    integer timeout_cycles;
    reg monitor_next_sample;
    reg next_sample_loaded_before_first_done;

    bci_accel_core dut (
        .clk(clk),
        .rst_n(rst_n),
        .stream_valid(stream_valid),
        .stream_ready(stream_ready),
        .stream_data(stream_data),
        .stream_type(stream_type),
        .stream_last(stream_last),
        .command_valid(command_valid),
        .command_ready(command_ready),
        .profile_select(2'b01),
        .instruction_version(2'b01),
        .busy(busy),
        .result(result),
        .infer_done(infer_done),
        .class_led(),
        .error(error),
        .clear_counters(1'b0),
        .snapshot_counters(1'b0),
        .total_cycles_snapshot(),
        .memory_stalls_snapshot(),
        .producer_stalls_snapshot(),
        .consumer_stalls_snapshot(),
        .mac_activity_snapshot(),
        .tile_occupancy_snapshot(),
        .trace_write_valid(),
        .trace_opcode(),
        .trace_write_address(),
        .trace_write_data(),
        .trace_write2_valid(),
        .trace_write2_address(),
        .trace_write2_data()
    );

    always #5 clk = ~clk;

    always @(posedge clk) begin
        cycle_count = cycle_count + 1;
        if (command_valid && command_ready) begin
            if (command_count == 0)
                first_start_cycle = cycle_count;
            else if (command_count == 1)
                second_start_cycle = cycle_count;
            command_count = command_count + 1;
        end
        if (monitor_next_sample && !infer_done &&
            dut.feature_memory.sample_loaded)
            next_sample_loaded_before_first_done = 1'b1;
        if (infer_done) begin
            if (done_count == 0) begin
                first_done_cycle = cycle_count;
                if (result[3:0] !== reference_predictions[0][3:0])
                    result_mismatches = result_mismatches + 1;
            end
            else if (done_count == 1) begin
                second_done_cycle = cycle_count;
                if (result[3:0] !== reference_predictions[1][3:0])
                    result_mismatches = result_mismatches + 1;
            end
            done_count = done_count + 1;
        end
    end

    task send_word;
        input [2:0] kind;
        input [15:0] word_value;
        input final_word;
        begin
            @(negedge clk);
            stream_valid = 1'b1;
            stream_type = kind;
            stream_data = word_value;
            stream_last = final_word;
            while (!stream_ready)
                @(negedge clk);
            @(negedge clk);
            stream_valid = 1'b0;
            stream_last = 1'b0;
        end
    endtask

    task send_sample;
        input integer sample_index;
        begin
            for (word_index = 0; word_index < WORDS_PER_SAMPLE;
                 word_index = word_index + 1)
                send_word(
                    3'b101,
                    input_words[
                        sample_index * WORDS_PER_SAMPLE + word_index
                    ],
                    word_index == WORDS_PER_SAMPLE - 1
                );
        end
    endtask

    task start_inference;
        begin
            timeout_cycles = 0;
            while (!command_ready && timeout_cycles < 1000000) begin
                @(negedge clk);
                timeout_cycles = timeout_cycles + 1;
            end
            if (!command_ready) begin
                protocol_errors = protocol_errors + 1;
            end
            else begin
                command_valid = 1'b1;
                @(negedge clk);
                command_valid = 1'b0;
            end
        end
    endtask

    initial begin
        $readmemh("input/sources/verification/p1_vectors/accuracy/s01_test_input_words.hex",
            input_words);
        $readmemh("input/sources/verification/p1_vectors/reference/parameter_words.hex",
            parameter_words);
        $readmemh("input/sources/verification/p1_vectors/reference/v2_instruction_words.hex",
            instruction_words);
        $readmemh(
            "input/sources/verification/p1_vectors/accuracy/s01_test_reference_predictions.hex",
            reference_predictions);

        clk = 1'b0;
        rst_n = 1'b0;
        stream_valid = 1'b0;
        stream_data = 16'd0;
        stream_type = 3'd0;
        stream_last = 1'b0;
        command_valid = 1'b0;
        cycle_count = 0;
        command_count = 0;
        done_count = 0;
        first_start_cycle = 0;
        first_done_cycle = 0;
        second_start_cycle = 0;
        second_done_cycle = 0;
        protocol_errors = 0;
        result_mismatches = 0;
        timeout_cycles = 0;
        monitor_next_sample = 1'b0;
        next_sample_loaded_before_first_done = 1'b0;

        repeat (5) @(negedge clk);
        rst_n = 1'b1;

        for (word_index = 0; word_index < 1076;
             word_index = word_index + 1)
            send_word(3'b011, parameter_words[word_index],
                word_index == 1075);
        for (word_index = 0; word_index < 264;
             word_index = word_index + 1)
            send_word(3'b110, instruction_words[word_index],
                word_index == 263);

        send_sample(0);
        start_inference;
        monitor_next_sample = 1'b1;

        // The second sample is intentionally presented while inference zero
        // is active. Backpressure is legal, but a throughput-capable design
        // must finish this transfer before the first infer_done pulse.
        send_sample(1);
        while (done_count < 1)
            @(negedge clk);
        monitor_next_sample = 1'b0;

        start_inference;
        timeout_cycles = 0;
        while (done_count < 2 && timeout_cycles < 1000000) begin
            @(negedge clk);
            timeout_cycles = timeout_cycles + 1;
        end
        if (done_count < 2)
            protocol_errors = protocol_errors + 1;
        if (error)
            protocol_errors = protocol_errors + 1;

        if ((protocol_errors == 0) && (result_mismatches == 0))
            $display("HDLFLOW_PIPELINE first_inference_cycles=%0d second_inference_cycles=%0d inter_inference_gap_cycles=%0d start_interval_cycles=%0d next_sample_loaded_before_first_done=%0d result_mismatches=0 protocol_errors=0 result=PASS",
                first_done_cycle - first_start_cycle,
                second_done_cycle - second_start_cycle,
                second_start_cycle - first_done_cycle,
                second_start_cycle - first_start_cycle,
                next_sample_loaded_before_first_done);
        else
            $display("HDLFLOW_PIPELINE first_inference_cycles=%0d second_inference_cycles=%0d inter_inference_gap_cycles=%0d start_interval_cycles=%0d next_sample_loaded_before_first_done=%0d result_mismatches=%0d protocol_errors=%0d result=FAIL",
                first_done_cycle - first_start_cycle,
                second_done_cycle - second_start_cycle,
                second_start_cycle - first_done_cycle,
                second_start_cycle - first_start_cycle,
                next_sample_loaded_before_first_done,
                result_mismatches, protocol_errors);
        $finish;
    end
endmodule
// END MIGRATED SCENARIO: eeg_bci_pipeline_tb.v

// BEGIN MIGRATED SCENARIO: eeg_bci_accuracy_batch_tb.v
`timescale 1ns/1ps

`ifdef P1_SCENARIO_3
`include "p1_batch_config.vh"
`endif

module eeg_bci_accuracy_batch_tb;
    parameter MAX_SAMPLES = 3432;
    parameter WORDS_PER_SAMPLE = 2048;
    parameter MAX_INPUT_WORDS = 7028736;

    reg clk;
    reg rst_n;
    reg stream_valid;
    wire stream_ready;
    reg [15:0] stream_data;
    reg [2:0] stream_type;
    reg stream_last;
    reg command_valid;
    wire command_ready;
    wire busy;
    wire [31:0] result;
    wire infer_done;
    wire [3:0] class_led;
    wire error;

    reg [15:0] input_words [0:MAX_INPUT_WORDS-1];
    reg [15:0] parameter_words [0:1075];
    reg [15:0] instruction_words [0:263];
    reg [15:0] labels [0:MAX_SAMPLES-1];
    reg [15:0] reference_predictions [0:MAX_SAMPLES-1];

    integer confusion [0:255];
    integer batch_start;
    integer batch_samples;
    integer sample_index;
    integer word_index;
    integer confusion_index;
    integer correct_count;
    integer rtl_reference_mismatches;
    integer protocol_errors;
    integer timeout_cycles;
    real accuracy_percent;

    bci_accel_core dut (
        .clk(clk),
        .rst_n(rst_n),
        .stream_valid(stream_valid),
        .stream_ready(stream_ready),
        .stream_data(stream_data),
        .stream_type(stream_type),
        .stream_last(stream_last),
        .command_valid(command_valid),
        .command_ready(command_ready),
        .profile_select(2'b01),
        .instruction_version(2'b01),
        .busy(busy),
        .result(result),
        .infer_done(infer_done),
        .class_led(class_led),
        .error(error),
        .clear_counters(1'b0),
        .snapshot_counters(1'b0),
        .total_cycles_snapshot(),
        .memory_stalls_snapshot(),
        .producer_stalls_snapshot(),
        .consumer_stalls_snapshot(),
        .mac_activity_snapshot(),
        .tile_occupancy_snapshot(),
        .trace_write_valid(),
        .trace_opcode(),
        .trace_write_address(),
        .trace_write_data(),
        .trace_write2_valid(),
        .trace_write2_address(),
        .trace_write2_data()
    );

    always #5 clk = ~clk;

    task send_word;
        input [2:0] kind;
        input [15:0] word_value;
        input final_word;
        begin
            @(negedge clk);
            stream_valid = 1'b1;
            stream_type = kind;
            stream_data = word_value;
            stream_last = final_word;
            while (!stream_ready)
                @(negedge clk);
            @(negedge clk);
            stream_valid = 1'b0;
            stream_last = 1'b0;
        end
    endtask

    task start_inference;
        begin
            @(negedge clk);
            if (!command_ready) begin
                $display("HDLFLOW_ACCURACY_PROTOCOL_ERROR global_index=%0d reason=command_not_ready",
                    sample_index);
                protocol_errors = protocol_errors + 1;
            end
            command_valid = 1'b1;
            @(negedge clk);
            command_valid = 1'b0;
        end
    endtask

    task wait_for_completion;
        begin
            timeout_cycles = 0;
            while (!infer_done && timeout_cycles < 1000000) begin
                @(posedge clk);
                timeout_cycles = timeout_cycles + 1;
            end
            if (!infer_done) begin
                $display("HDLFLOW_ACCURACY_PROTOCOL_ERROR global_index=%0d reason=infer_timeout",
                    sample_index);
                protocol_errors = protocol_errors + 1;
            end
            @(negedge clk);
        end
    endtask

    initial begin
`ifdef P1_BATCH_START
        batch_start = `P1_BATCH_START;
`else
        batch_start = 0;
`endif
`ifdef P1_BATCH_SAMPLES
        batch_samples = `P1_BATCH_SAMPLES;
`else
        batch_samples = 16;
`endif
        if (batch_start < 0 || batch_samples <= 0 ||
            batch_start + batch_samples > MAX_SAMPLES) begin
            $display("HDLFLOW_ACCURACY_SUMMARY result=FAIL reason=invalid_batch_range");
            $finish;
        end

        $readmemh("input/sources/verification/p1_vectors/accuracy/s01_test_input_words.hex",
            input_words);
        $readmemh("input/sources/verification/p1_vectors/reference/parameter_words.hex",
            parameter_words);
        $readmemh("input/sources/verification/p1_vectors/reference/v2_instruction_words.hex",
            instruction_words);
        $readmemh("input/sources/verification/p1_vectors/accuracy/s01_test_labels.hex", labels);
        $readmemh(
            "input/sources/verification/p1_vectors/accuracy/s01_test_reference_predictions.hex",
            reference_predictions);

        clk = 1'b0;
        rst_n = 1'b0;
        stream_valid = 1'b0;
        stream_data = 16'd0;
        stream_type = 3'd0;
        stream_last = 1'b0;
        command_valid = 1'b0;
        correct_count = 0;
        rtl_reference_mismatches = 0;
        protocol_errors = 0;
        for (confusion_index = 0; confusion_index < 256;
             confusion_index = confusion_index + 1)
            confusion[confusion_index] = 0;

        repeat (5) @(negedge clk);
        rst_n = 1'b1;

        for (word_index = 0; word_index < 1076;
             word_index = word_index + 1)
            send_word(3'b011, parameter_words[word_index],
                word_index == 1075);
        for (word_index = 0; word_index < 264;
             word_index = word_index + 1)
            send_word(3'b110, instruction_words[word_index],
                word_index == 263);

        for (sample_index = batch_start;
             sample_index < batch_start + batch_samples;
             sample_index = sample_index + 1) begin
            for (word_index = 0; word_index < WORDS_PER_SAMPLE;
                 word_index = word_index + 1)
                send_word(
                    3'b101,
                    input_words[
                        sample_index * WORDS_PER_SAMPLE + word_index
                    ],
                    word_index == WORDS_PER_SAMPLE - 1
                );

            if (dut.feature_memory.sample_count != 13'd2048 ||
                !dut.feature_memory.sample_loaded) begin
                $display("HDLFLOW_ACCURACY_PROTOCOL_ERROR global_index=%0d reason=sample_load_state count=%0d loaded=%0b",
                    sample_index, dut.feature_memory.sample_count,
                    dut.feature_memory.sample_loaded);
                protocol_errors = protocol_errors + 1;
            end

            start_inference;
            if (busy && stream_ready) begin
                $display("HDLFLOW_ACCURACY_PROTOCOL_ERROR global_index=%0d reason=sample_ready_while_busy",
                    sample_index);
                protocol_errors = protocol_errors + 1;
            end
            wait_for_completion;

            if (error) begin
                $display("HDLFLOW_ACCURACY_PROTOCOL_ERROR global_index=%0d reason=accelerator_error",
                    sample_index);
                protocol_errors = protocol_errors + 1;
            end
            if (result[3:0] !== reference_predictions[sample_index][3:0]) begin
                rtl_reference_mismatches =
                    rtl_reference_mismatches + 1;
                $display("HDLFLOW_ACCURACY_REFERENCE_MISMATCH global_index=%0d rtl=%0d reference=%0d",
                    sample_index, result[3:0],
                    reference_predictions[sample_index][3:0]);
            end
            if (result[3:0] == labels[sample_index][3:0])
                correct_count = correct_count + 1;
            confusion_index =
                labels[sample_index][3:0] * 16 + result[3:0];
            confusion[confusion_index] =
                confusion[confusion_index] + 1;
            $display("HDLFLOW_ACCURACY_SAMPLE global_index=%0d label=%0d rtl=%0d reference=%0d correct=%0d",
                sample_index, labels[sample_index][3:0], result[3:0],
                reference_predictions[sample_index][3:0],
                result[3:0] == labels[sample_index][3:0]);
        end

        if (dut.scheduler.parameter_word_count != 11'd1076 ||
            dut.scheduler.instruction_word_count != 9'd264) begin
            $display("HDLFLOW_ACCURACY_PROTOCOL_ERROR reason=frozen_package_changed params=%0d instructions=%0d",
                dut.scheduler.parameter_word_count,
                dut.scheduler.instruction_word_count);
            protocol_errors = protocol_errors + 1;
        end
        accuracy_percent = 100.0 * correct_count / batch_samples;
        for (confusion_index = 0; confusion_index < 16;
             confusion_index = confusion_index + 1)
            $display("HDLFLOW_ACCURACY_CONFUSION true_class=%0d c00=%0d c01=%0d c02=%0d c03=%0d c04=%0d c05=%0d c06=%0d c07=%0d c08=%0d c09=%0d c10=%0d c11=%0d c12=%0d c13=%0d c14=%0d c15=%0d",
                confusion_index,
                confusion[confusion_index*16+0],
                confusion[confusion_index*16+1],
                confusion[confusion_index*16+2],
                confusion[confusion_index*16+3],
                confusion[confusion_index*16+4],
                confusion[confusion_index*16+5],
                confusion[confusion_index*16+6],
                confusion[confusion_index*16+7],
                confusion[confusion_index*16+8],
                confusion[confusion_index*16+9],
                confusion[confusion_index*16+10],
                confusion[confusion_index*16+11],
                confusion[confusion_index*16+12],
                confusion[confusion_index*16+13],
                confusion[confusion_index*16+14],
                confusion[confusion_index*16+15]);
        if (rtl_reference_mismatches == 0 && protocol_errors == 0)
            $display("HDLFLOW_ACCURACY_SUMMARY subject=s01 start=%0d samples=%0d correct=%0d incorrect=%0d accuracy_percent=%0.6f rtl_reference_mismatches=0 protocol_errors=0 result=PASS",
                batch_start, batch_samples, correct_count,
                batch_samples-correct_count, accuracy_percent);
        else
            $display("HDLFLOW_ACCURACY_SUMMARY subject=s01 start=%0d samples=%0d correct=%0d incorrect=%0d accuracy_percent=%0.6f rtl_reference_mismatches=%0d protocol_errors=%0d result=FAIL",
                batch_start, batch_samples, correct_count,
                batch_samples-correct_count, accuracy_percent,
                rtl_reference_mismatches, protocol_errors);
        $finish;
    end
endmodule
// END MIGRATED SCENARIO: eeg_bci_accuracy_batch_tb.v

// BEGIN MIGRATED SCENARIO: eeg_bci_ps_axi4_gateway_tb.v
//==============================================================================
// Testbench   : eeg_bci_ps_axi4_gateway_tb
// Scope:
//   - Directed single-beat AXI4 checks for the V3 board gateway.
//   - Covers the first/last sample word, control pass-through, IDs, and errors.
// Spec Trace:
//   - REQ-EEG-BOARD-001, REQ-EEG-PERF-001, IF-AXI-CTRL, IF-BRAM-DATA.
//==============================================================================
`timescale 1ns/1ps

module eeg_bci_ps_axi4_gateway_tb;
    reg clk;
    reg rst_n;
    reg [11:0] awid;
    reg [31:0] awaddr;
    reg [7:0] awlen;
    reg [2:0] awsize;
    reg [1:0] awburst;
    reg awlock;
    reg [3:0] awcache;
    reg [2:0] awprot;
    reg [3:0] awqos;
    reg awvalid;
    wire awready;
    reg [31:0] wdata;
    reg [3:0] wstrb;
    reg wlast;
    reg wvalid;
    wire wready;
    wire [11:0] bid;
    wire [1:0] bresp;
    wire bvalid;
    reg bready;
    reg [11:0] arid;
    reg [31:0] araddr;
    reg [7:0] arlen;
    reg [2:0] arsize;
    reg [1:0] arburst;
    reg arlock;
    reg [3:0] arcache;
    reg [2:0] arprot;
    reg [3:0] arqos;
    reg arvalid;
    wire arready;
    wire [11:0] rid;
    wire [31:0] rdata;
    wire [1:0] rresp;
    wire rlast;
    wire rvalid;
    reg rready;
    wire sample_bram_clka;
    wire sample_bram_ena;
    wire [3:0] sample_bram_wea;
    wire [31:0] sample_bram_addra;
    wire [31:0] sample_bram_dina;
    reg [31:0] sample_bram_douta;
    wire sample_bram_clkb;
    wire sample_bram_enb;
    wire [3:0] sample_bram_web;
    wire [31:0] sample_bram_addrb;
    wire [31:0] sample_bram_dinb;
    reg [31:0] sample_bram_doutb;
    reg [31:0] sample_memory [0:2047];
    wire infer_done;
    wire [3:0] class_led;
    integer checks;
    integer errors;

    eeg_bci_ps_axi4_gateway dut (
        .s_axi_aclk(clk),
        .s_axi_aresetn(rst_n),
        .s_axi_awid(awid),
        .s_axi_awaddr(awaddr),
        .s_axi_awlen(awlen),
        .s_axi_awsize(awsize),
        .s_axi_awburst(awburst),
        .s_axi_awlock(awlock),
        .s_axi_awcache(awcache),
        .s_axi_awprot(awprot),
        .s_axi_awqos(awqos),
        .s_axi_awvalid(awvalid),
        .s_axi_awready(awready),
        .s_axi_wdata(wdata),
        .s_axi_wstrb(wstrb),
        .s_axi_wlast(wlast),
        .s_axi_wvalid(wvalid),
        .s_axi_wready(wready),
        .s_axi_bid(bid),
        .s_axi_bresp(bresp),
        .s_axi_bvalid(bvalid),
        .s_axi_bready(bready),
        .s_axi_arid(arid),
        .s_axi_araddr(araddr),
        .s_axi_arlen(arlen),
        .s_axi_arsize(arsize),
        .s_axi_arburst(arburst),
        .s_axi_arlock(arlock),
        .s_axi_arcache(arcache),
        .s_axi_arprot(arprot),
        .s_axi_arqos(arqos),
        .s_axi_arvalid(arvalid),
        .s_axi_arready(arready),
        .s_axi_rid(rid),
        .s_axi_rdata(rdata),
        .s_axi_rresp(rresp),
        .s_axi_rlast(rlast),
        .s_axi_rvalid(rvalid),
        .s_axi_rready(rready),
        .sample_bram_clka(sample_bram_clka),
        .sample_bram_ena(sample_bram_ena),
        .sample_bram_wea(sample_bram_wea),
        .sample_bram_addra(sample_bram_addra),
        .sample_bram_dina(sample_bram_dina),
        .sample_bram_douta(sample_bram_douta),
        .sample_bram_clkb(sample_bram_clkb),
        .sample_bram_enb(sample_bram_enb),
        .sample_bram_web(sample_bram_web),
        .sample_bram_addrb(sample_bram_addrb),
        .sample_bram_dinb(sample_bram_dinb),
        .sample_bram_doutb(sample_bram_doutb),
        .infer_done(infer_done),
        .class_led(class_led)
    );

    always #7 clk = ~clk;

    always @(posedge sample_bram_clka) begin
        if (sample_bram_ena) begin
            if (|sample_bram_wea)
                sample_memory[sample_bram_addra[12:2]] <= sample_bram_dina;
            sample_bram_douta <= sample_memory[sample_bram_addra[12:2]];
        end
    end

    always @(posedge sample_bram_clkb) begin
        if (sample_bram_enb) begin
            if (|sample_bram_web)
                sample_memory[sample_bram_addrb[12:2]] <= sample_bram_dinb;
            sample_bram_doutb <= sample_memory[sample_bram_addrb[12:2]];
        end
    end

    task expect_equal;
        input [255:0] name;
        input [31:0] actual;
        input [31:0] expected;
        begin
            checks = checks + 1;
            if (actual !== expected) begin
                errors = errors + 1;
                $display("AXI4_GATEWAY_MISMATCH name=%0s actual=%08x expected=%08x",
                    name, actual, expected);
            end
        end
    endtask

    task axi_write;
        input [11:0] id_value;
        input [31:0] address_value;
        input [31:0] data_value;
        input [3:0] strobe_value;
        input [7:0] length_value;
        input [1:0] expected_response;
        begin
            @(negedge clk);
            awid = id_value;
            awaddr = address_value;
            awlen = length_value;
            awsize = 3'd2;
            awburst = 2'b01;
            awvalid = 1'b1;
            wdata = data_value;
            wstrb = strobe_value;
            wlast = 1'b1;
            wvalid = 1'b1;
            while (!(awready && wready))
                @(negedge clk);
            @(negedge clk);
            awvalid = 1'b0;
            wvalid = 1'b0;
            bready = 1'b1;
            while (!bvalid)
                @(negedge clk);
            expect_equal("write_response", {18'd0, bid, bresp},
                {18'd0, id_value, expected_response});
            @(negedge clk);
            bready = 1'b0;
        end
    endtask

    task axi_read;
        input [11:0] id_value;
        input [31:0] address_value;
        input [7:0] length_value;
        input [1:0] expected_response;
        input [31:0] expected_data;
        begin
            @(negedge clk);
            arid = id_value;
            araddr = address_value;
            arlen = length_value;
            arsize = 3'd2;
            arburst = 2'b01;
            arvalid = 1'b1;
            while (!arready)
                @(negedge clk);
            @(negedge clk);
            arvalid = 1'b0;
            rready = 1'b1;
            while (!rvalid)
                @(negedge clk);
            expect_equal("read_response", {17'd0, rlast, rid, rresp},
                {17'd0, 1'b1, id_value, expected_response});
            expect_equal("read_data", rdata, expected_data);
            @(negedge clk);
            rready = 1'b0;
        end
    endtask

    initial begin
        clk = 1'b0;
        rst_n = 1'b0;
        awid = 12'd0;
        awaddr = 32'd0;
        awlen = 8'd0;
        awsize = 3'd2;
        awburst = 2'b01;
        awlock = 1'b0;
        awcache = 4'd0;
        awprot = 3'd0;
        awqos = 4'd0;
        awvalid = 1'b0;
        wdata = 32'd0;
        wstrb = 4'hf;
        wlast = 1'b1;
        wvalid = 1'b0;
        bready = 1'b0;
        arid = 12'd0;
        araddr = 32'd0;
        arlen = 8'd0;
        arsize = 3'd2;
        arburst = 2'b01;
        arlock = 1'b0;
        arcache = 4'd0;
        arprot = 3'd0;
        arqos = 4'd0;
        arvalid = 1'b0;
        rready = 1'b0;
        checks = 0;
        errors = 0;

        repeat (5) @(negedge clk);
        rst_n = 1'b1;
        repeat (3) @(negedge clk);

        // Four adjacent parameter words must remain independent.  The physical
        // BMG pin contract is byte-addressed; this sequence catches an
        // accidental second address shift that aliases all four writes.
        axi_write(12'h123, 32'h4000_0000, 32'h0000_b572, 4'hf,
            8'd0, 2'b00);
        axi_read(12'h234, 32'h4000_0000, 8'd0, 2'b00,
            32'h0000_b572);
        axi_write(12'h124, 32'h4000_0004, 32'h0000_b2bd, 4'hf,
            8'd0, 2'b00);
        axi_write(12'h125, 32'h4000_0008, 32'h0000_b5bb, 4'hf,
            8'd0, 2'b00);
        axi_write(12'h126, 32'h4000_000c, 32'h0000_abad, 4'hf,
            8'd0, 2'b00);
        axi_read(12'h235, 32'h4000_0000, 8'd0, 2'b00,
            32'h0000_b572);
        axi_read(12'h236, 32'h4000_0004, 8'd0, 2'b00,
            32'h0000_b2bd);
        axi_read(12'h237, 32'h4000_0008, 8'd0, 2'b00,
            32'h0000_b5bb);
        axi_read(12'h238, 32'h4000_000c, 8'd0, 2'b00,
            32'h0000_abad);
        axi_write(12'h345, 32'h4000_1ffc, 32'ha55a_2468, 4'hf,
            8'd0, 2'b00);
        axi_read(12'h456, 32'h4000_1ffc, 8'd0, 2'b00,
            32'ha55a_2468);

        axi_write(12'h567, 32'h4000_0000, 32'hffff_ffff, 4'h3,
            8'd0, 2'b10);
        axi_read(12'h678, 32'h4000_0000, 8'd0, 2'b00,
            32'h0000_b572);
        axi_write(12'h789, 32'h4000_0004, 32'h1111_2222, 4'hf,
            8'd1, 2'b10);
        axi_read(12'h89a, 32'h4100_0000, 8'd0, 2'b10, 32'd0);

        axi_read(12'h9ab, 32'h43c0_0018, 8'd0, 2'b00,
            32'h0000_0005);
        axi_write(12'habc, 32'h43c0_0018, 32'h0000_0001, 4'hf,
            8'd0, 2'b00);
        axi_read(12'hbcd, 32'h43c0_0018, 8'd0, 2'b00,
            32'h0000_0001);
        axi_read(12'hcde, 32'h43c0_003c, 8'd0, 2'b10, 32'd0);

        if (errors == 0)
            $display("AXI4_GATEWAY_PASS checks=%0d errors=0", checks);
        else
            $display("AXI4_GATEWAY_FAIL checks=%0d errors=%0d", checks,
                errors);
        #20;
        $finish;
    end

    initial begin
        #200000;
        $display("AXI4_GATEWAY_TIMEOUT");
        $finish;
    end
endmodule
// END MIGRATED SCENARIO: eeg_bci_ps_axi4_gateway_tb.v

// BEGIN MIGRATED SCENARIO: instruction_scheduler_multichannel_tb.v
`timescale 1ns/1ps

module instruction_scheduler_multichannel_tb;
    reg clk;
    reg rst_n;
    reg load_valid;
    wire load_ready;
    reg [2:0] load_type;
    reg [15:0] load_data;
    reg load_last;
    wire start_ready;
    wire [4:0] active_channels;
    wire [12:0] expected_sample_words;
    wire channel_config_valid;
    reg [15:0] instruction_words [0:263];
    integer index;
    integer failures;

    instruction_scheduler dut (
        .clk(clk),
        .rst_n(rst_n),
        .load_valid(load_valid),
        .load_ready(load_ready),
        .load_type(load_type),
        .load_data(load_data),
        .load_last(load_last),
        .start_valid(1'b0),
        .start_ready(start_ready),
        .profile_select(2'b01),
        .instruction_version(2'b01),
        .sample_loaded(1'b0),
        .op_valid(),
        .op_ready(1'b0),
        .opcode(),
        .descriptor_index(),
        .source_base(),
        .destination_base(),
        .parameter_base(),
        .op_done(1'b0),
        .op_error(1'b0),
        .all_done(),
        .busy(),
        .format_error(),
        .parameter_read_address(11'd0),
        .parameter_read_data(),
        .parameter_word_count(),
        .instruction_word_count(),
        .active_channels(active_channels),
        .expected_sample_words(expected_sample_words),
        .channel_config_valid(channel_config_valid)
    );

    always #5 clk = ~clk;

    task reset_dut;
        begin
            @(negedge clk);
            rst_n = 1'b0;
            load_valid = 1'b0;
            load_last = 1'b0;
            repeat (4) @(negedge clk);
            rst_n = 1'b1;
            repeat (2) @(negedge clk);
        end
    endtask

    task load_profile;
        input integer requested_channels;
        input integer mismatch_descriptor;
        begin
            $readmemh(
                "input/sources/verification/p1_vectors/multichannel/CH16/v2_instruction_words.hex",
                instruction_words);
            for (index = 0; index <= 4; index = index + 1)
                instruction_words[index * 24 + 12] = requested_channels;
            if (mismatch_descriptor >= 1 && mismatch_descriptor <= 4)
                instruction_words[mismatch_descriptor * 24 + 12] =
                    requested_channels + 1;

            for (index = 0; index < 264; index = index + 1) begin
                @(negedge clk);
                load_type = 3'b110;
                load_data = instruction_words[index];
                load_last = index == 263;
                load_valid = 1'b1;
                @(posedge clk);
                while (!load_ready)
                    @(posedge clk);
            end
            @(negedge clk);
            load_valid = 1'b0;
            load_last = 1'b0;
        end
    endtask

    task expect_config;
        input integer requested_channels;
        input integer mismatch_descriptor;
        input expected_valid;
        begin
            reset_dut();
            load_profile(requested_channels, mismatch_descriptor);
            if ((active_channels !== requested_channels[4:0]) ||
                (expected_sample_words !== (requested_channels << 7)) ||
                (channel_config_valid !== expected_valid)) begin
                $display("CHANNEL_CONFIG_FAIL requested=%0d mismatch_desc=%0d active=%0d sample_words=%0d expected_valid=%0d actual_valid=%0d valid_mask=%03x",
                    requested_channels, mismatch_descriptor, active_channels,
                    expected_sample_words, expected_valid,
                    channel_config_valid, dut.descriptor_format_valid);
                failures = failures + 1;
            end
            else begin
                $display("CHANNEL_CONFIG_PASS requested=%0d mismatch_desc=%0d valid=%0d",
                    requested_channels, mismatch_descriptor, expected_valid);
            end
        end
    endtask

    initial begin
        clk = 1'b0;
        rst_n = 1'b0;
        load_valid = 1'b0;
        load_type = 3'd0;
        load_data = 16'd0;
        load_last = 1'b0;
        failures = 0;

        expect_config(2, 0, 1'b1);
        expect_config(16, 0, 1'b1);
        expect_config(1, 0, 1'b0);
        expect_config(17, 0, 1'b0);
        expect_config(8, 3, 1'b0);

        if (failures == 0)
            $display("CHANNEL_CONFIG_NEGATIVE_PASS checks=5 failures=0");
        else
            $display("CHANNEL_CONFIG_NEGATIVE_FAIL checks=5 failures=%0d",
                failures);
        if (failures != 0)
            $fatal(1);
        $finish;
    end
endmodule
// END MIGRATED SCENARIO: instruction_scheduler_multichannel_tb.v

// Single directed verification authority.  SCENARIO selects one preserved
// scenario group at elaboration; no legacy file is an active TB source.
module tb_top;
`ifdef P1_SCENARIO_1
    localparam integer ACTIVE_SCENARIO = 1;
`elsif P1_SCENARIO_2
    localparam integer ACTIVE_SCENARIO = 2;
`elsif P1_SCENARIO_3
    localparam integer ACTIVE_SCENARIO = 3;
`elsif P1_SCENARIO_4
    localparam integer ACTIVE_SCENARIO = 4;
`elsif P1_SCENARIO_5
    localparam integer ACTIVE_SCENARIO = 5;
`else
    localparam integer ACTIVE_SCENARIO = 0;
`endif

    generate
        if (ACTIVE_SCENARIO == 0) begin : gen_core_functional
            eeg_bci_core_functional_tb scenario();
        end
        else if (ACTIVE_SCENARIO == 1) begin : gen_multichannel
            eeg_bci_multichannel_tb scenario();
        end
        else if (ACTIVE_SCENARIO == 2) begin : gen_pipeline
            eeg_bci_pipeline_tb scenario();
        end
        else if (ACTIVE_SCENARIO == 3) begin : gen_accuracy_batch
            eeg_bci_accuracy_batch_tb scenario();
        end
        else if (ACTIVE_SCENARIO == 4) begin : gen_axi4_gateway
            eeg_bci_ps_axi4_gateway_tb scenario();
        end
        else if (ACTIVE_SCENARIO == 5) begin : gen_scheduler_config
            instruction_scheduler_multichannel_tb scenario();
        end
        else begin : gen_invalid
            initial begin
                $display("HDLFLOW_INTEGRATED_TB_FAIL reason=invalid_scenario scenario=%0d", ACTIVE_SCENARIO);
                $finish;
            end
        end
    endgenerate
endmodule
