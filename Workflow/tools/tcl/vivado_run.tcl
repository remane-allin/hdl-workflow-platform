if {$argc != 5} {
    error "usage: vivado_run.tcl context.tcl stage action project.tcl report.tcl"
}
set context_file [file normalize [lindex $argv 0]]
set wf_stage [lindex $argv 1]
set wf_action [lindex $argv 2]
set project_script [file normalize [lindex $argv 3]]
set report_script [file normalize [lindex $argv 4]]
foreach required [list $context_file $project_script $report_script] {
    if {![file isfile $required]} {
        error "required Tcl file not found: $required"
    }
}
source $context_file
source $report_script

proc wf_assert_declared_files {fileset expected extensions bd_names} {
    set normalized_expected {}
    foreach path $expected {
        lappend normalized_expected [file normalize $path]
    }
    foreach object [get_files -quiet -of_objects [get_filesets $fileset]] {
        set path [file normalize $object]
        set extension [string tolower [file extension $path]]
        if {[lsearch -exact $extensions $extension] < 0} {
            continue
        }
        if {[lsearch -exact $normalized_expected $path] >= 0} {
            continue
        }
        set generated_wrapper 0
        foreach bd_name $bd_names {
            set portable [string map {\\ /} $path]
            if {[file tail $path] eq "${bd_name}_wrapper.v" || [string first "/bd/${bd_name}/" $portable] >= 0} {
                set generated_wrapper 1
            }
        }
        if {!$generated_wrapper} {
            error "native project contains an undeclared $fileset file: $path"
        }
    }
}

proc wf_run_needs_refresh {run} {
    set value [get_property NEEDS_REFRESH $run]
    return [expr {$value eq "1" || [string equal -nocase $value "true"]}]
}

proc wf_generate_supported_targets {object desired label} {
    set supported [get_property SUPPORTED_TARGETS $object]
    if {[llength $supported] == 0} {
        set supported [list_targets $object]
    }
    set targets {}
    foreach target $desired {
        if {[lsearch -exact $supported $target] >= 0} {
            lappend targets $target
        }
    }
    if {[llength $targets] == 0} {
        if {[string match *.bd [get_property NAME $object]]} {
            set targets all
        } else {
            error "$label exposes none of the required generation targets"
        }
    }
    generate_target $targets $object
}

source $project_script
if {[llength [info commands wf_project_sync]] != 1} {
    error "project.tcl must define wf_project_sync"
}
wf_project_sync
if {[current_project -quiet] eq ""} {
    error "project sync did not leave one project open"
}
set_param general.maxThreads $wf_max_jobs
if {$wf_stage eq "sync"} {
    if {$wf_action ne "execute"} {
        error "sync only supports execute action"
    }
    update_compile_order -fileset sources_1
    update_compile_order -fileset sim_1
} elseif {$wf_stage eq "synth"} {
    set synth_run [get_runs synth_1]
    set progress [get_property PROGRESS $synth_run]
    if {$wf_action eq "prepare"} {
        if {$progress ne "100%" || [wf_run_needs_refresh $synth_run]} {
            reset_run synth_1
            set_property REPORT_STRATEGY {No Reports} $synth_run
            launch_runs synth_1 -scripts_only
            puts "WF_NATIVE_RUN=synth_1"
        } else {
            puts "WF_NATIVE_RUN="
        }
    } elseif {$wf_action eq "collect"} {
        set status [get_property STATUS $synth_run]
        if {$progress ne "100%" || [regexp -nocase {error|fail} $status]} {
            error "synth_1 failed: $status"
        }
        open_run synth_1
        wf_report_synth $wf_report_root
    } else {
        error "synth only supports prepare or collect action"
    }
} elseif {$wf_stage eq "route"} {
    set synth_run [get_runs synth_1]
    if {[get_property PROGRESS $synth_run] ne "100%" || [wf_run_needs_refresh $synth_run]} {
        error "route requires completed synth_1"
    }
    set impl_run [get_runs impl_1]
    set progress [get_property PROGRESS $impl_run]
    set status [get_property STATUS $impl_run]
    if {$wf_action eq "prepare"} {
        if {$progress ne "100%" || ![regexp {route_design Complete} $status] || [wf_run_needs_refresh $impl_run]} {
            reset_run impl_1
            set_property REPORT_STRATEGY {No Reports} $impl_run
            launch_runs impl_1 -to_step route_design -scripts_only
            puts "WF_NATIVE_RUN=impl_1"
        } else {
            puts "WF_NATIVE_RUN="
        }
    } elseif {$wf_action eq "collect"} {
        if {$progress ne "100%" || ![regexp {route_design Complete} $status]} {
            error "impl_1 failed: $status"
        }
        open_run impl_1
        wf_report_route $wf_report_root
    } else {
        error "route only supports prepare or collect action"
    }
} elseif {$wf_stage eq "release"} {
    if {$wf_action ne "execute"} {
        error "release only supports execute action"
    }
    set impl_run [get_runs impl_1]
    set status [get_property STATUS $impl_run]
    if {[get_property PROGRESS $impl_run] ne "100%" || ![regexp {route_design Complete} $status] || [wf_run_needs_refresh $impl_run]} {
        error "release requires completed routed impl_1"
    }
    open_run impl_1
    if {$wf_bitstream ne ""} {
        write_bitstream -force $wf_bitstream
    }
    if {$wf_xsa ne ""} {
        write_hw_platform -fixed -include_bit -force -file $wf_xsa
    }
} else {
    error "unsupported Vivado stage: $wf_stage"
}
close_project
exit
