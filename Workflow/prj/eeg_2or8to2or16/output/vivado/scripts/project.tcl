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

proc wf_create_bd {} {
    global wf_project_root
    set bd_name eeg_bci_ps_pl_system
    create_bd_design $bd_name
    current_bd_design $bd_name
    set ps7 [create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 processing_system7_0]
    set ps7_cell_obj $ps7
    source [file join $wf_project_root input sources platform navigator_zynq_7020_ps7_preset.tcl]
    set_property -dict [list \
        CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {70} \
        CONFIG.PCW_ACT_FPGA0_PERIPHERAL_FREQMHZ {70.000000} \
        CONFIG.PCW_USE_M_AXI_GP0 {1} \
        CONFIG.PCW_USE_FABRIC_INTERRUPT {1} \
        CONFIG.PCW_IRQ_F2P_INTR {1} \
        CONFIG.PCW_IRQ_F2P_MODE {DIRECT} \
        CONFIG.PCW_USE_S_AXI_HP0 {0} \
        CONFIG.PCW_USE_S_AXI_HP1 {0}] $ps7
    create_bd_intf_port -mode Master -vlnv xilinx.com:interface:ddrx_rtl:1.0 DDR
    create_bd_intf_port -mode Master -vlnv xilinx.com:display_processing_system7:fixedio_rtl:1.0 FIXED_IO
    set bci [create_bd_cell -type module -reference eeg_bci_ps_axi4_gateway BCI_0]
    set converter [create_bd_cell -type ip -vlnv xilinx.com:ip:axi_protocol_converter:2.1 axi3_to_axi4_0]
    set_property -dict [list CONFIG.SI_PROTOCOL {AXI3} CONFIG.MI_PROTOCOL {AXI4}] $converter
    set memory [create_bd_cell -type ip -vlnv xilinx.com:ip:blk_mem_gen:8.4 sample_bram_0]
    set_property -dict [list CONFIG.EN_SAFETY_CKT {false} CONFIG.Memory_Type {True_Dual_Port_RAM} \
        CONFIG.Use_Byte_Write_Enable {true} CONFIG.Byte_Size {8} CONFIG.Enable_32bit_Address {true} \
        CONFIG.Write_Width_A {32} CONFIG.Write_Depth_A {2048} CONFIG.Read_Width_A {32} \
        CONFIG.Enable_A {Use_ENA_Pin} CONFIG.Write_Width_B {32} CONFIG.Read_Width_B {32} \
        CONFIG.Enable_B {Use_ENB_Pin} CONFIG.Register_PortA_Output_of_Memory_Primitives {false} \
        CONFIG.Register_PortB_Output_of_Memory_Primitives {false} CONFIG.Use_RSTA_Pin {false} \
        CONFIG.Use_RSTB_Pin {false}] $memory
    set reset [create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 rst_ps7_0_100M]
    connect_bd_intf_net [get_bd_intf_ports DDR] [get_bd_intf_pins $ps7/DDR]
    connect_bd_intf_net [get_bd_intf_ports FIXED_IO] [get_bd_intf_pins $ps7/FIXED_IO]
    connect_bd_intf_net [get_bd_intf_pins $ps7/M_AXI_GP0] [get_bd_intf_pins $converter/S_AXI]
    connect_bd_intf_net [get_bd_intf_pins $converter/M_AXI] [get_bd_intf_pins $bci/S_AXI]
    connect_bd_net [get_bd_pins $ps7/FCLK_CLK0] [get_bd_pins $ps7/M_AXI_GP0_ACLK] \
        [get_bd_pins $converter/aclk] [get_bd_pins $bci/s_axi_aclk] [get_bd_pins $reset/slowest_sync_clk]
    connect_bd_net [get_bd_pins $ps7/FCLK_RESET0_N] [get_bd_pins $reset/ext_reset_in]
    connect_bd_net [get_bd_pins $bci/infer_done] [get_bd_pins $ps7/IRQ_F2P]
    connect_bd_net [get_bd_pins $reset/peripheral_aresetn] [get_bd_pins $converter/aresetn] [get_bd_pins $bci/s_axi_aresetn]
    foreach suffix {clka ena wea addra dina} {
        connect_bd_net [get_bd_pins $bci/sample_bram_$suffix] [get_bd_pins $memory/$suffix]
    }
    connect_bd_net [get_bd_pins $memory/douta] [get_bd_pins $bci/sample_bram_douta]
    foreach suffix {clkb enb web addrb dinb} {
        connect_bd_net [get_bd_pins $bci/sample_bram_$suffix] [get_bd_pins $memory/$suffix]
    }
    connect_bd_net [get_bd_pins $memory/doutb] [get_bd_pins $bci/sample_bram_doutb]
    set target {}
    foreach candidate {BCI_0/S_AXI/Reg BCI_0/S_AXI/S_AXI_reg BCI_0/S_AXI/reg0} {
        set found [get_bd_addr_segs -quiet $candidate]
        if {[llength $found] > 0} {
            set target $found
            break
        }
    }
    if {[llength $target] == 0} {
        error "BCI AXI address segment was not generated"
    }
    assign_bd_address -offset 0x40000000 -range 0x04000000 \
        -target_address_space [get_bd_addr_spaces $ps7/Data] $target -force
    validate_bd_design
    save_bd_design
}

