# Loop3 Database Preflight

- project: Hi3593_v2
- board: navigator_zynq_7020
- mode: ps_pl
- tool_version: 2024.2

## Hardware Resources

### TX1IN
- alias: TX1IN -> UART3_TX (external_boundary.HI8592_driver_logic.fallback_mode=pl_sampler_readback)
- uart_tx | pin=J15 | interface=uart | TXD 端口 UART3_TX

### TX0IN
- alias: TX0IN -> UART3_TX (external_boundary.HI8592_driver_logic.fallback_mode=pl_sampler_readback)
- uart_tx | pin=J15 | interface=uart | TXD 端口 UART3_TX

### SLP
- alias: SLP -> UART3_TX (external_boundary.HI8592_driver_logic.fallback_mode=pl_sampler_readback)
- uart_tx | pin=J15 | interface=uart | TXD 端口 UART3_TX

## Vivado Tcl Commands

- create_project: Create a new project
- launch_runs: Launch a set of runs

## Vitis Guide Topics

- platform: AI Engine Development; Embedded Software Development; Getting Started with Vitis Unified Software Platform
- application: Introduction; Introduction; Introduction
- domain: Vendor; Introduction to Vitis; Versal Adaptive SoC Power Domains
- xsct: Limitations and Known Issues; Fixed Platform Design; Extensible Platform Design

## Required Use

- Run this preflight before generating Vivado or Vitis scripts.
- Script generation must cite the hardware resource rows and Tcl command rows used.
- If an item is missing, add or fix the library entry before board-specific script generation.

result: PASS
