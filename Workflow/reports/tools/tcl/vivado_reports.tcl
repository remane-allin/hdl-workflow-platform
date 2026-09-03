proc wf_report_synth {report_root} {
    file mkdir $report_root
    report_utilization -file [file join $report_root synth_utilization.rpt]
}

proc wf_report_route {report_root} {
    file mkdir $report_root
    report_timing_summary -delay_type min_max -report_unconstrained -max_paths 20 \
        -file [file join $report_root route_timing.rpt]
    report_utilization -file [file join $report_root route_utilization.rpt]
    report_drc -file [file join $report_root route_drc.rpt]
    report_route_status -file [file join $report_root route_status.rpt]
    set metric_file [open [file join $report_root route_metrics.txt] w]
    set setup_paths [get_timing_paths -setup -max_paths 1]
    set hold_paths [get_timing_paths -hold -max_paths 1]
    if {[llength $setup_paths] == 0 || [llength $hold_paths] == 0} {
        close $metric_file
        error "routed design has no setup or hold timing path"
    }
    puts $metric_file "setup_wns=[get_property SLACK [lindex $setup_paths 0]]"
    puts $metric_file "hold_wns=[get_property SLACK [lindex $hold_paths 0]]"
    puts $metric_file "drc_errors=[llength [get_drc_violations -quiet -filter {SEVERITY == Error}]]"
    puts $metric_file "drc_critical_warnings=[llength [get_drc_violations -quiet -filter {SEVERITY == {Critical Warning}}]]"
    close $metric_file
}
