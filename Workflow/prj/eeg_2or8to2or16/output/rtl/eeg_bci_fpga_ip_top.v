//==============================================================================
// Module      : eeg_bci_fpga_ip_top
// File        : eeg_bci_fpga_ip_top.v
// Project     : eeg_2or8to2or16
// Description : Vivado module-reference shell for the frozen accelerator top.
// Scope:
//   - Exposes complete AXI4-Lite and BRAM_PORT interface metadata to IP Integrator.
//   - Maps the interfaces one-to-one into eeg_bci_accel_top.
// Spec Trace:
//   - REQ-EEG-ARCH-001, REQ-EEG-BOARD-001, REQ-EEG-CH16-001.
// Notes:
//   - AXI protection attributes are accepted at the official boundary but are
//     not consumed by the frozen register block.
//==============================================================================
`timescale 1ns/1ps
`default_nettype none

module eeg_bci_fpga_ip_top #(
    parameter C_S00_AXI_ADDR_WIDTH = 6
) (
    input  wire                              s00_axi_aclk,
    input  wire                              s00_axi_aresetn,
    input  wire [C_S00_AXI_ADDR_WIDTH-1:0]   s00_axi_awaddr,
    input  wire [2:0]                        s00_axi_awprot,
    input  wire                              s00_axi_awvalid,
    output wire                              s00_axi_awready,
    input  wire [31:0]                       s00_axi_wdata,
    input  wire [3:0]                        s00_axi_wstrb,
    input  wire                              s00_axi_wvalid,
    output wire                              s00_axi_wready,
    output wire [1:0]                        s00_axi_bresp,
    output wire                              s00_axi_bvalid,
    input  wire                              s00_axi_bready,
    input  wire [C_S00_AXI_ADDR_WIDTH-1:0]   s00_axi_araddr,
    input  wire [2:0]                        s00_axi_arprot,
    input  wire                              s00_axi_arvalid,
    output wire                              s00_axi_arready,
    output wire [31:0]                       s00_axi_rdata,
    output wire [1:0]                        s00_axi_rresp,
    output wire                              s00_axi_rvalid,
    input  wire                              s00_axi_rready,
    output wire                              bram_port_clk,
    output wire                              bram_port_rst,
    output wire                              bram_port_en,
    output wire [31:0]                       bram_port_addr,
    output wire [3:0]                        bram_port_we,
    output wire [31:0]                       bram_port_din,
    input  wire [31:0]                       bram_port_dout,
    output wire                              infer_done,
    output wire [3:0]                        class_led
);
    eeg_bci_accel_top #(
        .C_S00_AXI_ADDR_WIDTH(C_S00_AXI_ADDR_WIDTH)
    ) accelerator (
        .s00_axi_aclk(s00_axi_aclk),
        .s00_axi_aresetn(s00_axi_aresetn),
        .s00_axi_awaddr(s00_axi_awaddr),
        .s00_axi_awvalid(s00_axi_awvalid),
        .s00_axi_awready(s00_axi_awready),
        .s00_axi_wdata(s00_axi_wdata),
        .s00_axi_wstrb(s00_axi_wstrb),
        .s00_axi_wvalid(s00_axi_wvalid),
        .s00_axi_wready(s00_axi_wready),
        .s00_axi_bresp(s00_axi_bresp),
        .s00_axi_bvalid(s00_axi_bvalid),
        .s00_axi_bready(s00_axi_bready),
        .s00_axi_araddr(s00_axi_araddr),
        .s00_axi_arvalid(s00_axi_arvalid),
        .s00_axi_arready(s00_axi_arready),
        .s00_axi_rdata(s00_axi_rdata),
        .s00_axi_rresp(s00_axi_rresp),
        .s00_axi_rvalid(s00_axi_rvalid),
        .s00_axi_rready(s00_axi_rready),
        .ram_clk(bram_port_clk),
        .ram_rst(bram_port_rst),
        .ram_en(bram_port_en),
        .ram_addr(bram_port_addr),
        .ram_we(bram_port_we),
        .ram_wr_data(bram_port_din),
        .ram_rd_data(bram_port_dout),
        .infer_done(infer_done),
        .class_led(class_led)
    );
endmodule
`default_nettype wire
