// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2024 Advanced Micro Devices, Inc. All Rights Reserved.
// --------------------------------------------------------------------------------
// Tool Version: Vivado v.2024.2 (win64) Build 5239630 Fri Nov 08 22:35:27 MST 2024
// Date        : Thu Sep  3 12:09:56 2026
// Host        : DESKTOP-ADCQ3LG running 64-bit major release  (build 9200)
// Command     : write_verilog -force -mode funcsim
//               g:/EEG/Workflow/prj/eeg_ssvep_2to16/output/vivado/ip/feature_bank0_bmg/feature_bank0_bmg_sim_netlist.v
// Design      : feature_bank0_bmg
// Purpose     : This verilog netlist is a functional simulation representation of the design and should not be modified
//               or synthesized. This netlist cannot be used for SDF annotated simulation.
// Device      : xc7z020clg400-1
// --------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

(* CHECK_LICENSE_TYPE = "feature_bank0_bmg,blk_mem_gen_v8_4_9,{}" *) (* downgradeipidentifiedwarnings = "yes" *) (* x_core_info = "blk_mem_gen_v8_4_9,Vivado 2024.2" *) 
(* NotValidForBitStream *)
module feature_bank0_bmg
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
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTA CLK" *) (* x_interface_mode = "slave BRAM_PORTA" *) (* x_interface_parameter = "XIL_INTERFACENAME BRAM_PORTA, MEM_ADDRESS_MODE BYTE_ADDRESS, MEM_SIZE 8192, MEM_WIDTH 32, MEM_ECC NONE, MASTER_TYPE OTHER, READ_LATENCY 1" *) input clka;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTA EN" *) input ena;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTA WE" *) input [0:0]wea;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTA ADDR" *) input [10:0]addra;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTA DIN" *) input [15:0]dina;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTA DOUT" *) output [15:0]douta;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTB CLK" *) (* x_interface_mode = "slave BRAM_PORTB" *) (* x_interface_parameter = "XIL_INTERFACENAME BRAM_PORTB, MEM_ADDRESS_MODE BYTE_ADDRESS, MEM_SIZE 8192, MEM_WIDTH 32, MEM_ECC NONE, MASTER_TYPE OTHER, READ_LATENCY 1" *) input clkb;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTB EN" *) input enb;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTB WE" *) input [0:0]web;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTB ADDR" *) input [10:0]addrb;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTB DIN" *) input [15:0]dinb;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTB DOUT" *) output [15:0]doutb;

  wire [10:0]addra;
  wire [10:0]addrb;
  wire clka;
  wire clkb;
  wire [15:0]dina;
  wire [15:0]dinb;
  wire [15:0]douta;
  wire [15:0]doutb;
  wire ena;
  wire enb;
  wire [0:0]wea;
  wire [0:0]web;
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
  wire [10:0]NLW_U0_rdaddrecc_UNCONNECTED;
  wire [3:0]NLW_U0_s_axi_bid_UNCONNECTED;
  wire [1:0]NLW_U0_s_axi_bresp_UNCONNECTED;
  wire [10:0]NLW_U0_s_axi_rdaddrecc_UNCONNECTED;
  wire [15:0]NLW_U0_s_axi_rdata_UNCONNECTED;
  wire [3:0]NLW_U0_s_axi_rid_UNCONNECTED;
  wire [1:0]NLW_U0_s_axi_rresp_UNCONNECTED;

  (* C_ADDRA_WIDTH = "11" *) 
  (* C_ADDRB_WIDTH = "11" *) 
  (* C_ALGORITHM = "1" *) 
  (* C_AXI_ID_WIDTH = "4" *) 
  (* C_AXI_SLAVE_TYPE = "0" *) 
  (* C_AXI_TYPE = "1" *) 
  (* C_BYTE_SIZE = "9" *) 
  (* C_COMMON_CLK = "0" *) 
  (* C_COUNT_18K_BRAM = "0" *) 
  (* C_COUNT_36K_BRAM = "1" *) 
  (* C_CTRL_ECC_ALGO = "NONE" *) 
  (* C_DEFAULT_DATA = "0" *) 
  (* C_DISABLE_WARN_BHV_COLL = "0" *) 
  (* C_DISABLE_WARN_BHV_RANGE = "0" *) 
  (* C_ELABORATION_DIR = "./" *) 
  (* C_ENABLE_32BIT_ADDRESS = "0" *) 
  (* C_EN_DEEPSLEEP_PIN = "0" *) 
  (* C_EN_ECC_PIPE = "0" *) 
  (* C_EN_RDADDRA_CHG = "0" *) 
  (* C_EN_RDADDRB_CHG = "0" *) 
  (* C_EN_SAFETY_CKT = "0" *) 
  (* C_EN_SHUTDOWN_PIN = "0" *) 
  (* C_EN_SLEEP_PIN = "0" *) 
  (* C_EST_POWER_SUMMARY = "Estimated Power for IP     :     5.6824 mW" *) 
  (* C_FAMILY = "zynq" *) 
  (* C_HAS_AXI_ID = "0" *) 
  (* C_HAS_ENA = "1" *) 
  (* C_HAS_ENB = "1" *) 
  (* C_HAS_INJECTERR = "0" *) 
  (* C_HAS_MEM_OUTPUT_REGS_A = "1" *) 
  (* C_HAS_MEM_OUTPUT_REGS_B = "1" *) 
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
  (* C_INIT_FILE = "feature_bank0_bmg.mem" *) 
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
  (* C_READ_WIDTH_A = "16" *) 
  (* C_READ_WIDTH_B = "16" *) 
  (* C_RSTRAM_A = "0" *) 
  (* C_RSTRAM_B = "0" *) 
  (* C_RST_PRIORITY_A = "CE" *) 
  (* C_RST_PRIORITY_B = "CE" *) 
  (* C_SIM_COLLISION_CHECK = "ALL" *) 
  (* C_USE_BRAM_BLOCK = "0" *) 
  (* C_USE_BYTE_WEA = "0" *) 
  (* C_USE_BYTE_WEB = "0" *) 
  (* C_USE_DEFAULT_DATA = "0" *) 
  (* C_USE_ECC = "0" *) 
  (* C_USE_SOFTECC = "0" *) 
  (* C_USE_URAM = "0" *) 
  (* C_WEA_WIDTH = "1" *) 
  (* C_WEB_WIDTH = "1" *) 
  (* C_WRITE_DEPTH_A = "2048" *) 
  (* C_WRITE_DEPTH_B = "2048" *) 
  (* C_WRITE_MODE_A = "READ_FIRST" *) 
  (* C_WRITE_MODE_B = "READ_FIRST" *) 
  (* C_WRITE_WIDTH_A = "16" *) 
  (* C_WRITE_WIDTH_B = "16" *) 
  (* C_XDEVICEFAMILY = "zynq" *) 
  (* downgradeipidentifiedwarnings = "yes" *) 
  (* is_du_within_envelope = "true" *) 
  feature_bank0_bmg_blk_mem_gen_v8_4_9 U0
       (.addra(addra),
        .addrb(addrb),
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
        .rdaddrecc(NLW_U0_rdaddrecc_UNCONNECTED[10:0]),
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
        .s_axi_rdaddrecc(NLW_U0_s_axi_rdaddrecc_UNCONNECTED[10:0]),
        .s_axi_rdata(NLW_U0_s_axi_rdata_UNCONNECTED[15:0]),
        .s_axi_rid(NLW_U0_s_axi_rid_UNCONNECTED[3:0]),
        .s_axi_rlast(NLW_U0_s_axi_rlast_UNCONNECTED),
        .s_axi_rready(1'b0),
        .s_axi_rresp(NLW_U0_s_axi_rresp_UNCONNECTED[1:0]),
        .s_axi_rvalid(NLW_U0_s_axi_rvalid_UNCONNECTED),
        .s_axi_sbiterr(NLW_U0_s_axi_sbiterr_UNCONNECTED),
        .s_axi_wdata({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .s_axi_wlast(1'b0),
        .s_axi_wready(NLW_U0_s_axi_wready_UNCONNECTED),
        .s_axi_wstrb(1'b0),
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
`pragma protect encoding = (enctype = "BASE64", line_length = 76, bytes = 28912)
`pragma protect data_block
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
OzsS78jOuYP/lr530Q==
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
