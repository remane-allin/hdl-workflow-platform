# Loop3 Database Preflight

- project: Hi3593_v2
- board: navigator_zynq_7020
- mode: ps_pl
- tool_version: 2024.2

## Hardware Resources

### PS_KEY0
- ps_key[0] | pin=MIO12 | interface=key | PS按键KEY0
- ps_key[1] | pin=MIO11 | interface=key | PS按键KEY1

### PS_LED1
- ps_led[1] | pin=MIO8 | interface=led | PS_LED1

### PL_LED0
- led[0] | pin=H15 | interface=led | (底板)PL_LED0

### PL_GCLK_50MHZ
- PL_GCLK_50MHZ | pin= | interface=clock | Core board has a 50MHz active oscillator for PL. PL_GCLK connects to an FPGA global clock MRCC and can feed user logic or MMCM/PLL derive...

### UART3_RX
- uart_rx | pin=T19 | interface=uart | RXD 端口 UART3_RX

### UART3_TX
- uart_tx | pin=J15 | interface=uart | TXD 端口 UART3_TX

## Vivado Tcl Commands

- create_project: Create a new project
- add_files: Add sources to the active fileset
- set_property: Set property on object(s)
- create_bd_design: Create a new design and its top level hierarchy cell with the same name.
- create_bd_cell: Add an IP cell from the IP catalog, or add a new hierarchical block.
- apply_bd_automation: Runs an automation rule on an IPI object.
- assign_bd_address: Automatically assign addresses to unmapped IP
- validate_bd_design: Run Parameter Propagation for specified design or for a specific cell.
- save_bd_design: Save an existing IP subsystem design to disk file.
- launch_runs: Launch a set of runs
- report_timing_summary: Report timing summary
- report_utilization: Compute utilization of device and display report
- report_drc: Run DRC
- write_bitstream: Write a bitstream for the current design
- program_hw_devices: Program hardware devices

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
