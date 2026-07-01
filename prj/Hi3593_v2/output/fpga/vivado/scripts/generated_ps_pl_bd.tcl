## Generated PS_PL Block Design Tcl from Loop3 database/UG-gated flow.
## database_preflight: output/reports/loop3/preflight/database_preflight.md
## prototype_plan_check: output/reports/loop3/preflight/prototype_plan_check.md
## The command only runs after local Vivado Tcl and Vitis guide rows are found.
## ps7_preset: work/loop3_fpga_proto/board_profiles/navigator_zynq_7020_ps7_preset.tcl
set bd_name ps_pl_system
create_bd_design $bd_name
create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 processing_system7_0

set ps7_cell_obj [get_bd_cells processing_system7_0]
set fclk_mhz 100
source [file join $project_root work loop3_fpga_proto board_profiles navigator_zynq_7020_ps7_preset.tcl]

set_property -dict [list \
    CONFIG.PCW_USE_M_AXI_GP0 {1} \
    CONFIG.PCW_USE_CR_FABRIC {1} \
    CONFIG.PCW_EN_CLK0_PORT {1} \
    CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {100} \
    CONFIG.PCW_GPIO_MIO_GPIO_ENABLE {1} \
    CONFIG.PCW_UIPARAM_DDR_ENABLE {1} \
    CONFIG.PCW_UIPARAM_DDR_BUS_WIDTH {32 Bit} \
    CONFIG.PCW_USE_S_AXI_HP0 {0} \
    CONFIG.PCW_USE_S_AXI_HP1 {0} \
] [get_bd_cells processing_system7_0]

apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 \
    -config {make_external "FIXED_IO, DDR" apply_board_preset "0" Master "Disable" Slave "Disable"} \
    [get_bd_cells processing_system7_0]

create_bd_cell -type module -reference hi3593_v2_proto_top hi3593_v2_proto_top_0
connect_bd_net [get_bd_pins processing_system7_0/FCLK_CLK0] [get_bd_pins processing_system7_0/M_AXI_GP0_ACLK]
connect_bd_net [get_bd_pins processing_system7_0/FCLK_CLK0] [get_bd_pins hi3593_v2_proto_top_0/s00_axi_aclk]
if {[llength [get_bd_pins -quiet hi3593_v2_proto_top_0/s00_axi_aresetn]]} {
    create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 axi_resetn_const
    set_property -dict [list CONFIG.CONST_VAL {1} CONFIG.CONST_WIDTH {1}] [get_bd_cells axi_resetn_const]
    connect_bd_net [get_bd_pins axi_resetn_const/dout] [get_bd_pins hi3593_v2_proto_top_0/s00_axi_aresetn]
}
if {[llength [get_bd_pins -quiet hi3593_v2_proto_top_0/pl_resetn]]} {
    create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 pl_resetn_const
    set_property -dict [list CONFIG.CONST_VAL {1} CONFIG.CONST_WIDTH {1}] [get_bd_cells pl_resetn_const]
    connect_bd_net [get_bd_pins pl_resetn_const/dout] [get_bd_pins hi3593_v2_proto_top_0/pl_resetn]
}

apply_bd_automation -rule xilinx.com:bd_rule:axi4 \
    -config [list \
        Clk_master "/processing_system7_0/FCLK_CLK0" \
        Clk_slave "/processing_system7_0/FCLK_CLK0" \
        Clk_xbar "/processing_system7_0/FCLK_CLK0" \
        Master "/processing_system7_0/M_AXI_GP0" \
        Slave "/hi3593_v2_proto_top_0/s00_axi" \
        ddr_seg "Auto" \
        intc_ip "New AXI Interconnect" \
        master_apm "0" \
    ] \
    [get_bd_intf_pins hi3593_v2_proto_top_0/s00_axi]

set sys_clk_port [create_bd_port -dir I sys_clk]
connect_bd_net $sys_clk_port [get_bd_pins hi3593_v2_proto_top_0/sys_clk]
set uart_rx_port [create_bd_port -dir I uart_rx]
connect_bd_net $uart_rx_port [get_bd_pins hi3593_v2_proto_top_0/uart_rx]
set uart_tx_port [create_bd_port -dir O uart_tx]
connect_bd_net $uart_tx_port [get_bd_pins hi3593_v2_proto_top_0/uart_tx]
set pl_led0_port [create_bd_port -dir O pl_led0]
connect_bd_net $pl_led0_port [get_bd_pins hi3593_v2_proto_top_0/pl_led0]

assign_bd_address -target_address_space [get_bd_addr_spaces processing_system7_0/Data] \
    -offset 0x43C00000 -range 64K \
    [get_bd_addr_segs hi3593_v2_proto_top_0/s00_axi/reg0] -force

validate_bd_design
save_bd_design
## first_axi_region=pl_ctrl
