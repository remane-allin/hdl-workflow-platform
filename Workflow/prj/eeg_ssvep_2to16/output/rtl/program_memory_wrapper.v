// -----------------------------------------------------------------------------
// Module: program_memory_wrapper
// Description: Stable wrapper around one 512x64 simple-dual-port BMG used for
//              program descriptors and compiler-placed constants.
// Scope: Shared EEG/SSVEP execution overlay program storage.
// Spec Trace: REQ-RRB-003, REQ-RRB-005, REQ-RRB-007, REQ-RRB-021
// -----------------------------------------------------------------------------

`default_nettype none

module program_memory_wrapper (
    input  wire        clk,
    input  wire        reset_n,
    input  wire        session_busy,
    input  wire        load_valid,
    output wire        load_ready,
    input  wire [8:0]  load_address,
    input  wire [63:0] load_data,
    input  wire        read_valid,
    input  wire [8:0]  read_address,
    output reg         read_response_valid,
    output wire [63:0] read_response_data
);
    wire load_accept;

    assign load_ready = ~session_busy;
    assign load_accept = load_valid & load_ready;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            read_response_valid <= 1'b0;
        end
        else begin
            read_response_valid <= read_valid;
        end
    end

    program_store_bmg u_program_store_bmg (
        .clka(clk),
        .ena(load_accept),
        .wea(load_accept),
        .addra(load_address),
        .dina(load_data),
        .clkb(clk),
        .enb(read_valid),
        .addrb(read_address),
        .doutb(read_response_data)
    );
endmodule
`default_nettype wire
