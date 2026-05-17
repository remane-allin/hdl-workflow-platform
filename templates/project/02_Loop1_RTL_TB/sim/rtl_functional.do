transcript on
onerror {quit -code 1}

if {![info exists script_dir]} {
    set script_dir [file normalize [file dirname [info script]]]
}
if {![info exists project_root]} {
    set project_root [file normalize [file join $script_dir .. ..]]
}
if {![file exists [file join $script_dir compile.do]] && [file exists [file join [pwd] project_scaffold.yaml]]} {
    set project_root [file normalize [pwd]]
    set script_dir [file join $project_root 02_Loop1_RTL_TB sim]
}
if {![info exists loop1_tb_tops]} {
    set loop1_tb_tops [list loop1_tb]
}
set report_dir [file join $project_root 05_Output reports loop1]
file mkdir $report_dir
transcript file [file join $report_dir modelsim_loop1.log]
transcript on

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

set workspace_root [file normalize [file join $project_root .. ..]]
set env(PYTHONPATH) [file join $workspace_root engine]
set refresh_cmd [list python -m hdlflow.cli loop1-refresh-reports --project $project_root]
if {[catch {eval exec $refresh_cmd} refresh_out]} {
    puts $refresh_out
    quit -code 1
}
puts $refresh_out
puts "Loop1 rtl_functional.do PASS"
quit -code 0
