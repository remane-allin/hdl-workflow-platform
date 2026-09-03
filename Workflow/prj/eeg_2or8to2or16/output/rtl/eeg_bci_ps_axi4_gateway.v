//==============================================================================
// Module      : eeg_bci_ps_axi4_gateway
// Project     : eeg_2or8to2or16
// Description : Resource-minimal Zynq PS GP0 attachment for the V3 accelerator.
//
// A dedicated AXI3-to-AXI4 protocol converter connects the Zynq GP0 master to
// this AXI4 endpoint.  The module preserves the released software address map
// while avoiding a general-purpose AXI crossbar and AXI BRAM controller:
//   0x4000_0000 .. 0x4000_1fff : 2048 x 32-bit sample staging RAM
//   0x43c0_0000 .. 0x43c0_ffff : accelerator AXI4-Lite registers
//
// The software uses strongly ordered Xil_In32/Xil_Out32 accesses.  Accordingly
// this endpoint accepts one AXI4 transaction at a time and returns SLVERR for
// bursts, narrow/unaligned accesses, or addresses outside the two frozen
// windows.  AXI IDs are preserved in every response.
//
// Scope:
//   - Board-only PS address decode, single-beat AXI4 adaptation, and BRAM ports.
//   - Does not change the accelerator instruction, arithmetic, or stream rules.
// Spec Trace:
//   - REQ-EEG-ARCH-001, REQ-EEG-BOARD-001, REQ-EEG-PERF-001.
//==============================================================================
`timescale 1ns/1ps
`default_nettype none

