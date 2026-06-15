transcript on
onerror {quit -code 1}

if {![info exists script_dir]} {
    set script_dir [file normalize [file dirname [info script]]]
}
if {![info exists project_root]} {
    set project_root [file normalize [file join $script_dir .. .. ..]]
}
if {![file exists [file join $script_dir compile.do]] && [file exists [file join [pwd] project_scaffold.yaml]]} {
    set project_root [file normalize [pwd]]
    set script_dir [file join $project_root work/loop1_rtl_tb sim]
}
if {![info exists loop1_tb_tops]} {
    set loop1_tb_tops [list loop1_tb]
}
if {![info exists loop1_dut_instance]} {
    set loop1_dut_instance dut
}
if {![info exists loop1_wave_extra_signals]} {
    set loop1_wave_extra_signals [list]
}
if {![info exists loop1_wave_extra_groups]} {
    set loop1_wave_extra_groups [list]
}
if {![info exists loop1_wave_dut_recursive]} {
    set loop1_wave_dut_recursive 0
}
set current_dir [file join $project_root work/loop1_rtl_tb current]
set log_dir [file join $current_dir log]
set runtime_dir [file join $project_root work/loop1_rtl_tb _runtime]
set wave_dir [file join $project_root output sim loop1 wave]
set top_wave_manifest [file join $project_root work/loop1_rtl_tb config top_wave_manifest.yaml]
file mkdir $log_dir
file mkdir $wave_dir
transcript file [file join $log_dir modelsim.log]
transcript on
puts "HDLFLOW_WAVE_MANIFEST path=$top_wave_manifest"

proc hdlflow_try_vcd_add {signal_path} {
    if {[catch {vcd add $signal_path} err]} {
        puts "HDLFLOW_WAVE_SKIP vcd_add=$signal_path reason=$err"
    }
}

proc hdlflow_try_log {signal_path} {
    if {[catch {log -r $signal_path} err]} {
        puts "HDLFLOW_WAVE_SKIP log=$signal_path reason=$err"
    }
}

proc hdlflow_add_wave_group {group_name signal_path recursive} {
    if {$recursive} {
        set vcd_cmd [list vcd add -r $signal_path]
    } else {
        set vcd_cmd [list vcd add $signal_path]
    }
    if {[catch {{*}$vcd_cmd} err]} {
        puts "HDLFLOW_WAVE_SKIP group=$group_name vcd_add=$signal_path reason=$err"
    } else {
        puts "HDLFLOW_WAVE_GROUP name=$group_name scope=$signal_path recursive=$recursive"
    }
    hdlflow_try_log $signal_path
}

set no_quit 1
do [file join $script_dir compile.do]
unset no_quit

set work_lib [file join $project_root work/loop1_rtl_tb _runtime work]
foreach tb_top $loop1_tb_tops {
    puts "Loop1 running TB top: $tb_top"
    set safe_tb_top [string map {"/" "_" "\\" "_" ":" "_" "." "_"} $tb_top]
    set wlf_file [file join $wave_dir "${safe_tb_top}.wlf"]
    set vcd_file [file join $wave_dir "${safe_tb_top}_top.vcd"]
    vsim -wlf $wlf_file -onfinish stop -voptargs=+acc -lib $work_lib $tb_top
    set dut_scope "/$tb_top/$loop1_dut_instance"
    vcd file $vcd_file
    set default_wave_groups [list [list tb_top "/$tb_top/*" 0] [list dut_top "${dut_scope}/*" $loop1_wave_dut_recursive]]
    foreach wave_group $default_wave_groups {
        hdlflow_add_wave_group [lindex $wave_group 0] [lindex $wave_group 1] [lindex $wave_group 2]
    }
    foreach wave_group $loop1_wave_extra_groups {
        if {[llength $wave_group] < 2} {
            puts "HDLFLOW_WAVE_SKIP malformed_group=$wave_group"
        } else {
            set group_recursive 0
            if {[llength $wave_group] >= 3} {
                set group_recursive [lindex $wave_group 2]
            }
            hdlflow_add_wave_group [lindex $wave_group 0] [lindex $wave_group 1] $group_recursive
        }
    }
    foreach wave_signal $loop1_wave_extra_signals {
        hdlflow_try_vcd_add $wave_signal
        hdlflow_try_log $wave_signal
    }
    puts "HDLFLOW_WAVE_DUMP tb_top=$tb_top vcd=$vcd_file wlf=$wlf_file scope=$dut_scope"
    run -all
    catch {vcd flush}
    catch {vcd off}
    quit -sim
}

set workspace_root [file normalize [file join $project_root .. ..]]
set env(PYTHONPATH) [file join $workspace_root env core]
set refresh_cmd [list python -m hdlflow.cli loop1-refresh-reports --project $project_root]
if {[catch {eval exec $refresh_cmd} refresh_out]} {
    puts $refresh_out
    quit -code 1
}
puts $refresh_out
set waveform_cmd [list python -m hdlflow.cli loop1-waveform-gate --project $project_root --manifest $top_wave_manifest]
if {[catch {eval exec $waveform_cmd} waveform_out]} {
    puts $waveform_out
    puts "Loop1 waveform advisory: FAIL - review waveform_query_report.md and waveform_gate.json"
} else {
    puts $waveform_out
}
puts "Loop1 rtl_functional.do PASS"
quit -code 0
