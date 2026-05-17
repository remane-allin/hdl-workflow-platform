transcript on
onerror {quit -code 1}

if {![info exists uvm_test_name]} {
    set uvm_test_name full_regression_test
}
if {![info exists uvm_seed_count]} {
    set uvm_seed_count 100
}
set enable_code_coverage 1

set script_dir [file normalize [file dirname [info script]]]
if {![file exists [file join $script_dir uvm_full_functional.do]] && [file exists [file join [pwd] project_scaffold.yaml]]} {
    set script_dir [file join [file normalize [pwd]] 03_Loop2_UVM_Verify sim]
}
do [file join $script_dir uvm_full_functional.do]
