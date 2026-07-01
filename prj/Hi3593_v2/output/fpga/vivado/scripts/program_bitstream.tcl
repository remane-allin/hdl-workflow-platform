## Loop3 Vivado board programming flow.
## Launch only through env/tool/scripts/Invoke-HdlVivado.ps1.

if {![info exists ::env(HDLFLOW_PROJECT_ROOT)]} {
    error "HDLFLOW_PROJECT_ROOT is required; use Invoke-HdlVivado.ps1 -Project"
}

set project_root [file normalize $::env(HDLFLOW_PROJECT_ROOT)]
set bit_file [file join $project_root output fpga vivado bitstream hi3593_v2_ps_pl.bit]
set report_dir [file join $project_root output reports loop3]
set report_file [file join $report_dir board_programming_report.md]
set jtag_frequency_hz 250000

if {![file exists $bit_file]} {
    error "Missing bitstream: $bit_file"
}
file mkdir $report_dir

proc loop3_open_hw_target_with_frequency {frequency_hz} {
    set targets [get_hw_targets -quiet */xilinx_tcf/Digilent/*]
    if {[llength $targets] == 0} {
        set targets [get_hw_targets -quiet]
    }
    if {[llength $targets] == 0} {
        error "No hardware targets found"
    }

    set target [lindex $targets 0]
    current_hw_target $target
    if {[string length $frequency_hz] > 0} {
        set_property PARAM.FREQUENCY $frequency_hz $target
        puts "LOOP3_JTAG_FREQUENCY_HZ $frequency_hz target=$target"
    }
    open_hw_target $target
    return $target
}

open_hw_manager
connect_hw_server
set hw_target [loop3_open_hw_target_with_frequency $jtag_frequency_hz]

set devices [get_hw_devices xc7z020*]
if {[llength $devices] == 0} {
    set devices [get_hw_devices]
}
if {[llength $devices] == 0} {
    error "No hardware devices found"
}

set device [lindex $devices 0]
current_hw_device $device
refresh_hw_device $device
set_property PROGRAM.FILE $bit_file $device
program_hw_devices $device
refresh_hw_device $device

set fh [open $report_file w]
puts $fh "# Loop3 Board Programming"
puts $fh ""
puts $fh "- project: Hi3593_v2"
puts $fh "- tool: vivado hardware manager"
puts $fh "- bitstream: output/fpga/vivado/bitstream/hi3593_v2_ps_pl.bit"
puts $fh "- hw_target: $hw_target"
puts $fh "- jtag_frequency_hz: $jtag_frequency_hz"
puts $fh "- device: $device"
puts $fh "- result: PASS"
close $fh

puts "LOOP3_BOARD_PROGRAM_PASS bitstream=$bit_file device=$device"
