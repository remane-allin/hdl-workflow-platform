// Module: feature_memory_subsystem
// Description: Stores input and intermediate 16-bit feature words.
// Scope: One 8192-word FM0 with logical epoch aliasing and collision checks.
// Spec Trace: REQ-EEG-MEM-001, REQ-EEG-CH16-001,
//             REQ-EEG-V3-OPT-002.
`timescale 1ns/1ps
`default_nettype none

module feature_memory_subsystem (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        sample_valid,
    output wire        sample_ready,
    input  wire [15:0] sample_data,
    input  wire        sample_last,
    input  wire        sample_reset,
    input  wire [12:0] expected_sample_words,
    input  wire        channel_config_valid,
    output reg         sample_loaded,
    output reg  [12:0] sample_count,
    input  wire        read_enable,
    input  wire        read_pair_enable,
    input  wire        read_quad_enable,
    input  wire [12:0] read_address,
    output reg         read_valid,
    output wire [15:0] read_data,
    output wire [15:0] read_pair_data,
    output wire [15:0] read_quad_data2,
    output wire [15:0] read_quad_data3,
    output wire [15:0] read_oct_data4,
    output wire [15:0] read_oct_data5,
    output wire [15:0] read_oct_data6,
    output wire [15:0] read_oct_data7,
    input  wire        write_valid,
    output wire        write_ready,
    input  wire [12:0] write_address,
    input  wire [15:0] write_data,
    input  wire        write2_valid,
    output wire        write2_ready,
    input  wire [12:0] write2_address,
    input  wire [15:0] write2_data,
    output reg         address_error,
    output reg  [31:0] read_count,
    output reg  [31:0] write_count,
    output reg  [31:0] collision_stall_count
);
    // Address bits {8:7,0} identify one of eight channel/parity banks.
    // Removing those bits leaves eight 1024x16 banks: the same 131072 stored
    // bits and four RAMB36 tiles as V1.0.  The channel bits retain OP4's
    // four-channel gather, while the parity bit exposes adjacent time words
    // to the loader and pool prefetcher without another memory copy.
    (* ram_style = "block" *) reg [15:0] feature_memory_bank0 [0:1023];
    (* ram_style = "block" *) reg [15:0] feature_memory_bank1 [0:1023];
    (* ram_style = "block" *) reg [15:0] feature_memory_bank2 [0:1023];
    (* ram_style = "block" *) reg [15:0] feature_memory_bank3 [0:1023];
    (* ram_style = "block" *) reg [15:0] feature_memory_bank4 [0:1023];
    (* ram_style = "block" *) reg [15:0] feature_memory_bank5 [0:1023];
    (* ram_style = "block" *) reg [15:0] feature_memory_bank6 [0:1023];
    (* ram_style = "block" *) reg [15:0] feature_memory_bank7 [0:1023];
    reg [15:0] feature_memory_bank0_q;
    reg [15:0] feature_memory_bank1_q;
    reg [15:0] feature_memory_bank2_q;
    reg [15:0] feature_memory_bank3_q;
    reg [15:0] feature_memory_bank4_q;
    reg [15:0] feature_memory_bank5_q;
    reg [15:0] feature_memory_bank6_q;
    reg [15:0] feature_memory_bank7_q;
    reg [2:0] read_bank_select_q;
    reg       read_quad_select_q;
    wire        sample_write_enable;
    wire        compute_write_enable;
    wire        compute_write2_enable;
    wire [9:0] memory_write_index =
        {write_address[12:9], write_address[6:1]};
    wire [9:0] memory_write2_index =
        {write2_address[12:9], write2_address[6:1]};
    wire [2:0] memory_write_bank =
        {write_address[8:7], write_address[0]};
    wire [2:0] memory_write2_bank =
        {write2_address[8:7], write2_address[0]};
    wire bank0_write2_select =
        compute_write2_enable && (memory_write2_bank == 3'd0);
    wire bank1_write2_select =
        compute_write2_enable && (memory_write2_bank == 3'd1);
    wire bank2_write2_select =
        compute_write2_enable && (memory_write2_bank == 3'd2);
    wire bank3_write2_select =
        compute_write2_enable && (memory_write2_bank == 3'd3);
    wire bank4_write2_select =
        compute_write2_enable && (memory_write2_bank == 3'd4);
    wire bank5_write2_select =
        compute_write2_enable && (memory_write2_bank == 3'd5);
    wire bank6_write2_select =
        compute_write2_enable && (memory_write2_bank == 3'd6);
    wire bank7_write2_select =
        compute_write2_enable && (memory_write2_bank == 3'd7);
    wire [9:0] memory_read_index =
        {read_address[12:9], read_address[6:1]};
    wire [10:0] sample_offset = sample_count[10:0];
    // All samples occupy FM0[6144:8191]. OP4 is the last consumer of this
    // window, so OP5+ may refill it for the next inference without a bank
    // selector, a second buffer, or a widened sample counter update path.
    wire [12:0] sample_write_address = {2'b11, sample_offset};
    wire [9:0] sample_write_index =
        {sample_write_address[12:9], sample_write_address[6:1]};
    wire [2:0] sample_write_bank =
        {sample_write_address[8:7], sample_write_address[0]};

    wire write_read_collision = read_enable &&
        ((read_address == write_address) ||
         (read_pair_enable &&
          ((read_address + 13'd1) == write_address)) ||
         (read_quad_enable &&
          (((read_address + 13'd128) == write_address) ||
           ((read_address + 13'd256) == write_address) ||
           ((read_address + 13'd384) == write_address))));
    wire write2_read_collision = read_enable &&
        ((read_address == write2_address) ||
         (read_pair_enable &&
          ((read_address + 13'd1) == write2_address)) ||
         (read_quad_enable &&
          (((read_address + 13'd128) == write2_address) ||
           ((read_address + 13'd256) == write2_address) ||
           ((read_address + 13'd384) == write2_address))));
    wire write_bank_conflict =
        ({write_address[8:7], write_address[0]} ==
         {write2_address[8:7], write2_address[0]});
    wire sample_read_collision = read_enable &&
        ((read_address == sample_write_address) ||
         (read_pair_enable &&
          ((read_address + 13'd1) == sample_write_address)) ||
         (read_quad_enable &&
          (((read_address + 13'd128) == sample_write_address) ||
           ((read_address + 13'd256) == sample_write_address) ||
           ((read_address + 13'd384) == sample_write_address))));
    wire sample_write_conflict =
        (compute_write_enable &&
         (memory_write_bank == sample_write_bank)) ||
        (compute_write2_enable &&
         (memory_write2_bank == sample_write_bank));
    assign write_ready = !write_read_collision;
    assign write2_ready = !write2_read_collision &&
        !(write_valid && write_ready && write_bank_conflict);
    // The eight-bank feature memory can accept the staged sample word in the
    // same cycle as compute commits whenever its physical bank is free.  This
    // preserves the single stored sample image while closing the inter-sample
    // refill tail; conflicts are backpressured rather than counted as loads.
    assign sample_ready = channel_config_valid &&
        !sample_read_collision && !sample_write_conflict;
    assign sample_write_enable = sample_valid && sample_ready && !sample_reset &&
        !sample_loaded && (sample_count < expected_sample_words);
    assign compute_write_enable = write_valid && write_ready;
    assign compute_write2_enable = write2_valid && write2_ready;
    assign read_data =
        (read_bank_select_q == 3'd0) ? feature_memory_bank0_q :
        (read_bank_select_q == 3'd1) ? feature_memory_bank1_q :
        (read_bank_select_q == 3'd2) ? feature_memory_bank2_q :
        (read_bank_select_q == 3'd3) ? feature_memory_bank3_q :
        (read_bank_select_q == 3'd4) ? feature_memory_bank4_q :
        (read_bank_select_q == 3'd5) ? feature_memory_bank5_q :
        (read_bank_select_q == 3'd6) ? feature_memory_bank6_q :
                                      feature_memory_bank7_q;
    // In quad mode the second word is the same-parity value from the next
    // channel bank (+128).  Otherwise it is the adjacent time word (+1).
    assign read_pair_data = read_quad_select_q ?
        ((read_bank_select_q[2:1] == 2'd0) ?
            (read_bank_select_q[0] ? feature_memory_bank3_q : feature_memory_bank2_q) :
         (read_bank_select_q[2:1] == 2'd1) ?
            (read_bank_select_q[0] ? feature_memory_bank5_q : feature_memory_bank4_q) :
         (read_bank_select_q[2:1] == 2'd2) ?
            (read_bank_select_q[0] ? feature_memory_bank7_q : feature_memory_bank6_q) :
            (read_bank_select_q[0] ? feature_memory_bank1_q : feature_memory_bank0_q)) :
        (read_bank_select_q[0] ?
            ((read_bank_select_q[2:1] == 2'd0) ? feature_memory_bank0_q :
             (read_bank_select_q[2:1] == 2'd1) ? feature_memory_bank2_q :
             (read_bank_select_q[2:1] == 2'd2) ? feature_memory_bank4_q :
                                                feature_memory_bank6_q) :
            ((read_bank_select_q[2:1] == 2'd0) ? feature_memory_bank1_q :
             (read_bank_select_q[2:1] == 2'd1) ? feature_memory_bank3_q :
             (read_bank_select_q[2:1] == 2'd2) ? feature_memory_bank5_q :
                                                feature_memory_bank7_q));
    assign read_quad_data2 =
        (read_bank_select_q[2:1] == 2'd0) ?
            (read_bank_select_q[0] ? feature_memory_bank5_q : feature_memory_bank4_q) :
        (read_bank_select_q[2:1] == 2'd1) ?
            (read_bank_select_q[0] ? feature_memory_bank7_q : feature_memory_bank6_q) :
        (read_bank_select_q[2:1] == 2'd2) ?
            (read_bank_select_q[0] ? feature_memory_bank1_q : feature_memory_bank0_q) :
            (read_bank_select_q[0] ? feature_memory_bank3_q : feature_memory_bank2_q);
    assign read_quad_data3 =
        (read_bank_select_q[2:1] == 2'd0) ?
            (read_bank_select_q[0] ? feature_memory_bank7_q : feature_memory_bank6_q) :
        (read_bank_select_q[2:1] == 2'd1) ?
            (read_bank_select_q[0] ? feature_memory_bank1_q : feature_memory_bank0_q) :
        (read_bank_select_q[2:1] == 2'd2) ?
            (read_bank_select_q[0] ? feature_memory_bank3_q : feature_memory_bank2_q) :
            (read_bank_select_q[0] ? feature_memory_bank5_q : feature_memory_bank4_q);
    // The four banks with the opposite parity bit contain the adjacent time
    // point at the same BRAM row.  OP4 consumes these outputs together with
    // the normal quad response, doubling spatial-source bandwidth without
    // adding storage bits or another BRAM read port.
    assign read_oct_data4 =
        (read_bank_select_q == 3'd0) ? feature_memory_bank1_q :
        (read_bank_select_q == 3'd1) ? feature_memory_bank0_q :
        (read_bank_select_q == 3'd2) ? feature_memory_bank3_q :
        (read_bank_select_q == 3'd3) ? feature_memory_bank2_q :
        (read_bank_select_q == 3'd4) ? feature_memory_bank5_q :
        (read_bank_select_q == 3'd5) ? feature_memory_bank4_q :
        (read_bank_select_q == 3'd6) ? feature_memory_bank7_q :
                                      feature_memory_bank6_q;
    assign read_oct_data5 =
        (read_bank_select_q == 3'd0) ? feature_memory_bank3_q :
        (read_bank_select_q == 3'd1) ? feature_memory_bank2_q :
        (read_bank_select_q == 3'd2) ? feature_memory_bank5_q :
        (read_bank_select_q == 3'd3) ? feature_memory_bank4_q :
        (read_bank_select_q == 3'd4) ? feature_memory_bank7_q :
        (read_bank_select_q == 3'd5) ? feature_memory_bank6_q :
        (read_bank_select_q == 3'd6) ? feature_memory_bank1_q :
                                      feature_memory_bank0_q;
    assign read_oct_data6 =
        (read_bank_select_q == 3'd0) ? feature_memory_bank5_q :
        (read_bank_select_q == 3'd1) ? feature_memory_bank4_q :
        (read_bank_select_q == 3'd2) ? feature_memory_bank7_q :
        (read_bank_select_q == 3'd3) ? feature_memory_bank6_q :
        (read_bank_select_q == 3'd4) ? feature_memory_bank1_q :
        (read_bank_select_q == 3'd5) ? feature_memory_bank0_q :
        (read_bank_select_q == 3'd6) ? feature_memory_bank3_q :
                                      feature_memory_bank2_q;
    assign read_oct_data7 =
        (read_bank_select_q == 3'd0) ? feature_memory_bank7_q :
        (read_bank_select_q == 3'd1) ? feature_memory_bank6_q :
        (read_bank_select_q == 3'd2) ? feature_memory_bank1_q :
        (read_bank_select_q == 3'd3) ? feature_memory_bank0_q :
        (read_bank_select_q == 3'd4) ? feature_memory_bank3_q :
        (read_bank_select_q == 3'd5) ? feature_memory_bank2_q :
        (read_bank_select_q == 3'd6) ? feature_memory_bank5_q :
                                      feature_memory_bank4_q;

    always @(posedge clk) begin
        if ((compute_write_enable && (memory_write_bank == 3'd0)) ||
            bank0_write2_select ||
            (sample_write_enable && (sample_write_bank == 3'd0)))
            feature_memory_bank0[
                (compute_write_enable && (memory_write_bank == 3'd0)) ?
                    memory_write_index :
                bank0_write2_select ? memory_write2_index :
                    sample_write_index] <=
                (compute_write_enable && (memory_write_bank == 3'd0)) ?
                    write_data : bank0_write2_select ? write2_data : sample_data;
        if ((compute_write_enable && (memory_write_bank == 3'd1)) ||
            bank1_write2_select ||
            (sample_write_enable && (sample_write_bank == 3'd1)))
            feature_memory_bank1[
                (compute_write_enable && (memory_write_bank == 3'd1)) ?
                    memory_write_index :
                bank1_write2_select ? memory_write2_index :
                    sample_write_index] <=
                (compute_write_enable && (memory_write_bank == 3'd1)) ?
                    write_data : bank1_write2_select ? write2_data : sample_data;
        if ((compute_write_enable && (memory_write_bank == 3'd2)) ||
            bank2_write2_select ||
            (sample_write_enable && (sample_write_bank == 3'd2)))
            feature_memory_bank2[
                (compute_write_enable && (memory_write_bank == 3'd2)) ?
                    memory_write_index :
                bank2_write2_select ? memory_write2_index :
                    sample_write_index] <=
                (compute_write_enable && (memory_write_bank == 3'd2)) ?
                    write_data : bank2_write2_select ? write2_data : sample_data;
        if ((compute_write_enable && (memory_write_bank == 3'd3)) ||
            bank3_write2_select ||
            (sample_write_enable && (sample_write_bank == 3'd3)))
            feature_memory_bank3[
                (compute_write_enable && (memory_write_bank == 3'd3)) ?
                    memory_write_index :
                bank3_write2_select ? memory_write2_index :
                    sample_write_index] <=
                (compute_write_enable && (memory_write_bank == 3'd3)) ?
                    write_data : bank3_write2_select ? write2_data : sample_data;
        if ((compute_write_enable && (memory_write_bank == 3'd4)) ||
            bank4_write2_select ||
            (sample_write_enable && (sample_write_bank == 3'd4)))
            feature_memory_bank4[
                (compute_write_enable && (memory_write_bank == 3'd4)) ?
                    memory_write_index :
                bank4_write2_select ? memory_write2_index :
                    sample_write_index] <=
                (compute_write_enable && (memory_write_bank == 3'd4)) ?
                    write_data : bank4_write2_select ? write2_data : sample_data;
        if ((compute_write_enable && (memory_write_bank == 3'd5)) ||
            bank5_write2_select ||
            (sample_write_enable && (sample_write_bank == 3'd5)))
            feature_memory_bank5[
                (compute_write_enable && (memory_write_bank == 3'd5)) ?
                    memory_write_index :
                bank5_write2_select ? memory_write2_index :
                    sample_write_index] <=
                (compute_write_enable && (memory_write_bank == 3'd5)) ?
                    write_data : bank5_write2_select ? write2_data : sample_data;
        if ((compute_write_enable && (memory_write_bank == 3'd6)) ||
            bank6_write2_select ||
            (sample_write_enable && (sample_write_bank == 3'd6)))
            feature_memory_bank6[
                (compute_write_enable && (memory_write_bank == 3'd6)) ?
                    memory_write_index :
                bank6_write2_select ? memory_write2_index :
                    sample_write_index] <=
                (compute_write_enable && (memory_write_bank == 3'd6)) ?
                    write_data : bank6_write2_select ? write2_data : sample_data;
        if ((compute_write_enable && (memory_write_bank == 3'd7)) ||
            bank7_write2_select ||
            (sample_write_enable && (sample_write_bank == 3'd7)))
            feature_memory_bank7[
                (compute_write_enable && (memory_write_bank == 3'd7)) ?
                    memory_write_index :
                bank7_write2_select ? memory_write2_index :
                    sample_write_index] <=
                (compute_write_enable && (memory_write_bank == 3'd7)) ?
                    write_data : bank7_write2_select ? write2_data : sample_data;
        if (read_enable) begin
            feature_memory_bank0_q <= feature_memory_bank0[memory_read_index];
            feature_memory_bank1_q <= feature_memory_bank1[memory_read_index];
            feature_memory_bank2_q <= feature_memory_bank2[memory_read_index];
            feature_memory_bank3_q <= feature_memory_bank3[memory_read_index];
            feature_memory_bank4_q <= feature_memory_bank4[memory_read_index];
            feature_memory_bank5_q <= feature_memory_bank5[memory_read_index];
            feature_memory_bank6_q <= feature_memory_bank6[memory_read_index];
            feature_memory_bank7_q <= feature_memory_bank7[memory_read_index];
            read_bank_select_q <= {read_address[8:7], read_address[0]};
            read_quad_select_q <= read_quad_enable;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sample_loaded <= 1'b0;
            sample_count <= 13'd0;
            read_valid <= 1'b0;
            address_error <= 1'b0;
            read_count <= 32'd0;
            write_count <= 32'd0;
            collision_stall_count <= 32'd0;
        end
        else begin
            read_valid <= read_enable;
            if (read_enable) begin
                if (read_count != 32'hffff_ffff)
                    read_count <= read_count + 1'b1;
            end

            if (sample_reset) begin
                sample_loaded <= 1'b0;
                sample_count <= 13'd0;
            end
            else if (sample_valid && sample_ready) begin
                if (!sample_loaded && (sample_count < expected_sample_words)) begin
                    sample_count <= sample_count + 1'b1;
                    if (sample_last) begin
                        if ((sample_count + 1'b1) == expected_sample_words)
                            sample_loaded <= 1'b1;
                        else
                            address_error <= 1'b1;
                    end
                    else if ((sample_count + 1'b1) == expected_sample_words) begin
                        address_error <= 1'b1;
                    end
                end
                else begin
                    address_error <= 1'b1;
                end
            end

            if ((write_valid && write_ready) ||
                (write2_valid && write2_ready)) begin
                if ((write_valid && write_ready) &&
                    (write2_valid && write2_ready)) begin
                    if (write_count < 32'hffff_fffe)
                        write_count <= write_count + 2'd2;
                    else
                        write_count <= 32'hffff_ffff;
                end
                else if (write_count != 32'hffff_ffff) begin
                    write_count <= write_count + 1'b1;
                end
            end
            if ((write_valid && !write_ready) ||
                (write2_valid && !write2_ready)) begin
                if (collision_stall_count != 32'hffff_ffff)
                    collision_stall_count <= collision_stall_count + 1'b1;
            end
        end
    end
endmodule
`default_nettype wire
