// -----------------------------------------------------------------------------
// Module: descriptor_execution_engine
// Description: Single descriptor-owned execution overlay that reuses two local
//              256-bit tiles as ping/pong SAME_PAD weight slots, one operand
//              service, one APX cluster, and one ordered retire owner.
// Scope:
//   - Executes trusted program descriptors without profile-name decode.
//   - Prefetches the next weight tile while the active window is computing.
//   - Maps feature addresses directly with bank=address[1:0].
// Spec Trace: REQ-RRB-005, REQ-RRB-006, REQ-RRB-010, REQ-RRB-019,
//             REQ-RRB-020, REQ-RRB-022, REQ-RRB-023
// -----------------------------------------------------------------------------

`timescale 1ns/1ps
`default_nettype none

module descriptor_execution_engine (
    input  wire        clk,
    input  wire        reset_n,
    input  wire        descriptor_valid,
    output wire        descriptor_ready,
    input  wire [8:0]  descriptor_pc,
    input  wire [63:0] descriptor_base,
    input  wire [63:0] descriptor_ext0,
    input  wire [63:0] descriptor_ext1,
    input  wire [63:0] descriptor_ext2,
    output wire        descriptor_complete,
    output wire        busy,

    output wire        parameter_read_valid,
    output wire [8:0]  parameter_read_address,
    input  wire        parameter_read_response_valid,
    input  wire [63:0] parameter_read_response_data,
    output wire        program_read_valid,
    output wire [8:0]  program_read_address,
    input  wire        program_read_response_valid,
    input  wire [63:0] program_read_response_data,

    output wire        bank0_a_valid,
    output wire        bank0_a_write,
    output wire [12:0] bank0_a_address,
    output wire [15:0] bank0_a_write_data,
    input  wire        bank0_a_response_valid,
    input  wire [15:0] bank0_a_response_data,
    output wire        bank1_a_valid,
    output wire        bank1_a_write,
    output wire [12:0] bank1_a_address,
    output wire [15:0] bank1_a_write_data,
    input  wire        bank1_a_response_valid,
    input  wire [15:0] bank1_a_response_data,
    output wire        bank2_a_valid,
    output wire        bank2_a_write,
    output wire [12:0] bank2_a_address,
    output wire [15:0] bank2_a_write_data,
    input  wire        bank2_a_response_valid,
    input  wire [15:0] bank2_a_response_data,
    output wire        bank3_a_valid,
    output wire        bank3_a_write,
    output wire [12:0] bank3_a_address,
    output wire [15:0] bank3_a_write_data,
    input  wire        bank3_a_response_valid,
    input  wire [15:0] bank3_a_response_data,

    output wire        bank0_b_valid,
    output wire        bank0_b_write,
    output wire [12:0] bank0_b_address,
    output wire [15:0] bank0_b_write_data,
    input  wire        bank0_b_response_valid,
    input  wire [15:0] bank0_b_response_data,
    output wire        bank1_b_valid,
    output wire        bank1_b_write,
    output wire [12:0] bank1_b_address,
    output wire [15:0] bank1_b_write_data,
    input  wire        bank1_b_response_valid,
    input  wire [15:0] bank1_b_response_data,
    output wire        bank2_b_valid,
    output wire        bank2_b_write,
    output wire [12:0] bank2_b_address,
    output wire [15:0] bank2_b_write_data,
    input  wire        bank2_b_response_valid,
    input  wire [15:0] bank2_b_response_data,
    output wire        bank3_b_valid,
    output wire        bank3_b_write,
    output wire [12:0] bank3_b_address,
    output wire [15:0] bank3_b_write_data,
    input  wire        bank3_b_response_valid,
    input  wire [15:0] bank3_b_response_data,

    output wire        result_valid,
    input  wire        result_ready,
    output wire [15:0] result_data,
    output wire        result_last
);
    localparam [3:0] OPCODE_CONFIG = 4'h0;
    localparam [3:0] OPCODE_EMIT = 4'h2;
    localparam [1:0] SPACE_FRAME = 2'd1;
    localparam [1:0] APX_MULTIPLY_REDUCE = 2'd0;
    localparam [1:0] APX_ADD_VECTOR = 2'd1;
    localparam [1:0] APX_REDUCE_VECTOR = 2'd2;
    localparam [1:0] APX_MULTIPLY_VECTOR = 2'd3;
    localparam [3:0] MODE_COPY = 4'd1;
    localparam [3:0] MODE_EWISE = 4'd2;
    localparam [3:0] MODE_WINDOW_DOT = 4'd3;
    localparam [3:0] MODE_POOL = 4'd4;
    localparam [3:0] MODE_CENTERED_GRAM = 4'd6;
    localparam [3:0] MODE_SPD_FACTOR = 4'd7;
    localparam [3:0] MODE_FORWARD_SUBSTITUTE = 4'd8;
    localparam [3:0] MODE_IIR2_BANK = 4'd9;
    localparam [3:0] MODE_VECTOR_ADD = 4'd13;

    localparam [4:0] STATE_IDLE              = 5'd0;
    localparam [4:0] STATE_FIRST_WEIGHT_REQ  = 5'd1;
    localparam [4:0] STATE_FIRST_WEIGHT_WAIT = 5'd2;
    localparam [4:0] STATE_WINDOW_START      = 5'd3;
    localparam [4:0] STATE_WINDOW_RUN        = 5'd4;
    localparam [4:0] STATE_NEXT_WEIGHT_WAIT  = 5'd5;
    localparam [4:0] STATE_COMPLETE          = 5'd6;
    localparam [4:0] STATE_BIAS_RUN          = 5'd7;
    localparam [4:0] STATE_PAIR_PREFETCH     = 5'd8;
    localparam [4:0] STATE_PAIR_RUN          = 5'd9;
    localparam [4:0] STATE_PAIR_BIAS         = 5'd10;
    localparam [4:0] STATE_GENERIC_SOURCE    = 5'd11;
    localparam [4:0] STATE_EWISE_RESULT      = 5'd12;
    localparam [4:0] STATE_VECTOR_RESULT     = 5'd13;
    localparam [4:0] STATE_GENERIC_ACK       = 5'd14;
    // The two shared-compute states form an explicit FSM domain.  Bit 4 is
    // the compute-overlay owner and bit 3 selects tile versus kernel.  All
    // other states keep bit 4 clear, so hot scratch/APX arbitration consumes
    // these domain bits directly instead of a replicated full-state decode.
    localparam [4:0] STATE_KERNEL             = 5'b10000;
    localparam [4:0] STATE_TILE_DOT           = 5'b11000;

    localparam [1:0] RETIRE_STATE_TAIL   = 2'd1;
    localparam [1:0] RETIRE_STATE_RESULT = 2'd2;
    localparam [1:0] RETIRE_STATE_COMMIT = 2'd3;

    // Complex tiled dot products share the kernel row/column counters and
    // address generators, but retain their own top-level state so they cannot
    // be confused with the two-output TILE_PAIR shortcut.
    localparam [3:0] TILE_SOURCE0_REQ  = 4'd0;
    localparam [3:0] TILE_SOURCE0_WAIT = 4'd1;
    localparam [3:0] TILE_SOURCE1_REQ  = 4'd2;
    localparam [3:0] TILE_SOURCE1_WAIT = 4'd3;
    localparam [3:0] TILE_WEIGHT_REQ   = 4'd4;
    localparam [3:0] TILE_WEIGHT_WAIT  = 4'd5;
    localparam [3:0] TILE_IMAG_ISSUE   = 4'd6;
    localparam [3:0] TILE_DOT_WAIT     = 4'd7;
    localparam [3:0] TILE_RETIRE_REAL  = 4'd8;
    localparam [3:0] TILE_RETIRE_IMAG  = 4'd9;
    localparam [3:0] TILE_RETIRE_DRAIN = 4'd10;
    localparam [3:0] TILE_REAL_ISSUE   = 4'd11;

    localparam [1:0] OPERAND_ROLE_WEIGHT = 2'd0;
    localparam [1:0] OPERAND_ROLE_SOURCE = 2'd1;
    localparam [1:0] OPERAND_ROLE_BIAS   = 2'd2;
    localparam [1:0] OPERAND_ROLE_KERNEL  = 2'd3;

    localparam [1:0] KERNEL_PAIRWISE_STAT  = 2'd0;
    localparam [1:0] KERNEL_TRIANGULAR = 2'd1;
    localparam [1:0] KERNEL_BACKSUB  = 2'd2;
    localparam [1:0] KERNEL_RECURRENCE  = 2'd3;

    localparam [4:0] KERNEL_SOURCE_RESIDENT0 = 5'd1;
    localparam [4:0] KERNEL_SOURCE_PRODUCT = 5'd2;
    localparam [4:0] KERNEL_SOURCE_PAIR = 5'd3;
    localparam [4:0] KERNEL_SOURCE_ACTIVE_WEIGHT = 5'd4;
    localparam [4:0] KERNEL_SOURCE_NARROW = 5'd9;
    localparam [4:0] KERNEL_SOURCE_SCALAR = 5'd10;
    localparam [4:0] KERNEL_SOURCE_NEGATE = 5'h10;
    localparam [1:0] APX_OPERAND_EXTERNAL = 2'd0;
    localparam [1:0] APX_OPERAND_PRODUCT = 2'd1;
    localparam [1:0] APX_OPERAND_PAIR = 2'd2;
    localparam [1:0] APX_OPERAND_NARROW = 2'd3;

    localparam [1:0] APX_EXTERNAL_A_SOURCE0 = 2'd0;
    localparam [1:0] APX_EXTERNAL_A_SOURCE1 = 2'd1;
    localparam [1:0] APX_EXTERNAL_A_SOLVE = 2'd2;

    localparam [4:0] STAT_MEAN_STREAM      = 5'd0;
    localparam [4:0] STAT_MEAN_SCALE_ISSUE = 5'd1;
    localparam [4:0] STAT_MEAN_SCALE_WAIT  = 5'd2;
    localparam [4:0] STAT_MEAN_RETIRE      = 5'd3;
    localparam [4:0] STAT_PAIR_ROW_REQ     = 5'd4;
    localparam [4:0] STAT_PAIR_ROW_WAIT    = 5'd5;
    localparam [4:0] STAT_PAIR_COL_REQ     = 5'd6;
    localparam [4:0] STAT_PAIR_COL_WAIT    = 5'd7;
    localparam [4:0] STAT_PAIR_SELF_ISSUE  = 5'd8;
    localparam [4:0] STAT_PAIR_DRAIN       = 5'd9;
    localparam [4:0] STAT_POST_MUL_ISSUE   = 5'd10;
    localparam [4:0] STAT_POST_MUL_WAIT    = 5'd11;
    localparam [4:0] STAT_POST_ADD_WAIT    = 5'd12;
    localparam [4:0] STAT_POST_RETIRE_LOW  = 5'd13;
    localparam [4:0] STAT_POST_RETIRE_HIGH = 5'd14;
    localparam [4:0] STAT_TRACE_ISSUE      = 5'd15;
    localparam [4:0] STAT_TRACE_WAIT       = 5'd16;
    localparam [4:0] STAT_TRACE_SCALE_WAIT = 5'd17;
    localparam [4:0] STAT_TRACE_REG_WAIT   = 5'd18;
    localparam [4:0] STAT_TRACE_EPS_WAIT   = 5'd19;
    localparam [4:0] STAT_DIAG_ADD_ISSUE   = 5'd20;
    localparam [4:0] STAT_DIAG_ADD_WAIT    = 5'd21;
    localparam [4:0] STAT_DIAG_RETIRE      = 5'd22;
    localparam [4:0] STAT_MEAN_SCALE_LOAD  = 5'd23;
    localparam [4:0] STAT_TRACE_LOAD       = 5'd25;
    localparam [4:0] STAT_POST_MUL_LOAD    = 5'd26;
    localparam [4:0] STAT_POST_ADD_ISSUE   = 5'd27;
    localparam [4:0] STAT_TRACE_SCALE_ISSUE = 5'd28;
    localparam [4:0] STAT_TRACE_REG_ISSUE  = 5'd29;
    localparam [4:0] STAT_TRACE_EPS_ISSUE  = 5'd30;
    localparam [4:0] STAT_DIAG_ADD_LOAD    = 5'd31;

    localparam [4:0] TRI_CONST_REQ          = 5'd0;
    localparam [4:0] TRI_CONST_WAIT         = 5'd1;
    localparam [4:0] TRI_CLEAR              = 5'd2;
    localparam [4:0] TRI_STAT_REQ            = 5'd3;
    localparam [4:0] TRI_STAT_WAIT           = 5'd4;
    localparam [4:0] TRI_DOT_START          = 5'd5;
    localparam [4:0] TRI_DOT_TERM_WAIT      = 5'd6;
    localparam [4:0] TRI_DOT_REDUCE_ISSUE  = 5'd7;
    localparam [4:0] TRI_DOT_REDUCE_WAIT   = 5'd8;
    localparam [4:0] TRI_SUB_ISSUE         = 5'd9;
    localparam [4:0] TRI_SUB_WAIT          = 5'd10;
    localparam [4:0] TRI_DIAG_PREP         = 5'd11;
    localparam [4:0] TRI_RSQ_SQUARE_START  = 5'd12;
    localparam [4:0] TRI_RSQ_SQUARE_WAIT   = 5'd13;
    localparam [4:0] TRI_RSQ_VALUE_START   = 5'd14;
    localparam [4:0] TRI_RSQ_VALUE_WAIT    = 5'd15;
    localparam [4:0] TRI_RSQ_HALF_START    = 5'd16;
    localparam [4:0] TRI_RSQ_HALF_WAIT     = 5'd17;
    localparam [4:0] TRI_RSQ_CORR_ISSUE    = 5'd18;
    localparam [4:0] TRI_RSQ_CORR_WAIT     = 5'd19;
    localparam [4:0] TRI_RSQ_EST_START     = 5'd20;
    localparam [4:0] TRI_RSQ_EST_WAIT      = 5'd21;
    localparam [4:0] TRI_OUTPUT_START   = 5'd22;
    localparam [4:0] TRI_OUTPUT_WAIT    = 5'd23;
    localparam [4:0] TRI_RETIRE            = 5'd24;
    localparam [4:0] TRI_RETIRE_LOAD       = 5'd25;

    // BACKSUB keeps one triangular-matrix row and inverse resident while it walks all
    // sample chunks.  Products stream into opposite-parity scratch banks and
    // are reduced in the independent model's adjacent-pairwise order.
    localparam [4:0] BACKSUB_MATRIX_REQ       = 5'd0;
    localparam [4:0] BACKSUB_MATRIX_WAIT      = 5'd1;
    localparam [4:0] BACKSUB_INVERSE_REQ         = 5'd2;
    localparam [4:0] BACKSUB_INVERSE_WAIT        = 5'd3;
    localparam [4:0] BACKSUB_RAW_REQ             = 5'd4;
    localparam [4:0] BACKSUB_RAW_WAIT            = 5'd5;
    localparam [4:0] BACKSUB_CENTER_WAIT         = 5'd6;
    localparam [4:0] BACKSUB_PRODUCT_STREAM      = 5'd7;
    localparam [4:0] BACKSUB_REDUCE_01_ISSUE     = 5'd8;
    localparam [4:0] BACKSUB_REDUCE_01_WAIT      = 5'd9;
    localparam [4:0] BACKSUB_REDUCE_23_ISSUE     = 5'd10;
    localparam [4:0] BACKSUB_REDUCE_23_WAIT      = 5'd11;
    localparam [4:0] BACKSUB_REDUCE_FINAL_ISSUE  = 5'd12;
    localparam [4:0] BACKSUB_REDUCE_FINAL_WAIT   = 5'd13;
    localparam [4:0] BACKSUB_REDUCE_LAST_ISSUE   = 5'd14;
    localparam [4:0] BACKSUB_REDUCE_LAST_WAIT    = 5'd15;
    localparam [4:0] BACKSUB_SUB_ISSUE            = 5'd16;
    localparam [4:0] BACKSUB_SUB_WAIT             = 5'd17;
    localparam [4:0] BACKSUB_SCALE_ISSUE          = 5'd18;
    localparam [4:0] BACKSUB_SCALE_WAIT           = 5'd19;
    localparam [4:0] BACKSUB_RETIRE_LOW           = 5'd20;
    localparam [4:0] BACKSUB_RETIRE_HIGH          = 5'd21;

    // The recurrence loop is an autonomous stream engine.  Its compact phase
    // register is physically separate from the compound-command program
    // counter, so sample flow control cannot become a D-input path of the
    // shared Gram/factor/solve scheduler.
    localparam [2:0] REC_SOURCE    = 3'd0;
    localparam [2:0] REC_RUN_0     = 3'd1;
    localparam [2:0] REC_COS_WAIT  = 3'd2;
    localparam [2:0] REC_REAL      = 3'd3;
    localparam [2:0] REC_SINE_WAIT = 3'd4;
    localparam [2:0] REC_IMAG      = 3'd5;
    localparam [2:0] REC_RETIRE    = 3'd6;

    localparam [3:0] REC_TAG_COEFF   = 4'h1;
    localparam [3:0] REC_TAG_NEGATE  = 4'h2;
    localparam [3:0] REC_TAG_COSINE  = 4'h3;
    localparam [3:0] REC_TAG_SINE    = 4'h4;
    localparam [3:0] REC_TAG_ADD1    = 4'h5;
    localparam [3:0] REC_TAG_CURRENT = 4'h6;
    localparam [3:0] REC_TAG_REAL    = 4'h7;

    (* fsm_encoding = "user" *) reg [4:0] state_q;
    // Descriptor mode is static for the complete operation.  Preserve one
    // shared copy instead of allowing synthesis to spend flip-flops on local
    // replicas of this low-rate control bit.
    (* dont_touch = "yes" *) reg pool_mode_q;
    reg single_plane_q;
    reg emit_mode_q;
    reg pair_mode_q;
    reg tile_dot_mode_q;
    reg tile_complete_pending_q;
    reg ewise_mode_q;
    reg vector_add_mode_q;
    reg kernel_active_q;
    reg [1:0] kernel_kind_q;
    // Mutually exclusive compound kernels share the same datapath and event
    // sequencer, but each owns a five-bit phase PC.  Banking these tiny PCs
    // prevents three unrelated transition graphs from becoming one deep D
    // mux.  Vivado may map the inactive-mode hold to the FF clock enable.
    (* extract_enable = "yes" *) reg [4:0] kernel_stat_step_q;
    (* extract_enable = "yes" *) reg [4:0] kernel_tri_step_q;
    (* extract_enable = "yes" *) reg [4:0] kernel_backsub_step_q;
    wire [4:0] kernel_schedule_step;
    reg [3:0] tile_phase_q;
    reg [2:0] iir_phase_q;
    reg [3:0] kernel_row_q;
    reg [3:0] kernel_column_q;
    reg [4:0] kernel_chunk_q;
    reg [5:0] kernel_index_q;
    reg [5:0] kernel_request_count_q;
    reg [5:0] kernel_response_count_q;
    reg [5:0] kernel_result_count_q;
    reg kernel_chain_accepted_q;
    reg [12:0] kernel_chunk_base_q;
    reg [12:0] kernel_row_base_q;
    reg [12:0] kernel_row_base_d;
    reg kernel_row_base_load;
    reg [12:0] kernel_column_base_q;
    reg [12:0] kernel_destination_base_q;
    reg [15:0] kernel_value_q;
    reg [15:0] kernel_diagonal_q;
    // One mode-shared scalar context replaces separate factor/solve/IIR scalar
    // register families.  The slices are aliases below and are never live
    // for more than one kernel descriptor at a time.
    reg [143:0] kernel_scalar_bank_q;
    // The 128-bit state body uses the shared parity-banked scratch macro.  Keep
    // the four-word recurrence tail in its own compact logical register file:
    // driving RAM32M C ports increased post-opt LUT usage on XC7Z020 because
    // the shared masked write decode was replicated across the state macro.
    reg [63:0] iir_state_tail [0:11];
    reg [11:0] iir_samples_remaining_q;
    // IIR bank owns a sixteen-issue autonomous inner loop.  Keep that loop index
    // local instead of advancing the shared kernel program counter every cycle.
    // Three registered recovery cycles separate adjacent samples.  The first
    // covers the APX-local elastic ingress and the remaining two retire the
    // late ch4/ch5 add results before the next sample's ch0/ch1 negative
    // products reach the single local-state write port.
    reg [3:0] iir_run_step_q;
    reg [1:0] iir_restart_gap_q;
    // IIR terminal cosine/sine streams have at most one request and response
    // per channel.  Keep these counters local so the autonomous IIR bank issue
    // cadence cannot feed the shared Gram/factor/solve kernel counter network.
    reg [3:0] iir_terminal_request_count_q;
    reg [3:0] iir_terminal_response_count_q;
    reg [5:0] iir_history_valid_q;
    reg iir_source_pending_q;
    reg iir_prefetch_valid_q;
    reg iir_late_valid_q;
    reg iir_drain_q;
    reg iir_block_wait_q;
    reg kernel_refine_busy_q;
    reg kernel_refine_done_q;
    reg [2:0] kernel_refine_step_q;
    reg kernel_retire_accepted_q;
    reg kernel_retire_chained_q;
    reg [4:0] flags_q;
    reg [11:0] bound0_q;
    reg [11:0] bound1_q;
    reg [11:0] bound2_q;
    reg [4:0] lanes_q;
    reg [1:0] source_space_q;
    reg [12:0] source_stride0_q;
    reg [12:0] source_stride1_q;
    reg [12:0] source_stride2_q;
    reg [8:0] source_lane_stride_q;
    reg source_negate_q;
    reg source_fast_tile_q;
    reg [1:0] weight_space_q;
    reg [12:0] weight_stride0_q;
    reg [12:0] weight_stride1_q;
    reg [12:0] weight_stride2_q;
    reg [8:0] weight_lane_stride_q;
    reg weight_negate_q;
    reg [12:0] destination_stride0_q;
    reg [12:0] destination_stride1_q;
    reg [12:0] destination_stride2_q;
    reg [8:0] constant_base_row_q;
    reg [12:0] frame_base_q;

    reg [11:0] sequence_i0_q;
    reg [11:0] sequence_i2_q;
    // Sequence classification is captured with the descriptor and advanced
    // with the sequence context.  Keeping these stable for the whole plane
    // prevents the live loop counter from entering scratch/APX select cones.
    reg accumulation_enabled_q;
    reg first_sequence_plane_q;
    reg last_sequence_plane_q;
    reg next_last_sequence_plane_q;
    reg [11:0] group_plane_index_q;
    reg [12:0] source_i0_base_q;
    reg [12:0] weight_i0_base_q;
    reg [12:0] source_address_q;
    reg [12:0] weight_address_q;
    reg [12:0] destination_address_q;
    reg [12:0] retire_destination_q;

    (* ram_style = "distributed" *)
    reg [255:0] weight_slots [0:1];
    reg active_weight_slot_q;
    reg prefetch_pending_q;
    reg prefetch_ready_q;
    reg bias_prefetch_pending_q;
    reg bias_prefetch_ready_q;
    reg [15:0] bias_value_q;
    reg bias_chunk_ready_q;
    reg gather_source_pending_q;
    reg [11:0] gather_request_count_q;
    reg [11:0] gather_issue_count_q;
    reg [11:0] gather_result_count_q;
    reg [12:0] gather_source_address_q;
    reg source_buffer0_valid_q;
    reg [255:0] source_buffer0_data_q;
    reg [127:0] gram_local_data_q;
    // Solve has two simultaneous full-width lifetimes: the incoming sample
    // tile and pairwise-reduction residents.  Keep the stream tile in one
    // explicit payload/valid owner so response capture cannot overwrite
    // reduction data or alias the generic source-buffer lifetime.
    reg solve_stream_resident_valid_q;
    reg [255:0] solve_stream_resident_data_q;
    // Gram column tiles reuse the mode-shared resident-B payload owner.  Only
    // the valid bit is Gram-step-specific; the 256-bit payload lives in the existing
    // source_buffer1 register that is otherwise used by tile/IIR/solve.
    reg kernel_weight_resident_valid_q;
    // BACKSUB keeps one even-index product here until the adjacent odd
    // product arrives.  Reusing one shared tile preserves the paper model's
    // pairwise FP16 reduction order without reinstating per-row scratch tiles.
    reg [255:0] source_buffer1_data_q;
    reg scalar_buffer0_valid_q;
    reg scalar_buffer1_valid_q;
    reg [15:0] scalar_buffer0_data_q;
    reg [15:0] scalar_buffer1_data_q;
    reg prefetch_sequence_q;
    reg bias_sequence_q;
    reg pool_scale_pending_q;

    wire [3:0] scratch_front_read_row;
    wire [3:0] scratch_rmw_read_row;
    wire [3:0] scratch_retire_read_row;
    wire [3:0] scratch_role0_row;
    wire [3:0] scratch_role1_row;
    wire [127:0] scratch_even_read0_data;
    wire [127:0] scratch_even_read1_data;
    wire [127:0] scratch_odd_read0_data;
    wire [127:0] scratch_odd_read1_data;
    wire [127:0] scratch_role0_data;
    wire [127:0] scratch_role1_data;
    reg scratch_write_enable;
    reg [3:0] scratch_write_row;
    reg [7:0] scratch_write_mask;
    reg scratch_write_word_mode;
    reg [15:0] scratch_write_word_data;
    reg [127:0] scratch_write_data;
    reg [127:0] result_chunk_q;
    reg [3:0] chunk_word_count_q;
    reg [4:0] chunk_index_q;
    reg [3:0] chunk_lane_count_q;
    reg pool_chunk_select_q;
    reg pool_chunk_full_select_q;
    reg [3:0] window_issue_count_q;
    reg window_issue_block_q;
    reg chunk_full_q;
    reg accumulation_add_pending_q;
    reg bias_add_pending_q;
    reg window_done_pending_q;
    reg [4:0] produced_chunk_count_q;
    reg retire_stream_active_q;
    reg [11:0] retire_stream_word_index_q;
    reg [12:0] accumulation_retire_address_q;
    reg [11:0] emit_word_index_q;
    reg [3:0] emit_packet_lanes_q;
    reg emit_packet_finishes_group_q;
    reg emit_packet_last_q;
    reg emit_prefetch_request_q;
    reg [12:0] emit_prefetch_address_q;
    reg [4:0] emit_prefetch_lanes_q;
    reg [1:0] pair_prefetch_step_q;
    reg pair_issue_phase_q;
    reg [11:0] pair_block_base_q;
    reg [4:0] pair_block_samples_q;
    reg [12:0] pair_block_destination_q;
    reg [15:0] pair_bias0_q;
    reg [15:0] pair_bias1_q;
    reg pair_bias_pending_q;
    reg pair_retire_pending_q;
    reg window_chain_pending_q;
    // COPY owns a registered look-ahead context.  The response-to-successor
    // command path consumes these flags directly instead of repeating a
    // 12-bit sequence/bound comparison inside the global operand arbiter.
    reg [11:0] copy_remaining_q;
    reg copy_merge_eligible_q;
    reg copy_merge_current_q;
    reg copy_has_after_q;
    reg copy_next_merge_q;

    wire group_diagonal;
    wire descriptor_program_accept;
    wire sequence_context_advance;
    wire sequence_has_next;
    wire sequence_advances_outer;
    wire [11:0] group_plane_index;
    wire group_active_plane;
    wire [11:0] next_sequence_i0;
    wire [11:0] next_sequence_i2;
    wire next_sequence_has_next;
    wire next_sequence_advances_outer;
    wire sequence_reuses_parameters;
    wire next_sequence_reuses_parameters;
    wire window_chain_reuses_parameters;
    wire [11:0] next_group_plane_index;
    wire next_group_active_plane;
    wire next_final_accumulation_plane;
    wire [12:0] next_source_i0_base;
    wire [12:0] next_weight_i0_base;
    wire [12:0] next_source_address;
    wire [12:0] next_weight_address;
    wire [12:0] next_destination_address;
    wire [255:0] active_weight_tile;
    wire window_start_valid;
    wire window_chain_start_valid;
    wire window_chain_start_fire;
    wire [12:0] window_start_source_base;
    wire window_start_weight_select;
    wire window_start_weight_zero;

    reg service_request_valid;
    wire service_request_ready;
    wire operand_service_request_ready;
    wire kernel_stat_service_request_valid;
    wire kernel_tri_service_request_valid;
    wire kernel_backsub_service_request_valid;
    wire iir_service_request_valid;
    reg [1:0] service_request_space;
    reg [12:0] service_request_base;
    reg [9:0] service_request_lane_stride;
    reg [4:0] service_request_lanes;
    reg service_request_negate;
    reg service_request_bias;
    reg service_request_source;
    reg [11:0] service_request_repeat_count;
    reg [12:0] service_request_repeat_stride;
    reg operand_command_valid_q;
    reg [1:0] operand_command_space_q;
    reg [12:0] operand_command_base_q;
    reg [9:0] operand_command_lane_stride_q;
    reg [4:0] operand_command_lanes_q;
    reg operand_command_negate_q;
    reg operand_command_fast_feature_q;
    reg [11:0] operand_command_repeat_count_q;
    reg [12:0] operand_command_repeat_stride_q;
    reg [8:0] operand_command_constant_base_row_q;
    reg [1:0] operand_command_role_q;
    reg operand_pending_valid_q;
    reg [1:0] operand_pending_space_q;
    reg [12:0] operand_pending_base_q;
    reg [9:0] operand_pending_lane_stride_q;
    reg [4:0] operand_pending_lanes_q;
    reg operand_pending_negate_q;
    reg operand_pending_fast_feature_q;
    reg [11:0] operand_pending_repeat_count_q;
    reg [12:0] operand_pending_repeat_stride_q;
    reg [8:0] operand_pending_constant_base_row_q;
    reg [1:0] operand_pending_role_q;
    reg [1:0] operand_response_role_q;
    reg [4:0] operand_response_lanes_q;
    wire [3:0] service_feature_a_valid;
    wire [43:0] service_feature_a_address;
    wire [3:0] service_feature_b_valid;
    wire [43:0] service_feature_b_address;
    wire service_parameter_read_valid;
    wire [8:0] service_parameter_read_address;
    wire service_program_read_valid;
    wire [8:0] service_program_read_address;
    wire service_response_valid;
    reg service_response_ready;
    wire service_response_last;
    wire service_response_half;
    wire [127:0] service_response_data;
    wire service_response_accept;
    wire service_tile_response_valid;
    wire service_tile_response_accept;

    wire window_start_ready;
    wire window_feature_a_valid;
    wire [12:0] window_feature_a_address;
    wire window_feature_a_response_valid;
    wire [15:0] window_feature_a_response_data;
    wire window_apx_request_valid;
    wire window_apx_request_ready;
    wire window_apx_issue_eligible;
    wire window_apx_selected;
    wire [1:0] window_apx_request_operation;
    wire [4:0] window_apx_request_lanes;
    wire [15:0] window_apx_request_tag;
    wire window_apx_shift;
    wire [15:0] window_apx_sample;
    wire window_apx_weight_select;
    wire window_apx_weight_zero;
    wire window_resident_clear_valid;
    wire window_resident_seed_valid;
    wire [4:0] window_resident_seed_lanes;
    wire [15:0] window_resident_seed_data;
    wire window_result_valid;
    wire [15:0] window_result_tag;
    wire [15:0] window_result_data;
    wire window_done;

    wire apx_reduce_valid;
    wire apx_reduce_pre_valid;
    wire [15:0] apx_reduce_tag;
    wire [15:0] apx_reduce_pre_tag;
    wire [15:0] apx_reduce_result;
    wire apx_product_valid;
    wire apx_product_pre_valid;
    wire [15:0] apx_product_tag;
    wire [15:0] apx_product_pre_tag;
    wire [255:0] apx_product_bus;
    wire apx_pair_valid;
    wire apx_pair_pre_valid;
    wire [15:0] apx_pair_tag;
    wire [15:0] apx_pair_pre_tag;
    wire [255:0] apx_pair_bus;
    // The kernel scheduler observes only registered, predecoded completion
    // metadata.  APX result payloads remain resident in the APX result slots;
    // raw result tags cannot enter kernel phase or address-control cones.
    reg [9:0] kernel_fixed_completion_events_q;
    reg [12:0] kernel_pair_events_q;
    reg kernel_product_d100_event_q;
    reg kernel_product_f2_event_q;
    reg [3:0] kernel_product_row_q;
    reg [7:0] kernel_reduce_metadata_q;
    reg [8:0] kernel_post_add_metadata_q;
    reg [6:0] kernel_iir_product_metadata_q;
    reg [5:0] kernel_iir_pair_metadata_q;
    wire [10:0] kernel_completion_events;
    wire kernel_pair_d101_event = kernel_pair_events_q[0];
    wire kernel_pair_d102_event = kernel_pair_events_q[1];
    wire kernel_pair_d103_event = kernel_pair_events_q[2];
    wire kernel_pair_d201_event = kernel_pair_events_q[3];
    wire kernel_pair_d202_event = kernel_pair_events_q[4];
    wire kernel_pair_f000_event = kernel_pair_events_q[5];
    wire kernel_pair_f301_event = kernel_pair_events_q[6];
    wire kernel_pair_f302_event = kernel_pair_events_q[7];
    wire kernel_pair_f303_event = kernel_pair_events_q[8];
    wire kernel_pair_f304_event = kernel_pair_events_q[9];
    wire kernel_pair_f305_event = kernel_pair_events_q[10];
    wire kernel_pair_e001_event = kernel_pair_events_q[11];
    wire kernel_pair_e1xx_event = kernel_pair_events_q[12];
    wire kernel_mean_reduce_event = kernel_reduce_metadata_q[6];
    wire kernel_pair_reduce_event = kernel_reduce_metadata_q[7];
    wire [5:0] kernel_reduce_event_index =
        kernel_reduce_metadata_q[5:0];
    wire kernel_mean_accum_event = kernel_post_add_metadata_q[7];
    wire kernel_pair_accum_event = kernel_post_add_metadata_q[8];
    wire [6:0] kernel_post_add_event_index =
        kernel_post_add_metadata_q[6:0];
    wire iir_product_coeff_event = kernel_iir_product_metadata_q[6];
    wire iir_product_cosine_event = kernel_iir_product_metadata_q[5];
    wire iir_product_negative_event = kernel_iir_product_metadata_q[4];
    wire iir_product_sine_event = kernel_iir_product_metadata_q[3];
    wire [2:0] iir_product_event_channel =
        kernel_iir_product_metadata_q[2:0];
    wire iir_pair_add1_event = kernel_iir_pair_metadata_q[5];
    wire iir_pair_current_event = kernel_iir_pair_metadata_q[4];
    wire iir_pair_real_event = kernel_iir_pair_metadata_q[3];
    wire [2:0] iir_pair_event_channel = kernel_iir_pair_metadata_q[2:0];
    wire apx_request_ready;
    wire apx_busy;
    wire apx_request_valid;
    wire [1:0] apx_request_operation;
    wire [4:0] apx_request_lanes;
    wire [15:0] apx_request_tag;
    wire [255:0] apx_operand_a;
    wire [255:0] apx_operand_b;
    wire [255:0] apx_request_operand_a;
    wire [255:0] apx_request_operand_b;
    reg [191:0] shared_apx_live_narrow_operand_a;
    reg [191:0] shared_apx_live_narrow_operand_b;
    wire [191:0] apx_narrow_operand_a;
    wire [191:0] apx_narrow_operand_b;
    wire [15:0] apx_scalar_operand_b;
    wire apx_post_add_ready;
    wire apx_post_add_result_valid;
    wire [15:0] apx_post_add_result_tag;
    wire [15:0] apx_post_add_result;
    wire apx_post_add_pre_valid;
    wire [15:0] apx_post_add_pre_tag;
    reg kernel_apx_request_valid;
    reg [1:0] kernel_apx_request_operation;
    reg [4:0] kernel_apx_request_lanes;
    reg [15:0] kernel_apx_request_tag;
    reg [4:0] kernel_apx_source_a;
    reg [4:0] kernel_apx_source_b;
    reg [191:0] kernel_apx_narrow_a;
    reg [191:0] kernel_apx_narrow_b;
    reg kernel_apx_narrow_b_scalar;
    reg [15:0] kernel_apx_scalar_b;
    // Every APX producer crosses the same elastic transaction boundary.  The
    // slot stores compact control plus only the narrow operand payload that is
    // not already resident in a source/weight/window slot.  The low eight
    // narrow-A lanes reuse gram_local_data_q, so this replaces the old
    // kernel-only ingress without adding another wide register bank.
    reg shared_apx_issue_valid_q;
    reg [3:0] shared_apx_issue_owner_q;
    reg [1:0] shared_apx_issue_operation_q;
    reg [4:0] shared_apx_issue_lanes_q;
    reg [15:0] shared_apx_issue_tag_q;
    (* keep = "true" *) reg [19:0]
        shared_apx_issue_operand_a_control_q;
    (* keep = "true" *) reg [19:0]
        shared_apx_issue_operand_b_control_q;
    reg [63:0] shared_apx_issue_narrow_a_high_q;
    reg [127:0] shared_apx_issue_narrow_b_q;
    reg [1:0] shared_apx_issue_external_a_select_q;
    reg shared_apx_issue_weight_slot_q;
    reg shared_apx_issue_add_vector_q;
    reg shared_apx_issue_window_shift_q;
    reg [15:0] shared_apx_issue_window_sample_q;
    wire shared_apx_issue_ready;
    wire shared_apx_capture_fire;
    wire shared_apx_dispatch_fire;
    wire kernel_apx_request_fire;
    wire iir_apx_request_fire;
    wire kernel_scalar_add_valid;
    wire kernel_scalar_add_fire;
    wire [15:0] kernel_scalar_add_operand_x;
    wire [15:0] kernel_scalar_add_operand_y;
    wire [15:0] kernel_scalar_add_tag;
    reg kernel_scalar_command_valid_q;
    reg [15:0] kernel_scalar_command_x_q;
    reg [15:0] kernel_scalar_command_y_q;
    reg [15:0] kernel_scalar_command_tag_q;
    wire apx_request_add_vector;
    wire kernel_stat_active;
    wire kernel_triangular_active;
    wire kernel_backsub_active;
    wire kernel_recurrence_active;
    wire kernel_state_active;
    wire tile_state_active;
    wire compute_overlay_active;
    wire kernel_stat_kind;
    wire kernel_triangular_kind;
    wire kernel_backsub_kind;
    wire kernel_recurrence_kind;
    wire kernel_apx_owner;
    wire service_request_fire;
    wire operand_command_fire;
    wire service_request_fast_feature;
    wire [1:0] service_request_role;
    wire kernel_scheduler_service_fire;
    wire kernel_stat_service_fire;
    wire iir_service_request_fire;
    wire kernel_schedule_retire;
    wire [4:0] kernel_schedule_next_phase;
    wire kernel_schedule_advance;
    wire kernel_retire_phase;
    wire kernel_retire_accept;
    wire kernel_retire_complete;
    wire kernel_solve_high_chain_accept;
    wire kernel_source_service_load;
    wire kernel_source_service_beat_accept;
    wire kernel_solve_stream_load;
    wire kernel_source_local_load;
    wire kernel_source_result_load;
    wire kernel_source_load;
    wire kernel_source_pop;
    wire kernel_service_response_valid;
    wire kernel_service_response_accept;
    wire kernel_service_response_beat_accept;
    wire tile_service_response_beat_accept;
    wire kernel_pair_col_resident_load;
    wire kernel_pair_col_resident_pop;
    wire kernel_solve_source_pop;
    wire kernel_post_mul_load_bypass;
    wire kernel_post_mul_load_fire;
    wire kernel_refine_request_valid;
    wire kernel_refine_request_fire;
    wire [1:0] kernel_refine_request_operation;
    wire [4:0] kernel_refine_request_lanes;
    wire [15:0] kernel_refine_request_tag;
    reg [63:0] kernel_refine_operand_a;
    reg [63:0] kernel_refine_operand_b;
    wire [15:0] factor_floor;
    wire [15:0] factor_scalar;
    wire [15:0] factor_value;
    wire [15:0] factor_estimate;
    wire [15:0] factor_temp;
    wire [15:0] factor_inverse;
    wire [15:0] factor_refine_left;
    wire [15:0] factor_refine_right;
    wire [15:0] factor_refine_result;
    wire [15:0] factor_factor_left;
    wire [15:0] factor_factor_right;
    wire [15:0] factor_clamped_value;
    wire factor_dot_reduce_request;
    wire factor_scalar_add_request;
    wire [15:0] solve_mean;
    wire [15:0] solve_factor;
    wire [255:0] solve_product_tile0;
    wire [255:0] solve_product_tile1;
    wire solve_product_store;
    wire solve_terminal_product_prefetch;
    wire solve_f301_prefetch;
    wire solve_f303_prefetch;
    wire solve_f304_prefetch;
    wire iir_run_active;
    wire [3:0] iir_phase_index;
    wire iir_coeff_phase;
    wire iir_negative_phase;
    reg [2:0] iir_main_channel;
    reg [2:0] iir_add_channel;
    reg [2:0] iir_raw_read_channel;
    reg [2:0] iir_neg_read_channel;
    wire iir_main_is_negative;
    wire iir_main_request_valid;
    wire [15:0] iir_main_request_tag;
    wire iir_add_is_add1;
    wire iir_add_is_add2;
    wire iir_parallel_add_valid;
    wire iir_parallel_add_ready;
    wire [15:0] iir_parallel_add_tag;
    wire iir_prefetch_coeff;
    wire iir_prefetch_add2;
    wire iir_prefetch_real;
    wire iir_parallel_prefetch_valid;
    wire [2:0] iir_parallel_prefetch_channel;
    wire iir_negative_return;
    wire iir_current_return;
    wire iir_real_return;
    wire iir_imag_return;
    wire iir_previous_capture;
    wire [2:0] iir_capture_channel;
    wire iir_secondary_reads_raw;
    wire iir_state_write_valid;
    wire iir_state_write_neg;
    wire [2:0] iir_state_write_channel;
    wire [191:0] iir_state_write_data;
    wire [63:0] iir_raw_high;
    wire [63:0] iir_neg_high;
    wire [191:0] iir_raw_state_bus;
    wire [191:0] iir_neg_state_bus;
    wire [15:0] iir_source_scalar;
    wire iir_parallel_operand_a_pair;
    wire [191:0] iir_parallel_prefetch_operand_b;
    wire [15:0] iir_parallel_prefetch_scalar;
    reg [127:0] iir_retire_data;
    wire [3:0] iir_retire_word_count;
    wire iir_retire_last_chunk;
    wire iir_retire_last_channel;
    wire kernel_mean_reduce_return;
    wire kernel_pair_reduce_return;
    wire kernel_mean_accum_return;
    wire kernel_pair_accum_return;
    wire [5:0] kernel_reduce_scratch_index;
    wire [15:0] kernel_reduce_scratch_word;
    wire kernel_accum_add_valid;
    wire kernel_accum_add_event;
    wire kernel_stream_completion;
    reg [3:0] kernel_scratch_role0_row;
    reg [3:0] kernel_scratch_role1_row;
    wire accumulation_enabled;
    wire accumulation_plane;
    wire final_accumulation_plane;
    wire final_sequence_plane;
    wire first_sequence_plane;
    wire bias_enabled;
    wire bias_final_plane;
    wire aligned_accumulation_retire;
    wire window_issue_fire;
    wire gather_apx_request_valid;
    wire gather_apx_request_fire;
    wire compute_result_valid;
    wire [15:0] compute_result_tag;
    wire [15:0] compute_result_data;
    wire compute_done;
    wire compute_issue_fire;
    wire apx_add_request_valid;
    wire apx_add_request_fire;
    wire accumulation_pair_return;
    wire retire_stream_available;
    wire [127:0] scratch_compute_row;
    wire [127:0] retire_scratch_row;
    reg [15:0] retire_scratch_word;
    wire window_sequence_complete;
    wire scratch_first_plane_write;
    wire scratch_accumulation_write;
    wire scratch_bias_write;
    wire scratch_pool_scale_write;
    wire weight_slot_write;
    wire weight_slot_write_address;
    wire bias_add_request_valid;
    wire bias_epilogue_complete;
    wire same_pad;
    wire copy_mode;
    wire pool_mode;
    wire pool_scale_enabled;
    wire pool_scale_request_valid;
    wire pool_scale_request_fire;
    wire pool_scale_product_valid;
    wire pool_scale_direct_retire;
    wire pool_scale_result_accepted;
    wire pool_scalar_bypass;
    wire pool_scalar_result_valid;
    wire pool_chunk_overlap;
    wire [127:0] pool_chunk_build_data;
    wire [127:0] pool_chunk_full_data;
    wire source_response_accept;
    wire source_response_beat_accept;
    wire vector_source_accept;
    wire scalar_source_accept;
    wire source_buffer_pop;
    wire scalar_buffer_pop;
    wire gather_source_fire;
    wire gather_source_chain_request;
    wire result_chunk_complete;
    wire [3:0] completed_chunk_lanes;
    wire [3:0] bias_chunk_lanes;
    wire [3:0] accumulation_return_lanes;
    wire [127:0] result_chunk_with_current;
    wire [4:0] copy_request_lanes;
    wire copy_response_fire;
    wire copy_response_complete;
    wire copy_merge_next;
    wire copy_next_merge;
    wire [1:0] copy_advance_count;
    wire [1:0] copy_next_advance_count;
    wire copy_has_after_response;
    wire [4:0] copy_beat_lanes;
    wire [12:0] copy_next_source_address;
    wire [12:0] copy_next_destination_address;
    wire [4:0] emit_chunk_lanes;
    wire [4:0] emit_next_chunk_lanes;
    wire [11:0] emit_remaining_words;
    wire [11:0] emit_next_remaining_words;
    wire emit_finishes_group;
    wire emit_final_chunk;
    wire emit_has_next;
    wire emit_response_fire;
    wire emit_packet_done;
    wire [12:0] emit_next_source_address;
    wire pair_apx_request_valid;
    wire pair_apx_request_fire;
    wire pair_source_fire;
    wire pair_source_chain_request;
    wire pair_bias_request_valid;
    wire pair_bias_request_fire;
    wire pair_add_return;
    wire [1:0] pair_chunks_per_output;
    wire [2:0] pair_total_chunks;
    wire [5:0] pair_total_results;
    wire [5:0] pair_request_tag;
    wire pair_result_two_chunks;
    wire [3:0] pair_result_sample;
    wire [3:0] pair_result_scratch_index;
    wire pair_bias_output1;
    wire [1:0] pair_bias_chunk_in_output;
    wire [3:0] pair_bias_chunk_lanes;
    wire [12:0] pair_bias_destination;
    wire [127:0] pair_bias_scratch_row;
    wire [15:0] pair_selected_bias;
    wire tile_apx_request_valid;
    wire tile_apx_request_fire;
    wire [15:0] tile_apx_request_tag;
    reg [1:0] live_apx_external_a_source_select;
    localparam [3:0] SHARED_APX_OWNER_NONE      = 4'd0;
    localparam [3:0] SHARED_APX_OWNER_KERNEL    = 4'd1;
    localparam [3:0] SHARED_APX_OWNER_TILE      = 4'd2;
    localparam [3:0] SHARED_APX_OWNER_GENERIC   = 4'd3;
    localparam [3:0] SHARED_APX_OWNER_POOL      = 4'd4;
    localparam [3:0] SHARED_APX_OWNER_PAIR_BIAS = 4'd5;
    localparam [3:0] SHARED_APX_OWNER_ADD       = 4'd6;
    localparam [3:0] SHARED_APX_OWNER_PAIR      = 4'd7;
    localparam [3:0] SHARED_APX_OWNER_GATHER    = 4'd8;
    localparam [3:0] SHARED_APX_OWNER_WINDOW    = 4'd9;
    reg [3:0] shared_apx_live_owner;
    reg [1:0] shared_apx_live_operation;
    reg [4:0] shared_apx_live_lanes;
    reg [15:0] shared_apx_live_tag;
    reg shared_apx_live_add_vector;
    reg [1:0] shared_apx_live_operand_a_select;
    reg [1:0] shared_apx_live_operand_b_select;
    reg [1:0] shared_apx_live_external_a_select;
    reg shared_apx_live_weight_slot;
    reg shared_apx_live_operand_a_negate;
    reg shared_apx_live_operand_b_negate;
    reg shared_apx_live_narrow_b_scalar;
    reg shared_apx_live_window_shift;
    reg [15:0] shared_apx_live_window_sample;
    wire shared_apx_live_valid;
    wire [3:0] shared_apx_capture_owner;
    wire kernel_scalar_command_accept;
    wire tile_reduce_return;
    wire [3:0] tile_scratch_row;
    wire tile_retire_phase;
    wire generic_mode;
    wire generic_apx_request_valid;
    wire generic_apx_request_fire;
    wire generic_source_accept;
    wire generic_source_consumed;
    wire [11:0] pair_next_remaining_samples;
    wire [4:0] pair_next_block_samples;
    wire scalar_post_enabled;
    wire window_scalar_post_request_valid;
    wire scalar_post_request_valid;
    wire scalar_post_retire;
    wire scalar_post_last_return;
    wire [127:0] scalar_post_scratch_row;
    reg [15:0] scalar_post_previous;

    wire engine_retire_valid;
    wire [12:0] engine_retire_destination;
    wire [3:0] engine_retire_word_count;
    wire [7:0] engine_retire_lane_mask;
    wire engine_retire_word_mode;
    wire [15:0] engine_retire_word_data;
    wire [127:0] engine_retire_lane_data;
    wire engine_retire_result;
    wire engine_retire_last;

    // {valid,result,last,word_mode,destination,count,mask,word,lane_data}
    // Four mutually-exclusive execution domains compose locally and merge as
    // a one-hot transaction, replacing the former sixteen-deep priority mux.
    reg [172:0] kernel_retire_candidate;
    reg [172:0] service_retire_candidate;
    reg [172:0] vector_retire_candidate;
    reg [172:0] window_retire_candidate;
    wire [172:0] engine_retire_candidate;
    wire kernel_retire_domain;
    wire service_retire_domain;
    wire vector_retire_domain;

    // One registered transaction is the complete retire payload boundary.
    // unified_retire owns only drain state/index and never mirrors this data.
    reg [12:0] retire_packet_destination_q;
    reg [3:0] retire_packet_word_count_q;
    reg [7:0] retire_packet_lane_mask_q;
    reg [127:0] retire_packet_data_q;
    reg retire_packet_last_q;
    wire engine_retire_accept;
    wire engine_retire_full_commit;
    wire [1:0] engine_retire_state;

    wire retire_ready;
    wire retire_ack;
    wire retire_result_done;
    wire [3:0] retire_a_valid;
    wire [51:0] retire_a_address;
    wire [63:0] retire_a_data;
    wire [3:0] retire_b_valid;
    wire [51:0] retire_b_address;
    wire [63:0] retire_b_data;
    wire [15:0] retired_window_result;

    wire local_state_write_enable;
    wire local_state_write_dual_bank;
    wire local_state_write_bank;
    wire [2:0] local_state_write_index;
    wire [7:0] local_state_write_mask;
    wire [127:0] local_state_write_payload;
    wire [127:0] local_state_write_even_data;
    wire [127:0] local_state_write_odd_data;

    wire [3:0] memory_a_response_valid;
    wire [63:0] memory_a_response_data;
    wire [3:0] memory_b_response_valid;
    wire [63:0] memory_b_response_data;
    wire [3:0] service_memory_a_response_valid;
    wire [63:0] service_memory_a_response_data;
    wire [3:0] service_memory_b_response_valid;
    wire [63:0] service_memory_b_response_data;
    wire [3:0] memory_a_valid;
    wire [3:0] memory_a_write;
    wire [51:0] memory_a_address;
    wire [63:0] memory_a_write_data;
    wire [3:0] memory_b_valid;
    wire [3:0] memory_b_write;
    wire [51:0] memory_b_address;
    wire [63:0] memory_b_write_data;

    // Collapse all local-state producers into one architectural write owner.
    // Only the back-substitution product return writes both physical banks;
    // every other producer addresses one logical row through its parity bit.
    assign local_state_write_enable = solve_product_store ||
                                      scratch_write_enable;
    assign local_state_write_dual_bank = solve_product_store;
    assign local_state_write_bank = solve_product_store ?
                                    1'b0 : scratch_write_row[0];
    assign local_state_write_index = solve_product_store ?
                                     kernel_product_row_q[2:0] :
                                     scratch_write_row[3:1];
    assign local_state_write_mask = solve_product_store ?
                                    8'hFF : scratch_write_mask;
    assign local_state_write_payload = scratch_write_word_mode ?
        {8{scratch_write_word_data}} : scratch_write_data;
    assign local_state_write_even_data = solve_product_store ?
                                         apx_product_bus[127:0] :
                                         local_state_write_payload;
    assign local_state_write_odd_data = solve_product_store ?
                                        apx_product_bus[255:128] :
                                        local_state_write_payload;
    banked_local_state_2r1w u_accumulation_scratch (
        .clk(clk),
        .read0_index(scratch_role0_row[3:1]),
        .even_read0_data(scratch_even_read0_data),
        .read1_index(scratch_role1_row[3:1]),
        .even_read1_data(scratch_even_read1_data),
        .odd_read0_data(scratch_odd_read0_data),
        .odd_read1_data(scratch_odd_read1_data),
        .write_enable(local_state_write_enable),
        .write_dual_bank(local_state_write_dual_bank),
        .write_bank(local_state_write_bank),
        .write_index(local_state_write_index),
        .write_mask(local_state_write_mask),
        .write_even_data(local_state_write_even_data),
        .write_odd_data(local_state_write_odd_data)
    );

    function [7:0] lane_mask;
        input [3:0] lane_count;
        begin
            case (lane_count)
                4'd1: lane_mask = 8'h01;
                4'd2: lane_mask = 8'h03;
                4'd3: lane_mask = 8'h07;
                4'd4: lane_mask = 8'h0F;
                4'd5: lane_mask = 8'h1F;
                4'd6: lane_mask = 8'h3F;
                4'd7: lane_mask = 8'h7F;
                default: lane_mask = 8'hFF;
            endcase
        end
    endfunction

    function [127:0] insert_chunk_word;
        input [127:0] chunk;
        input [15:0] word_value;
        input [2:0] word_index;
        reg [127:0] updated_chunk;
        begin
            updated_chunk = chunk;
            case (word_index)
                3'd0: updated_chunk[15:0] = word_value;
                3'd1: updated_chunk[31:16] = word_value;
                3'd2: updated_chunk[47:32] = word_value;
                3'd3: updated_chunk[63:48] = word_value;
                3'd4: updated_chunk[79:64] = word_value;
                3'd5: updated_chunk[95:80] = word_value;
                3'd6: updated_chunk[111:96] = word_value;
                default: updated_chunk[127:112] = word_value;
            endcase
            insert_chunk_word = updated_chunk;
        end
    endfunction

    function [15:0] select_chunk_word;
        input [127:0] chunk;
        input [2:0] word_index;
        begin
            case (word_index)
                3'd0: select_chunk_word = chunk[15:0];
                3'd1: select_chunk_word = chunk[31:16];
                3'd2: select_chunk_word = chunk[47:32];
                3'd3: select_chunk_word = chunk[63:48];
                3'd4: select_chunk_word = chunk[79:64];
                3'd5: select_chunk_word = chunk[95:80];
                3'd6: select_chunk_word = chunk[111:96];
                default: select_chunk_word = chunk[127:112];
            endcase
        end
    endfunction

    function [15:0] refinement_low_word;
        input [15:0] source;
        reg [4:0] exponent_field;
        reg [4:0] low_mantissa;
        reg [2:0] leading_position;
        reg [5:0] residual_exponent;
        reg [10:0] residual_mantissa;
        begin
            exponent_field = source[14:10];
            low_mantissa = source[4:0];
            if (low_mantissa[4])
                leading_position = 3'd4;
            else if (low_mantissa[3])
                leading_position = 3'd3;
            else if (low_mantissa[2])
                leading_position = 3'd2;
            else if (low_mantissa[1])
                leading_position = 3'd1;
            else
                leading_position = 3'd0;
            residual_exponent = exponent_field + leading_position - 6'd10;
            residual_mantissa = 11'd0;
            if ((exponent_field == 5'd31) || (low_mantissa == 5'd0)) begin
                refinement_low_word = 16'd0;
            end
            else if (exponent_field == 5'd0) begin
                refinement_low_word = {source[15], 10'd0, low_mantissa};
            end
            else if ((exponent_field + leading_position) > 6'd10) begin
                residual_mantissa =
                    (low_mantissa - (5'd1 << leading_position)) <<
                    (4'd10 - leading_position);
                refinement_low_word = {
                    source[15], residual_exponent[4:0],
                    residual_mantissa[9:0]
                };
            end
            else begin
                residual_mantissa = low_mantissa <<
                    (exponent_field - 5'd1);
                refinement_low_word = {
                    source[15], 5'd0, residual_mantissa[9:0]
                };
            end
        end
    endfunction

    function [15:0] rsqrt_seed_word;
        input [4:0] exponent_field;
        begin
            case (exponent_field)
                5'd0: rsqrt_seed_word = 16'h59A8;
                5'd1: rsqrt_seed_word = 16'h5800;
                5'd2: rsqrt_seed_word = 16'h55A8;
                5'd3: rsqrt_seed_word = 16'h5400;
                5'd4: rsqrt_seed_word = 16'h51A8;
                5'd5: rsqrt_seed_word = 16'h5000;
                5'd6: rsqrt_seed_word = 16'h4DA8;
                5'd7: rsqrt_seed_word = 16'h4C00;
                5'd8: rsqrt_seed_word = 16'h49A8;
                5'd9: rsqrt_seed_word = 16'h4800;
                5'd10: rsqrt_seed_word = 16'h45A8;
                5'd11: rsqrt_seed_word = 16'h4400;
                5'd12: rsqrt_seed_word = 16'h41A8;
                5'd13: rsqrt_seed_word = 16'h4000;
                5'd14: rsqrt_seed_word = 16'h3DA8;
                5'd15: rsqrt_seed_word = 16'h3C00;
                5'd16: rsqrt_seed_word = 16'h39A8;
                5'd17: rsqrt_seed_word = 16'h3800;
                5'd18: rsqrt_seed_word = 16'h35A8;
                5'd19: rsqrt_seed_word = 16'h3400;
                5'd20: rsqrt_seed_word = 16'h31A8;
                5'd21: rsqrt_seed_word = 16'h3000;
                5'd22: rsqrt_seed_word = 16'h2DA8;
                5'd23: rsqrt_seed_word = 16'h2C00;
                5'd24: rsqrt_seed_word = 16'h29A8;
                5'd25: rsqrt_seed_word = 16'h2800;
                5'd26: rsqrt_seed_word = 16'h25A8;
                5'd27: rsqrt_seed_word = 16'h2400;
                5'd28: rsqrt_seed_word = 16'h21A8;
                5'd29: rsqrt_seed_word = 16'h2000;
                5'd30: rsqrt_seed_word = 16'h1DA8;
                default: rsqrt_seed_word = 16'h1C00;
            endcase
        end
    endfunction

    function fp16_less_than;
        input [15:0] left;
        input [15:0] right;
        begin
            if ((left[14:0] == 15'd0) && (right[14:0] == 15'd0))
                fp16_less_than = 1'b0;
            else if (left[15] != right[15])
                fp16_less_than = left[15];
            else if (!left[15])
                fp16_less_than = left[14:0] < right[14:0];
            else
                fp16_less_than = left[14:0] > right[14:0];
        end
    endfunction

    always @(*) begin
        case (compute_result_tag[2:0])
            3'd0: scalar_post_previous = scalar_post_scratch_row[15:0];
            3'd1: scalar_post_previous = scalar_post_scratch_row[31:16];
            3'd2: scalar_post_previous = scalar_post_scratch_row[47:32];
            3'd3: scalar_post_previous = scalar_post_scratch_row[63:48];
            3'd4: scalar_post_previous = scalar_post_scratch_row[79:64];
            3'd5: scalar_post_previous = scalar_post_scratch_row[95:80];
            3'd6: scalar_post_previous = scalar_post_scratch_row[111:96];
            default: scalar_post_previous = scalar_post_scratch_row[127:112];
        endcase
    end

    // Descriptor tags are local to one execution context.  Do not admit a new
    // context until the shared APX overlay has retired every token from the
    // previous one, otherwise an old local tag can alias the new descriptor.
    assign descriptor_ready = (state_q == STATE_IDLE) && !apx_busy &&
        !shared_apx_issue_valid_q;
    assign descriptor_complete = state_q == STATE_COMPLETE;
    assign busy = (state_q != STATE_IDLE) && (state_q != STATE_COMPLETE);
    // Two registered command slots form a hard scheduling boundary.  Ready is
    // derived only from local occupancy, never from the operand service's
    // combinational ready path.  A simultaneous head issue and new acceptance
    // replaces the head, preserving one-command-per-cycle steady throughput.
    assign service_request_ready = !operand_pending_valid_q;
    assign operand_command_fire = operand_command_valid_q &&
        operand_service_request_ready;
    assign kernel_state_active = state_q[4] && !state_q[3];
    assign tile_state_active = state_q[4] && state_q[3];
    assign compute_overlay_active = state_q[4];
    assign kernel_stat_kind = kernel_kind_q == KERNEL_PAIRWISE_STAT;
    assign kernel_triangular_kind = kernel_kind_q == KERNEL_TRIANGULAR;
    assign kernel_backsub_kind = kernel_kind_q == KERNEL_BACKSUB;
    assign kernel_recurrence_kind = kernel_kind_q == KERNEL_RECURRENCE;
    assign kernel_stat_active = kernel_state_active && kernel_stat_kind;
    assign kernel_triangular_active = kernel_state_active &&
        kernel_triangular_kind;
    assign kernel_backsub_active = kernel_state_active &&
        kernel_backsub_kind;
    assign kernel_recurrence_active = kernel_state_active &&
        kernel_recurrence_kind;
    assign kernel_schedule_step = (kernel_kind_q == KERNEL_TRIANGULAR) ?
        kernel_tri_step_q :
        ((kernel_kind_q == KERNEL_BACKSUB) ?
         kernel_backsub_step_q : kernel_stat_step_q);
    assign kernel_apx_owner = kernel_state_active;
    assign service_request_fire = service_request_valid &&
        service_request_ready;
    assign service_request_fast_feature =
        copy_mode || emit_mode_q ||
        (source_fast_tile_q && service_request_source &&
         ((service_request_lanes == 5'd4) ||
          (service_request_lanes == 5'd8) ||
          (service_request_lanes == 5'd16))) ||
        (pool_scalar_bypass && service_request_source);
    assign service_request_role =
        compute_overlay_active ?
        OPERAND_ROLE_KERNEL :
        (service_request_source ? OPERAND_ROLE_SOURCE :
         (service_request_bias ? OPERAND_ROLE_BIAS :
          OPERAND_ROLE_WEIGHT));
    // Form owner-local request intent before the shared operand command slot.
    // The global arbiter still transports one canonical command, but unrelated
    // COPY/window predicates can no longer enter compound-kernel phase or row
    // update cones through service_request_valid.
    assign kernel_stat_service_request_valid = kernel_stat_active &&
        (((kernel_stat_step_q == STAT_MEAN_STREAM) &&
          (kernel_request_count_q < {2'd0, bound0_q[3:0]})) ||
         ((kernel_stat_step_q == STAT_MEAN_STREAM) &&
          kernel_stream_completion &&
          ((kernel_result_count_q + 6'd1) >=
           {2'd0, bound0_q[3:0]}) &&
          (({7'd0, kernel_chunk_q} + 12'd1) <
           ((bound1_q + 12'd15) >> 5'd4))) ||
         ((kernel_stat_step_q == STAT_MEAN_RETIRE) &&
          kernel_retire_complete) ||
         (kernel_stat_step_q == STAT_PAIR_ROW_REQ) ||
         (kernel_stat_step_q == STAT_PAIR_COL_REQ) ||
         ((kernel_stat_step_q == STAT_PAIR_ROW_WAIT) &&
          source_buffer0_valid_q && (kernel_row_q != 4'd0)) ||
         ((kernel_stat_step_q == STAT_PAIR_COL_WAIT) &&
          kernel_service_response_accept &&
          ((kernel_column_q +
            (kernel_weight_resident_valid_q ? 4'd2 : 4'd1)) <
           kernel_row_q)) ||
         ((kernel_stat_step_q == STAT_PAIR_DRAIN) &&
          kernel_stream_completion &&
          ((kernel_result_count_q + 6'd1) >= kernel_index_q) &&
          (({7'd0, kernel_chunk_q} + 12'd1) <
           ((bound1_q + 12'd15) >> 5'd4))));
    assign kernel_tri_service_request_valid = kernel_triangular_active &&
        ((kernel_tri_step_q == TRI_CONST_REQ) ||
         (kernel_tri_step_q == TRI_STAT_REQ));
    assign kernel_backsub_service_request_valid = kernel_backsub_active &&
        ((kernel_backsub_step_q == BACKSUB_MATRIX_REQ) ||
         (kernel_backsub_step_q == BACKSUB_INVERSE_REQ) ||
         (kernel_backsub_step_q == BACKSUB_RAW_REQ) ||
         ((kernel_backsub_step_q == BACKSUB_PRODUCT_STREAM) &&
          (kernel_request_count_q < {2'd0, kernel_row_q})));
    assign iir_service_request_valid = kernel_recurrence_active &&
        (((iir_phase_q == REC_SOURCE) && !iir_source_pending_q) ||
         (iir_run_active && !iir_drain_q &&
          (|iir_samples_remaining_q[11:1]) &&
          !iir_source_pending_q && !iir_prefetch_valid_q) ||
         (((iir_phase_q == REC_COS_WAIT) ||
           (iir_phase_q == REC_SINE_WAIT)) &&
          !iir_source_pending_q));

    assign kernel_scheduler_service_fire = service_request_ready &&
        (kernel_stat_service_request_valid ||
         kernel_tri_service_request_valid ||
         kernel_backsub_service_request_valid);
    assign kernel_stat_service_fire = service_request_ready &&
        kernel_stat_service_request_valid;
    assign iir_service_request_fire = service_request_ready &&
        iir_service_request_valid;

    shared_kernel_step_sequencer kernel_step_sequencer_inst (
        .operator_select(kernel_kind_q),
        .step_index(kernel_schedule_step),
        .service_request_fire(kernel_scheduler_service_fire),
        .apx_request_fire(kernel_apx_request_fire),
        .completion_events(kernel_completion_events),
        .retire_complete(kernel_retire_complete),
        .scalar_request_fire(kernel_scalar_add_fire),
        .retire_phase(kernel_schedule_retire),
        .transition_valid(),
        .advance(kernel_schedule_advance),
        .next_step_index(kernel_schedule_next_phase)
    );

    // Row addressing has one dedicated state island.  Keeping this register
    // out of the descriptor-wide sequential mux prevents generic convolution
    // bounds and emit control from entering the matrix-kernel address path.
    always @(*) begin
        kernel_row_base_d = kernel_row_base_q;
        kernel_row_base_load = 1'b0;
        case (state_q)
            STATE_FIRST_WEIGHT_WAIT: begin
                if (!copy_mode && service_tile_response_valid &&
                    (tile_dot_mode_q || kernel_active_q)) begin
                    kernel_row_base_d = source_address_q;
                    kernel_row_base_load = 1'b1;
                end
                else begin
                end
            end
            STATE_TILE_DOT: begin
                if ((tile_phase_q == TILE_RETIRE_IMAG) && retire_ack &&
                    ((kernel_row_q + 4'd1) < bound0_q[3:0])) begin
                    kernel_row_base_d =
                        source_i0_base_q + source_stride0_q;
                    kernel_row_base_load = 1'b1;
                end
                else begin
                end
            end
            STATE_KERNEL: begin
                if (kernel_kind_q == KERNEL_PAIRWISE_STAT) begin
                    case (kernel_stat_step_q)
                        STAT_MEAN_STREAM: begin
                            if (kernel_stat_service_fire) begin
                                kernel_row_base_d =
                                    kernel_row_base_q + source_stride0_q;
                                kernel_row_base_load = 1'b1;
                            end
                            else begin
                            end
                            if (kernel_stream_completion &&
                                ((kernel_result_count_q + 6'd1) >=
                                 {2'd0, bound0_q[3:0]}) &&
                                (({7'd0, kernel_chunk_q} + 12'd1) <
                                 ((bound1_q + 12'd15) >> 5'd4))) begin
                                kernel_row_base_d = kernel_chunk_base_q +
                                    (source_stride1_q << 5'd4) +
                                    (kernel_stat_service_fire ?
                                     source_stride0_q : 13'd0);
                                kernel_row_base_load = 1'b1;
                            end
                            else begin
                            end
                        end
                        STAT_MEAN_RETIRE: begin
                            if (kernel_retire_complete) begin
                                kernel_row_base_d = source_address_q;
                                kernel_row_base_load = 1'b1;
                            end
                            else begin
                            end
                        end
                        STAT_PAIR_ROW_WAIT: begin
                            if ((kernel_row_q == 4'd0) &&
                                kernel_apx_request_fire &&
                                ((kernel_row_q + 4'd1) <
                                 bound0_q[3:0])) begin
                                kernel_row_base_d =
                                    kernel_row_base_q + source_stride0_q;
                                kernel_row_base_load = 1'b1;
                            end
                            else begin
                            end
                        end
                        STAT_PAIR_SELF_ISSUE: begin
                            if (kernel_apx_request_fire &&
                                ((kernel_row_q + 4'd1) <
                                 bound0_q[3:0])) begin
                                kernel_row_base_d =
                                    kernel_row_base_q + source_stride0_q;
                                kernel_row_base_load = 1'b1;
                            end
                            else begin
                            end
                        end
                        STAT_PAIR_DRAIN: begin
                            if (kernel_stream_completion &&
                                ((kernel_result_count_q + 6'd1) >=
                                 kernel_index_q)) begin
                                if (({7'd0, kernel_chunk_q} + 12'd1) >=
                                    ((bound1_q + 12'd15) >> 5'd4))
                                    kernel_row_base_d =
                                        destination_address_q;
                                else
                                    kernel_row_base_d = kernel_chunk_base_q +
                                        (source_stride1_q << 5'd4);
                                kernel_row_base_load = 1'b1;
                            end
                            else begin
                            end
                        end
                        STAT_POST_RETIRE_LOW: begin
                            if (kernel_retire_complete &&
                                (kernel_row_q == kernel_column_q) &&
                                ((kernel_row_q + 4'd1) <
                                 bound0_q[3:0])) begin
                                kernel_row_base_d =
                                    kernel_row_base_q + {1'b0, bound0_q};
                                kernel_row_base_load = 1'b1;
                            end
                            else begin
                            end
                        end
                        default: begin
                        end
                    endcase
                end
                else if (kernel_kind_q == KERNEL_BACKSUB) begin
                    if ((kernel_backsub_step_q == BACKSUB_RETIRE_HIGH) &&
                        kernel_retire_complete) begin
                        if (({7'd0, kernel_chunk_q} + 12'd1) <
                            ((bound1_q + 12'd15) >> 5'd4)) begin
                            kernel_row_base_d = kernel_row_base_q +
                                (source_stride1_q << 5'd4);
                            kernel_row_base_load = 1'b1;
                        end
                        else if ((kernel_row_q + 4'd1) <
                                 bound0_q[3:0]) begin
                            kernel_row_base_d =
                                source_i0_base_q + source_stride0_q;
                            kernel_row_base_load = 1'b1;
                        end
                        else begin
                        end
                    end
                    else begin
                    end
                end
                else begin
                end
            end
            default: begin
            end
        endcase
    end

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n)
            kernel_row_base_q <= 13'd0;
        else if (kernel_row_base_load)
            kernel_row_base_q <= kernel_row_base_d;
        else begin
        end
    end

    assign kernel_completion_events = {
        kernel_fixed_completion_events_q[9:5],
        kernel_pair_d202_event,
        kernel_fixed_completion_events_q[4:0]
    };

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            kernel_fixed_completion_events_q <= 10'd0;
            kernel_pair_events_q <= 13'd0;
            kernel_product_d100_event_q <= 1'b0;
            kernel_product_f2_event_q <= 1'b0;
            kernel_product_row_q <= 4'd0;
            kernel_reduce_metadata_q <= 8'd0;
            kernel_post_add_metadata_q <= 9'd0;
            kernel_iir_product_metadata_q <= 7'd0;
            kernel_iir_pair_metadata_q <= 6'd0;
        end
        else begin
            // Pre-valid/tag are APX pipeline registers exactly one cycle ahead
            // of the data result.  Predecoding them here aligns compact event
            // IDs and address metadata with the result without adding latency.
            kernel_fixed_completion_events_q <= {
                kernel_apx_owner && apx_post_add_pre_valid &&
                    (apx_post_add_pre_tag[15:8] == 8'hE1),
                kernel_apx_owner && apx_post_add_pre_valid &&
                    (apx_post_add_pre_tag == 16'hE005),
                kernel_apx_owner && apx_post_add_pre_valid &&
                    (apx_post_add_pre_tag == 16'hE001),
                kernel_apx_owner && apx_reduce_pre_valid &&
                    (apx_reduce_pre_tag == 16'hD200),
                kernel_apx_owner && apx_reduce_pre_valid &&
                    (apx_reduce_pre_tag == 16'hE002),
                kernel_apx_owner && apx_product_pre_valid &&
                    (apx_product_pre_tag == 16'hF400),
                kernel_apx_owner && apx_product_pre_valid &&
                    (apx_product_pre_tag == 16'hE004),
                kernel_apx_owner && apx_product_pre_valid &&
                    (apx_product_pre_tag == 16'hE003),
                kernel_apx_owner && apx_product_pre_valid &&
                    (apx_product_pre_tag == 16'hE000),
                kernel_apx_owner && apx_product_pre_valid &&
                    (apx_product_pre_tag == 16'hB001)
            };
            kernel_pair_events_q <= {
                kernel_apx_owner && apx_pair_pre_valid &&
                    (apx_pair_pre_tag[15:8] == 8'hE1),
                kernel_apx_owner && apx_pair_pre_valid &&
                    (apx_pair_pre_tag == 16'hE001),
                kernel_apx_owner && apx_pair_pre_valid &&
                    (apx_pair_pre_tag == 16'hF305),
                kernel_apx_owner && apx_pair_pre_valid &&
                    (apx_pair_pre_tag == 16'hF304),
                kernel_apx_owner && apx_pair_pre_valid &&
                    (apx_pair_pre_tag == 16'hF303),
                kernel_apx_owner && apx_pair_pre_valid &&
                    (apx_pair_pre_tag == 16'hF302),
                kernel_apx_owner && apx_pair_pre_valid &&
                    (apx_pair_pre_tag == 16'hF301),
                kernel_apx_owner && apx_pair_pre_valid &&
                    (apx_pair_pre_tag == 16'hF000),
                kernel_apx_owner && apx_pair_pre_valid &&
                    (apx_pair_pre_tag == 16'hD202),
                kernel_apx_owner && apx_pair_pre_valid &&
                    (apx_pair_pre_tag == 16'hD201),
                kernel_apx_owner && apx_pair_pre_valid &&
                    (apx_pair_pre_tag == 16'hD103),
                kernel_apx_owner && apx_pair_pre_valid &&
                    (apx_pair_pre_tag == 16'hD102),
                kernel_apx_owner && apx_pair_pre_valid &&
                    (apx_pair_pre_tag == 16'hD101)
            };
            kernel_product_d100_event_q <=
                kernel_apx_owner && apx_product_pre_valid &&
                (apx_product_pre_tag == 16'hD100);
            kernel_product_f2_event_q <=
                kernel_apx_owner && apx_product_pre_valid &&
                (apx_product_pre_tag[15:8] == 8'hF2);
            if (kernel_apx_owner && apx_product_pre_valid &&
                (apx_product_pre_tag[15:8] == 8'hF2))
                kernel_product_row_q <= apx_product_pre_tag[3:0];
            kernel_reduce_metadata_q[7:6] <= {
                kernel_apx_owner && apx_reduce_pre_valid &&
                    (apx_reduce_pre_tag[15:12] == 4'hC),
                kernel_apx_owner && apx_reduce_pre_valid &&
                    (apx_reduce_pre_tag[15:12] == 4'hA)
            };
            if (kernel_apx_owner && apx_reduce_pre_valid &&
                ((apx_reduce_pre_tag[15:12] == 4'hA) ||
                 (apx_reduce_pre_tag[15:12] == 4'hC)))
                kernel_reduce_metadata_q[5:0] <=
                    apx_reduce_pre_tag[5:0];
            kernel_post_add_metadata_q[8:7] <= {
                kernel_apx_owner && apx_post_add_pre_valid &&
                    (apx_post_add_pre_tag[15:12] == 4'h6),
                kernel_apx_owner && apx_post_add_pre_valid &&
                    (apx_post_add_pre_tag[15:12] == 4'h5)
            };
            if (kernel_apx_owner && apx_post_add_pre_valid &&
                ((apx_post_add_pre_tag[15:12] == 4'h5) ||
                 (apx_post_add_pre_tag[15:12] == 4'h6)))
                kernel_post_add_metadata_q[6:0] <=
                    apx_post_add_pre_tag[6:0];
            kernel_iir_product_metadata_q[6:3] <= {
                kernel_recurrence_active && apx_product_pre_valid &&
                    (apx_product_pre_tag[15:12] == REC_TAG_COEFF),
                kernel_recurrence_active && apx_product_pre_valid &&
                    (apx_product_pre_tag[15:12] == REC_TAG_COSINE),
                kernel_recurrence_active && apx_product_pre_valid &&
                    (apx_product_pre_tag[15:12] == REC_TAG_NEGATE),
                kernel_recurrence_active && apx_product_pre_valid &&
                    (apx_product_pre_tag[15:12] == REC_TAG_SINE)
            };
            if (kernel_recurrence_active && apx_product_pre_valid &&
                ((apx_product_pre_tag[15:12] == REC_TAG_COEFF) ||
                 (apx_product_pre_tag[15:12] == REC_TAG_COSINE) ||
                 (apx_product_pre_tag[15:12] == REC_TAG_NEGATE) ||
                 (apx_product_pre_tag[15:12] == REC_TAG_SINE)))
                kernel_iir_product_metadata_q[2:0] <=
                    apx_product_pre_tag[2:0];
            kernel_iir_pair_metadata_q[5:3] <= {
                kernel_recurrence_active && apx_pair_pre_valid &&
                    (apx_pair_pre_tag[15:12] == REC_TAG_ADD1),
                kernel_recurrence_active && apx_pair_pre_valid &&
                    (apx_pair_pre_tag[15:12] == REC_TAG_CURRENT),
                kernel_recurrence_active && apx_pair_pre_valid &&
                    (apx_pair_pre_tag[15:12] == REC_TAG_REAL)
            };
            if (kernel_recurrence_active && apx_pair_pre_valid &&
                ((apx_pair_pre_tag[15:12] == REC_TAG_ADD1) ||
                 (apx_pair_pre_tag[15:12] == REC_TAG_CURRENT) ||
                 (apx_pair_pre_tag[15:12] == REC_TAG_REAL)))
                kernel_iir_pair_metadata_q[2:0] <=
                    apx_pair_pre_tag[2:0];
        end
    end

    assign kernel_retire_domain = tile_retire_phase ||
        (kernel_stat_active &&
         ((kernel_stat_step_q == STAT_MEAN_RETIRE) ||
          (kernel_stat_step_q == STAT_POST_RETIRE_LOW) ||
          (kernel_stat_step_q == STAT_POST_RETIRE_HIGH) ||
          (kernel_stat_step_q == STAT_DIAG_RETIRE))) ||
        (kernel_triangular_active && (kernel_tri_step_q == TRI_RETIRE)) ||
        (kernel_backsub_active &&
         ((kernel_backsub_step_q == BACKSUB_RETIRE_LOW) ||
          (kernel_backsub_step_q == BACKSUB_RETIRE_HIGH))) ||
        (kernel_recurrence_active && (iir_phase_q == REC_RETIRE));
    assign service_retire_domain =
        (state_q == STATE_FIRST_WEIGHT_WAIT) &&
        ((emit_mode_q && service_tile_response_valid) ||
         (copy_mode && service_response_valid));
    assign vector_retire_domain =
        ((state_q == STATE_EWISE_RESULT) && apx_product_valid) ||
        ((state_q == STATE_VECTOR_RESULT) && apx_pair_valid) ||
        ((state_q == STATE_PAIR_BIAS) && !flags_q[2] &&
         !pair_retire_pending_q) || pair_add_return;

    assign engine_retire_candidate = kernel_retire_domain ?
        kernel_retire_candidate :
        (service_retire_domain ? service_retire_candidate :
         (vector_retire_domain ? vector_retire_candidate :
          window_retire_candidate));
    assign engine_retire_valid = engine_retire_candidate[172];
    assign engine_retire_result = engine_retire_candidate[171];
    assign engine_retire_last = engine_retire_candidate[170];
    assign engine_retire_word_mode = engine_retire_candidate[169];
    assign engine_retire_destination = engine_retire_candidate[168:156];
    assign engine_retire_word_count = engine_retire_candidate[155:152];
    assign engine_retire_lane_mask = engine_retire_candidate[151:144];
    assign engine_retire_word_data = engine_retire_candidate[143:128];
    assign engine_retire_lane_data = engine_retire_candidate[127:0];

    assign engine_retire_accept = engine_retire_valid && retire_ready;
    assign engine_retire_full_commit =
        (engine_retire_word_count == 4'd8) &&
        (engine_retire_destination[2:0] == 3'd0);
    assign engine_retire_state = engine_retire_result ?
        RETIRE_STATE_RESULT :
        (((engine_retire_word_count == 4'd1) ||
          engine_retire_full_commit) ?
         RETIRE_STATE_COMMIT : RETIRE_STATE_TAIL);

    // Retire ownership is decoded once in the common scheduler.  Destination
    // and data composition remain phase-local.
    assign kernel_retire_phase = kernel_apx_owner &&
        (kernel_recurrence_active ? (iir_phase_q == REC_RETIRE) :
         kernel_schedule_retire);
    assign kernel_retire_accept = kernel_retire_phase &&
        engine_retire_accept;
    assign kernel_retire_complete = kernel_retire_accepted_q && retire_ack;
    assign kernel_solve_high_chain_accept = kernel_backsub_active &&
        (kernel_backsub_step_q == BACKSUB_RETIRE_LOW) &&
        kernel_retire_accepted_q && !kernel_retire_chained_q &&
        engine_retire_accept;
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            kernel_retire_accepted_q <= 1'b0;
            kernel_retire_chained_q <= 1'b0;
        end
        else if (!kernel_retire_phase) begin
            kernel_retire_accepted_q <= 1'b0;
            kernel_retire_chained_q <= 1'b0;
        end
        else if (!kernel_retire_accepted_q && kernel_retire_accept) begin
            kernel_retire_accepted_q <= 1'b1;
            kernel_retire_chained_q <= 1'b0;
        end
        else if (kernel_retire_complete) begin
            kernel_retire_accepted_q <=
                kernel_backsub_active &&
                (kernel_backsub_step_q == BACKSUB_RETIRE_LOW) &&
                (kernel_retire_chained_q ||
                 kernel_solve_high_chain_accept);
            kernel_retire_chained_q <= 1'b0;
        end
        else if (kernel_solve_high_chain_accept)
            kernel_retire_chained_q <= 1'b1;
    end
    assign service_response_accept = service_response_valid &&
        service_response_ready;
    assign service_tile_response_valid = service_response_valid &&
        service_response_last;
    assign service_tile_response_accept = service_response_accept &&
        service_response_last;
    assign kernel_service_response_beat_accept = kernel_apx_owner &&
        (operand_response_role_q == OPERAND_ROLE_KERNEL) &&
        service_response_accept;
    assign tile_service_response_beat_accept =
        tile_state_active &&
        (operand_response_role_q == OPERAND_ROLE_KERNEL) &&
        service_response_accept;
    assign kernel_service_response_valid = kernel_apx_owner &&
        (operand_response_role_q == OPERAND_ROLE_KERNEL) &&
        service_tile_response_valid;
    assign kernel_service_response_accept =
        kernel_service_response_valid && service_response_ready;
    assign kernel_pair_col_resident_load = kernel_stat_active &&
        (kernel_stat_step_q == STAT_PAIR_COL_WAIT) &&
        kernel_service_response_accept;
    assign kernel_pair_col_resident_pop = kernel_stat_active &&
        (kernel_stat_step_q == STAT_PAIR_COL_WAIT) &&
        kernel_weight_resident_valid_q && kernel_apx_request_fire;
    assign kernel_solve_source_pop = kernel_backsub_active &&
        kernel_apx_request_fire &&
        (((kernel_backsub_step_q == BACKSUB_RAW_WAIT) &&
          (kernel_apx_request_tag == 16'hF000)) ||
         ((kernel_backsub_step_q == BACKSUB_PRODUCT_STREAM) &&
          (kernel_apx_request_tag[15:8] == 8'hF2)));
    // Wide response data terminates at a resident register before APX issue.
    // The kernel scheduler observes only registered valid/event bits.
    assign kernel_post_mul_load_bypass = kernel_stat_active &&
        (kernel_stat_step_q == STAT_POST_MUL_LOAD);
    assign kernel_post_mul_load_fire = kernel_post_mul_load_bypass &&
        kernel_apx_request_fire;
    assign kernel_source_service_load = kernel_stat_active &&
        kernel_service_response_accept &&
        ((kernel_stat_step_q == STAT_MEAN_STREAM) ||
         (kernel_stat_step_q == STAT_PAIR_ROW_WAIT));
    assign kernel_source_service_beat_accept = kernel_stat_active &&
        kernel_service_response_beat_accept &&
        ((kernel_stat_step_q == STAT_MEAN_STREAM) ||
         (kernel_stat_step_q == STAT_PAIR_ROW_WAIT));
    assign kernel_solve_stream_load = kernel_backsub_active &&
        kernel_service_response_accept &&
        ((kernel_backsub_step_q == BACKSUB_RAW_WAIT) ||
         (kernel_backsub_step_q == BACKSUB_PRODUCT_STREAM));
    assign kernel_source_local_load = kernel_stat_active &&
        ((kernel_stat_step_q == STAT_MEAN_SCALE_LOAD) ||
         (kernel_stat_step_q == STAT_TRACE_LOAD) ||
         ((kernel_stat_step_q == STAT_POST_MUL_LOAD) &&
          !kernel_post_mul_load_fire) ||
         (kernel_stat_step_q == STAT_DIAG_ADD_LOAD));
    assign kernel_source_result_load = kernel_stat_active &&
        (((kernel_stat_step_q == STAT_POST_MUL_WAIT) &&
          kernel_completion_events[1]) ||
         ((kernel_stat_step_q == STAT_TRACE_WAIT) &&
          kernel_completion_events[6]) ||
         ((kernel_stat_step_q == STAT_TRACE_SCALE_WAIT) &&
          kernel_completion_events[2]) ||
         ((kernel_stat_step_q == STAT_TRACE_REG_WAIT) &&
          kernel_completion_events[3]));
    assign kernel_source_load = kernel_source_service_load ||
        kernel_source_local_load ||
        kernel_source_result_load;
    assign kernel_source_pop =
        (kernel_stat_active &&
         ((kernel_apx_request_fire &&
          ((kernel_stat_step_q == STAT_MEAN_STREAM) ||
           ((kernel_stat_step_q == STAT_PAIR_ROW_WAIT) &&
            (kernel_row_q == 4'd0)) ||
           (kernel_stat_step_q == STAT_MEAN_SCALE_ISSUE) ||
           (kernel_stat_step_q == STAT_PAIR_SELF_ISSUE) ||
           (kernel_stat_step_q == STAT_POST_MUL_ISSUE) ||
           (kernel_stat_step_q == STAT_TRACE_ISSUE) ||
           (kernel_stat_step_q == STAT_TRACE_SCALE_ISSUE) ||
           (kernel_stat_step_q == STAT_TRACE_REG_ISSUE))) ||
          kernel_scalar_add_fire));

    // A column response is acknowledged into the existing active-weight
    // resident.  APX may consume it only from the registered-valid state on
    // the following cycle, so RAM response timing cannot reach APX control.
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n)
            kernel_weight_resident_valid_q <= 1'b0;
        else if (!kernel_stat_active ||
                 (kernel_stat_step_q != STAT_PAIR_COL_WAIT))
            kernel_weight_resident_valid_q <= 1'b0;
        else begin
            case ({kernel_pair_col_resident_load,
                   kernel_pair_col_resident_pop})
                2'b10: kernel_weight_resident_valid_q <= 1'b1;
                2'b01: kernel_weight_resident_valid_q <= 1'b0;
                2'b11: kernel_weight_resident_valid_q <= 1'b1;
                default: begin
                end
            endcase
        end
    end

    assign factor_floor = kernel_scalar_bank_q[15:0];
    assign factor_scalar = kernel_scalar_bank_q[31:16];
    assign factor_value = kernel_scalar_bank_q[47:32];
    assign factor_estimate = kernel_scalar_bank_q[63:48];
    assign factor_temp = kernel_scalar_bank_q[79:64];
    assign factor_inverse = kernel_scalar_bank_q[95:80];
    assign factor_refine_left = kernel_scalar_bank_q[111:96];
    assign factor_refine_right = kernel_scalar_bank_q[127:112];
    assign factor_refine_result = kernel_scalar_bank_q[143:128];
    assign factor_factor_left = select_chunk_word(
        scratch_role0_data, kernel_index_q[2:0]);
    assign factor_factor_right = select_chunk_word(
        scratch_role1_data, kernel_index_q[2:0]);
    assign factor_clamped_value = fp16_less_than(
        factor_scalar, factor_floor) ? factor_floor : factor_scalar;
    assign solve_mean = select_chunk_word(
        scratch_role0_data, kernel_row_q[2:0]);
    assign solve_factor = select_chunk_word(
        weight_slots[0][127:0], kernel_response_count_q[2:0]);
    assign solve_product_tile0 = {
        scratch_odd_read0_data, scratch_even_read0_data};
    assign solve_product_tile1 = {
        scratch_odd_read1_data, scratch_even_read1_data};
    assign solve_product_store = kernel_backsub_active &&
        (kernel_backsub_step_q == BACKSUB_PRODUCT_STREAM) &&
        kernel_product_f2_event_q;
    // Solve scratch is asynchronous only inside its bank owner.  Pre-result
    // tags capture the rows into the two existing APX residents one cycle
    // before the dependent command consumes them.
    assign solve_terminal_product_prefetch = kernel_backsub_active &&
        (kernel_backsub_step_q == BACKSUB_PRODUCT_STREAM) &&
        apx_product_pre_valid &&
        (apx_product_pre_tag[15:8] == 8'hF2) &&
        (kernel_row_q >= 4'd2) &&
        (({2'd0, apx_product_pre_tag[3:0]} + 6'd1) >=
         {2'd0, kernel_row_q});
    assign solve_f301_prefetch = kernel_backsub_active &&
        (kernel_backsub_step_q == BACKSUB_REDUCE_01_WAIT) &&
        apx_pair_pre_valid && (apx_pair_pre_tag == 16'hF301);
    assign solve_f303_prefetch = kernel_backsub_active &&
        (kernel_backsub_step_q == BACKSUB_REDUCE_FINAL_WAIT) &&
        apx_pair_pre_valid && (apx_pair_pre_tag == 16'hF303);
    assign solve_f304_prefetch = kernel_backsub_active &&
        (kernel_backsub_step_q == BACKSUB_REDUCE_LAST_WAIT) &&
        apx_pair_pre_valid && (apx_pair_pre_tag == 16'hF304);
    assign iir_run_active = kernel_recurrence_active &&
        (iir_phase_q == REC_RUN_0);
    assign iir_phase_index = iir_run_step_q;
    assign iir_coeff_phase = (iir_phase_index <= 4'd2) ||
        ((iir_phase_index >= 4'd10) && (iir_phase_index <= 4'd12));
    assign iir_negative_phase =
        ((iir_phase_index >= 4'd3) && (iir_phase_index <= 4'd5)) ||
        (iir_phase_index >= 4'd13);
    assign iir_main_is_negative = iir_run_active && iir_negative_phase;
    assign iir_main_request_valid =
        (iir_run_active && !iir_drain_q && !iir_block_wait_q &&
         (iir_restart_gap_q == 2'd0) &&
         (iir_main_channel < bound0_q[2:0]) &&
         (iir_coeff_phase ||
          (iir_negative_phase &&
           (|iir_samples_remaining_q[11:1])))) ||
        (kernel_recurrence_active &&
         ((iir_phase_q == REC_REAL) ||
          (iir_phase_q == REC_IMAG)) &&
         (iir_terminal_request_count_q <
          {1'b0, bound0_q[2:0]}));
    assign iir_main_request_tag =
        (iir_phase_q == REC_REAL) ?
            {REC_TAG_COSINE, 9'd0,
             iir_terminal_request_count_q[2:0]} :
        ((iir_phase_q == REC_IMAG) ?
            {REC_TAG_SINE, 9'd0,
             iir_terminal_request_count_q[2:0]} :
        (iir_main_is_negative ?
            {REC_TAG_NEGATE, 9'd0, iir_main_channel} :
            {REC_TAG_COEFF, 9'd0, iir_main_channel}));
    // Tags, rather than a duplicated latency counter, select the recurrence
    // add channel.  The registered APX command packet may shift absolute
    // latency, but tagged products still enter the same single add stream.
    assign iir_add_is_add1 = iir_run_active && !iir_block_wait_q &&
        iir_product_coeff_event &&
        (iir_product_event_channel < bound0_q[2:0]);
    assign iir_add_is_add2 = iir_run_active && !iir_block_wait_q &&
        iir_pair_add1_event &&
        (iir_pair_event_channel < bound0_q[2:0]) &&
        ((iir_pair_event_channel < 3'd3) ?
         !iir_drain_q : iir_late_valid_q);
    assign iir_parallel_add_valid = iir_add_is_add1 ||
        iir_add_is_add2 ||
        ((iir_phase_q == REC_REAL) && iir_product_cosine_event);
    assign iir_parallel_add_tag =
        (iir_phase_q == REC_REAL) ?
            {REC_TAG_REAL, 9'd0, iir_product_event_channel} :
        (iir_add_is_add1 ?
            {REC_TAG_ADD1, 9'd0, iir_add_channel} :
            {REC_TAG_CURRENT, 9'd0, iir_add_channel});
    assign iir_prefetch_coeff = iir_run_active &&
        apx_product_pre_valid &&
        (apx_product_pre_tag[15:12] == REC_TAG_COEFF) &&
        (apx_product_pre_tag[2:0] < bound0_q[2:0]);
    assign iir_prefetch_add2 = iir_run_active &&
        apx_pair_pre_valid &&
        (apx_pair_pre_tag[15:12] == REC_TAG_ADD1) &&
        (apx_pair_pre_tag[2:0] < bound0_q[2:0]);
    assign iir_prefetch_real = (iir_phase_q == REC_REAL) &&
        apx_product_pre_valid &&
        (apx_product_pre_tag[15:12] == REC_TAG_COSINE);
    assign iir_parallel_prefetch_valid = iir_prefetch_coeff ||
        iir_prefetch_add2 || iir_prefetch_real;
    assign iir_parallel_prefetch_channel = iir_prefetch_add2 ?
        apx_pair_pre_tag[2:0] : apx_product_pre_tag[2:0];
    assign iir_negative_return = iir_run_active &&
        iir_product_negative_event;
    assign iir_current_return = iir_run_active && iir_pair_current_event;
    assign iir_real_return = (iir_phase_q == REC_REAL) &&
        iir_pair_real_event;
    assign iir_imag_return = (iir_phase_q == REC_IMAG) &&
        iir_product_sine_event;
    assign iir_previous_capture = iir_run_active &&
        ((!iir_drain_q && !(|iir_samples_remaining_q[11:1]) &&
          (iir_phase_index >= 4'd7) && (iir_phase_index <= 4'd9)) ||
         (iir_drain_q && (iir_phase_index >= 4'd1) &&
          (iir_phase_index <= 4'd3)));
    // APX multiply now issues directly from its resident source boundary.
    // Separate the two three-channel issue groups by the history-capture
    // window.  This avoids simultaneous coefficient and add-result prefetches
    // after removal of the wide APX input queue, and leaves the current-state
    // return phases free at the single local-state write port.
    assign iir_capture_channel = iir_drain_q ?
        (iir_phase_index[2:0] + 3'd2) :
        (iir_phase_index[2:0] - 3'd7);
    assign iir_secondary_reads_raw = iir_previous_capture;
    assign iir_state_write_valid = iir_previous_capture ||
        iir_negative_return || iir_current_return ||
        iir_real_return || iir_imag_return;
    assign iir_state_write_neg = iir_previous_capture ||
        iir_negative_return || iir_imag_return;
    assign iir_state_write_channel = iir_previous_capture ?
        iir_capture_channel :
        ((iir_negative_return || iir_imag_return) ?
         iir_product_event_channel : iir_pair_event_channel);
    assign iir_state_write_data = iir_previous_capture ?
        iir_neg_state_bus :
        ((iir_negative_return || iir_imag_return) ?
         apx_product_bus[191:0] : apx_pair_bus[191:0]);

    always @(*) begin
        iir_main_channel = 3'd0;
        case (iir_phase_index)
            4'd0, 4'd3: iir_main_channel = 3'd0;
            4'd1, 4'd4: iir_main_channel = 3'd1;
            4'd2, 4'd5: iir_main_channel = 3'd2;
            4'd10, 4'd13: iir_main_channel = 3'd3;
            4'd11, 4'd14: iir_main_channel = 3'd4;
            4'd12, 4'd15: iir_main_channel = 3'd5;
            default: iir_main_channel = 3'd0;
        endcase
        iir_add_channel = 3'd0;
        case (iir_phase_index)
            4'd0: iir_add_channel = 3'd3;
            4'd1: iir_add_channel = 3'd4;
            4'd2: iir_add_channel = 3'd5;
            4'd4, 4'd7: iir_add_channel = 3'd0;
            4'd5, 4'd8: iir_add_channel = 3'd1;
            4'd6, 4'd9: iir_add_channel = 3'd2;
            4'd11: iir_add_channel = 3'd3;
            4'd12: iir_add_channel = 3'd4;
            4'd13: iir_add_channel = 3'd5;
            default: iir_add_channel = 3'd0;
        endcase
        if (iir_product_coeff_event)
            iir_add_channel = iir_product_event_channel;
        else if (iir_pair_add1_event)
            iir_add_channel = iir_pair_event_channel;
    end

    always @(*) begin
        iir_raw_read_channel = iir_main_channel;
        iir_neg_read_channel = iir_add_channel;
        if (iir_phase_q == REC_REAL) begin
            iir_raw_read_channel = iir_product_event_channel;
            iir_neg_read_channel =
                iir_terminal_request_count_q[2:0];
        end
        else if (iir_phase_q == REC_IMAG) begin
            iir_raw_read_channel = 3'd0;
            iir_neg_read_channel =
                iir_terminal_request_count_q[2:0];
        end
        else if (iir_phase_q == REC_RETIRE) begin
            iir_raw_read_channel = kernel_row_q[2:0];
            iir_neg_read_channel = kernel_row_q[2:0];
        end
        else if (iir_previous_capture) begin
            iir_neg_read_channel = iir_capture_channel;
        end
        if (iir_prefetch_coeff)
            iir_neg_read_channel = apx_product_pre_tag[2:0];
        if (iir_prefetch_real)
            iir_raw_read_channel = apx_product_pre_tag[2:0];
    end

    assign iir_raw_high = iir_state_tail[
        {iir_raw_read_channel, 1'b0}];
    assign iir_neg_high = iir_state_tail[
        {iir_neg_read_channel, !iir_secondary_reads_raw}];
    assign iir_raw_state_bus = iir_history_valid_q[iir_raw_read_channel] ?
        {iir_raw_high, scratch_role0_data} : 192'd0;
    assign iir_neg_state_bus = iir_history_valid_q[iir_neg_read_channel] ?
        {iir_neg_high, scratch_role1_data} : 192'd0;
    assign iir_source_scalar =
        (iir_parallel_prefetch_channel == 3'd0) ?
            result_chunk_q[15:0] :
        ((iir_parallel_prefetch_channel == 3'd1) ?
            result_chunk_q[31:16] :
        ((iir_parallel_prefetch_channel == 3'd2) ?
            result_chunk_q[47:32] :
        ((iir_parallel_prefetch_channel == 3'd3) ?
            source_buffer0_data_q[15:0] :
        ((iir_parallel_prefetch_channel == 3'd4) ?
            source_buffer0_data_q[31:16] :
         source_buffer0_data_q[47:32]))));
    assign iir_parallel_operand_a_pair =
        (iir_phase_q != REC_REAL) && !iir_add_is_add1;
    assign iir_parallel_prefetch_scalar =
        (iir_prefetch_coeff &&
         !iir_history_valid_q[iir_neg_read_channel]) ?
        16'h8000 : iir_source_scalar;
    assign iir_parallel_prefetch_operand_b = iir_prefetch_real ?
        iir_raw_state_bus :
        ((iir_prefetch_coeff &&
          iir_history_valid_q[iir_neg_read_channel]) ?
         iir_neg_state_bus : {12{iir_parallel_prefetch_scalar}});

    assign iir_retire_word_count =
        (({7'd0, kernel_chunk_q[1:0], 2'd0} + 11'd4) <=
         {6'd0, lanes_q}) ? 4'd8 :
        ({1'b0, lanes_q} -
         {4'd0, kernel_chunk_q[1:0], 2'd0}) << 1;
    assign iir_retire_last_chunk =
        ({7'd0, kernel_chunk_q[1:0], 2'd0} + 11'd4) >=
        {6'd0, lanes_q};
    assign iir_retire_last_channel =
        (kernel_row_q[2:0] + 3'd1) >= bound0_q[2:0];

    always @(*) begin
        case (kernel_chunk_q[1:0])
            2'd0: iir_retire_data = {
                iir_neg_state_bus[63:48], iir_raw_state_bus[63:48],
                iir_neg_state_bus[47:32], iir_raw_state_bus[47:32],
                iir_neg_state_bus[31:16], iir_raw_state_bus[31:16],
                iir_neg_state_bus[15:0], iir_raw_state_bus[15:0]
            };
            2'd1: iir_retire_data = {
                iir_neg_state_bus[127:112], iir_raw_state_bus[127:112],
                iir_neg_state_bus[111:96], iir_raw_state_bus[111:96],
                iir_neg_state_bus[95:80], iir_raw_state_bus[95:80],
                iir_neg_state_bus[79:64], iir_raw_state_bus[79:64]
            };
            default: iir_retire_data = {
                iir_neg_state_bus[191:176], iir_raw_state_bus[191:176],
                iir_neg_state_bus[175:160], iir_raw_state_bus[175:160],
                iir_neg_state_bus[159:144], iir_raw_state_bus[159:144],
                iir_neg_state_bus[143:128], iir_raw_state_bus[143:128]
            };
        endcase
    end

    always @(*) begin
        kernel_refine_operand_a = 64'd0;
        kernel_refine_operand_b = 64'd0;
        case (kernel_refine_step_q)
            3'd0: begin
                kernel_refine_operand_a[15:0] =
                    (factor_refine_left[14:10] == 5'd31) ?
                    factor_refine_left : (factor_refine_left & 16'hFFE0);
                kernel_refine_operand_b[15:0] =
                    (factor_refine_right[14:10] == 5'd31) ?
                    factor_refine_right : (factor_refine_right & 16'hFFE0);
                kernel_refine_operand_a[31:16] =
                    kernel_refine_operand_a[15:0];
                kernel_refine_operand_b[31:16] =
                    refinement_low_word(factor_refine_right);
                kernel_refine_operand_a[47:32] =
                    refinement_low_word(factor_refine_left);
                kernel_refine_operand_b[47:32] =
                    kernel_refine_operand_b[15:0];
                kernel_refine_operand_a[63:48] =
                    kernel_refine_operand_a[47:32];
                kernel_refine_operand_b[63:48] =
                    kernel_refine_operand_b[31:16];
            end
            3'd1: begin
                kernel_refine_operand_a[15:0] = apx_product_bus[31:16];
                kernel_refine_operand_b[15:0] = apx_product_bus[47:32];
            end
            3'd2: begin
                kernel_refine_operand_a[15:0] = source_buffer0_data_q[15:0];
                kernel_refine_operand_b[15:0] = apx_pair_bus[15:0];
            end
            default: begin
                kernel_refine_operand_a[15:0] = apx_pair_bus[15:0];
                kernel_refine_operand_b[15:0] = source_buffer0_data_q[63:48];
            end
        endcase
    end

    assign kernel_refine_request_valid = kernel_triangular_active &&
        kernel_refine_busy_q &&
        ((kernel_refine_step_q == 3'd0) ||
         ((kernel_refine_step_q == 3'd1) &&
          kernel_product_d100_event_q) ||
         ((kernel_refine_step_q == 3'd2) &&
          kernel_pair_d101_event) ||
         ((kernel_refine_step_q == 3'd3) &&
          kernel_pair_d102_event));
    assign kernel_refine_request_operation =
        (kernel_refine_step_q == 3'd0) ?
        APX_MULTIPLY_VECTOR : APX_ADD_VECTOR;
    assign kernel_refine_request_lanes =
        (kernel_refine_step_q == 3'd0) ? 5'd4 : 5'd1;
    assign kernel_refine_request_tag =
        (kernel_refine_step_q == 3'd0) ? 16'hD100 :
        (kernel_refine_step_q == 3'd1) ? 16'hD101 :
        (kernel_refine_step_q == 3'd2) ? 16'hD102 : 16'hD103;
    // Refinement result events transfer their resolved operands into the
    // registered APX ownership slot on this handshake.
    assign kernel_refine_request_fire = kernel_triangular_active &&
        kernel_refine_busy_q && kernel_apx_request_fire &&
        (kernel_apx_request_tag == kernel_refine_request_tag);
    assign factor_dot_reduce_request = kernel_triangular_active &&
        (kernel_tri_step_q == TRI_DOT_REDUCE_ISSUE);
    assign factor_scalar_add_request = kernel_triangular_active &&
        ((kernel_tri_step_q == TRI_SUB_ISSUE) ||
         (kernel_tri_step_q == TRI_RSQ_CORR_ISSUE));
    assign kernel_mean_reduce_return = kernel_stat_active &&
        kernel_mean_reduce_event;
    assign kernel_pair_reduce_return = kernel_stat_active &&
        kernel_pair_reduce_event;
    assign kernel_mean_accum_return = kernel_stat_active &&
        kernel_mean_accum_event;
    assign kernel_pair_accum_return = kernel_stat_active &&
        kernel_pair_accum_event;
    assign kernel_reduce_scratch_index = kernel_mean_reduce_return ?
        (6'd24 + {2'd0, kernel_reduce_event_index[3:0]}) :
        kernel_reduce_event_index;
    assign kernel_reduce_scratch_word = select_chunk_word(
        scratch_role0_data, kernel_reduce_scratch_index[2:0]);
    assign kernel_accum_add_event = (kernel_chunk_q != 5'd0) &&
        (kernel_mean_reduce_return || kernel_pair_reduce_return);
    assign kernel_accum_add_valid = kernel_stat_active &&
        kernel_accum_add_event;
    assign kernel_scalar_add_valid = kernel_stat_active &&
        ((kernel_stat_step_q == STAT_POST_ADD_ISSUE) ||
         (kernel_stat_step_q == STAT_TRACE_EPS_ISSUE) ||
         (kernel_stat_step_q == STAT_DIAG_ADD_ISSUE));
    assign kernel_scalar_add_fire = kernel_scalar_add_valid &&
        !kernel_scalar_command_valid_q;
    assign kernel_scalar_add_operand_x =
        (kernel_stat_step_q == STAT_DIAG_ADD_ISSUE) ?
        gram_local_data_q[15:0] : source_buffer0_data_q[15:0];
    assign kernel_scalar_add_operand_y = active_weight_tile[15:0];
    assign kernel_scalar_add_tag =
        (kernel_stat_step_q == STAT_POST_ADD_ISSUE) ? 16'hE001 :
        ((kernel_stat_step_q == STAT_TRACE_EPS_ISSUE) ? 16'hE005 :
         (16'hE100 | {12'd0, kernel_row_q}));
    assign kernel_scalar_command_accept =
        kernel_scalar_command_valid_q && !kernel_accum_add_valid &&
        apx_post_add_ready;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            kernel_scalar_command_valid_q <= 1'b0;
            kernel_scalar_command_x_q <= 16'd0;
            kernel_scalar_command_y_q <= 16'd0;
            kernel_scalar_command_tag_q <= 16'd0;
        end
        else if (!kernel_stat_active) begin
            kernel_scalar_command_valid_q <= 1'b0;
        end
        else begin
            if (kernel_scalar_command_accept)
                kernel_scalar_command_valid_q <= 1'b0;
            if (kernel_scalar_add_fire) begin
                kernel_scalar_command_valid_q <= 1'b1;
                kernel_scalar_command_x_q <= kernel_scalar_add_operand_x;
                kernel_scalar_command_y_q <= kernel_scalar_add_operand_y;
                kernel_scalar_command_tag_q <= kernel_scalar_add_tag;
            end
        end
    end
    assign kernel_stream_completion =
        ((kernel_chunk_q == 5'd0) &&
         (kernel_mean_reduce_return || kernel_pair_reduce_return)) ||
        ((kernel_chunk_q != 5'd0) &&
         (kernel_mean_accum_return || kernel_pair_accum_return));
    assign group_diagonal = flags_q[4];
    assign descriptor_program_accept = (state_q == STATE_IDLE) &&
        descriptor_valid && descriptor_ready &&
        (descriptor_base[63:60] != OPCODE_CONFIG);
    assign sequence_context_advance =
        ((state_q == STATE_WINDOW_RUN) && window_sequence_complete &&
         !(bias_final_plane && !scalar_post_enabled) &&
         sequence_has_next) ||
        ((state_q == STATE_BIAS_RUN) && bias_epilogue_complete &&
         sequence_has_next);
    assign sequence_advances_outer = last_sequence_plane_q;
    assign sequence_has_next = !last_sequence_plane_q ||
        ((sequence_i0_q + 12'd1) < bound0_q);
    assign next_sequence_i0 = sequence_advances_outer ?
        (sequence_i0_q + 12'd1) : sequence_i0_q;
    assign next_sequence_i2 = sequence_advances_outer ?
        bound2_q : (sequence_i2_q - 12'd1);
    assign next_sequence_advances_outer = sequence_advances_outer ?
        !accumulation_enabled_q : next_last_sequence_plane_q;
    assign next_sequence_has_next = !next_sequence_advances_outer ||
        ((next_sequence_i0 + 12'd1) < bound0_q);
    // A zero outer weight stride is an explicit descriptor promise that the
    // next output channel consumes the same resident kernel and bias.  Limit
    // the reuse path to single-plane work so accumulation ordering remains on
    // the existing path.
    assign sequence_reuses_parameters = !accumulation_enabled &&
        sequence_advances_outer && (weight_stride0_q == 13'd0);
    assign next_sequence_reuses_parameters = !accumulation_enabled &&
        next_sequence_advances_outer && (weight_stride0_q == 13'd0);
    assign window_chain_reuses_parameters =
        sequence_reuses_parameters &&
        (!bias_enabled || bias_prefetch_ready_q);
    assign next_group_plane_index = sequence_advances_outer ?
        12'd0 : (group_plane_index_q + 12'd1);
    assign next_group_active_plane =
        next_group_plane_index == next_sequence_i0;
    assign next_source_i0_base =
        source_i0_base_q + source_stride0_q;
    assign next_weight_i0_base =
        weight_i0_base_q + weight_stride0_q;
    assign next_source_address = sequence_advances_outer ?
        next_source_i0_base : (source_address_q + source_stride2_q);
    assign next_weight_address = sequence_advances_outer ?
        next_weight_i0_base : (weight_address_q + weight_stride2_q);
    assign next_destination_address = sequence_advances_outer ?
        (destination_address_q + destination_stride0_q) :
        destination_address_q;
    assign active_weight_tile = weight_slots[active_weight_slot_q];
    assign group_plane_index = group_plane_index_q;
    assign group_active_plane = group_plane_index == sequence_i0_q;
    assign same_pad = flags_q[1];
    assign next_final_accumulation_plane = accumulation_enabled_q &&
        next_sequence_advances_outer;
    // One look-ahead window context is legal only while the current sequence
    // has at least the APX drain depth and no retiring scalar post-operation.
    // Weight readiness is an ordinary cache-slot dependency; no profile name
    // or run-time legality tree is introduced.
    assign window_chain_start_valid =
        (state_q == STATE_WINDOW_RUN) && same_pad && !pool_mode &&
        sequence_has_next && (bound1_q >= 12'd16) &&
        !window_chain_pending_q && !window_done &&
        ((!bias_enabled &&
          (!scalar_post_enabled || !scalar_post_retire)) ||
         window_chain_reuses_parameters) &&
        (window_chain_reuses_parameters ||
         (group_diagonal && !sequence_advances_outer) ||
         prefetch_ready_q);
    assign window_start_valid =
        ((state_q == STATE_WINDOW_START) && same_pad) ||
        window_chain_start_valid;
    assign window_chain_start_fire = window_chain_start_valid &&
        window_start_ready;
    assign window_start_source_base =
        (window_chain_start_valid ? next_source_address : source_address_q) +
        ((source_space_q == SPACE_FRAME) ? frame_base_q : 13'd0);
    assign window_start_weight_select = window_chain_start_valid ?
        ((window_chain_reuses_parameters ||
          (group_diagonal && !sequence_advances_outer)) ?
         active_weight_slot_q : ~active_weight_slot_q) :
        active_weight_slot_q;
    assign window_start_weight_zero = window_chain_start_valid ?
        (group_diagonal && !next_group_active_plane) :
        (group_diagonal && !group_active_plane);
    assign copy_mode = !pool_mode_q && prefetch_sequence_q &&
        ((state_q == STATE_FIRST_WEIGHT_REQ) ||
         (state_q == STATE_FIRST_WEIGHT_WAIT));
    assign pool_mode = pool_mode_q;
    assign copy_merge_next = copy_mode && copy_merge_current_q;
    assign copy_request_lanes = copy_merge_next ? 5'd16 : lanes_q;
    assign copy_response_fire = copy_mode &&
        (state_q == STATE_FIRST_WEIGHT_WAIT) &&
        service_response_accept;
    assign copy_response_complete = copy_response_fire &&
        service_response_last;
    assign copy_advance_count = copy_merge_next ? 2'd2 : 2'd1;
    assign copy_next_advance_count = copy_next_merge_q ? 2'd2 : 2'd1;
    assign copy_has_after_response = copy_has_after_q;
    assign copy_next_merge = copy_next_merge_q;

    // Advance plane classification only at the architectural sequence commit.
    // Hot window/scratch control consumes these registered flags, while the
    // loop counter remains available for address/accounting state only.
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            accumulation_enabled_q <= 1'b0;
            first_sequence_plane_q <= 1'b0;
            last_sequence_plane_q <= 1'b0;
            next_last_sequence_plane_q <= 1'b0;
            group_plane_index_q <= 12'd0;
        end
        else if (descriptor_program_accept) begin
            accumulation_enabled_q <= descriptor_base[23:12] > 12'd1;
            first_sequence_plane_q <= 1'b1;
            last_sequence_plane_q <= descriptor_base[23:12] == 12'd1;
            next_last_sequence_plane_q <=
                descriptor_base[23:12] == 12'd2;
            group_plane_index_q <= 12'd0;
        end
        else if (sequence_context_advance) begin
            if (sequence_advances_outer) begin
                first_sequence_plane_q <= 1'b1;
                last_sequence_plane_q <= !accumulation_enabled_q;
                next_last_sequence_plane_q <= bound2_q == 12'd2;
                group_plane_index_q <= 12'd0;
            end
            else begin
                first_sequence_plane_q <= 1'b0;
                last_sequence_plane_q <= next_last_sequence_plane_q;
                next_last_sequence_plane_q <= sequence_i2_q == 12'd3;
                group_plane_index_q <= group_plane_index_q + 12'd1;
            end
        end
    end

    // COPY successor issue remains response-chained, but its comparison work
    // is performed into this small context state one command in advance.
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            copy_remaining_q <= 12'd0;
            copy_merge_eligible_q <= 1'b0;
            copy_merge_current_q <= 1'b0;
            copy_has_after_q <= 1'b0;
            copy_next_merge_q <= 1'b0;
        end
        else if (descriptor_program_accept) begin
            copy_remaining_q <= descriptor_base[47:36];
            copy_merge_eligible_q <=
                (descriptor_base[57:54] == MODE_COPY) &&
                (descriptor_base[4:0] == 5'd8) &&
                (descriptor_ext0[48:36] == 13'd8) &&
                (descriptor_ext2[48:36] == 13'd8) &&
                (descriptor_ext0[9:1] == 9'd1);
            copy_merge_current_q <=
                (descriptor_base[57:54] == MODE_COPY) &&
                (descriptor_base[4:0] == 5'd8) &&
                (descriptor_base[47:36] >= 12'd2) &&
                (descriptor_ext0[48:36] == 13'd8) &&
                (descriptor_ext2[48:36] == 13'd8) &&
                (descriptor_ext0[9:1] == 9'd1);
            copy_has_after_q <=
                descriptor_base[47:36] >
                (((descriptor_base[57:54] == MODE_COPY) &&
                  (descriptor_base[4:0] == 5'd8) &&
                  (descriptor_base[47:36] >= 12'd2) &&
                  (descriptor_ext0[48:36] == 13'd8) &&
                  (descriptor_ext2[48:36] == 13'd8) &&
                  (descriptor_ext0[9:1] == 9'd1)) ? 12'd2 : 12'd1);
            copy_next_merge_q <=
                (descriptor_base[57:54] == MODE_COPY) &&
                (descriptor_base[4:0] == 5'd8) &&
                (descriptor_base[47:36] >= 12'd4) &&
                (descriptor_ext0[48:36] == 13'd8) &&
                (descriptor_ext2[48:36] == 13'd8) &&
                (descriptor_ext0[9:1] == 9'd1);
        end
        else if (copy_response_complete) begin
            copy_remaining_q <= copy_remaining_q -
                {10'd0, copy_advance_count};
            copy_merge_current_q <= copy_next_merge_q;
            copy_has_after_q <= copy_remaining_q >
                ({10'd0, copy_advance_count} +
                 {10'd0, copy_next_advance_count});
            copy_next_merge_q <= copy_merge_eligible_q &&
                (copy_remaining_q >=
                 ({10'd0, copy_advance_count} +
                  {10'd0, copy_next_advance_count} + 12'd2));
        end
    end
    assign copy_beat_lanes = service_response_half ?
        (copy_request_lanes - 5'd8) :
        ((copy_request_lanes > 5'd8) ? 5'd8 : copy_request_lanes);
    assign copy_next_source_address =
        source_address_q + (copy_merge_next ?
        (source_stride0_q << 1) : source_stride0_q);
    assign copy_next_destination_address =
        destination_address_q + (copy_merge_next ?
        (destination_stride0_q << 1) : destination_stride0_q);
    assign emit_remaining_words = bound2_q - emit_word_index_q;
    assign emit_chunk_lanes = (emit_remaining_words >= 12'd8) ?
        5'd8 : {1'b0, emit_remaining_words[3:0]};
    assign emit_finishes_group =
        (emit_word_index_q + {7'd0, emit_chunk_lanes}) >= bound2_q;
    assign emit_final_chunk = emit_finishes_group &&
        ((sequence_i0_q + 12'd1) >= bound1_q);
    assign emit_has_next = !emit_final_chunk;
    assign emit_next_source_address = emit_finishes_group ?
        (source_i0_base_q + source_stride0_q) :
        (source_address_q + (source_stride1_q << 5'd3));
    assign emit_next_remaining_words = bound2_q - emit_word_index_q -
        {7'd0, emit_chunk_lanes};
    assign emit_next_chunk_lanes = emit_finishes_group ?
        ((bound2_q >= 12'd8) ? 5'd8 : {1'b0, bound2_q[3:0]}) :
        ((emit_next_remaining_words >= 12'd8) ?
         5'd8 : {1'b0, emit_next_remaining_words[3:0]});
    assign emit_response_fire = emit_mode_q &&
        (state_q == STATE_FIRST_WEIGHT_WAIT) &&
        service_tile_response_valid && retire_ready;
    assign emit_packet_done = emit_mode_q &&
        (state_q == STATE_WINDOW_RUN) && retire_result_done;
    assign pair_next_remaining_samples =
        bound1_q - pair_block_base_q - 12'd16;
    assign pair_next_block_samples =
        (pair_next_remaining_samples >= 12'd16) ?
        5'd16 : {1'b0, pair_next_remaining_samples[3:0]};
    assign pair_chunks_per_output =
        (pair_block_samples_q > 5'd8) ? 2'd2 : 2'd1;
    assign pair_total_chunks = {pair_chunks_per_output, 1'b0};
    assign pair_total_results = {pair_block_samples_q, 1'b0};
    assign pair_request_tag =
        {pair_chunks_per_output[1], gather_issue_count_q[3:0],
         pair_issue_phase_q};
    assign pair_result_two_chunks = apx_reduce_tag[5];
    assign pair_result_sample = apx_reduce_tag[4:1];
    assign pair_result_scratch_index =
        apx_reduce_tag[0] ?
        ({3'd0, pair_result_two_chunks} + 4'd1 +
         {3'd0, pair_result_sample[3]}) :
        {3'd0, pair_result_sample[3]};
    assign pair_bias_output1 =
        {2'd0, chunk_index_q} >=
        {4'd0, pair_chunks_per_output};
    assign pair_bias_chunk_in_output = pair_bias_output1 ?
        (chunk_index_q[1:0] - pair_chunks_per_output) :
        chunk_index_q[1:0];
    assign pair_bias_chunk_lanes =
        (pair_bias_chunk_in_output == 2'd0) ?
        ((pair_block_samples_q >= 5'd8) ? 4'd8 :
         pair_block_samples_q[3:0]) :
        (pair_block_samples_q[3:0] - 4'd8);
    assign pair_bias_destination =
        pair_block_destination_q +
        (pair_bias_output1 ? destination_stride0_q : 13'd0) +
        (pair_bias_chunk_in_output[0] ?
         (destination_stride1_q << 5'd3) : 13'd0);
    assign pair_bias_scratch_row = scratch_role0_data;
    assign pair_selected_bias = pair_bias_output1 ?
        pair_bias1_q : pair_bias0_q;
    assign pair_apx_request_valid = pair_mode_q &&
        (state_q == STATE_PAIR_RUN) &&
        source_buffer0_valid_q;
    assign pair_apx_request_fire = shared_apx_capture_fire &&
        (shared_apx_capture_owner == SHARED_APX_OWNER_PAIR);
    assign pair_source_fire = pair_apx_request_fire &&
        pair_issue_phase_q;
    assign pair_source_chain_request = source_response_accept &&
        (state_q == STATE_PAIR_RUN) &&
        (gather_request_count_q < {7'd0, pair_block_samples_q});
    assign pair_bias_request_valid = pair_mode_q && flags_q[2] &&
        (state_q == STATE_PAIR_BIAS) &&
        !pair_bias_pending_q && !pair_retire_pending_q && retire_ready &&
        ({2'd0, chunk_index_q} < {4'd0, pair_total_chunks});
    assign pair_bias_request_fire = shared_apx_capture_fire &&
        (shared_apx_capture_owner == SHARED_APX_OWNER_PAIR_BIAS);
    assign pair_add_return = (state_q == STATE_PAIR_BIAS) &&
        pair_bias_pending_q && apx_pair_valid;
    assign tile_apx_request_valid = tile_state_active &&
        ((tile_phase_q == TILE_REAL_ISSUE) ||
         (tile_phase_q == TILE_IMAG_ISSUE));
    assign tile_apx_request_fire = shared_apx_capture_fire &&
        (shared_apx_capture_owner == SHARED_APX_OWNER_TILE);
    assign tile_apx_request_tag =
        ((tile_phase_q == TILE_IMAG_ISSUE) ? 16'hE810 : 16'hE800) |
        {12'd0, kernel_column_q};
    assign tile_reduce_return = tile_state_active &&
        apx_reduce_valid && (apx_reduce_tag[15:8] == 8'hE8);
    assign tile_scratch_row = apx_reduce_tag[4] ? 4'd11 : 4'd10;
    assign tile_retire_phase = tile_state_active &&
        ((tile_phase_q == TILE_RETIRE_REAL) ||
         (tile_phase_q == TILE_RETIRE_IMAG));
    assign generic_mode = ewise_mode_q || vector_add_mode_q;
    assign generic_apx_request_valid =
        (state_q == STATE_GENERIC_SOURCE) &&
        source_buffer0_valid_q && retire_ready;
    assign generic_apx_request_fire = shared_apx_capture_fire &&
        (shared_apx_capture_owner == SHARED_APX_OWNER_GENERIC);
    assign generic_source_accept =
        (state_q == STATE_GENERIC_SOURCE) &&
        (operand_response_role_q == OPERAND_ROLE_SOURCE) &&
        service_tile_response_accept;
    assign generic_source_consumed = generic_apx_request_fire;
    assign pool_scale_enabled = pool_mode && flags_q[0];
    assign pool_scalar_bypass = pool_mode && (lanes_q == 5'd1);
    assign pool_scalar_result_valid =
        (state_q == STATE_WINDOW_RUN) && pool_scalar_bypass &&
        scalar_buffer0_valid_q &&
        !window_issue_block_q && !apx_add_request_valid;
    assign pool_chunk_overlap = pool_scalar_bypass &&
        accumulation_enabled;
    assign pool_chunk_build_data = pool_chunk_select_q ?
        weight_slots[1][127:0] : result_chunk_q;
    assign pool_chunk_full_data = pool_chunk_full_select_q ?
        weight_slots[1][127:0] : result_chunk_q;
    assign compute_result_valid = pool_scalar_bypass ?
        pool_scalar_result_valid : (same_pad ?
        window_result_valid :
        apx_reduce_valid);
    assign compute_result_tag = pool_scalar_bypass ?
        {4'd0, gather_result_count_q} : (same_pad ?
        window_result_tag : apx_reduce_tag);
    assign compute_result_data = pool_scalar_bypass ?
        scalar_buffer0_data_q : (same_pad ?
        window_result_data : apx_reduce_result);
    assign compute_done = same_pad ?
        window_done :
        (compute_result_valid &&
         ((gather_result_count_q + 12'd1) >= bound1_q));
    assign retired_window_result =
        (flags_q[3] && compute_result_data[15]) ?
        16'd0 : compute_result_data;
    assign accumulation_enabled = accumulation_enabled_q;
    assign accumulation_plane = accumulation_enabled_q &&
        !first_sequence_plane_q;
    assign final_accumulation_plane = accumulation_enabled_q &&
        last_sequence_plane_q;
    assign final_sequence_plane = group_diagonal ||
        last_sequence_plane_q;
    assign first_sequence_plane = first_sequence_plane_q;
    assign bias_enabled = flags_q[2];
    assign bias_final_plane = bias_enabled && final_sequence_plane;
    assign scalar_post_enabled = (state_q == STATE_WINDOW_RUN) &&
        !pool_mode &&
        ((accumulation_plane && !bias_final_plane) ||
         (bias_final_plane && !accumulation_enabled));
    assign window_scalar_post_request_valid = compute_result_valid &&
        scalar_post_enabled &&
        (!bias_final_plane || bias_prefetch_ready_q);
    assign scalar_post_request_valid = window_scalar_post_request_valid;
    assign scalar_post_retire = scalar_post_enabled &&
        (!accumulation_plane || final_accumulation_plane);
    assign scalar_post_last_return = apx_post_add_result_valid &&
        (apx_post_add_result_tag[11:0] == (bound1_q - 12'd1));
    assign scalar_post_scratch_row = scratch_role0_data;
    assign aligned_accumulation_retire =
        (destination_stride1_q == 13'd1) &&
        (destination_address_q[2:0] == 3'd0);
    assign bias_add_request_valid = bias_chunk_ready_q &&
        !accumulation_add_pending_q;
    assign apx_add_request_valid =
        (chunk_full_q && !accumulation_add_pending_q) ||
        bias_add_request_valid;
    assign apx_add_request_fire = shared_apx_capture_fire &&
        (shared_apx_capture_owner == SHARED_APX_OWNER_ADD);
    assign pool_scale_request_valid = pool_scale_enabled &&
        !pool_scale_pending_q &&
        ((compute_result_valid && single_plane_q) ||
         (accumulation_pair_return && final_accumulation_plane));
    assign pool_scale_request_fire = shared_apx_capture_fire &&
        (shared_apx_capture_owner == SHARED_APX_OWNER_POOL);
    assign pool_scale_product_valid = pool_scale_enabled &&
        pool_scale_pending_q && apx_product_valid;
    assign pool_scale_direct_retire = pool_scale_product_valid &&
        (!accumulation_enabled || aligned_accumulation_retire);
    assign pool_scale_result_accepted = pool_scale_product_valid &&
        ((!accumulation_enabled || aligned_accumulation_retire) ?
         retire_ready : 1'b1);
    assign gather_apx_request_valid =
        (state_q == STATE_WINDOW_RUN) && !same_pad &&
        !pool_scalar_bypass &&
        source_buffer0_valid_q &&
        (!scalar_post_enabled || !bias_final_plane ||
         bias_prefetch_ready_q) &&
        !window_issue_block_q &&
        !apx_add_request_valid;
    assign gather_apx_request_fire = shared_apx_capture_fire &&
        (shared_apx_capture_owner == SHARED_APX_OWNER_GATHER);
    // The APX-local ingress register captures the transient window sample and
    // shift metadata on this handshake.  The window can therefore advance
    // without retaining a second engine-side command slot.
    assign window_apx_issue_eligible = same_pad &&
        (!scalar_post_enabled || !bias_final_plane ||
         bias_prefetch_ready_q) &&
        !window_issue_block_q && !apx_add_request_valid;
    assign window_apx_request_ready = window_apx_issue_eligible &&
        shared_apx_issue_ready &&
        (shared_apx_live_owner == SHARED_APX_OWNER_WINDOW);
    assign window_issue_fire = window_apx_request_valid &&
        window_apx_request_ready;
    assign gather_source_fire = pool_scalar_result_valid ||
        gather_apx_request_fire;
    assign gather_source_chain_request = source_response_accept &&
        (state_q == STATE_WINDOW_RUN) &&
        !pool_scalar_bypass &&
        (gather_request_count_q < bound1_q);
    assign source_response_accept =
        (operand_response_role_q == OPERAND_ROLE_SOURCE) &&
        service_response_accept &&
        (pool_scalar_bypass || service_response_last);
    assign source_response_beat_accept =
        (operand_response_role_q == OPERAND_ROLE_SOURCE) &&
        service_response_accept && !pool_scalar_bypass;
    // EMIT responses retire directly and do not belong to the compute source
    // buffer.  Keeping the ownership boundary here prevents a retire packet
    // from being re-issued as a gather request while it drains.
    assign vector_source_accept = source_response_accept &&
        !pool_scalar_bypass && !emit_mode_q;
    assign scalar_source_accept = source_response_accept &&
        pool_scalar_bypass;
    assign source_buffer_pop = pair_mode_q ?
        pair_source_fire : (!pool_scalar_bypass && gather_source_fire);
    assign scalar_buffer_pop = pool_scalar_bypass &&
        gather_source_fire;
    assign compute_issue_fire = pool_scalar_bypass ?
        pool_scalar_result_valid : (same_pad ?
        window_issue_fire : gather_apx_request_fire);
    assign accumulation_pair_return = apx_pair_valid &&
        accumulation_add_pending_q;
    assign retire_stream_available = retire_stream_active_q &&
        ({5'd0, retire_stream_word_index_q[11:3]} <
         {9'd0, produced_chunk_count_q});
    assign scratch_front_read_row = scalar_post_request_valid ?
        compute_result_tag[6:3] : chunk_index_q[3:0];
    assign scratch_rmw_read_row =
        (apx_post_add_result_valid &&
         !apx_post_add_result_tag[15]) ?
        apx_post_add_result_tag[6:3] : pair_result_scratch_index;
    assign scratch_retire_read_row = retire_stream_word_index_q[6:3];
    always @(*) begin
        kernel_scratch_role0_row = 4'd0;
        kernel_scratch_role1_row = 4'd0;
        // The final port selector below owns top-level state arbitration.
        // Decode only the descriptor-static kernel kind here; repeating the
        // top FSM decode inside every row branch made one state bit traverse
        // the complete asynchronous scratch read and Gram capture path.
        if (kernel_stat_kind) begin
            if (kernel_accum_add_event)
                kernel_scratch_role0_row =
                    kernel_reduce_scratch_index[5:3];
            else if ((kernel_stat_step_q == STAT_MEAN_SCALE_LOAD) ||
                     (kernel_stat_step_q == STAT_MEAN_RETIRE) ||
                     (kernel_stat_step_q == STAT_POST_MUL_LOAD))
                kernel_scratch_role0_row = 4'd3;
            else if ((kernel_stat_step_q == STAT_TRACE_LOAD) ||
                     (kernel_stat_step_q == STAT_DIAG_ADD_LOAD))
                kernel_scratch_role0_row = 4'd4;

            if (kernel_mean_accum_return || kernel_pair_accum_return)
                kernel_scratch_role1_row =
                    kernel_post_add_event_index[6:3];
            else if ((kernel_chunk_q == 5'd0) &&
                     (kernel_mean_reduce_return ||
                      kernel_pair_reduce_return))
                kernel_scratch_role1_row =
                    kernel_reduce_scratch_index[5:3];
            else if ((kernel_stat_step_q == STAT_POST_MUL_LOAD) ||
                     (kernel_stat_step_q == STAT_POST_ADD_WAIT))
                kernel_scratch_role1_row = kernel_index_q[5:3];
            else if ((kernel_stat_step_q == STAT_POST_RETIRE_LOW) ||
                     (kernel_stat_step_q == STAT_DIAG_ADD_WAIT))
                kernel_scratch_role1_row = 4'd4;
            else
                kernel_scratch_role1_row = kernel_scratch_role0_row;
        end
        else if (kernel_triangular_kind) begin
            if ((kernel_tri_step_q == TRI_RETIRE_LOAD) ||
                (kernel_tri_step_q == TRI_RETIRE))
                kernel_scratch_role0_row =
                    (kernel_result_count_q[3:0] < bound0_q[3:0]) ?
                    kernel_result_count_q[3:0] : bound0_q[3:0];
            else if ((kernel_tri_step_q == TRI_DOT_TERM_WAIT) ||
                     (kernel_tri_step_q == TRI_DOT_REDUCE_ISSUE) ||
                     (kernel_tri_step_q == TRI_DOT_REDUCE_WAIT))
                kernel_scratch_role0_row = bound0_q[3:0] + 4'd1;
            else if (kernel_tri_step_q == TRI_RSQ_EST_WAIT)
                kernel_scratch_role0_row = bound0_q[3:0];
            else
                kernel_scratch_role0_row = kernel_column_q;
            kernel_scratch_role1_row = kernel_row_q;
        end
        else if (kernel_backsub_kind) begin
            case (kernel_backsub_step_q)
                BACKSUB_REDUCE_01_ISSUE: begin
                    kernel_scratch_role0_row = 4'd0;
                    kernel_scratch_role1_row = 4'd2;
                end
                BACKSUB_PRODUCT_STREAM: begin
                    kernel_scratch_role0_row = 4'd0;
                    kernel_scratch_role1_row = 4'd2;
                end
                BACKSUB_REDUCE_23_ISSUE: begin
                    kernel_scratch_role0_row = 4'd4;
                    kernel_scratch_role1_row = 4'd6;
                end
                BACKSUB_REDUCE_01_WAIT: begin
                    kernel_scratch_role0_row = 4'd4;
                    kernel_scratch_role1_row = 4'd6;
                end
                BACKSUB_REDUCE_LAST_ISSUE: begin
                    kernel_scratch_role0_row =
                        (kernel_row_q == 4'd3) ? 4'd4 : 4'd8;
                        kernel_scratch_role1_row =
                        kernel_scratch_role0_row;
                end
                BACKSUB_REDUCE_FINAL_WAIT: begin
                    kernel_scratch_role0_row = 4'd8;
                    kernel_scratch_role1_row = 4'd8;
                end
                BACKSUB_SUB_ISSUE: begin
                    kernel_scratch_role0_row = 4'd0;
                    kernel_scratch_role1_row = 4'd2;
                end
                default: begin
                    // The descriptor's initial source-B tile holds all means.
                    kernel_scratch_role0_row = 4'd15;
                    kernel_scratch_role1_row = 4'd15;
                end
            endcase
        end
        else if (kernel_recurrence_kind) begin
            kernel_scratch_role0_row = {iir_raw_read_channel, 1'b0};
            kernel_scratch_role1_row = {
                iir_neg_read_channel,
                iir_secondary_reads_raw ? 1'b0 : 1'b1
            };
        end
    end

    assign scratch_role0_row = tile_retire_phase ?
        ((tile_phase_q == TILE_RETIRE_IMAG) ? 4'd11 : 4'd10) :
        (kernel_apx_owner ?
        kernel_scratch_role0_row :
        (apx_add_request_valid || pair_bias_request_valid ||
         scalar_post_request_valid) ?
        scratch_front_read_row :
        (retire_stream_available ? scratch_retire_read_row :
         chunk_index_q[3:0]));
    assign scratch_role1_row = tile_reduce_return ?
        tile_scratch_row : (kernel_apx_owner ?
        kernel_scratch_role1_row :
        ((apx_post_add_result_valid &&
          !apx_post_add_result_tag[15]) ||
         (pair_mode_q && (state_q == STATE_PAIR_RUN) &&
          apx_reduce_valid)) ?
        scratch_rmw_read_row :
        ((retire_stream_available &&
          (scratch_retire_read_row != scratch_role0_row)) ?
         scratch_retire_read_row : scratch_role0_row));
    assign scratch_role0_data = scratch_role0_row[0] ?
        scratch_odd_read0_data : scratch_even_read0_data;
    assign scratch_role1_data = scratch_role1_row[0] ?
        scratch_odd_read1_data : scratch_even_read1_data;
    assign scratch_compute_row = scratch_role0_data;
    assign retire_scratch_row =
        (scratch_retire_read_row == scratch_role0_row) ?
        scratch_role0_data : scratch_role1_data;
    assign window_sequence_complete =
        window_chain_pending_q ?
        ((window_chain_reuses_parameters && scalar_post_enabled) ?
         (window_done_pending_q && scalar_post_last_return) : window_done) :
        (scalar_post_enabled ?
        (window_done_pending_q && scalar_post_last_return) :
        ((compute_done && !accumulation_plane && !bias_final_plane &&
          !pool_scale_enabled) ||
         (window_done_pending_q && !window_issue_block_q &&
           !chunk_full_q && !accumulation_add_pending_q &&
           !retire_stream_active_q)));
    assign result_chunk_complete = compute_result_valid &&
        ((chunk_word_count_q == 4'd7) || compute_done);
    assign completed_chunk_lanes = (chunk_word_count_q == 4'd7) ?
        4'd8 : (chunk_word_count_q + 4'd1);
    assign bias_chunk_lanes =
        ((bound1_q - {4'd0, chunk_index_q, 3'd0}) >= 13'd8) ?
        4'd8 : (bound1_q - {4'd0, chunk_index_q, 3'd0});
    assign accumulation_return_lanes =
        bias_add_pending_q ?
        bias_chunk_lanes : chunk_lane_count_q;
    assign result_chunk_with_current = insert_chunk_word(
        pool_chunk_overlap ? pool_chunk_build_data : result_chunk_q,
        compute_result_data, chunk_word_count_q[2:0]);
    assign scratch_first_plane_write =
        (state_q == STATE_WINDOW_RUN) && result_chunk_complete &&
        (accumulation_enabled || bias_enabled) &&
        first_sequence_plane;
    assign scratch_accumulation_write =
        (state_q == STATE_WINDOW_RUN) && accumulation_pair_return &&
        (!final_accumulation_plane || bias_enabled ||
         !aligned_accumulation_retire);
    assign scratch_bias_write = (state_q == STATE_BIAS_RUN) &&
        accumulation_pair_return && !aligned_accumulation_retire;
    assign scratch_pool_scale_write =
        (state_q == STATE_WINDOW_RUN) && pool_scale_product_valid &&
        accumulation_enabled && !aligned_accumulation_retire;
    assign weight_slot_write = !copy_mode && service_response_accept &&
        ((state_q == STATE_FIRST_WEIGHT_WAIT) ||
         ((state_q == STATE_WINDOW_RUN) && prefetch_pending_q) ||
         (state_q == STATE_NEXT_WEIGHT_WAIT) ||
         ((state_q == STATE_PAIR_PREFETCH) &&
          (pair_prefetch_step_q == 2'd0)));
    assign weight_slot_write_address =
        (state_q == STATE_FIRST_WEIGHT_WAIT) ?
        1'b0 : ((state_q == STATE_PAIR_PREFETCH) ?
        1'b1 : ~active_weight_slot_q);
    assign bias_epilogue_complete = (state_q == STATE_BIAS_RUN) &&
        ({4'd0, chunk_index_q, 3'd0} >= bound1_q) &&
        !accumulation_add_pending_q && !retire_stream_active_q;

    always @(*) begin
        kernel_apx_request_valid = 1'b0;
        kernel_apx_request_operation = APX_MULTIPLY_VECTOR;
        kernel_apx_request_lanes = lanes_q;
        kernel_apx_request_tag = 16'hE000;
        kernel_apx_source_a = KERNEL_SOURCE_RESIDENT0;
        kernel_apx_source_b = KERNEL_SOURCE_ACTIVE_WEIGHT;
        kernel_apx_narrow_a = 192'd0;
        kernel_apx_narrow_b = 192'd0;
        kernel_apx_narrow_b_scalar = 1'b0;
        kernel_apx_scalar_b = 16'd0;
        if (kernel_stat_active) begin
            case (kernel_stat_step_q)
                STAT_MEAN_STREAM: begin
                    if (source_buffer0_valid_q) begin
                        kernel_apx_request_valid = 1'b1;
                        kernel_apx_request_operation =
                            APX_MULTIPLY_REDUCE;
                        kernel_apx_request_tag =
                            16'hA000 |
                            {10'd0, kernel_response_count_q};
                    end
                end
                STAT_PAIR_ROW_WAIT: begin
                    if ((kernel_row_q == 4'd0) &&
                        source_buffer0_valid_q) begin
                        kernel_apx_request_valid = 1'b1;
                        kernel_apx_request_operation =
                            APX_MULTIPLY_REDUCE;
                        kernel_apx_request_tag =
                            16'hC000 | {10'd0, kernel_index_q};
                    end
                end
                STAT_PAIR_COL_WAIT: begin
                    if (kernel_weight_resident_valid_q) begin
                        kernel_apx_request_valid = 1'b1;
                        kernel_apx_request_operation =
                            APX_MULTIPLY_REDUCE;
                        kernel_apx_request_tag =
                            16'hC000 | {10'd0, kernel_index_q};
                    end
                end
                STAT_MEAN_SCALE_ISSUE: begin
                    kernel_apx_request_valid = 1'b1;
                    kernel_apx_request_operation = APX_MULTIPLY_VECTOR;
                    kernel_apx_request_lanes = {1'b0, bound0_q[3:0]};
                    kernel_apx_request_tag = 16'hB001;
                    kernel_apx_source_a = KERNEL_SOURCE_NARROW;
                    kernel_apx_narrow_a[127:0] = gram_local_data_q;
                end
                STAT_PAIR_SELF_ISSUE: begin
                    kernel_apx_request_valid = 1'b1;
                    kernel_apx_request_operation = APX_MULTIPLY_REDUCE;
                    kernel_apx_request_tag =
                        16'hC000 | {10'd0, kernel_index_q};
                end
                STAT_POST_MUL_LOAD: begin
                    kernel_apx_request_valid = 1'b1;
                    kernel_apx_request_operation = APX_MULTIPLY_VECTOR;
                    kernel_apx_request_lanes = 5'd2;
                    kernel_apx_request_tag = 16'hE000;
                    kernel_apx_source_a = KERNEL_SOURCE_NARROW;
                    kernel_apx_source_b = KERNEL_SOURCE_NARROW;
                    kernel_apx_narrow_a[31:0] = {
                        select_chunk_word(
                            scratch_role0_data, kernel_row_q[2:0]),
                        select_chunk_word(
                            scratch_role1_data, kernel_index_q[2:0])
                    };
                    kernel_apx_narrow_b[31:0] = {
                        select_chunk_word(
                            scratch_role0_data, kernel_column_q[2:0]),
                        weight_slots[0][15:0]
                    };
                end
                STAT_POST_MUL_ISSUE: begin
                    kernel_apx_request_valid = 1'b1;
                    kernel_apx_request_operation = APX_MULTIPLY_VECTOR;
                    kernel_apx_request_lanes = 5'd2;
                    kernel_apx_request_tag = 16'hE000;
                    kernel_apx_source_a = KERNEL_SOURCE_NARROW;
                    kernel_apx_narrow_a[127:0] = gram_local_data_q;
                end
                STAT_TRACE_ISSUE: begin
                    kernel_apx_request_valid = 1'b1;
                    kernel_apx_request_operation = APX_MULTIPLY_REDUCE;
                    kernel_apx_request_lanes = {1'b0, bound0_q[3:0]};
                    kernel_apx_request_tag = 16'hE002;
                    kernel_apx_source_a = KERNEL_SOURCE_NARROW;
                    kernel_apx_narrow_a[127:0] = gram_local_data_q;
                end
                STAT_TRACE_SCALE_ISSUE: begin
                    kernel_apx_request_valid = 1'b1;
                    kernel_apx_request_operation = APX_MULTIPLY_VECTOR;
                    kernel_apx_request_lanes = 5'd1;
                    kernel_apx_request_tag = 16'hE003;
                end
                STAT_TRACE_REG_ISSUE: begin
                    kernel_apx_request_valid = 1'b1;
                    kernel_apx_request_operation = APX_MULTIPLY_VECTOR;
                    kernel_apx_request_lanes = 5'd1;
                    kernel_apx_request_tag = 16'hE004;
                end
                default: begin
                end
            endcase
        end
        else if (kernel_triangular_active) begin
            kernel_apx_source_a = KERNEL_SOURCE_NARROW;
            kernel_apx_source_b = KERNEL_SOURCE_NARROW;
            if (kernel_refine_request_valid) begin
                kernel_apx_request_valid = 1'b1;
                kernel_apx_request_operation =
                    kernel_refine_request_operation;
                kernel_apx_request_lanes = kernel_refine_request_lanes;
                kernel_apx_request_tag = kernel_refine_request_tag;
                kernel_apx_narrow_a[63:0] = kernel_refine_operand_a;
                kernel_apx_narrow_b[63:0] = kernel_refine_operand_b;
            end
            else if (factor_dot_reduce_request) begin
                kernel_apx_request_valid = 1'b1;
                kernel_apx_request_operation = APX_REDUCE_VECTOR;
                kernel_apx_request_lanes = {1'b0, kernel_row_q};
                kernel_apx_request_tag = 16'hD200;
                kernel_apx_narrow_a = scratch_role0_data;
            end
            else if (factor_scalar_add_request) begin
                kernel_apx_request_valid = 1'b1;
                kernel_apx_request_operation = APX_ADD_VECTOR;
                kernel_apx_request_lanes = 5'd1;
                kernel_apx_request_tag =
                    (kernel_tri_step_q == TRI_SUB_ISSUE) ?
                    16'hD201 : 16'hD202;
                kernel_apx_narrow_a[15:0] =
                    (kernel_tri_step_q == TRI_SUB_ISSUE) ?
                    factor_scalar : 16'h3E00;
                kernel_apx_narrow_b[15:0] =
                    (kernel_tri_step_q == TRI_SUB_ISSUE) ?
                    (factor_refine_result ^ 16'h8000) :
                    (factor_temp ^ 16'h8000);
            end
        end
        else if (kernel_backsub_active) begin
            case (kernel_backsub_step_q)
                BACKSUB_RAW_WAIT: begin
                    if (solve_stream_resident_valid_q) begin
                        kernel_apx_request_valid = 1'b1;
                        kernel_apx_request_operation = APX_ADD_VECTOR;
                        kernel_apx_request_lanes = lanes_q;
                        kernel_apx_request_tag = 16'hF000;
                        kernel_apx_source_a = KERNEL_SOURCE_RESIDENT0;
                        kernel_apx_source_b =
                            KERNEL_SOURCE_NARROW | KERNEL_SOURCE_NEGATE;
                        kernel_apx_scalar_b = solve_mean;
                        kernel_apx_narrow_b_scalar = 1'b1;
                    end
                end
                BACKSUB_CENTER_WAIT: begin
                    if (kernel_pair_f000_event &&
                        (kernel_row_q == 4'd0)) begin
                        kernel_apx_request_valid = 1'b1;
                        kernel_apx_request_operation =
                            APX_MULTIPLY_VECTOR;
                        kernel_apx_request_lanes = lanes_q;
                        kernel_apx_request_tag = 16'hF400;
                        kernel_apx_source_a = KERNEL_SOURCE_PAIR;
                        kernel_apx_source_b = KERNEL_SOURCE_NARROW;
                        kernel_apx_scalar_b = kernel_diagonal_q;
                        kernel_apx_narrow_b_scalar = 1'b1;
                    end
                end
                BACKSUB_PRODUCT_STREAM: begin
                    if (solve_stream_resident_valid_q) begin
                        kernel_apx_request_valid = 1'b1;
                        kernel_apx_request_operation =
                            APX_MULTIPLY_VECTOR;
                        kernel_apx_request_lanes = lanes_q;
                        kernel_apx_request_tag =
                            16'hF200 | {10'd0, kernel_response_count_q};
                        kernel_apx_source_a = KERNEL_SOURCE_RESIDENT0;
                        kernel_apx_source_b = KERNEL_SOURCE_NARROW;
                        kernel_apx_scalar_b = solve_factor;
                        kernel_apx_narrow_b_scalar = 1'b1;
                    end
                    else if (kernel_product_f2_event_q &&
                             ((kernel_result_count_q + 6'd1) >=
                              {2'd0, kernel_row_q})) begin
                        if (kernel_row_q == 4'd1) begin
                            kernel_apx_request_valid = 1'b1;
                            kernel_apx_request_operation =
                                APX_ADD_VECTOR;
                            kernel_apx_request_lanes = lanes_q;
                            kernel_apx_request_tag = 16'hF305;
                            kernel_apx_source_a =
                                KERNEL_SOURCE_RESIDENT0;
                            kernel_apx_source_b = KERNEL_SOURCE_PRODUCT |
                                KERNEL_SOURCE_NEGATE;
                        end
                        else if (kernel_row_q >= 4'd3) begin
                            kernel_apx_request_valid = 1'b1;
                            kernel_apx_request_operation =
                                APX_ADD_VECTOR;
                            kernel_apx_request_lanes = lanes_q;
                            kernel_apx_request_tag = 16'hF301;
                            kernel_apx_source_a =
                                KERNEL_SOURCE_RESIDENT0;
                            kernel_apx_source_b =
                                KERNEL_SOURCE_ACTIVE_WEIGHT;
                        end
                    end
                end
                BACKSUB_REDUCE_01_ISSUE: begin
                    kernel_apx_request_valid = 1'b1;
                    kernel_apx_request_operation = APX_ADD_VECTOR;
                    kernel_apx_request_lanes = lanes_q;
                    kernel_apx_request_tag = 16'hF301;
                    kernel_apx_source_a = KERNEL_SOURCE_RESIDENT0;
                    kernel_apx_source_b = KERNEL_SOURCE_ACTIVE_WEIGHT;
                end
                BACKSUB_REDUCE_01_WAIT: begin
                    if (kernel_pair_f301_event) begin
                        kernel_apx_request_valid = 1'b1;
                        kernel_apx_request_operation = APX_ADD_VECTOR;
                        kernel_apx_request_lanes = lanes_q;
                        if (kernel_row_q == 4'd2) begin
                            kernel_apx_request_tag = 16'hF305;
                            kernel_apx_source_a =
                                KERNEL_SOURCE_RESIDENT0;
                            kernel_apx_source_b = KERNEL_SOURCE_PAIR |
                                KERNEL_SOURCE_NEGATE;
                        end
                        else if (kernel_row_q == 4'd3) begin
                            kernel_apx_request_tag = 16'hF304;
                            kernel_apx_source_a = KERNEL_SOURCE_PAIR;
                            kernel_apx_source_b =
                                KERNEL_SOURCE_ACTIVE_WEIGHT;
                        end
                        else begin
                            kernel_apx_request_tag = 16'hF302;
                            kernel_apx_source_a =
                                KERNEL_SOURCE_RESIDENT0;
                            kernel_apx_source_b =
                                KERNEL_SOURCE_ACTIVE_WEIGHT;
                        end
                    end
                end
                BACKSUB_REDUCE_23_ISSUE: begin
                    kernel_apx_request_valid = 1'b1;
                    kernel_apx_request_operation = APX_ADD_VECTOR;
                    kernel_apx_request_lanes = lanes_q;
                    kernel_apx_request_tag = 16'hF302;
                    kernel_apx_source_a = KERNEL_SOURCE_RESIDENT0;
                    kernel_apx_source_b = KERNEL_SOURCE_ACTIVE_WEIGHT;
                end
                BACKSUB_REDUCE_23_WAIT: begin
                    if (kernel_pair_f302_event) begin
                        kernel_apx_request_valid = 1'b1;
                        kernel_apx_request_operation = APX_ADD_VECTOR;
                        kernel_apx_request_lanes = lanes_q;
                        kernel_apx_request_tag = 16'hF303;
                        kernel_apx_source_a = KERNEL_SOURCE_RESIDENT0;
                        kernel_apx_source_b = KERNEL_SOURCE_PAIR;
                    end
                end
                BACKSUB_REDUCE_FINAL_ISSUE: begin
                    kernel_apx_request_valid = 1'b1;
                    kernel_apx_request_operation = APX_ADD_VECTOR;
                    kernel_apx_request_lanes = lanes_q;
                    kernel_apx_request_tag = 16'hF303;
                    kernel_apx_source_a = KERNEL_SOURCE_RESIDENT0;
                    kernel_apx_source_b = KERNEL_SOURCE_ACTIVE_WEIGHT;
                end
                BACKSUB_REDUCE_FINAL_WAIT: begin
                    if (kernel_pair_f303_event) begin
                        kernel_apx_request_valid = 1'b1;
                        kernel_apx_request_operation = APX_ADD_VECTOR;
                        kernel_apx_request_lanes = lanes_q;
                        if (kernel_row_q == 4'd5) begin
                            kernel_apx_request_tag = 16'hF304;
                            kernel_apx_source_a = KERNEL_SOURCE_PAIR;
                            kernel_apx_source_b =
                                KERNEL_SOURCE_ACTIVE_WEIGHT;
                        end
                        else begin
                            kernel_apx_request_tag = 16'hF305;
                            kernel_apx_source_a =
                                KERNEL_SOURCE_RESIDENT0;
                            kernel_apx_source_b = KERNEL_SOURCE_PAIR |
                                KERNEL_SOURCE_NEGATE;
                        end
                    end
                end
                BACKSUB_REDUCE_LAST_ISSUE: begin
                    kernel_apx_request_valid = 1'b1;
                    kernel_apx_request_operation = APX_ADD_VECTOR;
                    kernel_apx_request_lanes = lanes_q;
                    kernel_apx_request_tag = 16'hF304;
                    kernel_apx_source_a = KERNEL_SOURCE_RESIDENT0;
                    kernel_apx_source_b = KERNEL_SOURCE_ACTIVE_WEIGHT;
                end
                BACKSUB_REDUCE_LAST_WAIT: begin
                    if (kernel_pair_f304_event) begin
                        kernel_apx_request_valid = 1'b1;
                        kernel_apx_request_operation = APX_ADD_VECTOR;
                        kernel_apx_request_lanes = lanes_q;
                        kernel_apx_request_tag = 16'hF305;
                        kernel_apx_source_a = KERNEL_SOURCE_RESIDENT0;
                        kernel_apx_source_b = KERNEL_SOURCE_PAIR |
                            KERNEL_SOURCE_NEGATE;
                    end
                end
                BACKSUB_SUB_ISSUE: begin
                    kernel_apx_request_valid = 1'b1;
                    kernel_apx_request_operation = APX_ADD_VECTOR;
                    kernel_apx_request_lanes = lanes_q;
                    kernel_apx_request_tag = 16'hF305;
                    kernel_apx_source_a = KERNEL_SOURCE_RESIDENT0;
                    kernel_apx_source_b = KERNEL_SOURCE_ACTIVE_WEIGHT |
                        KERNEL_SOURCE_NEGATE;
                end
                BACKSUB_SUB_WAIT: begin
                    if (kernel_pair_f305_event) begin
                        kernel_apx_request_valid = 1'b1;
                        kernel_apx_request_operation =
                            APX_MULTIPLY_VECTOR;
                        kernel_apx_request_lanes = lanes_q;
                        kernel_apx_request_tag = 16'hF400;
                        kernel_apx_source_a = KERNEL_SOURCE_PAIR;
                        kernel_apx_source_b = KERNEL_SOURCE_NARROW;
                        kernel_apx_scalar_b = kernel_diagonal_q;
                        kernel_apx_narrow_b_scalar = 1'b1;
                    end
                end
                BACKSUB_SCALE_ISSUE: begin
                    kernel_apx_request_valid = 1'b1;
                    kernel_apx_request_operation = APX_MULTIPLY_VECTOR;
                    kernel_apx_request_lanes = lanes_q;
                    kernel_apx_request_tag = 16'hF400;
                    kernel_apx_source_a = KERNEL_SOURCE_RESIDENT0;
                    kernel_apx_source_b = KERNEL_SOURCE_NARROW;
                    kernel_apx_scalar_b = kernel_diagonal_q;
                    kernel_apx_narrow_b_scalar = 1'b1;
                end
                default: begin
                end
            endcase
        end
        else if (kernel_recurrence_active && iir_main_request_valid) begin
            kernel_apx_request_valid = 1'b1;
            kernel_apx_request_operation = APX_MULTIPLY_VECTOR;
            kernel_apx_request_lanes = lanes_q;
            kernel_apx_request_tag = iir_main_request_tag;
            // IIR coefficients already reside in weight slot zero.  Keep that
            // 192-bit payload local instead of copying it into the shared issue
            // slot; only the explicit -1 command uses narrow scalar broadcast.
            kernel_apx_source_a = KERNEL_SOURCE_NARROW;
            kernel_apx_source_b = KERNEL_SOURCE_ACTIVE_WEIGHT;
            kernel_apx_narrow_a =
                ((iir_phase_q == REC_REAL) ||
                 (iir_phase_q == REC_IMAG)) ?
                iir_neg_state_bus : iir_raw_state_bus;
            if (iir_run_active) begin
                if (iir_main_is_negative) begin
                    kernel_apx_source_b = KERNEL_SOURCE_NARROW;
                    kernel_apx_scalar_b = 16'hBC00;
                    kernel_apx_narrow_b_scalar = 1'b1;
                end
            end
            else begin
                kernel_apx_source_b = KERNEL_SOURCE_ACTIVE_WEIGHT |
                    KERNEL_SOURCE_NEGATE;
            end
        end
    end

    // Kernel external data uses one compact source address.  All other
    // non-recursive modes resolve their operands in the shared command owner
    // below, so their phase control cannot reach the APX input directly.
    always @(*) begin
        live_apx_external_a_source_select = APX_EXTERNAL_A_SOURCE0;
        if (kernel_apx_owner) begin
            if (kernel_backsub_active &&
                (((kernel_backsub_step_q == BACKSUB_RAW_WAIT) &&
                  (kernel_apx_request_tag == 16'hF000)) ||
                 ((kernel_backsub_step_q == BACKSUB_PRODUCT_STREAM) &&
                  (kernel_apx_request_tag[15:8] == 8'hF2))))
                live_apx_external_a_source_select = APX_EXTERNAL_A_SOLVE;
        end
    end

    // One top-level ownership decoder converts every producer into a candidate
    // APX command.  It does not drive the arithmetic cluster directly: the
    // selected transaction must first cross shared_apx_issue_*_q.
    always @(*) begin
        shared_apx_live_owner = SHARED_APX_OWNER_NONE;
        shared_apx_live_operation = APX_MULTIPLY_VECTOR;
        shared_apx_live_lanes = 5'd1;
        shared_apx_live_tag = 16'd0;
        shared_apx_live_add_vector = 1'b0;
        shared_apx_live_operand_a_select = APX_OPERAND_EXTERNAL;
        shared_apx_live_operand_b_select = APX_OPERAND_EXTERNAL;
        shared_apx_live_external_a_select = APX_EXTERNAL_A_SOURCE0;
        shared_apx_live_weight_slot = active_weight_slot_q;
        shared_apx_live_operand_a_negate = 1'b0;
        shared_apx_live_operand_b_negate = 1'b0;
        shared_apx_live_narrow_b_scalar = 1'b0;
        shared_apx_live_window_shift = 1'b0;
        shared_apx_live_window_sample = 16'd0;

        if (kernel_apx_owner && kernel_apx_request_valid) begin
            shared_apx_live_owner = SHARED_APX_OWNER_KERNEL;
            shared_apx_live_operation = kernel_apx_request_operation;
            shared_apx_live_lanes = kernel_apx_request_lanes;
            shared_apx_live_tag = kernel_apx_request_tag;
            case (kernel_apx_source_a[3:0])
                KERNEL_SOURCE_PRODUCT:
                    shared_apx_live_operand_a_select = APX_OPERAND_PRODUCT;
                KERNEL_SOURCE_PAIR:
                    shared_apx_live_operand_a_select = APX_OPERAND_PAIR;
                KERNEL_SOURCE_NARROW:
                    shared_apx_live_operand_a_select = APX_OPERAND_NARROW;
                default:
                    shared_apx_live_operand_a_select = APX_OPERAND_EXTERNAL;
            endcase
            case (kernel_apx_source_b[3:0])
                KERNEL_SOURCE_PRODUCT:
                    shared_apx_live_operand_b_select = APX_OPERAND_PRODUCT;
                KERNEL_SOURCE_PAIR:
                    shared_apx_live_operand_b_select = APX_OPERAND_PAIR;
                KERNEL_SOURCE_NARROW:
                    shared_apx_live_operand_b_select = APX_OPERAND_NARROW;
                KERNEL_SOURCE_SCALAR:
                    shared_apx_live_operand_b_select = APX_OPERAND_NARROW;
                default:
                    shared_apx_live_operand_b_select = APX_OPERAND_EXTERNAL;
            endcase
            shared_apx_live_external_a_select =
                live_apx_external_a_source_select;
            shared_apx_live_weight_slot = kernel_recurrence_active ?
                1'b0 : active_weight_slot_q;
            shared_apx_live_operand_a_negate =
                kernel_apx_source_a[4];
            shared_apx_live_operand_b_negate =
                kernel_apx_source_b[4];
            shared_apx_live_narrow_b_scalar =
                kernel_apx_narrow_b_scalar;
            shared_apx_live_add_vector =
                (kernel_triangular_active || kernel_backsub_active) &&
                (kernel_apx_request_operation == APX_ADD_VECTOR);
        end
        else if (!kernel_apx_owner) begin
            if (tile_apx_request_valid) begin
                shared_apx_live_owner = SHARED_APX_OWNER_TILE;
                shared_apx_live_operation = APX_MULTIPLY_REDUCE;
                shared_apx_live_lanes = lanes_q;
                shared_apx_live_tag = tile_apx_request_tag;
                shared_apx_live_external_a_select =
                    (tile_phase_q == TILE_IMAG_ISSUE) ?
                    APX_EXTERNAL_A_SOURCE1 : APX_EXTERNAL_A_SOURCE0;
                shared_apx_live_weight_slot = 1'b0;
            end
            else if (generic_apx_request_valid) begin
                shared_apx_live_owner = SHARED_APX_OWNER_GENERIC;
                shared_apx_live_operation = vector_add_mode_q ?
                    APX_ADD_VECTOR : APX_MULTIPLY_VECTOR;
                shared_apx_live_lanes = lanes_q;
                if (pool_mode && ewise_mode_q) begin
                    shared_apx_live_operand_b_select = APX_OPERAND_NARROW;
                    shared_apx_live_narrow_b_scalar = 1'b1;
                end
                shared_apx_live_add_vector = vector_add_mode_q;
            end
            else if (pool_scale_request_valid) begin
                shared_apx_live_owner = SHARED_APX_OWNER_POOL;
                shared_apx_live_operation = APX_MULTIPLY_VECTOR;
                shared_apx_live_lanes = accumulation_pair_return ?
                    {1'b0, accumulation_return_lanes} : 5'd1;
                shared_apx_live_tag = {11'd0, chunk_index_q};
                shared_apx_live_operand_a_select = APX_OPERAND_NARROW;
                shared_apx_live_operand_b_select = APX_OPERAND_NARROW;
                shared_apx_live_narrow_b_scalar = 1'b1;
            end
            else if (pair_bias_request_valid) begin
                shared_apx_live_owner = SHARED_APX_OWNER_PAIR_BIAS;
                shared_apx_live_operation = APX_ADD_VECTOR;
                shared_apx_live_lanes = {1'b0, pair_bias_chunk_lanes};
                shared_apx_live_tag = {11'd0, chunk_index_q};
                shared_apx_live_operand_a_select = APX_OPERAND_NARROW;
                shared_apx_live_operand_b_select = APX_OPERAND_NARROW;
                shared_apx_live_narrow_b_scalar = 1'b1;
                shared_apx_live_add_vector = 1'b1;
            end
            else if (apx_add_request_valid) begin
                shared_apx_live_owner = SHARED_APX_OWNER_ADD;
                shared_apx_live_operation = APX_ADD_VECTOR;
                shared_apx_live_lanes = bias_add_request_valid ?
                    {1'b0, bias_chunk_lanes} :
                    {1'b0, chunk_lane_count_q};
                shared_apx_live_tag = {11'd0, chunk_index_q};
                shared_apx_live_operand_a_select = APX_OPERAND_NARROW;
                shared_apx_live_operand_b_select = APX_OPERAND_NARROW;
                shared_apx_live_narrow_b_scalar = bias_add_request_valid;
                shared_apx_live_add_vector = 1'b1;
            end
            else if (pair_apx_request_valid) begin
                shared_apx_live_owner = SHARED_APX_OWNER_PAIR;
                shared_apx_live_operation = APX_MULTIPLY_REDUCE;
                shared_apx_live_lanes = lanes_q;
                shared_apx_live_tag = {10'd0, pair_request_tag};
                shared_apx_live_weight_slot = pair_issue_phase_q;
            end
            else if (gather_apx_request_valid) begin
                shared_apx_live_owner = SHARED_APX_OWNER_GATHER;
                shared_apx_live_operation = APX_MULTIPLY_REDUCE;
                shared_apx_live_lanes = lanes_q;
                shared_apx_live_tag = {4'd0, gather_issue_count_q};
                if (pool_mode) begin
                    shared_apx_live_operand_b_select = APX_OPERAND_NARROW;
                    shared_apx_live_narrow_b_scalar = 1'b1;
                end
            end
            else if (window_apx_request_valid &&
                     window_apx_issue_eligible) begin
                shared_apx_live_owner = SHARED_APX_OWNER_WINDOW;
                shared_apx_live_operation = window_apx_request_operation;
                shared_apx_live_lanes = window_apx_request_lanes;
                shared_apx_live_tag = window_apx_request_tag;
                shared_apx_live_weight_slot = window_apx_weight_select;
                if (window_apx_weight_zero) begin
                    shared_apx_live_operand_b_select = APX_OPERAND_NARROW;
                    shared_apx_live_narrow_b_scalar = 1'b1;
                end
                shared_apx_live_window_shift = window_apx_shift;
                shared_apx_live_window_sample = window_apx_sample;
            end
        end
    end

    assign shared_apx_live_valid =
        shared_apx_live_owner != SHARED_APX_OWNER_NONE;

    // The transaction slot is elastic.  A dispatched command may be replaced
    // by the next candidate on the same edge, preserving one command per cycle
    // without allowing APX ready or any arithmetic result to reach state_q.
    assign shared_apx_dispatch_fire = shared_apx_issue_valid_q &&
        apx_request_ready;
    assign shared_apx_issue_ready = !shared_apx_issue_valid_q ||
        shared_apx_dispatch_fire;
    assign shared_apx_capture_owner = shared_apx_live_owner;
    assign shared_apx_capture_fire = shared_apx_live_valid &&
        shared_apx_issue_ready;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n)
            shared_apx_issue_valid_q <= 1'b0;
        else if (shared_apx_dispatch_fire || shared_apx_capture_fire)
            shared_apx_issue_valid_q <= shared_apx_capture_fire;
    end

    // Payload registers have no reset fanout; valid is the sole observability
    // guard.  Product/pair dependencies remain compact APX-local result-slot
    // selections.  Copying them through a descriptor-level 256-bit resident
    // would sample a wide add after its low half but before its high half.
    always @(posedge clk) begin
        if (shared_apx_capture_fire) begin
            shared_apx_issue_owner_q <= shared_apx_live_owner;
            shared_apx_issue_operation_q <= shared_apx_live_operation;
            shared_apx_issue_lanes_q <= shared_apx_live_lanes;
            shared_apx_issue_tag_q <= shared_apx_live_tag;
            shared_apx_issue_operand_a_control_q <= {4{
                shared_apx_live_operand_a_negate, 2'b00,
                shared_apx_live_operand_a_select
            }};
            shared_apx_issue_operand_b_control_q <= {4{
                shared_apx_live_operand_b_negate, 1'b0,
                shared_apx_live_narrow_b_scalar,
                shared_apx_live_operand_b_select
            }};
            shared_apx_issue_narrow_a_high_q <=
                shared_apx_live_narrow_operand_a[191:128];
            shared_apx_issue_narrow_b_q <=
                shared_apx_live_narrow_operand_b[127:0];
            shared_apx_issue_external_a_select_q <=
                shared_apx_live_external_a_select;
            shared_apx_issue_weight_slot_q <=
                shared_apx_live_weight_slot;
            shared_apx_issue_add_vector_q <=
                shared_apx_live_add_vector;
            shared_apx_issue_window_shift_q <=
                shared_apx_live_window_shift;
            shared_apx_issue_window_sample_q <=
                shared_apx_live_window_sample;
        end
    end

    // Producer-visible acceptance is the enqueue event.  The state machine can
    // prepare the following command while APX consumes only the registered head.
    assign kernel_apx_request_fire = shared_apx_capture_fire &&
        (shared_apx_capture_owner == SHARED_APX_OWNER_KERNEL);
    assign iir_apx_request_fire = kernel_recurrence_active &&
        kernel_apx_request_fire;

    assign apx_request_valid = shared_apx_issue_valid_q;
    assign apx_request_operation = shared_apx_issue_operation_q;
    assign apx_request_lanes = shared_apx_issue_lanes_q;
    assign apx_request_tag = shared_apx_issue_tag_q;
    assign apx_operand_a =
        (shared_apx_issue_external_a_select_q ==
         APX_EXTERNAL_A_SOURCE1) ?
         source_buffer1_data_q :
        (shared_apx_issue_external_a_select_q ==
         APX_EXTERNAL_A_SOLVE) ?
         solve_stream_resident_data_q : source_buffer0_data_q;
    assign apx_operand_b = weight_slots[shared_apx_issue_weight_slot_q];
    assign window_apx_selected =
        shared_apx_issue_owner_q == SHARED_APX_OWNER_WINDOW;

    always @(*) begin
        shared_apx_live_narrow_operand_a = 192'd0;
        shared_apx_live_narrow_operand_b = 192'd0;

        if (shared_apx_live_valid) begin
            case (shared_apx_live_owner)
                SHARED_APX_OWNER_KERNEL: begin
                    shared_apx_live_narrow_operand_a =
                        kernel_apx_narrow_a;
                    shared_apx_live_narrow_operand_b =
                        kernel_apx_narrow_b_scalar ?
                        {176'd0, kernel_apx_scalar_b} :
                        kernel_apx_narrow_b;
                end
                SHARED_APX_OWNER_POOL: begin
                    shared_apx_live_narrow_operand_a =
                        accumulation_pair_return ?
                        {64'd0, apx_pair_bus[127:0]} :
                        {176'd0, compute_result_data};
                    shared_apx_live_narrow_operand_b =
                        {176'd0, active_weight_tile[15:0]};
                end
                SHARED_APX_OWNER_PAIR_BIAS: begin
                    shared_apx_live_narrow_operand_a =
                        {64'd0, pair_bias_scratch_row};
                    shared_apx_live_narrow_operand_b =
                        {176'd0, pair_selected_bias};
                end
                SHARED_APX_OWNER_ADD: begin
                    shared_apx_live_narrow_operand_a =
                        {64'd0, scratch_compute_row};
                    shared_apx_live_narrow_operand_b = bias_add_request_valid ?
                        {176'd0, bias_value_q} :
                        {64'd0, (pool_chunk_overlap ?
                         pool_chunk_full_data : result_chunk_q)};
                end
                SHARED_APX_OWNER_GENERIC,
                SHARED_APX_OWNER_GATHER: begin
                    shared_apx_live_narrow_operand_b =
                        {176'd0, 16'h3C00};
                end
                SHARED_APX_OWNER_WINDOW:
                    shared_apx_live_narrow_operand_b = 192'd0;
                default: begin
                    shared_apx_live_narrow_operand_a = 192'd0;
                    shared_apx_live_narrow_operand_b = 192'd0;
                end
            endcase

        end
    end
    assign apx_narrow_operand_a = {
        shared_apx_issue_narrow_a_high_q, gram_local_data_q
    };
    assign apx_narrow_operand_b = {64'd0, shared_apx_issue_narrow_b_q};
    assign apx_scalar_operand_b = shared_apx_issue_narrow_b_q[15:0];
    assign apx_request_operand_a = apx_operand_a;
    assign apx_request_operand_b = apx_operand_b;
    assign apx_request_add_vector = shared_apx_issue_add_vector_q;

    function [15:0] relu_word;
        input [15:0] value;
        begin
            relu_word = (flags_q[3] && value[15]) ? 16'd0 : value;
        end
    endfunction

    function [127:0] relu_chunk;
        input [127:0] values;
        integer word_index;
        begin
            for (word_index = 0; word_index < 8;
                 word_index = word_index + 1) begin
                relu_chunk[word_index*16 +: 16] =
                    relu_word(values[word_index*16 +: 16]);
            end
        end
    endfunction

    always @(*) begin
        case (retire_stream_word_index_q[2:0])
            3'd0: retire_scratch_word = retire_scratch_row[15:0];
            3'd1: retire_scratch_word = retire_scratch_row[31:16];
            3'd2: retire_scratch_word = retire_scratch_row[47:32];
            3'd3: retire_scratch_word = retire_scratch_row[63:48];
            3'd4: retire_scratch_word = retire_scratch_row[79:64];
            3'd5: retire_scratch_word = retire_scratch_row[95:80];
            3'd6: retire_scratch_word = retire_scratch_row[111:96];
            default: retire_scratch_word = retire_scratch_row[127:112];
        endcase
    end

    always @(*) begin
        kernel_retire_candidate = 173'd0;

        if (tile_retire_phase) begin
            kernel_retire_candidate = {
                1'b1, 1'b0, 1'b0, 1'b0,
                kernel_destination_base_q +
                    ((tile_phase_q == TILE_RETIRE_IMAG) ?
                     destination_stride2_q : 13'd0),
                bound1_q[3:0], lane_mask(bound1_q[3:0]),
                16'd0, scratch_role0_data};
        end
        else if (kernel_stat_active &&
                 (kernel_stat_step_q == STAT_MEAN_RETIRE)) begin
            kernel_retire_candidate = {
                !kernel_retire_accepted_q, 1'b0, 1'b0, 1'b0,
                destination_address_q + destination_stride0_q,
                bound0_q[3:0], lane_mask(bound0_q[3:0]),
                16'd0, scratch_role0_data};
        end
        else if (kernel_stat_active &&
                 ((kernel_stat_step_q == STAT_POST_RETIRE_LOW) ||
                  (kernel_stat_step_q == STAT_POST_RETIRE_HIGH) ||
                  (kernel_stat_step_q == STAT_DIAG_RETIRE))) begin
            kernel_retire_candidate = {
                !kernel_retire_accepted_q, 1'b0, 1'b0, 1'b1,
                kernel_destination_base_q, 4'd1, 8'h01,
                kernel_value_q, 128'd0};
        end
        else if (kernel_triangular_active &&
                 (kernel_tri_step_q == TRI_RETIRE)) begin
            kernel_retire_candidate = {
                !kernel_retire_accepted_q, 1'b0, 1'b0, 1'b0,
                retire_destination_q, bound0_q[3:0],
                lane_mask(bound0_q[3:0]), 16'd0,
                kernel_scalar_bank_q[127:0]};
        end
        else if (kernel_backsub_active &&
                 ((kernel_backsub_step_q == BACKSUB_RETIRE_LOW) ||
                  (kernel_backsub_step_q == BACKSUB_RETIRE_HIGH))) begin
            kernel_retire_candidate = {
                (!kernel_retire_accepted_q ||
                 ((kernel_backsub_step_q == BACKSUB_RETIRE_LOW) &&
                  !kernel_retire_chained_q)),
                1'b0, 1'b0, 1'b0,
                kernel_destination_base_q +
                    (((kernel_backsub_step_q == BACKSUB_RETIRE_HIGH) ||
                      ((kernel_backsub_step_q == BACKSUB_RETIRE_LOW) &&
                       kernel_retire_accepted_q)) ? 13'd8 : 13'd0),
                4'd8, 8'hFF, 16'd0,
                (((kernel_backsub_step_q == BACKSUB_RETIRE_HIGH) ||
                  ((kernel_backsub_step_q == BACKSUB_RETIRE_LOW) &&
                   kernel_retire_accepted_q)) ?
                 weight_slots[1][255:128] :
                 weight_slots[1][127:0])};
        end
        else if (kernel_recurrence_active &&
                 (iir_phase_q == REC_RETIRE)) begin
            kernel_retire_candidate = {
                !kernel_retire_accepted_q, 1'b0, 1'b0, 1'b0,
                kernel_destination_base_q +
                    {8'd0, kernel_chunk_q[1:0], 3'd0},
                iir_retire_word_count,
                lane_mask(iir_retire_word_count),
                16'd0, iir_retire_data};
        end
    end

    always @(*) begin
        service_retire_candidate = 173'd0;

        if (emit_mode_q && (state_q == STATE_FIRST_WEIGHT_WAIT) &&
            service_tile_response_valid) begin
            service_retire_candidate = {
                1'b1, 1'b1, emit_final_chunk, 1'b0,
                retire_destination_q, emit_chunk_lanes[3:0],
                lane_mask(emit_chunk_lanes[3:0]), 16'd0,
                service_response_data[127:0]};
        end
        else if (copy_mode && (state_q == STATE_FIRST_WEIGHT_WAIT) &&
                 service_response_valid) begin
            service_retire_candidate = {
                1'b1, 1'b0, 1'b0, 1'b0,
                retire_destination_q +
                    (service_response_half ? 13'd8 : 13'd0),
                copy_beat_lanes[3:0],
                lane_mask(copy_beat_lanes[3:0]), 16'd0,
                service_response_data[127:0]};
        end
    end

    always @(*) begin
        vector_retire_candidate = 173'd0;

        if ((state_q == STATE_EWISE_RESULT) && apx_product_valid) begin
            vector_retire_candidate = {
                1'b1, 1'b0, 1'b0, 1'b0,
                retire_destination_q, lanes_q[3:0],
                lane_mask(lanes_q[3:0]), 16'd0,
                apx_product_bus[127:0]};
        end
        else if ((state_q == STATE_VECTOR_RESULT) && apx_pair_valid) begin
            vector_retire_candidate = {
                1'b1, 1'b0, 1'b0, 1'b0,
                retire_destination_q, lanes_q[3:0],
                lane_mask(lanes_q[3:0]), 16'd0,
                apx_pair_bus[127:0]};
        end
        else if ((state_q == STATE_PAIR_BIAS) && !flags_q[2] &&
                 !pair_retire_pending_q) begin
            vector_retire_candidate = {
                1'b1, 1'b0, 1'b0, 1'b0,
                pair_bias_destination, pair_bias_chunk_lanes,
                lane_mask(pair_bias_chunk_lanes), 16'd0,
                relu_chunk(pair_bias_scratch_row)};
        end
        else if (pair_add_return) begin
            vector_retire_candidate = {
                1'b1, 1'b0, 1'b0, 1'b0,
                pair_bias_destination, pair_bias_chunk_lanes,
                lane_mask(pair_bias_chunk_lanes), 16'd0,
                relu_chunk(apx_pair_bus[127:0])};
        end
    end

    always @(*) begin
        window_retire_candidate = 173'd0;

        if (!kernel_apx_owner && apx_post_add_result_valid &&
            apx_post_add_result_tag[15]) begin
            window_retire_candidate = {
                1'b1, 1'b0, 1'b0, 1'b1,
                accumulation_retire_address_q, 4'd1, 8'h01,
                relu_word(apx_post_add_result), 128'd0};
        end
        else if (pool_scale_direct_retire) begin
            window_retire_candidate = {
                1'b1, 1'b0, 1'b0, 1'b0,
                (accumulation_enabled ?
                 accumulation_retire_address_q : retire_destination_q),
                (accumulation_enabled ?
                 accumulation_return_lanes : 4'd1),
                (accumulation_enabled ?
                 lane_mask(accumulation_return_lanes) : 8'h01),
                16'd0, apx_product_bus[127:0]};
        end
        else if (compute_result_valid && !accumulation_enabled &&
                 !bias_enabled && !pool_scale_enabled) begin
            window_retire_candidate = {
                1'b1, 1'b0, 1'b0, 1'b1,
                retire_destination_q, 4'd1, 8'h01,
                retired_window_result, 128'd0};
        end
        else if (accumulation_pair_return &&
                 final_accumulation_plane && !bias_enabled &&
                 !pool_scale_enabled && aligned_accumulation_retire) begin
            window_retire_candidate = {
                1'b1, 1'b0, 1'b0, 1'b0,
                accumulation_retire_address_q,
                accumulation_return_lanes,
                lane_mask(accumulation_return_lanes), 16'd0,
                relu_chunk(apx_pair_bus[127:0])};
        end
        else if (accumulation_pair_return &&
                 (state_q == STATE_BIAS_RUN) &&
                 aligned_accumulation_retire) begin
            window_retire_candidate = {
                1'b1, 1'b0, 1'b0, 1'b0,
                accumulation_retire_address_q,
                accumulation_return_lanes,
                lane_mask(accumulation_return_lanes), 16'd0,
                relu_chunk(apx_pair_bus[127:0])};
        end
        else if (retire_stream_available) begin
            window_retire_candidate = {
                1'b1, 1'b0, 1'b0, 1'b1,
                accumulation_retire_address_q, 4'd1, 8'h01,
                relu_word(retire_scratch_word), 128'd0};
        end
    end

    // Capture and drain may occur on the same edge for aligned/scalar packets.
    // Nonblocking replacement preserves the old packet for the current commit
    // cycle while installing the next transaction without a throughput bubble.
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            retire_packet_destination_q <= 13'd0;
            retire_packet_word_count_q <= 4'd0;
            retire_packet_lane_mask_q <= 8'd0;
            retire_packet_data_q <= 128'd0;
            retire_packet_last_q <= 1'b0;
        end
        else if (engine_retire_accept) begin
            retire_packet_destination_q <= engine_retire_destination;
            retire_packet_word_count_q <= engine_retire_word_count;
            retire_packet_lane_mask_q <= engine_retire_lane_mask;
            retire_packet_data_q <= engine_retire_word_mode ?
                {112'd0, engine_retire_word_data} :
                engine_retire_lane_data;
            retire_packet_last_q <= engine_retire_last;
        end
    end

    assign parameter_read_valid = service_parameter_read_valid;
    assign parameter_read_address = service_parameter_read_address;
    assign program_read_valid = service_program_read_valid;
    assign program_read_address = service_program_read_address;

    assign memory_a_response_valid = {
        bank3_a_response_valid, bank2_a_response_valid,
        bank1_a_response_valid, bank0_a_response_valid
    };
    assign memory_a_response_data = {
        bank3_a_response_data, bank2_a_response_data,
        bank1_a_response_data, bank0_a_response_data
    };
    assign memory_b_response_valid = {
        bank3_b_response_valid, bank2_b_response_valid,
        bank1_b_response_valid, bank0_b_response_valid
    };
    assign memory_b_response_data = {
        bank3_b_response_data, bank2_b_response_data,
        bank1_b_response_data, bank0_b_response_data
    };

    assign bank0_a_valid = memory_a_valid[0];
    assign bank0_a_write = memory_a_write[0];
    assign bank0_a_address = memory_a_address[12:0];
    assign bank0_a_write_data = memory_a_write_data[15:0];
    assign bank1_a_valid = memory_a_valid[1];
    assign bank1_a_write = memory_a_write[1];
    assign bank1_a_address = memory_a_address[25:13];
    assign bank1_a_write_data = memory_a_write_data[31:16];
    assign bank2_a_valid = memory_a_valid[2];
    assign bank2_a_write = memory_a_write[2];
    assign bank2_a_address = memory_a_address[38:26];
    assign bank2_a_write_data = memory_a_write_data[47:32];
    assign bank3_a_valid = memory_a_valid[3];
    assign bank3_a_write = memory_a_write[3];
    assign bank3_a_address = memory_a_address[51:39];
    assign bank3_a_write_data = memory_a_write_data[63:48];
    assign bank0_b_valid = memory_b_valid[0];
    assign bank0_b_write = memory_b_write[0];
    assign bank0_b_address = memory_b_address[12:0];
    assign bank0_b_write_data = memory_b_write_data[15:0];
    assign bank1_b_valid = memory_b_valid[1];
    assign bank1_b_write = memory_b_write[1];
    assign bank1_b_address = memory_b_address[25:13];
    assign bank1_b_write_data = memory_b_write_data[31:16];
    assign bank2_b_valid = memory_b_valid[2];
    assign bank2_b_write = memory_b_write[2];
    assign bank2_b_address = memory_b_address[38:26];
    assign bank2_b_write_data = memory_b_write_data[47:32];
    assign bank3_b_valid = memory_b_valid[3];
    assign bank3_b_write = memory_b_write[3];
    assign bank3_b_address = memory_b_address[51:39];
    assign bank3_b_write_data = memory_b_write_data[63:48];

    // The descriptor engine may form a successor request from the current
    // response, but the operand service sees only this registered command.
    // This keeps response control out of the next Feature-RAM address cone
    // without changing the RAM's externally visible read latency.
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            operand_command_valid_q <= 1'b0;
            operand_command_space_q <= 2'd0;
            operand_command_base_q <= 13'd0;
            operand_command_lane_stride_q <= 10'd0;
            operand_command_lanes_q <= 5'd0;
            operand_command_negate_q <= 1'b0;
            operand_command_fast_feature_q <= 1'b0;
            operand_command_repeat_count_q <= 12'd0;
            operand_command_repeat_stride_q <= 13'd0;
            operand_command_constant_base_row_q <= 9'd0;
            operand_command_role_q <= OPERAND_ROLE_WEIGHT;
            operand_pending_valid_q <= 1'b0;
            operand_pending_space_q <= 2'd0;
            operand_pending_base_q <= 13'd0;
            operand_pending_lane_stride_q <= 10'd0;
            operand_pending_lanes_q <= 5'd0;
            operand_pending_negate_q <= 1'b0;
            operand_pending_fast_feature_q <= 1'b0;
            operand_pending_repeat_count_q <= 12'd0;
            operand_pending_repeat_stride_q <= 13'd0;
            operand_pending_constant_base_row_q <= 9'd0;
            operand_pending_role_q <= OPERAND_ROLE_WEIGHT;
            operand_response_role_q <= OPERAND_ROLE_WEIGHT;
            operand_response_lanes_q <= 5'd0;
        end
        else begin
            if (operand_command_fire) begin
                operand_response_role_q <= operand_command_role_q;
                operand_response_lanes_q <= operand_command_lanes_q;
            end
            case ({service_request_fire, operand_command_fire})
                2'b01: begin
                    if (operand_pending_valid_q) begin
                        operand_command_valid_q <= 1'b1;
                        operand_command_space_q <=
                            operand_pending_space_q;
                        operand_command_base_q <=
                            operand_pending_base_q;
                        operand_command_lane_stride_q <=
                            operand_pending_lane_stride_q;
                        operand_command_lanes_q <=
                            operand_pending_lanes_q;
                        operand_command_negate_q <=
                            operand_pending_negate_q;
                        operand_command_fast_feature_q <=
                            operand_pending_fast_feature_q;
                        operand_command_repeat_count_q <=
                            operand_pending_repeat_count_q;
                        operand_command_repeat_stride_q <=
                            operand_pending_repeat_stride_q;
                        operand_command_constant_base_row_q <=
                            operand_pending_constant_base_row_q;
                        operand_command_role_q <=
                            operand_pending_role_q;
                        operand_pending_valid_q <= 1'b0;
                    end
                    else begin
                        operand_command_valid_q <= 1'b0;
                    end
                end
                2'b10: begin
                    if (operand_command_valid_q) begin
                        operand_pending_valid_q <= 1'b1;
                        operand_pending_space_q <= service_request_space;
                        operand_pending_base_q <= service_request_base;
                        operand_pending_lane_stride_q <=
                            service_request_lane_stride;
                        operand_pending_lanes_q <= service_request_lanes;
                        operand_pending_negate_q <= service_request_negate;
                        operand_pending_fast_feature_q <=
                            service_request_fast_feature;
                        operand_pending_repeat_count_q <=
                            service_request_repeat_count;
                        operand_pending_repeat_stride_q <=
                            service_request_repeat_stride;
                        operand_pending_constant_base_row_q <=
                            constant_base_row_q;
                        operand_pending_role_q <= service_request_role;
                    end
                    else begin
                        operand_command_valid_q <= 1'b1;
                        operand_command_space_q <= service_request_space;
                        operand_command_base_q <= service_request_base;
                        operand_command_lane_stride_q <=
                            service_request_lane_stride;
                        operand_command_lanes_q <= service_request_lanes;
                        operand_command_negate_q <= service_request_negate;
                        operand_command_fast_feature_q <=
                            service_request_fast_feature;
                        operand_command_repeat_count_q <=
                            service_request_repeat_count;
                        operand_command_repeat_stride_q <=
                            service_request_repeat_stride;
                        operand_command_constant_base_row_q <=
                            constant_base_row_q;
                        operand_command_role_q <= service_request_role;
                    end
                end
                2'b11: begin
                    // pending_valid is necessarily clear because it drives
                    // request_ready.  Replace the issued head directly.
                    operand_command_valid_q <= 1'b1;
                    operand_command_space_q <= service_request_space;
                    operand_command_base_q <= service_request_base;
                    operand_command_lane_stride_q <=
                        service_request_lane_stride;
                    operand_command_lanes_q <= service_request_lanes;
                    operand_command_negate_q <= service_request_negate;
                    operand_command_fast_feature_q <=
                        service_request_fast_feature;
                    operand_command_repeat_count_q <=
                        service_request_repeat_count;
                    operand_command_repeat_stride_q <=
                        service_request_repeat_stride;
                    operand_command_constant_base_row_q <=
                        constant_base_row_q;
                    operand_command_role_q <= service_request_role;
                    operand_pending_valid_q <= 1'b0;
                end
                default: begin
                    // Occupancy and payload remain unchanged.
                end
            endcase
        end
    end

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            state_q <= STATE_IDLE;
            pool_mode_q <= 1'b0;
            single_plane_q <= 1'b0;
            emit_mode_q <= 1'b0;
            pair_mode_q <= 1'b0;
            tile_dot_mode_q <= 1'b0;
            tile_complete_pending_q <= 1'b0;
            ewise_mode_q <= 1'b0;
            vector_add_mode_q <= 1'b0;
            kernel_active_q <= 1'b0;
            kernel_kind_q <= 2'd0;
            kernel_stat_step_q <= 5'd0;
            kernel_tri_step_q <= 5'd0;
            kernel_backsub_step_q <= 5'd0;
            tile_phase_q <= TILE_SOURCE0_REQ;
            iir_phase_q <= REC_SOURCE;
            kernel_row_q <= 4'd0;
            kernel_column_q <= 4'd0;
            kernel_chunk_q <= 5'd0;
            kernel_index_q <= 6'd0;
            kernel_request_count_q <= 6'd0;
            kernel_response_count_q <= 6'd0;
            kernel_result_count_q <= 6'd0;
            kernel_chain_accepted_q <= 1'b0;
            kernel_chunk_base_q <= 13'd0;
            kernel_column_base_q <= 13'd0;
            kernel_destination_base_q <= 13'd0;
            kernel_value_q <= 16'd0;
            kernel_diagonal_q <= 16'd0;
            kernel_scalar_bank_q <= 144'd0;
            iir_samples_remaining_q <= 12'd0;
            iir_run_step_q <= 4'd0;
            iir_restart_gap_q <= 2'd0;
            iir_terminal_request_count_q <= 4'd0;
            iir_terminal_response_count_q <= 4'd0;
            iir_history_valid_q <= 6'd0;
            iir_source_pending_q <= 1'b0;
            iir_prefetch_valid_q <= 1'b0;
            iir_late_valid_q <= 1'b0;
            iir_drain_q <= 1'b0;
            iir_block_wait_q <= 1'b0;
            kernel_refine_busy_q <= 1'b0;
            kernel_refine_done_q <= 1'b0;
            kernel_refine_step_q <= 3'd0;
            flags_q <= 5'd0;
            bound0_q <= 12'd0;
            bound1_q <= 12'd0;
            bound2_q <= 12'd0;
            lanes_q <= 5'd0;
            source_space_q <= 2'd0;
            source_stride0_q <= 13'd0;
            source_stride1_q <= 13'd0;
            source_stride2_q <= 13'd0;
            source_lane_stride_q <= 9'd0;
            source_negate_q <= 1'b0;
            source_fast_tile_q <= 1'b0;
            weight_space_q <= 2'd0;
            weight_stride0_q <= 13'd0;
            weight_stride1_q <= 13'd0;
            weight_stride2_q <= 13'd0;
            weight_lane_stride_q <= 9'd0;
            weight_negate_q <= 1'b0;
            destination_stride0_q <= 13'd0;
            destination_stride1_q <= 13'd0;
            destination_stride2_q <= 13'd0;
            constant_base_row_q <= 9'd0;
            frame_base_q <= 13'd0;
            sequence_i0_q <= 12'd0;
            sequence_i2_q <= 12'd0;
            source_i0_base_q <= 13'd0;
            weight_i0_base_q <= 13'd0;
            source_address_q <= 13'd0;
            weight_address_q <= 13'd0;
            destination_address_q <= 13'd0;
            retire_destination_q <= 13'd0;
            active_weight_slot_q <= 1'b0;
            prefetch_pending_q <= 1'b0;
            prefetch_ready_q <= 1'b0;
            bias_prefetch_pending_q <= 1'b0;
            bias_prefetch_ready_q <= 1'b0;
            bias_value_q <= 16'd0;
            bias_chunk_ready_q <= 1'b0;
            gather_source_pending_q <= 1'b0;
            gather_request_count_q <= 12'd0;
            gather_issue_count_q <= 12'd0;
            gather_result_count_q <= 12'd0;
            gather_source_address_q <= 13'd0;
            source_buffer0_valid_q <= 1'b0;
            source_buffer0_data_q <= 256'd0;
            gram_local_data_q <= 128'd0;
            source_buffer1_data_q <= 256'd0;
            solve_stream_resident_valid_q <= 1'b0;
            solve_stream_resident_data_q <= 256'd0;
            scalar_buffer0_valid_q <= 1'b0;
            scalar_buffer1_valid_q <= 1'b0;
            scalar_buffer0_data_q <= 16'd0;
            scalar_buffer1_data_q <= 16'd0;
            prefetch_sequence_q <= 1'b0;
            bias_sequence_q <= 1'b0;
            pool_scale_pending_q <= 1'b0;
            result_chunk_q <= 128'd0;
            chunk_word_count_q <= 4'd0;
            chunk_index_q <= 5'd0;
            chunk_lane_count_q <= 4'd8;
            pool_chunk_select_q <= 1'b0;
            pool_chunk_full_select_q <= 1'b0;
            window_issue_count_q <= 4'd0;
            window_issue_block_q <= 1'b0;
            chunk_full_q <= 1'b0;
            accumulation_add_pending_q <= 1'b0;
            bias_add_pending_q <= 1'b0;
            window_done_pending_q <= 1'b0;
            produced_chunk_count_q <= 5'd0;
            retire_stream_active_q <= 1'b0;
            retire_stream_word_index_q <= 12'd0;
            accumulation_retire_address_q <= 13'd0;
            emit_word_index_q <= 12'd0;
            emit_packet_lanes_q <= 4'd0;
            emit_packet_finishes_group_q <= 1'b0;
            emit_packet_last_q <= 1'b0;
            emit_prefetch_request_q <= 1'b0;
            emit_prefetch_address_q <= 13'd0;
            emit_prefetch_lanes_q <= 5'd0;
            pair_prefetch_step_q <= 2'd0;
            pair_issue_phase_q <= 1'b0;
            pair_block_base_q <= 12'd0;
            pair_block_samples_q <= 5'd0;
            pair_block_destination_q <= 13'd0;
            pair_bias0_q <= 16'd0;
            pair_bias1_q <= 16'd0;
            pair_bias_pending_q <= 1'b0;
            pair_retire_pending_q <= 1'b0;
            window_chain_pending_q <= 1'b0;
        end
        else begin
            kernel_refine_done_q <= 1'b0;
            if (kernel_refine_busy_q) begin
                // D101 needs lane 0 of the complete D100 product on its next
                // dependency edge.  Capture that transient result when it is
                // produced, independently of the later APX command accept.
                if ((kernel_refine_step_q == 3'd1) &&
                    kernel_product_d100_event_q)
                    source_buffer0_data_q <= apx_product_bus;
                if (kernel_refine_request_fire) begin
                    if (kernel_refine_step_q == 3'd0)
                        kernel_refine_step_q <= 3'd1;
                    else if (kernel_refine_step_q == 3'd1) begin
                        kernel_refine_step_q <= 3'd2;
                    end
                    else if (kernel_refine_step_q == 3'd2)
                        kernel_refine_step_q <= 3'd3;
                    else
                        kernel_refine_step_q <= 3'd4;
                end
                if ((kernel_refine_step_q == 3'd4) &&
                    kernel_pair_d103_event) begin
                    kernel_scalar_bank_q[143:128] <=
                        apx_pair_bus[15:0];
                    kernel_refine_busy_q <= 1'b0;
                    kernel_refine_done_q <= 1'b1;
                end
            end
            if (emit_prefetch_request_q && service_request_ready)
                emit_prefetch_request_q <= 1'b0;
            case ({(vector_source_accept || generic_source_accept ||
                    kernel_source_load),
                   (source_buffer_pop || generic_source_consumed ||
                    kernel_source_pop)})
                2'b10: begin
                    source_buffer0_valid_q <= 1'b1;
                end
                2'b01: begin
                    source_buffer0_valid_q <= 1'b0;
                end
                2'b11: begin
                    source_buffer0_valid_q <= 1'b1;
                end
                default: begin
                end
            endcase
            case ({kernel_solve_stream_load, kernel_solve_source_pop})
                2'b10: begin
                    solve_stream_resident_valid_q <= 1'b1;
                end
                2'b01: begin
                    solve_stream_resident_valid_q <= 1'b0;
                end
                2'b11: begin
                    solve_stream_resident_valid_q <= 1'b1;
                end
                default: begin
                end
            endcase
            if (kernel_backsub_active && kernel_service_response_beat_accept &&
                ((kernel_backsub_step_q == BACKSUB_RAW_WAIT) ||
                 (kernel_backsub_step_q == BACKSUB_PRODUCT_STREAM))) begin
                if (service_response_half)
                    solve_stream_resident_data_q[255:128] <=
                        service_response_data;
                else begin
                    solve_stream_resident_data_q[127:0] <=
                        service_response_data;
                    if (operand_response_lanes_q <= 5'd8)
                        solve_stream_resident_data_q[255:128] <= 128'd0;
                end
            end
            else if (shared_apx_capture_fire && kernel_backsub_active &&
                     (shared_apx_capture_owner ==
                      SHARED_APX_OWNER_KERNEL)) begin
                if (kernel_apx_source_a[3:0] ==
                    KERNEL_SOURCE_PAIR[3:0])
                    solve_stream_resident_data_q <= apx_pair_bus;
                else if (kernel_apx_source_a[3:0] ==
                         KERNEL_SOURCE_PRODUCT[3:0])
                    solve_stream_resident_data_q <= apx_product_bus;
                else if (live_apx_external_a_source_select ==
                         APX_EXTERNAL_A_SOURCE1)
                    solve_stream_resident_data_q <= source_buffer1_data_q;
                else if (live_apx_external_a_source_select ==
                         APX_EXTERNAL_A_SOURCE0)
                    solve_stream_resident_data_q <= source_buffer0_data_q;
            end
            // Every narrow-A command borrows this low 128-bit register.  Full
            // resident commands leave it untouched; modes are mutually
            // exclusive, so the reuse does not duplicate Gram storage.
            if (shared_apx_capture_fire &&
                (shared_apx_live_operand_a_select == APX_OPERAND_NARROW))
                gram_local_data_q <=
                    shared_apx_live_narrow_operand_a[127:0];
            else if (kernel_source_local_load) begin
                case (kernel_stat_step_q)
                    STAT_MEAN_SCALE_LOAD,
                    STAT_TRACE_LOAD:
                        gram_local_data_q <= scratch_role0_data;
                    STAT_POST_MUL_LOAD:
                        gram_local_data_q[31:0] <= {
                            select_chunk_word(scratch_role0_data,
                                              kernel_row_q[2:0]),
                            select_chunk_word(scratch_role1_data,
                                              kernel_index_q[2:0])};
                    STAT_DIAG_ADD_LOAD:
                        gram_local_data_q[15:0] <=
                            select_chunk_word(scratch_role0_data,
                                              kernel_row_q[2:0]);
                    default: begin
                    end
                endcase
            end
            if (tile_service_response_beat_accept) begin
                if (tile_phase_q == TILE_SOURCE0_WAIT) begin
                    if (service_response_half)
                        source_buffer0_data_q[255:128] <=
                            service_response_data;
                    else begin
                        source_buffer0_data_q[127:0] <=
                            service_response_data;
                        if (operand_response_lanes_q <= 5'd8)
                            source_buffer0_data_q[255:128] <= 128'd0;
                    end
                end
                else if (tile_phase_q == TILE_SOURCE1_WAIT) begin
                    if (service_response_half)
                        source_buffer1_data_q[255:128] <=
                            service_response_data;
                    else begin
                        source_buffer1_data_q[127:0] <=
                            service_response_data;
                        if (operand_response_lanes_q <= 5'd8)
                            source_buffer1_data_q[255:128] <= 128'd0;
                    end
                end
            end
            else if (source_response_beat_accept ||
                     kernel_source_service_beat_accept) begin
                if (service_response_half)
                    source_buffer0_data_q[255:128] <=
                        service_response_data;
                else begin
                    source_buffer0_data_q[127:0] <=
                        service_response_data;
                    if (operand_response_lanes_q <= 5'd8)
                        source_buffer0_data_q[255:128] <= 128'd0;
                end
            end
            else if (kernel_source_result_load) begin
                if (kernel_stat_step_q == STAT_TRACE_WAIT)
                    source_buffer0_data_q[15:0] <= apx_reduce_result;
                else
                    source_buffer0_data_q[15:0] <=
                        apx_product_bus[15:0];
            end
            else if (solve_terminal_product_prefetch)
                source_buffer0_data_q <= solve_product_tile0;
            else if (solve_f301_prefetch &&
                     ((kernel_row_q == 4'd2) ||
                      (kernel_row_q >= 4'd4))) begin
                source_buffer0_data_q <= (kernel_row_q == 4'd2) ?
                    source_buffer1_data_q : solve_product_tile0;
            end
            else if (solve_f303_prefetch &&
                     (kernel_row_q != 4'd5))
                source_buffer0_data_q <= source_buffer1_data_q;
            else if (solve_f304_prefetch)
                source_buffer0_data_q <= source_buffer1_data_q;
            else if (kernel_backsub_active && kernel_pair_f000_event) begin
                source_buffer0_data_q <= apx_pair_bus;
                source_buffer1_data_q <= apx_pair_bus;
            end
            else if (kernel_backsub_active && kernel_pair_f301_event &&
                     (kernel_row_q >= 4'd3)) begin
                source_buffer0_data_q <= apx_pair_bus;
            end
            else if (kernel_backsub_active && kernel_pair_f305_event) begin
                source_buffer0_data_q <= apx_pair_bus;
            end
            else if (kernel_backsub_active && kernel_pair_f303_event &&
                     (kernel_row_q == 4'd5)) begin
                source_buffer0_data_q <= apx_pair_bus;
            end
            case ({scalar_source_accept, scalar_buffer_pop})
                2'b10: begin
                    if (!scalar_buffer0_valid_q) begin
                        scalar_buffer0_valid_q <= 1'b1;
                        scalar_buffer0_data_q <=
                            service_response_data[15:0];
                    end
                    else begin
                        scalar_buffer1_valid_q <= 1'b1;
                        scalar_buffer1_data_q <=
                            service_response_data[15:0];
                    end
                end
                2'b01: begin
                    if (scalar_buffer1_valid_q) begin
                        scalar_buffer0_valid_q <= 1'b1;
                        scalar_buffer0_data_q <= scalar_buffer1_data_q;
                        scalar_buffer1_valid_q <= 1'b0;
                    end
                    else begin
                        scalar_buffer0_valid_q <= 1'b0;
                    end
                end
                2'b11: begin
                    scalar_buffer0_valid_q <= 1'b1;
                    scalar_buffer0_data_q <= service_response_data[15:0];
                end
                default: begin
                end
            endcase
            case (state_q)
                STATE_IDLE: begin
                    if (descriptor_valid && descriptor_ready) begin
                        if (descriptor_base[63:60] == OPCODE_CONFIG) begin
                            constant_base_row_q <= descriptor_ext0[30:22];
                            frame_base_q <= {descriptor_ext0[1:0], 11'd0};
                            emit_mode_q <= 1'b0;
                            pair_mode_q <= 1'b0;
                            tile_dot_mode_q <= 1'b0;
                            tile_complete_pending_q <= 1'b0;
                            ewise_mode_q <= 1'b0;
                            vector_add_mode_q <= 1'b0;
                            kernel_active_q <= 1'b0;
                            state_q <= STATE_COMPLETE;
                        end
                        else begin
                            emit_mode_q <=
                                descriptor_base[63:60] == OPCODE_EMIT;
                            pair_mode_q <=
                                (descriptor_base[57:54] == MODE_WINDOW_DOT) &&
                                descriptor_base[48] &&
                                !descriptor_base[49] &&
                                (descriptor_base[47:36] == 12'd2) &&
                                (descriptor_base[23:12] == 12'd1);
                            tile_dot_mode_q <=
                                (descriptor_base[57:54] == MODE_WINDOW_DOT) &&
                                descriptor_base[48] &&
                                !descriptor_base[49] &&
                                (descriptor_base[23:12] > 12'd1);
                            tile_complete_pending_q <= 1'b0;
                            ewise_mode_q <=
                                descriptor_base[57:54] == MODE_EWISE;
                            vector_add_mode_q <=
                                descriptor_base[57:54] == MODE_VECTOR_ADD;
                            kernel_active_q <=
                                (descriptor_base[57:54] >=
                                 MODE_CENTERED_GRAM) &&
                                (descriptor_base[57:54] <= MODE_IIR2_BANK);
                            kernel_kind_q <=
                                descriptor_base[55:54] - 2'd2;
                            kernel_stat_step_q <= 5'd0;
                            kernel_tri_step_q <= 5'd0;
                            kernel_backsub_step_q <= 5'd0;
                            tile_phase_q <= TILE_SOURCE0_REQ;
                            iir_phase_q <= REC_SOURCE;
                            iir_run_step_q <= 4'd0;
                            kernel_scalar_bank_q <= 144'd0;
                            kernel_refine_busy_q <= 1'b0;
                            kernel_refine_done_q <= 1'b0;
                            kernel_refine_step_q <= 3'd0;
                            pool_mode_q <=
                                descriptor_base[57:54] == MODE_POOL;
                            single_plane_q <=
                                descriptor_base[23:12] == 12'd1;
                            flags_q <= descriptor_base[52:48];
                            bound0_q <= descriptor_base[47:36];
                            bound1_q <= descriptor_base[35:24];
                            bound2_q <= descriptor_base[23:12];
                            lanes_q <= descriptor_base[4:0];
                            source_space_q <= descriptor_ext0[63:62];
                            source_stride0_q <= descriptor_ext0[48:36];
                            source_stride1_q <= descriptor_ext0[35:23];
                            source_stride2_q <= descriptor_ext0[22:10];
                            source_lane_stride_q <= descriptor_ext0[9:1];
                            source_negate_q <= descriptor_ext0[0];
                            // Software/program generation owns the invariant
                            // that later tile advances preserve this initial
                            // alignment.  Capture eligibility once at the
                            // descriptor boundary; do not re-decode dynamic
                            // loop addresses on every operand command.
                            source_fast_tile_q <=
                                !descriptor_ext0[63] &&
                                ((descriptor_ext0[9:1] == 9'd1) ||
                                 (descriptor_ext0[35:23] == 13'd1)) &&
                                (descriptor_ext0[50:49] == 2'd0);
                            weight_space_q <= descriptor_ext1[63:62];
                            weight_stride0_q <= descriptor_ext1[48:36];
                            weight_stride1_q <= descriptor_ext1[35:23];
                            weight_stride2_q <= descriptor_ext1[22:10];
                            weight_lane_stride_q <= descriptor_ext1[9:1];
                            weight_negate_q <= descriptor_ext1[0];
                            destination_stride0_q <= descriptor_ext2[48:36];
                            destination_stride1_q <= descriptor_ext2[35:23];
                            destination_stride2_q <= descriptor_ext2[22:10];
                            sequence_i0_q <= 12'd0;
                            sequence_i2_q <= descriptor_base[23:12];
                            source_i0_base_q <= descriptor_ext0[61:49];
                            weight_i0_base_q <= descriptor_ext1[61:49];
                            source_address_q <= descriptor_ext0[61:49];
                            weight_address_q <= descriptor_ext1[61:49];
                            destination_address_q <= descriptor_ext2[61:49];
                            retire_destination_q <= descriptor_ext2[61:49];
                            active_weight_slot_q <= 1'b0;
                            prefetch_pending_q <= 1'b0;
                            prefetch_ready_q <= 1'b0;
                            bias_prefetch_pending_q <= 1'b0;
                            bias_prefetch_ready_q <= 1'b0;
                            gather_source_pending_q <= 1'b0;
                            gather_request_count_q <= 12'd0;
                            gather_issue_count_q <= 12'd0;
                            gather_source_address_q <=
                                descriptor_ext0[61:49];
                            source_buffer0_valid_q <= 1'b0;
                            window_issue_count_q <= 4'd0;
                            pool_chunk_select_q <= 1'b0;
                            pool_chunk_full_select_q <= 1'b0;
                            accumulation_retire_address_q <=
                                descriptor_ext2[61:49];
                            prefetch_sequence_q <=
                                descriptor_base[57:54] == MODE_COPY;
                            bias_sequence_q <= 1'b0;
                            pool_scale_pending_q <= 1'b0;
                            window_done_pending_q <= 1'b0;
                            retire_stream_active_q <= 1'b0;
                            emit_word_index_q <= 12'd0;
                            emit_packet_lanes_q <= 4'd0;
                            emit_packet_finishes_group_q <= 1'b0;
                            emit_packet_last_q <= 1'b0;
                            emit_prefetch_request_q <= 1'b0;
                            pair_prefetch_step_q <= 2'd0;
                            pair_issue_phase_q <= 1'b0;
                            pair_block_base_q <= 12'd0;
                            pair_block_samples_q <=
                                (descriptor_base[35:24] >= 12'd16) ?
                                5'd16 :
                                {1'b0, descriptor_base[27:24]};
                            pair_block_destination_q <=
                                descriptor_ext2[61:49];
                            pair_bias_pending_q <= 1'b0;
                            pair_retire_pending_q <= 1'b0;
                            window_chain_pending_q <= 1'b0;
                            state_q <= STATE_FIRST_WEIGHT_REQ;
                        end
                    end
                end

                STATE_FIRST_WEIGHT_REQ: begin
                    if (service_request_ready) begin
                        state_q <= STATE_FIRST_WEIGHT_WAIT;
                    end
                end

                STATE_FIRST_WEIGHT_WAIT: begin
                    if (emit_response_fire) begin
                        emit_packet_lanes_q <= emit_chunk_lanes[3:0];
                        emit_packet_finishes_group_q <=
                            emit_finishes_group;
                        emit_packet_last_q <= emit_final_chunk;
                        if (emit_has_next) begin
                            emit_prefetch_request_q <= 1'b1;
                            emit_prefetch_address_q <=
                                emit_next_source_address;
                            emit_prefetch_lanes_q <=
                                emit_next_chunk_lanes;
                        end
                        state_q <= STATE_WINDOW_RUN;
                    end
                    else if (copy_response_complete) begin
                        if (copy_has_after_response) begin
                            sequence_i0_q <= sequence_i0_q +
                                {10'd0, copy_advance_count};
                            source_address_q <= copy_next_source_address;
                            gather_source_address_q <=
                                copy_next_source_address;
                            destination_address_q <=
                                copy_next_destination_address;
                            retire_destination_q <=
                                copy_next_destination_address;
                        end
                        else begin
                            state_q <= STATE_COMPLETE;
                        end
                    end
                    else if (!copy_mode && service_tile_response_valid) begin
                        if (tile_dot_mode_q) begin
                            tile_phase_q <= TILE_SOURCE0_REQ;
                            tile_complete_pending_q <= 1'b0;
                            kernel_row_q <= 4'd0;
                            kernel_column_q <= 4'd0;
                            kernel_result_count_q <= 6'd0;
                            source_i0_base_q <= source_address_q;
                            weight_i0_base_q <= weight_address_q;
                            retire_destination_q <= destination_address_q;
                            kernel_column_base_q <= weight_address_q;
                            kernel_destination_base_q <=
                                destination_address_q;
                            state_q <= STATE_TILE_DOT;
                        end
                        else if (pair_mode_q) begin
                            pair_prefetch_step_q <= 2'd0;
                            prefetch_pending_q <= 1'b0;
                            state_q <= STATE_PAIR_PREFETCH;
                        end
                        else if (generic_mode) begin
                            gather_source_pending_q <= 1'b0;
                            gather_request_count_q <= 12'd0;
                            gather_issue_count_q <= 12'd0;
                            gather_source_address_q <= source_address_q;
                            source_buffer0_valid_q <= 1'b0;
                            state_q <= STATE_GENERIC_SOURCE;
                        end
                        else if (kernel_active_q) begin
                            active_weight_slot_q <= 1'b1;
                            kernel_stat_step_q <= 5'd0;
                            kernel_tri_step_q <= 5'd0;
                            kernel_backsub_step_q <= 5'd0;
                            kernel_row_q <= 4'd0;
                            kernel_column_q <= 4'd0;
                            kernel_chunk_q <= 5'd0;
                            kernel_index_q <= 6'd0;
                            kernel_request_count_q <= 6'd0;
                            kernel_response_count_q <= 6'd0;
                            kernel_result_count_q <= 6'd0;
                            kernel_chain_accepted_q <= 1'b0;
                            kernel_chunk_base_q <=
                                (kernel_kind_q == KERNEL_BACKSUB) ?
                                destination_address_q : source_address_q;
                            kernel_column_base_q <=
                                (kernel_kind_q == KERNEL_BACKSUB) ?
                                (weight_address_q + weight_stride0_q) :
                                source_address_q;
                            kernel_destination_base_q <=
                                destination_address_q;
                            source_buffer0_valid_q <= 1'b0;
                            solve_stream_resident_valid_q <= 1'b0;
                            if (kernel_kind_q == KERNEL_RECURRENCE) begin
                                iir_samples_remaining_q <= 12'd0;
                                iir_run_step_q <= 4'd0;
                                iir_restart_gap_q <= 2'd0;
                                iir_terminal_request_count_q <= 4'd0;
                                iir_terminal_response_count_q <= 4'd0;
                                iir_history_valid_q <= 6'd0;
                                iir_source_pending_q <= 1'b0;
                                iir_prefetch_valid_q <= 1'b0;
                                iir_late_valid_q <= 1'b0;
                                iir_drain_q <= 1'b0;
                                iir_block_wait_q <= 1'b0;
                            end
                            state_q <= STATE_KERNEL;
                        end
                        else begin
                            state_q <= STATE_WINDOW_START;
                        end
                    end
                end

                STATE_TILE_DOT: begin
                    if (tile_reduce_return)
                        kernel_result_count_q <=
                            kernel_result_count_q + 6'd1;
                    case (tile_phase_q)
                        TILE_SOURCE0_REQ: begin
                            if (service_request_valid &&
                                service_request_ready)
                                tile_phase_q <= TILE_SOURCE0_WAIT;
                        end
                        TILE_SOURCE0_WAIT: begin
                            if (service_tile_response_accept)
                                tile_phase_q <= TILE_SOURCE1_REQ;
                        end
                        TILE_SOURCE1_REQ: begin
                            if (service_request_valid &&
                                service_request_ready)
                                tile_phase_q <= TILE_SOURCE1_WAIT;
                        end
                        TILE_SOURCE1_WAIT: begin
                            if (service_tile_response_accept)
                                tile_phase_q <= TILE_WEIGHT_REQ;
                        end
                        TILE_WEIGHT_REQ: begin
                            if (service_request_valid &&
                                service_request_ready)
                                tile_phase_q <= TILE_WEIGHT_WAIT;
                        end
                        TILE_WEIGHT_WAIT: begin
                            if (service_tile_response_accept)
                                tile_phase_q <= TILE_REAL_ISSUE;
                        end
                        TILE_REAL_ISSUE: begin
                            if (tile_apx_request_fire)
                                tile_phase_q <= TILE_IMAG_ISSUE;
                        end
                        TILE_IMAG_ISSUE: begin
                            if (tile_apx_request_fire) begin
                                if ((kernel_column_q + 4'd1) <
                                    bound1_q[3:0]) begin
                                    kernel_column_q <=
                                        kernel_column_q + 4'd1;
                                    kernel_column_base_q <=
                                        kernel_column_base_q +
                                        weight_stride1_q;
                                    tile_phase_q <= TILE_WEIGHT_REQ;
                                end
                                else begin
                                    tile_phase_q <= TILE_DOT_WAIT;
                                end
                            end
                        end
                        TILE_DOT_WAIT: begin
                            if (tile_reduce_return &&
                                ((kernel_result_count_q + 6'd1) >=
                                 {1'b0, bound1_q[3:0], 1'b0}))
                                tile_phase_q <= TILE_RETIRE_REAL;
                        end
                        TILE_RETIRE_REAL: begin
                            if (retire_ack)
                                tile_phase_q <= TILE_RETIRE_IMAG;
                        end
                        TILE_RETIRE_IMAG: begin
                            if (retire_ack) begin
                                kernel_result_count_q <= 6'd0;
                                if ((kernel_row_q + 4'd1) <
                                    bound0_q[3:0]) begin
                                    tile_complete_pending_q <= 1'b0;
                                    kernel_row_q <= kernel_row_q + 4'd1;
                                    kernel_column_q <= 4'd0;
                                    source_i0_base_q <=
                                        source_i0_base_q + source_stride0_q;
                                    weight_i0_base_q <=
                                        weight_i0_base_q + weight_stride0_q;
                                    retire_destination_q <=
                                        retire_destination_q +
                                        destination_stride0_q;
                                    kernel_column_base_q <=
                                        weight_i0_base_q + weight_stride0_q;
                                    kernel_destination_base_q <=
                                        retire_destination_q +
                                        destination_stride0_q;
                                    tile_phase_q <= TILE_RETIRE_DRAIN;
                                end
                                else begin
                                    tile_complete_pending_q <= 1'b1;
                                    tile_phase_q <= TILE_RETIRE_DRAIN;
                                end
                            end
                        end
                        TILE_RETIRE_DRAIN: begin
                            if (!(|retire_a_valid) &&
                                !(|retire_b_valid)) begin
                                if (tile_complete_pending_q)
                                    state_q <= STATE_COMPLETE;
                                else
                                    tile_phase_q <= TILE_SOURCE0_REQ;
                            end
                        end
                        default: tile_phase_q <= TILE_SOURCE0_REQ;
                    endcase
                end

                STATE_PAIR_PREFETCH: begin
                    if (service_request_valid && service_request_ready)
                        prefetch_pending_q <= 1'b1;
                    if (service_tile_response_valid) begin
                        prefetch_pending_q <= 1'b0;
                        if (pair_prefetch_step_q == 2'd0) begin
                            if (flags_q[2]) begin
                                pair_prefetch_step_q <= 2'd1;
                            end
                            else begin
                                pair_bias0_q <= 16'd0;
                                pair_bias1_q <= 16'd0;
                                pair_issue_phase_q <= 1'b0;
                                pair_block_base_q <= 12'd0;
                                pair_block_destination_q <=
                                    destination_address_q;
                                gather_source_pending_q <= 1'b0;
                                gather_request_count_q <= 12'd0;
                                gather_issue_count_q <= 12'd0;
                                gather_result_count_q <= 12'd0;
                                gather_source_address_q <= source_address_q;
                                source_buffer0_valid_q <= 1'b0;
                                chunk_index_q <= 5'd0;
                                pair_bias_pending_q <= 1'b0;
                                pair_retire_pending_q <= 1'b0;
                                state_q <= STATE_PAIR_RUN;
                            end
                        end
                        else if (pair_prefetch_step_q == 2'd1) begin
                            pair_bias0_q <= service_response_data[15:0];
                            pair_prefetch_step_q <= 2'd2;
                        end
                        else begin
                            pair_bias1_q <= service_response_data[15:0];
                            pair_issue_phase_q <= 1'b0;
                            pair_block_base_q <= 12'd0;
                            pair_block_destination_q <=
                                destination_address_q;
                            gather_source_pending_q <= 1'b0;
                            gather_request_count_q <= 12'd0;
                            gather_issue_count_q <= 12'd0;
                            gather_result_count_q <= 12'd0;
                            gather_source_address_q <= source_address_q;
                            source_buffer0_valid_q <= 1'b0;
                            chunk_index_q <= 5'd0;
                            pair_bias_pending_q <= 1'b0;
                            pair_retire_pending_q <= 1'b0;
                            state_q <= STATE_PAIR_RUN;
                        end
                    end
                end

                STATE_PAIR_RUN: begin
                    if (source_response_accept)
                        gather_source_pending_q <= 1'b0;
                    if (service_request_valid && service_request_ready &&
                        service_request_source) begin
                        gather_source_pending_q <= 1'b1;
                        gather_request_count_q <=
                            gather_request_count_q + 12'd1;
                        gather_source_address_q <=
                            gather_source_address_q + source_stride1_q;
                    end
                    if (pair_apx_request_fire) begin
                        if (pair_issue_phase_q) begin
                            pair_issue_phase_q <= 1'b0;
                            gather_issue_count_q <=
                                gather_issue_count_q + 12'd1;
                        end
                        else begin
                            pair_issue_phase_q <= 1'b1;
                        end
                    end
                    if (apx_reduce_valid) begin
                        gather_result_count_q <=
                            gather_result_count_q + 12'd1;
                        if ((gather_result_count_q + 12'd1) >=
                            {6'd0, pair_total_results}) begin
                            chunk_index_q <= 5'd0;
                            pair_bias_pending_q <= 1'b0;
                            pair_retire_pending_q <= 1'b0;
                            state_q <= STATE_PAIR_BIAS;
                        end
                    end
                end

                STATE_PAIR_BIAS: begin
                    if (pair_bias_request_fire)
                        pair_bias_pending_q <= 1'b1;
                    if (pair_add_return) begin
                        pair_bias_pending_q <= 1'b0;
                        pair_retire_pending_q <= 1'b1;
                    end
                    if (retire_ack &&
                        (pair_retire_pending_q || !flags_q[2])) begin
                        pair_retire_pending_q <= 1'b0;
                        if (({2'd0, chunk_index_q} + 7'd1) >=
                            {4'd0, pair_total_chunks}) begin
                            chunk_index_q <= 5'd0;
                            if ((pair_block_base_q +
                                 {7'd0, pair_block_samples_q}) >=
                                bound1_q) begin
                                state_q <= STATE_COMPLETE;
                            end
                            else begin
                                pair_block_base_q <=
                                    pair_block_base_q + 12'd16;
                                pair_block_samples_q <=
                                    pair_next_block_samples;
                                pair_block_destination_q <=
                                    pair_block_destination_q +
                                    (destination_stride1_q << 5'd4);
                                gather_source_pending_q <= 1'b0;
                                gather_request_count_q <= 12'd0;
                                gather_issue_count_q <= 12'd0;
                                gather_result_count_q <= 12'd0;
                                source_buffer0_valid_q <= 1'b0;
                                pair_issue_phase_q <= 1'b0;
                                state_q <= STATE_PAIR_RUN;
                            end
                        end
                        else begin
                            chunk_index_q <= chunk_index_q + 5'd1;
                        end
                    end
                end

                STATE_WINDOW_START: begin
                    if (!same_pad || window_start_ready) begin
                        retire_destination_q <= destination_address_q;
                        result_chunk_q <= 128'd0;
                        chunk_word_count_q <= 4'd0;
                        chunk_index_q <= 5'd0;
                        chunk_lane_count_q <= 4'd8;
                        pool_chunk_select_q <= 1'b0;
                        pool_chunk_full_select_q <= 1'b0;
                        window_issue_count_q <= 4'd0;
                        window_issue_block_q <= 1'b0;
                        chunk_full_q <= 1'b0;
                        accumulation_add_pending_q <= 1'b0;
                        bias_add_pending_q <= 1'b0;
                        window_done_pending_q <= 1'b0;
                        produced_chunk_count_q <= 5'd0;
                        retire_stream_word_index_q <= 12'd0;
                        accumulation_retire_address_q <=
                            destination_address_q;
                        gather_source_pending_q <= 1'b0;
                        gather_request_count_q <= 12'd0;
                        gather_issue_count_q <= 12'd0;
                        gather_result_count_q <= 12'd0;
                        gather_source_address_q <= source_address_q;
                        source_buffer0_valid_q <= 1'b0;
                        prefetch_sequence_q <= sequence_has_next &&
                            (!group_diagonal || sequence_advances_outer) &&
                            !sequence_reuses_parameters;
                        bias_sequence_q <= bias_final_plane;
                        retire_stream_active_q <=
                            final_accumulation_plane &&
                            !aligned_accumulation_retire &&
                            !bias_enabled;
                        window_chain_pending_q <= 1'b0;
                        state_q <= STATE_WINDOW_RUN;
                    end
                end

                STATE_WINDOW_RUN: begin
                    if (emit_mode_q) begin
                        if (emit_packet_done) begin
                            if (emit_packet_last_q) begin
                                state_q <= STATE_COMPLETE;
                            end
                            else begin
                                if (emit_packet_finishes_group_q) begin
                                    sequence_i0_q <=
                                        sequence_i0_q + 12'd1;
                                    emit_word_index_q <= 12'd0;
                                    source_i0_base_q <=
                                        source_i0_base_q +
                                        source_stride0_q;
                                end
                                else begin
                                    emit_word_index_q <=
                                        emit_word_index_q +
                                        {8'd0, emit_packet_lanes_q};
                                end
                                if (emit_packet_finishes_group_q)
                                    source_address_q <=
                                        source_i0_base_q + source_stride0_q;
                                else
                                    source_address_q <= source_address_q +
                                        (source_stride1_q << 5'd3);
                                state_q <= STATE_FIRST_WEIGHT_WAIT;
                            end
                        end
                    end
                    else begin
                    if (source_response_accept &&
                        (!pool_scalar_bypass || service_response_last))
                        gather_source_pending_q <= 1'b0;
                    if (service_request_valid && service_request_ready) begin
                        if (service_request_source) begin
                            gather_source_pending_q <= 1'b1;
                            if (pool_scalar_bypass) begin
                                gather_request_count_q <= bound1_q;
                            end
                            else begin
                                gather_request_count_q <=
                                    gather_request_count_q + 12'd1;
                                gather_source_address_q <=
                                    gather_source_address_q + source_stride1_q;
                            end
                        end
                        else if (service_request_bias)
                            bias_prefetch_pending_q <= 1'b1;
                        else
                            prefetch_pending_q <= 1'b1;
                    end
                    if (service_tile_response_valid &&
                        (operand_response_role_q !=
                         OPERAND_ROLE_SOURCE)) begin
                        if (operand_response_role_q ==
                            OPERAND_ROLE_BIAS) begin
                            bias_value_q <= service_response_data[15:0];
                            bias_prefetch_pending_q <= 1'b0;
                            bias_prefetch_ready_q <= 1'b1;
                        end
                        else begin
                            prefetch_pending_q <= 1'b0;
                            prefetch_ready_q <= 1'b1;
                        end
                    end
                    if (window_chain_start_fire)
                        window_chain_pending_q <= 1'b1;
                    if (gather_source_fire) begin
                        gather_issue_count_q <=
                            gather_issue_count_q + 12'd1;
                    end
                    if (compute_issue_fire && accumulation_plane &&
                        !scalar_post_enabled) begin
                        if (window_issue_count_q == 4'd7) begin
                            window_issue_count_q <= 4'd0;
                            window_issue_block_q <=
                                !pool_chunk_overlap;
                        end
                        else begin
                            window_issue_count_q <=
                                window_issue_count_q + 4'd1;
                        end
                    end
                    if (!same_pad && compute_result_valid)
                        gather_result_count_q <=
                            gather_result_count_q + 12'd1;
                    if (compute_result_valid &&
                        (accumulation_enabled || bias_enabled) &&
                        !scalar_post_enabled) begin
                        if (!pool_chunk_overlap ||
                            !pool_chunk_select_q)
                            result_chunk_q[
                                chunk_word_count_q*16 +: 16] <=
                                compute_result_data;
                        if (result_chunk_complete) begin
                            chunk_word_count_q <= 4'd0;
                            chunk_lane_count_q <= completed_chunk_lanes;
                            if (pool_chunk_overlap) begin
                                pool_chunk_full_select_q <=
                                    pool_chunk_select_q;
                                pool_chunk_select_q <=
                                    ~pool_chunk_select_q;
                            end
                            if (first_sequence_plane) begin
                                chunk_index_q <= chunk_index_q + 5'd1;
                            end
                            else begin
                                chunk_full_q <= 1'b1;
                            end
                        end
                        else begin
                            chunk_word_count_q <=
                                chunk_word_count_q + 4'd1;
                        end
                    end
                    else if (compute_result_valid && !pool_scale_enabled) begin
                        retire_destination_q <= retire_destination_q +
                            destination_stride1_q;
                    end
                    if (pool_scale_request_fire)
                        window_issue_block_q <= 1'b1;
                    if (pool_scale_request_fire)
                        pool_scale_pending_q <= 1'b1;
                    if (pool_scale_result_accepted)
                        pool_scale_pending_q <= 1'b0;
                    if (apx_add_request_fire) begin
                        chunk_full_q <= 1'b0;
                        accumulation_add_pending_q <= 1'b1;
                        bias_add_pending_q <= 1'b0;
                    end
                    if (accumulation_pair_return) begin
                        accumulation_add_pending_q <= 1'b0;
                        window_issue_block_q <= pool_scale_enabled &&
                            final_accumulation_plane &&
                            (!pool_chunk_overlap ||
                             window_done_pending_q);
                        chunk_index_q <= chunk_index_q + 5'd1;
                        if (final_accumulation_plane && !bias_enabled &&
                            !pool_scale_enabled) begin
                            if (aligned_accumulation_retire) begin
                                accumulation_retire_address_q <=
                                    accumulation_retire_address_q +
                                    {9'd0, accumulation_return_lanes};
                            end
                            else begin
                                produced_chunk_count_q <=
                                    produced_chunk_count_q + 5'd1;
                            end
                        end
                    end
                    if (apx_post_add_result_valid &&
                        apx_post_add_result_tag[15] &&
                        retire_ready) begin
                        accumulation_retire_address_q <=
                            accumulation_retire_address_q +
                            destination_stride1_q;
                    end
                    if (scalar_post_last_return && bias_final_plane &&
                        !(window_chain_pending_q && sequence_has_next &&
                          sequence_reuses_parameters))
                        bias_prefetch_ready_q <= 1'b0;
                    if (pool_scale_product_valid) begin
                        if (accumulation_enabled &&
                            aligned_accumulation_retire) begin
                            accumulation_retire_address_q <=
                                accumulation_retire_address_q +
                                {9'd0, accumulation_return_lanes};
                        end
                        else if (!accumulation_enabled) begin
                            retire_destination_q <= retire_destination_q +
                                destination_stride1_q;
                        end
                    end
                    if (scratch_pool_scale_write)
                        produced_chunk_count_q <=
                            produced_chunk_count_q + 5'd1;
                    if (pool_scale_enabled &&
                        (retire_ack || scratch_pool_scale_write))
                        window_issue_block_q <= 1'b0;
                    if (retire_stream_available && retire_ready) begin
                        if ((retire_stream_word_index_q + 12'd1) >=
                            bound1_q) begin
                            retire_stream_active_q <= 1'b0;
                        end
                        else begin
                            retire_stream_word_index_q <=
                                retire_stream_word_index_q + 12'd1;
                            accumulation_retire_address_q <=
                                accumulation_retire_address_q +
                                destination_stride1_q;
                        end
                    end
                    if (compute_done &&
                        (accumulation_plane || bias_final_plane ||
                         pool_scale_enabled))
                        window_done_pending_q <= 1'b1;
                    if (window_sequence_complete) begin
                        if (window_chain_pending_q) begin
                            retire_destination_q <=
                                next_destination_address;
                            result_chunk_q <= 128'd0;
                            chunk_word_count_q <= 4'd0;
                            chunk_index_q <= 5'd0;
                            chunk_lane_count_q <= 4'd8;
                            window_issue_count_q <= 4'd0;
                            window_issue_block_q <= 1'b0;
                            chunk_full_q <= 1'b0;
                            accumulation_add_pending_q <= 1'b0;
                            bias_add_pending_q <= 1'b0;
                            window_done_pending_q <= 1'b0;
                            produced_chunk_count_q <= 5'd0;
                            retire_stream_word_index_q <= 12'd0;
                            accumulation_retire_address_q <=
                                next_destination_address;
                            gather_source_pending_q <= 1'b0;
                            gather_request_count_q <= 12'd0;
                            gather_issue_count_q <= 12'd0;
                            gather_result_count_q <= 12'd0;
                            gather_source_address_q <=
                                next_source_address;
                            source_buffer0_valid_q <= 1'b0;
                            prefetch_sequence_q <=
                                next_sequence_has_next &&
                                (!group_diagonal ||
                                 next_sequence_advances_outer) &&
                                !next_sequence_reuses_parameters;
                            bias_sequence_q <=
                                window_chain_reuses_parameters &&
                                bias_final_plane;
                            retire_stream_active_q <=
                                next_final_accumulation_plane &&
                                !aligned_accumulation_retire;
                            window_chain_pending_q <= 1'b0;
                        end
                        if (bias_final_plane && !scalar_post_enabled) begin
                            if (bias_prefetch_ready_q ||
                                (service_tile_response_valid &&
                                 bias_prefetch_pending_q)) begin
                                window_done_pending_q <= 1'b0;
                                chunk_index_q <= 5'd0;
                                accumulation_add_pending_q <= 1'b0;
                                bias_add_pending_q <= 1'b0;
                                produced_chunk_count_q <= 5'd0;
                                retire_stream_word_index_q <= 12'd0;
                                accumulation_retire_address_q <=
                                    destination_address_q;
                                retire_stream_active_q <=
                                    !aligned_accumulation_retire;
                                bias_prefetch_ready_q <= 1'b0;
                                bias_chunk_ready_q <= 1'b0;
                                state_q <= STATE_BIAS_RUN;
                            end
                        end
                        else if (sequence_has_next) begin
                            window_done_pending_q <= 1'b0;
                            if (group_diagonal &&
                                !sequence_advances_outer) begin
                                sequence_i2_q <= sequence_i2_q - 12'd1;
                                source_address_q <= next_source_address;
                                weight_address_q <= next_weight_address;
                                destination_address_q <=
                                    next_destination_address;
                                retire_destination_q <=
                                    next_destination_address;
                                state_q <= window_chain_pending_q ?
                                    STATE_WINDOW_RUN : STATE_WINDOW_START;
                            end
                            else if (pool_mode) begin
                                if (sequence_advances_outer) begin
                                    sequence_i0_q <= sequence_i0_q + 12'd1;
                                    sequence_i2_q <= bound2_q;
                                    source_i0_base_q <= next_source_i0_base;
                                    weight_i0_base_q <= next_weight_i0_base;
                                end
                                else begin
                                    sequence_i2_q <= sequence_i2_q - 12'd1;
                                end
                                source_address_q <= next_source_address;
                                weight_address_q <= next_weight_address;
                                destination_address_q <=
                                    next_destination_address;
                                retire_destination_q <=
                                    next_destination_address;
                                // Pool planes share one resident reciprocal
                                // and need no window handshake.  Rearm the
                                // scalar stream in place so adjacent planes
                                // do not pay a pure reset-state bubble.
                                result_chunk_q <= 128'd0;
                                chunk_word_count_q <= 4'd0;
                                chunk_index_q <= 5'd0;
                                chunk_lane_count_q <= 4'd8;
                                pool_chunk_select_q <= 1'b0;
                                pool_chunk_full_select_q <= 1'b0;
                                window_issue_count_q <= 4'd0;
                                window_issue_block_q <= 1'b0;
                                chunk_full_q <= 1'b0;
                                accumulation_add_pending_q <= 1'b0;
                                bias_add_pending_q <= 1'b0;
                                produced_chunk_count_q <= 5'd0;
                                retire_stream_word_index_q <= 12'd0;
                                accumulation_retire_address_q <=
                                    next_destination_address;
                                gather_source_pending_q <= 1'b0;
                                gather_request_count_q <= 12'd0;
                                gather_issue_count_q <= 12'd0;
                                gather_result_count_q <= 12'd0;
                                gather_source_address_q <=
                                    next_source_address;
                                source_buffer0_valid_q <= 1'b0;
                                prefetch_sequence_q <=
                                    next_sequence_has_next;
                                bias_sequence_q <= bias_enabled &&
                                    next_final_accumulation_plane;
                                retire_stream_active_q <=
                                    next_final_accumulation_plane &&
                                    !aligned_accumulation_retire &&
                                    !bias_enabled;
                                window_chain_pending_q <= 1'b0;
                                state_q <= STATE_WINDOW_RUN;
                            end
                            else if (sequence_reuses_parameters) begin
                                sequence_i0_q <= sequence_i0_q + 12'd1;
                                sequence_i2_q <= bound2_q;
                                source_i0_base_q <= next_source_i0_base;
                                weight_i0_base_q <= next_weight_i0_base;
                                source_address_q <= next_source_address;
                                weight_address_q <= next_weight_address;
                                destination_address_q <=
                                    next_destination_address;
                                retire_destination_q <=
                                    next_destination_address;
                                state_q <= window_chain_pending_q ?
                                    STATE_WINDOW_RUN : STATE_WINDOW_START;
                            end
                            else if (prefetch_ready_q ||
                                     service_tile_response_valid) begin
                                active_weight_slot_q <=
                                    ~active_weight_slot_q;
                                if (sequence_advances_outer) begin
                                    sequence_i0_q <= sequence_i0_q + 12'd1;
                                    sequence_i2_q <= bound2_q;
                                    source_i0_base_q <= next_source_i0_base;
                                    weight_i0_base_q <= next_weight_i0_base;
                                end
                                else begin
                                    sequence_i2_q <= sequence_i2_q - 12'd1;
                                end
                                source_address_q <= next_source_address;
                                weight_address_q <= next_weight_address;
                                destination_address_q <=
                                    next_destination_address;
                                retire_destination_q <=
                                    next_destination_address;
                                prefetch_ready_q <= 1'b0;
                                state_q <= window_chain_pending_q ?
                                    STATE_WINDOW_RUN : STATE_WINDOW_START;
                            end
                            else begin
                                if (sequence_advances_outer) begin
                                    sequence_i0_q <= sequence_i0_q + 12'd1;
                                    sequence_i2_q <= bound2_q;
                                    source_i0_base_q <= next_source_i0_base;
                                    weight_i0_base_q <= next_weight_i0_base;
                                end
                                else begin
                                    sequence_i2_q <= sequence_i2_q - 12'd1;
                                end
                                source_address_q <= next_source_address;
                                weight_address_q <= next_weight_address;
                                destination_address_q <=
                                    next_destination_address;
                                retire_destination_q <=
                                    next_destination_address;
                                state_q <= STATE_NEXT_WEIGHT_WAIT;
                            end
                        end
                        else begin
                            window_done_pending_q <= 1'b0;
                            window_chain_pending_q <= 1'b0;
                            state_q <= STATE_COMPLETE;
                        end
                    end
                    end
                end

                STATE_BIAS_RUN: begin
                    if (!bias_chunk_ready_q &&
                        !accumulation_add_pending_q &&
                        ({4'd0, chunk_index_q, 3'd0} < bound1_q)) begin
                        bias_chunk_ready_q <= 1'b1;
                    end
                    if (apx_add_request_fire) begin
                        accumulation_add_pending_q <= 1'b1;
                        bias_add_pending_q <= 1'b1;
                        bias_chunk_ready_q <= 1'b0;
                    end
                    if (accumulation_pair_return) begin
                        accumulation_add_pending_q <= 1'b0;
                        bias_add_pending_q <= 1'b0;
                        chunk_index_q <= chunk_index_q + 5'd1;
                        if (aligned_accumulation_retire) begin
                            accumulation_retire_address_q <=
                                accumulation_retire_address_q +
                                {9'd0, accumulation_return_lanes};
                        end
                        else begin
                            produced_chunk_count_q <=
                                produced_chunk_count_q + 5'd1;
                        end
                    end
                    if (retire_stream_available && retire_ready) begin
                        if ((retire_stream_word_index_q + 12'd1) >=
                            bound1_q) begin
                            retire_stream_active_q <= 1'b0;
                        end
                        else begin
                            retire_stream_word_index_q <=
                                retire_stream_word_index_q + 12'd1;
                            accumulation_retire_address_q <=
                                accumulation_retire_address_q +
                                destination_stride1_q;
                        end
                    end
                    if (bias_epilogue_complete) begin
                        bias_prefetch_pending_q <= 1'b0;
                        bias_prefetch_ready_q <= 1'b0;
                        bias_chunk_ready_q <= 1'b0;
                        if (sequence_has_next) begin
                            if (prefetch_ready_q) begin
                                active_weight_slot_q <=
                                    ~active_weight_slot_q;
                                if (sequence_advances_outer) begin
                                    sequence_i0_q <= sequence_i0_q + 12'd1;
                                    sequence_i2_q <= bound2_q;
                                    source_i0_base_q <= next_source_i0_base;
                                    weight_i0_base_q <= next_weight_i0_base;
                                end
                                else begin
                                    sequence_i2_q <= sequence_i2_q - 12'd1;
                                end
                                source_address_q <= next_source_address;
                                weight_address_q <= next_weight_address;
                                destination_address_q <=
                                    next_destination_address;
                                retire_destination_q <=
                                    next_destination_address;
                                prefetch_ready_q <= 1'b0;
                                state_q <= STATE_WINDOW_START;
                            end
                            else begin
                                if (sequence_advances_outer) begin
                                    sequence_i0_q <= sequence_i0_q + 12'd1;
                                    sequence_i2_q <= bound2_q;
                                    source_i0_base_q <= next_source_i0_base;
                                    weight_i0_base_q <= next_weight_i0_base;
                                end
                                else begin
                                    sequence_i2_q <= sequence_i2_q - 12'd1;
                                end
                                source_address_q <= next_source_address;
                                weight_address_q <= next_weight_address;
                                destination_address_q <=
                                    next_destination_address;
                                retire_destination_q <=
                                    next_destination_address;
                                state_q <= STATE_NEXT_WEIGHT_WAIT;
                            end
                        end
                        else begin
                            state_q <= STATE_COMPLETE;
                        end
                    end
                end

                STATE_NEXT_WEIGHT_WAIT: begin
                    if (service_request_valid && service_request_ready)
                        prefetch_pending_q <= 1'b1;
                    if (service_tile_response_valid) begin
                        active_weight_slot_q <= ~active_weight_slot_q;
                        prefetch_pending_q <= 1'b0;
                        prefetch_ready_q <= 1'b0;
                        state_q <= generic_mode ?
                            STATE_GENERIC_SOURCE : STATE_WINDOW_START;
                    end
                end

                STATE_GENERIC_SOURCE: begin
                    if (generic_source_accept)
                        gather_source_pending_q <= 1'b0;
                    if (service_request_valid && service_request_ready) begin
                        gather_source_pending_q <= 1'b1;
                        gather_request_count_q <=
                            gather_request_count_q + 12'd1;
                        gather_source_address_q <=
                            gather_source_address_q + source_stride1_q;
                    end
                    if (generic_apx_request_fire) begin
                        gather_issue_count_q <=
                            gather_issue_count_q + 12'd1;
                        state_q <= vector_add_mode_q ?
                            STATE_VECTOR_RESULT : STATE_EWISE_RESULT;
                    end
                end

                STATE_EWISE_RESULT: begin
                    if (apx_product_valid && retire_ready)
                        state_q <= STATE_GENERIC_ACK;
                end

                STATE_VECTOR_RESULT: begin
                    if (apx_pair_valid && retire_ready)
                        state_q <= STATE_GENERIC_ACK;
                end

                STATE_GENERIC_ACK: begin
                    if (retire_ack) begin
                        if (gather_request_count_q < bound1_q) begin
                            retire_destination_q <=
                                retire_destination_q +
                                destination_stride1_q;
                            if (weight_stride1_q != 13'd0) begin
                                weight_address_q <=
                                    weight_address_q +
                                    weight_stride1_q;
                                state_q <= STATE_NEXT_WEIGHT_WAIT;
                            end
                            else begin
                                state_q <= STATE_GENERIC_SOURCE;
                            end
                        end
                        else if ((sequence_i0_q + 12'd1) <
                                 bound0_q) begin
                            sequence_i0_q <= sequence_i0_q + 12'd1;
                            gather_request_count_q <= 12'd0;
                            source_i0_base_q <=
                                source_i0_base_q + source_stride0_q;
                            source_address_q <=
                                source_i0_base_q + source_stride0_q;
                            gather_source_address_q <=
                                source_i0_base_q + source_stride0_q;
                            weight_i0_base_q <=
                                weight_i0_base_q + weight_stride0_q;
                            weight_address_q <=
                                weight_i0_base_q + weight_stride0_q;
                            destination_address_q <=
                                destination_address_q +
                                destination_stride0_q;
                            retire_destination_q <=
                                destination_address_q +
                                destination_stride0_q;
                            state_q <= (weight_stride0_q != 13'd0) ?
                                STATE_NEXT_WEIGHT_WAIT :
                                STATE_GENERIC_SOURCE;
                        end
                        else begin
                            state_q <= STATE_COMPLETE;
                        end
                    end
                end

                STATE_KERNEL: begin
                    // One shared kernel context owns all dense/matrix modes.
                    // Unsupported kinds remain here; they never fall through
                    // into the generic window datapath.
                    if (kernel_schedule_advance) begin
                        case (kernel_kind_q)
                            KERNEL_PAIRWISE_STAT:
                                kernel_stat_step_q <=
                                    kernel_schedule_next_phase;
                            KERNEL_TRIANGULAR:
                                kernel_tri_step_q <=
                                    kernel_schedule_next_phase;
                            KERNEL_BACKSUB:
                                kernel_backsub_step_q <=
                                    kernel_schedule_next_phase;
                            default: begin
                                // Recurrence owns iir_phase_q instead.
                            end
                        endcase
                    end
                    if (kernel_kind_q == KERNEL_PAIRWISE_STAT) begin
                        if (kernel_stream_completion)
                            kernel_result_count_q <=
                                kernel_result_count_q + 6'd1;
                        case (kernel_stat_step_q)
                            STAT_MEAN_STREAM: begin
                                if (kernel_stat_service_fire) begin
                                    kernel_request_count_q <=
                                        kernel_request_count_q + 6'd1;
                                end
                                if (kernel_apx_request_fire)
                                    kernel_response_count_q <=
                                        kernel_response_count_q + 6'd1;
                                if (kernel_stream_completion &&
                                    ((kernel_result_count_q + 6'd1) >=
                                     {2'd0, bound0_q[3:0]})) begin
                                    if (({7'd0, kernel_chunk_q} + 12'd1) >=
                                        ((bound1_q + 12'd15) >> 5'd4)) begin
                                        kernel_result_count_q <= 6'd0;
                                        kernel_stat_step_q <=
                                            STAT_MEAN_SCALE_LOAD;
                                    end
                                    else begin
                                        kernel_chunk_q <=
                                            kernel_chunk_q + 5'd1;
                                        kernel_request_count_q <=
                                            kernel_stat_service_fire ?
                                            6'd1 : 6'd0;
                                        kernel_response_count_q <= 6'd0;
                                        kernel_result_count_q <= 6'd0;
                                        kernel_chunk_base_q <=
                                            kernel_chunk_base_q +
                                            (source_stride1_q << 5'd4);
                                    end
                                end
                            end
                            STAT_MEAN_SCALE_LOAD: begin
                                // Common scheduler: local -> APX issue.
                            end
                            STAT_MEAN_SCALE_ISSUE: begin
                                // Common scheduler: APX request handshake.
                            end
                            STAT_MEAN_SCALE_WAIT: begin
                                // Common scheduler: tagged product return.
                            end
                            STAT_MEAN_RETIRE: begin
                                if (kernel_retire_complete) begin
                                    kernel_stat_step_q <=
                                        kernel_stat_service_fire ?
                                        STAT_PAIR_ROW_WAIT :
                                        STAT_PAIR_ROW_REQ;
                                    kernel_row_q <= 4'd0;
                                    kernel_column_q <= 4'd0;
                                    kernel_chunk_q <= 5'd0;
                                    kernel_index_q <= 6'd0;
                                    kernel_result_count_q <= 6'd0;
                                    kernel_chunk_base_q <= source_address_q;
                                    kernel_column_base_q <= source_address_q;
                                end
                            end
                            STAT_PAIR_ROW_REQ: begin
                                // Common scheduler: service request handshake.
                            end
                            STAT_PAIR_ROW_WAIT: begin
                                if ((kernel_row_q == 4'd0) &&
                                    kernel_apx_request_fire) begin
                                    kernel_column_q <= 4'd0;
                                    kernel_column_base_q <=
                                        kernel_chunk_base_q;
                                    kernel_index_q <=
                                        kernel_index_q + 6'd1;
                                    if ((kernel_row_q + 4'd1) >=
                                        bound0_q[3:0]) begin
                                        kernel_stat_step_q <= STAT_PAIR_DRAIN;
                                    end
                                    else begin
                                        kernel_row_q <= kernel_row_q + 4'd1;
                                        kernel_stat_step_q <= STAT_PAIR_ROW_REQ;
                                    end
                                end
                                else if ((kernel_row_q != 4'd0) &&
                                         source_buffer0_valid_q) begin
                                    kernel_column_q <= 4'd0;
                                    kernel_column_base_q <=
                                        kernel_chunk_base_q;
                                    kernel_stat_step_q <=
                                        kernel_stat_service_fire ?
                                        STAT_PAIR_COL_WAIT :
                                        STAT_PAIR_COL_REQ;
                                end
                            end
                            STAT_PAIR_COL_REQ: begin
                                // Common scheduler: service request handshake.
                            end
                            STAT_PAIR_COL_WAIT: begin
                                if (kernel_pair_col_resident_pop) begin
                                    kernel_index_q <= kernel_index_q + 6'd1;
                                    if ((kernel_column_q + 4'd1) <
                                        kernel_row_q) begin
                                        kernel_column_q <=
                                            kernel_column_q + 4'd1;
                                        kernel_column_base_q <=
                                            kernel_column_base_q +
                                            source_stride0_q;
                                        kernel_stat_step_q <=
                                            (kernel_chain_accepted_q ||
                                             kernel_pair_col_resident_load) ?
                                            STAT_PAIR_COL_WAIT :
                                            STAT_PAIR_COL_REQ;
                                    end
                                    else begin
                                        kernel_stat_step_q <=
                                            STAT_PAIR_SELF_ISSUE;
                                    end
                                    if (kernel_pair_col_resident_load) begin
                                        kernel_chain_accepted_q <=
                                            kernel_stat_service_fire;
                                    end
                                    else begin
                                        kernel_chain_accepted_q <= 1'b0;
                                    end
                                end
                                else if (kernel_pair_col_resident_load) begin
                                    kernel_chain_accepted_q <=
                                        kernel_stat_service_fire;
                                end
                            end
                            STAT_PAIR_SELF_ISSUE: begin
                                if (kernel_apx_request_fire) begin
                                    kernel_index_q <= kernel_index_q + 6'd1;
                                    if ((kernel_row_q + 4'd1) >=
                                        bound0_q[3:0]) begin
                                        kernel_stat_step_q <= STAT_PAIR_DRAIN;
                                    end
                                    else begin
                                        kernel_row_q <= kernel_row_q + 4'd1;
                                        kernel_stat_step_q <= STAT_PAIR_ROW_REQ;
                                    end
                                end
                            end
                            STAT_PAIR_DRAIN: begin
                                if (kernel_stream_completion &&
                                    ((kernel_result_count_q + 6'd1) >=
                                     kernel_index_q)) begin
                                    if (({7'd0, kernel_chunk_q} + 12'd1) >=
                                        ((bound1_q + 12'd15) >> 5'd4)) begin
                                        kernel_stat_step_q <=
                                            STAT_POST_MUL_LOAD;
                                        kernel_row_q <= 4'd0;
                                        kernel_column_q <= 4'd0;
                                        kernel_index_q <= 6'd0;
                                        kernel_result_count_q <= 6'd0;
                                        kernel_column_base_q <=
                                            destination_address_q;
                                        kernel_destination_base_q <=
                                            destination_address_q;
                                    end
                                    else begin
                                        kernel_chunk_q <=
                                            kernel_chunk_q + 5'd1;
                                        kernel_row_q <= 4'd0;
                                        kernel_column_q <= 4'd0;
                                        kernel_index_q <= 6'd0;
                                        kernel_result_count_q <= 6'd0;
                                        kernel_chunk_base_q <=
                                            kernel_chunk_base_q +
                                            (source_stride1_q << 5'd4);
                                        kernel_column_base_q <=
                                            kernel_chunk_base_q +
                                            (source_stride1_q << 5'd4);
                                        kernel_stat_step_q <=
                                            kernel_stat_service_fire ?
                                            STAT_PAIR_ROW_WAIT :
                                            STAT_PAIR_ROW_REQ;
                                    end
                                end
                            end
                            STAT_POST_MUL_LOAD: begin
                                kernel_stat_step_q <= kernel_post_mul_load_fire ?
                                    STAT_POST_MUL_WAIT :
                                    STAT_POST_MUL_ISSUE;
                            end
                            STAT_POST_MUL_ISSUE: begin
                                // Common scheduler: APX request handshake.
                            end
                            STAT_POST_MUL_WAIT: begin
                                // Common scheduler: tagged product return.
                            end
                            STAT_POST_ADD_ISSUE: begin
                                // Common scheduler: scalar request handshake.
                            end
                            STAT_POST_ADD_WAIT: begin
                                if (kernel_completion_events[8]) begin
                                    kernel_value_q <= apx_post_add_result;
                                end
                            end
                            STAT_POST_RETIRE_LOW: begin
                                if (kernel_retire_complete) begin
                                    if (kernel_row_q != kernel_column_q) begin
                                        kernel_destination_base_q <=
                                            kernel_column_base_q;
                                        kernel_stat_step_q <=
                                            STAT_POST_RETIRE_HIGH;
                                    end
                                    else if ((kernel_row_q + 4'd1) >=
                                             bound0_q[3:0]) begin
                                        kernel_stat_step_q <= STAT_TRACE_LOAD;
                                    end
                                    else begin
                                        kernel_row_q <= kernel_row_q + 4'd1;
                                        kernel_column_q <= 4'd0;
                                        kernel_index_q <=
                                            kernel_index_q + 6'd1;
                                        kernel_destination_base_q <=
                                            kernel_row_base_q +
                                            {1'b0, bound0_q};
                                        kernel_column_base_q <=
                                            destination_address_q +
                                            {8'd0, kernel_row_q} + 13'd1;
                                        kernel_stat_step_q <=
                                            STAT_POST_MUL_LOAD;
                                    end
                                end
                            end
                            STAT_POST_RETIRE_HIGH: begin
                                if (kernel_retire_complete) begin
                                    kernel_column_q <=
                                        kernel_column_q + 4'd1;
                                    kernel_index_q <=
                                        kernel_index_q + 6'd1;
                                    kernel_destination_base_q <=
                                        kernel_row_base_q +
                                        {9'd0, kernel_column_q} + 13'd1;
                                    kernel_column_base_q <=
                                        kernel_column_base_q +
                                        {1'b0, bound0_q};
                                    kernel_stat_step_q <= STAT_POST_MUL_LOAD;
                                end
                            end
                            STAT_TRACE_LOAD: begin
                                // Common scheduler: local -> APX issue.
                            end
                            STAT_TRACE_ISSUE: begin
                                // Common scheduler: APX request handshake.
                            end
                            STAT_TRACE_WAIT: begin
                                // Common scheduler: tagged reduce return.
                            end
                            STAT_TRACE_SCALE_ISSUE: begin
                                // Common scheduler: APX request handshake.
                            end
                            STAT_TRACE_SCALE_WAIT: begin
                                // Common scheduler: tagged product return.
                            end
                            STAT_TRACE_REG_ISSUE: begin
                                // Common scheduler: APX request handshake.
                            end
                            STAT_TRACE_REG_WAIT: begin
                                // Common scheduler: tagged product return.
                            end
                            STAT_TRACE_EPS_ISSUE: begin
                                // Common scheduler: scalar request handshake.
                            end
                            STAT_TRACE_EPS_WAIT: begin
                                if (kernel_completion_events[9]) begin
                                    kernel_diagonal_q <= apx_post_add_result;
                                    kernel_row_q <= 4'd0;
                                    kernel_destination_base_q <=
                                        destination_address_q;
                                end
                            end
                            STAT_DIAG_ADD_LOAD: begin
                                // Common scheduler: local -> scalar issue.
                            end
                            STAT_DIAG_ADD_ISSUE: begin
                                // Common scheduler: scalar request handshake.
                            end
                            STAT_DIAG_ADD_WAIT: begin
                                if (kernel_completion_events[10]) begin
                                    kernel_value_q <= apx_post_add_result;
                                end
                            end
                            STAT_DIAG_RETIRE: begin
                                if (kernel_retire_complete) begin
                                    if ((kernel_row_q + 4'd1) >=
                                        bound0_q[3:0]) begin
                                        state_q <= STATE_COMPLETE;
                                    end
                                    else begin
                                        kernel_row_q <= kernel_row_q + 4'd1;
                                        kernel_destination_base_q <=
                                            kernel_destination_base_q +
                                            {1'b0, bound0_q} + 13'd1;
                                        kernel_stat_step_q <=
                                            STAT_DIAG_ADD_LOAD;
                                    end
                                end
                            end
                            default: kernel_stat_step_q <= STAT_MEAN_STREAM;
                        endcase
                    end
                    else if (kernel_kind_q == KERNEL_TRIANGULAR) begin
                        case (kernel_tri_step_q)
                            TRI_CONST_REQ: begin
                                // Common scheduler: service request handshake.
                            end
                            TRI_CONST_WAIT: begin
                                if (kernel_service_response_accept) begin
                                    kernel_scalar_bank_q[15:0] <=
                                        service_response_data[79:64];
                                    kernel_index_q <= 6'd0;
                                    kernel_tri_step_q <= TRI_CLEAR;
                                end
                            end
                            TRI_CLEAR: begin
                                if (kernel_index_q[3:0] >=
                                    (bound0_q[3:0] + 4'd1)) begin
                                    kernel_index_q <= 6'd0;
                                    kernel_tri_step_q <= TRI_STAT_REQ;
                                end
                                else begin
                                    kernel_index_q <= kernel_index_q + 6'd1;
                                end
                            end
                            TRI_STAT_REQ: begin
                                // Common scheduler: service request handshake.
                            end
                            TRI_STAT_WAIT: begin
                                if (kernel_service_response_accept) begin
                                    kernel_scalar_bank_q[31:16] <=
                                        service_response_data[15:0];
                                    if (kernel_row_q == 4'd0) begin
                                        if (kernel_column_q == kernel_row_q)
                                            kernel_tri_step_q <= TRI_DIAG_PREP;
                                        else
                                            kernel_tri_step_q <=
                                                TRI_OUTPUT_START;
                                    end
                                    else begin
                                        kernel_index_q <= 6'd0;
                                        kernel_tri_step_q <= TRI_DOT_START;
                                    end
                                end
                            end
                            TRI_DOT_START: begin
                                if (!kernel_refine_busy_q) begin
                                    kernel_scalar_bank_q[111:96] <=
                                        factor_factor_left;
                                    kernel_scalar_bank_q[127:112] <=
                                        factor_factor_right;
                                    kernel_refine_step_q <= 3'd0;
                                    kernel_refine_busy_q <= 1'b1;
                                    kernel_tri_step_q <= TRI_DOT_TERM_WAIT;
                                end
                            end
                            TRI_DOT_TERM_WAIT: begin
                                if (kernel_refine_done_q) begin
                                    if ((kernel_index_q + 6'd1) <
                                        {2'd0, kernel_row_q}) begin
                                        kernel_index_q <=
                                            kernel_index_q + 6'd1;
                                        kernel_tri_step_q <= TRI_DOT_START;
                                    end
                                    else begin
                                        kernel_tri_step_q <=
                                            TRI_DOT_REDUCE_ISSUE;
                                    end
                                end
                            end
                            TRI_DOT_REDUCE_ISSUE: begin
                                // Common scheduler: APX request handshake.
                            end
                            TRI_DOT_REDUCE_WAIT: begin
                                if (kernel_completion_events[7]) begin
                                    kernel_scalar_bank_q[143:128] <=
                                        apx_reduce_result;
                                end
                            end
                            TRI_SUB_ISSUE: begin
                                // Common scheduler: APX request handshake.
                            end
                            TRI_SUB_WAIT: begin
                                if (kernel_pair_d201_event)
                                    kernel_scalar_bank_q[31:16] <=
                                        apx_pair_bus[15:0];
                                if (kernel_pair_d201_event) begin
                                    if (kernel_column_q == kernel_row_q)
                                        kernel_tri_step_q <= TRI_DIAG_PREP;
                                    else
                                        kernel_tri_step_q <=
                                            TRI_OUTPUT_START;
                                end
                            end
                            TRI_DIAG_PREP: begin
                                kernel_scalar_bank_q[47:32] <=
                                    factor_clamped_value;
                                kernel_scalar_bank_q[63:48] <=
                                    rsqrt_seed_word(
                                        factor_clamped_value[14:10]);
                                kernel_chunk_q <= 5'd0;
                                kernel_tri_step_q <= TRI_RSQ_SQUARE_START;
                            end
                            TRI_RSQ_SQUARE_START: begin
                                if (!kernel_refine_busy_q) begin
                                    kernel_scalar_bank_q[111:96] <=
                                        factor_estimate;
                                    kernel_scalar_bank_q[127:112] <=
                                        factor_estimate;
                                    kernel_refine_step_q <= 3'd0;
                                    kernel_refine_busy_q <= 1'b1;
                                    kernel_tri_step_q <= TRI_RSQ_SQUARE_WAIT;
                                end
                            end
                            TRI_RSQ_SQUARE_WAIT: begin
                                if (kernel_refine_done_q) begin
                                    kernel_scalar_bank_q[79:64] <=
                                        factor_refine_result;
                                    kernel_tri_step_q <= TRI_RSQ_VALUE_START;
                                end
                            end
                            TRI_RSQ_VALUE_START: begin
                                if (!kernel_refine_busy_q) begin
                                    kernel_scalar_bank_q[111:96] <= factor_value;
                                    kernel_scalar_bank_q[127:112] <= factor_temp;
                                    kernel_refine_step_q <= 3'd0;
                                    kernel_refine_busy_q <= 1'b1;
                                    kernel_tri_step_q <= TRI_RSQ_VALUE_WAIT;
                                end
                            end
                            TRI_RSQ_VALUE_WAIT: begin
                                if (kernel_refine_done_q) begin
                                    kernel_scalar_bank_q[79:64] <=
                                        factor_refine_result;
                                    kernel_tri_step_q <= TRI_RSQ_HALF_START;
                                end
                            end
                            TRI_RSQ_HALF_START: begin
                                if (!kernel_refine_busy_q) begin
                                    kernel_scalar_bank_q[111:96] <= 16'h3800;
                                    kernel_scalar_bank_q[127:112] <= factor_temp;
                                    kernel_refine_step_q <= 3'd0;
                                    kernel_refine_busy_q <= 1'b1;
                                    kernel_tri_step_q <= TRI_RSQ_HALF_WAIT;
                                end
                            end
                            TRI_RSQ_HALF_WAIT: begin
                                if (kernel_refine_done_q) begin
                                    kernel_scalar_bank_q[79:64] <=
                                        factor_refine_result;
                                    kernel_tri_step_q <= TRI_RSQ_CORR_ISSUE;
                                end
                            end
                            TRI_RSQ_CORR_ISSUE: begin
                                // Common scheduler: APX request handshake.
                            end
                            TRI_RSQ_CORR_WAIT: begin
                                if (kernel_pair_d202_event) begin
                                    kernel_scalar_bank_q[79:64] <=
                                        apx_pair_bus[15:0];
                                end
                            end
                            TRI_RSQ_EST_START: begin
                                if (!kernel_refine_busy_q) begin
                                    kernel_scalar_bank_q[111:96] <=
                                        factor_estimate;
                                    kernel_scalar_bank_q[127:112] <= factor_temp;
                                    kernel_refine_step_q <= 3'd0;
                                    kernel_refine_busy_q <= 1'b1;
                                    kernel_tri_step_q <= TRI_RSQ_EST_WAIT;
                                end
                            end
                            TRI_RSQ_EST_WAIT: begin
                                if (kernel_refine_done_q) begin
                                    kernel_scalar_bank_q[63:48] <=
                                        factor_refine_result;
                                    if (kernel_chunk_q[1:0] == 2'd2) begin
                                        kernel_scalar_bank_q[95:80] <=
                                            factor_refine_result;
                                        kernel_tri_step_q <= TRI_OUTPUT_START;
                                    end
                                    else begin
                                        kernel_chunk_q <= kernel_chunk_q + 5'd1;
                                        kernel_tri_step_q <=
                                            TRI_RSQ_SQUARE_START;
                                    end
                                end
                            end
                            TRI_OUTPUT_START: begin
                                if (!kernel_refine_busy_q) begin
                                    kernel_scalar_bank_q[111:96] <=
                                        (kernel_column_q == kernel_row_q) ?
                                        factor_value : factor_scalar;
                                    kernel_scalar_bank_q[127:112] <=
                                        factor_inverse;
                                    kernel_refine_step_q <= 3'd0;
                                    kernel_refine_busy_q <= 1'b1;
                                    kernel_tri_step_q <= TRI_OUTPUT_WAIT;
                                end
                            end
                            TRI_OUTPUT_WAIT: begin
                                if (kernel_refine_done_q) begin
                                    if ((kernel_column_q + 4'd1) <
                                        bound0_q[3:0]) begin
                                        kernel_column_q <=
                                            kernel_column_q + 4'd1;
                                        source_address_q <=
                                            source_address_q +
                                            {1'b0, bound0_q};
                                        kernel_tri_step_q <= TRI_STAT_REQ;
                                    end
                                    else begin
                                        retire_destination_q <=
                                            retire_destination_q +
                                            {1'b0, bound0_q} + 13'd1;
                                        if ((kernel_row_q + 4'd1) <
                                            bound0_q[3:0]) begin
                                            kernel_row_q <= kernel_row_q + 4'd1;
                                            kernel_column_q <=
                                                kernel_row_q + 4'd1;
                                            source_i0_base_q <=
                                                source_i0_base_q +
                                                {1'b0, bound0_q} + 13'd1;
                                            source_address_q <=
                                                source_i0_base_q +
                                                {1'b0, bound0_q} + 13'd1;
                                            kernel_tri_step_q <= TRI_STAT_REQ;
                                        end
                                        else begin
                                            kernel_result_count_q <= 6'd0;
                                            kernel_tri_step_q <=
                                                TRI_RETIRE_LOAD;
                                        end
                                    end
                                end
                            end
                            TRI_RETIRE_LOAD: begin
                                // Reuse the scalar bank as a local row register.
                                // This separates asynchronous scratch decode
                                // from the shared retire packet boundary.
                                kernel_scalar_bank_q[127:0] <=
                                    scratch_role0_data;
                                kernel_tri_step_q <= TRI_RETIRE;
                            end
                            TRI_RETIRE: begin
                                if (kernel_retire_complete) begin
                                    if (kernel_result_count_q[3:0] ==
                                        bound0_q[3:0]) begin
                                        state_q <= STATE_COMPLETE;
                                    end
                                    else begin
                                        kernel_result_count_q <=
                                            kernel_result_count_q + 6'd1;
                                        retire_destination_q <=
                                            retire_destination_q +
                                                {1'b0, bound0_q};
                                        kernel_tri_step_q <=
                                            TRI_RETIRE_LOAD;
                                    end
                                end
                            end
                            default: kernel_tri_step_q <= TRI_CONST_REQ;
                        endcase
                    end
                    else if (kernel_kind_q == KERNEL_BACKSUB) begin
                        case (kernel_backsub_step_q)
                            BACKSUB_MATRIX_REQ: begin
                                // Common scheduler: service request handshake.
                            end
                            BACKSUB_MATRIX_WAIT: begin
                                if (kernel_service_response_accept)
                                    kernel_backsub_step_q <= BACKSUB_INVERSE_REQ;
                            end
                            BACKSUB_INVERSE_REQ: begin
                                // Common scheduler: service request handshake.
                            end
                            BACKSUB_INVERSE_WAIT: begin
                                if (kernel_service_response_accept) begin
                                    kernel_diagonal_q <=
                                        service_response_data[15:0];
                                    kernel_backsub_step_q <= BACKSUB_RAW_REQ;
                                end
                            end
                            BACKSUB_RAW_REQ: begin
                                // Common scheduler: service request handshake.
                            end
                            BACKSUB_RAW_WAIT: begin
                                if (kernel_apx_request_fire)
                                    kernel_backsub_step_q <= BACKSUB_CENTER_WAIT;
                            end
                            BACKSUB_CENTER_WAIT: begin
                                if (kernel_pair_f000_event) begin
                                    if (kernel_row_q == 4'd0)
                                        kernel_backsub_step_q <= BACKSUB_SCALE_WAIT;
                                    else begin
                                        kernel_request_count_q <= 6'd0;
                                        kernel_response_count_q <= 6'd0;
                                        kernel_result_count_q <= 6'd0;
                                        gather_source_address_q <=
                                            kernel_chunk_base_q;
                                        kernel_backsub_step_q <=
                                            BACKSUB_PRODUCT_STREAM;
                                    end
                                end
                            end
                            BACKSUB_PRODUCT_STREAM: begin
                                if (service_request_valid &&
                                    service_request_ready) begin
                                    kernel_request_count_q <=
                                        kernel_request_count_q + 6'd1;
                                    gather_source_address_q <=
                                        gather_source_address_q +
                                        destination_stride0_q;
                                end
                                if (kernel_apx_request_fire)
                                    kernel_response_count_q <=
                                        kernel_response_count_q + 6'd1;
                                if (kernel_product_f2_event_q) begin
                                    kernel_result_count_q <=
                                        kernel_result_count_q + 6'd1;
                                    if ((kernel_result_count_q + 6'd1) >=
                                        {2'd0, kernel_row_q}) begin
                                        if (kernel_row_q == 4'd1)
                                            kernel_backsub_step_q <= BACKSUB_SUB_WAIT;
                                        else if (kernel_row_q >= 4'd3)
                                            kernel_backsub_step_q <=
                                                BACKSUB_REDUCE_01_WAIT;
                                        else
                                            kernel_backsub_step_q <=
                                                BACKSUB_REDUCE_01_ISSUE;
                                    end
                                end
                            end
                            BACKSUB_REDUCE_01_ISSUE: begin
                                // Common scheduler: APX request handshake.
                            end
                            BACKSUB_REDUCE_01_WAIT: begin
                                if (kernel_pair_f301_event) begin
                                    if (kernel_row_q == 4'd2)
                                        kernel_backsub_step_q <= BACKSUB_SUB_WAIT;
                                    else if (kernel_row_q == 4'd3)
                                        kernel_backsub_step_q <=
                                            BACKSUB_REDUCE_LAST_WAIT;
                                    else
                                        kernel_backsub_step_q <=
                                            BACKSUB_REDUCE_23_WAIT;
                                end
                            end
                            BACKSUB_REDUCE_23_ISSUE: begin
                                // Common scheduler: APX request handshake.
                            end
                            BACKSUB_REDUCE_23_WAIT: begin
                                if (kernel_pair_f302_event)
                                    kernel_backsub_step_q <=
                                        BACKSUB_REDUCE_FINAL_WAIT;
                            end
                            BACKSUB_REDUCE_FINAL_ISSUE: begin
                                // Common scheduler: APX request handshake.
                            end
                            BACKSUB_REDUCE_FINAL_WAIT: begin
                                if (kernel_pair_f303_event) begin
                                    if (kernel_row_q == 4'd5)
                                        kernel_backsub_step_q <=
                                            BACKSUB_REDUCE_LAST_WAIT;
                                    else
                                        kernel_backsub_step_q <= BACKSUB_SUB_WAIT;
                                end
                            end
                            BACKSUB_REDUCE_LAST_ISSUE: begin
                                // Common scheduler: APX request handshake.
                            end
                            BACKSUB_REDUCE_LAST_WAIT: begin
                                if (kernel_pair_f304_event)
                                    kernel_backsub_step_q <= BACKSUB_SUB_WAIT;
                            end
                            BACKSUB_SUB_ISSUE: begin
                                // Common scheduler: APX request handshake.
                            end
                            BACKSUB_SUB_WAIT: begin
                                if (kernel_pair_f305_event)
                                    kernel_backsub_step_q <= BACKSUB_SCALE_WAIT;
                            end
                            BACKSUB_SCALE_ISSUE: begin
                                // Common scheduler: APX request handshake.
                            end
                            BACKSUB_SCALE_WAIT: begin
                                // Common scheduler: tagged product return.
                            end
                            BACKSUB_RETIRE_LOW: begin
                                // Common scheduler: ordered retire completion.
                            end
                            BACKSUB_RETIRE_HIGH: begin
                                if (kernel_retire_complete) begin
                                    kernel_request_count_q <= 6'd0;
                                    kernel_response_count_q <= 6'd0;
                                    kernel_result_count_q <= 6'd0;
                                    if (({7'd0, kernel_chunk_q} + 12'd1) <
                                        ((bound1_q + 12'd15) >> 5'd4)) begin
                                        kernel_chunk_q <=
                                            kernel_chunk_q + 5'd1;
                                        kernel_chunk_base_q <=
                                            kernel_chunk_base_q +
                                            (destination_stride1_q << 5'd4);
                                        kernel_destination_base_q <=
                                            kernel_destination_base_q +
                                            (destination_stride1_q << 5'd4);
                                        gather_source_address_q <=
                                            kernel_chunk_base_q +
                                            (destination_stride1_q << 5'd4);
                                        kernel_backsub_step_q <= BACKSUB_RAW_REQ;
                                    end
                                    else if ((kernel_row_q + 4'd1) <
                                             bound0_q[3:0]) begin
                                        kernel_row_q <= kernel_row_q + 4'd1;
                                        kernel_chunk_q <= 5'd0;
                                        source_i0_base_q <=
                                            source_i0_base_q +
                                            source_stride0_q;
                                        kernel_chunk_base_q <=
                                            destination_address_q;
                                        kernel_column_base_q <=
                                            kernel_column_base_q +
                                            {1'b0, bound0_q};
                                        retire_destination_q <=
                                            retire_destination_q +
                                            destination_stride0_q;
                                        kernel_destination_base_q <=
                                            retire_destination_q +
                                            destination_stride0_q;
                                        gather_source_address_q <=
                                            destination_address_q;
                                        kernel_backsub_step_q <= BACKSUB_MATRIX_REQ;
                                    end
                                    else begin
                                        state_q <= STATE_COMPLETE;
                                    end
                                end
                            end
                            default: kernel_backsub_step_q <= BACKSUB_MATRIX_REQ;
                        endcase
                    end
                    else if (kernel_kind_q == KERNEL_RECURRENCE) begin
                        case (iir_phase_q)
                            REC_SOURCE: begin
                                if (iir_service_request_fire)
                                    iir_source_pending_q <= 1'b1;
                                if (service_tile_response_valid &&
                                    iir_source_pending_q) begin
                                    result_chunk_q <= {32'd0,
                                        service_response_data[95:0]};
                                    iir_source_pending_q <= 1'b0;
                                    iir_prefetch_valid_q <= 1'b0;
                                    iir_late_valid_q <= 1'b0;
                                    iir_drain_q <= 1'b0;
                                    iir_block_wait_q <= 1'b0;
                                    iir_samples_remaining_q <= bound1_q;
                                    iir_run_step_q <= 4'd0;
                                    iir_restart_gap_q <= 2'd0;
                                    gather_source_address_q <=
                                        source_address_q + source_stride1_q;
                                    iir_phase_q <= REC_RUN_0;
                                end
                            end
                            REC_RUN_0: begin
                                if (iir_service_request_fire) begin
                                    iir_source_pending_q <= 1'b1;
                                    gather_source_address_q <=
                                        gather_source_address_q +
                                        source_stride1_q;
                                end
                                if (service_tile_response_valid &&
                                    iir_source_pending_q) begin
                                    source_buffer1_data_q[95:0] <=
                                        service_response_data[95:0];
                                    iir_source_pending_q <= 1'b0;
                                    iir_prefetch_valid_q <= 1'b1;
                                end
                                if (iir_current_return)
                                    iir_history_valid_q[
                                        iir_pair_event_channel] <= 1'b1;

                                if (iir_restart_gap_q != 2'd0) begin
                                    iir_restart_gap_q <=
                                        iir_restart_gap_q - 2'd1;
                                end
                                else if (iir_block_wait_q) begin
                                    if (service_tile_response_valid &&
                                        iir_source_pending_q) begin
                                        source_buffer0_data_q[47:0] <=
                                            result_chunk_q[95:48];
                                        iir_late_valid_q <= 1'b1;
                                        result_chunk_q <= {32'd0,
                                            service_response_data[95:0]};
                                        iir_prefetch_valid_q <= 1'b0;
                                        iir_samples_remaining_q <=
                                            iir_samples_remaining_q - 12'd1;
                                        iir_run_step_q <= 4'd0;
                                        iir_block_wait_q <= 1'b0;
                                    end
                                end
                                else if (iir_run_step_q == 4'd15) begin
                                    if (!(|iir_samples_remaining_q[11:1])) begin
                                        source_buffer0_data_q[47:0] <=
                                            result_chunk_q[95:48];
                                        iir_late_valid_q <= 1'b1;
                                        iir_drain_q <= 1'b1;
                                        iir_run_step_q <= 4'd0;
                                        iir_restart_gap_q <= 2'd3;
                                    end
                                    else if (iir_prefetch_valid_q ||
                                             (service_tile_response_valid &&
                                              iir_source_pending_q)) begin
                                        source_buffer0_data_q[47:0] <=
                                            result_chunk_q[95:48];
                                        iir_late_valid_q <= 1'b1;
                                        result_chunk_q <= {32'd0,
                                            iir_prefetch_valid_q ?
                                            source_buffer1_data_q[95:0] :
                                            service_response_data[95:0]};
                                        iir_prefetch_valid_q <= 1'b0;
                                        iir_samples_remaining_q <=
                                            iir_samples_remaining_q - 12'd1;
                                        iir_run_step_q <= 4'd0;
                                        iir_restart_gap_q <= 2'd3;
                                    end
                                    else begin
                                        iir_block_wait_q <= 1'b1;
                                    end
                                end
                                else begin
                                    iir_run_step_q <=
                                        iir_run_step_q + 4'd1;
                                end

                                if (iir_drain_q && iir_current_return &&
                                    (iir_pair_event_channel ==
                                     (bound0_q[2:0] - 3'd1))) begin
                                    iir_source_pending_q <= 1'b0;
                                    iir_terminal_request_count_q <= 4'd0;
                                    iir_terminal_response_count_q <= 4'd0;
                                    iir_run_step_q <= 4'd0;
                                    iir_restart_gap_q <= 2'd0;
                                    iir_phase_q <= REC_COS_WAIT;
                                end
                            end
                            REC_COS_WAIT: begin
                                if (iir_service_request_fire)
                                    iir_source_pending_q <= 1'b1;
                                if (service_tile_response_valid &&
                                    iir_source_pending_q) begin
                                    iir_source_pending_q <= 1'b0;
                                    iir_terminal_request_count_q <= 4'd0;
                                    iir_terminal_response_count_q <= 4'd0;
                                    iir_phase_q <= REC_REAL;
                                end
                            end
                            REC_REAL: begin
                                if (iir_apx_request_fire)
                                    iir_terminal_request_count_q <=
                                        iir_terminal_request_count_q + 4'd1;
                                if (iir_real_return) begin
                                    iir_terminal_response_count_q <=
                                        iir_terminal_response_count_q + 4'd1;
                                    if ((iir_terminal_response_count_q +
                                         4'd1) >=
                                        {1'b0, bound0_q[2:0]}) begin
                                        iir_source_pending_q <= 1'b0;
                                        iir_terminal_request_count_q <= 4'd0;
                                        iir_terminal_response_count_q <= 4'd0;
                                        iir_phase_q <= REC_SINE_WAIT;
                                    end
                                end
                            end
                            REC_SINE_WAIT: begin
                                if (iir_service_request_fire)
                                    iir_source_pending_q <= 1'b1;
                                if (service_tile_response_valid &&
                                    iir_source_pending_q) begin
                                    iir_source_pending_q <= 1'b0;
                                    iir_terminal_request_count_q <= 4'd0;
                                    iir_terminal_response_count_q <= 4'd0;
                                    iir_phase_q <= REC_IMAG;
                                end
                            end
                            REC_IMAG: begin
                                if (iir_apx_request_fire)
                                    iir_terminal_request_count_q <=
                                        iir_terminal_request_count_q + 4'd1;
                                if (iir_imag_return) begin
                                    iir_terminal_response_count_q <=
                                        iir_terminal_response_count_q + 4'd1;
                                    if ((iir_terminal_response_count_q +
                                         4'd1) >=
                                        {1'b0, bound0_q[2:0]}) begin
                                        kernel_row_q <= 4'd0;
                                        kernel_chunk_q <= 5'd0;
                                        kernel_destination_base_q <=
                                            destination_address_q;
                                        iir_phase_q <= REC_RETIRE;
                                    end
                                end
                            end
                            REC_RETIRE: begin
                                if (kernel_retire_complete) begin
                                    if (iir_retire_last_chunk) begin
                                        kernel_chunk_q <= 5'd0;
                                        if (iir_retire_last_channel) begin
                                            state_q <= STATE_COMPLETE;
                                        end
                                        else begin
                                            kernel_row_q <=
                                                kernel_row_q + 4'd1;
                                            kernel_destination_base_q <=
                                                kernel_destination_base_q +
                                                destination_stride0_q;
                                        end
                                    end
                                    else begin
                                        kernel_chunk_q <=
                                            kernel_chunk_q + 5'd1;
                                    end
                                end
                            end
                            default: begin
                                iir_run_step_q <= 4'd0;
                                iir_restart_gap_q <= 2'd0;
                                iir_phase_q <= REC_SOURCE;
                            end
                        endcase
                    end
                end

                STATE_COMPLETE: begin
                    state_q <= STATE_IDLE;
                end

                default: begin
                    state_q <= STATE_IDLE;
                end
            endcase
        end
    end

    always @(posedge clk) begin
        if (tile_state_active &&
            (tile_phase_q == TILE_WEIGHT_WAIT) &&
            tile_service_response_beat_accept) begin
            if (service_response_half)
                weight_slots[0][255:128] <= service_response_data;
            else begin
                weight_slots[0][127:0] <= service_response_data;
                if (operand_response_lanes_q <= 5'd8)
                    weight_slots[0][255:128] <= 128'd0;
            end
        end
        else if (kernel_recurrence_active &&
            ((iir_phase_q == REC_COS_WAIT) ||
             (iir_phase_q == REC_SINE_WAIT)) &&
            kernel_service_response_beat_accept &&
            iir_source_pending_q) begin
            if (service_response_half)
                weight_slots[0][255:128] <= service_response_data;
            else begin
                weight_slots[0][127:0] <= service_response_data;
                if (operand_response_lanes_q <= 5'd8)
                    weight_slots[0][255:128] <= 128'd0;
            end
        end
        else if (kernel_backsub_active &&
            (kernel_backsub_step_q == BACKSUB_MATRIX_WAIT) &&
            kernel_service_response_beat_accept) begin
            if (service_response_half)
                weight_slots[0][255:128] <= service_response_data;
            else begin
                weight_slots[0][127:0] <= service_response_data;
                if (operand_response_lanes_q <= 5'd8)
                    weight_slots[0][255:128] <= 128'd0;
            end
        end
        else if (solve_terminal_product_prefetch &&
                 (kernel_row_q >= 4'd3))
            weight_slots[1] <= solve_product_tile1;
        else if (solve_f301_prefetch && (kernel_row_q >= 4'd3))
            weight_slots[1] <= (kernel_row_q == 4'd3) ?
                solve_product_tile0 : solve_product_tile1;
        else if (solve_f303_prefetch && (kernel_row_q == 4'd5))
            weight_slots[1] <= solve_product_tile0;
        else if (kernel_backsub_active && kernel_product_f2_event_q &&
                 (kernel_row_q <= 4'd2))
            weight_slots[1] <= apx_product_bus;
        else if (kernel_backsub_active && kernel_pair_f301_event &&
                 (kernel_row_q == 4'd2))
            weight_slots[1] <= apx_pair_bus;
        else if (kernel_backsub_active && kernel_pair_f302_event)
            weight_slots[1] <= apx_pair_bus;
        else if (kernel_backsub_active && kernel_pair_f303_event &&
                 (kernel_row_q != 4'd5))
            weight_slots[1] <= apx_pair_bus;
        else if (kernel_backsub_active && kernel_pair_f304_event)
            weight_slots[1] <= apx_pair_bus;
        else if (kernel_backsub_active &&
                 (kernel_backsub_step_q == BACKSUB_SCALE_WAIT) &&
                 kernel_completion_events[4])
            weight_slots[1] <= apx_product_bus;
        else if (kernel_stat_active &&
            (kernel_stat_step_q == STAT_MEAN_STREAM) &&
            (kernel_response_count_q == 6'd0))
            weight_slots[1] <= {16{16'h3C00}};
        else if (kernel_stat_active &&
            (kernel_stat_step_q == STAT_MEAN_SCALE_LOAD))
            weight_slots[1] <= {16{weight_slots[0][15:0]}};
        else if (kernel_stat_active &&
                 (kernel_stat_step_q == STAT_PAIR_ROW_WAIT) &&
                 kernel_service_response_beat_accept) begin
            if (service_response_half)
                weight_slots[1][255:128] <= service_response_data;
            else begin
                weight_slots[1][127:0] <= service_response_data;
                if (operand_response_lanes_q <= 5'd8)
                    weight_slots[1][255:128] <= 128'd0;
            end
        end
        else if (kernel_stat_active &&
                 (kernel_stat_step_q == STAT_PAIR_COL_WAIT) &&
                 kernel_service_response_beat_accept) begin
            if (service_response_half)
                weight_slots[1][255:128] <= service_response_data;
            else begin
                weight_slots[1][127:0] <= service_response_data;
                if (operand_response_lanes_q <= 5'd8)
                    weight_slots[1][255:128] <= 128'd0;
            end
        end
        // The final column command still references weight_slots[1] while it
        // waits in shared_apx_issue_*_q.  Re-purpose that resident for the
        // following self-product only on the old command's APX dispatch edge;
        // the APX samples the old column before this nonblocking update and the
        // newly enqueued self command observes the replacement one cycle later.
        else if (kernel_stat_active &&
                 (kernel_stat_step_q == STAT_PAIR_SELF_ISSUE) &&
                 shared_apx_dispatch_fire &&
                 (shared_apx_issue_owner_q == SHARED_APX_OWNER_KERNEL))
            weight_slots[1] <= source_buffer0_data_q;
        else if (kernel_stat_active &&
                 (kernel_stat_step_q == STAT_TRACE_LOAD))
            weight_slots[1] <= {16{16'h3C00}};
        else if (kernel_stat_active &&
                 (kernel_stat_step_q == STAT_POST_MUL_LOAD))
            weight_slots[1][31:0] <= {
                select_chunk_word(scratch_role0_data,
                                  kernel_column_q[2:0]),
                weight_slots[0][15:0]};
        else if (kernel_stat_active &&
                 (kernel_stat_step_q == STAT_POST_MUL_WAIT) &&
                 kernel_completion_events[1])
            weight_slots[1][15:0] <=
                apx_product_bus[31:16] ^ 16'h8000;
        else if (kernel_stat_active &&
                 (kernel_stat_step_q == STAT_TRACE_WAIT) &&
                 kernel_completion_events[6])
            weight_slots[1][15:0] <= weight_slots[0][31:16];
        else if (kernel_stat_active &&
                 (kernel_stat_step_q == STAT_TRACE_SCALE_WAIT) &&
                 kernel_completion_events[2])
            weight_slots[1][15:0] <= weight_slots[0][47:32];
        else if (kernel_stat_active &&
                 (kernel_stat_step_q == STAT_TRACE_REG_WAIT) &&
                 kernel_completion_events[3])
            weight_slots[1][15:0] <= weight_slots[0][63:48];
        else if (kernel_stat_active &&
                 (kernel_stat_step_q == STAT_DIAG_ADD_LOAD))
            weight_slots[1][15:0] <= kernel_diagonal_q;
        else if (weight_slot_write) begin
            if (service_response_half)
                weight_slots[weight_slot_write_address][255:128] <=
                    service_response_data;
            else begin
                weight_slots[weight_slot_write_address][127:0] <=
                    service_response_data;
                if (operand_response_lanes_q <= 5'd8)
                    weight_slots[weight_slot_write_address][255:128] <=
                        128'd0;
            end
        end
        else if (pool_chunk_overlap && pool_chunk_select_q &&
                 compute_result_valid &&
                 (accumulation_enabled || bias_enabled) &&
                 !scalar_post_enabled)
            weight_slots[1][chunk_word_count_q*16 +: 16] <=
                compute_result_data;
    end

    // History-valid masks every read until its row has been written, so this
    // compact state file needs no reset tree.  The low and high state portions
    // share the same architectural write event and logical row address.
    always @(posedge clk) begin
        if (kernel_recurrence_active && iir_state_write_valid)
            iir_state_tail[
                {iir_state_write_channel, iir_state_write_neg}] <=
                iir_state_write_data[191:128];
    end

    always @(*) begin
        scratch_write_enable = 1'b0;
        scratch_write_row = 4'd0;
        scratch_write_mask = 8'hFF;
        scratch_write_word_mode = 1'b0;
        scratch_write_word_data = 16'd0;
        scratch_write_data = 128'd0;

        if (tile_reduce_return) begin
            scratch_write_enable = 1'b1;
            scratch_write_row = tile_scratch_row;
            scratch_write_mask = 8'h01 << apx_reduce_tag[2:0];
            scratch_write_word_mode = 1'b1;
            scratch_write_word_data = apx_reduce_result;
        end
        else if (kernel_recurrence_active && iir_state_write_valid) begin
            scratch_write_enable = 1'b1;
            scratch_write_row = {
                iir_state_write_channel, iir_state_write_neg
            };
            scratch_write_data = iir_state_write_data[127:0];
        end
        else if ((state_q == STATE_FIRST_WEIGHT_WAIT) && kernel_active_q &&
            (kernel_kind_q == KERNEL_BACKSUB) && service_response_accept &&
            !service_response_half) begin
            scratch_write_enable = 1'b1;
            scratch_write_row = 4'd15;
            scratch_write_data = service_response_data[127:0];
        end
        else if (kernel_stat_active && (kernel_chunk_q == 5'd0) &&
            (kernel_mean_reduce_return || kernel_pair_reduce_return)) begin
            scratch_write_enable = 1'b1;
            scratch_write_row = kernel_reduce_scratch_index[5:3];
            scratch_write_mask =
                8'h01 << kernel_reduce_scratch_index[2:0];
            scratch_write_word_mode = 1'b1;
            scratch_write_word_data = apx_reduce_result;
        end
        else if (kernel_stat_active &&
                 (kernel_stat_step_q == STAT_MEAN_SCALE_WAIT) &&
                 kernel_completion_events[0]) begin
            scratch_write_enable = 1'b1;
            scratch_write_row = 4'd3;
            scratch_write_data = apx_product_bus[127:0];
        end
        else if (kernel_stat_active &&
                 (kernel_stat_step_q == STAT_POST_ADD_WAIT) &&
                 kernel_pair_e001_event) begin
            scratch_write_enable = 1'b1;
            scratch_write_row = kernel_index_q[5:3];
            scratch_write_mask = 8'h01 << kernel_index_q[2:0];
            scratch_write_word_mode = 1'b1;
            scratch_write_word_data = apx_pair_bus[15:0];
        end
        else if (kernel_stat_active &&
                 (kernel_stat_step_q == STAT_POST_RETIRE_LOW) &&
                 (kernel_row_q == kernel_column_q)) begin
            scratch_write_enable = 1'b1;
            scratch_write_row = 4'd4;
            scratch_write_mask = 8'h01 << kernel_row_q[2:0];
            scratch_write_word_mode = 1'b1;
            scratch_write_word_data = kernel_value_q;
        end
        else if (kernel_stat_active &&
                 (kernel_stat_step_q == STAT_DIAG_ADD_WAIT) &&
                 kernel_pair_e1xx_event) begin
            scratch_write_enable = 1'b1;
            scratch_write_row = 4'd4;
            scratch_write_mask = 8'h01 << kernel_row_q[2:0];
            scratch_write_word_mode = 1'b1;
            scratch_write_word_data = apx_pair_bus[15:0];
        end
        else if (kernel_triangular_active &&
                 (kernel_tri_step_q == TRI_CLEAR)) begin
            scratch_write_enable = 1'b1;
            scratch_write_row = kernel_index_q[3:0];
            scratch_write_data = 128'd0;
        end
        else if (kernel_triangular_active &&
                 (kernel_tri_step_q == TRI_DOT_TERM_WAIT) &&
                 kernel_refine_done_q) begin
            scratch_write_enable = 1'b1;
            scratch_write_row = bound0_q[3:0] + 4'd1;
            scratch_write_mask = 8'h01 << kernel_index_q[2:0];
            scratch_write_word_mode = 1'b1;
            scratch_write_word_data = factor_refine_result;
        end
        else if (kernel_triangular_active &&
                 (kernel_tri_step_q == TRI_RSQ_EST_WAIT) &&
                 kernel_refine_done_q &&
                 (kernel_chunk_q[1:0] == 2'd2)) begin
            scratch_write_enable = 1'b1;
            scratch_write_row = bound0_q[3:0];
            scratch_write_mask = 8'h01 << kernel_row_q[2:0];
            scratch_write_word_mode = 1'b1;
            scratch_write_word_data = factor_refine_result;
        end
        else if (kernel_triangular_active &&
                 (kernel_tri_step_q == TRI_OUTPUT_WAIT) &&
                 kernel_refine_done_q) begin
            scratch_write_enable = 1'b1;
            scratch_write_row = kernel_column_q;
            scratch_write_mask = 8'h01 << kernel_row_q[2:0];
            scratch_write_word_mode = 1'b1;
            scratch_write_word_data = factor_refine_result;
        end
        else if (scratch_pool_scale_write) begin
            scratch_write_enable = 1'b1;
            scratch_write_row = apx_product_tag[3:0];
            scratch_write_data = apx_product_bus[127:0];
        end
        else if (kernel_mean_accum_return || kernel_pair_accum_return) begin
            scratch_write_enable = 1'b1;
            scratch_write_row = kernel_post_add_event_index[6:3];
            scratch_write_mask =
                8'h01 << kernel_post_add_event_index[2:0];
            scratch_write_word_mode = 1'b1;
            scratch_write_word_data = apx_post_add_result;
        end
        else if (apx_post_add_result_valid &&
                 !apx_post_add_result_tag[15]) begin
            scratch_write_enable = 1'b1;
            scratch_write_row = apx_post_add_result_tag[6:3];
            scratch_write_mask =
                8'h01 << apx_post_add_result_tag[2:0];
            scratch_write_word_mode = 1'b1;
            scratch_write_word_data = apx_post_add_result;
        end
        else if (pair_mode_q && (state_q == STATE_PAIR_RUN) &&
                 apx_reduce_valid) begin
            scratch_write_enable = 1'b1;
            scratch_write_row = pair_result_scratch_index;
            scratch_write_mask = 8'h01 << pair_result_sample[2:0];
            scratch_write_word_mode = 1'b1;
            scratch_write_word_data = apx_reduce_result;
        end
        else if (scratch_first_plane_write) begin
            scratch_write_enable = 1'b1;
            scratch_write_row = chunk_index_q[3:0];
            scratch_write_data = result_chunk_with_current;
        end
        else if (scratch_accumulation_write || scratch_bias_write) begin
            scratch_write_enable = 1'b1;
            scratch_write_row = chunk_index_q[3:0];
            scratch_write_data = apx_pair_bus[127:0];
        end
    end

    always @(*) begin
        service_request_valid = 1'b0;
        service_request_space = weight_space_q;
        service_request_base = weight_address_q;
        service_request_lane_stride =
            {weight_lane_stride_q[8], weight_lane_stride_q};
        service_request_lanes = lanes_q;
        service_request_negate = weight_negate_q;
        service_request_bias = 1'b0;
        service_request_source = 1'b0;
        service_request_repeat_count = 12'd1;
        service_request_repeat_stride = 13'd0;
        service_response_ready = 1'b0;

        if (tile_state_active &&
            ((tile_phase_q == TILE_SOURCE0_REQ) ||
             (tile_phase_q == TILE_SOURCE0_WAIT) ||
             (tile_phase_q == TILE_SOURCE1_REQ) ||
             (tile_phase_q == TILE_SOURCE1_WAIT) ||
             (tile_phase_q == TILE_WEIGHT_REQ) ||
             (tile_phase_q == TILE_WEIGHT_WAIT))) begin
            if ((tile_phase_q == TILE_WEIGHT_REQ) ||
                (tile_phase_q == TILE_WEIGHT_WAIT)) begin
                service_request_space = weight_space_q;
                service_request_base = kernel_column_base_q;
                service_request_lane_stride =
                    {weight_lane_stride_q[8], weight_lane_stride_q};
                service_request_lanes = lanes_q;
                service_request_negate = weight_negate_q;
            end
            else begin
                service_request_space = source_space_q;
                service_request_base = kernel_row_base_q +
                    (((tile_phase_q == TILE_SOURCE1_REQ) ||
                      (tile_phase_q == TILE_SOURCE1_WAIT)) ?
                     source_stride2_q : 13'd0);
                service_request_lane_stride =
                    {source_lane_stride_q[8], source_lane_stride_q};
                service_request_lanes = lanes_q;
                service_request_negate = source_negate_q;
                service_request_source = 1'b1;
            end
        end
        else if (kernel_stat_active) begin
            service_request_space = source_space_q;
            case (kernel_stat_step_q)
                STAT_MEAN_STREAM: begin
                    service_request_base =
                        (kernel_stream_completion &&
                         ((kernel_result_count_q + 6'd1) >=
                          {2'd0, bound0_q[3:0]}) &&
                         (({7'd0, kernel_chunk_q} + 12'd1) <
                          ((bound1_q + 12'd15) >> 5'd4))) ?
                        (kernel_chunk_base_q +
                         (source_stride1_q << 5'd4)) : kernel_row_base_q;
                end
                STAT_MEAN_RETIRE:
                    service_request_base = source_address_q;
                STAT_PAIR_ROW_WAIT: begin
                    service_request_base =
                        (kernel_row_q == 4'd0) ?
                        (kernel_row_base_q + source_stride0_q) :
                        kernel_chunk_base_q;
                end
                STAT_PAIR_COL_REQ:
                    service_request_base = kernel_column_base_q;
                STAT_PAIR_COL_WAIT:
                    service_request_base = kernel_column_base_q +
                        source_stride0_q +
                        (kernel_weight_resident_valid_q ?
                         source_stride0_q : 13'd0);
                STAT_PAIR_SELF_ISSUE:
                    service_request_base =
                        kernel_row_base_q + source_stride0_q;
                STAT_PAIR_DRAIN:
                    service_request_base =
                        kernel_chunk_base_q + (source_stride1_q << 5'd4);
                default:
                    service_request_base = kernel_row_base_q;
            endcase
            service_request_lane_stride = source_stride1_q[9:0];
            service_request_lanes = lanes_q;
            service_request_negate = source_negate_q;
            service_request_source = 1'b1;
        end
        else if (kernel_triangular_active) begin
            if ((kernel_tri_step_q == TRI_CONST_REQ) ||
                (kernel_tri_step_q == TRI_CONST_WAIT)) begin
                service_request_space = weight_space_q;
                service_request_base = weight_address_q;
                service_request_lane_stride =
                    {weight_lane_stride_q[8], weight_lane_stride_q};
                service_request_lanes = lanes_q;
                service_request_negate = weight_negate_q;
            end
            else begin
                service_request_space = source_space_q;
                service_request_base = source_address_q;
                service_request_lane_stride =
                    {source_lane_stride_q[8], source_lane_stride_q};
                service_request_lanes = 5'd1;
                service_request_negate = source_negate_q;
                service_request_source = 1'b1;
            end
        end
        else if (kernel_recurrence_active) begin
            if ((iir_phase_q == REC_SOURCE) || iir_run_active) begin
                service_request_space = source_space_q;
                service_request_base =
                    (iir_phase_q == REC_SOURCE) ?
                    source_address_q : gather_source_address_q;
                service_request_lane_stride = source_stride0_q[9:0];
                service_request_lanes = {2'd0, bound0_q[2:0]};
                service_request_negate = source_negate_q;
                service_request_source = 1'b1;
            end
            else begin
                service_request_space = weight_space_q;
                service_request_base = weight_i0_base_q +
                    ((iir_phase_q == REC_COS_WAIT) ?
                     {8'd0, lanes_q} : {7'd0, lanes_q, 1'b0});
                service_request_lane_stride =
                    {weight_lane_stride_q[8], weight_lane_stride_q};
                service_request_lanes = lanes_q;
                service_request_negate = weight_negate_q;
            end
        end
        else if (kernel_backsub_active) begin
            if ((kernel_backsub_step_q == BACKSUB_MATRIX_REQ) ||
                (kernel_backsub_step_q == BACKSUB_MATRIX_WAIT)) begin
                service_request_space = weight_space_q;
                service_request_base = kernel_column_base_q;
                service_request_lane_stride =
                    {weight_lane_stride_q[8], weight_lane_stride_q};
                service_request_lanes = {1'b0, bound0_q[3:0]};
                service_request_negate = weight_negate_q;
            end
            else if ((kernel_backsub_step_q == BACKSUB_INVERSE_REQ) ||
                     (kernel_backsub_step_q == BACKSUB_INVERSE_WAIT)) begin
                service_request_space = weight_space_q;
                service_request_base = weight_address_q +
                    weight_stride1_q + {9'd0, kernel_row_q};
                service_request_lane_stride = 10'd0;
                service_request_lanes = 5'd1;
                service_request_negate = weight_negate_q;
            end
            else if ((kernel_backsub_step_q == BACKSUB_RAW_REQ) ||
                     (kernel_backsub_step_q == BACKSUB_RAW_WAIT)) begin
                service_request_space = source_space_q;
                service_request_base = kernel_row_base_q;
                service_request_lane_stride = source_stride1_q[9:0];
                service_request_lanes = lanes_q;
                service_request_negate = source_negate_q;
                service_request_source = 1'b1;
            end
            else begin
                service_request_space = 2'd0;
                service_request_base = gather_source_address_q;
                service_request_lane_stride =
                    destination_stride1_q[9:0];
                service_request_lanes = lanes_q;
                service_request_negate = 1'b0;
                service_request_source = 1'b1;
            end
        end
        else if (copy_mode) begin
            service_request_space = source_space_q;
            service_request_base = gather_source_address_q;
            service_request_lane_stride =
                {source_lane_stride_q[8], source_lane_stride_q};
            service_request_lanes = copy_response_complete ?
                (copy_next_merge ? 5'd16 : lanes_q) :
                copy_request_lanes;
            service_request_negate = source_negate_q;
            service_request_source = 1'b1;
        end
        else if (emit_mode_q) begin
            service_request_space = source_space_q;
            service_request_base = source_address_q;
            service_request_lane_stride = source_stride1_q[9:0];
            service_request_lanes = emit_chunk_lanes;
            service_request_negate = source_negate_q;
            service_request_source = 1'b1;
        end

        if (tile_state_active &&
            ((tile_phase_q == TILE_SOURCE0_REQ) ||
             (tile_phase_q == TILE_SOURCE1_REQ) ||
             (tile_phase_q == TILE_WEIGHT_REQ))) begin
            service_request_valid = 1'b1;
        end
        else if (kernel_tri_service_request_valid) begin
            service_request_valid = 1'b1;
        end
        else if (iir_service_request_valid) begin
            service_request_valid = 1'b1;
        end
        else if (kernel_backsub_service_request_valid) begin
            service_request_valid = 1'b1;
        end
        else if (kernel_stat_service_request_valid) begin
            service_request_valid = 1'b1;
        end
        else if (emit_prefetch_request_q) begin
            service_request_valid = 1'b1;
            service_request_base = emit_prefetch_address_q;
            service_request_lanes = emit_prefetch_lanes_q;
        end
        else if ((state_q == STATE_FIRST_WEIGHT_WAIT) &&
            copy_response_complete && copy_has_after_response) begin
            service_request_valid = 1'b1;
            service_request_base = copy_next_source_address;
        end
        else if ((state_q == STATE_PAIR_PREFETCH) &&
                 !prefetch_pending_q) begin
            service_request_valid = 1'b1;
            case (pair_prefetch_step_q)
                2'd0: begin
                    service_request_base =
                        weight_i0_base_q + weight_stride0_q;
                end
                2'd1: begin
                    service_request_base =
                        weight_i0_base_q + weight_stride2_q;
                    service_request_lane_stride = 10'd0;
                    service_request_lanes = 5'd1;
                    service_request_bias = 1'b1;
                end
                default: begin
                    service_request_base = weight_i0_base_q +
                        weight_stride0_q + weight_stride2_q;
                    service_request_lane_stride = 10'd0;
                    service_request_lanes = 5'd1;
                    service_request_bias = 1'b1;
                end
            endcase
        end
        else if (pair_mode_q && (state_q == STATE_PAIR_RUN) &&
                 (gather_request_count_q <
                  {7'd0, pair_block_samples_q}) &&
                 (!gather_source_pending_q ||
                  pair_source_chain_request)) begin
            service_request_valid = 1'b1;
            service_request_space = source_space_q;
            service_request_base = gather_source_address_q;
            service_request_lane_stride =
                {source_lane_stride_q[8], source_lane_stride_q};
            service_request_lanes = lanes_q;
            service_request_negate = source_negate_q;
            service_request_source = 1'b1;
        end
        else if ((state_q == STATE_GENERIC_SOURCE) &&
                 !gather_source_pending_q &&
                 !source_buffer0_valid_q &&
                 (gather_request_count_q < bound1_q)) begin
            service_request_valid = 1'b1;
            service_request_space = source_space_q;
            service_request_base = gather_source_address_q;
            service_request_lane_stride =
                {source_lane_stride_q[8], source_lane_stride_q};
            service_request_lanes = lanes_q;
            service_request_negate = source_negate_q;
            service_request_source = 1'b1;
        end
        else if (state_q == STATE_FIRST_WEIGHT_REQ)
            service_request_valid = 1'b1;
        else if ((state_q == STATE_NEXT_WEIGHT_WAIT) &&
                 !prefetch_pending_q)
            service_request_valid = 1'b1;
        else if ((state_q == STATE_WINDOW_RUN) &&
                 scalar_post_enabled && bias_sequence_q &&
                 !bias_prefetch_pending_q &&
                 !bias_prefetch_ready_q) begin
            service_request_valid = 1'b1;
            service_request_base = weight_address_q + weight_stride2_q;
            service_request_lane_stride = 10'd0;
            service_request_lanes = 5'd1;
            service_request_bias = 1'b1;
        end
        else if ((state_q == STATE_WINDOW_RUN) && !emit_mode_q &&
                 !same_pad &&
                 (gather_request_count_q < bound1_q) &&
                 (!gather_source_pending_q ||
                  gather_source_chain_request)) begin
            service_request_valid = 1'b1;
            service_request_space = source_space_q;
            service_request_base = gather_source_address_q;
            service_request_lane_stride =
                {source_lane_stride_q[8], source_lane_stride_q};
            service_request_lanes = lanes_q;
            service_request_negate = source_negate_q;
            service_request_source = 1'b1;
        end
        else if ((state_q == STATE_WINDOW_RUN) && same_pad &&
                 prefetch_sequence_q &&
                 !prefetch_pending_q && !prefetch_ready_q) begin
            service_request_valid = 1'b1;
            service_request_base = next_weight_address;
        end
        else if ((state_q == STATE_WINDOW_RUN) && bias_sequence_q &&
                 !bias_prefetch_pending_q &&
                 !bias_prefetch_ready_q) begin
            service_request_valid = 1'b1;
            service_request_base = weight_address_q + weight_stride2_q;
            service_request_lane_stride = 10'd0;
            service_request_lanes = 5'd1;
            service_request_bias = 1'b1;
        end

        if (tile_state_active &&
            ((tile_phase_q == TILE_SOURCE0_WAIT) ||
             (tile_phase_q == TILE_SOURCE1_WAIT)))
            service_response_ready = 1'b1;
        else if (tile_state_active &&
                  (tile_phase_q == TILE_WEIGHT_WAIT))
            service_response_ready = 1'b1;
        else if (kernel_recurrence_active)
            service_response_ready = 1'b1;
        else if (kernel_triangular_active &&
            ((kernel_tri_step_q == TRI_CONST_WAIT) ||
             (kernel_tri_step_q == TRI_STAT_WAIT)))
            service_response_ready = 1'b1;
        else if (kernel_backsub_active &&
                 ((kernel_backsub_step_q == BACKSUB_MATRIX_WAIT) ||
                  (kernel_backsub_step_q == BACKSUB_INVERSE_WAIT)))
            service_response_ready = 1'b1;
        else if (kernel_backsub_active &&
                 ((kernel_backsub_step_q == BACKSUB_RAW_WAIT) ||
                  (kernel_backsub_step_q == BACKSUB_PRODUCT_STREAM)))
            // Enqueue transfers only the resident reference into the shared
            // APX issue slot.  Keep its payload immutable until APX samples
            // that slot on the following dispatch edge.
            service_response_ready = !solve_stream_resident_valid_q;
        else if (kernel_stat_active &&
            (kernel_stat_step_q == STAT_MEAN_STREAM))
            service_response_ready = !source_buffer0_valid_q;
        else if (kernel_stat_active &&
                 (kernel_stat_step_q == STAT_PAIR_ROW_WAIT))
            service_response_ready = !source_buffer0_valid_q;
        else if (kernel_stat_active &&
                 (kernel_stat_step_q == STAT_PAIR_COL_WAIT))
            service_response_ready = !kernel_weight_resident_valid_q;
        else if (state_q == STATE_FIRST_WEIGHT_WAIT)
            service_response_ready = (emit_mode_q || copy_mode) ?
                retire_ready : 1'b1;
        else if (state_q == STATE_NEXT_WEIGHT_WAIT)
            service_response_ready = 1'b1;
        else if (state_q == STATE_PAIR_PREFETCH)
            service_response_ready = 1'b1;
        else if (state_q == STATE_PAIR_RUN)
            service_response_ready = !source_buffer0_valid_q;
        else if (state_q == STATE_GENERIC_SOURCE)
            service_response_ready = !source_buffer0_valid_q;
        else if ((state_q == STATE_WINDOW_RUN) && emit_mode_q)
            service_response_ready = 1'b0;
        else if (state_q == STATE_WINDOW_RUN) begin
            if (operand_response_role_q == OPERAND_ROLE_SOURCE) begin
                if (pool_scalar_bypass)
                    service_response_ready = !scalar_buffer1_valid_q;
                else
                    service_response_ready = !source_buffer0_valid_q;
            end
            else
                service_response_ready = 1'b1;
        end

        if (service_request_space == SPACE_FRAME)
            service_request_base = service_request_base + frame_base_q;
        if (pool_scalar_bypass && service_request_source) begin
            service_request_repeat_count = bound1_q;
            service_request_repeat_stride = source_stride1_q;
        end
    end

    unified_memory_fabric u_memory_fabric (
        .clk(clk),
        .reset_n(reset_n),
        .service_a_valid(service_feature_a_valid),
        .service_a_address(service_feature_a_address),
        .service_b_valid(service_feature_b_valid),
        .service_b_address(service_feature_b_address),
        .service_a_response_valid(service_memory_a_response_valid),
        .service_a_response_data(service_memory_a_response_data),
        .service_b_response_valid(service_memory_b_response_valid),
        .service_b_response_data(service_memory_b_response_data),
        .window_a_valid(window_feature_a_valid),
        .window_a_address(window_feature_a_address),
        .window_a_response_valid(window_feature_a_response_valid),
        .window_a_response_data(window_feature_a_response_data),
        .retire_a_valid(retire_a_valid),
        .retire_a_address(retire_a_address),
        .retire_a_data(retire_a_data),
        .retire_b_valid(retire_b_valid),
        .retire_b_address(retire_b_address),
        .retire_b_data(retire_b_data),
        .memory_a_valid(memory_a_valid),
        .memory_a_write(memory_a_write),
        .memory_a_address(memory_a_address),
        .memory_a_write_data(memory_a_write_data),
        .memory_b_valid(memory_b_valid),
        .memory_b_write(memory_b_write),
        .memory_b_address(memory_b_address),
        .memory_b_write_data(memory_b_write_data),
        .memory_a_response_valid(memory_a_response_valid),
        .memory_a_response_data(memory_a_response_data),
        .memory_b_response_valid(memory_b_response_valid),
        .memory_b_response_data(memory_b_response_data)
    );

    shared_operand_tile_service u_operand_service (
        .clk(clk),
        .reset_n(reset_n),
        .request_valid(operand_command_valid_q),
        .request_ready(operand_service_request_ready),
        .request_space(operand_command_space_q),
        .request_base(operand_command_base_q),
        .request_lane_stride(operand_command_lane_stride_q),
        .request_lanes(operand_command_lanes_q),
        .request_negate(operand_command_negate_q),
        // COPY/EMIT use aligned microtiles.  Scalar pooling uses the same
        // trusted feature-memory port as a one-word-per-cycle stream; keeping
        // this selection at the generic request boundary avoids a
        // profile-specific datapath in the execution engine.
        .request_fast_feature(operand_command_fast_feature_q),
        .request_repeat_count(operand_command_repeat_count_q),
        .request_repeat_stride(operand_command_repeat_stride_q),
        .fast_issue_allowed(!window_feature_a_valid &&
                            !(|retire_a_valid) && !(|retire_b_valid)),
        .constant_base_row(operand_command_constant_base_row_q),
        .feature_read_a_valid(service_feature_a_valid),
        .feature_read_a_address(service_feature_a_address),
        .feature_read_b_valid(service_feature_b_valid),
        .feature_read_b_address(service_feature_b_address),
        .feature_read_a_response_valid(service_memory_a_response_valid),
        .feature_read_a_response_data(service_memory_a_response_data),
        .feature_read_b_response_valid(service_memory_b_response_valid),
        .feature_read_b_response_data(service_memory_b_response_data),
        .parameter_read_valid(service_parameter_read_valid),
        .parameter_read_address(service_parameter_read_address),
        .parameter_read_response_valid(parameter_read_response_valid),
        .parameter_read_response_data(parameter_read_response_data),
        .program_read_valid(service_program_read_valid),
        .program_read_address(service_program_read_address),
        .program_read_response_valid(program_read_response_valid),
        .program_read_response_data(program_read_response_data),
        .response_valid(service_response_valid),
        .response_ready(service_response_ready),
        .response_last(service_response_last),
        .response_half(service_response_half),
        .response_data(service_response_data)
    );

    shared_window_pipeline u_window_pipeline (
        .clk(clk),
        .reset_n(reset_n),
        .start_valid(window_start_valid),
        .start_ready(window_start_ready),
        .start_lanes(lanes_q),
        .start_output_count(bound1_q),
        .start_source_base(window_start_source_base),
        .start_source_stride(source_stride1_q),
        .start_tag_base(16'd0),
        .start_weight_select(window_start_weight_select),
        .start_weight_zero(window_start_weight_zero),
        .feature_read_a_valid(window_feature_a_valid),
        .feature_read_a_ready(!(|retire_a_valid)),
        .feature_read_a_address(window_feature_a_address),
        .feature_read_a_response_valid(window_feature_a_response_valid),
        .feature_read_a_response_data(window_feature_a_response_data),
        .apx_request_valid(window_apx_request_valid),
        .apx_request_ready(window_apx_request_ready),
        .apx_request_operation(window_apx_request_operation),
        .apx_request_lanes(window_apx_request_lanes),
        .apx_request_tag(window_apx_request_tag),
        .apx_window_shift(window_apx_shift),
        .apx_window_sample(window_apx_sample),
        .apx_weight_select(window_apx_weight_select),
        .apx_weight_zero(window_apx_weight_zero),
        .window_resident_clear_valid(window_resident_clear_valid),
        .window_resident_seed_valid(window_resident_seed_valid),
        .window_resident_seed_lanes(window_resident_seed_lanes),
        .window_resident_seed_data(window_resident_seed_data),
        .apx_reduce_valid(apx_reduce_valid),
        .apx_reduce_tag(apx_reduce_tag),
        .apx_reduce_result(apx_reduce_result),
        .result_valid(window_result_valid),
        .result_tag(window_result_tag),
        .result_data(window_result_data),
        .done(window_done)
    );

    (* keep_hierarchy = "yes" *)
    apx_cluster u_apx_cluster (
        .clk(clk),
        .reset_n(reset_n),
        .request_valid(apx_request_valid),
        .request_ready(apx_request_ready),
        .busy(apx_busy),
        .request_operation(apx_request_operation),
        .request_add_vector(apx_request_add_vector),
        .request_lanes(apx_request_lanes),
        .request_tag(apx_request_tag),
        .operand_a_low_beat(apx_request_operand_a[127:0]),
        .operand_a_high_beat(apx_request_operand_a[255:128]),
        .operand_b_low_beat(apx_request_operand_b[127:0]),
        .operand_b_high_beat(apx_request_operand_b[255:128]),
        .narrow_operand_a_low_beat(apx_narrow_operand_a[127:0]),
        .narrow_operand_a_high_beat(apx_narrow_operand_a[191:128]),
        .narrow_operand_b_low_beat(apx_narrow_operand_b[127:0]),
        .narrow_operand_b_high_beat(apx_narrow_operand_b[191:128]),
        .request_operand_a_select(
            {shared_apx_issue_operand_a_control_q[16:15],
             shared_apx_issue_operand_a_control_q[11:10],
             shared_apx_issue_operand_a_control_q[6:5],
             shared_apx_issue_operand_a_control_q[1:0]}),
        .request_operand_b_select(
            {shared_apx_issue_operand_b_control_q[16:15],
             shared_apx_issue_operand_b_control_q[11:10],
             shared_apx_issue_operand_b_control_q[6:5],
             shared_apx_issue_operand_b_control_q[1:0]}),
        .request_operand_a_negate(
            {shared_apx_issue_operand_a_control_q[19],
             shared_apx_issue_operand_a_control_q[14],
             shared_apx_issue_operand_a_control_q[9],
             shared_apx_issue_operand_a_control_q[4]}),
        .request_operand_b_negate(
            {shared_apx_issue_operand_b_control_q[19],
             shared_apx_issue_operand_b_control_q[14],
             shared_apx_issue_operand_b_control_q[9],
             shared_apx_issue_operand_b_control_q[4]}),
        .request_operand_b_scalar(
            {shared_apx_issue_operand_b_control_q[17],
             shared_apx_issue_operand_b_control_q[12],
             shared_apx_issue_operand_b_control_q[7],
             shared_apx_issue_operand_b_control_q[2]}),
        .request_operand_b_scalar_value(apx_scalar_operand_b),
        .request_window_operand(window_apx_selected),
        .request_window_shift(shared_apx_issue_window_shift_q),
        .request_window_sample(shared_apx_issue_window_sample_q),
        .window_resident_clear_valid(window_resident_clear_valid),
        .window_resident_seed_valid(window_resident_seed_valid),
        .window_resident_seed_lanes(window_resident_seed_lanes),
        .window_resident_seed_data(window_resident_seed_data),
        .parallel_add_valid(iir_parallel_add_valid),
        .parallel_add_ready(iir_parallel_add_ready),
        .parallel_add_lanes(lanes_q),
        .parallel_add_tag(iir_parallel_add_tag),
        .parallel_prefetch_valid(iir_parallel_prefetch_valid),
        .parallel_operand_a_pair(iir_parallel_operand_a_pair),
        .parallel_prefetch_b_low_beat(
            iir_parallel_prefetch_operand_b[127:0]),
        .parallel_prefetch_b_high_beat(
            iir_parallel_prefetch_operand_b[191:128]),
        .post_add_valid(kernel_apx_owner ?
            (kernel_accum_add_valid || kernel_scalar_command_valid_q) :
            scalar_post_request_valid),
        .post_add_ready(apx_post_add_ready),
        .post_add_operand_x(kernel_apx_owner ?
            (kernel_accum_add_valid ? kernel_reduce_scratch_word :
             kernel_scalar_command_x_q) : (accumulation_plane ?
            scalar_post_previous : compute_result_data)),
        .post_add_operand_y(kernel_apx_owner ?
            (kernel_accum_add_valid ? apx_reduce_result :
             kernel_scalar_command_y_q) : (accumulation_plane ?
            compute_result_data : bias_value_q)),
        .post_add_tag(kernel_apx_owner ?
            (kernel_accum_add_valid ?
             ((kernel_mean_reduce_return ? 16'h5000 : 16'h6000) |
              {10'd0, kernel_reduce_scratch_index}) :
             kernel_scalar_command_tag_q) :
            {scalar_post_retire, 3'd0, compute_result_tag[11:0]}),
        .post_add_result_valid(apx_post_add_result_valid),
        .post_add_result_tag(apx_post_add_result_tag),
        .post_add_result(apx_post_add_result),
        .post_add_pre_valid(apx_post_add_pre_valid),
        .post_add_pre_tag(apx_post_add_pre_tag),
        .product_valid(apx_product_valid),
        .product_pre_valid(apx_product_pre_valid),
        .product_tag(apx_product_tag),
        .product_pre_tag(apx_product_pre_tag),
        .product_slot_low_beat(apx_product_bus[127:0]),
        .product_slot_high_beat(apx_product_bus[255:128]),
        .pair_valid(apx_pair_valid),
        .pair_pre_valid(apx_pair_pre_valid),
        .pair_tag(apx_pair_tag),
        .pair_pre_tag(apx_pair_pre_tag),
        .pair_slot_low_beat(apx_pair_bus[127:0]),
        .pair_slot_high_beat(apx_pair_bus[255:128]),
        .reduce_valid(apx_reduce_valid),
        .reduce_pre_valid(apx_reduce_pre_valid),
        .reduce_tag(apx_reduce_tag),
        .reduce_pre_tag(apx_reduce_pre_tag),
        .reduce_result(apx_reduce_result)
    );

    unified_retire u_unified_retire (
        .clk(clk),
        .reset_n(reset_n),
        .retire_valid(engine_retire_valid),
        .retire_ready(retire_ready),
        .retire_state(engine_retire_state),
        .packet_last(retire_packet_last_q),
        .packet_destination_base(retire_packet_destination_q),
        .packet_word_count(retire_packet_word_count_q),
        .packet_lane_mask(retire_packet_lane_mask_q),
        .packet_data(retire_packet_data_q),
        .retire_ack(retire_ack),
        .bank_a_write_valid(retire_a_valid),
        .bank_a_write_address(retire_a_address),
        .bank_a_write_data(retire_a_data),
        .bank_b_write_valid(retire_b_valid),
        .bank_b_write_address(retire_b_address),
        .bank_b_write_data(retire_b_data),
        .result_valid(result_valid),
        .result_ready(result_ready),
        .result_data(result_data),
        .result_last(result_last),
        .result_packet_done(retire_result_done)
    );
endmodule
`default_nettype wire
