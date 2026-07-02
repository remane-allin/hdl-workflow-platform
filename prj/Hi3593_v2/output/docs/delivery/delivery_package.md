---
doc_type: delivery_package
project: Hi3593_v2
ip_name: hi3593_v2_top
version: DRAFT
status: DRAFT
generated_at: 2026-07-02T15:57:21
generator: hdlflow.docgen.delivery_package
source_manifest: output/docs/manifests/delivery_doc_manifest.json
owner_agent: Arbtr
review_agents: [Spec, Arch, Exec, Sim, Review]
change_id: CR-20260702155634-forbid-directed-tb-markdown-sidecar
---

# hi3593_v2_top Delivery Package

<!-- HDL-DELIVERY-DOC START -->

## 0. Delivery Status
| Item | Value |
| --- | --- |
| Project | Hi3593_v2 |
| IP / Module | hi3593_v2_top |
| Status | DRAFT |
| Owner Agent | Arbtr |
| Review Agents | Spec, Arch, Exec, Sim, Review |
| Generated At | 2026-07-02T15:57:21 |
| Change ID | CR-20260702155634-forbid-directed-tb-markdown-sidecar |

## 1. Release Decision
| Item | Status |
| --- | --- |
| Docset Current | DRAFT |
| Spec Exit | pass |
| Loop1 Exit | fail |
| Loop2 Exit | fail |
| Loop3 Exit | pass |
| Final Gate | pass |

## 2. Delivered Document Set
| Document | Path | Status |
| --- | --- | --- |
| Application Guide | output/docs/application/application_guide.md | DRAFT |
| Microarchitecture Specification | output/docs/design/microarchitecture_spec.md | DRAFT |
| Verification Plan | output/docs/test/verification_plan.md | DRAFT |
| Delivery Package | output/docs/delivery/delivery_package.md | DRAFT |

## 3. Delivered Engineering Artifacts
| Artifact Type | Count | Root |
| --- | --- | --- |
| RTL | 9 | output/rtl |
| Directed TB | 1 | output/tb |
| UVM | 15 | output/uvm |
| FPGA | 59 | output/fpga |
| Reports | 152 | output/reports |

## 4. Gate Status Summary
| Field | Value |
| --- | --- |
| spec_exit | pass |
| loop1_exit | fail |
| loop2_entry | fail |
| loop2_exit | fail |
| loop3_entry | pending |
| loop3_exit | pass |
| final_gate | pass |

## 5. Semantic Gate Status
| Gate | Mode | Status | Issue Count |
| --- | --- | --- | --- |
| requirements_consistency_gate | advisory | PASS | 0 |
| architecture_impact_gate | advisory | PASS | 0 |
| design_routing_gate | advisory | PASS | 0 |
| microarchitecture_completeness_gate | advisory | PASS | 0 |
| rtl_obligation_gate | advisory | PASS | 0 |
| tb_blackbox_obligation_gate | advisory | PASS | 0 |
| waveform_semantic_gate | advisory | PASS | 0 |
| uvm_obligation_gate | advisory | PASS | 0 |

## 6. Release State
| Field | Value |
| --- | --- |
| state | RELEASE_FAIL |
| ok | not recorded |
| blockers | final audit PASS conflicts with latest release gate FAIL |
| warnings | not recorded |

## 7. Verification Evidence
| Evidence Area | Value | Required |
| --- | --- | --- |
| Loop1 | fail | pass |
| Loop2 | fail | pass |
| Loop3 | pass | pass |
| Review Findings | see work/docparse/review/role_findings.yaml | no blockers |

