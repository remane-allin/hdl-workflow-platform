transcript on
onerror {quit -code 1}

if {![info exists no_quit]} {
    set no_quit 0
}
if {![info exists enable_code_coverage]} {
    set enable_code_coverage 0
}

set script_dir [file normalize [file dirname [info script]]]
set project_root [file normalize [file join $script_dir .. ..]]
set rtl_dir [file join $project_root 05_Output rtl]
set tb_dir [file join $project_root 05_Output tb]
set runtime_dir [file join $project_root 02_Loop1_RTL_TB _runtime]
set work_lib [file join $runtime_dir work]

file mkdir $runtime_dir
if {[file exists $work_lib]} {
    vdel -lib $work_lib -all
}
vlib $work_lib

set vlog_opts [list -work $work_lib]
if {$enable_code_coverage} {
    lappend vlog_opts +cover=bcfst
}

set rtl_files [lsort [concat \
    [glob -nocomplain [file join $rtl_dir *.v]] \
    [glob -nocomplain [file join $rtl_dir *.sv]]]]
set tb_files [lsort [concat \
    [glob -nocomplain [file join $tb_dir *.v]] \
    [glob -nocomplain [file join $tb_dir *.sv]]]]

if {[llength $rtl_files] == 0} {
    puts "ERROR: no RTL files found under $rtl_dir"
    quit -code 1
}
if {[llength $tb_files] == 0} {
    puts "ERROR: no Loop1 TB files found under $tb_dir"
    quit -code 1
}

foreach rtl_file $rtl_files {
    if {[string match *.sv $rtl_file]} {
        eval vlog -sv $vlog_opts [list $rtl_file]
    } else {
        eval vlog $vlog_opts [list $rtl_file]
    }
}

foreach tb_file $tb_files {
    if {[string match *.sv $tb_file]} {
        eval vlog -sv $vlog_opts [list $tb_file]
    } else {
        eval vlog $vlog_opts [list $tb_file]
    }
}

puts "Loop1 compile.do PASS"
if {!$no_quit} {
    quit -code 0
}
