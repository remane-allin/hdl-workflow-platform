// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2024 Advanced Micro Devices, Inc. All Rights Reserved.
// --------------------------------------------------------------------------------
// Tool Version: Vivado v.2024.2 (win64) Build 5239630 Fri Nov 08 22:35:27 MST 2024
// Date        : Thu Sep  3 12:09:55 2026
// Host        : DESKTOP-ADCQ3LG running 64-bit major release  (build 9200)
// Command     : write_verilog -force -mode funcsim -rename_top feature_bank1_bmg -prefix
//               feature_bank1_bmg_ feature_bank0_bmg_sim_netlist.v
// Design      : feature_bank0_bmg
// Purpose     : This verilog netlist is a functional simulation representation of the design and should not be modified
//               or synthesized. This netlist cannot be used for SDF annotated simulation.
// Device      : xc7z020clg400-1
// --------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

(* CHECK_LICENSE_TYPE = "feature_bank0_bmg,blk_mem_gen_v8_4_9,{}" *) (* downgradeipidentifiedwarnings = "yes" *) (* x_core_info = "blk_mem_gen_v8_4_9,Vivado 2024.2" *) 
(* NotValidForBitStream *)
module feature_bank1_bmg
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
  feature_bank1_bmg_blk_mem_gen_v8_4_9 U0
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
YSzf2dozBDkAOiNwU+W1+3TJFvbP/+KHL7c=
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