proc wf_project_sync {} {
    global wf_rtl_files wf_tb_file wf_project_root wf_xpr wf_part wf_project_name
    global wf_xdc_files wf_sim_models wf_top wf_tb_top wf_workflow_root wf_opt_resynth_area
    global wf_synthesis_strategy wf_synthesis_directive wf_implementation_strategy
    global wf_opt_directive wf_place_directive wf_phys_opt_enabled
    global wf_phys_opt_directive wf_route_directive wf_constraints_used_in_synthesis
    global wf_ip_files wf_bd_names
    wf_require_files $wf_rtl_files "active RTL"
    wf_require_files [list $wf_tb_file [file join $wf_project_root input sources platform navigator_zynq_7020_ps7_preset.tcl]] "project input"
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
    wf_add_missing $wf_xdc_files constrs_1
    wf_add_missing $wf_sim_models sim_1
    wf_add_missing [list $wf_tb_file] sim_1
    foreach path $wf_xdc_files {
        set constraint_file [get_files -quiet $path]
        set_property USED_IN_SYNTHESIS $wf_constraints_used_in_synthesis $constraint_file
        set_property USED_IN_IMPLEMENTATION true $constraint_file
    }
    update_compile_order -fileset sources_1
    if {[llength [get_files -quiet eeg_bci_ps_pl_system.bd]] == 0} {
        wf_create_bd
    } else {
        set bd_file [lindex [get_files eeg_bci_ps_pl_system.bd] 0]
        open_bd_design $bd_file
        if {[llength [get_bd_cells -quiet BCI_0]] == 0} {
            error "native block design is incomplete; an approved block-design repair is required"
        }
        validate_bd_design
        save_bd_design
    }
    set bd_file [lindex [get_files eeg_bci_ps_pl_system.bd] 0]
    set bd_run [get_runs -quiet eeg_bci_ps_pl_system_synth_1]
    set wrapper_files [get_files -quiet *eeg_bci_ps_pl_system_wrapper.v]
    set refresh_bd [expr {[llength $bd_run] == 0 || [llength $wrapper_files] == 0}]
    if {[llength $bd_run] > 0 && [wf_run_needs_refresh $bd_run]} {
        set refresh_bd 1
    }
    if {$refresh_bd} {
        wf_generate_supported_targets $bd_file {instantiation_template synthesis simulation implementation} "block design"
        set wrapper [make_wrapper -files $bd_file -top]
        if {[llength $wrapper_files] == 0} {
            add_files -norecurse $wrapper
        }
    }
    if {[llength $bd_run] == 0} {
        create_ip_run $bd_file
    }
    set_property source_mgmt_mode All [current_project]
    set_property top $wf_top [get_filesets sources_1]
    set_property top $wf_tb_top [get_filesets sim_1]
    set synth [get_runs synth_1]
    set_property STRATEGY $wf_synthesis_strategy $synth
    set_property STEPS.SYNTH_DESIGN.ARGS.DIRECTIVE $wf_synthesis_directive $synth
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