## 8. Prototype / Board Validation Plan
| Area | Item | Detail |
| --- | --- | --- |
| prototype_mode | ps_pl | prototype setting |
| board | navigator_zynq_7020 | prototype setting |
| resource_estimate | LUT | 3000 |
| resource_estimate | BRAM | 1 |
| ps_pl_boundary | axi_lite_control_window | name=axi_lite_control_window; base=0x43C00000; range=64K |
| ps_pl_boundary | digital_pin_sampler | name=digital_pin_sampler; pins=TX1IN, TX0IN, SLP |
| ps_pl_boundary | ps_pl_wrapper | name=ps_pl_wrapper; module=hi3593_v2_proto_top; source=output/fpga/vivado/src/hi3593_v2_proto_top.v; role=AXI4-Lite control/status wrapper around hi3593_v2_top for Loop3 bringup only. |
| ps_pl_boundary | ps_uart0_console | name=ps_uart0_console; base=STDIN_BASEADDRESS; physical_path=PS UART0 MIO 14..15 / COM3; role=Automated Loop3 board-control serial console for Vitis command/response evidence. |
| risk_items | item | id=RISK-ANALOG-001; text=Analog voltage/slew/lightning behavior cannot be signed off without board equipment evidence. |
| board_waveform_checks | item | id=BW-PSPL-001; text=Sample digital driver-control pins through PS/PL path. |

## 9. FPGA Validation Matrix
| FPGA Test | Requirement | Mode | Claim Level | Evidence Level | Status |
| --- | --- | --- | --- | --- | --- |
| fpga_asm_boundary_001 | ASM-BOUNDARY-001 | ps_pl_emulation | level_0 | level_0 | planned |
| fpga_baseline_seed_001 | BASELINE-SEED-001 | ps_pl_emulation | level_0 | level_0 | planned |
| fpga_req_aclk_001 | REQ-ACLK-001 | ps_pl_emulation | level_0 | level_0 | planned |
| fpga_req_arinc_001 | REQ-ARINC-001 | ps_pl_emulation | level_0 | level_0 | planned |
| fpga_req_fifo_001 | REQ-FIFO-001 | ps_pl_emulation | level_0 | level_0 | planned |
| fpga_req_flagint_001 | REQ-FLAGINT-001 | ps_pl_emulation | level_0 | level_0 | planned |
| fpga_req_inst_001 | REQ-INST-001 | ps_pl_emulation | level_0 | level_0 | planned |
| fpga_req_label_001 | REQ-LABEL-001 | ps_pl_emulation | level_0 | level_0 | planned |
| fpga_req_mailbox_001 | REQ-MAILBOX-001 | ps_pl_emulation | level_0 | level_0 | planned |
| fpga_req_mb_pins_001 | REQ-MB-PINS-001 | ps_pl_emulation | level_0 | level_0 | planned |
| fpga_req_plabel_001 | REQ-PLABEL-001 | ps_pl_emulation | level_0 | level_0 | planned |
| fpga_req_proto_001 | REQ-PROTO-001 | ps_pl_emulation | level_0 | level_0 | planned |
| fpga_req_rst_001 | REQ-RST-001 | ps_pl_emulation | level_0 | level_0 | planned |
| fpga_req_rst_002 | REQ-RST-002 | ps_pl_emulation | level_0 | level_0 | planned |
| fpga_req_rx_001 | REQ-RX-001 | ps_pl_emulation | level_0 | level_0 | planned |
| fpga_req_rx_filter_001 | REQ-RX-FILTER-001 | ps_pl_emulation | level_0 | level_0 | planned |
| fpga_req_spi_001 | REQ-SPI-001 | ps_pl_emulation | level_0 | level_0 | planned |
| fpga_req_spi_002 | REQ-SPI-002 | ps_pl_emulation | level_0 | level_0 | planned |
| fpga_req_status_001 | REQ-STATUS-001 | ps_pl_emulation | level_0 | level_0 | planned |
| fpga_req_tx_001 | REQ-TX-001 | ps_pl_emulation | level_0 | level_0 | planned |
| fpga_req_tx_full_001 | REQ-TX-FULL-001 | ps_pl_emulation | level_0 | level_0 | planned |

