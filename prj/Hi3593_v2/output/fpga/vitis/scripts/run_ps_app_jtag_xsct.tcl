## Loop3 PS app JTAG launch flow.
## Launch through env/tool/scripts/Invoke-HdlVitis.ps1 -Tool xsct.

set script_dir [file dirname [file normalize [info script]]]
set project_root [file normalize [file join $script_dir .. .. .. ..]]
set workspace_dir [file join $project_root output fpga vitis workspace]
set report_dir [file join $project_root output reports loop3]
set log_stamp [clock format [clock seconds] -format "%Y%m%d_%H%M%S"]
set run_log [file join $report_dir ps_app_download_${log_stamp}.log]
set jtag_frequency_hz 250000
set bit_file [file join $project_root output fpga vivado bitstream hi3593_v2_ps_pl.bit]
set xsa_file [file join $project_root output fpga vivado hw_platform hi3593_v2_ps_pl.xsa]

file mkdir $report_dir

proc loop3_try_set_jtag_frequency {frequency_hz} {
    if {![string length $frequency_hz]} {
        return
    }
    set target_status [catch {jtag targets} target_result]
    puts "LOOP3_JTAG_TARGETS status=$target_status"
    if {[string length $target_result]} {
        puts $target_result
    }
    set select_status [catch {jtag targets -set -filter {level == 0}} select_result]
    if {$select_status != 0} {
        set select_status [catch {jtag targets 1} select_result]
    }
    puts "LOOP3_JTAG_SCAN_CHAIN_SELECT status=$select_status result=$select_result"
    set list_status [catch {jtag frequency -list} list_result]
    puts "LOOP3_JTAG_FREQUENCY_LIST status=$list_status result=$list_result"
    set freq_status [catch {jtag frequency $frequency_hz} freq_result]
    puts "LOOP3_JTAG_FREQUENCY_SET status=$freq_status result=$freq_result requested=$frequency_hz"
}

proc loop3_reconnect_target {frequency_hz} {
    set disconnect_status [catch {disconnect} disconnect_result]
    puts "LOOP3_XSDB_DISCONNECT status=$disconnect_status result=$disconnect_result"
    after 2000
    set connect_status [catch {connect} connect_result]
    puts "LOOP3_XSDB_RECONNECT status=$connect_status result=$connect_result"
    if {$connect_status != 0} {
        error "XSDB reconnect failed"
    }
    after 1000
    loop3_try_set_jtag_frequency $frequency_hz
}

proc loop3_select_arm_target {frequency_hz} {
    set arm_filter {name =~ "ARM*#0"}
    set status [catch {targets -set -filter $arm_filter} result]
    if {$status == 0} {
        return
    }

    puts "LOOP3_ARM_TARGET_INITIAL_SELECT_FAIL result=$result"
    set dump_status [catch {targets} dump_result]
    puts "LOOP3_TARGETS_BEFORE_RECOVERY status=$dump_status"
    if {[string length $dump_result]} {
        puts $dump_result
    }

    set dap_status [catch {targets -set -filter {name =~ "DAP*"}} dap_result]
    puts "LOOP3_DAP_SELECT status=$dap_status result=$dap_result"
    if {$dap_status == 0} {
        set reset_status [catch {rst -dap} reset_result]
        puts "LOOP3_DAP_RESET status=$reset_status result=$reset_result"
        after 1000
        set dump_status [catch {targets} dump_result]
        puts "LOOP3_TARGETS_AFTER_DAP_RESET status=$dump_status"
        if {[string length $dump_result]} {
            puts $dump_result
        }
        set apu_status [catch {targets -set -filter {name =~ "APU"}} apu_result]
        puts "LOOP3_APU_SELECT_AFTER_DAP status=$apu_status result=$apu_result"
        if {$apu_status == 0} {
            set system_status [catch {rst -system} system_result]
            puts "LOOP3_APU_SYSTEM_RESET status=$system_status result=$system_result"
            after 1000
            if {$system_status != 0} {
                set srst_status [catch {rst -srst} srst_result]
                puts "LOOP3_APU_SRST_RESET status=$srst_status result=$srst_result"
                after 3000
                if {$srst_status != 0} {
                    set por_status [catch {rst -por} por_result]
                    puts "LOOP3_APU_POR_RESET status=$por_status result=$por_result"
                    after 5000
                }
                loop3_reconnect_target $frequency_hz
                set dump_status [catch {targets} dump_result]
                puts "LOOP3_TARGETS_AFTER_STRONG_RESET status=$dump_status"
                if {[string length $dump_result]} {
                    puts $dump_result
                }
            }
        }
        loop3_try_set_jtag_frequency $frequency_hz
        set status [catch {targets -set -filter $arm_filter} result]
        if {$status == 0} {
            return
        }
        puts "LOOP3_ARM_TARGET_AFTER_DAP_RESET_FAIL result=$result"
        set reset_status [catch {rst -system} reset_result]
        puts "LOOP3_DAP_SYSTEM_RESET status=$reset_status result=$reset_result"
        after 1000
        loop3_try_set_jtag_frequency $frequency_hz
    }

    set status [catch {targets -set -filter $arm_filter} result]
    if {$status != 0} {
        set dump_status [catch {targets} dump_result]
        puts "LOOP3_TARGETS_AFTER_RECOVERY status=$dump_status"
        if {[string length $dump_result]} {
            puts $dump_result
        }
        error $result
    }
}

