// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2024 Advanced Micro Devices, Inc. All Rights Reserved.
// --------------------------------------------------------------------------------
// Tool Version: Vivado v.2024.2 (win64) Build 5239630 Fri Nov 08 22:35:27 MST 2024
// Date        : Thu Sep  3 12:09:55 2026
// Host        : DESKTOP-ADCQ3LG running 64-bit major release  (build 9200)
// Command     : write_verilog -force -mode funcsim -rename_top feature_bank2_bmg -prefix
//               feature_bank2_bmg_ feature_bank0_bmg_sim_netlist.v
// Design      : feature_bank0_bmg
// Purpose     : This verilog netlist is a functional simulation representation of the design and should not be modified
//               or synthesized. This netlist cannot be used for SDF annotated simulation.
// Device      : xc7z020clg400-1
// --------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

(* CHECK_LICENSE_TYPE = "feature_bank0_bmg,blk_mem_gen_v8_4_9,{}" *) (* downgradeipidentifiedwarnings = "yes" *) (* x_core_info = "blk_mem_gen_v8_4_9,Vivado 2024.2" *) 
(* NotValidForBitStream *)
module feature_bank2_bmg
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
  feature_bank2_bmg_blk_mem_gen_v8_4_9 U0
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
iU6bOgL/aDZTKUcNr7kh16WIkLvT92+vwFg=
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
