//==============================================================================
// Module      : hi3593_v2_top
// File        : hi3593_v2_top.v
// Project     : Hi3593_v2
// Description : Hierarchy-only HI-3593 digital controller integration top.
// Scope:
//   - Instantiates reset, SPI, CDC, register, mailbox/status, FIFO, TX, and RX child modules.
//   - Does not own protocol decode, register updates, datapath mutation, CDC, or FIFO storage.
// Spec Trace:
//   - REQ-RST-001, REQ-SPI-001, REQ-FIFO-001, REQ-TX-001, REQ-RX-001
//   - REQ-LABEL-001, REQ-PLABEL-001, REQ-MAILBOX-001, REQ-MB-PINS-001
// Notes:
//   - MR is the only external reset pin.
//==============================================================================

module hi3593_v2_top (
    input  wire ACLK,
    input  wire MR,
    input  wire CS,
    input  wire SCK,
    input  wire SI,
    output wire SO,
    input  wire OUT1A,
    input  wire OUT1B,
    input  wire OUT2A,
    input  wire OUT2B,
    output wire TX1IN,
    output wire TX0IN,
    output wire SLP,
    output wire TEMPTY,
    output wire TFULL,
    output wire R1FLAG,
    output wire R2FLAG,
    output wire R1INT,
    output wire R2INT,
    output wire MB1_1,
    output wire MB1_2,
    output wire MB1_3,
    output wire MB2_1,
    output wire MB2_2,
    output wire MB2_3
);

//------------------------------------------------------------------------------
// Interconnect
//------------------------------------------------------------------------------

wire         spi_cmd_req_sck;
wire         spi_cmd_ack_sck;
wire [7:0]   spi_opcode_sck;
wire [255:0] spi_wdata_sck;
wire [5:0]   spi_byte_count_sck;
wire         spi_partial_discard;
wire [255:0] spi_read_data_sck;

wire         spi_cmd_valid;
wire [7:0]   spi_opcode;
wire [255:0] spi_wdata;
wire [255:0] read_data;

wire         opcode_04_pulse;
wire         opcode_44_pulse;
wire         master_reset;
wire         fifo_reset;

wire         tx_fifo_wr;
wire [31:0]  tx_fifo_wdata;
wire         tx_start_pulse;
wire [7:0]   tx_control;
wire [7:0]   rx1_control;
wire [7:0]   rx2_control;

wire         tx_fifo_rd;
wire [31:0]  tx_fifo_rdata;
wire         tx_fifo_empty;
wire         tx_fifo_half;
wire         tx_fifo_full;
wire [5:0]   tx_fifo_count;
wire         tx_fifo_overflow_seen;

wire         rx1_fifo_rd;
wire [31:0]  rx1_fifo_rdata;
wire         rx1_fifo_empty;
wire         rx1_fifo_half;
wire         rx1_fifo_full;
wire [5:0]   rx1_fifo_count;
wire         rx1_fifo_overflow_seen;

wire         rx2_fifo_rd;
wire [31:0]  rx2_fifo_rdata;
wire         rx2_fifo_empty;
wire         rx2_fifo_half;
wire         rx2_fifo_full;
wire [5:0]   rx2_fifo_count;
wire         rx2_fifo_overflow_seen;

wire         rx1_word_valid;
wire [31:0]  rx1_word_data;
wire         rx1_priority_match;
wire [1:0]   rx1_priority_slot;
wire         rx1_parity_error;
wire         rx1_label_reject;

wire         rx2_word_valid;
wire [31:0]  rx2_word_data;
wire         rx2_priority_match;
wire [1:0]   rx2_priority_slot;
wire         rx2_parity_error;
wire         rx2_label_reject;

wire [7:0]   rx1_status;
wire [7:0]   rx2_status;
wire [23:0]  rx1_mailbox1;
wire [23:0]  rx1_mailbox2;
wire [23:0]  rx1_mailbox3;
wire [23:0]  rx2_mailbox1;
wire [23:0]  rx2_mailbox2;
wire [23:0]  rx2_mailbox3;
wire         rx1_mailbox1_clear;
wire         rx1_mailbox2_clear;
wire         rx1_mailbox3_clear;
wire         rx2_mailbox1_clear;
wire         rx2_mailbox2_clear;
wire         rx2_mailbox3_clear;

wire [7:0]   flag_interrupt_assignment;
wire [7:0]   aclk_division;
wire [255:0] rx1_label_memory;
wire [255:0] rx2_label_memory;
wire [23:0]  rx1_priority_labels;
wire [23:0]  rx2_priority_labels;
wire         tx_busy;

//------------------------------------------------------------------------------
// Child Instances
//------------------------------------------------------------------------------

