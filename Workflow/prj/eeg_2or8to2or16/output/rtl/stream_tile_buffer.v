// Module: stream_tile_buffer
// Description: Captures one operation-local tile of up to 256 words.
// Scope: Sixteen distributed-RAM banks provide one aligned 16-word window.
// Spec Trace: REQ-EEG-MEM-001, REQ-EEG-ARCH-001.
`timescale 1ns/1ps
`default_nettype none

module stream_tile_buffer (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          clear,
    input  wire          write_valid,
    input  wire [7:0]    write_index,
    input  wire [15:0]   write_data,
    input  wire          write2_valid,
    input  wire [7:0]    write2_index,
    input  wire [15:0]   write2_data,
    input  wire          write3_valid,
    input  wire [7:0]    write3_index,
    input  wire [15:0]   write3_data,
    input  wire          write4_valid,
    input  wire [7:0]    write4_index,
    input  wire [15:0]   write4_data,
    output wire          write_ready,
    input  wire [7:0]    read_base_index,
    output wire [255:0]  read_window,
    output reg  [8:0]    live_count,
    output reg  [8:0]    maximum_occupancy,
    output reg           overflow_error
);
    (* ram_style = "distributed" *) reg [15:0] bank0 [0:15];
    (* ram_style = "distributed" *) reg [15:0] bank1 [0:15];
    (* ram_style = "distributed" *) reg [15:0] bank2 [0:15];
    (* ram_style = "distributed" *) reg [15:0] bank3 [0:15];
    (* ram_style = "distributed" *) reg [15:0] bank4 [0:15];
    (* ram_style = "distributed" *) reg [15:0] bank5 [0:15];
    (* ram_style = "distributed" *) reg [15:0] bank6 [0:15];
    (* ram_style = "distributed" *) reg [15:0] bank7 [0:15];
    (* ram_style = "distributed" *) reg [15:0] bank8 [0:15];
    (* ram_style = "distributed" *) reg [15:0] bank9 [0:15];
    (* ram_style = "distributed" *) reg [15:0] bank10 [0:15];
    (* ram_style = "distributed" *) reg [15:0] bank11 [0:15];
    (* ram_style = "distributed" *) reg [15:0] bank12 [0:15];
    (* ram_style = "distributed" *) reg [15:0] bank13 [0:15];
    (* ram_style = "distributed" *) reg [15:0] bank14 [0:15];
    (* ram_style = "distributed" *) reg [15:0] bank15 [0:15];

    wire [3:0] base_row = read_base_index[7:4];
    wire [3:0] base_bank = read_base_index[3:0];
    wire [3:0] bank0_row = base_row + (base_bank > 4'd0);
    wire [3:0] bank1_row = base_row + (base_bank > 4'd1);
    wire [3:0] bank2_row = base_row + (base_bank > 4'd2);
    wire [3:0] bank3_row = base_row + (base_bank > 4'd3);
    wire [3:0] bank4_row = base_row + (base_bank > 4'd4);
    wire [3:0] bank5_row = base_row + (base_bank > 4'd5);
    wire [3:0] bank6_row = base_row + (base_bank > 4'd6);
    wire [3:0] bank7_row = base_row + (base_bank > 4'd7);
    wire [3:0] bank8_row = base_row + (base_bank > 4'd8);
    wire [3:0] bank9_row = base_row + (base_bank > 4'd9);
    wire [3:0] bank10_row = base_row + (base_bank > 4'd10);
    wire [3:0] bank11_row = base_row + (base_bank > 4'd11);
    wire [3:0] bank12_row = base_row + (base_bank > 4'd12);
    wire [3:0] bank13_row = base_row + (base_bank > 4'd13);
    wire [3:0] bank14_row = base_row + (base_bank > 4'd14);
    wire [3:0] bank15_row = base_row;

    wire [255:0] physical_bank_words = {
        bank15[bank15_row], bank14[bank14_row],
        bank13[bank13_row], bank12[bank12_row],
        bank11[bank11_row], bank10[bank10_row],
        bank9[bank9_row], bank8[bank8_row],
        bank7[bank7_row], bank6[bank6_row],
        bank5[bank5_row], bank4[bank4_row],
        bank3[bank3_row], bank2[bank2_row],
        bank1[bank1_row], bank0[bank0_row]
    };
    wire [255:0] rotate_by_1 = base_bank[0] ?
        {physical_bank_words[15:0], physical_bank_words[255:16]} :
        physical_bank_words;
    wire [255:0] rotate_by_2 = base_bank[1] ?
        {rotate_by_1[31:0], rotate_by_1[255:32]} :
        rotate_by_1;
    wire [255:0] rotate_by_4 = base_bank[2] ?
        {rotate_by_2[63:0], rotate_by_2[255:64]} :
        rotate_by_2;
    wire [255:0] rotate_by_8 = base_bank[3] ?
        {rotate_by_4[127:0], rotate_by_4[255:128]} :
        rotate_by_4;

    assign write_ready = !overflow_error;
    assign read_window = rotate_by_8;

    always @(posedge clk) begin
        if (rst_n && !clear && write4_valid && write_ready) begin
            // OP4 quad writes are aligned groups of four distributed-RAM
            // banks. Each physical bank still receives at most one write.
            case (write_index[3:2])
                2'd0: begin
                    bank0[write_index[7:4]] <= write_data;
                    bank1[write_index[7:4]] <= write2_data;
                    bank2[write_index[7:4]] <= write3_data;
                    bank3[write_index[7:4]] <= write4_data;
                end
                2'd1: begin
                    bank4[write_index[7:4]] <= write_data;
                    bank5[write_index[7:4]] <= write2_data;
                    bank6[write_index[7:4]] <= write3_data;
                    bank7[write_index[7:4]] <= write4_data;
                end
                2'd2: begin
                    bank8[write_index[7:4]] <= write_data;
                    bank9[write_index[7:4]] <= write2_data;
                    bank10[write_index[7:4]] <= write3_data;
                    bank11[write_index[7:4]] <= write4_data;
                end
                2'd3: begin
                    bank12[write_index[7:4]] <= write_data;
                    bank13[write_index[7:4]] <= write2_data;
                    bank14[write_index[7:4]] <= write3_data;
                    bank15[write_index[7:4]] <= write4_data;
                end
                default: begin end
            endcase
        end
        else if (rst_n && !clear && write2_valid && write_ready) begin
            // Paired OP4 writes are always aligned even/odd bank pairs.  One
            // branch per physical bank preserves a single write port, allowing
            // Vivado to keep every 16x16 bank in distributed RAM.
            case (write_index[3:1])
                3'd0: begin
                    bank0[write_index[7:4]] <= write_data;
                    bank1[write_index[7:4]] <= write2_data;
                end
                3'd1: begin
                    bank2[write_index[7:4]] <= write_data;
                    bank3[write_index[7:4]] <= write2_data;
                end
                3'd2: begin
                    bank4[write_index[7:4]] <= write_data;
                    bank5[write_index[7:4]] <= write2_data;
                end
                3'd3: begin
                    bank6[write_index[7:4]] <= write_data;
                    bank7[write_index[7:4]] <= write2_data;
                end
                3'd4: begin
                    bank8[write_index[7:4]] <= write_data;
                    bank9[write_index[7:4]] <= write2_data;
                end
                3'd5: begin
                    bank10[write_index[7:4]] <= write_data;
                    bank11[write_index[7:4]] <= write2_data;
                end
                3'd6: begin
                    bank12[write_index[7:4]] <= write_data;
                    bank13[write_index[7:4]] <= write2_data;
                end
                3'd7: begin
                    bank14[write_index[7:4]] <= write_data;
                    bank15[write_index[7:4]] <= write2_data;
                end
                default: begin end
            endcase
        end
        else if (rst_n && !clear && write_valid && write_ready) begin
            case (write_index[3:0])
                4'd0: bank0[write_index[7:4]] <= write_data;
                4'd1: bank1[write_index[7:4]] <= write_data;
                4'd2: bank2[write_index[7:4]] <= write_data;
                4'd3: bank3[write_index[7:4]] <= write_data;
                4'd4: bank4[write_index[7:4]] <= write_data;
                4'd5: bank5[write_index[7:4]] <= write_data;
                4'd6: bank6[write_index[7:4]] <= write_data;
                4'd7: bank7[write_index[7:4]] <= write_data;
                4'd8: bank8[write_index[7:4]] <= write_data;
                4'd9: bank9[write_index[7:4]] <= write_data;
                4'd10: bank10[write_index[7:4]] <= write_data;
                4'd11: bank11[write_index[7:4]] <= write_data;
                4'd12: bank12[write_index[7:4]] <= write_data;
                4'd13: bank13[write_index[7:4]] <= write_data;
                4'd14: bank14[write_index[7:4]] <= write_data;
                4'd15: bank15[write_index[7:4]] <= write_data;
                default: begin end
            endcase
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            live_count <= 9'd0;
            maximum_occupancy <= 9'd0;
            overflow_error <= 1'b0;
        end
        else if (clear) begin
            live_count <= 9'd0;
            overflow_error <= 1'b0;
        end
        else if ((write_valid || write2_valid || write3_valid || write4_valid) &&
                 write_ready) begin
            if (write4_valid) begin
                if ({1'b0, write4_index} >= live_count)
                    live_count <= {1'b0, write4_index} + 1'b1;
                if (({1'b0, write4_index} + 1'b1) > maximum_occupancy)
                    maximum_occupancy <= {1'b0, write4_index} + 1'b1;
            end
            else if (write3_valid) begin
                if ({1'b0, write3_index} >= live_count)
                    live_count <= {1'b0, write3_index} + 1'b1;
                if (({1'b0, write3_index} + 1'b1) > maximum_occupancy)
                    maximum_occupancy <= {1'b0, write3_index} + 1'b1;
            end
            else if (write2_valid &&
                (!write_valid || (write2_index > write_index))) begin
                if ({1'b0, write2_index} >= live_count)
                    live_count <= {1'b0, write2_index} + 1'b1;
                if (({1'b0, write2_index} + 1'b1) > maximum_occupancy)
                    maximum_occupancy <= {1'b0, write2_index} + 1'b1;
            end
            else begin
                if ({1'b0, write_index} >= live_count)
                    live_count <= {1'b0, write_index} + 1'b1;
                if (({1'b0, write_index} + 1'b1) > maximum_occupancy)
                    maximum_occupancy <= {1'b0, write_index} + 1'b1;
            end
        end
    end
endmodule
`default_nettype wire