set elf_candidates [glob -nocomplain [file join $workspace_dir hi3593_v2_loop3_app Debug *.elf]]
if {[llength $elf_candidates] == 0} {
    set elf_candidates [glob -nocomplain [file join $workspace_dir hi3593_v2_loop3_app *.elf]]
}
if {[llength $elf_candidates] == 0} {
    error "Missing PS application ELF; run build_ps_app_xsct.tcl first"
}
if {![file exists $bit_file]} {
    error "Missing bitstream: $bit_file"
}
if {![file exists $xsa_file]} {
    error "Missing XSA: $xsa_file"
}
set elf_path [file normalize [lindex $elf_candidates 0]]
set ps7_init_candidates [list \
    [file join $workspace_dir hi3593_v2_loop3_app _ide psinit ps7_init.tcl] \
    [file join $workspace_dir hi3593_v2_hw export hi3593_v2_hw hw ps7_init.tcl]]
set ps7_init_tcl ""
foreach candidate $ps7_init_candidates {
    if {[file exists $candidate]} {
        set ps7_init_tcl [file normalize $candidate]
        break
    }
}
if {$ps7_init_tcl eq ""} {
    error "Missing PS7 init Tcl; run build_ps_app_xsct.tcl first"
}

connect
loop3_try_set_jtag_frequency $jtag_frequency_hz
loop3_select_arm_target $jtag_frequency_hz

set reset_status [catch {rst} reset_result]
puts "LOOP3_SYSTEM_RESET_PRE_FPGA status=$reset_status result=$reset_result"
after 1000
loop3_try_set_jtag_frequency $jtag_frequency_hz

set fpga_status [catch {fpga -file $bit_file} fpga_result]
puts "LOOP3_XSDB_FPGA_CONFIG status=$fpga_status result=$fpga_result"
if {$fpga_status != 0} {
    error "XSDB FPGA configuration failed"
}
after 1000
loop3_try_set_jtag_frequency $jtag_frequency_hz

loop3_select_arm_target $jtag_frequency_hz
set loadhw_status [catch {loadhw -hw $xsa_file} loadhw_result]
puts "LOOP3_XSDB_LOADHW status=$loadhw_status result=$loadhw_result"
if {$loadhw_status != 0} {
    error "XSDB loadhw failed"
}

loop3_select_arm_target $jtag_frequency_hz
set stop_status [catch {stop} stop_result]
puts "LOOP3_ARM_STOP_BEFORE_PS7_INIT status=$stop_status result=$stop_result"
source $ps7_init_tcl
set ps7_init_status [catch {ps7_init} ps7_init_result]
puts "LOOP3_PS7_INIT status=$ps7_init_status result=$ps7_init_result"
if {$ps7_init_status != 0} {
    error "ps7_init failed"
}
set ps7_post_status [catch {ps7_post_config} ps7_post_result]
puts "LOOP3_PS7_POST_CONFIG status=$ps7_post_status result=$ps7_post_result"
if {$ps7_post_status != 0} {
    error "ps7_post_config failed"
}

loop3_select_arm_target $jtag_frequency_hz
dow $elf_path
con

set fh [open $run_log w]
puts $fh "LOOP3_PS_APP_DOWNLOAD_PASS elf=$elf_path"
puts $fh "LOOP3_JTAG_FREQUENCY_HZ $jtag_frequency_hz"
close $fh
puts "LOOP3_PS_APP_DOWNLOAD_PASS log=$run_log"
