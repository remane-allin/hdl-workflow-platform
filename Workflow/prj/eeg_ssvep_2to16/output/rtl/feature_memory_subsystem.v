// -----------------------------------------------------------------------------
// Module: feature_memory_subsystem
// Description: Four fixed, bank-local 2048x16 true-dual-port BMG wrappers.
//              Logical word address bits [1:0] select the externally fixed bank
//              pin and bits [12:2] select the physical row inside that bank.
// Scope: Shared feature/frame storage with eight aggregate word ports.
// Spec Trace: REQ-RRB-007, REQ-RRB-009, REQ-RRB-019, REQ-RRB-020, REQ-RRB-022
// -----------------------------------------------------------------------------

`default_nettype none

module feature_memory_subsystem (
    input  wire        clk,
    input  wire        reset_n,

    input  wire        bank0_a_valid,
    input  wire        bank0_a_write,
    input  wire [12:0] bank0_a_address,
    input  wire [15:0] bank0_a_write_data,
    output reg         bank0_a_response_valid,
    output wire [15:0] bank0_a_response_data,
    input  wire        bank1_a_valid,
    input  wire        bank1_a_write,
    input  wire [12:0] bank1_a_address,
    input  wire [15:0] bank1_a_write_data,
    output reg         bank1_a_response_valid,
    output wire [15:0] bank1_a_response_data,
    input  wire        bank2_a_valid,
    input  wire        bank2_a_write,
    input  wire [12:0] bank2_a_address,
    input  wire [15:0] bank2_a_write_data,
    output reg         bank2_a_response_valid,
    output wire [15:0] bank2_a_response_data,
    input  wire        bank3_a_valid,
    input  wire        bank3_a_write,
    input  wire [12:0] bank3_a_address,
    input  wire [15:0] bank3_a_write_data,
    output reg         bank3_a_response_valid,
    output wire [15:0] bank3_a_response_data,

    input  wire        bank0_b_valid,
    input  wire        bank0_b_write,
    input  wire [12:0] bank0_b_address,
    input  wire [15:0] bank0_b_write_data,
    output reg         bank0_b_response_valid,
    output wire [15:0] bank0_b_response_data,
    input  wire        bank1_b_valid,
    input  wire        bank1_b_write,
    input  wire [12:0] bank1_b_address,
    input  wire [15:0] bank1_b_write_data,
    output reg         bank1_b_response_valid,
    output wire [15:0] bank1_b_response_data,
    input  wire        bank2_b_valid,
    input  wire        bank2_b_write,
    input  wire [12:0] bank2_b_address,
    input  wire [15:0] bank2_b_write_data,
    output reg         bank2_b_response_valid,
    output wire [15:0] bank2_b_response_data,
    input  wire        bank3_b_valid,
    input  wire        bank3_b_write,
    input  wire [12:0] bank3_b_address,
    input  wire [15:0] bank3_b_write_data,
    output reg         bank3_b_response_valid,
    output wire [15:0] bank3_b_response_data
);
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            bank0_a_response_valid <= 1'b0;
            bank1_a_response_valid <= 1'b0;
            bank2_a_response_valid <= 1'b0;
            bank3_a_response_valid <= 1'b0;
            bank0_b_response_valid <= 1'b0;
            bank1_b_response_valid <= 1'b0;
            bank2_b_response_valid <= 1'b0;
            bank3_b_response_valid <= 1'b0;
        end
        else begin
            bank0_a_response_valid <= bank0_a_valid & ~bank0_a_write;
            bank1_a_response_valid <= bank1_a_valid & ~bank1_a_write;
            bank2_a_response_valid <= bank2_a_valid & ~bank2_a_write;
            bank3_a_response_valid <= bank3_a_valid & ~bank3_a_write;
            bank0_b_response_valid <= bank0_b_valid & ~bank0_b_write;
            bank1_b_response_valid <= bank1_b_valid & ~bank1_b_write;
            bank2_b_response_valid <= bank2_b_valid & ~bank2_b_write;
            bank3_b_response_valid <= bank3_b_valid & ~bank3_b_write;
        end
    end

    feature_bank0_bmg u_feature_bank0_bmg (
        .clka(clk),
        .ena(bank0_a_valid),
        .wea(bank0_a_write),
        .addra(bank0_a_address[12:2]),
        .dina(bank0_a_write_data),
        .douta(bank0_a_response_data),
        .clkb(clk),
        .enb(bank0_b_valid),
        .web(bank0_b_write),
        .addrb(bank0_b_address[12:2]),
        .dinb(bank0_b_write_data),
        .doutb(bank0_b_response_data)
    );

    feature_bank1_bmg u_feature_bank1_bmg (
        .clka(clk),
        .ena(bank1_a_valid),
        .wea(bank1_a_write),
        .addra(bank1_a_address[12:2]),
        .dina(bank1_a_write_data),
        .douta(bank1_a_response_data),
        .clkb(clk),
        .enb(bank1_b_valid),
        .web(bank1_b_write),
        .addrb(bank1_b_address[12:2]),
        .dinb(bank1_b_write_data),
        .doutb(bank1_b_response_data)
    );

    feature_bank2_bmg u_feature_bank2_bmg (
        .clka(clk),
        .ena(bank2_a_valid),
        .wea(bank2_a_write),
        .addra(bank2_a_address[12:2]),
        .dina(bank2_a_write_data),
        .douta(bank2_a_response_data),
        .clkb(clk),
        .enb(bank2_b_valid),
        .web(bank2_b_write),
        .addrb(bank2_b_address[12:2]),
        .dinb(bank2_b_write_data),
        .doutb(bank2_b_response_data)
    );

    feature_bank3_bmg u_feature_bank3_bmg (
        .clka(clk),
        .ena(bank3_a_valid),
        .wea(bank3_a_write),
        .addra(bank3_a_address[12:2]),
        .dina(bank3_a_write_data),
        .douta(bank3_a_response_data),
        .clkb(clk),
        .enb(bank3_b_valid),
        .web(bank3_b_write),
        .addrb(bank3_b_address[12:2]),
        .dinb(bank3_b_write_data),
        .doutb(bank3_b_response_data)
    );
endmodule
`default_nettype wire
