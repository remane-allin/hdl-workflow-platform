## Loop3 Vitis/XSCT PS application build flow.
## Launch through env/tool/scripts/Invoke-HdlVitis.ps1 -Tool xsct.

set script_dir [file dirname [file normalize [info script]]]
set project_root [file normalize [file join $script_dir .. .. .. ..]]
set workspace_dir [file join $project_root output fpga vitis workspace]
set report_dir [file join $project_root output fpga vitis reports]
set xsa_file [file join $project_root output fpga vivado hw_platform hi3593_v2_ps_pl.xsa]
set src_dir [file join $project_root output fpga vitis src]
set build_report [file join $report_dir ps_app_build_report.md]

file mkdir $workspace_dir
file mkdir $report_dir

if {![file exists $xsa_file]} {
    error "Missing XSA: $xsa_file"
}
if {![file exists [file join $src_dir hi3593_loop3_app.c]]} {
    error "Missing PS application source"
}

setws $workspace_dir

catch {deleteprojects -name hi3593_v2_loop3_app}
catch {deleteprojects -name hi3593_v2_bsp}
catch {deleteprojects -name hi3593_v2_hw}
catch {file delete -force [file join $workspace_dir hi3593_v2_loop3_app]}
catch {file delete -force [file join $workspace_dir hi3593_v2_loop3_app_system]}
catch {file delete -force [file join $workspace_dir hi3593_v2_bsp]}
catch {file delete -force [file join $workspace_dir hi3593_v2_hw]}

createhw -name hi3593_v2_hw -hwspec $xsa_file
createbsp -name hi3593_v2_bsp -hwproject hi3593_v2_hw -proc ps7_cortexa9_0 -os standalone
createapp -name hi3593_v2_loop3_app -app {Empty Application} -proc ps7_cortexa9_0 -hwproject hi3593_v2_hw -bsp hi3593_v2_bsp
importsources -name hi3593_v2_loop3_app -path $src_dir
app build -name hi3593_v2_loop3_app

set make_dir [file join $workspace_dir hi3593_v2_loop3_app Debug]
set make_file [file join $make_dir makefile]
if {![file exists $make_file]} {
    error "PS application makefile was not generated: $make_file"
}

set make_exe "make"
if {[info exists ::env(HDLFLOW_VITIS_ROOT)]} {
    set vitis_root [file normalize $::env(HDLFLOW_VITIS_ROOT)]
    set gnu_bin [file join $vitis_root gnu aarch32 nt gcc-arm-none-eabi bin]
    set gnuwin_bin [file join $vitis_root gnuwin bin]
    set make_candidate [file join $gnuwin_bin make.exe]
    if {[file exists $make_candidate]} {
        set make_exe $make_candidate
    }
    set ::env(PATH) "$gnu_bin;$gnuwin_bin;$::env(PATH)"
}

set make_status [catch {exec $make_exe -C $make_dir all 2>@1} make_output]
puts $make_output
if {$make_status != 0} {
    error "PS application make failed"
}

set elf_candidates [glob -nocomplain [file join $workspace_dir hi3593_v2_loop3_app Debug *.elf]]
if {[llength $elf_candidates] == 0} {
    set elf_candidates [glob -nocomplain [file join $workspace_dir hi3593_v2_loop3_app *.elf]]
}
if {[llength $elf_candidates] == 0} {
    error "PS application build completed without an ELF"
}

set elf_path [file normalize [lindex $elf_candidates 0]]
set rel_elf [string map {\\ /} $elf_path]
set rel_root [string map {\\ /} $project_root]
set rel_prefix "$rel_root/"
if {[string first $rel_prefix $rel_elf] == 0} {
    set rel_elf [string range $rel_elf [string length $rel_prefix] end]
}
set fh [open $build_report w]
puts $fh "# Loop3 PS Application Build"
puts $fh ""
puts $fh "- project: Hi3593_v2"
puts $fh "- tool: xsct"
puts $fh "- xsa: output/fpga/vivado/hw_platform/hi3593_v2_ps_pl.xsa"
puts $fh "- source: output/fpga/vitis/src/hi3593_loop3_app.c"
puts $fh "- elf: $rel_elf"
puts $fh "- result: PASS"
close $fh

puts "LOOP3_PS_APP_BUILD_PASS elf=$elf_path"
