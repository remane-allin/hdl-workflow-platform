// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2024 Advanced Micro Devices, Inc. All Rights Reserved.
// --------------------------------------------------------------------------------
// Tool Version: Vivado v.2024.2 (win64) Build 5239630 Fri Nov 08 22:35:27 MST 2024
// Date        : Thu Sep  3 12:09:55 2026
// Host        : DESKTOP-ADCQ3LG running 64-bit major release  (build 9200)
// Command     : write_verilog -force -mode funcsim -rename_top program_store_bmg -prefix
//               program_store_bmg_ parameter_store_bmg_sim_netlist.v
// Design      : parameter_store_bmg
// Purpose     : This verilog netlist is a functional simulation representation of the design and should not be modified
//               or synthesized. This netlist cannot be used for SDF annotated simulation.
// Device      : xc7z020clg400-1
// --------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

(* CHECK_LICENSE_TYPE = "parameter_store_bmg,blk_mem_gen_v8_4_9,{}" *) (* downgradeipidentifiedwarnings = "yes" *) (* x_core_info = "blk_mem_gen_v8_4_9,Vivado 2024.2" *) 
(* NotValidForBitStream *)
module program_store_bmg
   (clka,
    ena,
    wea,
    addra,
    dina,
    clkb,
    enb,
    addrb,
    doutb);
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTA CLK" *) (* x_interface_mode = "slave BRAM_PORTA" *) (* x_interface_parameter = "XIL_INTERFACENAME BRAM_PORTA, MEM_ADDRESS_MODE BYTE_ADDRESS, MEM_SIZE 8192, MEM_WIDTH 32, MEM_ECC NONE, MASTER_TYPE OTHER, READ_LATENCY 1" *) input clka;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTA EN" *) input ena;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTA WE" *) input [0:0]wea;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTA ADDR" *) input [8:0]addra;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTA DIN" *) input [63:0]dina;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTB CLK" *) (* x_interface_mode = "slave BRAM_PORTB" *) (* x_interface_parameter = "XIL_INTERFACENAME BRAM_PORTB, MEM_ADDRESS_MODE BYTE_ADDRESS, MEM_SIZE 8192, MEM_WIDTH 32, MEM_ECC NONE, MASTER_TYPE OTHER, READ_LATENCY 1" *) input clkb;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTB EN" *) input enb;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTB ADDR" *) input [8:0]addrb;
  (* x_interface_info = "xilinx.com:interface:bram:1.0 BRAM_PORTB DOUT" *) output [63:0]doutb;

  wire [8:0]addra;
  wire [8:0]addrb;
  wire clka;
  wire clkb;
  wire [63:0]dina;
  wire [63:0]doutb;
  wire ena;
  wire enb;
  wire [0:0]wea;
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
  wire [63:0]NLW_U0_douta_UNCONNECTED;
  wire [8:0]NLW_U0_rdaddrecc_UNCONNECTED;
  wire [3:0]NLW_U0_s_axi_bid_UNCONNECTED;
  wire [1:0]NLW_U0_s_axi_bresp_UNCONNECTED;
  wire [8:0]NLW_U0_s_axi_rdaddrecc_UNCONNECTED;
  wire [63:0]NLW_U0_s_axi_rdata_UNCONNECTED;
  wire [3:0]NLW_U0_s_axi_rid_UNCONNECTED;
  wire [1:0]NLW_U0_s_axi_rresp_UNCONNECTED;

  (* C_ADDRA_WIDTH = "9" *) 
  (* C_ADDRB_WIDTH = "9" *) 
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
  (* C_EST_POWER_SUMMARY = "Estimated Power for IP     :     6.966099 mW" *) 
  (* C_FAMILY = "zynq" *) 
  (* C_HAS_AXI_ID = "0" *) 
  (* C_HAS_ENA = "1" *) 
  (* C_HAS_ENB = "1" *) 
  (* C_HAS_INJECTERR = "0" *) 
  (* C_HAS_MEM_OUTPUT_REGS_A = "0" *) 
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
  (* C_INIT_FILE = "parameter_store_bmg.mem" *) 
  (* C_INIT_FILE_NAME = "no_coe_file_loaded" *) 
  (* C_INTERFACE_TYPE = "0" *) 
  (* C_LOAD_INIT_FILE = "0" *) 
  (* C_MEM_TYPE = "1" *) 
  (* C_MUX_PIPELINE_STAGES = "0" *) 
  (* C_PRIM_TYPE = "1" *) 
  (* C_READ_DEPTH_A = "512" *) 
  (* C_READ_DEPTH_B = "512" *) 
  (* C_READ_LATENCY_A = "1" *) 
  (* C_READ_LATENCY_B = "1" *) 
  (* C_READ_WIDTH_A = "64" *) 
  (* C_READ_WIDTH_B = "64" *) 
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
  (* C_WRITE_DEPTH_A = "512" *) 
  (* C_WRITE_DEPTH_B = "512" *) 
  (* C_WRITE_MODE_A = "NO_CHANGE" *) 
  (* C_WRITE_MODE_B = "WRITE_FIRST" *) 
  (* C_WRITE_WIDTH_A = "64" *) 
  (* C_WRITE_WIDTH_B = "64" *) 
  (* C_XDEVICEFAMILY = "zynq" *) 
  (* downgradeipidentifiedwarnings = "yes" *) 
  (* is_du_within_envelope = "true" *) 
  program_store_bmg_blk_mem_gen_v8_4_9 U0
       (.addra(addra),
        .addrb(addrb),
        .clka(clka),
        .clkb(clkb),
        .dbiterr(NLW_U0_dbiterr_UNCONNECTED),
        .deepsleep(1'b0),
        .dina(dina),
        .dinb({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .douta(NLW_U0_douta_UNCONNECTED[63:0]),
        .doutb(doutb),
        .eccpipece(1'b0),
        .ena(ena),
        .enb(enb),
        .injectdbiterr(1'b0),
        .injectsbiterr(1'b0),
        .rdaddrecc(NLW_U0_rdaddrecc_UNCONNECTED[8:0]),
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
        .s_axi_rdaddrecc(NLW_U0_s_axi_rdaddrecc_UNCONNECTED[8:0]),
        .s_axi_rdata(NLW_U0_s_axi_rdata_UNCONNECTED[63:0]),
        .s_axi_rid(NLW_U0_s_axi_rid_UNCONNECTED[3:0]),
        .s_axi_rlast(NLW_U0_s_axi_rlast_UNCONNECTED),
        .s_axi_rready(1'b0),
        .s_axi_rresp(NLW_U0_s_axi_rresp_UNCONNECTED[1:0]),
        .s_axi_rvalid(NLW_U0_s_axi_rvalid_UNCONNECTED),
        .s_axi_sbiterr(NLW_U0_s_axi_sbiterr_UNCONNECTED),
        .s_axi_wdata({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .s_axi_wlast(1'b0),
        .s_axi_wready(NLW_U0_s_axi_wready_UNCONNECTED),
        .s_axi_wstrb(1'b0),
        .s_axi_wvalid(1'b0),
        .sbiterr(NLW_U0_sbiterr_UNCONNECTED),
        .shutdown(1'b0),
        .sleep(1'b0),
        .wea(wea),
        .web(1'b0));
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
`pragma protect encoding = (enctype = "BASE64", line_length = 76, bytes = 31040)
`pragma protect data_block
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
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
