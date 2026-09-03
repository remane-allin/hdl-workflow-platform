// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2024 Advanced Micro Devices, Inc. All Rights Reserved.
// --------------------------------------------------------------------------------
// Tool Version: Vivado v.2024.2 (win64) Build 5239630 Fri Nov 08 22:35:27 MST 2024
// Date        : Thu Sep  3 10:59:23 2026
// Host        : DESKTOP-ADCQ3LG running 64-bit major release  (build 9200)
// Command     : write_verilog -force -mode funcsim
//               g:/EEG/Workflow/prj/eeg_2or8to2or16/output/vivado/eeg_bci.gen/sources_1/bd/eeg_bci_ps_pl_system/ip/eeg_bci_ps_pl_system_sample_bram_0_0/eeg_bci_ps_pl_system_sample_bram_0_0_sim_netlist.v
// Design      : eeg_bci_ps_pl_system_sample_bram_0_0
// Purpose     : This verilog netlist is a functional simulation representation of the design and should not be modified
//               or synthesized. This netlist cannot be used for SDF annotated simulation.
// Device      : xc7z020clg400-1
// --------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

(* CHECK_LICENSE_TYPE = "eeg_bci_ps_pl_system_sample_bram_0_0,blk_mem_gen_v8_4_9,{}" *) (* downgradeipidentifiedwarnings = "yes" *) (* x_core_info = "blk_mem_gen_v8_4_9,Vivado 2024.2" *) 
(* NotValidForBitStream *)
module eeg_bci_ps_pl_system_sample_bram_0_0
   (clka,
    ena,
    wea,
    addra,
    dina,
    douta,
    clkb,
    enb,
    web,
    addrb,
    dinb,
    doutb);
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTA CLK" *) (* x_interface_mode = "slave BRAM_PORTA" *) (* x_interface_parameter = "XIL_INTERFACENAME BRAM_PORTA, MEM_ADDRESS_MODE BYTE_ADDRESS, MEM_SIZE 8192, MEM_WIDTH 32, MEM_ECC NONE, MASTER_TYPE BRAM_CTRL, READ_WRITE_MODE READ_WRITE, READ_LATENCY 1" *) input clka;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTA EN" *) input ena;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTA WE" *) input [3:0]wea;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTA ADDR" *) input [31:0]addra;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTA DIN" *) input [31:0]dina;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTA DOUT" *) output [31:0]douta;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTB CLK" *) (* x_interface_mode = "slave BRAM_PORTB" *) (* x_interface_parameter = "XIL_INTERFACENAME BRAM_PORTB, MEM_ADDRESS_MODE BYTE_ADDRESS, MEM_SIZE 8192, MEM_WIDTH 32, MEM_ECC NONE, MASTER_TYPE BRAM_CTRL, READ_WRITE_MODE READ_WRITE, READ_LATENCY 1" *) input clkb;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTB EN" *) input enb;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTB WE" *) input [3:0]web;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTB ADDR" *) input [31:0]addrb;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTB DIN" *) input [31:0]dinb;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTB DOUT" *) output [31:0]doutb;

  wire [31:0]addra;
  wire [31:0]addrb;
  wire clka;
  wire clkb;
  wire [31:0]dina;
  wire [31:0]dinb;
  wire [31:0]douta;
  wire [31:0]doutb;
  wire ena;
  wire enb;
  wire [3:0]wea;
  wire [3:0]web;
  wire NLW_U0_dbiterr_UNCONNECTED;
  wire NLW_U0_rsta_busy_UNCONNECTED;
  wire NLW_U0_rstb_busy_UNCONNECTED;
  wire NLW_U0_s_axi_arready_UNCONNECTED;
  wire NLW_U0_s_axi_awready_UNCONNECTED;
  wire NLW_U0_s_axi_bvalid_UNCONNECTED;
  wire NLW_U0_s_axi_dbiterr_UNCONNECTED;
  wire NLW_U0_s_axi_rlast_UNCONNECTED;
  wire NLW_U0_s_axi_rvalid_UNCONNECTED;
  wire NLW_U0_s_axi_sbiterr_UNCONNECTED;
  wire NLW_U0_s_axi_wready_UNCONNECTED;
  wire NLW_U0_sbiterr_UNCONNECTED;
  wire [31:0]NLW_U0_rdaddrecc_UNCONNECTED;
  wire [3:0]NLW_U0_s_axi_bid_UNCONNECTED;
  wire [1:0]NLW_U0_s_axi_bresp_UNCONNECTED;
  wire [31:0]NLW_U0_s_axi_rdaddrecc_UNCONNECTED;
  wire [31:0]NLW_U0_s_axi_rdata_UNCONNECTED;
  wire [3:0]NLW_U0_s_axi_rid_UNCONNECTED;
  wire [1:0]NLW_U0_s_axi_rresp_UNCONNECTED;

  (* C_ADDRA_WIDTH = "32" *) 
  (* C_ADDRB_WIDTH = "32" *) 
  (* C_ALGORITHM = "1" *) 
  (* C_AXI_ID_WIDTH = "4" *) 
  (* C_AXI_SLAVE_TYPE = "0" *) 
  (* C_AXI_TYPE = "1" *) 
  (* C_BYTE_SIZE = "8" *) 
  (* C_COMMON_CLK = "0" *) 
  (* C_COUNT_18K_BRAM = "0" *) 
  (* C_COUNT_36K_BRAM = "2" *) 
  (* C_CTRL_ECC_ALGO = "NONE" *) 
  (* C_DEFAULT_DATA = "0" *) 
  (* C_DISABLE_WARN_BHV_COLL = "0" *) 
  (* C_DISABLE_WARN_BHV_RANGE = "0" *) 
  (* C_ELABORATION_DIR = "./" *) 
  (* C_ENABLE_32BIT_ADDRESS = "1" *) 
  (* C_EN_DEEPSLEEP_PIN = "0" *) 
  (* C_EN_ECC_PIPE = "0" *) 
  (* C_EN_RDADDRA_CHG = "0" *) 
  (* C_EN_RDADDRB_CHG = "0" *) 
  (* C_EN_SAFETY_CKT = "0" *) 
  (* C_EN_SHUTDOWN_PIN = "0" *) 
  (* C_EN_SLEEP_PIN = "0" *) 
  (* C_EST_POWER_SUMMARY = "Estimated Power for IP     :     10.7492 mW" *) 
  (* C_FAMILY = "zynq" *) 
  (* C_HAS_AXI_ID = "0" *) 
  (* C_HAS_ENA = "1" *) 
  (* C_HAS_ENB = "1" *) 
  (* C_HAS_INJECTERR = "0" *) 
  (* C_HAS_MEM_OUTPUT_REGS_A = "0" *) 
  (* C_HAS_MEM_OUTPUT_REGS_B = "0" *) 
  (* C_HAS_MUX_OUTPUT_REGS_A = "0" *) 
  (* C_HAS_MUX_OUTPUT_REGS_B = "0" *) 
  (* C_HAS_REGCEA = "0" *) 
  (* C_HAS_REGCEB = "0" *) 
  (* C_HAS_RSTA = "0" *) 
  (* C_HAS_RSTB = "0" *) 
  (* C_HAS_SOFTECC_INPUT_REGS_A = "0" *) 
  (* C_HAS_SOFTECC_OUTPUT_REGS_B = "0" *) 
  (* C_INITA_VAL = "0" *) 
  (* C_INITB_VAL = "0" *) 
  (* C_INIT_FILE = "NONE" *) 
  (* C_INIT_FILE_NAME = "no_coe_file_loaded" *) 
  (* C_INTERFACE_TYPE = "0" *) 
  (* C_LOAD_INIT_FILE = "0" *) 
  (* C_MEM_TYPE = "2" *) 
  (* C_MUX_PIPELINE_STAGES = "0" *) 
  (* C_PRIM_TYPE = "1" *) 
  (* C_READ_DEPTH_A = "2048" *) 
  (* C_READ_DEPTH_B = "2048" *) 
  (* C_READ_LATENCY_A = "1" *) 
  (* C_READ_LATENCY_B = "1" *) 
  (* C_READ_WIDTH_A = "32" *) 
  (* C_READ_WIDTH_B = "32" *) 
  (* C_RSTRAM_A = "0" *) 
  (* C_RSTRAM_B = "0" *) 
  (* C_RST_PRIORITY_A = "CE" *) 
  (* C_RST_PRIORITY_B = "CE" *) 
  (* C_SIM_COLLISION_CHECK = "ALL" *) 
  (* C_USE_BRAM_BLOCK = "1" *) 
  (* C_USE_BYTE_WEA = "1" *) 
  (* C_USE_BYTE_WEB = "1" *) 
  (* C_USE_DEFAULT_DATA = "0" *) 
  (* C_USE_ECC = "0" *) 
  (* C_USE_SOFTECC = "0" *) 
  (* C_USE_URAM = "0" *) 
  (* C_WEA_WIDTH = "4" *) 
  (* C_WEB_WIDTH = "4" *) 
  (* C_WRITE_DEPTH_A = "2048" *) 
  (* C_WRITE_DEPTH_B = "2048" *) 
  (* C_WRITE_MODE_A = "WRITE_FIRST" *) 
  (* C_WRITE_MODE_B = "WRITE_FIRST" *) 
  (* C_WRITE_WIDTH_A = "32" *) 
  (* C_WRITE_WIDTH_B = "32" *) 
  (* C_XDEVICEFAMILY = "zynq" *) 
  (* downgradeipidentifiedwarnings = "yes" *) 
  (* is_du_within_envelope = "true" *) 
  eeg_bci_ps_pl_system_sample_bram_0_0_blk_mem_gen_v8_4_9 U0
       (.addra({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,addra[12:2],1'b0,1'b0}),
        .addrb({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,addrb[12:2],1'b0,1'b0}),
        .clka(clka),
        .clkb(clkb),
        .dbiterr(NLW_U0_dbiterr_UNCONNECTED),
        .deepsleep(1'b0),
        .dina(dina),
        .dinb(dinb),
        .douta(douta),
        .doutb(doutb),
        .eccpipece(1'b0),
        .ena(ena),
        .enb(enb),
        .injectdbiterr(1'b0),
        .injectsbiterr(1'b0),
        .rdaddrecc(NLW_U0_rdaddrecc_UNCONNECTED[31:0]),
        .regcea(1'b1),
        .regceb(1'b1),
        .rsta(1'b0),
        .rsta_busy(NLW_U0_rsta_busy_UNCONNECTED),
        .rstb(1'b0),
        .rstb_busy(NLW_U0_rstb_busy_UNCONNECTED),
        .s_aclk(1'b0),
        .s_aresetn(1'b0),
        .s_axi_araddr({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .s_axi_arburst({1'b0,1'b0}),
        .s_axi_arid({1'b0,1'b0,1'b0,1'b0}),
        .s_axi_arlen({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .s_axi_arready(NLW_U0_s_axi_arready_UNCONNECTED),
        .s_axi_arsize({1'b0,1'b0,1'b0}),
        .s_axi_arvalid(1'b0),
        .s_axi_awaddr({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .s_axi_awburst({1'b0,1'b0}),
        .s_axi_awid({1'b0,1'b0,1'b0,1'b0}),
        .s_axi_awlen({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .s_axi_awready(NLW_U0_s_axi_awready_UNCONNECTED),
        .s_axi_awsize({1'b0,1'b0,1'b0}),
        .s_axi_awvalid(1'b0),
        .s_axi_bid(NLW_U0_s_axi_bid_UNCONNECTED[3:0]),
        .s_axi_bready(1'b0),
        .s_axi_bresp(NLW_U0_s_axi_bresp_UNCONNECTED[1:0]),
        .s_axi_bvalid(NLW_U0_s_axi_bvalid_UNCONNECTED),
        .s_axi_dbiterr(NLW_U0_s_axi_dbiterr_UNCONNECTED),
        .s_axi_injectdbiterr(1'b0),
        .s_axi_injectsbiterr(1'b0),
        .s_axi_rdaddrecc(NLW_U0_s_axi_rdaddrecc_UNCONNECTED[31:0]),
        .s_axi_rdata(NLW_U0_s_axi_rdata_UNCONNECTED[31:0]),
        .s_axi_rid(NLW_U0_s_axi_rid_UNCONNECTED[3:0]),
        .s_axi_rlast(NLW_U0_s_axi_rlast_UNCONNECTED),
        .s_axi_rready(1'b0),
        .s_axi_rresp(NLW_U0_s_axi_rresp_UNCONNECTED[1:0]),
        .s_axi_rvalid(NLW_U0_s_axi_rvalid_UNCONNECTED),
        .s_axi_sbiterr(NLW_U0_s_axi_sbiterr_UNCONNECTED),
        .s_axi_wdata({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .s_axi_wlast(1'b0),
        .s_axi_wready(NLW_U0_s_axi_wready_UNCONNECTED),
        .s_axi_wstrb({1'b0,1'b0,1'b0,1'b0}),
        .s_axi_wvalid(1'b0),
        .sbiterr(NLW_U0_sbiterr_UNCONNECTED),
        .shutdown(1'b0),
        .sleep(1'b0),
        .wea(wea),
        .web(web));
endmodule
`pragma protect begin_protected
`pragma protect version = 1
`pragma protect encrypt_agent = "XILINX"
`pragma protect encrypt_agent_info = "Xilinx Encryption Tool 2024.2"
`pragma protect key_keyowner="Synopsys", key_keyname="SNPS-VCS-RSA-2", key_method="rsa"
`pragma protect encoding = (enctype="BASE64", line_length=76, bytes=128)
`pragma protect key_block
FPXllyX2NFs/RMngGqZy2bLYbZr92CdofeZrJOHklWXExpaPgHNYp2Lzm4MnflbnrfSkCmLwwKT5
zfRgEip7FKQ5Zhb73p0MAIADixBZ/ZRt4hQkJL0T9brm0waLHfanjnov2aCX6jN3LbQc3ujmDga6
Dd73k78u4xjRTDv1/P4=

`pragma protect key_keyowner="Aldec", key_keyname="ALDEC15_001", key_method="rsa"
`pragma protect encoding = (enctype="BASE64", line_length=76, bytes=256)
`pragma protect key_block
kr7VKKvChFoiyRCReag+OvU3jnmG9pN0cv+BxhNmMKLthg/ksgNZyU3L+fQ7cmIQELtlUjwjkBAP
Jjq5RsCnHbJxj+Ys1GNhriiBsxLqxWCP8onhAVvgZN2xZFOih0UWpqlU8NVP8Eww1ohvkDgxTstC
3kDmYehxIUJjqCC/mgRZmuezqugrFdubYmBoz16tUvD17iA5qqCIMS9xSIXYp2LBNekmWEwrVqzu
R4koEo4UlXl/CEw0XY3QvMoHnlXgu6N/6sc+nxZtKSwjiMVvGnZE9UVvJPAC3Hn3zKFGlK53mmGO
Tj0dWzhwX0ahSYzkyJC/HLdbGZmriL2UNvDyFw==

`pragma protect key_keyowner="Mentor Graphics Corporation", key_keyname="MGC-VELOCE-RSA", key_method="rsa"
`pragma protect encoding = (enctype="BASE64", line_length=76, bytes=128)
`pragma protect key_block
CaLc9FGt3AdRHfNtGAsGFY/QEvHY1Vv4TvvgCDsdDMqiuDeLizFJDJeskBWjeKDoE2cufK8TxiBq
mySRQNJoeOKnxTiDdf+Rx6m0iR6h/YeswegYwgghpM5KVrl6mSwF3+4yEovPM7a+9ArDQ5vl+WT8
SilNGzyW0KnTwe7+szs=

`pragma protect key_keyowner="Mentor Graphics Corporation", key_keyname="MGC-VERIF-SIM-RSA-2", key_method="rsa"
`pragma protect encoding = (enctype="BASE64", line_length=76, bytes=256)
`pragma protect key_block
cEnudSW1X71p0Xuq6jrXOxHnBku87IA0RA3zKqmeZHZM0r+9rEm5MSzX8RecnQ994yiqeyxbIH2l
fGEzUzr0ZzryS3fkf2LnJuB39f2YARW9eVCSiaeWaraZuY1l89T+h3vgdlurS/1LIraYLS1MyOXa
6F1LAcQp3W4OO4ctc3q1FRMZGldRS1biMsKwJ8Lxj8NEOm67UfgFrJNQAxbVXEfbWRWhKtwNxcTB
JbgC8j4EHkIA46mzoHloeBAL6KieplQUBjKXSSTb66rxglbFhWLy+mirROHcocu9J4ZbvTRYZEww
4lso1lqAllVLAoKYqa3WImZuSRoTbGDngBt9Lg==

`pragma protect key_keyowner="Real Intent", key_keyname="RI-RSA-KEY-1", key_method="rsa"
`pragma protect encoding = (enctype="BASE64", line_length=76, bytes=256)
`pragma protect key_block
rOyI+x4PlmKcVSFoN3oKgSYpVlmYxc194Ej04il/YmBg10xopy4zmtu5sdCP/uGSNYcNGWeAiw01
mNf98KyNgTUFXruHCA38qjhhEIvl4vfWWn3W3mFRxrIuwmnreT6qTvgMaxIkCdVBDP7Iy7O6WmCf
3Va5X5hnCHhtXgX5UYniBHiLjmupv63B8XMAYDH2n6mQ3H0DF7mtb7psBafd0Z6+IWUbmzwMtKrf
ZrRJBGAhNT0i1KrEjEh/rWjN7Z7N32zQ+Pl1kc5gYCQIX5McfdTdqSaRVXZ/HF90ymS7/8d5LDyj
Er+ORdcjnOn6oAyY4PuUUl4OYUHv5k+RglTe5Q==

`pragma protect key_keyowner="Xilinx", key_keyname="xilinxt_2023_11", key_method="rsa"
`pragma protect encoding = (enctype="BASE64", line_length=76, bytes=256)
`pragma protect key_block
bJa7kPSpDipzoJoQu1APEjc8vFLqBfQZK/grZvWijD7/FgMTerFCWLUY6n8DWeGdvjXvTeyrqCHE
2rP/H57wUqPC8tIJlGm6ZYQGjZ3TgYqLrJshDE5zYMTO//q0vuSraWvZP7A7SLuW6y7tFE/nplpx
L8gbYORx6j70okGUwnamCMS9yhFr7Z2QTJne1k4GNFGvy66URk3k5cBPl5j4/1yc4xGV+aWYl6L8
q8RorRU/CltObHKrji/jdiY1WtdGrkpRyCEFc+XNPazL9xSLLu5bz6XlvKwoks+8a5KYT/VFUovM
JbM0bpAXM8Z7rGaPuXjqXtZBg5praTZLu/WNcA==

`pragma protect key_keyowner="Metrics Technologies Inc.", key_keyname="DSim", key_method="rsa"
`pragma protect encoding = (enctype="BASE64", line_length=76, bytes=256)
`pragma protect key_block
PYKBDinOGc/kIVdFzXrz2wA4/QNFxLDrQfTWfR5TjYE6bm49vrZi0bawcr9HXp4OP1+XxPLB3oCP
oV5e/rYeDln531ebt8yEg27XCoSHEX4FU8oG8aBJ8fqgWayOnAMJt025WodOxuZXbhT1zPo7J3uh
6iO9Mv7RtYE2fZ1W+G8oN//FTOEJYPWlKYnt0cDeZrN3I4rHHptZHuu7l8T+df0PYea3x6U3Mvkl
ojZ+TwQtdu0NuYY5j3QNgx3+W2XYq1M773FAnEz/deW54EjE+jf1jjrBk2pl8SYxeKuutS15oPVF
eHdqXYVcJxoUY5JH8z04lITKEnZ4oq6sYS6dog==

`pragma protect key_keyowner="Atrenta", key_keyname="ATR-SG-RSA-1", key_method="rsa"
`pragma protect encoding = (enctype="BASE64", line_length=76, bytes=384)
`pragma protect key_block
tl+2vFCWZ583gQGsVC7oopz2NCKBiJ9uOHYBGzJZheOHJMqI/ehNvo25l710eBx00tztXzM30AH6
ZhAJg+kJwE2jO0MV5fmG5dnwXmLqoGEJMBs7xwWxvYK7w/0z9M0AJKD7HnuC+IiLhNU/fIxyuE+I
+vWqp//RcfY0tMMp2I2J1yEW6GUahS1ve/4JchssZ7Xu7VthoSDWXMQWATbvsUsDzeSo2+Ruz8Kq
Dc05HqEU8NgBxDPPEKLCcdKLp4byglwj7iCAtCjsPy8P18qjgb2sycFjNgmaiNMMB51WqeD+hneG
hLOue9bqVdEojkrb3q4WbsGZKz0bAGsryxslOlYHP1b8vey3yI2ixA80wyERe8d3GRIeZiSxGykH
qWxsE6x/iyi8QRb5mXZPMApA+Fln8tYmn7+1rFCm8gF4gJWhr1PsSJqTi658symGrzT0Ghjvf2QL
SvvoaeNdy0pOsWs7jLBFndd4GiFA+9K6Y33sziLToU9EvvFokENIslod

`pragma protect key_keyowner="Cadence Design Systems.", key_keyname="CDS_RSA_KEY_VER_1", key_method="rsa"
`pragma protect encoding = (enctype="BASE64", line_length=76, bytes=256)
`pragma protect key_block
oYiCujFRj1F3wKsGZlHR9niEtR9MLXEVAVfy+f/3xrmpW6Ye5a+fBCvm4TH+iRQefGHNdMPnzTNW
K/pEPAS9uMJjOdFiu+APT+LYrSRnEg4W0dX5buSDGM6LBWAuMseoTMjbJJoYDGLRckJgW43E30mX
ej4823nkbfwc+Ecbrup825qLyv8RTQLNHafvJA5lSapdqXwnlOIYRmcHn+sfAh5pGv9kW9aokcdh
ObR2XYxX99rYloyvz3x0pmjxD5ILW4SQMB1IUEuuyqX6eb5IQ+kZ41hjvsHIuQH29vzpCfV9Jqha
WC5yxxK1R+cleZSKD1H1gVzbTei8uFs/91Bgeg==

`pragma protect key_keyowner="Synplicity", key_keyname="SYNP15_1", key_method="rsa"
`pragma protect encoding = (enctype="BASE64", line_length=76, bytes=256)
`pragma protect key_block
urNc+S8AFPj+GVFdqJE5V7P8O6QI6MA3nkwYb8NKbYbVufnXKg6voJIRYYeYr7EOa8mrqirozWbY
Lln9SLWnkaAy2LvL/N6WahoQdCt++4RH+xe768XvSrVUFPrIwZRixqMLurc/tPov4i5P/ukZKl18
ZPZvXRzUNlvCZnMPcF+5QCQihqPbjcZ0YyGgWgX/ipTGG3sNqmylGN7qLa4Rgqu/mB5a2xVyu5Wc
911+/X3VVFx697WVaP5V0SbOzYN8R8+8B8kdznwixMA+f4lSbBXyRysVOSzYjo8bKEMqyKMVBQn9
xDmEuV0DvVWXdO7VPvWA1LuJFwS07OxeI2GCcQ==

`pragma protect key_keyowner="Mentor Graphics Corporation", key_keyname="MGC-PREC-RSA", key_method="rsa"
`pragma protect encoding = (enctype="BASE64", line_length=76, bytes=256)
`pragma protect key_block
QcP7fsLZxaDrG29e9HQeXfu2TsKsdyW7Yc1vWct6lbmDEfXkWMU1fFWSPIjPzRc9UOnfEu0bRn+B
D+8MWokqes3WF7txljBmgUPiNGZ8arUU6ENa/IY/Wv7iaB/ZKM5PtdnFAkjDIrYyKFCTz/U6Yzwi
hBGGarK/wYQOLzeeKRewiPTiNUL7tztWuMZ1t1msxD951EeKrwjrjcXIIuf/TzrOGUOlWgjHlnrl
4Q/lfMAnRLBNTSWG+5wWewCE8jK2X/gJ5AV4p3x1WP3+JglbxpP39l3pzedXqciZPbuz2XlFnRPV
KByaUaAShzJ56p8+0HjWebibqQdieGNPiPWW0Q==

`pragma protect data_method = "AES128-CBC"
`pragma protect encoding = (enctype = "BASE64", line_length = 76, bytes = 51648)
`pragma protect data_block
+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
HxLpWR0D
`pragma protect end_protected
`ifndef GLBL
`define GLBL
`timescale  1 ps / 1 ps

module glbl ();

    parameter ROC_WIDTH = 100000;
    parameter TOC_WIDTH = 0;
    parameter GRES_WIDTH = 10000;
    parameter GRES_START = 10000;

//--------   STARTUP Globals --------------
    wire GSR;
    wire GTS;
    wire GWE;
    wire PRLD;
    wire GRESTORE;
    tri1 p_up_tmp;
    tri (weak1, strong0) PLL_LOCKG = p_up_tmp;

    wire PROGB_GLBL;
    wire CCLKO_GLBL;
    wire FCSBO_GLBL;
    wire [3:0] DO_GLBL;
    wire [3:0] DI_GLBL;
   
    reg GSR_int;
    reg GTS_int;
    reg PRLD_int;
    reg GRESTORE_int;

//--------   JTAG Globals --------------
    wire JTAG_TDO_GLBL;
    wire JTAG_TCK_GLBL;
    wire JTAG_TDI_GLBL;
    wire JTAG_TMS_GLBL;
    wire JTAG_TRST_GLBL;

    reg JTAG_CAPTURE_GLBL;
    reg JTAG_RESET_GLBL;
    reg JTAG_SHIFT_GLBL;
    reg JTAG_UPDATE_GLBL;
    reg JTAG_RUNTEST_GLBL;

    reg JTAG_SEL1_GLBL = 0;
    reg JTAG_SEL2_GLBL = 0 ;
    reg JTAG_SEL3_GLBL = 0;
    reg JTAG_SEL4_GLBL = 0;

    reg JTAG_USER_TDO1_GLBL = 1'bz;
    reg JTAG_USER_TDO2_GLBL = 1'bz;
    reg JTAG_USER_TDO3_GLBL = 1'bz;
    reg JTAG_USER_TDO4_GLBL = 1'bz;

    assign (strong1, weak0) GSR = GSR_int;
    assign (strong1, weak0) GTS = GTS_int;
    assign (weak1, weak0) PRLD = PRLD_int;
    assign (strong1, weak0) GRESTORE = GRESTORE_int;

    initial begin
	GSR_int = 1'b1;
	PRLD_int = 1'b1;
	#(ROC_WIDTH)
	GSR_int = 1'b0;
	PRLD_int = 1'b0;
    end

    initial begin
	GTS_int = 1'b1;
	#(TOC_WIDTH)
	GTS_int = 1'b0;
    end

    initial begin 
	GRESTORE_int = 1'b0;
	#(GRES_START);
	GRESTORE_int = 1'b1;
	#(GRES_WIDTH);
	GRESTORE_int = 1'b0;
    end

endmodule
`endif
