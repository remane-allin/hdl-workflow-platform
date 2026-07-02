---
doc_type: verification_plan
project: Hi3593_v2
ip_name: hi3593_v2_top
version: DRAFT
status: DRAFT
generated_at: 2026-07-02T15:57:21
generator: hdlflow.docgen.verification_plan
source_manifest: output/docs/manifests/verification_doc_manifest.json
owner_agent: Sim
review_agents: [Exec, Review, Arbtr]
change_id: CR-20260702155634-forbid-directed-tb-markdown-sidecar
---

# hi3593_v2_top Verification Plan

<!-- HDL-VERIF-DOC START -->

## 0. Document Status
| Item | Value |
| --- | --- |
| Project | Hi3593_v2 |
| IP / Module | hi3593_v2_top |
| Status | DRAFT |
| Owner Agent | Sim |
| Review Agents | Exec, Review, Arbtr |
| Generated At | 2026-07-02T15:57:21 |
| Change ID | CR-20260702155634-forbid-directed-tb-markdown-sidecar |

## 1. Verification Goals
| Goal | Requirement IDs / Checks |
| --- | --- |
| spi_slave_if | partial byte discard, opcode_04 opcode_08 opcode_0C opcode_10 opcode_24 opcode_40 opcode_44 opcode_80 opcode_84 opcode_A0 opcode_C0 |
| spi_cmd_cdc | read opcode dummy bytes are ignored while CDC response is pending, ACLK command pulse is emitted once per complete SCK-domain command |
| rx_mailbox_status | priority mailbox capture and read-clear, flag interrupt output selection |
| sync_fifo | tx_fifo_full_ignore, rx_location32_overwrite |
| arinc429_tx | parity_odd_even, selftest_null_driver |
| system_level | id=SL-RESET; text=MR and opcode_04 produce master reset; opcode_44 is FIFO/mailbox-only. |
| scoreboard | id=SB-SPEC; model=Command-level reference model tracks registers, FIFO counts, and expected readbacks from register_map.yaml. |
| reference_model | id=RM-ARINC; text=ARINC model handles 32-bit word parity, label bit order, and selected high/low rate class. |

