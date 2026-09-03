// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2024 Advanced Micro Devices, Inc. All Rights Reserved.
// --------------------------------------------------------------------------------
// Tool Version: Vivado v.2024.2 (win64) Build 5239630 Fri Nov 08 22:35:27 MST 2024
// Date        : Thu Sep  3 12:09:56 2026
// Host        : DESKTOP-ADCQ3LG running 64-bit major release  (build 9200)
// Command     : write_verilog -force -mode funcsim
//               g:/EEG/Workflow/prj/eeg_ssvep_2to16/output/vivado/ip/parameter_store_bmg/parameter_store_bmg_sim_netlist.v
// Design      : parameter_store_bmg
// Purpose     : This verilog netlist is a functional simulation representation of the design and should not be modified
//               or synthesized. This netlist cannot be used for SDF annotated simulation.
// Device      : xc7z020clg400-1
// --------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

(* CHECK_LICENSE_TYPE = "parameter_store_bmg,blk_mem_gen_v8_4_9,{}" *) (* downgradeipidentifiedwarnings = "yes" *) (* x_core_info = "blk_mem_gen_v8_4_9,Vivado 2024.2" *) 
(* NotValidForBitStream *)
module parameter_store_bmg
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
  parameter_store_bmg_blk_mem_gen_v8_4_9 U0
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
`pragma protect encoding = (enctype = "BASE64", line_length = 76, bytes = 31344)
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
