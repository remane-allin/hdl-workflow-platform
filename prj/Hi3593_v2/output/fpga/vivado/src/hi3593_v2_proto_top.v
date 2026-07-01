//==============================================================================
// Module      : hi3593_v2_proto_top
// File        : hi3593_v2_proto_top.v
// Project     : Hi3593_v2
// Description : Loop3 PS/PL AXI adapter around the signed HI-3593 v2 top.
// Scope:
//   - Expose an AXI4-Lite control/status aperture for PS software.
//   - Bit-bang the signed SPI pins, drive RX digital inputs, and sample TX pins.
//   - Do not format UART text or replace core protocol behavior.
// Spec Trace:
//   - REQ-PROTO-001, DI-PROTO-AXI-001, PI-FPGA-WRAP-001
// Notes:
//   - PS software owns serial text, cache maintenance, and board verdicts.
//==============================================================================

module hi3593_v2_proto_top (
    input  wire        sys_clk,
    input  wire        uart_rx,
    output wire        uart_tx,
    output wire        pl_led0,

    (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 s00_axi_aclk CLK" *)
    (* X_INTERFACE_PARAMETER = "ASSOCIATED_BUSIF s00_axi, ASSOCIATED_RESET s00_axi_aresetn, FREQ_HZ 100000000" *)
    input  wire        s00_axi_aclk,
    (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 s00_axi_aresetn RST" *)
    (* X_INTERFACE_PARAMETER = "POLARITY ACTIVE_LOW" *)
    input  wire        s00_axi_aresetn,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s00_axi AWADDR" *)
    input  wire [31:0] s00_axi_awaddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s00_axi AWPROT" *)
    input  wire [2:0]  s00_axi_awprot,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s00_axi AWVALID" *)
    input  wire        s00_axi_awvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s00_axi AWREADY" *)
    output reg         s00_axi_awready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s00_axi WDATA" *)
    input  wire [31:0] s00_axi_wdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s00_axi WSTRB" *)
    input  wire [3:0]  s00_axi_wstrb,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s00_axi WVALID" *)
    input  wire        s00_axi_wvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s00_axi WREADY" *)
    output reg         s00_axi_wready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s00_axi BRESP" *)
    output reg  [1:0]  s00_axi_bresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s00_axi BVALID" *)
    output reg         s00_axi_bvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s00_axi BREADY" *)
    input  wire        s00_axi_bready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s00_axi ARADDR" *)
    input  wire [31:0] s00_axi_araddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s00_axi ARPROT" *)
    input  wire [2:0]  s00_axi_arprot,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s00_axi ARVALID" *)
    input  wire        s00_axi_arvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s00_axi ARREADY" *)
    output reg         s00_axi_arready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s00_axi RDATA" *)
    output reg  [31:0] s00_axi_rdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s00_axi RRESP" *)
    output reg  [1:0]  s00_axi_rresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s00_axi RVALID" *)
    (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s00_axi, DATA_WIDTH 32, PROTOCOL AXI4LITE, ADDR_WIDTH 32, HAS_BURST 0, HAS_LOCK 0, HAS_PROT 1, HAS_CACHE 0, HAS_QOS 0, HAS_REGION 0, HAS_WSTRB 1, HAS_BRESP 1, HAS_RRESP 1, SUPPORTS_NARROW_BURST 0, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, MAX_BURST_LENGTH 1" *)
    output reg         s00_axi_rvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s00_axi RREADY" *)
    input  wire        s00_axi_rready
);

localparam [3:0] ADDR_CONTROL   = 4'h0;
localparam [3:0] ADDR_STATUS    = 4'h1;
localparam [3:0] ADDR_TX_SAMPLE = 4'h2;
localparam [3:0] ADDR_RX_DRIVE  = 4'h3;
localparam [3:0] ADDR_ID        = 4'h4;

reg  [31:0] control_reg;
reg  [31:0] rx_drive_reg;
reg  [31:0] tx_sample_reg;
reg         uart_rx_meta;
reg         uart_rx_sync;
reg  [31:0] read_data_comb;

wire        core_SO;
wire        core_TEMPTY;
wire        core_TFULL;
wire        core_R1FLAG;
wire        core_R2FLAG;
wire        core_R1INT;
wire        core_R2INT;
wire        core_MB1_1;
wire        core_MB1_2;
wire        core_MB1_3;
wire        core_MB2_1;
wire        core_MB2_2;
wire        core_MB2_3;
wire        core_TX1IN;
wire        core_TX0IN;
wire        core_SLP;
wire        write_fire;
wire        read_fire;
wire        unused_sys_clk;
wire [2:0]  unused_axi_prot;

assign write_fire = s00_axi_awvalid & s00_axi_wvalid & ~s00_axi_bvalid;
assign read_fire = s00_axi_arvalid & ~s00_axi_rvalid;
assign unused_sys_clk = sys_clk;
assign unused_axi_prot = s00_axi_awprot ^ s00_axi_arprot;
assign uart_tx = 1'b1;
assign pl_led0 = control_reg[8] ? 1'b1 : core_TEMPTY;

hi3593_v2_top u_hi3593_v2_top (
    .ACLK(s00_axi_aclk),
    .MR(control_reg[0]),
    .CS(control_reg[1]),
    .SCK(control_reg[2]),
    .SI(control_reg[3]),
    .SO(core_SO),
    .OUT1A(rx_drive_reg[0]),
    .OUT1B(rx_drive_reg[1]),
    .OUT2A(rx_drive_reg[2]),
    .OUT2B(rx_drive_reg[3]),
    .TX1IN(core_TX1IN),
    .TX0IN(core_TX0IN),
    .SLP(core_SLP),
    .TEMPTY(core_TEMPTY),
    .TFULL(core_TFULL),
    .R1FLAG(core_R1FLAG),
    .R2FLAG(core_R2FLAG),
    .R1INT(core_R1INT),
    .R2INT(core_R2INT),
    .MB1_1(core_MB1_1),
    .MB1_2(core_MB1_2),
    .MB1_3(core_MB1_3),
    .MB2_1(core_MB2_1),
    .MB2_2(core_MB2_2),
    .MB2_3(core_MB2_3)
);

function [31:0] apply_wstrb;
    input [31:0] old_value;
    input [31:0] new_value;
    input [3:0]  strb;
    begin
        apply_wstrb = old_value;
        if (strb[0]) begin
            apply_wstrb[7:0] = new_value[7:0];
        end
        if (strb[1]) begin
            apply_wstrb[15:8] = new_value[15:8];
        end
        if (strb[2]) begin
            apply_wstrb[23:16] = new_value[23:16];
        end
        if (strb[3]) begin
            apply_wstrb[31:24] = new_value[31:24];
        end
    end
endfunction

always @(*) begin
    read_data_comb = 32'h00000000;
    case (s00_axi_araddr[5:2])
        ADDR_CONTROL: begin
            read_data_comb = control_reg;
        end
        ADDR_STATUS: begin
            read_data_comb = {
                15'h0000,
                core_MB2_3,
                core_MB2_2,
                core_MB2_1,
                core_MB1_3,
                core_MB1_2,
                core_MB1_1,
                uart_rx_sync,
                core_R2INT,
                core_R1INT,
                core_R2FLAG,
                core_R1FLAG,
                core_TFULL,
                core_TEMPTY,
                core_SLP,
                core_TX0IN,
                core_TX1IN,
                core_SO
            };
        end
        ADDR_TX_SAMPLE: begin
            read_data_comb = tx_sample_reg;
        end
        ADDR_RX_DRIVE: begin
            read_data_comb = rx_drive_reg;
        end
        ADDR_ID: begin
            read_data_comb = 32'h48335933;
        end
        default: begin
            read_data_comb = 32'h00000000;
        end
    endcase
end

always @(posedge s00_axi_aclk or negedge s00_axi_aresetn) begin
    if (!s00_axi_aresetn) begin
        control_reg  <= 32'h00000001;
        rx_drive_reg <= 32'h00000000;
        tx_sample_reg <= 32'h00000000;
        uart_rx_meta <= 1'b1;
        uart_rx_sync <= 1'b1;
    end
    else begin
        uart_rx_meta <= uart_rx;
        uart_rx_sync <= uart_rx_meta;
        tx_sample_reg <= {
            11'h000,
            core_MB2_3,
            core_MB2_2,
            core_MB2_1,
            core_MB1_3,
            core_MB1_2,
            core_MB1_1,
            uart_rx_sync,
            core_R2INT,
            core_R1INT,
            core_R2FLAG,
            core_R1FLAG,
            core_TFULL,
            core_TEMPTY,
            core_SLP,
            core_TX0IN,
            core_TX1IN,
            core_SO,
            rx_drive_reg[3:0]
        };
        if (write_fire) begin
            case (s00_axi_awaddr[5:2])
                ADDR_CONTROL: begin
                    control_reg <= apply_wstrb(control_reg, s00_axi_wdata, s00_axi_wstrb);
                end
                ADDR_RX_DRIVE: begin
                    rx_drive_reg <= apply_wstrb(rx_drive_reg, s00_axi_wdata, s00_axi_wstrb);
                end
                default: begin
                    control_reg <= control_reg;
                    rx_drive_reg <= rx_drive_reg;
                end
            endcase
        end
        else begin
            control_reg <= control_reg;
            rx_drive_reg <= rx_drive_reg;
        end
    end
end

always @(posedge s00_axi_aclk or negedge s00_axi_aresetn) begin
    if (!s00_axi_aresetn) begin
        s00_axi_awready <= 1'b0;
        s00_axi_wready  <= 1'b0;
        s00_axi_bresp   <= 2'b00;
        s00_axi_bvalid  <= 1'b0;
        s00_axi_arready <= 1'b0;
        s00_axi_rdata   <= 32'h00000000;
        s00_axi_rresp   <= 2'b00;
        s00_axi_rvalid  <= 1'b0;
    end
    else begin
        s00_axi_awready <= write_fire;
        s00_axi_wready  <= write_fire;
        s00_axi_arready <= read_fire;

        if (write_fire) begin
            s00_axi_bvalid <= 1'b1;
            s00_axi_bresp  <= 2'b00;
        end
        else if (s00_axi_bvalid && s00_axi_bready) begin
            s00_axi_bvalid <= 1'b0;
            s00_axi_bresp  <= 2'b00;
        end
        else begin
            s00_axi_bvalid <= s00_axi_bvalid;
            s00_axi_bresp  <= s00_axi_bresp;
        end

        if (read_fire) begin
            s00_axi_rvalid <= 1'b1;
            s00_axi_rresp  <= 2'b00;
            s00_axi_rdata  <= read_data_comb;
        end
        else if (s00_axi_rvalid && s00_axi_rready) begin
            s00_axi_rvalid <= 1'b0;
            s00_axi_rresp  <= 2'b00;
            s00_axi_rdata  <= s00_axi_rdata;
        end
        else begin
            s00_axi_rvalid <= s00_axi_rvalid;
            s00_axi_rresp  <= s00_axi_rresp;
            s00_axi_rdata  <= s00_axi_rdata;
        end
    end
end

endmodule