module eeg_bci_ps_axi4_gateway (
    (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 CLK.S_AXI_ACLK CLK" *)
    (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME CLK.S_AXI_ACLK, ASSOCIATED_BUSIF S_AXI, ASSOCIATED_RESET s_axi_aresetn" *)
    input  wire         s_axi_aclk,
    (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 RST.S_AXI_ARESETN RST" *)
    (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME RST.S_AXI_ARESETN, POLARITY ACTIVE_LOW" *)
    input  wire         s_axi_aresetn,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWID" *)
    (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME S_AXI, PROTOCOL AXI4, DATA_WIDTH 32, ADDR_WIDTH 32, ID_WIDTH 12, READ_WRITE_MODE READ_WRITE, HAS_BURST 1, HAS_LOCK 1, HAS_PROT 1, HAS_CACHE 1, HAS_QOS 1, HAS_REGION 0, HAS_WSTRB 1, HAS_BRESP 1, HAS_RRESP 1, SUPPORTS_NARROW_BURST 0, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, MAX_BURST_LENGTH 256" *)
    input  wire [11:0]  s_axi_awid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWADDR" *)
    input  wire [31:0]  s_axi_awaddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWLEN" *)
    input  wire [7:0]   s_axi_awlen,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWSIZE" *)
    input  wire [2:0]   s_axi_awsize,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWBURST" *)
    input  wire [1:0]   s_axi_awburst,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWLOCK" *)
    input  wire         s_axi_awlock,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWCACHE" *)
    input  wire [3:0]   s_axi_awcache,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWPROT" *)
    input  wire [2:0]   s_axi_awprot,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWQOS" *)
    input  wire [3:0]   s_axi_awqos,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWVALID" *)
    input  wire         s_axi_awvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWREADY" *)
    output wire         s_axi_awready,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WDATA" *)
    input  wire [31:0]  s_axi_wdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WSTRB" *)
    input  wire [3:0]   s_axi_wstrb,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WLAST" *)
    input  wire         s_axi_wlast,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WVALID" *)
    input  wire         s_axi_wvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WREADY" *)
    output wire         s_axi_wready,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BID" *)
    output reg  [11:0]  s_axi_bid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BRESP" *)
    output reg  [1:0]   s_axi_bresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BVALID" *)
    output reg          s_axi_bvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BREADY" *)
    input  wire         s_axi_bready,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARID" *)
    input  wire [11:0]  s_axi_arid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARADDR" *)
    input  wire [31:0]  s_axi_araddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARLEN" *)
    input  wire [7:0]   s_axi_arlen,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARSIZE" *)
    input  wire [2:0]   s_axi_arsize,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARBURST" *)
    input  wire [1:0]   s_axi_arburst,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARLOCK" *)
    input  wire         s_axi_arlock,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARCACHE" *)
    input  wire [3:0]   s_axi_arcache,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARPROT" *)
    input  wire [2:0]   s_axi_arprot,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARQOS" *)
    input  wire [3:0]   s_axi_arqos,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARVALID" *)
    input  wire         s_axi_arvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARREADY" *)
    output wire         s_axi_arready,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RID" *)
    output reg  [11:0]  s_axi_rid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *)
    output reg  [31:0]  s_axi_rdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RRESP" *)
    output reg  [1:0]   s_axi_rresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RLAST" *)
    output reg          s_axi_rlast,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RVALID" *)
    output reg          s_axi_rvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RREADY" *)
    input  wire         s_axi_rready,

    output wire         sample_bram_clka,
    output wire         sample_bram_ena,
    output wire [3:0]   sample_bram_wea,
    output wire [31:0]  sample_bram_addra,
    output wire [31:0]  sample_bram_dina,
    input  wire [31:0]  sample_bram_douta,
    output wire         sample_bram_clkb,
    output wire         sample_bram_enb,
    output wire [3:0]   sample_bram_web,
    output wire [31:0]  sample_bram_addrb,
    output wire [31:0]  sample_bram_dinb,
    input  wire [31:0]  sample_bram_doutb,

    output wire         infer_done,
    output wire [3:0]   class_led
);
    localparam [31:0] SAMPLE_BASE = 32'h4000_0000;
    localparam [15:0] CONTROL_PAGE = 16'h43c0;
    localparam [1:0] AXI_OKAY = 2'b00;
    localparam [1:0] AXI_SLVERR = 2'b10;

    reg [11:0] awid_hold;
    reg [31:0] awaddr_hold;
    reg [7:0]  awlen_hold;
    reg [2:0]  awsize_hold;
    reg [1:0]  awburst_hold;
    reg        aw_hold_valid;
    reg [31:0] wdata_hold;
    reg [3:0]  wstrb_hold;
    reg        wlast_hold;
    reg        w_hold_valid;
    reg        control_write_issued;

    reg [11:0] arid_hold;
    reg [31:0] araddr_hold;
    reg [7:0]  arlen_hold;
    reg [2:0]  arsize_hold;
    reg [1:0]  arburst_hold;
    reg        ar_hold_valid;
    reg        control_read_issued;
    reg        sample_read_wait;

    wire ctrl_awready;
    wire ctrl_wready;
    wire [1:0] ctrl_bresp;
    wire ctrl_bvalid;
    wire ctrl_arready;
    wire [31:0] ctrl_rdata;
    wire [1:0] ctrl_rresp;
    wire ctrl_rvalid;
    wire ram_clk;
    wire ram_rst;
    wire ram_en;
    wire [31:0] ram_addr;
    wire [3:0] ram_we;
    wire [31:0] ram_wr_data;

    wire write_pair_valid = aw_hold_valid && w_hold_valid;
    wire write_is_sample =
        (awaddr_hold[31:13] == SAMPLE_BASE[31:13]);
    wire write_is_control = (awaddr_hold[31:16] == CONTROL_PAGE);
    wire write_protocol_ok = (awlen_hold == 8'd0) &&
        (awsize_hold == 3'd2) && !awaddr_hold[1] && !awaddr_hold[0] &&
        wlast_hold &&
        ((awburst_hold == 2'b00) || (awburst_hold == 2'b01));
    wire control_write_start = write_pair_valid && write_is_control &&
        write_protocol_ok && !control_write_issued && !s_axi_bvalid;
    wire sample_write_fire = write_pair_valid && write_is_sample &&
        write_protocol_ok && (wstrb_hold == 4'hf) &&
        !control_write_issued && !s_axi_bvalid;

    wire read_is_sample =
        (araddr_hold[31:13] == SAMPLE_BASE[31:13]);
    wire read_is_control = (araddr_hold[31:16] == CONTROL_PAGE);
    wire read_protocol_ok = (arlen_hold == 8'd0) &&
        (arsize_hold == 3'd2) && !araddr_hold[1] && !araddr_hold[0] &&
        ((arburst_hold == 2'b00) || (arburst_hold == 2'b01));
    wire control_read_start = ar_hold_valid && read_is_control &&
        read_protocol_ok && !control_read_issued && !sample_read_wait &&
        !s_axi_rvalid;
    wire sample_read_fire = ar_hold_valid && read_is_sample &&
        read_protocol_ok && !control_read_issued && !sample_read_wait &&
        !s_axi_rvalid && !sample_write_fire;

    assign s_axi_awready = !aw_hold_valid && !s_axi_bvalid &&
        !control_write_issued;
    assign s_axi_wready = !w_hold_valid && !s_axi_bvalid &&
        !control_write_issued;
    assign s_axi_arready = !ar_hold_valid && !s_axi_rvalid &&
        !control_read_issued && !sample_read_wait;

    wire ctrl_awvalid = control_write_start;
    wire ctrl_wvalid = control_write_start;
    wire ctrl_bready = control_write_issued && !s_axi_bvalid;
    wire ctrl_arvalid = control_read_start;
    wire ctrl_rready = control_read_issued && !s_axi_rvalid;

    // The board design binds these two native ports to a 2048 x 32 true-dual-
    // port Block Memory Generator with Enable_32bit_Address enabled.  Its BRAM
    // pins therefore consume byte addresses even though storage is word-wide.
    // Port A serves AXI4 sample accesses; port B retains the accelerator
    // reader's frozen one-cycle BRAM latency.
    assign sample_bram_clka = s_axi_aclk;
    assign sample_bram_ena = sample_write_fire || sample_read_fire;
    assign sample_bram_wea = sample_write_fire ? 4'hf : 4'h0;
    assign sample_bram_addra = sample_write_fire ?
        {19'd0, awaddr_hold[12:0]} : {19'd0, araddr_hold[12:0]};
    assign sample_bram_dina = wdata_hold;
    assign sample_bram_clkb = ram_clk;
    assign sample_bram_enb = ram_en;
    assign sample_bram_web = ram_we;
    assign sample_bram_addrb = {19'd0, ram_addr[12:0]};
    assign sample_bram_dinb = ram_wr_data;

    always @(posedge s_axi_aclk or negedge s_axi_aresetn) begin
        if (!s_axi_aresetn) begin
            awid_hold <= 12'd0;
            awaddr_hold <= 32'd0;
            awlen_hold <= 8'd0;
            awsize_hold <= 3'd0;
            awburst_hold <= 2'd0;
            aw_hold_valid <= 1'b0;
            wdata_hold <= 32'd0;
            wstrb_hold <= 4'd0;
            wlast_hold <= 1'b0;
            w_hold_valid <= 1'b0;
            control_write_issued <= 1'b0;
            s_axi_bid <= 12'd0;
            s_axi_bresp <= AXI_OKAY;
            s_axi_bvalid <= 1'b0;
            arid_hold <= 12'd0;
            araddr_hold <= 32'd0;
            arlen_hold <= 8'd0;
            arsize_hold <= 3'd0;
            arburst_hold <= 2'd0;
            ar_hold_valid <= 1'b0;
            control_read_issued <= 1'b0;
            sample_read_wait <= 1'b0;
            s_axi_rid <= 12'd0;
            s_axi_rdata <= 32'd0;
            s_axi_rresp <= AXI_OKAY;
            s_axi_rlast <= 1'b0;
            s_axi_rvalid <= 1'b0;
        end
        else begin
            if (s_axi_awvalid && s_axi_awready) begin
                awid_hold <= s_axi_awid;
                awaddr_hold <= s_axi_awaddr;
                awlen_hold <= s_axi_awlen;
                awsize_hold <= s_axi_awsize;
                awburst_hold <= s_axi_awburst;
                aw_hold_valid <= 1'b1;
            end
            if (s_axi_wvalid && s_axi_wready) begin
                wdata_hold <= s_axi_wdata;
                wstrb_hold <= s_axi_wstrb;
                wlast_hold <= s_axi_wlast;
                w_hold_valid <= 1'b1;
            end

            if (s_axi_bvalid && s_axi_bready)
                s_axi_bvalid <= 1'b0;

            if (write_pair_valid && !s_axi_bvalid &&
                !control_write_issued) begin
                if (!write_protocol_ok ||
                    (write_is_sample && (wstrb_hold != 4'hf)) ||
                    (!write_is_sample && !write_is_control)) begin
                    s_axi_bid <= awid_hold;
                    s_axi_bresp <= AXI_SLVERR;
                    s_axi_bvalid <= 1'b1;
                    aw_hold_valid <= 1'b0;
                    w_hold_valid <= 1'b0;
                end
                else if (write_is_sample) begin
                    s_axi_bid <= awid_hold;
                    s_axi_bresp <= AXI_OKAY;
                    s_axi_bvalid <= 1'b1;
                    aw_hold_valid <= 1'b0;
                    w_hold_valid <= 1'b0;
                end
                else if (ctrl_awready && ctrl_wready) begin
                    control_write_issued <= 1'b1;
                end
            end

            if (control_write_issued && ctrl_bvalid && ctrl_bready) begin
                s_axi_bid <= awid_hold;
                s_axi_bresp <= ctrl_bresp;
                s_axi_bvalid <= 1'b1;
                aw_hold_valid <= 1'b0;
                w_hold_valid <= 1'b0;
                control_write_issued <= 1'b0;
            end

            if (s_axi_arvalid && s_axi_arready) begin
                arid_hold <= s_axi_arid;
                araddr_hold <= s_axi_araddr;
                arlen_hold <= s_axi_arlen;
                arsize_hold <= s_axi_arsize;
                arburst_hold <= s_axi_arburst;
                ar_hold_valid <= 1'b1;
            end

            if (s_axi_rvalid && s_axi_rready) begin
                s_axi_rvalid <= 1'b0;
                s_axi_rlast <= 1'b0;
            end

            if (ar_hold_valid && !s_axi_rvalid &&
                !control_read_issued && !sample_read_wait) begin
                if (!read_protocol_ok ||
                    (!read_is_sample && !read_is_control)) begin
                    s_axi_rid <= arid_hold;
                    s_axi_rdata <= 32'd0;
                    s_axi_rresp <= AXI_SLVERR;
                    s_axi_rlast <= 1'b1;
                    s_axi_rvalid <= 1'b1;
                    ar_hold_valid <= 1'b0;
                end
                else if (read_is_sample) begin
                    sample_read_wait <= 1'b1;
                end
                else if (ctrl_arready) begin
                    control_read_issued <= 1'b1;
                end
            end

            if (sample_read_wait && !s_axi_rvalid) begin
                s_axi_rid <= arid_hold;
                s_axi_rdata <= sample_bram_douta;
                s_axi_rresp <= AXI_OKAY;
                s_axi_rlast <= 1'b1;
                s_axi_rvalid <= 1'b1;
                ar_hold_valid <= 1'b0;
                sample_read_wait <= 1'b0;
            end

            if (control_read_issued && ctrl_rvalid && ctrl_rready) begin
                s_axi_rid <= arid_hold;
                s_axi_rdata <= ctrl_rdata;
                s_axi_rresp <= ctrl_rresp;
                s_axi_rlast <= 1'b1;
                s_axi_rvalid <= 1'b1;
                ar_hold_valid <= 1'b0;
                control_read_issued <= 1'b0;
            end
        end
    end

    eeg_bci_accel_top accelerator (
        .s00_axi_aclk(s_axi_aclk),
        .s00_axi_aresetn(s_axi_aresetn),
        .s00_axi_awaddr(awaddr_hold[5:0]),
        .s00_axi_awvalid(ctrl_awvalid),
        .s00_axi_awready(ctrl_awready),
        .s00_axi_wdata(wdata_hold),
        .s00_axi_wstrb(wstrb_hold),
        .s00_axi_wvalid(ctrl_wvalid),
        .s00_axi_wready(ctrl_wready),
        .s00_axi_bresp(ctrl_bresp),
        .s00_axi_bvalid(ctrl_bvalid),
        .s00_axi_bready(ctrl_bready),
        .s00_axi_araddr(araddr_hold[5:0]),
        .s00_axi_arvalid(ctrl_arvalid),
        .s00_axi_arready(ctrl_arready),
        .s00_axi_rdata(ctrl_rdata),
        .s00_axi_rresp(ctrl_rresp),
        .s00_axi_rvalid(ctrl_rvalid),
        .s00_axi_rready(ctrl_rready),
        .ram_clk(ram_clk),
        .ram_rst(ram_rst),
        .ram_en(ram_en),
        .ram_addr(ram_addr),
        .ram_we(ram_we),
        .ram_wr_data(ram_wr_data),
        .ram_rd_data(sample_bram_doutb),
        .infer_done(infer_done),
        .class_led(class_led)
    );

    // The stream reader is read-only by contract.  Keeping this assertion as
    // a synthesis-time observable net lets simulation/audit catch regressions
    // without adding hardware state.
    wire unused_reader_write = |ram_we | |ram_wr_data | ram_rst;
    wire unused_axi_attributes = |s_axi_awlock | |s_axi_awcache |
        |s_axi_awprot | |s_axi_awqos | |s_axi_arlock | |s_axi_arcache |
        |s_axi_arprot | |s_axi_arqos | unused_reader_write;

endmodule
`default_nettype wire