## 2. Operation Model
| Operation | Requirements | Type | Interface | Expected Response | Coverage Bins |
| --- | --- | --- | --- | --- | --- |
| OP_ASM_BOUNDARY_001 | ASM-BOUNDARY-001 | functional | spi_host | observable functional response satisfies requirement: ASM-BOUNDARY-001 | op_asm_boundary_001_nominal, op_asm_boundary_001_reset_interaction, op_asm_boundary_001_negative_or_boundary |
| OP_BASELINE_SEED_001 | BASELINE-SEED-001 | functional | spi_host | observable functional response satisfies requirement: BASELINE-SEED-001 | op_baseline_seed_001_nominal, op_baseline_seed_001_reset_interaction, op_baseline_seed_001_negative_or_boundary |
| OP_REQ_ACLK_001 | REQ-ACLK-001 | read | spi_host | observable read response satisfies requirement: REQ-ACLK-001 | op_req_aclk_001_nominal, op_req_aclk_001_reset_interaction, op_req_aclk_001_negative_or_boundary |
| OP_REQ_ARINC_001 | REQ-ARINC-001 | stream | spi_host | observable stream response satisfies requirement: REQ-ARINC-001 | op_req_arinc_001_nominal, op_req_arinc_001_reset_interaction, op_req_arinc_001_negative_or_boundary |
| OP_REQ_FIFO_001 | REQ-FIFO-001 | write | spi_host | observable write response satisfies requirement: REQ-FIFO-001 | op_req_fifo_001_nominal, op_req_fifo_001_reset_interaction, op_req_fifo_001_negative_or_boundary |
| OP_REQ_FLAGINT_001 | REQ-FLAGINT-001 | read | spi_host | observable read response satisfies requirement: REQ-FLAGINT-001 | op_req_flagint_001_nominal, op_req_flagint_001_reset_interaction, op_req_flagint_001_negative_or_boundary |
| OP_REQ_INST_001 | REQ-INST-001 | write | spi_host | observable write response satisfies requirement: REQ-INST-001 | op_req_inst_001_nominal, op_req_inst_001_reset_interaction, op_req_inst_001_negative_or_boundary |
| OP_REQ_LABEL_001 | REQ-LABEL-001 | read | spi_host | observable read response satisfies requirement: REQ-LABEL-001 | op_req_label_001_nominal, op_req_label_001_reset_interaction, op_req_label_001_negative_or_boundary |
| OP_REQ_MAILBOX_001 | REQ-MAILBOX-001 | read | spi_host | observable read response satisfies requirement: REQ-MAILBOX-001 | op_req_mailbox_001_nominal, op_req_mailbox_001_reset_interaction, op_req_mailbox_001_negative_or_boundary |
| OP_REQ_MB_PINS_001 | REQ-MB-PINS-001 | read | spi_host | observable read response satisfies requirement: REQ-MB-PINS-001 | op_req_mb_pins_001_nominal, op_req_mb_pins_001_reset_interaction, op_req_mb_pins_001_negative_or_boundary |
| OP_REQ_PLABEL_001 | REQ-PLABEL-001 | reset | spi_host | observable reset response satisfies requirement: REQ-PLABEL-001 | op_req_plabel_001_nominal, op_req_plabel_001_reset_interaction, op_req_plabel_001_negative_or_boundary |
| OP_REQ_PROTO_001 | REQ-PROTO-001 | read | spi_host | observable read response satisfies requirement: REQ-PROTO-001 | op_req_proto_001_nominal, op_req_proto_001_reset_interaction, op_req_proto_001_negative_or_boundary |
| OP_REQ_RST_001 | REQ-RST-001 | functional | spi_host | observable functional response satisfies requirement: REQ-RST-001 | op_req_rst_001_nominal, op_req_rst_001_reset_interaction, op_req_rst_001_negative_or_boundary |
| OP_REQ_RST_002 | REQ-RST-002 | read | spi_host | observable read response satisfies requirement: REQ-RST-002 | op_req_rst_002_nominal, op_req_rst_002_reset_interaction, op_req_rst_002_negative_or_boundary |
| OP_REQ_RX_001 | REQ-RX-001 | stream | spi_host | observable stream response satisfies requirement: REQ-RX-001 | op_req_rx_001_nominal, op_req_rx_001_reset_interaction, op_req_rx_001_negative_or_boundary |
| OP_REQ_RX_FILTER_001 | REQ-RX-FILTER-001 | stream | spi_host | observable stream response satisfies requirement: REQ-RX-FILTER-001 | op_req_rx_filter_001_nominal, op_req_rx_filter_001_reset_interaction, op_req_rx_filter_001_negative_or_boundary |
| OP_REQ_SPI_001 | REQ-SPI-001 | functional | spi_host | observable functional response satisfies requirement: REQ-SPI-001 | op_req_spi_001_nominal, op_req_spi_001_reset_interaction, op_req_spi_001_negative_or_boundary |
| OP_REQ_SPI_002 | REQ-SPI-002 | write | spi_host | observable write response satisfies requirement: REQ-SPI-002 | op_req_spi_002_nominal, op_req_spi_002_reset_interaction, op_req_spi_002_negative_or_boundary |
| OP_REQ_STATUS_001 | REQ-STATUS-001 | read | spi_host | observable read response satisfies requirement: REQ-STATUS-001 | op_req_status_001_nominal, op_req_status_001_reset_interaction, op_req_status_001_negative_or_boundary |
| OP_REQ_TX_001 | REQ-TX-001 | write | spi_host | observable write response satisfies requirement: REQ-TX-001 | op_req_tx_001_nominal, op_req_tx_001_reset_interaction, op_req_tx_001_negative_or_boundary |
| OP_REQ_TX_FULL_001 | REQ-TX-FULL-001 | stream | spi_host | observable stream response satisfies requirement: REQ-TX-FULL-001 | op_req_tx_full_001_nominal, op_req_tx_full_001_reset_interaction, op_req_tx_full_001_negative_or_boundary |

