`timescale 1ns / 1ps

//==============================================================================
// Module      : arinc_tx_core
// File        : A429Top_TX.v
// Project     : starter_hdl_project
// Description : ARINC 429 TX core wrapper，连接外部 TX FIFO 与底层 TX 模块。
//
// Scope:
//   - 从外部 TX FIFO 获取 32-bit ARINC word。
//   - 将 CONTROL WORD REGISTER 的 TX 配置位传递给 TX 模块。
//   - 输出 ARINC 429 TX differential pair。
//   - 本模块不保存 FIFO 数据，也不实现 SPI command decode。
//
// Spec Trace:
//   - CR3  : TX parity bit enable。
//   - CR9  : TX parity select。
//   - CR10 : TX data rate select。
//   - CR11 : ARINC label bit order。
//
// Notes:
//   - op_reset 为高电平有效，传入 TX 时转换为低电平有效 RESET_N0。
//   - iCfg_Reg[0]、[1]、[2] 分别映射 DATARATE、PARITYEN、ODD_N_EVEN。
//==============================================================================

module arinc_tx_core(
        // Clock and reset
        input           iClk,
        input           op_reset,
        input           i_force_null,

        // Control interface
        input   [7:0]   iCfg_Reg,
        input           iTx_Enable,
        input           iLabel_Bit_Order,

        // External TX FIFO interface
        input   [31:0]  i_tx_fifo_data,
        input           i_tx_fifo_empty,
        output          o_tx_fifo_rden,

        // ARINC 429 line output
        output          oArinc429_Txp,
        output          oArinc429_Txn
    );

//------------------------------------------------------------------------------
// Internal Signals
//------------------------------------------------------------------------------
wire                    TX_Rdn;

//------------------------------------------------------------------------------
// FIFO Read Handshake
//------------------------------------------------------------------------------
assign o_tx_fifo_rden = TX_Rdn;

//------------------------------------------------------------------------------
// TX Core Instance
//------------------------------------------------------------------------------
TX A429_TX(
        .CLK            (iClk),
        .RESET_N0       (!op_reset),

        .TXA            (oArinc429_Txp),
        .TXB            (oArinc429_Txn),

        .ENTX           (iTx_Enable),
        .DATARATE       (iCfg_Reg[0]),
        .PARITYEN       (iCfg_Reg[1]),
        .ODD_N_EVEN     (iCfg_Reg[2]),

        .oRdn           (TX_Rdn),
        .iFifo_Empty    (i_tx_fifo_empty),
        .iData          (i_tx_fifo_data),
        .FORCE_NULL     (i_force_null),
        .LABEL_BIT_ORDER(iLabel_Bit_Order)
     );

endmodule
