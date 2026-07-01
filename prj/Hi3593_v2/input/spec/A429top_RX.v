`timescale 1ns / 1ps

//==============================================================================
// Module      : arinc_rx_core
// File        : A429top_RX.v
// Project     : starter_hdl_project
// Description : ARINC 429 RX core wrapper，连接底层 RX 模块与外部 RX FIFO。
//
// Scope:
//   - 接收 ARINC 429 differential pair，并输出 32-bit RX word。
//   - 将 label recognition、decoder、parity 和 data rate 控制位传递给 RX 模块。
//   - 输出 decoded label，供外部 label table 匹配。
//   - 本模块不保存 RX FIFO 数据，也不实现 label table。
//
// Spec Trace:
//   - CR0  : RX data rate select。
//   - CR2  : Label recognition enable。
//   - CR4  : RX parity check enable。
//   - CR6  : RX decoder enable。
//   - CR7/8: Decoder match bits。
//   - CR11 : ARINC label bit order。
//
// Notes:
//   - op_reset 为高电平有效，传入 RX 时转换为低电平有效 RESET_N0。
//   - RX 覆写策略由下游 FIFO 处理，本 wrapper 只转发写请求。
//==============================================================================

module arinc_rx_core(
        // Clock, reset, and ARINC line input
        input          iClk,
        input          op_reset,
        input          iA429_RX_P,
        input          iA429_RX_N,

        // Control interface
        input          i_parity_en,
        input          i_label_rec_en,
        input          i_label_match,
        input          i_label_bit_order,
        input          i_data_rate_sel,
        input          i_decoder_en,
        input          i_decoder_match_b10,
        input          i_decoder_match_b9,

        // External RX FIFO interface
        output         o_rx_data_valid,
        output [31:0]  o_rx_data,
        input          i_rx_fifo_full,

        // Decoded label output
        output [7:0]   o_decoded_label
    );

//------------------------------------------------------------------------------
// Internal Signals
//------------------------------------------------------------------------------
wire                   RX_Wr;
wire [31:0]            RX_Data;

//------------------------------------------------------------------------------
// RX FIFO Write Interface
//------------------------------------------------------------------------------
assign o_rx_data_valid = RX_Wr;
assign o_rx_data = RX_Data;

//------------------------------------------------------------------------------
// RX Core Instance
//------------------------------------------------------------------------------
RX RX_Channel (
    .CLK                    (iClk),
    .RESET_N0               (!op_reset),

    .RXA                    (iA429_RX_P),
    .RXB                    (iA429_RX_N),

    .PARITYEN               (i_parity_en),
    .ODD_N_EVEN             (1'b0),
    .oWrn                   (RX_Wr),
    .oData                  (RX_Data),

    .i_rx_fifo_full         (i_rx_fifo_full),

    .i_label_rec_en         (i_label_rec_en),
    .i_label_match          (i_label_match),
    .o_decoded_label        (o_decoded_label),
    .LABEL_BIT_ORDER        (i_label_bit_order),
    .DATARATE               (i_data_rate_sel),

    .i_decoder_en           (i_decoder_en),
    .i_decoder_match_b10    (i_decoder_match_b10),
    .i_decoder_match_b9     (i_decoder_match_b9)
    );

endmodule
