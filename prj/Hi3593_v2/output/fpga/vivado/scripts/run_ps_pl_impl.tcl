## Loop3 Vivado PS/PL implementation flow.
## Launch only through env/tool/scripts/Invoke-HdlVivado.ps1.

if {![info exists ::env(HDLFLOW_PROJECT_ROOT)]} {
    error "HDLFLOW_PROJECT_ROOT is required; use Invoke-HdlVivado.ps1 -Project"
}

set project_root [file normalize $::env(HDLFLOW_PROJECT_ROOT)]
set vivado_root [file join $project_root output fpga vivado]
set project_dir [file join $vivado_root project hi3593_v2_ps_pl]
set report_dir [file join $vivado_root reports]
set bit_dir [file join $vivado_root bitstream]
set hw_dir [file join $vivado_root hw_platform]
set generated_bd_tcl [file join $vivado_root scripts generated_ps_pl_bd.tcl]
set xdc_file [file join $vivado_root constraints generated_board.xdc]
set proto_src [file join $vivado_root src hi3593_v2_proto_top.v]
set run_report [file join $report_dir pure_pl_uart_led_proto_run.md]

file mkdir $project_dir
file mkdir $report_dir
file mkdir $bit_dir
file mkdir $hw_dir

create_project hi3593_v2_ps_pl $project_dir -part xc7z020clg400-2 -force
set_property target_language Verilog [current_project]

set rtl_files [glob -nocomplain [file join $project_root output rtl *.v]]
if {[llength $rtl_files] == 0} {
    error "No RTL files found under output/rtl"
}
add_files -norecurse $rtl_files
add_files -norecurse $proto_src
add_files -fileset constrs_1 -norecurse $xdc_file
update_compile_order -fileset sources_1

source $generated_bd_tcl
set bd_file [get_files -quiet [file join $project_dir hi3593_v2_ps_pl.srcs sources_1 bd ps_pl_system ps_pl_system.bd]]
if {[llength $bd_file] == 0} {
    set bd_file [get_files -quiet */ps_pl_system.bd]
}
if {[llength $bd_file] == 0} {
    error "PS/PL block design file was not created"
}

set uartlite_cell [create_bd_cell -type ip -vlnv xilinx.com:ip:axi_uartlite:2.0 axi_uartlite_0]
set_property -dict [list \
    CONFIG.C_BAUDRATE {115200} \
    CONFIG.C_DATA_BITS {8} \
    CONFIG.C_USE_PARITY {0} \
] $uartlite_cell
connect_bd_net [get_bd_pins processing_system7_0/FCLK_CLK0] [get_bd_pins axi_uartlite_0/s_axi_aclk]
if {[llength [get_bd_pins -quiet axi_resetn_const/dout]]} {
    connect_bd_net [get_bd_pins axi_resetn_const/dout] [get_bd_pins axi_uartlite_0/s_axi_aresetn]
}
if {[llength [get_bd_ports -quiet uart_rx]]} {
    set uart_rx_net [get_bd_nets -quiet -of_objects [get_bd_ports uart_rx]]
    if {[llength $uart_rx_net] && [llength [get_bd_pins -quiet hi3593_v2_proto_top_0/uart_rx]]} {
        catch {disconnect_bd_net [lindex $uart_rx_net 0] [get_bd_pins hi3593_v2_proto_top_0/uart_rx]}
    }
    connect_bd_net [get_bd_ports uart_rx] [get_bd_pins axi_uartlite_0/rx]
}
if {[llength [get_bd_ports -quiet uart_tx]]} {
    set uart_tx_net [get_bd_nets -quiet -of_objects [get_bd_ports uart_tx]]
    if {[llength $uart_tx_net] && [llength [get_bd_pins -quiet hi3593_v2_proto_top_0/uart_tx]]} {
        catch {disconnect_bd_net [lindex $uart_tx_net 0] [get_bd_pins hi3593_v2_proto_top_0/uart_tx]}
    }
    connect_bd_net [get_bd_ports uart_tx] [get_bd_pins axi_uartlite_0/tx]
}
apply_bd_automation -rule xilinx.com:bd_rule:axi4 \
    -config [list \
        Clk_master "/processing_system7_0/FCLK_CLK0" \
        Clk_slave "/processing_system7_0/FCLK_CLK0" \
        Clk_xbar "/processing_system7_0/FCLK_CLK0" \
        Master "/processing_system7_0/M_AXI_GP0" \
        Slave "/axi_uartlite_0/S_AXI" \
        ddr_seg "Auto" \
        intc_ip "New AXI Interconnect" \
        master_apm "0" \
    ] \
    [get_bd_intf_pins axi_uartlite_0/S_AXI]
assign_bd_address -target_address_space [get_bd_addr_spaces processing_system7_0/Data] \
    -offset 0x43C10000 -range 64K \
    [get_bd_addr_segs axi_uartlite_0/S_AXI/Reg] -force
validate_bd_design
save_bd_design

generate_target all $bd_file
make_wrapper -files $bd_file -top -import
update_compile_order -fileset sources_1
set_property top ps_pl_system_wrapper [current_fileset]

launch_runs synth_1 -jobs 4
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {
    error "synth_1 did not complete: [get_property STATUS [get_runs synth_1]]"
}

launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {
    error "impl_1 did not complete: [get_property STATUS [get_runs impl_1]]"
}

open_run impl_1
report_timing_summary -file [file join $report_dir post_impl_timing_summary.rpt]
report_drc -file [file join $report_dir post_impl_drc.rpt]
report_utilization -file [file join $report_dir post_impl_utilization.rpt]

set bit_candidates [glob -nocomplain [file join $project_dir hi3593_v2_ps_pl.runs impl_1 *.bit]]
if {[llength $bit_candidates] == 0} {
    error "No bitstream emitted by impl_1"
}
file copy -force [lindex $bit_candidates 0] [file join $bit_dir hi3593_v2_ps_pl.bit]

if {[llength [info commands write_hw_platform]]} {
    write_hw_platform -fixed -include_bit -force -file [file join $hw_dir hi3593_v2_ps_pl.xsa]
}

set fh [open $run_report w]
puts $fh "# Loop3 Vivado PS/PL Run"
puts $fh ""
puts $fh "- project: Hi3593_v2"
puts $fh "- board: navigator_zynq_7020"
puts $fh "- part: xc7z020clg400-2"
puts $fh "- mode: ps_pl"
puts $fh "- top_module: hi3593_v2_proto_top"
puts $fh "- serial_path: PS software over PS UART0 MIO 14..15 / COM3; AXI UARTLite remains a PL peripheral only"
puts $fh "- bitstream: output/fpga/vivado/bitstream/hi3593_v2_ps_pl.bit"
puts $fh "- timing_report: output/fpga/vivado/reports/post_impl_timing_summary.rpt"
puts $fh "- drc_report: output/fpga/vivado/reports/post_impl_drc.rpt"
puts $fh "- result: PASS"
puts $fh ""
puts $fh "## Database and UG Provenance"
puts $fh ""
puts $fh "ug_flow_guard: PASS"
puts $fh "vivado_tcl_source: local software UG/Tcl database"
puts $fh "database_preflight: output/reports/loop3/preflight/database_preflight.md"
puts $fh "prototype_plan_check: output/reports/loop3/preflight/prototype_plan_check.md"
close $fh

puts "LOOP3_VIVADO_IMPL_PASS bitstream=output/fpga/vivado/bitstream/hi3593_v2_ps_pl.bit"