## 3. Directed TB Obligations
| TB Test | Requirement | Operation | Observed Interface | Evidence Type | Status |
| --- | --- | --- | --- | --- | --- |
| tb_op_asm_boundary_001 | ASM-BOUNDARY-001 | OP_ASM_BOUNDARY_001 | spi_host | blackbox | verified |
| tb_op_baseline_seed_001 | BASELINE-SEED-001 | OP_BASELINE_SEED_001 | spi_host | blackbox | verified |
| tb_op_req_aclk_001 | REQ-ACLK-001 | OP_REQ_ACLK_001 | spi_host | blackbox | verified |
| tb_op_req_arinc_001 | REQ-ARINC-001 | OP_REQ_ARINC_001 | spi_host | blackbox | verified |
| tb_op_req_fifo_001 | REQ-FIFO-001 | OP_REQ_FIFO_001 | spi_host | blackbox | verified |
| tb_op_req_flagint_001 | REQ-FLAGINT-001 | OP_REQ_FLAGINT_001 | spi_host | blackbox | verified |
| tb_op_req_inst_001 | REQ-INST-001 | OP_REQ_INST_001 | spi_host | blackbox | verified |
| tb_op_req_label_001 | REQ-LABEL-001 | OP_REQ_LABEL_001 | spi_host | blackbox | verified |
| tb_op_req_mailbox_001 | REQ-MAILBOX-001 | OP_REQ_MAILBOX_001 | spi_host | blackbox | verified |
| tb_op_req_mb_pins_001 | REQ-MB-PINS-001 | OP_REQ_MB_PINS_001 | spi_host | blackbox | verified |
| tb_op_req_plabel_001 | REQ-PLABEL-001 | OP_REQ_PLABEL_001 | spi_host | blackbox | verified |
| tb_op_req_proto_001 | REQ-PROTO-001 | OP_REQ_PROTO_001 | spi_host | blackbox | verified |
| tb_op_req_rst_001 | REQ-RST-001 | OP_REQ_RST_001 | spi_host | blackbox | verified |
| tb_op_req_rst_002 | REQ-RST-002 | OP_REQ_RST_002 | spi_host | blackbox | verified |
| tb_op_req_rx_001 | REQ-RX-001 | OP_REQ_RX_001 | spi_host | blackbox | verified |
| tb_op_req_rx_filter_001 | REQ-RX-FILTER-001 | OP_REQ_RX_FILTER_001 | spi_host | blackbox | verified |
| tb_op_req_spi_001 | REQ-SPI-001 | OP_REQ_SPI_001 | spi_host | blackbox | verified |
| tb_op_req_spi_002 | REQ-SPI-002 | OP_REQ_SPI_002 | spi_host | blackbox | verified |
| tb_op_req_status_001 | REQ-STATUS-001 | OP_REQ_STATUS_001 | spi_host | blackbox | verified |
| tb_op_req_tx_001 | REQ-TX-001 | OP_REQ_TX_001 | spi_host | blackbox | verified |
| tb_op_req_tx_full_001 | REQ-TX-FULL-001 | OP_REQ_TX_FULL_001 | spi_host | blackbox | verified |

## 4. VCD Semantic Windows
| Window | Operation | Interface | Decoder | Evidence Level | Expected Events |
| --- | --- | --- | --- | --- | --- |
| wave_op_asm_boundary_001 | OP_ASM_BOUNDARY_001 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_ASM_BOUNDARY_001 |
| wave_op_baseline_seed_001 | OP_BASELINE_SEED_001 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_BASELINE_SEED_001 |
| wave_op_req_aclk_001 | OP_REQ_ACLK_001 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_REQ_ACLK_001 |
| wave_op_req_arinc_001 | OP_REQ_ARINC_001 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_REQ_ARINC_001 |
| wave_op_req_fifo_001 | OP_REQ_FIFO_001 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_REQ_FIFO_001 |
| wave_op_req_flagint_001 | OP_REQ_FLAGINT_001 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_REQ_FLAGINT_001 |
| wave_op_req_inst_001 | OP_REQ_INST_001 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_REQ_INST_001 |
| wave_op_req_label_001 | OP_REQ_LABEL_001 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_REQ_LABEL_001 |
| wave_op_req_mailbox_001 | OP_REQ_MAILBOX_001 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_REQ_MAILBOX_001 |
| wave_op_req_mb_pins_001 | OP_REQ_MB_PINS_001 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_REQ_MB_PINS_001 |
| wave_op_req_plabel_001 | OP_REQ_PLABEL_001 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_REQ_PLABEL_001 |
| wave_op_req_proto_001 | OP_REQ_PROTO_001 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_REQ_PROTO_001 |
| wave_op_req_rst_001 | OP_REQ_RST_001 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_REQ_RST_001 |
| wave_op_req_rst_002 | OP_REQ_RST_002 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_REQ_RST_002 |
| wave_op_req_rx_001 | OP_REQ_RX_001 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_REQ_RX_001 |
| wave_op_req_rx_filter_001 | OP_REQ_RX_FILTER_001 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_REQ_RX_FILTER_001 |
| wave_op_req_spi_001 | OP_REQ_SPI_001 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_REQ_SPI_001 |
| wave_op_req_spi_002 | OP_REQ_SPI_002 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_REQ_SPI_002 |
| wave_op_req_status_001 | OP_REQ_STATUS_001 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_REQ_STATUS_001 |
| wave_op_req_tx_001 | OP_REQ_TX_001 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_REQ_TX_001 |
| wave_op_req_tx_full_001 | OP_REQ_TX_FULL_001 | spi_host | event_list_decoder | verification | interface=spi_host; operation=OP_REQ_TX_FULL_001 |

