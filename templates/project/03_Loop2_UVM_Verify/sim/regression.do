transcript on
onerror {quit -code 1}

if {![info exists uvm_test_name]} {
    set uvm_test_name full_regression_test
}
if {![info exists uvm_seed_count]} {
    set uvm_seed_count 100
}
set enable_code_coverage 1

do [file join [file dirname [info script]] uvm_baseline.do]
