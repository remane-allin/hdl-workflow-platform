`timescale 1ns / 1ps

//==============================================================================
// Module      : RX
// File        : RX.v
// Project     : starter_hdl_project
// Description : ARINC 429 RX protocol core，接收并过滤 32-bit ARINC word。
//
// Scope:
//   - 解码 RXA/RXB line state，重建 ARINC 429 word。
//   - 支持 high speed / low speed data rate。
//   - 支持 parity check、label recognition、decoder bit match 和 CR11 label bit order。
//   - 产生 RX FIFO write request 和 decoded label。
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
//   - RESET_N0 为低电平有效异步 reset。
//   - FIFO full 时仍输出写请求，覆写策略由下游 FIFO 处理。
//   - storage_reg[31] 在 parity check enabled 时用于标记 parity error。
//==============================================================================
module RX(
		CLK             , 		// 时钟信号 1MHz (重构后统一基准)
		RESET_N0        ,		// 复位信号 低电平有效

		RXA             ,		// ARINC 429 RX 正端口
		RXB             ,		// ARINC 429 RX 负端口

		PARITYEN        ,		// RX 奇偶校验使能 0:禁止; 1:使能
		ODD_N_EVEN      ,		// RX 奇偶校验模式 0:奇校验; 1:偶校验

		oWrn            ,		// RX DMA FIFO 写信号
		oData           ,		// RX DMA FIFO 32位数据

		// 外部FIFO满标志输入
		i_rx_fifo_full  ,		// 外部FIFO满标志

		// 标签识别相关接口
		i_label_rec_en  ,    	// 标签识别使能
		i_label_match   ,     	// 标签匹配结果
		o_decoded_label ,   	// 输出解码后的标签
		LABEL_BIT_ORDER ,   	// ARINC 429标签位顺序控制 (CR11): 0=位反转; 1=保持原样
		DATARATE        ,		// 数据速率选择 (CR0): 0=高速(100kbps); 1=低速(12.5kbps)

		// 解码器相关接口
		i_decoder_en    ,    	// 解码器使能 (CR6)
		i_decoder_match_b10,	// 解码器匹配位10 (CR7)
		i_decoder_match_b9  	// 解码器匹配位9 (CR8)
		);
//------------------------------------------------------------------------------
// Parameters
//------------------------------------------------------------------------------
	// RX word processing FSM。
	parameter[3:0]   idle0           = 0; // 初始状态
   parameter[3:0]   branch          = 1; // 决定接收标签或数据
   parameter[3:0]   label_A         = 2; // 接收标签
   parameter[3:0]   arinc_A         = 3; // 接收数据
   parameter[3:0]   parity          = 4; // 奇偶校验
   parameter[3:0]   check_label     = 5; // 检查标签
   parameter[3:0]   wait_for_gap    = 6; // 等待 ARINC word gap。
	// RX FIFO write FSM。
   parameter[1:0]   idle_state      = 0; // 初始状态
   parameter[1:0]   fifo_A          = 1; // 写DMA FIFO
   parameter[1:0]   finish          = 2; // 完成一个字
	// ARINC line state detect FSM。
   parameter[2:0]   dataProcIdle    = 0; // 初始状态
   parameter[2:0]   dataProcWait    = 1;
   parameter[2:0]   dataProc        = 2;
   parameter[2:0]   dataProcWid     = 3;
	// Data rate check FSM。
	parameter[2:0]   rateCntIdle     = 0;
   parameter[2:0]   rateCntStart    = 1;
   parameter[2:0]   rateCntStop     = 2;
//------------------------------------------------------------------------------
// Port Declarations
//------------------------------------------------------------------------------
   input            CLK             ; // 核心429时钟 (1MHz基准)
   input            RESET_N0        ; // 主异步低电平有效复位

   input            RXA             ; // ARINC接收输入A
   input            RXB             ; // ARINC接收输入B

   input            PARITYEN        ; // 0 = 第32位是数据; 1 = 第32位是奇偶校验
   input            ODD_N_EVEN      ; // 奇偶校验: 0 = 奇校验; 1 = 偶校验

	output           oWrn            ; // RX DMA FIFO 写信号
	output[31:0]     oData           ; // RX DMA FIFO 32位数据

	// 外部 FIFO 满标志输入。
	input            i_rx_fifo_full  ; // 外部FIFO满标志

	// Label recognition 相关端口。
	input            i_label_rec_en  ; // 标签识别使能
	input            i_label_match   ; // 标签匹配结果
	output [7:0]     o_decoded_label ; // 输出解码后的标签
	input            LABEL_BIT_ORDER ; // ARINC 429标签位顺序控制 (CR11): 0=位反转; 1=保持原样
	input            DATARATE        ; // 数据速率选择 (CR0): 0=高速(100kbps); 1=低速(12.5kbps)

	// Decoder 相关端口。
	input            i_decoder_en    ; // 解码器使能 (CR6)
	input            i_decoder_match_b10; // 解码器匹配位10 (CR7)
	input            i_decoder_match_b9 ; // 解码器匹配位9 (CR8)

//------------------------------------------------------------------------------
// Internal Registers
//------------------------------------------------------------------------------
   reg  [2:0]       data_process_state  ; // 数据处理状态机
   reg  [2:0]       clkRateCntState     ; // 时钟速率计数状态机
   // word_cnt 已由 null_cnt 字间隔逻辑替代。

   reg              CLK_en              ; // 时钟使能
   reg              CLK_en_next         ; // 时钟使能下一状态

   reg  [3:0]       rx_present_state    ; // RX状态机当前状态
   reg  [3:0]       rx_next_state       ; // RX状态机下一状态
   reg  [1:0]       wrfifo_present_state; // 写FIFO状态机当前状态
   reg  [1:0]       wrfifo_next_state   ; // 写FIFO状态机下一状态
   reg  [31:0]      storage_reg         ; // 存储寄存器
   reg  [5:0]       bit_cnt             ; // 位计数器
   reg  [10:0]      rate_cnt            ; // 保留用于兼容性，但在1MHz下不使用
   reg              inc_bitcnt          ; // 位计数器递增使能
   reg              clr_bitcnt          ; // 位计数器清零使能
   // clr_wordcnt 和 wordcnt_clr 已由 inc_nullcnt / clr_nullcnt 替代。

   reg              shift_label         ; // 标签移位使能
   reg              shift_arinc         ; // ARINC数据移位使能
   reg  [31:0]      rx_din              ; // 接收数据输入
   reg              fifo_write_en       ; // FIFO写使能 低电平有效

   // 待写入 FIFO 的最终数据，包含 parity error 标记。
   wire [31:0]      data_to_write       ; // 经过奇偶校验标记处理后的数据
   reg  [9:0]       timeout             ; // 超时计数器
   reg              inc_timeout         ; // 超时计数器递增使能
   reg              clr_timeout         ; // 超时计数器清零使能

   reg              parity_val          ; // 奇偶校验值

   reg              calc_parity         ; // 计算奇偶校验使能

   reg              RXA_in              ; // RXA输入寄存器
   reg              RXA_in1             ; // RXA输入寄存器1
   reg              RXB_in              ; // RXB输入寄存器
   reg              RXB_in1             ; // RXB输入寄存器1

	reg              start_wrfifo        ; // 开始写FIFO信号

	// 解码器相关信号
	wire             decoder_bit_9       ; // ARINC数据字第9位
	wire             decoder_bit_10      ; // ARINC数据字第10位
	wire             decoder_match       ; // 解码器匹配结果
	wire             label_pass          ; // 标签匹配条件
	wire             decoder_pass        ; // 解码器匹配条件

   reg  [7:0]       zeroHighCnt         ; // 零高电平计数
   reg  [7:0]       zeroLowCnt          ; // 零低电平计数
   reg  [7:0]       onesHighCnt         , // 一高电平计数
                    onesLowCnt          ; // 一低电平计数
   reg  [7:0]       nullHighCnt         , // 空闲高电平计数
                    nullLowCnt          ; // 空闲低电平计数
   reg  [7:0]       clkRateCnt          ; // 时钟速率计数
	
	reg              ones_dat_syn        , // 逻辑1数据同步寄存器
	                 ones_dat_syn1       ; // 逻辑1数据同步寄存器1
   reg              zero_dat_syn        , // 逻辑0数据同步寄存器
                    zero_dat_syn1       ; // 逻辑0数据同步寄存器1
   reg              null_dat_r1         , // 空闲数据寄存器1
                    null_dat_r2         ; // 空闲数据寄存器2

	reg              shift_data_auto     ; // 自动数据移位信号
   reg              data_valid_auto     ; // 自动数据有效信号
   reg              ones_det_auto       , // 自动逻辑1检测
                    zero_det_auto       , // 自动逻辑0检测
                    reg_ones_det_auto   , // 寄存器逻辑1检测
                    reg_zero_det_auto   ; // 寄存器逻辑0检测
   reg              null_dat_fall_next  ; // 空闲数据下降沿下一状态
   reg  [2:0]       data_det_widCnt     ; // 数据检测宽度计数器
	reg  [7:0]       clkRateCntReg       ; // 时钟速率计数寄存器
	reg  [5:0]       null_cnt            ; // ARINC word gap 计数器。

	reg  [9:0]       timeoutVal          ; // 超时值
   reg              reg0_data_valid_auto, // 数据有效自动寄存器0
                    reg1_data_valid_auto; // 数据有效自动寄存器1
	reg  [7:0]       nullLowCntReg       ; // 空闲低电平计数寄存器
//------------------------------------------------------------------------------
// Internal Wires
//------------------------------------------------------------------------------
   wire             parity_equal        ; // 奇偶校验相等信号
   wire             ones_dat            ; // 逻辑1数据信号
   wire             zero_dat            ; // 逻辑0数据信号
   wire             null_dat            ; // 空闲数据信号

   wire [7:0]       qClkRateCnt         ; // 时钟速率计数查询信号

	wire             shift_data          ; // 数据移位信号
   wire             data_valid          ; // 数据有效信号

   wire             null_dat_fall       , // 空闲数据下降沿
                    null_dat_rise       ; // 空闲数据上升沿

   // 字间隔控制信号。
   reg              inc_nullcnt         ; // 字间隔计数器递增信号
   reg              clr_nullcnt         ; // 字间隔计数器清零信号

   wire [7:0]       received_label      ; // 从寄存器中获取的原始标签
   wire [7:0]       reversed_label      ; // 位反转后的标签

   wire [7:0]       dynamic_threshold   ; // 根据DATARATE动态选择的位宽验证门限
//------------------------------------------------------------------------------
// Output and Decode Assignments
//------------------------------------------------------------------------------

	assign  oData               = rx_din                 ;
	// 更新FIFO写入条件：同时考虑标签识别和解码器匹配
	// 只有当标签匹配（如果使能）AND 解码器匹配（如果使能）时才写入FIFO
	assign  oWrn                = (~fifo_write_en) &&
	                             ((!i_label_rec_en) || (i_label_rec_en && i_label_match)) &&
	                             decoder_match;

	assign received_label = storage_reg[7:0];
	assign reversed_label = {received_label[0], received_label[1], received_label[2], received_label[3],
	                         received_label[4], received_label[5], received_label[6], received_label[7]};
	// 根据 LABEL_BIT_ORDER (CR11) 选择最终输出的解码标签
	assign o_decoded_label = LABEL_BIT_ORDER ? received_label : reversed_label;

	// 提取ARINC数据字的第9位和第10位 (storage_reg[31:0]中的位8和位9)
	assign decoder_bit_9  = storage_reg[8];   // ARINC数据字第9位
	assign decoder_bit_10 = storage_reg[9];   // ARINC数据字第10位

	// 根据奇偶校验结果，生成最终要写入FIFO的数据
	// 1. 如果PARITYEN=0，直接使用原始数据 storage_reg
	// 2. 如果PARITYEN=1:
	//    - 校验正确 (parity_equal=1)，bit[31]应为0。!parity_equal = 0
	//    - 校验错误 (parity_equal=0)，bit[31]应为1。!parity_equal = 1
	assign data_to_write = PARITYEN ? {!parity_equal, storage_reg[30:0]} : storage_reg;

	// 解码器匹配结果
	assign decoder_match = (!i_decoder_en) ||
	                      (i_decoder_en &&
	                       (decoder_bit_10 == i_decoder_match_b10) &&
	                       (decoder_bit_9 == i_decoder_match_b9));

	// 标签匹配条件：标签识别禁用 OR (标签识别使能 AND 标签匹配)
	assign label_pass = (!i_label_rec_en) || (i_label_rec_en && i_label_match);

	// 解码器匹配条件：解码器禁用 OR (解码器使能 AND 位匹配)
	assign decoder_pass = (!i_decoder_en) ||
	                     (i_decoder_en &&
	                      (decoder_bit_10 == i_decoder_match_b10) &&
	                      (decoder_bit_9 == i_decoder_match_b9));

	// 根据 DATARATE 动态选择 bit width validation threshold。
	// DATARATE=0: 使用标准门限 qClkRateCnt；DATARATE=1: 使用约 8 倍门限。
	assign dynamic_threshold = (DATARATE == 1'b0) ? qClkRateCnt : {qClkRateCnt[4:0], 3'b000};

   assign  ones_dat            = RXA_in & ~RXB_in       ; // 检测逻辑1: RXA高，RXB低
   assign  zero_dat            = ~RXA_in & RXB_in       ; // 检测逻辑0: RXA低，RXB高
   assign  null_dat            = ~(RXA_in | RXB_in)     ; // 检测空闲: RXA和RXB都为低

   assign  qClkRateCnt         = {1'b0,clkRateCnt[7:1]} ; // 时钟速率计数查询

	assign  shift_data          = shift_data_auto        ; // 数据移位信号
   assign  data_valid          = data_valid_auto        ; // 数据有效信号

	assign  null_dat_fall       = null_dat_r2 & (!null_dat_r1)  ; // 空闲数据下降沿检测
   assign  null_dat_rise       = (!null_dat_r2) & null_dat_r1  ; // 空闲数据上升沿检测

	assign  parity_equal        = ODD_N_EVEN ^ parity_val        ; // 奇偶校验相等判断
//------------------------------------------------------------------------------
// RXA Synchronizer Stage 1
//------------------------------------------------------------------------------
	always @(posedge CLK or negedge RESET_N0)
	begin
		if (RESET_N0 == 1'b0)
		begin
			RXA_in1 <= 1'b0        ;
		end
		else
		begin
			RXA_in1 <= RXA         ;
		end
	end
//------------------------------------------------------------------------------
// RXA Synchronizer Stage 2
//------------------------------------------------------------------------------
	always @(posedge CLK or negedge RESET_N0)
	begin
		if (RESET_N0 == 1'b0)
		begin
			RXA_in  <= 1'b0        ;
		end
		else
		begin
			RXA_in  <= RXA_in1     ;
		end
	end
//------------------------------------------------------------------------------
// RXB Synchronizer Stage 1
//------------------------------------------------------------------------------
	always @(posedge CLK or negedge RESET_N0)
	begin
		if (RESET_N0 == 1'b0)
		begin
			RXB_in1 <= 1'b0        ;
		end
		else
		begin
			RXB_in1 <= RXB         ;
		end
	end
//------------------------------------------------------------------------------
// RXB Synchronizer Stage 2
//------------------------------------------------------------------------------
	always @(posedge CLK or negedge RESET_N0)
	begin
		if (RESET_N0 == 1'b0)
		begin
			RXB_in  <= 1'b0        ;
		end
		else
		begin
			RXB_in  <= RXB_in1     ;
		end
	end
//------------------------------------------------------------------------------
// Sample Pulse Generation
//------------------------------------------------------------------------------
	always @(rate_cnt)
	begin
		CLK_en_next = 1'b0 ;
		// 1 MHz 基准下每 10 个周期产生一次采样脉冲，用于 100 kHz 采样。
		if (rate_cnt == 11'd9)
		begin
			CLK_en_next = 1'b1 ;
		end
	end
//------------------------------------------------------------------------------
// Sample Counter
//------------------------------------------------------------------------------
	always @(posedge CLK or negedge RESET_N0)
	begin
		if (RESET_N0 == 1'b0)
		begin
			rate_cnt <= 11'd0   ;
			CLK_en   <= 1'b0    ;
		end
		else
		begin
			CLK_en   <= CLK_en_next     ;
			rate_cnt <= rate_cnt + 1    ;
			// 1 MHz 下每 10 个 clk 周期重置计数器。
			if (rate_cnt == 11'd9)
			begin
				rate_cnt <= 11'd0 ;
			end
		end
	end
//------------------------------------------------------------------------------
// Null Edge Generation
//------------------------------------------------------------------------------
   always @(posedge CLK or negedge RESET_N0)
   begin
      // 提取 null_dat edge，并同步 ones_dat / zero_dat。
      if (RESET_N0 == 1'b0)
      begin
         ones_dat_syn1 <= 1'b0	;
         ones_dat_syn  <= 1'b0	;
         zero_dat_syn1 <= 1'b0	;
         zero_dat_syn  <= 1'b0	;
         null_dat_r1   <= 1'b0	;
         null_dat_r2   <= 1'b0	;
      end
      else 
      begin
         ones_dat_syn1 <= ones_dat		;
         ones_dat_syn  <= ones_dat_syn1;
         zero_dat_syn1 <= zero_dat		;
         zero_dat_syn  <= zero_dat_syn1;
         null_dat_r1   <= null_dat		;
         null_dat_r2   <= null_dat_r1	;
      end
   end
//------------------------------------------------------------------------------
// Null Falling Edge Delay
//------------------------------------------------------------------------------
   always @(posedge CLK or negedge RESET_N0)
   begin
      if (RESET_N0 == 1'b0)
      begin
         null_dat_fall_next <= 1'b0;
      end
      else 
      begin
         null_dat_fall_next <= null_dat_fall;      
      end
   end
//------------------------------------------------------------------------------
// Data Rate Width Counter
//------------------------------------------------------------------------------
   // 对 A/B bus 分别统计高低电平宽度，并记录 data rate 周期计数。
   always @(posedge CLK or negedge RESET_N0)
   begin
      if (RESET_N0 == 1'b0 )
      begin
         clkRateCnt <= 8'h00 ;
         clkRateCntReg <= 8'h00; 
         clkRateCntState <= rateCntIdle;
      end
      else 
      begin
      case(clkRateCntState)
        rateCntIdle:
        begin
            clkRateCnt <= 8'h00;
            if(null_dat_fall == 1'b1)
            begin
                clkRateCntState <= rateCntStart;
            end
        end
        rateCntStart:
        begin
             if (CLK_en == 1'b1)
             begin
                clkRateCnt <= clkRateCnt + 1;
             end    
             if(null_dat_rise == 1'b1)    
             begin
                clkRateCntState <= rateCntStop;
             end    
        end
        rateCntStop:
        begin
            clkRateCntReg <= clkRateCnt;
            clkRateCntState <= rateCntIdle;
        end
        default:
        begin
            clkRateCntState <= rateCntIdle;
            clkRateCnt <= 8'h00;
        end

      endcase
      end
   end
//------------------------------------------------------------------------------
// Zero High-Level Width Counter
//------------------------------------------------------------------------------
   // 统计 zero symbol 的高电平宽度。
   always @(posedge CLK)
   begin
      if ((RESET_N0 == 1'b0 )||(null_dat_fall_next == 1'b1))
      begin
			zeroHighCnt <= 8'h00 ; 
      end
      else 
      begin
         if ((CLK_en == 1'b1)&& (null_dat_r2 == 1'b0) && (zero_dat_syn == 1'b1))
         begin
           zeroHighCnt <= zeroHighCnt + 1;
         end
      end
   end
//------------------------------------------------------------------------------
// Zero Low-Level Width Counter
//------------------------------------------------------------------------------
   // 统计 zero symbol 的低电平宽度。
   always @(posedge CLK)
   begin
      if ((RESET_N0 == 1'b0 ) ||(null_dat_rise == 1'b1))
      begin
         zeroLowCnt <= 8'h00 ; 
      end
      else 
      begin
         if ((CLK_en == 1'b1) && (null_dat_r2 == 1'b1) && (zero_dat_syn == 1'b0))
         begin
            zeroLowCnt <= zeroLowCnt + 1;
         end
      end
   end
//------------------------------------------------------------------------------
// One High-Level Width Counter
//------------------------------------------------------------------------------
   // 统计 one symbol 的高电平宽度。
   always @(posedge CLK)
   begin
      if ((RESET_N0 == 1'b0 ) ||(null_dat_fall_next == 1'b1))
      begin
         onesHighCnt <= 8'h00 ; 
      end
      else 
      begin
         if ((CLK_en == 1'b1) && (null_dat_r2 == 1'b0) && (ones_dat_syn == 1'b1))
         begin
            onesHighCnt <= onesHighCnt + 1;
         end
      end
   end
//------------------------------------------------------------------------------
// One Low-Level Width Counter
//------------------------------------------------------------------------------
   // 统计 one symbol 的低电平宽度。
   always @(posedge CLK)
   begin
      if ((RESET_N0 == 1'b0 ) ||(null_dat_rise == 1'b1))
      begin
         onesLowCnt <= 8'h00 ; 
      end
      else 
      begin
         if ((CLK_en == 1'b1) && (null_dat_r2 == 1'b1) && (ones_dat_syn == 1'b0))
         begin
            onesLowCnt <= onesLowCnt + 1;
         end
      end
   end
//------------------------------------------------------------------------------
// Null High-Level Width Counter
//------------------------------------------------------------------------------
   // 统计 null symbol 的高电平宽度。
   always @(posedge CLK)
   begin
      if ((RESET_N0 == 1'b0 ) ||(null_dat_rise == 1'b1))
      begin
         nullHighCnt <= 8'h00 ; 
      end
      else 
      begin
         if ((CLK_en == 1'b1) && (null_dat_r2 == 1'b1))
         begin
            nullHighCnt <= nullHighCnt + 1;
         end
      end
   end
//------------------------------------------------------------------------------
// Null Low-Level Width Counter
//------------------------------------------------------------------------------
   // 统计 null symbol 的低电平宽度。
   always @(posedge CLK)
   begin
      if ((RESET_N0 == 1'b0 ) ||(null_dat_fall == 1'b1))
      begin
         nullLowCnt <= 8'h00 ; 
      end
      else 
      begin
         if ((CLK_en == 1'b1) && (null_dat_r2 == 1'b0))
         begin
            nullLowCnt <= nullLowCnt + 1;
         end
      end
   end
//------------------------------------------------------------------------------
// Word Gap Counter
//------------------------------------------------------------------------------
// 由 wait_for_gap 状态控制，独立于 bitstream decoder。
always @(posedge CLK or negedge RESET_N0)
begin
    if (RESET_N0 == 1'b0)
    begin
        null_cnt <= 6'd0;     // 复位后清零计数器
    end
    else
    begin
        if (clr_nullcnt == 1'b1)
        begin
            null_cnt <= 6'd0;     // 清零计数器
        end
        else if (inc_nullcnt == 1'b1)
        begin
            // 在每个半比特周期 (CLK_en)，递增计数器
            if (CLK_en == 1'b1)
            begin
                null_cnt <= null_cnt + 1;
            end
        end
    end
end
//------------------------------------------------------------------------------
// Symbol Detection FSM
//------------------------------------------------------------------------------
   // 利用 null_dat edge 和 symbol width 统计判断 ones_dat / zero_dat。
   always @(posedge CLK or negedge RESET_N0)
   begin
      if (RESET_N0 == 1'b0)
      begin
         ones_det_auto <= 1'b0 ; 
         zero_det_auto <= 1'b0 ; 
         data_det_widCnt <= 3'b000;
         data_process_state <= dataProcIdle;
         nullLowCntReg <= 8'h00;
      end
      else 
      begin
      case (data_process_state)
        dataProcIdle:
        begin
            data_det_widCnt <= 3'b000;
            nullLowCntReg <= 8'h00;
            // 不依赖 word_cnt，保证 bit detect 对新的 line activity 保持敏感。
            if(null_dat_rise == 1'b1)
            begin
                data_process_state <= dataProcWait;
                nullLowCntReg <= nullLowCnt;
            end
            else
            begin
                data_process_state <= dataProcIdle;
            end
        end
        dataProcWait:
        begin
            if ((nullLowCntReg == {2'b00, nullLowCnt[7:2]}) || (null_dat_fall == 1'b1))
            begin
                data_process_state <= dataProc;
            end
            else if (CLK_en == 1'b1)
            begin
                nullLowCntReg <= nullLowCntReg - 1;
            end
        end
        dataProc:
        begin
               if ((onesHighCnt > dynamic_threshold) & (onesLowCnt > dynamic_threshold))
               begin
                  ones_det_auto <= 1'b1 ;
                  zero_det_auto <= 1'b0 ;
               end
               else if ((zeroHighCnt > dynamic_threshold) & (zeroLowCnt > dynamic_threshold))
               begin
                  ones_det_auto <= 1'b0 ;
                  zero_det_auto <= 1'b1 ;
               end
               else
               begin
                  ones_det_auto <= 1'b0 ;
                  zero_det_auto <= 1'b0 ;
               end
               data_process_state <= dataProcWid;
        end
        dataProcWid:
        begin
               if (data_det_widCnt == 3'd2)
               begin 
                  data_process_state <= dataProcIdle;
                  ones_det_auto <= 1'b0 ; 
                  zero_det_auto <= 1'b0 ; 
               end
               else if (CLK_en == 1'b1)
               begin
                  data_det_widCnt <= data_det_widCnt + 1;
               end
        end
        default:
			begin
				ones_det_auto <= 1'b0 ; 
				zero_det_auto <= 1'b0 ; 
				data_process_state <= dataProcIdle;
			end
        endcase
      end
   end   
//------------------------------------------------------------------------------
// Receiver Front-End Processing
//------------------------------------------------------------------------------
   always @(posedge CLK or negedge RESET_N0)
   begin
      if (RESET_N0 == 1'b0)
      begin
         shift_data_auto <= 1'b0 ; 
         data_valid_auto <= 1'b0 ; 
         reg_ones_det_auto <= 1'b0 ; 
         reg_zero_det_auto <= 1'b0 ; 
      end
      else 
      begin
         if (CLK_en == 1'b1)
         begin
            // one/zero detect shift register。
            reg_ones_det_auto <= ones_det_auto ; 
            reg_zero_det_auto <= zero_det_auto ; 
            // data_valid digital one-shot。
             if ((reg_ones_det_auto == 1'b0) & (ones_det_auto == 1'b1))
            begin
               shift_data_auto <= 1'b1 ; 
               data_valid_auto <= 1'b1 ; 
            end
            else if ((reg_zero_det_auto == 1'b0) & (zero_det_auto == 1'b1))
            begin
               shift_data_auto <= 1'b0 ; 
               data_valid_auto <= 1'b1 ; 
            end
            else
            begin
               data_valid_auto <= 1'b0 ; 
            end 
         end 
      end 
   end 
//------------------------------------------------------------------------------
// Data Valid Delay and Timeout Reference
//------------------------------------------------------------------------------
   always @(posedge CLK or negedge RESET_N0)
   begin
      if (RESET_N0 == 1'b0)
      begin
        reg0_data_valid_auto <= 1'b0;
        reg1_data_valid_auto <= 1'b0;
      end
      else
      begin
        reg0_data_valid_auto <= data_valid_auto; 
        reg1_data_valid_auto <= reg0_data_valid_auto;
      end
   end
   always @(posedge CLK or negedge RESET_N0)
   begin
      // data_valid 上升沿锁存当前 data rate 计数值，作为后续 bit gap timeout 参考。
      if (RESET_N0 == 1'b0)
      begin
        timeoutVal <= 10'hff;
      end
      else if((reg1_data_valid_auto == 1'b0) && (reg0_data_valid_auto == 1'b1))
      begin
           timeoutVal <= {clkRateCntReg[7:0],2'b00}; 
      end
   end
//------------------------------------------------------------------------------
// RX Word FSM Combinational Logic
//------------------------------------------------------------------------------
   always @(*)
   begin
      inc_bitcnt   = 1'b0 ;
      clr_bitcnt   = 1'b0 ;
      shift_label  = 1'b0 ;
      shift_arinc  = 1'b0 ;
      inc_timeout  = 1'b0 ;
      clr_timeout  = 1'b0 ;
      calc_parity  = 1'b0 ;
      start_wrfifo = 1'b0 ;
      inc_nullcnt  = 1'b0 ; // 字间隔计数器递增。
      clr_nullcnt  = 1'b0 ; // 字间隔计数器清零。
      case (rx_present_state)
         idle0 :
                  begin
                     if (data_valid == 1'b1)
                     begin
                        rx_next_state = branch ;
                        clr_timeout   = 1'b1   ;
                     end
                     else
                     begin
                        rx_next_state = idle0 ;
                     end
                     if (timeout > timeoutVal)
                     begin
                        clr_bitcnt = 1'b1 ;
                     end
                     else if (bit_cnt > 6'b000000)
                     begin
                        inc_timeout = 1'b1 ;
                     end
                  end
         branch :
                  begin
                     inc_bitcnt = 1'b1 ;
                     // 检查标签位
                     if (bit_cnt > 6'b000111)
                     begin
                        // 标签接收完成
                        rx_next_state = arinc_A ;
                     end
                     else
                     begin
                        rx_next_state = label_A ; // shift label in	
                     end 
                     if (bit_cnt <= 6'b011111)
                     begin
                        // calc parity on 31 bits of data
                        calc_parity = 1'b1 ; 
                     end 
                  end
         label_A :
                  begin
                     // pass thru 8 times
                     shift_label = 1'b1 ; 
                     rx_next_state = idle0 ; 
                  end
         arinc_A :
                  begin
                     shift_arinc = 1'b1 ; 
                     if (bit_cnt > 6'b011111)
							begin
							// check for parity error here.
							rx_next_state = parity ; 
							end
                     else
                     begin
                        rx_next_state = idle0 ; 
                     end 
                  end
         parity :
                  begin
                     // 无论奇偶校验结果如何，状态机都应继续到下一状态。
                     // 校验结果将在数据写入FIFO前用于标记第32位。
                     rx_next_state = check_label ;
                  end
         check_label :
                  begin
                     // 在此状态下，storage_reg[7:0]已通过o_decoded_label输出
                     // 同时检查标签匹配和解码器匹配结果
                     // 使用预定义的wire信号进行判断

                     if (label_pass && decoder_pass)
                     begin
                        // 数据有效：触发FIFO写，并转换到等待字间隔状态
                        rx_next_state = wait_for_gap;
                        start_wrfifo = 1'b1;
                     end
                     else
                     begin
                        // 数据无效：丢弃，直接转换到等待字间隔状态
                        rx_next_state = wait_for_gap;
                     end
                  end
         wait_for_gap:
                  begin
                     // 进入此状态，意味着一个字的处理流程（无论有效无效）已经结束。
                     // 开始进行字间隔同步。

                     // 优先检测新的 data activity，而不是固定等待。
                     if (data_valid == 1'b1)
                     begin
                        // 检测到新的比特活动，立即开始处理新字
                        rx_next_state = branch;
                        clr_timeout = 1'b1;
                        clr_nullcnt = 1'b1;  // 清零间隔计数器
                        clr_bitcnt = 1'b1;   // 新 word 从干净 bit counter 状态开始。
                     end
                     else
                     begin
                        // 没有新数据，继续字间隔计时
                        inc_nullcnt = 1'b1;

                        // 判断是否已满足最小字间隔 (4个比特时间 ≈ 8个半比特周期)
                        if (null_cnt > 6'd7) // 使用localparam STANDARD_NULL_COUNT更佳
                        begin
                           // 间隔已满足，清零计数器并返回IDLE，等待下一个比特的到来
                           rx_next_state = idle0;
                           clr_nullcnt = 1'b1;
                        end
                        else
                        begin
                           // 间隔未满足，保持在此状态继续计时
                           rx_next_state = wait_for_gap;
                        end
                     end
                  end
         default :
                  begin
                     rx_next_state = idle0 ;
                  end
      endcase 
   end 
//------------------------------------------------------------------------------
// RX FIFO Write Control
//------------------------------------------------------------------------------
	// RX write FIFO FSM，保存通过 label/decoder 过滤后的 ARINC word。
   always @(*)
   begin
      fifo_write_en = 1'b1 ; // active low
      rx_din = 32'h0 ;
      wrfifo_next_state = wrfifo_present_state;
      case (wrfifo_present_state)
         idle_state :
                  begin
                     if (start_wrfifo == 1'b1)  // 移除FIFO满检查，始终允许写入
                     begin
                        wrfifo_next_state = fifo_A ;
                     end
                  end
         fifo_A :
                  begin
                     // 移除FIFO满检查，始终产生写信号实现覆盖写入
                     fifo_write_en = 1'b0 ; // active low
                     // 使用经过奇偶校验标记处理后的数据
                     rx_din = data_to_write ;
                     wrfifo_next_state = finish ;
                  end
         finish :
                  begin
                     if (start_wrfifo == 1'b0)
							begin
                        wrfifo_next_state = idle_state ;
                     end
                  end
         default :
                  begin
                     wrfifo_next_state = idle_state ;
                  end
      endcase
   end
//------------------------------------------------------------------------------
// RX FSM Sequential Logic
//------------------------------------------------------------------------------
   // RX后端状态机的同步部分
	always @(posedge CLK or negedge RESET_N0)
	begin
		if (RESET_N0 == 1'b0)
		begin
			rx_present_state     <= idle0       ;
			wrfifo_present_state <= idle_state  ;
			bit_cnt              <= 6'b000000   ;
			storage_reg          <= 'h00000000  ;
			timeout              <= 10'h00      ;
			parity_val           <= 1'b0        ;
		end
		else
		begin
			wrfifo_present_state <= wrfifo_next_state ;
			if (CLK_en == 1'b1)
			begin
				rx_present_state <= rx_next_state       ;
				// 6位位计数器
				if (clr_bitcnt == 1'b1)
				begin
					bit_cnt <= 6'b000000    ;
				end
				else if (inc_bitcnt == 1'b1)
				begin
					bit_cnt 	<= bit_cnt + 1 ;
				end
				//32 bit storage register
				// remember the label comes in MSB first (left shift)
				// the rest of the arinc word comes in LSB first
				if (shift_label == 1'b1)
				begin
					storage_reg[7:0] 	<= {shift_data,storage_reg[7:1]} 	;
				end
				if (shift_arinc == 1'b1)
				begin
					storage_reg[31:8]	<= {shift_data, storage_reg[31:9]} 	;
				end
				//10 bit \"timeout\" counter to make sure no bit gaps
				if (clr_timeout == 1'b1)
				begin
					timeout 	<= 10'h00 		;
				end
				else if (inc_timeout == 1'b1)
				begin
					timeout 	<= timeout + 1 ;
				end

				// 奇偶校验计算
				if (clr_bitcnt == 1'b1)
				begin
					parity_val  <= 1'b0         ;
				end
				else if (calc_parity == 1'b1)
				begin
					parity_val  <= parity_val ^ shift_data ;
				end
			end
		end
	end

endmodule
