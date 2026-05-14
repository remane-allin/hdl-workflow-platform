transcript on
onerror {quit -code 1}

if {![info exists script_dir]} {
    set script_dir [file normalize [file dirname [info script]]]
}
if {![info exists project_root]} {
    set project_root [file normalize [file join $script_dir .. ..]]
}
if {![info exists loop1_tb_tops]} {
    set loop1_tb_tops [list loop1_tb]
}

set no_quit 1
do [file join $script_dir compile.do]
unset no_quit

set work_lib [file join $project_root 02_Loop1_RTL_TB _runtime work]
foreach tb_top $loop1_tb_tops {
    puts "Loop1 running TB top: $tb_top"
    vsim -onfinish stop -voptargs=+acc -lib $work_lib $tb_top
    run -all
    quit -sim
}

puts "Loop1 rtl_functional.do PASS"
quit -code 0