## 5. Test Matrix
| Test | Expected Result |
| --- | --- |
| FFM-OPCODES | tests not recorded |
| FFM-BOUNDARIES | tests not recorded |
| reset_mid_frame | scenario |
| label_filtering | scenario |
| parity_odd_even | scenario |
| selftest_loopback | scenario |
| status_polling | scenario |
| FIFO pressure: fill TX to 32 and attempt 33rd write. | stress |
| FIFO pressure: fill RX to 32 and accept 33rd word. | stress |
| PS+PL register sanity through generated address window. | fpga-realistic |
| PS+PL driver/receiver digital pin sampler sanity. | fpga-realistic |
| partial_spi_byte | negative |
| unsupported_opcode_no_side_effect | negative |
| id=BE-001; text=After MR, tx_control, rx_control, aclk_division, and flag assignment registers read default zero; TX empty is asserted. | baseline |

## 6. Coverage
| Field | Value |
| --- | --- |
| functional_coverage | id=COV-SPI-OPCODES; bins=opcode_04, opcode_08, opcode_0C, opcode_10, opcode_24, opcode_40, opcode_44, opcode_80, opcode_84, opcode_A0, opcode_C0, id=COV-RESET-MODES; bins=MR, opcode_04, opcode_44, id=COV-FIFO-LEVELS; bins=empty, half, full, overflow_policy |
| code_coverage_targets | control_fsm, fifo_policies, arinc_tx_rx_paths |
| cross_coverage | opcode_group_x_access_direction, fifo_level_x_policy |
| illegal_bins | command_only_opcode_crossed_with_read_payload, pin_level_external_claim_without_board_evidence |
| closure_thresholds | functional_coverage_min=80, checked_transactions_min=64 |
| assumptions | Coverage gain is valid only with scoreboard checks enabled. |

## 7. Assertions
| Field | Value |
| --- | --- |
| assertions | id=A-TOP-NO-SECOND-RESET; target=hi3593_v2_top; intent=Only MR is exposed as a top-level reset input., id=A-SPI-BYTE-BOUNDARY; target=spi_slave_if; intent=No command side effect is emitted for incomplete SPI bytes., id=A-SPI-CDC-SINGLE-CMD; target=spi_cmd_cdc; intent=Each complete SPI command produces exactly one ACLK command pulse and one SCK acknowledge., id=A-MAILBOX-READ-CLEAR; target=rx_mailbox_status; intent=Mailbox valid pins clear after their read opcode while mailbox payload remains available for readback., id=A-FIFO-BOUNDS; target=sync_fifo; intent=FIFO count stays in 0..32 and honors selected full policy., id=A-TX-NULL-GAP; target=arinc429_tx; intent=TX driver controls return to NULL during reset, selftest, and word gaps. |
| bind_targets | output/uvm/assertions/hi3593_v2_assertions.sv |
| disabled_conditions | reset_active |
| severity_policy | assertion_failure_is_loop2_fail |
| assumptions | not recorded |

## 8. Waveform Secondary Check Plan
| Check | Evidence |
| --- | --- |
| reset_release | covered by waveform intent |
| spi_opcode_activity | covered by waveform intent |
| arinc_tx_response | covered by waveform intent |
| mailbox_status | covered by waveform intent |
| WAVE-RESET | MR, TEMPTY, TFULL |
| WAVE-SPI | CS, SCK, SI, SO |
| WAVE-TX | TX1IN, TX0IN, SLP |

## 9. Directed TB Log / Waveform Artifact Contract
| Contract Area | Value |
| --- | --- |
| no directed TB contract | not recorded |

