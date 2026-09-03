// Module: eeg_bci_clock_reset_bridge
// Description: Adapts the AXI clock and active-low reset to BRAM pins.
// Scope: Structural clock/reset boundary for the hierarchy-only project top.
// Spec Trace: IF-BRAM-DATA, REQ-EEG-ARCH-001.
`timescale 1ns/1ps
`default_nettype none

module eeg_bci_clock_reset_bridge (
    input  wire axi_clock,
    input  wire axi_reset_n,
    output wire ram_clock,
    output wire ram_reset
);
    assign ram_clock = axi_clock;
    assign ram_reset = !axi_reset_n;
endmodule
`default_nettype wire
