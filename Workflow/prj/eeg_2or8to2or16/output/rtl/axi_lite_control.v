// Module: axi_lite_control
// Description: AXI-Lite register bank for load, start, result, and counters.
// Scope: Frozen 0x00 through 0x34 control and status register contract.
// Spec Trace: IF-AXI-CTRL, REQ-EEG-PERF-001.
`timescale 1ns/1ps
`default_nettype none

module axi_lite_control #(
    parameter ADDR_WIDTH = 6
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire [ADDR_WIDTH-1:0] s_axi_awaddr,
    input  wire                  s_axi_awvalid,
    output wire                  s_axi_awready,
    input  wire [31:0]           s_axi_wdata,
    input  wire [3:0]            s_axi_wstrb,
    input  wire                  s_axi_wvalid,
    output wire                  s_axi_wready,
    output reg  [1:0]            s_axi_bresp,
    output reg                   s_axi_bvalid,
    input  wire                  s_axi_bready,
    input  wire [ADDR_WIDTH-1:0] s_axi_araddr,
    input  wire                  s_axi_arvalid,
    output wire                  s_axi_arready,
    output reg  [31:0]           s_axi_rdata,
    output reg  [1:0]            s_axi_rresp,
    output reg                   s_axi_rvalid,
    input  wire                  s_axi_rready,
    output reg  [31:0]           start_address,
    output reg  [31:0]           read_length,
    output reg  [2:0]            iport_state,
    output wire [1:0]            profile_select,
    output wire [1:0]            instruction_version,
    output wire                  reader_command_valid,
    input  wire                  reader_command_ready,
    output wire                  core_command_valid,
    input  wire                  core_command_ready,
    output reg                   clear_counters,
    output reg                   snapshot_counters,
    input  wire                  reader_busy,
    input  wire                  core_busy,
    input  wire [31:0]           classification_result,
    input  wire                  accelerator_error,
    input  wire [31:0]           total_cycles,
    input  wire [31:0]           memory_stalls,
    input  wire [31:0]           producer_stalls,
    input  wire [31:0]           consumer_stalls,
    input  wire [31:0]           mac_activity,
    input  wire [31:0]           tile_occupancy
);
    reg [ADDR_WIDTH-1:0] awaddr_hold;
    reg [31:0] wdata_hold;
    reg [3:0] wstrb_hold;
    reg aw_hold_valid;
    reg w_hold_valid;
    reg [31:0] profile_control;
    reg request_pending;
    reg [31:0] write_value;
    integer byte_index;

    assign s_axi_awready = !aw_hold_valid;
    assign s_axi_wready = !w_hold_valid;
    assign s_axi_arready = !s_axi_rvalid;
    assign profile_select = profile_control[1:0];
    assign instruction_version = profile_control[3:2];
    assign reader_command_valid = request_pending && (iport_state != 3'b000);
    assign core_command_valid = request_pending && (iport_state == 3'b000);

    always @* begin
        write_value = 32'd0;
        case (awaddr_hold[5:0])
            6'h04: write_value = start_address;
            6'h08: write_value = read_length;
            6'h0C: write_value = {29'd0, iport_state};
            6'h18: write_value = profile_control;
            default: write_value = 32'd0;
        endcase
        for (byte_index = 0; byte_index < 4; byte_index = byte_index + 1)
            if (wstrb_hold[byte_index])
                write_value[byte_index*8 +: 8] = wdata_hold[byte_index*8 +: 8];
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            awaddr_hold <= {ADDR_WIDTH{1'b0}};
            wdata_hold <= 32'd0;
            wstrb_hold <= 4'd0;
            aw_hold_valid <= 1'b0;
            w_hold_valid <= 1'b0;
            s_axi_bresp <= 2'b00;
            s_axi_bvalid <= 1'b0;
            s_axi_rdata <= 32'd0;
            s_axi_rresp <= 2'b00;
            s_axi_rvalid <= 1'b0;
            start_address <= 32'd0;
            read_length <= 32'd0;
            iport_state <= 3'd0;
            profile_control <= 32'h0000_0005;
            request_pending <= 1'b0;
            clear_counters <= 1'b0;
            snapshot_counters <= 1'b0;
        end
        else begin
            clear_counters <= 1'b0;
            snapshot_counters <= 1'b0;

            if (s_axi_awvalid && s_axi_awready) begin
                awaddr_hold <= s_axi_awaddr;
                aw_hold_valid <= 1'b1;
            end
            if (s_axi_wvalid && s_axi_wready) begin
                wdata_hold <= s_axi_wdata;
                wstrb_hold <= s_axi_wstrb;
                w_hold_valid <= 1'b1;
            end

            if (aw_hold_valid && w_hold_valid && !s_axi_bvalid) begin
                s_axi_bresp <= 2'b00;
                case (awaddr_hold[5:0])
                    6'h00: begin
                        if (write_value[0] && !request_pending)
                            request_pending <= 1'b1;
                    end
                    6'h04: start_address <= write_value;
                    6'h08: read_length <= write_value;
                    6'h0C: iport_state <= write_value[2:0];
                    6'h18: begin
                        if (!core_busy && !reader_busy &&
                            (write_value[31:4] == 0) &&
                            (write_value[1:0] <= 1) &&
                            (write_value[3:2] <= 1))
                            profile_control <= write_value;
                        else
                            s_axi_bresp <= 2'b10;
                    end
                    6'h1C: begin
                        clear_counters <= write_value[0];
                        snapshot_counters <= write_value[1];
                        if (write_value[31:2] != 0)
                            s_axi_bresp <= 2'b10;
                    end
                    default: s_axi_bresp <= 2'b10;
                endcase
                aw_hold_valid <= 1'b0;
                w_hold_valid <= 1'b0;
                s_axi_bvalid <= 1'b1;
            end

            if (s_axi_bvalid && s_axi_bready)
                s_axi_bvalid <= 1'b0;

            if ((reader_command_valid && reader_command_ready) ||
                (core_command_valid && core_command_ready))
                request_pending <= 1'b0;

            if (s_axi_arvalid && s_axi_arready) begin
                s_axi_rresp <= 2'b00;
                case (s_axi_araddr[5:0])
                    6'h00: s_axi_rdata <= {29'd0, accelerator_error,
                        (reader_busy || core_busy), request_pending};
                    6'h04: s_axi_rdata <= start_address;
                    6'h08: s_axi_rdata <= read_length;
                    6'h0C: s_axi_rdata <= {29'd0, iport_state};
                    6'h10: s_axi_rdata <= classification_result;
                    6'h14: s_axi_rdata <=
                        {8'd8, 6'd24, 5'd13, 5'd14, 4'd15, 4'b1111};
                    6'h18: s_axi_rdata <= profile_control;
                    6'h1C: s_axi_rdata <= 32'd0;
                    6'h20: s_axi_rdata <= total_cycles;
                    6'h24: s_axi_rdata <= memory_stalls;
                    6'h28: s_axi_rdata <= producer_stalls;
                    6'h2C: s_axi_rdata <= consumer_stalls;
                    6'h30: s_axi_rdata <= mac_activity;
                    6'h34: s_axi_rdata <= tile_occupancy;
                    default: begin
                        s_axi_rdata <= 32'd0;
                        s_axi_rresp <= 2'b10;
                    end
                endcase
                s_axi_rvalid <= 1'b1;
            end
            if (s_axi_rvalid && s_axi_rready)
                s_axi_rvalid <= 1'b0;
        end
    end
endmodule
`default_nettype wire