## 10. Change Control Summary
| Field | Value |
| --- | --- |
| output | version=1; signoff_owner=Arbtr Agent; source_origin=requirements-frontdoor-gated flow |
| deliverables | rtl=output/rtl/arinc429_rx.v, output/rtl/arinc429_tx.v, output/rtl/control_status_regs.v, output/rtl/hi3593_v2_top.v, output/rtl/reset_ctrl.v, output/rtl/rx_mailbox_status.v, output/rtl/spi_cmd_cdc.v, output/rtl/spi_slave_if.v, output/rtl/sync_fifo.v; tb=output/tb/loop1_tb.v; uvm=output/uvm/agents/spi/spi_agent.sv, output/uvm/agents/spi/spi_driver.sv, output/uvm/agents/spi/spi_item.sv, output/uvm/agents/spi/spi_monitor.sv, output/uvm/agents/spi/spi_sequencer.sv, output/uvm/assertions/dut_assertions.sv, output/uvm/cfg/uvm_config.sv, output/uvm/cov/coverage.sv, output/uvm/env/env.sv, output/uvm/env/scoreboard.sv, output/uvm/env/uvm_pkg.sv, output/uvm/manifest.yaml, output/uvm/README.md, output/uvm/seq_lib/virtual_sequences.svh, output/uvm/tb/tb_dut_if.sv, output/uvm/tb/tb_uvm.sv, output/uvm/tests/tests.svh; fpga=output/fpga/vivado/bitstream/hi3593_v2_ps_pl.bit; vivado=output/fpga/vivado/reports/post_impl_drc.rpt, output/fpga/vivado/reports/post_impl_timing_summary.rpt, output/fpga/vivado/reports/post_impl_utilization.rpt, output/fpga/vivado/reports/pure_pl_uart_led_proto_run.md, output/fpga/vivado/scripts/generated_ps_pl_bd.tcl, output/fpga/vivado/scripts/program_bitstream.tcl, output/fpga/vivado/scripts/run_ps_pl_impl.tcl; vitis=output/fpga/vitis/src/hi3593_loop3_app.c, output/fpga/vitis/boot/BOOT.bin, output/fpga/vitis/boot/boot_image.bif, output/fpga/vitis/boot/Build-BootImage.ps1, output/fpga/vitis/workspace/hi3593_v2_hw/export/hi3593_v2_hw/hi3593_v2_hw.xpfm, output/fpga/vitis/workspace/hi3593_v2_hw/export/hi3593_v2_hw/hw/hi3593_v2_ps_pl.xsa, output/fpga/vitis/workspace/hi3593_v2_hw/export/hi3593_v2_hw/sw/hi3593_v2_hw/boot/fsbl.elf, output/fpga/vitis/workspace/hi3593_v2_hw/hw/hi3593_v2_ps_pl.xsa, output/fpga/vitis/workspace/hi3593_v2_hw/zynq_fsbl/fsbl.elf, output/fpga/vitis/workspace/hi3593_v2_loop3_app/Debug/hi3593_v2_loop3_app.elf |
| reports | index=output/reports/README.md; audit_report=output/reports/final_audit_report.md; trace_matrix=work/docparse/trace_matrix; compliance_summary=output/reports/final_audit_report.md |
| verification | loop1_gate=PASS; loop1_manifest=work/memory/recovery/rollback_manifests/work_loop1_rtl_tb_develop_20260702154536.json; loop2_gate=PASS; loop2_manifest=work/memory/recovery/rollback_manifests/work_loop2_uvm_develop_20260702154544.json; loop3_gate=PASS; loop3_manifest=work/memory/recovery/rollback_manifests/work_loop3_fpga_proto_develop_20260702154551.json; final_gate=PASS; final_report=output/reports/final_audit_report.md |

## 11. Signoff Checklist
| Checklist ID | Item | Required |
| --- | --- | --- |
| SIGN-001 | Application Guide generated and current | yes |
| SIGN-002 | Microarchitecture Spec generated and current | yes |
| SIGN-003 | Verification Plan generated and current | yes |
| SIGN-004 | Docset manifest matches all documents | yes |
| SIGN-005 | Required engineering gates passed | yes |

<!-- HDL-DELIVERY-DOC END -->
