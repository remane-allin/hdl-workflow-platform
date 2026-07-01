//==============================================================================
// Module      : control_status_regs
// File        : control_status_regs.v
// Project     : Hi3593_v2
// Description : HI-3593 control/status register file and opcode side effects.
// Scope:
//   - Owns control registers, label/priority memories, command pulses, FIFO commands, and readback muxing.
//   - Does not own SPI CDC, SPI bit framing, RX mailbox state, FIFO storage, or ARINC bit timing.
// Spec Trace:
//   - REQ-SPI-002, REQ-RST-001, REQ-RST-002, REQ-STATUS-001, REQ-LABEL-001
//   - REQ-PLABEL-001, REQ-MAILBOX-001, REQ-FLAGINT-001, REQ-ACLK-001
// Notes:
//   - Opcode 0x44 clears FIFO and RX mailbox state through fifo_reset only.
//==============================================================================

module control_status_regs (
    input  wire         ACLK,
    input  wire         master_reset,
    input  wire         fifo_reset,
    input  wire         spi_cmd_valid,
    input  wire [7:0]   spi_opcode,
    input  wire [255:0] spi_wdata,
    input  wire         tx_fifo_empty,
    input  wire         tx_fifo_half,
    input  wire         tx_fifo_full,
    input  wire [31:0]  rx1_fifo_rdata,
    input  wire [31:0]  rx2_fifo_rdata,
    input  wire [7:0]   rx1_status,
    input  wire [7:0]   rx2_status,
    input  wire [23:0]  rx1_mailbox1,
    input  wire [23:0]  rx1_mailbox2,
    input  wire [23:0]  rx1_mailbox3,
    input  wire [23:0]  rx2_mailbox1,
    input  wire [23:0]  rx2_mailbox2,
    input  wire [23:0]  rx2_mailbox3,
    output reg  [255:0] read_data,
    output reg          opcode_04_pulse,
    output reg          opcode_44_pulse,
    output reg          tx_fifo_wr,
    output reg  [31:0]  tx_fifo_wdata,
    output reg          tx_start_pulse,
    output reg          rx1_fifo_rd,
    output reg          rx2_fifo_rd,
    output reg          rx1_mailbox1_clear,
    output reg          rx1_mailbox2_clear,
    output reg          rx1_mailbox3_clear,
    output reg          rx2_mailbox1_clear,
    output reg          rx2_mailbox2_clear,
    output reg          rx2_mailbox3_clear,
    output reg  [7:0]   tx_control,
    output reg  [7:0]   rx1_control,
    output reg  [7:0]   rx2_control,
    output reg  [7:0]   flag_interrupt_assignment,
    output reg  [7:0]   aclk_division,
    output reg  [255:0] rx1_label_memory,
    output reg  [255:0] rx2_label_memory,
    output reg  [23:0]  rx1_priority_labels,
    output reg  [23:0]  rx2_priority_labels,
    output reg          TEMPTY,
    output reg          TFULL
);

//------------------------------------------------------------------------------
// Opcode Constants
//------------------------------------------------------------------------------

localparam [7:0] OP_MASTER_RESET     = 8'h04;
localparam [7:0] OP_WRITE_TX_CONTROL = 8'h08;
localparam [7:0] OP_WRITE_TX_FIFO    = 8'h0C;
localparam [7:0] OP_WRITE_RX1_CTRL   = 8'h10;
localparam [7:0] OP_WRITE_RX1_LABEL  = 8'h14;
localparam [7:0] OP_WRITE_RX1_PRI    = 8'h18;
localparam [7:0] OP_WRITE_RX2_CTRL   = 8'h24;
localparam [7:0] OP_WRITE_RX2_LABEL  = 8'h28;
localparam [7:0] OP_WRITE_RX2_PRI    = 8'h2C;
localparam [7:0] OP_WRITE_FLAG       = 8'h34;
localparam [7:0] OP_WRITE_ACLK_DIV   = 8'h38;
localparam [7:0] OP_TX_ENABLE        = 8'h40;
localparam [7:0] OP_FIFO_RESET       = 8'h44;
localparam [7:0] OP_SET_RX1_LABELS   = 8'h48;
localparam [7:0] OP_SET_RX2_LABELS   = 8'h4C;
localparam [7:0] OP_READ_TX_STATUS   = 8'h80;
localparam [7:0] OP_READ_TX_CONTROL  = 8'h84;
localparam [7:0] OP_READ_RX1_STATUS  = 8'h90;
localparam [7:0] OP_READ_RX1_CTRL    = 8'h94;
localparam [7:0] OP_READ_RX1_LABEL   = 8'h98;
localparam [7:0] OP_READ_RX1_PRI     = 8'h9C;
localparam [7:0] OP_READ_RX1_FIFO    = 8'hA0;
localparam [7:0] OP_READ_RX1_MB1     = 8'hA4;
localparam [7:0] OP_READ_RX1_MB2     = 8'hA8;
localparam [7:0] OP_READ_RX1_MB3     = 8'hAC;
localparam [7:0] OP_READ_RX2_STATUS  = 8'hB0;
localparam [7:0] OP_READ_RX2_CTRL    = 8'hB4;
localparam [7:0] OP_READ_RX2_LABEL   = 8'hB8;
localparam [7:0] OP_READ_RX2_PRI     = 8'hBC;
localparam [7:0] OP_READ_RX2_FIFO    = 8'hC0;
localparam [7:0] OP_READ_RX2_MB1     = 8'hC4;
localparam [7:0] OP_READ_RX2_MB2     = 8'hC8;
localparam [7:0] OP_READ_RX2_MB3     = 8'hCC;
localparam [7:0] OP_READ_FLAG        = 8'hD0;
localparam [7:0] OP_READ_ACLK_DIV    = 8'hD4;

