//==============================================================================
// Module      : banked_local_state_2r1w
// Project     : eeg_ssvep_2to16
// Description : Compact technology-boundary local-state macro.
// Scope:
//   - Two parity banks, eight 128-bit rows per bank.
//   - Two asynchronous reads and one masked synchronous write per bank.
//   - FPGA maps explicitly to multiport LUTRAM; an ASIC implementation replaces
//     only this module with an equivalent 2R1W register-file macro.
//   - No descriptor, signal-profile, or scheduling decode.
// Spec Trace:
//   - REQ-RRB-006, REQ-RRB-012, REQ-RRB-019, REQ-RRB-023
//   - MOD-LOCAL-STATE, IF-LOCAL-STATE
// Contract:
//   - Reads observing a write edge see the old row on that edge.
//   - A single write command selects one parity bank.  A dual-bank command
//     writes both halves of a 256-bit solve return at the same row index.
//   - One RAM32M stores two identical 2-bit low-state copies: A serves read0,
//     B serves read1, and ADDRD is the common write address.
//==============================================================================
`timescale 1ns/1ps
`default_nettype none

module banked_local_state_2r1w (
    input  wire         clk,
    input  wire [2:0]   read0_index,
    output wire [127:0] even_read0_data,
    input  wire [2:0]   read1_index,
    output wire [127:0] even_read1_data,
    output wire [127:0] odd_read0_data,
    output wire [127:0] odd_read1_data,
    input  wire         write_enable,
    input  wire         write_dual_bank,
    input  wire         write_bank,
    input  wire [2:0]   write_index,
    input  wire [7:0]   write_mask,
    input  wire [127:0] write_even_data,
    input  wire [127:0] write_odd_data
);
    wire even_write_enable;
    wire odd_write_enable;

    assign even_write_enable = write_enable &&
                               (write_dual_bank || !write_bank);
    assign odd_write_enable = write_enable &&
                              (write_dual_bank || write_bank);

    // Keep the macro behavioral boundary simple and let implementation clone
    // address drivers where placement requires it.  Forced LUT1 fanout trees
    // add a logic level to every asynchronous read and prevent the placer from
    // choosing the replication points from actual RAM32M locations.
    genvar pair_index;
    generate
        for (pair_index = 0; pair_index < 64;
             pair_index = pair_index + 1) begin : gen_state_pair
                wire [1:0] even_read0_pair;
                wire [1:0] even_read1_pair;
                wire [1:0] odd_read0_pair;
                wire [1:0] odd_read1_pair;
                wire [1:0] unused_even_c;
                wire [1:0] unused_even_d;
                wire [1:0] unused_odd_c;
                wire [1:0] unused_odd_d;
                wire [1:0] even_write_pair;
                wire [1:0] odd_write_pair;

                assign even_write_pair =
                    write_even_data[pair_index*2 +: 2];
                assign odd_write_pair =
                    write_odd_data[pair_index*2 +: 2];

                RAM32M #(
                    .INIT_A(64'd0), .INIT_B(64'd0),
                    .INIT_C(64'd0), .INIT_D(64'd0)
                ) u_even_state (
                    .DOA(even_read0_pair),
                    .DOB(even_read1_pair),
                    .DOC(unused_even_c),
                    .DOD(unused_even_d),
                    .ADDRA({2'b00, read0_index}),
                    .ADDRB({2'b00, read1_index}),
                    .ADDRC(5'd0),
                    .ADDRD({2'b00, write_index}),
                    .DIA(even_write_pair),
                    .DIB(even_write_pair),
                    .DIC(2'd0),
                    .DID(2'd0),
                    .WCLK(clk),
                    .WE(even_write_enable && write_mask[pair_index/8])
                );

                RAM32M #(
                    .INIT_A(64'd0), .INIT_B(64'd0),
                    .INIT_C(64'd0), .INIT_D(64'd0)
                ) u_odd_state (
                    .DOA(odd_read0_pair),
                    .DOB(odd_read1_pair),
                    .DOC(unused_odd_c),
                    .DOD(unused_odd_d),
                    .ADDRA({2'b00, read0_index}),
                    .ADDRB({2'b00, read1_index}),
                    .ADDRC(5'd0),
                    .ADDRD({2'b00, write_index}),
                    .DIA(odd_write_pair),
                    .DIB(odd_write_pair),
                    .DIC(2'd0),
                    .DID(2'd0),
                    .WCLK(clk),
                    .WE(odd_write_enable && write_mask[pair_index/8])
                );

                assign even_read0_data[pair_index*2 +: 2] =
                    even_read0_pair;
                assign even_read1_data[pair_index*2 +: 2] =
                    even_read1_pair;
                assign odd_read0_data[pair_index*2 +: 2] =
                    odd_read0_pair;
                assign odd_read1_data[pair_index*2 +: 2] =
                    odd_read1_pair;
        end
    endgenerate
endmodule
`default_nettype wire