spi_slave_if u_spi_if (
    .SCK(SCK),
    .MR(MR),
    .CS(CS),
    .SI(SI),
    .read_data(spi_read_data_sck),
    .spi_cmd_ack(spi_cmd_ack_sck),
    .SO(SO),
    .spi_cmd_req(spi_cmd_req_sck),
    .spi_opcode(spi_opcode_sck),
    .spi_wdata(spi_wdata_sck),
    .spi_byte_count(spi_byte_count_sck),
    .partial_discard(spi_partial_discard)
);

spi_cmd_cdc u_spi_cmd_cdc (
    .ACLK(ACLK),
    .SCK(SCK),
    .MR(MR),
    .sck_cmd_req(spi_cmd_req_sck),
    .sck_opcode(spi_opcode_sck),
    .sck_wdata(spi_wdata_sck),
    .read_data_aclk(read_data),
    .sck_cmd_ack(spi_cmd_ack_sck),
    .read_data_sck(spi_read_data_sck),
    .aclk_cmd_valid(spi_cmd_valid),
    .aclk_opcode(spi_opcode),
    .aclk_wdata(spi_wdata)
);

reset_ctrl u_reset_ctrl (
    .ACLK(ACLK),
    .MR(MR),
    .opcode_04_pulse(opcode_04_pulse),
    .opcode_44_pulse(opcode_44_pulse),
    .master_reset(master_reset),
    .fifo_reset(fifo_reset)
);

control_status_regs u_reg_ctrl (
    .ACLK(ACLK),
    .master_reset(master_reset),
    .fifo_reset(fifo_reset),
    .spi_cmd_valid(spi_cmd_valid),
    .spi_opcode(spi_opcode),
    .spi_wdata(spi_wdata),
    .tx_fifo_empty(tx_fifo_empty),
    .tx_fifo_half(tx_fifo_half),
    .tx_fifo_full(tx_fifo_full),
    .rx1_fifo_rdata(rx1_fifo_rdata),
    .rx2_fifo_rdata(rx2_fifo_rdata),
    .rx1_status(rx1_status),
    .rx2_status(rx2_status),
    .rx1_mailbox1(rx1_mailbox1),
    .rx1_mailbox2(rx1_mailbox2),
    .rx1_mailbox3(rx1_mailbox3),
    .rx2_mailbox1(rx2_mailbox1),
    .rx2_mailbox2(rx2_mailbox2),
    .rx2_mailbox3(rx2_mailbox3),
    .read_data(read_data),
    .opcode_04_pulse(opcode_04_pulse),
    .opcode_44_pulse(opcode_44_pulse),
    .tx_fifo_wr(tx_fifo_wr),
    .tx_fifo_wdata(tx_fifo_wdata),
    .tx_start_pulse(tx_start_pulse),
    .rx1_fifo_rd(rx1_fifo_rd),
    .rx2_fifo_rd(rx2_fifo_rd),
    .rx1_mailbox1_clear(rx1_mailbox1_clear),
    .rx1_mailbox2_clear(rx1_mailbox2_clear),
    .rx1_mailbox3_clear(rx1_mailbox3_clear),
    .rx2_mailbox1_clear(rx2_mailbox1_clear),
    .rx2_mailbox2_clear(rx2_mailbox2_clear),
    .rx2_mailbox3_clear(rx2_mailbox3_clear),
    .tx_control(tx_control),
    .rx1_control(rx1_control),
    .rx2_control(rx2_control),
    .flag_interrupt_assignment(flag_interrupt_assignment),
    .aclk_division(aclk_division),
    .rx1_label_memory(rx1_label_memory),
    .rx2_label_memory(rx2_label_memory),
    .rx1_priority_labels(rx1_priority_labels),
    .rx2_priority_labels(rx2_priority_labels),
    .TEMPTY(TEMPTY),
    .TFULL(TFULL)
);