## 10. UVM Environment Plan
| Area | Item | Detail |
| --- | --- | --- |
| framework | root | output/uvm |
| framework | template_family | rkv_style_uvm |
| framework | package_entry | output/uvm/env/uvm_pkg.sv |
| framework | tb_top | output/uvm/tb/tb_uvm.sv |
| framework | entry_check | work/loop2_uvm/sim/uvm_full_functional.do |
| framework | regression_entry | work/loop2_uvm/sim/regression.do |
| required_entry_file | output/uvm/tb/tb_dut_if.sv | Loop2 compile prerequisite |
| required_entry_file | output/uvm/env/uvm_pkg.sv | Loop2 compile prerequisite |
| required_entry_file | output/uvm/tb/tb_uvm.sv | Loop2 compile prerequisite |
| interface | tb_dut_if | ACLK, MR, CS, SCK, SI, SO, TX1IN, TX0IN, SLP |
| agent | spi_agent | active |
| agent | arinc_logic_agent | active_passive |

## 11. UVM Tests / Scoreboards / Coverage
| Kind | Item | Plan / Trace |
| --- | --- | --- |
| scoreboard | scoreboard | scoreboard check |
| trace | REQ-SPI-001 | UVM trace target |
| trace | REQ-SPI-002 | UVM trace target |
| trace | REQ-RST-001 | UVM trace target |
| trace | REQ-RST-002 | UVM trace target |
| trace | REQ-FIFO-001 | UVM trace target |
| trace | REQ-ARINC-001 | UVM trace target |
| trace | REQ-RX-001 | UVM trace target |
| trace | REQ-TX-001 | UVM trace target |
| trace | REQ-STATUS-001 | UVM trace target |
| trace | REQ-PROTO-001 | UVM trace target |

