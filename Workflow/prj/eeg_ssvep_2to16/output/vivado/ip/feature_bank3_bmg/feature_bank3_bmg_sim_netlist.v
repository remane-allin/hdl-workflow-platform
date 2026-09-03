// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2024 Advanced Micro Devices, Inc. All Rights Reserved.
// --------------------------------------------------------------------------------
// Tool Version: Vivado v.2024.2 (win64) Build 5239630 Fri Nov 08 22:35:27 MST 2024
// Date        : Thu Sep  3 12:09:55 2026
// Host        : DESKTOP-ADCQ3LG running 64-bit major release  (build 9200)
// Command     : write_verilog -force -mode funcsim -rename_top feature_bank3_bmg -prefix
//               feature_bank3_bmg_ feature_bank0_bmg_sim_netlist.v
// Design      : feature_bank0_bmg
// Purpose     : This verilog netlist is a functional simulation representation of the design and should not be modified
//               or synthesized. This netlist cannot be used for SDF annotated simulation.
// Device      : xc7z020clg400-1
// --------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

(* CHECK_LICENSE_TYPE = "feature_bank0_bmg,blk_mem_gen_v8_4_9,{}" *) (* downgradeipidentifiedwarnings = "yes" *) (* x_core_info = "blk_mem_gen_v8_4_9,Vivado 2024.2" *) 
(* NotValidForBitStream *)
module feature_bank3_bmg
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
  feature_bank3_bmg_blk_mem_gen_v8_4_9 U0
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
`pragma protect encoding = (enctype = "BASE64", line_length = 76, bytes = 28640)
`pragma protect data_block
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
gbVvYLlWf1eUUG38BRjR6RmmCr5+N4EBkuQ=
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
