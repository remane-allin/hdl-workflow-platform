// -----------------------------------------------------------------------------
// Module: bmg_sim_models
// Purpose: Behavioral simulation models for the six reviewed Block Memory
//          Generator instances used by the shared overlay.
// Requirements: REQ-RRB-005, REQ-RRB-007, REQ-RRB-020
// Notes: These models reproduce the configured one-cycle registered read
//        behavior. They are testbench support only and are not synthesized.
// -----------------------------------------------------------------------------

`timescale 1ns/1ps

// Behavioral model for the subset of the 7-series RAM32M primitive used by
// banked_local_state_2r1w.  Production synthesis binds the device primitive;
// directed simulation compiles this model in the testbench library.
module RAM32M #(
    parameter [63:0] INIT_A = 64'd0,
    parameter [63:0] INIT_B = 64'd0,
    parameter [63:0] INIT_C = 64'd0,
    parameter [63:0] INIT_D = 64'd0
) (
    output wire [1:0] DOA,
    output wire [1:0] DOB,
    output wire [1:0] DOC,
    output wire [1:0] DOD,
    input  wire [4:0] ADDRA,
    input  wire [4:0] ADDRB,
    input  wire [4:0] ADDRC,
    input  wire [4:0] ADDRD,
    input  wire [1:0] DIA,
    input  wire [1:0] DIB,
    input  wire [1:0] DIC,
    input  wire [1:0] DID,
    input  wire       WCLK,
    input  wire       WE
);
    reg [63:0] memory_a;
    reg [63:0] memory_b;
    reg [63:0] memory_c;
    reg [63:0] memory_d;

    initial begin
        memory_a = INIT_A;
        memory_b = INIT_B;
        memory_c = INIT_C;
        memory_d = INIT_D;
    end

    assign DOA = memory_a[ADDRA*2 +: 2];
    assign DOB = memory_b[ADDRB*2 +: 2];
    assign DOC = memory_c[ADDRC*2 +: 2];
    assign DOD = memory_d[ADDRD*2 +: 2];

    always @(posedge WCLK) begin
        if (WE) begin
            memory_a[ADDRD*2 +: 2] <= DIA;
            memory_b[ADDRD*2 +: 2] <= DIB;
            memory_c[ADDRD*2 +: 2] <= DIC;
            memory_d[ADDRD*2 +: 2] <= DID;
        end
    end
endmodule

module program_store_bmg (
    input  wire        clka,
    input  wire        ena,
    input  wire [0:0]  wea,
    input  wire [8:0]  addra,
    input  wire [63:0] dina,
    input  wire        clkb,
    input  wire        enb,
    input  wire [8:0]  addrb,
    output reg  [63:0] doutb
);
    reg [63:0] memory [0:511];

    always @(posedge clka) begin
        if (ena && wea[0]) begin
            memory[addra] <= dina;
        end
    end

    always @(posedge clkb) begin
        if (enb) begin
            doutb <= memory[addrb];
        end
    end
endmodule

module parameter_store_bmg (
    input  wire        clka,
    input  wire        ena,
    input  wire [0:0]  wea,
    input  wire [8:0]  addra,
    input  wire [63:0] dina,
    input  wire        clkb,
    input  wire        enb,
    input  wire [8:0]  addrb,
    output reg  [63:0] doutb
);
    reg [63:0] memory [0:511];

    always @(posedge clka) begin
        if (ena && wea[0]) begin
            memory[addra] <= dina;
        end
    end

    always @(posedge clkb) begin
        if (enb) begin
            doutb <= memory[addrb];
        end
    end
endmodule

module feature_bank0_bmg (
    input  wire        clka,
    input  wire        ena,
    input  wire [0:0]  wea,
    input  wire [10:0] addra,
    input  wire [15:0] dina,
    output reg  [15:0] douta,
    input  wire        clkb,
    input  wire        enb,
    input  wire [0:0]  web,
    input  wire [10:0] addrb,
    input  wire [15:0] dinb,
    output reg  [15:0] doutb
);
    reg [15:0] memory [0:2047];

    always @(posedge clka) begin
        if (ena) begin
            douta <= memory[addra];
            if (wea[0]) begin
                memory[addra] <= dina;
            end
        end
    end

    always @(posedge clkb) begin
        if (enb) begin
            doutb <= memory[addrb];
            if (web[0]) begin
                memory[addrb] <= dinb;
            end
        end
    end
endmodule

module feature_bank1_bmg (
    input  wire        clka,
    input  wire        ena,
    input  wire [0:0]  wea,
    input  wire [10:0] addra,
    input  wire [15:0] dina,
    output reg  [15:0] douta,
    input  wire        clkb,
    input  wire        enb,
    input  wire [0:0]  web,
    input  wire [10:0] addrb,
    input  wire [15:0] dinb,
    output reg  [15:0] doutb
);
    reg [15:0] memory [0:2047];

    always @(posedge clka) begin
        if (ena) begin
            douta <= memory[addra];
            if (wea[0]) begin
                memory[addra] <= dina;
            end
        end
    end

    always @(posedge clkb) begin
        if (enb) begin
            doutb <= memory[addrb];
            if (web[0]) begin
                memory[addrb] <= dinb;
            end
        end
    end
endmodule

module feature_bank2_bmg (
    input  wire        clka,
    input  wire        ena,
    input  wire [0:0]  wea,
    input  wire [10:0] addra,
    input  wire [15:0] dina,
    output reg  [15:0] douta,
    input  wire        clkb,
    input  wire        enb,
    input  wire [0:0]  web,
    input  wire [10:0] addrb,
    input  wire [15:0] dinb,
    output reg  [15:0] doutb
);
    reg [15:0] memory [0:2047];

    always @(posedge clka) begin
        if (ena) begin
            douta <= memory[addra];
            if (wea[0]) begin
                memory[addra] <= dina;
            end
        end
    end

    always @(posedge clkb) begin
        if (enb) begin
            doutb <= memory[addrb];
            if (web[0]) begin
                memory[addrb] <= dinb;
            end
        end
    end
endmodule

module feature_bank3_bmg (
    input  wire        clka,
    input  wire        ena,
    input  wire [0:0]  wea,
    input  wire [10:0] addra,
    input  wire [15:0] dina,
    output reg  [15:0] douta,
    input  wire        clkb,
    input  wire        enb,
    input  wire [0:0]  web,
    input  wire [10:0] addrb,
    input  wire [15:0] dinb,
    output reg  [15:0] doutb
);
    reg [15:0] memory [0:2047];

    always @(posedge clka) begin
        if (ena) begin
            douta <= memory[addra];
            if (wea[0]) begin
                memory[addra] <= dina;
            end
        end
    end

    always @(posedge clkb) begin
        if (enb) begin
            doutb <= memory[addrb];
            if (web[0]) begin
                memory[addrb] <= dinb;
            end
        end
    end
endmodule