rx_mailbox_status u_mailbox_status (
    .ACLK(ACLK),
    .master_reset(master_reset),
    .fifo_reset(fifo_reset),
    .flag_interrupt_assignment(flag_interrupt_assignment),
    .rx1_fifo_empty(rx1_fifo_empty),
    .rx1_fifo_half(rx1_fifo_half),
    .rx2_fifo_empty(rx2_fifo_empty),
    .rx2_fifo_half(rx2_fifo_half),
    .rx1_word_valid(rx1_word_valid),
    .rx2_word_valid(rx2_word_valid),
    .rx1_word_data(rx1_word_data),
    .rx2_word_data(rx2_word_data),
    .rx1_priority_match(rx1_priority_match),
    .rx2_priority_match(rx2_priority_match),
    .rx1_priority_slot(rx1_priority_slot),
    .rx2_priority_slot(rx2_priority_slot),
    .rx1_parity_error(rx1_parity_error),
    .rx2_parity_error(rx2_parity_error),
    .rx1_label_reject(rx1_label_reject),
    .rx2_label_reject(rx2_label_reject),
    .rx1_mailbox1_clear(rx1_mailbox1_clear),
    .rx1_mailbox2_clear(rx1_mailbox2_clear),
    .rx1_mailbox3_clear(rx1_mailbox3_clear),
    .rx2_mailbox1_clear(rx2_mailbox1_clear),
    .rx2_mailbox2_clear(rx2_mailbox2_clear),
    .rx2_mailbox3_clear(rx2_mailbox3_clear),
    .rx1_status(rx1_status),
    .rx2_status(rx2_status),
    .rx1_mailbox1(rx1_mailbox1),
    .rx1_mailbox2(rx1_mailbox2),
    .rx1_mailbox3(rx1_mailbox3),
    .rx2_mailbox1(rx2_mailbox1),
    .rx2_mailbox2(rx2_mailbox2),
    .rx2_mailbox3(rx2_mailbox3),
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

sync_fifo #(
    .OVERWRITE_ON_FULL(0)
) u_tx_fifo (
    .clk(ACLK),
    .rst(master_reset),
    .clear(fifo_reset),
    .wr_en(tx_fifo_wr),
    .rd_en(tx_fifo_rd),
    .wr_data(tx_fifo_wdata),
    .rd_data(tx_fifo_rdata),
    .empty(tx_fifo_empty),
    .half(tx_fifo_half),
    .full(tx_fifo_full),
    .count(tx_fifo_count),
    .overflow_seen(tx_fifo_overflow_seen)
);

sync_fifo #(
    .OVERWRITE_ON_FULL(1)
) u_rx1_fifo (
    .clk(ACLK),
    .rst(master_reset),
    .clear(fifo_reset),
    .wr_en(rx1_word_valid),
    .rd_en(rx1_fifo_rd),
    .wr_data(rx1_word_data),
    .rd_data(rx1_fifo_rdata),
    .empty(rx1_fifo_empty),
    .half(rx1_fifo_half),
    .full(rx1_fifo_full),
    .count(rx1_fifo_count),
    .overflow_seen(rx1_fifo_overflow_seen)
);

sync_fifo #(
    .OVERWRITE_ON_FULL(1)
) u_rx2_fifo (
    .clk(ACLK),
    .rst(master_reset),
    .clear(fifo_reset),
    .wr_en(rx2_word_valid),
    .rd_en(rx2_fifo_rd),
    .wr_data(rx2_word_data),
    .rd_data(rx2_fifo_rdata),
    .empty(rx2_fifo_empty),
    .half(rx2_fifo_half),
    .full(rx2_fifo_full),
    .count(rx2_fifo_count),
    .overflow_seen(rx2_fifo_overflow_seen)
);

arinc429_tx u_arinc_tx (
    .ACLK(ACLK),
    .reset(master_reset),
    .tx_start_pulse(tx_start_pulse),
    .tx_control(tx_control),
    .fifo_empty(tx_fifo_empty),
    .fifo_rdata(tx_fifo_rdata),
    .fifo_rd(tx_fifo_rd),
    .TX1IN(TX1IN),
    .TX0IN(TX0IN),
    .SLP(SLP),
    .busy(tx_busy)
);

arinc429_rx u_arinc_rx1 (
    .ACLK(ACLK),
    .reset(master_reset),
    .OUTA(OUT1A),
    .OUTB(OUT1B),
    .rx_control(rx1_control),
    .label_memory(rx1_label_memory),
    .priority_labels(rx1_priority_labels),
    .rx_word_valid(rx1_word_valid),
    .rx_word_data(rx1_word_data),
    .priority_match(rx1_priority_match),
    .priority_slot(rx1_priority_slot),
    .parity_error(rx1_parity_error),
    .label_reject(rx1_label_reject)
);

arinc429_rx u_arinc_rx2 (
    .ACLK(ACLK),
    .reset(master_reset),
    .OUTA(OUT2A),
    .OUTB(OUT2B),
    .rx_control(rx2_control),
    .label_memory(rx2_label_memory),
    .priority_labels(rx2_priority_labels),
    .rx_word_valid(rx2_word_valid),
    .rx_word_data(rx2_word_data),
    .priority_match(rx2_priority_match),
    .priority_slot(rx2_priority_slot),
    .parity_error(rx2_parity_error),
    .label_reject(rx2_label_reject)
);

endmodule
