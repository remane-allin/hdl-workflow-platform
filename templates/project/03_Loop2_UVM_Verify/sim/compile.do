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
if {![file exists [file join $project_root project_scaffold.yaml]] && [file exists [file join [pwd] project_scaffold.yaml]]} {
    set project_root [file normalize [pwd]]
    set script_dir [file join $project_root 03_Loop2_UVM_Verify sim]
}
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

set rtl_forbidden [lsort [concat \
    [glob -nocomplain [file join $rtl_dir *.sv]] \
    [glob -nocomplain [file join $rtl_dir *.svh]]]]
set tb_forbidden [lsort [concat \
    [glob -nocomplain [file join $tb_dir *.sv]] \
    [glob -nocomplain [file join $tb_dir *.svh]]]]
if {[llength $rtl_forbidden] != 0} {
    puts "ERROR: RTL must be Verilog-2001 .v only; SystemVerilog file(s) found:"
    foreach f $rtl_forbidden { puts "  $f" }
    quit -code 1
}
if {[llength $tb_forbidden] != 0} {
    puts "ERROR: directed TB must be Verilog-2001 .v only; SystemVerilog file(s) found:"
    foreach f $tb_forbidden { puts "  $f" }
    quit -code 1
}

set rtl_files [lsort [glob -nocomplain [file join $rtl_dir *.v]]]
set tb_files [lsort [glob -nocomplain [file join $tb_dir *.v]]]

if {[llength $rtl_files] == 0} {
    puts "ERROR: no RTL files found under $rtl_dir"
    quit -code 1
}

foreach f $rtl_files {
    eval vlog $vlog_opts [list $f]
}

foreach f $tb_files {
    eval vlog $vlog_opts [list $f]
}

puts "Loop2 compile.do PASS"
if {!$no_quit} {
    quit -code 0
}
