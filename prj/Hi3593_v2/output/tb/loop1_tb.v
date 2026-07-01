`timescale 1ns/1ps

//==============================================================================
// Module      : loop1_tb
// File        : loop1_tb.v
// Project     : Hi3593_v2
// Description : Requirement-task directed Loop1 TB for active baseline evidence.
// Scope:
//   - Drives top-level SPI, reset, and decoded ARINC receiver pins.
//   - Emits HDLFLOW task/check/summary and waveform-window evidence.
//==============================================================================

module loop1_tb;

reg ACLK;
reg MR;
reg CS;
reg SCK;
reg SI;
reg OUT1A;
reg OUT1B;
reg OUT2A;
reg OUT2B;

wire SO;
wire TX1IN;
wire TX0IN;
wire SLP;
wire TEMPTY;
wire TFULL;
wire R1FLAG;
wire R2FLAG;
wire R1INT;
wire R2INT;
wire MB1_1;
wire MB1_2;
wire MB1_3;
wire MB2_1;
wire MB2_2;
wire MB2_3;

integer total_tests;
integer passed_tests;
integer failed_tests;
integer total_checks;
integer passed_checks;
integer failed_checks;
integer current_task_failed;
integer idx;
integer guard_count;
integer tx_activity_seen;
integer selftest_ok;
reg [1:0] previous_tx_pair;

hi3593_v2_top dut (
    .ACLK(ACLK),
    .MR(MR),
    .CS(CS),
    .SCK(SCK),
    .SI(SI),
    .SO(SO),
    .OUT1A(OUT1A),
    .OUT1B(OUT1B),
    .OUT2A(OUT2A),
    .OUT2B(OUT2B),
    .TX1IN(TX1IN),
    .TX0IN(TX0IN),
    .SLP(SLP),
    .TEMPTY(TEMPTY),
    .TFULL(TFULL),
    .R1FLAG(R1FLAG),
    .R2FLAG(R2FLAG),
    .R1INT(R1INT),
    .R2INT(R2INT),
    .MB1_1(MB1_1),
    .MB1_2(MB1_2),
    .MB1_3(MB1_3),
    .MB2_1(MB2_1),
    .MB2_2(MB2_2),
    .MB2_3(MB2_3)
);

initial begin
    ACLK = 1'b0;
    forever #5 ACLK = ~ACLK;
end

task begin_task;
    input [1023:0] task_id;
    input [1023:0] requirement_id;
    input [1023:0] test_id;
    begin
        total_tests = total_tests + 1;
        current_task_failed = 0;
        $display("HDLFLOW|TASK_BEGIN|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=%0s|requirement_id=%0s|test_id=%0s", task_id, requirement_id, test_id);
        $display("HDLFLOW|TEST_BEGIN|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=%0s|scope=hi3593_v2_top", test_id);
    end
endtask

task end_task;
    input [1023:0] task_id;
    input [1023:0] requirement_id;
    input [1023:0] test_id;
    begin
        if (current_task_failed == 0) begin
            passed_tests = passed_tests + 1;
            $display("HDLFLOW|TASK_END|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=%0s|requirement_id=%0s|test_id=%0s|result=PASS", task_id, requirement_id, test_id);
        end
        else begin
            failed_tests = failed_tests + 1;
            $display("HDLFLOW|TASK_END|schema=hdlflow_event_v1|version=1|stage=loop1|task_id=%0s|requirement_id=%0s|test_id=%0s|result=FAIL", task_id, requirement_id, test_id);
        end
    end
endtask

task record_check;
    input [1023:0] test_id;
    input [1023:0] txn_id;
    input [1023:0] sent;
    input [1023:0] expected;
    input [1023:0] actual;
    input integer latency_cycles;
    input pass;
    begin
        total_checks = total_checks + 1;
        if (pass) begin
            passed_checks = passed_checks + 1;
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=%0s|txn_id=%0s|sent=%0s|expected=%0s|actual=%0s|latency_cycles=%0d|result=PASS", test_id, txn_id, sent, expected, actual, latency_cycles);
        end
        else begin
            failed_checks = failed_checks + 1;
            current_task_failed = 1;
            $display("HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=%0s|txn_id=%0s|sent=%0s|expected=%0s|actual=%0s|latency_cycles=%0d|result=FAIL", test_id, txn_id, sent, expected, actual, latency_cycles);
        end
    end
endtask

task wave_begin;
    input [1023:0] window_id;
    begin
        $display("HDLFLOW_WAVE_BEGIN id=%0s time=%0t scope=top", window_id, $time);
    end
endtask

task wave_end;
    input [1023:0] window_id;
    begin
        $display("HDLFLOW_WAVE_END id=%0s time=%0t", window_id, $time);
    end
endtask

task wait_aclk;
    input integer cycles;
    integer wait_index;
    begin
        for (wait_index = 0; wait_index < cycles; wait_index = wait_index + 1) begin
            @(posedge ACLK);
        end
    end
endtask

task spi_send_byte;
    input [7:0] value;
    integer bit_index;
    begin
        for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1) begin
            SI = value[7 - bit_index];
            #13;
            SCK = 1'b1;
            #13;
            SCK = 1'b0;
            #7;
        end
    end
endtask

task spi_begin;
    begin
        SCK = 1'b0;
        SI  = 1'b0;
        CS  = 1'b0;
        #21;
    end
endtask

task spi_finish;
    begin
        wait_aclk(3);
        CS = 1'b1;
        SI = 1'b0;
        SCK = 1'b0;
        wait_aclk(4);
    end
endtask

task spi_cmd0;
    input [7:0] opcode;
    begin
        spi_begin;
        spi_send_byte(opcode);
        spi_finish;
    end
endtask

task spi_write1;
    input [7:0] opcode;
    input [7:0] data0;
    begin
        spi_begin;
        spi_send_byte(opcode);
        spi_send_byte(data0);
        spi_finish;
    end
endtask

task spi_write4;
    input [7:0] opcode;
    input [31:0] data_word;
    begin
        spi_begin;
        spi_send_byte(opcode);
        spi_send_byte(data_word[31:24]);
        spi_send_byte(data_word[23:16]);
        spi_send_byte(data_word[15:8]);
        spi_send_byte(data_word[7:0]);
        spi_finish;
    end
endtask

task spi_write3;
    input [7:0] opcode;
    input [23:0] data_word;
    begin
        spi_begin;
        spi_send_byte(opcode);
        spi_send_byte(data_word[23:16]);
        spi_send_byte(data_word[15:8]);
        spi_send_byte(data_word[7:0]);
        spi_finish;
    end
endtask

task spi_write32;
    input [7:0] opcode;
    input [255:0] data_word;
    integer byte_index;
    begin
        spi_begin;
        spi_send_byte(opcode);
        for (byte_index = 31; byte_index >= 0; byte_index = byte_index - 1) begin
            spi_send_byte(data_word[(byte_index * 8) +: 8]);
        end
        spi_finish;
    end
endtask

task spi_read_bytes;
    input [7:0] opcode;
    input integer byte_count;
    integer byte_index;
    begin
        spi_begin;
        spi_send_byte(opcode);
        for (byte_index = 0; byte_index < byte_count; byte_index = byte_index + 1) begin
            spi_send_byte(8'h00);
        end
        spi_finish;
    end
endtask

task drive_rx1_word;
    input [31:0] value;
    integer bit_index;
    begin
        for (bit_index = 0; bit_index < 32; bit_index = bit_index + 1) begin
            @(negedge ACLK);
            OUT1A = value[bit_index];
            OUT1B = ~value[bit_index];
            @(posedge ACLK);
        end
        @(negedge ACLK);
        OUT1A = 1'b0;
        OUT1B = 1'b0;
        wait_aclk(3);
    end
endtask

task wait_tx_busy;
    begin
        guard_count = 0;
        while ((dut.tx_busy !== 1'b1) && (guard_count < 2000)) begin
            @(posedge ACLK);
            guard_count = guard_count + 1;
        end
    end
endtask

task wait_tx_idle;
    begin
        guard_count = 0;
        while ((dut.tx_busy !== 1'b0) && (guard_count < 8000)) begin
            @(posedge ACLK);
            guard_count = guard_count + 1;
        end
    end
endtask

initial begin
    total_tests = 0;
    passed_tests = 0;
    failed_tests = 0;
    total_checks = 0;
    passed_checks = 0;
    failed_checks = 0;
    current_task_failed = 0;
    tx_activity_seen = 0;
    selftest_ok = 1;
    previous_tx_pair = 2'b00;

    MR = 1'b1;
    CS = 1'b1;
    SCK = 1'b0;
    SI = 1'b0;
    OUT1A = 1'b0;
    OUT1B = 1'b0;
    OUT2A = 1'b0;
    OUT2B = 1'b0;

    $display("HDLFLOW|RUN_BEGIN|schema=hdlflow_event_v1|version=1|stage=loop1|suite=hi3593_v2_directed");

    begin_task("TASK_RESET_BASELINE_001", "REQ-RST-001", "reset_release");
    wait_aclk(4);
    wave_begin("reset_release");
    MR = 1'b0;
    wait_aclk(8);
    record_check("reset_release", "opcode_04_reset_baseline", "MR=external_active_high", "tx_control_0_fifo_empty_1", "reset_defaults_sampled", 8, ((dut.u_reg_ctrl.tx_control == 8'h00) && (dut.tx_fifo_count == 6'd0) && (TEMPTY === 1'b1) && (TFULL === 1'b0)));
    wave_end("reset_release");
    end_task("TASK_RESET_BASELINE_001", "REQ-RST-001", "reset_release");

    begin_task("TASK_SPI_PARTIAL_001", "REQ-SPI-001", "partial_spi_byte_discard");
    wave_begin("partial_spi_byte_discard");
    spi_begin;
    SI = 1'b1; #13; SCK = 1'b1; #13; SCK = 1'b0; #7;
    SI = 1'b0; #13; SCK = 1'b1; #13; SCK = 1'b0; #7;
    SI = 1'b1; #13; SCK = 1'b1; #13; SCK = 1'b0; #7;
    CS = 1'b1;
    wait_aclk(4);
    record_check("partial_spi_byte_discard", "partial_bits_before_cs_inactive", "CS_low_three_bits_then_high", "partial_discard_1", "partial_discard_sampled", 4, (dut.u_spi_if.partial_discard === 1'b1));
    wave_end("partial_spi_byte_discard");
    end_task("TASK_SPI_PARTIAL_001", "REQ-SPI-001", "partial_spi_byte_discard");

    begin_task("TASK_OPCODE_MATRIX_001", "REQ-SPI-002", "spi_opcode_activity");
    wave_begin("spi_opcode_activity");
    spi_cmd0(8'h00);
    record_check("opcode_00_no_operation", "opcode_00", "opcode_00", "no_side_effect_opcode_latched", "spi_opcode_00h", 4, (dut.u_spi_if.spi_opcode == 8'h00));
    spi_write1(8'h08, 8'h15);
    record_check("opcode_08_write_tx_control", "opcode_08", "opcode_08_data_15h", "tx_control_15h", "tx_control_sampled", 4, (dut.u_reg_ctrl.tx_control == 8'h15));
    spi_write1(8'h10, 8'h00);
    record_check("opcode_10_write_rx1_control", "opcode_10", "opcode_10_data_00h", "rx1_control_00h", "rx1_control_sampled", 4, (dut.u_reg_ctrl.rx1_control == 8'h00));
    spi_write1(8'h24, 8'h00);
    record_check("opcode_24_write_rx2_control", "opcode_24", "opcode_24_data_00h", "rx2_control_00h", "rx2_control_sampled", 4, (dut.u_reg_ctrl.rx2_control == 8'h00));
    spi_read_bytes(8'h84, 1);
    record_check("opcode_84_read_tx_control", "opcode_84", "opcode_84_read", "read_opcode_latched", "spi_opcode_84h", 4, (dut.u_spi_if.spi_opcode == 8'h84));
    spi_read_bytes(8'h80, 1);
    record_check("opcode_80_read_tx_status", "opcode_80", "opcode_80_read", "read_opcode_latched", "spi_opcode_80h", 4, (dut.u_spi_if.spi_opcode == 8'h80));
    spi_cmd0(8'hFF);
    record_check("opcode_ff_no_operation", "opcode_FF", "opcode_ff", "no_side_effect_opcode_latched", "spi_opcode_ffh", 4, (dut.u_spi_if.spi_opcode == 8'hFF));
    wave_end("spi_opcode_activity");
    end_task("TASK_OPCODE_MATRIX_001", "REQ-SPI-002", "spi_opcode_activity");

    begin_task("TASK_LABEL_MEMORY_001", "REQ-LABEL-001", "label_memory_descending_byte_order");
    wave_begin("label_memory_descending_byte_order");
    spi_write32(8'h14, 256'h8000000000000000000000000000000000000000000000000000000000000001);
    record_check("opcode_14_write_rx1_label_memory", "opcode_14", "opcode_14_32_bytes", "rx1_label_memory_pattern", "rx1_label_memory_sampled", 32, (dut.u_reg_ctrl.rx1_label_memory == 256'h8000000000000000000000000000000000000000000000000000000000000001));
    spi_read_bytes(8'h98, 32);
    record_check("opcode_98_read_rx1_label_memory", "opcode_98", "opcode_98_read_32", "rx1_label_read_opcode_latched", "spi_opcode_98h", 4, (dut.u_spi_if.spi_opcode == 8'h98));
    spi_cmd0(8'h48);
    wait_aclk(4);
    record_check("opcode_48_set_all_rx1_labels", "opcode_48", "opcode_48", "rx1_label_memory_all_ones", "rx1_label_all_sampled", 4, (dut.u_reg_ctrl.rx1_label_memory == {256{1'b1}}));
    spi_write32(8'h28, 256'h00000000000000000000000000000000000000000000000000000000000000AA);
    spi_read_bytes(8'hB8, 32);
    record_check("opcode_b8_read_rx2_label_memory", "opcode_B8", "opcode_b8_read_32", "rx2_label_read_opcode_latched", "spi_opcode_b8h", 4, (dut.u_spi_if.spi_opcode == 8'hB8));
    spi_cmd0(8'h4C);
    wait_aclk(4);
    record_check("opcode_4c_set_all_rx2_labels", "opcode_4C", "opcode_4c", "rx2_label_memory_all_ones", "rx2_label_all_sampled", 4, (dut.u_reg_ctrl.rx2_label_memory == {256{1'b1}}));
    wave_end("label_memory_descending_byte_order");
    end_task("TASK_LABEL_MEMORY_001", "REQ-LABEL-001", "label_memory_descending_byte_order");

    begin_task("TASK_PRIORITY_MAILBOX_001", "REQ-MAILBOX-001", "priority_mailbox_read_clears_valid");
    wave_begin("priority_mailbox_read_clears_valid");
    spi_write3(8'h18, 24'h112233);
    record_check("opcode_18_write_rx1_priority_labels", "opcode_18", "opcode_18_112233", "rx1_priority_labels_112233", "priority_labels_sampled", 4, (dut.u_reg_ctrl.rx1_priority_labels == 24'h112233));
    spi_read_bytes(8'h9C, 3);
    record_check("opcode_9c_read_rx1_priority_labels", "opcode_9C", "opcode_9c_read", "rx1_priority_read_opcode_latched", "spi_opcode_9ch", 4, (dut.u_spi_if.spi_opcode == 8'h9C));
    spi_write3(8'h2C, 24'h445566);
    spi_read_bytes(8'hBC, 3);
    record_check("opcode_bc_read_rx2_priority_labels", "opcode_BC", "opcode_bc_read", "rx2_priority_read_opcode_latched", "spi_opcode_bch", 4, (dut.u_spi_if.spi_opcode == 8'hBC));
    spi_write1(8'h10, 8'h06);
    drive_rx1_word(32'hAABBCC33);
    wait_aclk(6);
    record_check("rx1_priority_mailbox_slot1", "rx1_label_33", "OUT1_word_label_33", "MB1_1_valid_mailbox_aabbcc", "mailbox_sampled", 6, ((MB1_1 === 1'b1) && (dut.u_mailbox_status.rx1_mailbox1 == 24'hAABBCC)));
    spi_read_bytes(8'hA4, 3);
    wait_aclk(4);
    record_check("opcode_a4_read_rx1_mailbox_1", "opcode_A4", "opcode_a4_read", "MB1_1_cleared_after_read", "mb1_1_clear_sampled", 4, (MB1_1 === 1'b0));
    wave_end("priority_mailbox_read_clears_valid");
    end_task("TASK_PRIORITY_MAILBOX_001", "REQ-MAILBOX-001", "priority_mailbox_read_clears_valid");

    begin_task("TASK_FLAG_ACLK_001", "REQ-FLAGINT-001", "flag_interrupt_selection_and_aclk");
    wave_begin("flag_interrupt_selection_and_aclk");
    spi_write1(8'h34, 8'h55);
    spi_write1(8'h38, 8'hB2);
    record_check("opcode_34_write_flag_interrupt_assignment", "opcode_34", "opcode_34_55h", "flag_assignment_55h", "flag_assignment_sampled", 4, (dut.u_reg_ctrl.flag_interrupt_assignment == 8'h55));
    record_check("opcode_38_write_aclk_division", "opcode_38", "opcode_38_b2h", "aclk_division_b2h", "aclk_division_sampled", 4, (dut.u_reg_ctrl.aclk_division == 8'hB2));
    spi_read_bytes(8'hD0, 1);
    record_check("opcode_d0_read_flag_interrupt_assignment", "opcode_D0", "opcode_d0_read", "flag_read_opcode_latched", "spi_opcode_d0h", 4, (dut.u_spi_if.spi_opcode == 8'hD0));
    spi_read_bytes(8'hD4, 1);
    record_check("opcode_d4_read_aclk_division", "opcode_D4", "opcode_d4_read", "aclk_read_opcode_latched", "spi_opcode_d4h", 4, (dut.u_spi_if.spi_opcode == 8'hD4));
    wave_end("flag_interrupt_selection_and_aclk");
    end_task("TASK_FLAG_ACLK_001", "REQ-FLAGINT-001", "flag_interrupt_selection_and_aclk");

    begin_task("TASK_TX_FIFO_FULL_001", "REQ-FIFO-001", "tx_fifo_full_ignore");
    wave_begin("tx_fifo_full_ignore");
    for (idx = 0; idx < 32; idx = idx + 1) begin
        spi_write4(8'h0C, (32'hA5000000 + idx));
    end
    record_check("tx_fifo_full_ignore_opcode_0c", "fill_to_32", "opcode_0c_x32", "tx_fifo_count_32_full_1", "tx_fifo_full_sampled", 32, ((dut.tx_fifo_count == 6'd32) && (TFULL === 1'b1)));
    spi_write4(8'h0C, 32'hDEADBEEF);
    record_check("tx_fifo_full_ignore", "write_when_full", "opcode_0c_extra_word", "tx_count_stays_32_no_overflow", "tx_full_ignore_sampled", 4, ((dut.tx_fifo_count == 6'd32) && (dut.tx_fifo_overflow_seen === 1'b0)));
    wave_end("tx_fifo_full_ignore");
    end_task("TASK_TX_FIFO_FULL_001", "REQ-FIFO-001", "tx_fifo_full_ignore");

    begin_task("TASK_RESET_BOUNDARY_001", "REQ-RST-002", "master_reset_keeps_control_register_opcode44_boundary");
    wave_begin("master_reset_keeps_control_register_opcode44_boundary");
    spi_cmd0(8'h44);
    wait_aclk(6);
    record_check("master_reset_keeps_control_register_opcode44_boundary", "opcode_44", "opcode_44_fifo_mailbox_reset", "tx_control_kept_fifo_clear", "opcode_44_boundary_sampled", 6, ((dut.u_reg_ctrl.tx_control == 8'h15) && (dut.tx_fifo_count == 6'd0)));
    spi_write1(8'h08, 8'h55);
    spi_write4(8'h0C, 32'h11223344);
    spi_cmd0(8'h04);
    wait_aclk(10);
    record_check("opcode_04_master_reset", "opcode_04", "opcode_04_master_reset", "control_and_fifo_cleared", "master_reset_sampled", 10, ((dut.u_reg_ctrl.tx_control == 8'h00) && (dut.tx_fifo_count == 6'd0)));
    wave_end("master_reset_keeps_control_register_opcode44_boundary");
    end_task("TASK_RESET_BOUNDARY_001", "REQ-RST-002", "master_reset_keeps_control_register_opcode44_boundary");

    begin_task("TASK_RX_FIFO_OVERWRITE_001", "REQ-RX-001", "rx_location32_overwrite");
    wave_begin("rx_location32_overwrite");
    spi_write1(8'h10, 8'h00);
    for (idx = 0; idx < 33; idx = idx + 1) begin
        drive_rx1_word(32'h01010000 + idx);
    end
    record_check("rx_location32_overwrite", "rx1_33_words", "OUT1A_OUT1B_33_words", "rx_count_32_overflow_seen", "rx_overwrite_sampled", 33, ((dut.rx1_fifo_count == 6'd32) && (dut.rx1_fifo_overflow_seen === 1'b1) && (R1FLAG === 1'b1)));
    spi_read_bytes(8'hA0, 4);
    record_check("opcode_a0_read_rx1_fifo", "opcode_A0", "opcode_a0_read", "rx1_read_opcode_latched", "spi_opcode_a0h", 4, (dut.u_spi_if.spi_opcode == 8'hA0));
    spi_read_bytes(8'hC0, 4);
    record_check("opcode_c0_read_rx2_fifo", "opcode_C0", "opcode_c0_read", "rx2_read_opcode_latched", "spi_opcode_c0h", 4, (dut.u_spi_if.spi_opcode == 8'hC0));
    wave_end("rx_location32_overwrite");
    end_task("TASK_RX_FIFO_OVERWRITE_001", "REQ-RX-001", "rx_location32_overwrite");

    begin_task("TASK_TX_RESPONSE_001", "REQ-TX-001", "arinc_tx_response");
    wave_begin("arinc_tx_response");
    spi_cmd0(8'h44);
    wait_aclk(6);
    spi_write1(8'h08, 8'h04);
    spi_write4(8'h0C, 32'hAAAAAAAA);
    previous_tx_pair = {TX1IN, TX0IN};
    tx_activity_seen = 0;
    spi_cmd0(8'h40);
    wait_tx_busy;
    for (idx = 0; idx < 80; idx = idx + 1) begin
        @(posedge ACLK);
        if ({TX1IN, TX0IN} != previous_tx_pair) begin
            tx_activity_seen = 1;
        end
        if ((TX1IN === 1'b1) || (TX0IN === 1'b1)) begin
            tx_activity_seen = 1;
        end
        previous_tx_pair = {TX1IN, TX0IN};
    end
    record_check("opcode_40_transmit_enable", "opcode_40", "opcode_40_after_tx_fifo_word", "tx_driver_activity", "tx_activity_sampled", 80, ((guard_count < 2000) && (tx_activity_seen == 1)));
    wave_end("arinc_tx_response");
    wait_tx_idle;
    end_task("TASK_TX_RESPONSE_001", "REQ-TX-001", "arinc_tx_response");

    begin_task("TASK_SELFTEST_001", "REQ-TX-001", "selftest_null_driver");
    wave_begin("selftest_null_driver");
    spi_cmd0(8'h44);
    wait_aclk(6);
    spi_write1(8'h08, 8'h10);
    spi_write4(8'h0C, 32'hFFFFFFFF);
    spi_cmd0(8'h40);
    wait_tx_busy;
    selftest_ok = (guard_count < 2000);
    for (idx = 0; idx < 40; idx = idx + 1) begin
        @(posedge ACLK);
        if ((TX1IN !== 1'b0) || (TX0IN !== 1'b0)) begin
            selftest_ok = 0;
        end
    end
    record_check("selftest_null_driver", "selftest", "tx_control_selftest_then_opcode_40", "tx1in_0_tx0in_0_while_busy", "selftest_null_sampled", 40, (selftest_ok == 1));
    wave_end("selftest_null_driver");
    wait_tx_idle;
    end_task("TASK_SELFTEST_001", "REQ-TX-001", "selftest_null_driver");

    if (failed_checks == 0) begin
        $display("HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|total_tests=%0d|passed_tests=%0d|failed_tests=%0d|total_checks=%0d|passed_checks=%0d|failed_checks=%0d|result=PASS", total_tests, passed_tests, failed_tests, total_checks, passed_checks, failed_checks);
    end
    else begin
        $display("HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|total_tests=%0d|passed_tests=%0d|failed_tests=%0d|total_checks=%0d|passed_checks=%0d|failed_checks=%0d|result=FAIL", total_tests, passed_tests, failed_tests, total_checks, passed_checks, failed_checks);
    end
    if (failed_checks == 0) begin
        $display("HDLFLOW|RUN_END|schema=hdlflow_event_v1|version=1|stage=loop1|suite=hi3593_v2_directed|result=PASS");
    end
    else begin
        $display("HDLFLOW|RUN_END|schema=hdlflow_event_v1|version=1|stage=loop1|suite=hi3593_v2_directed|result=FAIL");
    end
    wait_aclk(10);
    $finish;
end

endmodule