## 12. UVM Multi-Scenario Obligations
| Sequence | Operation | Coverage Bins | Scoreboard | Assertions | Status |
| --- | --- | --- | --- | --- | --- |
| seq_op_asm_boundary_001 | OP_ASM_BOUNDARY_001 | op_asm_boundary_001_nominal, op_asm_boundary_001_reset_interaction, op_asm_boundary_001_negative_or_boundary | reference_model | assert_op_asm_boundary_001_blackbox_response | planned |
| seq_op_baseline_seed_001 | OP_BASELINE_SEED_001 | op_baseline_seed_001_nominal, op_baseline_seed_001_reset_interaction, op_baseline_seed_001_negative_or_boundary | reference_model | assert_op_baseline_seed_001_blackbox_response | planned |
| seq_op_req_aclk_001 | OP_REQ_ACLK_001 | op_req_aclk_001_nominal, op_req_aclk_001_reset_interaction, op_req_aclk_001_negative_or_boundary | reference_model | assert_op_req_aclk_001_blackbox_response | planned |
| seq_op_req_arinc_001 | OP_REQ_ARINC_001 | op_req_arinc_001_nominal, op_req_arinc_001_reset_interaction, op_req_arinc_001_negative_or_boundary | reference_model | assert_op_req_arinc_001_blackbox_response | planned |
| seq_op_req_fifo_001 | OP_REQ_FIFO_001 | op_req_fifo_001_nominal, op_req_fifo_001_reset_interaction, op_req_fifo_001_negative_or_boundary | reference_model | assert_op_req_fifo_001_blackbox_response | planned |
| seq_op_req_flagint_001 | OP_REQ_FLAGINT_001 | op_req_flagint_001_nominal, op_req_flagint_001_reset_interaction, op_req_flagint_001_negative_or_boundary | reference_model | assert_op_req_flagint_001_blackbox_response | planned |
| seq_op_req_inst_001 | OP_REQ_INST_001 | op_req_inst_001_nominal, op_req_inst_001_reset_interaction, op_req_inst_001_negative_or_boundary | reference_model | assert_op_req_inst_001_blackbox_response | planned |
| seq_op_req_label_001 | OP_REQ_LABEL_001 | op_req_label_001_nominal, op_req_label_001_reset_interaction, op_req_label_001_negative_or_boundary | reference_model | assert_op_req_label_001_blackbox_response | planned |
| seq_op_req_mailbox_001 | OP_REQ_MAILBOX_001 | op_req_mailbox_001_nominal, op_req_mailbox_001_reset_interaction, op_req_mailbox_001_negative_or_boundary | reference_model | assert_op_req_mailbox_001_blackbox_response | planned |
| seq_op_req_mb_pins_001 | OP_REQ_MB_PINS_001 | op_req_mb_pins_001_nominal, op_req_mb_pins_001_reset_interaction, op_req_mb_pins_001_negative_or_boundary | reference_model | assert_op_req_mb_pins_001_blackbox_response | planned |
| seq_op_req_plabel_001 | OP_REQ_PLABEL_001 | op_req_plabel_001_nominal, op_req_plabel_001_reset_interaction, op_req_plabel_001_negative_or_boundary | reference_model | assert_op_req_plabel_001_blackbox_response | planned |
| seq_op_req_proto_001 | OP_REQ_PROTO_001 | op_req_proto_001_nominal, op_req_proto_001_reset_interaction, op_req_proto_001_negative_or_boundary | reference_model | assert_op_req_proto_001_blackbox_response | planned |
| seq_op_req_rst_001 | OP_REQ_RST_001 | op_req_rst_001_nominal, op_req_rst_001_reset_interaction, op_req_rst_001_negative_or_boundary | reference_model | assert_op_req_rst_001_blackbox_response | planned |
| seq_op_req_rst_002 | OP_REQ_RST_002 | op_req_rst_002_nominal, op_req_rst_002_reset_interaction, op_req_rst_002_negative_or_boundary | reference_model | assert_op_req_rst_002_blackbox_response | planned |
| seq_op_req_rx_001 | OP_REQ_RX_001 | op_req_rx_001_nominal, op_req_rx_001_reset_interaction, op_req_rx_001_negative_or_boundary | reference_model | assert_op_req_rx_001_blackbox_response | planned |
| seq_op_req_rx_filter_001 | OP_REQ_RX_FILTER_001 | op_req_rx_filter_001_nominal, op_req_rx_filter_001_reset_interaction, op_req_rx_filter_001_negative_or_boundary | reference_model | assert_op_req_rx_filter_001_blackbox_response | planned |
| seq_op_req_spi_001 | OP_REQ_SPI_001 | op_req_spi_001_nominal, op_req_spi_001_reset_interaction, op_req_spi_001_negative_or_boundary | reference_model | assert_op_req_spi_001_blackbox_response | planned |
| seq_op_req_spi_002 | OP_REQ_SPI_002 | op_req_spi_002_nominal, op_req_spi_002_reset_interaction, op_req_spi_002_negative_or_boundary | reference_model | assert_op_req_spi_002_blackbox_response | planned |
| seq_op_req_status_001 | OP_REQ_STATUS_001 | op_req_status_001_nominal, op_req_status_001_reset_interaction, op_req_status_001_negative_or_boundary | reference_model | assert_op_req_status_001_blackbox_response | planned |
| seq_op_req_tx_001 | OP_REQ_TX_001 | op_req_tx_001_nominal, op_req_tx_001_reset_interaction, op_req_tx_001_negative_or_boundary | reference_model | assert_op_req_tx_001_blackbox_response | planned |
| seq_op_req_tx_full_001 | OP_REQ_TX_FULL_001 | op_req_tx_full_001_nominal, op_req_tx_full_001_reset_interaction, op_req_tx_full_001_negative_or_boundary | reference_model | assert_op_req_tx_full_001_blackbox_response | planned |

## 13. FPGA Validation Matrix
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

## 14. Exit Criteria
| Criteria | Evidence |
| --- | --- |
| AC-SPI-001 | SPI write/read transactions complete only on byte boundaries while CS is active low, and partial transfers are discarded. |
| AC-RST-001 | Top RTL exposes MR and has no hard_reset, soft_reset, or sw_reset top-level input; opcode 0x04 clears architectural state through reset_ctrl. |
| AC-RST-002 | Opcode 0x44 clears TX/RX FIFO counters and priority mailboxes while retaining control register values. |
| AC-FIFO-001 | TX full ignores the 33rd write; RX full accepts the 33rd word by overwriting the 32nd storage location. |
| AC-ARINC-001 | VCD windows show reset release, SPI command activity, TX driver-control response, and receiver FIFO/status response with no X/Z on required top ports except SO high-Z policy modeled as idle zero in FPGA RTL. |
| AC-UVM-001 | UVM scoreboard checks legal label/parity/SDI/FIFO scenarios from a spec reference model, not from DUT behavior. |
| AC-PROTO-001 | Loop3 reports classify IP-level, PS/PL emulation, external pin-level, and full hardware claims under claim_policy. |

<!-- HDL-VERIF-DOC END -->
