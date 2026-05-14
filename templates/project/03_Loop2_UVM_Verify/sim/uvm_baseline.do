transcript on
onerror {quit -code 1}

set script_dir [file normalize [file dirname [info script]]]
set project_root [file normalize [file join $script_dir .. ..]]
set output_dir [file join $project_root 05_Output]
set uvm_dir [file join $output_dir uvm]
set runtime_dir [file join $project_root 03_Loop2_UVM_Verify _runtime]
set work_lib [file join $runtime_dir work]

if {![info exists enable_code_coverage]} {
    set enable_code_coverage 0
}
if {![info exists uvm_test_name]} {
    set uvm_test_name baseline_test
}
if {![info exists uvm_seed_count]} {
    set uvm_seed_count 1
}
if {![info exists uvm_tb_top]} {
    set uvm_tb_top tb_uvm
}
if {![info exists uvm_if_file]} {
    set uvm_if_file [file join $uvm_dir tb tb_dut_if.sv]
}
if {![info exists uvm_pkg_file]} {
    set uvm_pkg_file [file join $uvm_dir env uvm_pkg.sv]
}
if {![info exists uvm_tb_top_file]} {
    set uvm_tb_top_file [file join $uvm_dir tb tb_uvm.sv]
}
if {![info exists uvm_sva_file]} {
    set uvm_sva_file ""
}

if {[info exists env(UVM_HOME)] && [file exists [file join $env(UVM_HOME) src uvm_pkg.sv]]} {
    set external_uvm_src [file normalize [file join $env(UVM_HOME) src]]
} else {
    set modelsim_home [file normalize [file join [file dirname [file dirname [info nameofexecutable]]] verilog_src]]
    set external_uvm_src ""
    foreach candidate [list uvm-1.2 uvm-1.1d uvm-1.1c uvm] {
        set candidate_dir [file join $modelsim_home $candidate src]
        if {[file exists [file join $candidate_dir uvm_pkg.sv]]} {
            set external_uvm_src $candidate_dir
            break
        }
    }
}

if {$external_uvm_src eq ""} {
    puts "ERROR: UVM source not found. Set UVM_HOME or install ModelSim/Questa UVM sources."
    quit -code 1
}

foreach required_file [list $uvm_if_file $uvm_pkg_file $uvm_tb_top_file] {
    if {![file exists $required_file]} {
        puts "ERROR: missing UVM source file $required_file"
        puts "       Instantiate files from 05_Output/uvm/*.template before running Loop2."
        quit -code 1
    }
}

set no_quit 1
do [file join $script_dir compile.do]

vlog -sv -work $work_lib +define+UVM_NO_DPI +incdir+$external_uvm_src [file join $external_uvm_src uvm_pkg.sv]

set project_incdirs [list \
    [file join $uvm_dir cfg] \
    [file join $uvm_dir agents] \
    [file join $uvm_dir cov] \
    [file join $uvm_dir env] \
    [file join $uvm_dir reg] \
    [file join $uvm_dir seq_lib] \
    [file join $uvm_dir tests] \
    [file join $uvm_dir tb] \
    [file join $uvm_dir assertions]]

foreach agent_dir [glob -nocomplain -type d [file join $uvm_dir agents *]] {
    lappend project_incdirs $agent_dir
}
foreach seq_dir [glob -nocomplain -type d [file join $uvm_dir seq_lib *]] {
    lappend project_incdirs $seq_dir
}

set project_vlog_args [list -sv -work $work_lib +incdir+$external_uvm_src]
foreach incdir $project_incdirs {
    if {[file exists $incdir]} {
        lappend project_vlog_args +incdir+$incdir
    }
}

eval vlog $project_vlog_args [list $uvm_if_file]
eval vlog $project_vlog_args [list $uvm_pkg_file]
if {$uvm_sva_file ne "" && [file exists $uvm_sva_file]} {
    eval vlog $project_vlog_args [list $uvm_sva_file]
}
eval vlog $project_vlog_args [list $uvm_tb_top_file]

set vsim_args [list -onfinish stop -voptargs=+acc -lib $work_lib $uvm_tb_top +UVM_TESTNAME=$uvm_test_name +UVM_NO_RELNOTES +UVM_VERBOSITY=UVM_MEDIUM +LOOP2_SEED_COUNT=$uvm_seed_count]
if {$enable_code_coverage} {
    set vsim_args [linsert $vsim_args 0 -coverage]
}

eval vsim $vsim_args
run -all

if {$enable_code_coverage} {
    coverage report -details -file [file join $runtime_dir loop2_coverage.txt]
}

quit -sim
puts "Loop2 UVM baseline PASS"
quit -code 0