wire [7:0] tx_status;

assign tx_status = {5'b00000, tx_fifo_full, tx_fifo_half, tx_fifo_empty};

//------------------------------------------------------------------------------
// Register And Command Side Effects
//------------------------------------------------------------------------------

always @(posedge ACLK) begin
    if (master_reset) begin
        opcode_04_pulse           <= 1'b0;
        opcode_44_pulse           <= 1'b0;
        tx_fifo_wr                <= 1'b0;
        tx_fifo_wdata             <= 32'd0;
        tx_start_pulse            <= 1'b0;
        rx1_fifo_rd               <= 1'b0;
        rx2_fifo_rd               <= 1'b0;
        rx1_mailbox1_clear        <= 1'b0;
        rx1_mailbox2_clear        <= 1'b0;
        rx1_mailbox3_clear        <= 1'b0;
        rx2_mailbox1_clear        <= 1'b0;
        rx2_mailbox2_clear        <= 1'b0;
        rx2_mailbox3_clear        <= 1'b0;
        tx_control                <= 8'd0;
        rx1_control               <= 8'd0;
        rx2_control               <= 8'd0;
        flag_interrupt_assignment <= 8'd0;
        aclk_division             <= 8'd0;
        rx1_label_memory          <= 256'd0;
        rx2_label_memory          <= 256'd0;
        rx1_priority_labels       <= 24'd0;
        rx2_priority_labels       <= 24'd0;
        TEMPTY                    <= 1'b1;
        TFULL                     <= 1'b0;
    end
    else begin
        opcode_04_pulse    <= 1'b0;
        opcode_44_pulse    <= 1'b0;
        tx_fifo_wr         <= 1'b0;
        tx_start_pulse     <= 1'b0;
        rx1_fifo_rd        <= 1'b0;
        rx2_fifo_rd        <= 1'b0;
        rx1_mailbox1_clear <= 1'b0;
        rx1_mailbox2_clear <= 1'b0;
        rx1_mailbox3_clear <= 1'b0;
        rx2_mailbox1_clear <= 1'b0;
        rx2_mailbox2_clear <= 1'b0;
        rx2_mailbox3_clear <= 1'b0;
        TEMPTY             <= tx_fifo_empty;
        TFULL              <= tx_fifo_full;

        if (fifo_reset) begin
            rx1_priority_labels <= 24'd0;
            rx2_priority_labels <= 24'd0;
        end
        else begin
            rx1_priority_labels <= rx1_priority_labels;
            rx2_priority_labels <= rx2_priority_labels;
        end

        if (spi_cmd_valid) begin
            case (spi_opcode)
                OP_MASTER_RESET: begin
                    opcode_04_pulse <= 1'b1;
                end
                OP_WRITE_TX_CONTROL: begin
                    tx_control <= spi_wdata[7:0];
                end
                OP_WRITE_TX_FIFO: begin
                    if (!tx_fifo_full) begin
                        tx_fifo_wr    <= 1'b1;
                        tx_fifo_wdata <= spi_wdata[31:0];
                    end
                    else begin
                        tx_fifo_wr    <= 1'b0;
                        tx_fifo_wdata <= tx_fifo_wdata;
                    end
                end
                OP_WRITE_RX1_CTRL: begin
                    rx1_control <= spi_wdata[7:0];
                end
                OP_WRITE_RX1_LABEL: begin
                    rx1_label_memory <= spi_wdata;
                end
                OP_WRITE_RX1_PRI: begin
                    rx1_priority_labels <= spi_wdata[23:0];
                end
                OP_WRITE_RX2_CTRL: begin
                    rx2_control <= spi_wdata[7:0];
                end
                OP_WRITE_RX2_LABEL: begin
                    rx2_label_memory <= spi_wdata;
                end
                OP_WRITE_RX2_PRI: begin
                    rx2_priority_labels <= spi_wdata[23:0];
                end
                OP_WRITE_FLAG: begin
                    flag_interrupt_assignment <= spi_wdata[7:0];
                end
                OP_WRITE_ACLK_DIV: begin
                    aclk_division <= spi_wdata[7:0];
                end
                OP_TX_ENABLE: begin
                    tx_start_pulse <= 1'b1;
                end
                OP_FIFO_RESET: begin
                    opcode_44_pulse <= 1'b1;
                end
                OP_SET_RX1_LABELS: begin
                    rx1_label_memory <= {256{1'b1}};
                end
                OP_SET_RX2_LABELS: begin
                    rx2_label_memory <= {256{1'b1}};
                end
                OP_READ_RX1_FIFO: begin
                    rx1_fifo_rd <= 1'b1;
                end
                OP_READ_RX1_MB1: begin
                    rx1_mailbox1_clear <= 1'b1;
                end
                OP_READ_RX1_MB2: begin
                    rx1_mailbox2_clear <= 1'b1;
                end
                OP_READ_RX1_MB3: begin
                    rx1_mailbox3_clear <= 1'b1;
                end
                OP_READ_RX2_FIFO: begin
                    rx2_fifo_rd <= 1'b1;
                end
                OP_READ_RX2_MB1: begin
                    rx2_mailbox1_clear <= 1'b1;
                end
                OP_READ_RX2_MB2: begin
                    rx2_mailbox2_clear <= 1'b1;
                end
                OP_READ_RX2_MB3: begin
                    rx2_mailbox3_clear <= 1'b1;
                end
                default: begin
                    tx_fifo_wdata <= tx_fifo_wdata;
                end
            endcase
        end
        else begin
            tx_fifo_wdata <= tx_fifo_wdata;
        end
    end
end

//------------------------------------------------------------------------------
// Readback Mux
//------------------------------------------------------------------------------

always @(*) begin
    read_data = 256'd0;
    case (spi_opcode)
        OP_READ_TX_STATUS: begin
            read_data = {tx_status, 248'd0};
        end
        OP_READ_TX_CONTROL: begin
            read_data = {tx_control, 248'd0};
        end
        OP_READ_RX1_STATUS: begin
            read_data = {rx1_status, 248'd0};
        end
        OP_READ_RX1_CTRL: begin
            read_data = {rx1_control, 248'd0};
        end
        OP_READ_RX1_LABEL: begin
            read_data = rx1_label_memory;
        end
        OP_READ_RX1_PRI: begin
            read_data = {rx1_priority_labels, 232'd0};
        end
        OP_READ_RX1_FIFO: begin
            read_data = {rx1_fifo_rdata, 224'd0};
        end
        OP_READ_RX1_MB1: begin
            read_data = {rx1_mailbox1, 232'd0};
        end
        OP_READ_RX1_MB2: begin
            read_data = {rx1_mailbox2, 232'd0};
        end
        OP_READ_RX1_MB3: begin
            read_data = {rx1_mailbox3, 232'd0};
        end
        OP_READ_RX2_STATUS: begin
            read_data = {rx2_status, 248'd0};
        end
        OP_READ_RX2_CTRL: begin
            read_data = {rx2_control, 248'd0};
        end
        OP_READ_RX2_LABEL: begin
            read_data = rx2_label_memory;
        end
        OP_READ_RX2_PRI: begin
            read_data = {rx2_priority_labels, 232'd0};
        end
        OP_READ_RX2_FIFO: begin
            read_data = {rx2_fifo_rdata, 224'd0};
        end
        OP_READ_RX2_MB1: begin
            read_data = {rx2_mailbox1, 232'd0};
        end
        OP_READ_RX2_MB2: begin
            read_data = {rx2_mailbox2, 232'd0};
        end
        OP_READ_RX2_MB3: begin
            read_data = {rx2_mailbox3, 232'd0};
        end
        OP_READ_FLAG: begin
            read_data = {flag_interrupt_assignment, 248'd0};
        end
        OP_READ_ACLK_DIV: begin
            read_data = {aclk_division, 248'd0};
        end
        default: begin
            read_data = 256'd0;
        end
    endcase
end

endmodule
