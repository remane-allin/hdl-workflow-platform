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
set output_dir [file join $project_root 05_Output]
set rtl_dir [file join $output_dir rtl]
set tb_dir [file join $output_dir tb]
set runtime_dir [file join $project_root 03_Loop2_UVM_Verify _runtime]
set work_lib [file join $runtime_dir work]

file mkdir $runtime_dir
if {[file exists $work_lib]} {
    vdel -lib $work_lib -all
}
vlib $work_lib

set vlog_opts [list -work $work_lib]
if {$enable_code_coverage} {
    lappend vlog_opts +cover=bcesft
}

set rtl_files [concat \
    [glob -nocomplain [file join $rtl_dir *.v]] \
    [glob -nocomplain [file join $rtl_dir *.sv]]]
set tb_files [concat \
    [glob -nocomplain [file join $tb_dir *.v]] \
    [glob -nocomplain [file join $tb_dir *.sv]]]

if {[llength $rtl_files] == 0} {
    puts "ERROR: no RTL files found under $rtl_dir"
    quit -code 1
}

foreach f $rtl_files {
    eval vlog $vlog_opts [list $f]
}

foreach f $tb_files {
    if {[string match *.sv $f]} {
        eval vlog -sv $vlog_opts [list $f]
    } else {
        eval vlog $vlog_opts [list $f]
    }
}

puts "Loop2 compile.do PASS"
if {!$no_quit} {
    quit -code 0
}
