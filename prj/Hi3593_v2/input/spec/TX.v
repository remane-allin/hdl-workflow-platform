`timescale 1ns / 1ps

//==============================================================================
// Module      : TX
// File        : TX.v
// Project     : starter_hdl_project
// Description : ARINC 429 TX protocol core，发送标准 32-bit ARINC word。
//
// Scope:
//   - 从 TX FIFO 读取 32-bit word，并按 ARINC 429 bit timing 输出 TXA/TXB。
//   - 支持 high speed / low speed data rate。
//   - 支持 odd/even parity 和 CR11 label bit order。
//   - 支持 FORCE_NULL 将 ARINC line output 强制为空闲状态。
//
// Spec Trace:
//   - CR3  : TX parity bit enable。
//   - CR9  : TX parity select。
//   - CR10 : TX data rate select。
//   - CR11 : ARINC label bit order。
//
// Notes:
//   - CLK 是本项目集成后的 ARINC reference clock。
//   - oRdn 是单周期 FIFO read pulse，由内部 FSM 触发。
//==============================================================================
module TX(
		CLK             ,		// 时钟信号 1MHz (重构后统一基准)
		RESET_N0        ,		// 复位信号 低电平有效

		TXA             ,		// ARINC 429 TX 正端口
		TXB             ,		// ARINC 429 TX 负端口
		ENTX            ,		// ARINC 429 TX 使能 1:使能发送; 0:禁止发送
		DATARATE        ,		// TX 传输波特率 0:100Kbps; 1:12.5Kbps
		PARITYEN        ,		// TX 奇偶校验使能 0:禁止; 1:使能
		ODD_N_EVEN      ,		// TX 奇偶校验模式 0:奇校验; 1:偶校验

		oRdn            ,		// TX DMA FIFO 读信号
		iFifo_Empty     ,		// TX DMA FIFO 空信号
		iData           ,		// TX DMA FIFO 32位数据
		FORCE_NULL      ,		// 强制Null状态输入
		LABEL_BIT_ORDER 		// ARINC 429标签位顺序控制 (CR11): 0=位反转; 1=保持原样
		);
//------------------------------------------------------------------------------
// Parameters
//------------------------------------------------------------------------------
	// TX 状态机参数。
   parameter[3:0]   idle         = 0    ; // 初始状态
   parameter[3:0]   rdfifo_1     = 1    ; // 读取DMA FIFO
   parameter[3:0]   rdfifo_2     = 2    ; // 加载DMA FIFO数据到移位寄存器
   parameter[3:0]   branch       = 3    ; // 决定发送寄存器
   parameter[3:0]   arinc_dat    = 4    ; // 按序发送字的每一位
   parameter[3:0]   arinc_null   = 5    ; // 完成一个字的传输
//------------------------------------------------------------------------------
// Port Declarations
//------------------------------------------------------------------------------
   input            CLK             ; 	// 核心429时钟 (1MHz基准)
   input            RESET_N0        ; 	// 主异步低电平有效复位
   input            ENTX            ; 	// 1:使能发送; 0:禁止发送
   output           TXA             ; 	// ARINC发送输出A
   output           TXB             ; 	// ARINC发送输出B
   input            DATARATE        ; 	// 数据速率: 0 = 100 kbps; 1 = 12.5 kbps
   input            PARITYEN        ; 	// 0 = 第32位是数据; 1 = 第32位是奇偶校验
   input            ODD_N_EVEN      ; 	// 奇偶校验: 0 = 奇校验; 1 = 偶校验
   output           oRdn            ;	// TX DMA FIFO 读信号
   input            iFifo_Empty     ;	// TX DMA FIFO 空信号
   input [31:0]     iData           ;	// TX DMA FIFO 32位数据
   input            FORCE_NULL      ;	// 强制Null状态输入
   input            LABEL_BIT_ORDER ;	// ARINC 429标签位顺序控制 (CR11): 0=位反转; 1=保持原样
//------------------------------------------------------------------------------
// Internal Registers
//------------------------------------------------------------------------------
   reg              CLK_en          ;	// 波特率脉冲
   reg              CLK_en_next     ;	// 波特率脉冲临时信号
   reg  [5:0]       bit_cnt         ;	// 一个A429字(32位)的位计数器
   reg  [10:0]      rate_cnt        ;	// 波特率计数器
   reg              trigger_fifo_read;      // 由FSM产生的、持续一个半比特周期的触发信号
   reg              trigger_fifo_read_d1;   // 用于边沿检测的延迟寄存器
   reg              ld0             ;	// 加载DMA数据到移位寄存器
   reg              ld0_next        ;	// 加载DMA数据信号临时信号
   reg  [3:0]       tx_present_state;	// TX状态机当前状态
   reg  [3:0]       tx_next_state   ;	// TX状态机下一状态
   reg  [31:0]      arinc_reg       ;	// TX移位数据寄存器
   reg              inc_bitcnt      ;  // 位计数器计数使能
   reg              clr_bitcnt      ;	// 清零位计数器
   reg              shift_arinc     ;	// 数据寄存器移位使能
   reg              ones_dat        ;	// A429总线状态: 逻辑1
   reg              zero_dat        ;	// A429总线状态: 逻辑0
   reg              null_dat        ;	// A429总线状态: 空闲
   reg  [3:0]       shift_cnt       ;	// 发送寄存器移位计数器
   reg              inc_shiftcnt    ;	// 发送寄存器移位计数器计数使能
   reg              clr_shiftcnt    ;	// 清零发送寄存器移位计数器
   reg  [9:0]       TXAreg          ;	// 总线P(A)的发送寄存器
   reg  [9:0]       TXBreg          ;	// 总线N(B)的发送寄存器
   reg  [5:0]       null_cnt        ;	// 字间隔计数器
   reg              inc_nullcnt     ;	// 字间隔计数器计数使能
   reg              clr_nullcnt     ;	// 清零字间隔计数器
   reg              ld_parity       ;	// 加载要发送字的奇偶校验位
   reg              start_tran      ;	// 发送开始使能
   reg              parity_val      ;	// 字的前30位的异或值
   reg              parity          ;	// 由输入ODD_N_EVEN决定的奇偶校验值
//------------------------------------------------------------------------------
// Internal Wires
//------------------------------------------------------------------------------
   wire             arinc_data      ; // 当前发送位
   wire             TXA             ; // ARINC发送输出A
   wire             TXB             ; // ARINC发送输出B
   wire [31:0]      data_to_load    ; // 用于加载到arinc_reg的数据
   wire [7:0]       original_label  ; // 原始标签
   wire [7:0]       reversed_label  ; // 位反转后的标签
   wire             single_cycle_read_pulse; // 最终生成的单周期读脉冲

	// 标准 ARINC 429 timing 参数。
	localparam STANDARD_BIT_COUNT = 6'd31;  // bit_cnt > 31 意味着完成了32位 (0-31) 的发送
	localparam STANDARD_NULL_COUNT = 6'd7;  // null_cnt > 7 对应4个比特时间的间隔 (8个半比特时间)
//------------------------------------------------------------------------------
// Output and Data Path Assignments
//------------------------------------------------------------------------------

   assign      TXA             = FORCE_NULL ? 1'b0 : TXAreg[9];
   assign      TXB             = FORCE_NULL ? 1'b0 : TXBreg[9];
	assign      arinc_data      = arinc_reg[0]              ;

	assign original_label = iData[7:0];
	assign reversed_label = {original_label[0], original_label[1], original_label[2], original_label[3],
	                         original_label[4], original_label[5], original_label[6], original_label[7]};
	// 根据 LABEL_BIT_ORDER (CR11) 选择最终加载的数据
	// CR11=1 (true) 使用原数据, CR11=0 (false) 使用标签反转后的数据
	assign data_to_load = LABEL_BIT_ORDER ? iData : {iData[31:8], reversed_label};

//------------------------------------------------------------------------------
// TX FIFO Read Pulse
//------------------------------------------------------------------------------
	// 将 FSM 产生的 trigger_fifo_read 转换为单周期 FIFO read pulse。
	always @(posedge CLK or negedge RESET_N0)
	begin
		if (RESET_N0 == 1'b0)
		begin
			trigger_fifo_read_d1 <= 1'b0;
		end
		else
		begin
			trigger_fifo_read_d1 <= trigger_fifo_read;
		end
	end

	assign single_cycle_read_pulse = trigger_fifo_read & ~trigger_fifo_read_d1;
	assign oRdn = single_cycle_read_pulse;
//------------------------------------------------------------------------------
// Parity Calculation
//------------------------------------------------------------------------------
	always @ (arinc_reg[30:0])
	begin
		parity_val = (  arinc_reg[0]  ^ arinc_reg[1]  ^ arinc_reg[2]  ^ arinc_reg[3]  ^ arinc_reg[4]  ^ arinc_reg[5]  ^
		                arinc_reg[6]  ^ arinc_reg[7]  ^ arinc_reg[8]  ^ arinc_reg[9]  ^ arinc_reg[10] ^ arinc_reg[11] ^
		                arinc_reg[12] ^ arinc_reg[13] ^ arinc_reg[14] ^ arinc_reg[15] ^ arinc_reg[16] ^ arinc_reg[17] ^
		                arinc_reg[18] ^ arinc_reg[19] ^ arinc_reg[20] ^ arinc_reg[21] ^ arinc_reg[22] ^ arinc_reg[23] ^
		                arinc_reg[24] ^ arinc_reg[25] ^ arinc_reg[26] ^ arinc_reg[27] ^ arinc_reg[28] ^ arinc_reg[29] ^
		                arinc_reg[30] );
	end
//------------------------------------------------------------------------------
// Parity Mode Select
//------------------------------------------------------------------------------
	always @ (parity_val or ODD_N_EVEN)
	begin
		parity = !(ODD_N_EVEN ^ parity_val);
	end
//------------------------------------------------------------------------------
// TX Start Control
//------------------------------------------------------------------------------
	always @(*)
	begin
		if (ENTX == 1'b1 && iFifo_Empty == 1'b0)
		begin
			start_tran = 1'b1;
		end
		else
		begin
			start_tran = 1'b0 ;
		end
	end
//------------------------------------------------------------------------------
// Data Rate Pulse Generation
//------------------------------------------------------------------------------
	always @(rate_cnt or DATARATE)
	begin
		CLK_en_next = 1'b0 ;
		if (DATARATE == 1'b0)
		begin
			// 100kbps: 半比特周期为5µs，在1MHz时钟下计数至4
			if (rate_cnt == 11'd4)
			begin
				CLK_en_next = 1'b1 ;
			end
		end
		else
		begin
			// 12.5kbps: 半比特周期为40µs，在1MHz时钟下计数至39
			if (rate_cnt == 11'd39)
			begin
				CLK_en_next = 1'b1 ;
			end
		end
	end
//------------------------------------------------------------------------------
// Data Rate Counter
//------------------------------------------------------------------------------
	always @(posedge CLK)
	begin
		if (RESET_N0 == 1'b0)
		begin
			rate_cnt <= 11'd0   ;
			CLK_en   <= 1'b0    ;
			ld0      <= 1'b0    ;
		end
		else
		begin
			ld0      <= ld0_next    ;
			rate_cnt <= rate_cnt + 1;
			CLK_en   <= CLK_en_next ;

			if (DATARATE == 1'b0)
			begin
				// 100kbps: 半比特周期为5µs，在1MHz时钟下计数至4
				if (rate_cnt == 11'd4)
				begin
					rate_cnt <= 11'd0 ;
				end
			end
			else
			begin
				// 12.5kbps: 半比特周期为40µs，在1MHz时钟下计数至39
				if (rate_cnt == 11'd39)
				begin
					rate_cnt <= 11'd0 ;
				end
			end
		end
	end
//------------------------------------------------------------------------------
// TX FSM Combinational Logic
//------------------------------------------------------------------------------
   always @(bit_cnt or iFifo_Empty or tx_present_state or start_tran or arinc_data or shift_cnt or null_cnt)
   begin
		trigger_fifo_read = 1'b0 ; // 默认不触发FIFO读取
		ld0_next        = 1'b0 ;
		inc_bitcnt      = 1'b0 ;
		clr_bitcnt      = 1'b0 ;
		clr_nullcnt     = 1'b0 ;
		inc_nullcnt     = 1'b0 ;
		clr_shiftcnt    = 1'b0 ;
		inc_shiftcnt    = 1'b0 ;
		shift_arinc     = 1'b0 ;
		null_dat        = 1'b0 ;
		ones_dat        = 1'b0 ;
		zero_dat        = 1'b0 ;
		ld_parity       = 1'b0 ;
      case (tx_present_state)
         idle :
                  begin
                     if (start_tran == 1'b1)
                     begin
                        // 在发送第一个数据字之前先产生初始字间间隔
                        tx_next_state = arinc_null;
                     end
                     else
                     begin
                        tx_next_state = idle    ;
                     end
                  end
         rdfifo_1 :
                  begin
                     clr_nullcnt       = 1'b1      ; // 清零所有计数器
                     clr_bitcnt        = 1'b1      ;
                     clr_shiftcnt      = 1'b1      ;
                     trigger_fifo_read = 1'b1      ; // 在rdfifo_1状态，将电平触发信号置高
                     tx_next_state     = rdfifo_2  ;
                  end
         rdfifo_2 :
                  begin
                     ld0_next        = 1'b1      ; // 准备锁存数据，不再处理读使能
                     tx_next_state   = branch    ;
                  end
         branch :
                  begin
                     tx_next_state   = arinc_dat    ;
                     if (arinc_data == 1'b1)
                     begin
                        ones_dat     = 1'b1         ;
                     end
                     else if (arinc_data == 1'b0)
                     begin
                        zero_dat     = 1'b1         ;
                     end
                  end
         arinc_dat :
                  begin
                     ld_parity       = 1'b1         ; // 如果使能则加载奇偶校验位
                     if (shift_cnt == 4'b0111)
                     begin
                        shift_arinc  = 1'b1         ; // 执行ARINC移位跳转
                        inc_bitcnt   = 1'b1         ; // 位计数器单次计数
                        inc_shiftcnt = 1'b1         ;
                        tx_next_state = arinc_dat   ;
                     end
                     else if (shift_cnt == 4'b1001)
                     begin
                        clr_shiftcnt = 1'b1         ;
                        if (bit_cnt > STANDARD_BIT_COUNT)	// 检查是否已发送完32位
                        begin
                           tx_next_state = arinc_null;
                        end
                        else if (arinc_data == 1'b1)
                        begin
                           tx_next_state = arinc_dat  ;
                           ones_dat     = 1'b1        ;
                        end
                        else if (arinc_data == 1'b0)
                        begin
                           tx_next_state = arinc_dat  ;
                           zero_dat     = 1'b1        ;
                        end
                     end
                     else
                     begin
                        inc_shiftcnt = 1'b1         ;
                        tx_next_state = arinc_dat   ;
                     end
                  end
         // 等待4个比特时间的字间隔
         arinc_null :
                  begin
                     clr_bitcnt      = 1'b1         ;
                     inc_nullcnt     = 1'b1         ;
                     null_dat        = 1'b1         ;
                     if (null_cnt > STANDARD_NULL_COUNT)// 检查4比特时间的字间隔是否结束
                     begin
                        if (iFifo_Empty == 1'b0)
                        begin
                           // 继续发送下一个字
                           tx_next_state = rdfifo_1   ;
                        end
                        else
                        begin
                           tx_next_state = idle       ;
                        end
                     end
                     else
                     begin
                        tx_next_state = arinc_null  ;
                     end
                  end
         default :
                  begin
                     tx_next_state   = idle         ;
                  end
      endcase 
   end 
//------------------------------------------------------------------------------
// TX FSM Sequential Logic
//------------------------------------------------------------------------------
	always @(posedge CLK)
	begin
		if (RESET_N0 == 1'b0)
		begin
			tx_present_state <= idle            ;
			null_cnt         <= 6'b000000       ;
			shift_cnt        <= 4'b0000         ;
			bit_cnt          <= 6'b000000       ;
			arinc_reg        <= 'h00000000      ;
			TXAreg           <= 10'b0000000000  ;
			TXBreg           <= 10'b0000000000  ;
		end
		else
		begin
			if (CLK_en == 1'b1)
			begin
				tx_present_state <= tx_next_state ;
				// 最终发送阶段
				if (ones_dat == 1'b1)
				begin
					TXAreg <= 10'b1111100000 ; // 发送逻辑1: TXA高，TXB低
					TXBreg <= 10'b0000000000 ;
				end
				else if (zero_dat == 1'b1)
				begin
					TXAreg <= 10'b0000000000 ; // 发送逻辑0: TXA低，TXB高
					TXBreg <= 10'b1111100000 ;
				end
				else if (null_dat == 1'b1)
				begin
					TXAreg <= 10'b0000000000 ; // 空闲状态: TXA和TXB都为低
					TXBreg <= 10'b0000000000 ;
				end
				else
				begin
					TXAreg <= {TXAreg[8:0], 1'b0} ; // 移位寄存器左移
					TXBreg <= {TXBreg[8:0], 1'b0} ;
				end
				// 加载FIFO读取寄存器
				if (shift_arinc == 1'b1)
				begin
					// 右移位
					arinc_reg <= {1'b0, arinc_reg[31:1]} ;
				end
				else if (ld0 == 1'b1)
				begin
					arinc_reg <= data_to_load;     // 加载新的32位数据（已根据CR11处理标签位反转）
				end
				else if ((ld_parity == 1'b1) & (PARITYEN == 1'b1))
				begin
					arinc_reg[31] <= parity ;      // 加载奇偶校验位
				end
				// 6位位计数器
				if (clr_bitcnt == 1'b1)
				begin
					bit_cnt <= 6'b000000 ;
				end
				else if (inc_bitcnt == 1'b1)
				begin
					bit_cnt <= bit_cnt + 1 ;
				end
				// 4位移位计数器
				if (clr_shiftcnt == 1'b1)
				begin
					shift_cnt <= 4'b0000 ;
				end
				else if (inc_shiftcnt == 1'b1)
				begin
					shift_cnt <= shift_cnt + 1 ;
				end
				// 6位空闲计数器
				if (clr_nullcnt == 1'b1)
				begin
					null_cnt <= 6'b000000 ;
				end
				else if (inc_nullcnt == 1'b1)
				begin
					null_cnt <= null_cnt + 1 ;
				end
			end // CLK_en if
		end // 时钟复位 if
	end
endmodule
