proc wf_require_files {paths label} {
    foreach path $paths {
        if {![file isfile $path]} {
            error "$label not found: $path"
        }
    }
}

proc wf_add_missing {files fileset} {
    foreach path $files {
        if {[llength [get_files -quiet $path]] == 0} {
            add_files -fileset $fileset -norecurse $path
        }
    }
}

proc wf_project_sync {} {
    global wf_rtl_files wf_tb_file wf_xpr wf_part wf_project_name wf_ip_files
    global wf_xdc_files wf_sim_models wf_top wf_tb_top wf_workflow_root wf_opt_resynth_area
    global wf_synthesis_strategy wf_synthesis_directive wf_implementation_strategy
    global wf_opt_directive wf_place_directive wf_phys_opt_enabled
    global wf_phys_opt_directive wf_route_directive
    global wf_synthesis_mode wf_constraints_used_in_synthesis
    global wf_bd_names

    wf_require_files $wf_rtl_files "active RTL"
    wf_require_files $wf_ip_files "native IP"
    wf_require_files $wf_xdc_files "constraint"
    wf_require_files [concat $wf_sim_models [list $wf_tb_file]] "verification source"
    file mkdir [file dirname $wf_xpr]
    if {[file isfile $wf_xpr]} {
        open_project $wf_xpr
        if {[get_property PART [current_project]] ne $wf_part} {
            error "native project part differs from design"
        }
    } else {
        create_project $wf_project_name [file dirname $wf_xpr] -part $wf_part
        set_property target_language Verilog [current_project]
        set_property simulator_language Verilog [current_project]
    }

    wf_add_missing $wf_rtl_files sources_1
    wf_add_missing $wf_ip_files sources_1
    wf_add_missing $wf_xdc_files constrs_1
    wf_add_missing $wf_sim_models sim_1
    wf_add_missing [list $wf_tb_file] sim_1
    foreach path $wf_xdc_files {
        set constraint_file [get_files -quiet $path]
        set_property USED_IN_SYNTHESIS $wf_constraints_used_in_synthesis $constraint_file
        set_property USED_IN_IMPLEMENTATION true $constraint_file
    }
    set ips [get_ips -quiet]
    if {[llength $ips] != [llength $wf_ip_files]} {
        error "native project IP binding count differs from design"
    }
    set expected_ip_names {}
    foreach path $wf_ip_files {
        lappend expected_ip_names [file rootname [file tail $path]]
    }
    set actual_ip_names {}
    foreach ip $ips {
        lappend actual_ip_names [get_property NAME $ip]
    }
    if {[lsort $expected_ip_names] ne [lsort $actual_ip_names]} {
        error "native project IP identities differ from design"
    }
    foreach ip $ips {
        set locked [get_property IS_LOCKED $ip]
        if {$locked eq "1" || [string equal -nocase $locked "true"]} {
            error "native IP is locked and requires an approved upgrade: [get_property NAME $ip]"
        }
        set run_name "[get_property NAME $ip]_synth_1"
        set ip_run [get_runs -quiet $run_name]
        set refresh_ip [expr {[llength $ip_run] == 0}]
        if {[llength $ip_run] > 0 && [wf_run_needs_refresh $ip_run]} {
            set refresh_ip 1
        }
        if {$refresh_ip} {
            wf_generate_supported_targets $ip {instantiation_template synthesis simulation implementation} "IP [get_property NAME $ip]"
        }
        if {[llength $ip_run] == 0} {
            create_ip_run $ip
        }
    }

    set_property source_mgmt_mode All [current_project]
    set_property top $wf_top [get_filesets sources_1]
    set_property top $wf_tb_top [get_filesets sim_1]
    set synth [get_runs synth_1]
    set_property STRATEGY $wf_synthesis_strategy $synth
    set_property STEPS.SYNTH_DESIGN.ARGS.DIRECTIVE $wf_synthesis_directive $synth
    if {$wf_synthesis_mode eq "out_of_context"} {
        set_property -dict [list \
            {STEPS.SYNTH_DESIGN.ARGS.MORE OPTIONS} {-mode out_of_context}] $synth
    } else {
        set_property {STEPS.SYNTH_DESIGN.ARGS.MORE OPTIONS} {} $synth
    }
    set impl [get_runs impl_1]
    set_property STRATEGY $wf_implementation_strategy $impl
    set_property STEPS.OPT_DESIGN.ARGS.DIRECTIVE $wf_opt_directive $impl
    if {$wf_opt_resynth_area} {
        set_property STEPS.OPT_DESIGN.TCL.POST \
            [file normalize [file join $wf_workflow_root tools tcl opt_resynth_area.tcl]] $impl
    } else {
        set_property STEPS.OPT_DESIGN.TCL.POST {} $impl
    }
    set_property STEPS.PLACE_DESIGN.ARGS.DIRECTIVE $wf_place_directive $impl
    set_property STEPS.PHYS_OPT_DESIGN.IS_ENABLED $wf_phys_opt_enabled $impl
    if {$wf_phys_opt_enabled} {
        set_property STEPS.PHYS_OPT_DESIGN.ARGS.DIRECTIVE $wf_phys_opt_directive $impl
    }
    set_property STEPS.ROUTE_DESIGN.ARGS.DIRECTIVE $wf_route_directive $impl
    wf_assert_declared_files sources_1 [concat $wf_rtl_files $wf_ip_files] {.v .sv .xci} $wf_bd_names
    wf_assert_declared_files sim_1 [concat $wf_sim_models [list $wf_tb_file]] {.v .sv} {}
    wf_assert_declared_files constrs_1 $wf_xdc_files {.xdc} {}
    update_compile_order -fileset sources_1
    update_compile_order -fileset sim_1
}
