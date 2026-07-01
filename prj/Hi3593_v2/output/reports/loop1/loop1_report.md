---
report_schema: hdlflow_report_v1
report_type: loop1
project: Hi3593_v2
stage: loop1_rtl_tb
result: PASS
generated_at: 2026-06-30T22:43:20
change_id: null
source_cmd: work/loop1_rtl_tb/current/cmd/command.json
source_manifest: work/loop1_rtl_tb/current/manifest.json
report_json: output/reports/loop1/loop1_report.json
report_manifest: output/reports/loop1/loop1_report_manifest.json
---
# Loop1 RTL/TB Report

<!-- HDL-REPORT START -->

## 0. Result
| Field | Value |
| --- | --- |
| Stage | `loop1_rtl_tb` |
| Result | **PASS** |
| Total Tests | 11 |
| Passed Tests | 11 |
| Failed Tests | 0 |
| Total Checks | 32 |
| Passed Checks | 32 |
| Failed Checks | 0 |

```text
******************************************************************************************^^^^**********^^^^^***********************^^^^**^^^****************************************************************************************************
```

## 1. Summary
All structured checks passed.

## 2. Main Results
| Test ID | Txn ID | Sent | Expected RX | Actual RX | Latency Cycles | Result |
| --- | --- | --- | --- | --- | ---: | --- |
| reset_release | opcode_04_reset_baseline | MR=external_active_high | tx_control_0_fifo_empty_1 | reset_defaults_sampled | 8 | PASS |
| partial_spi_byte_discard | partial_bits_before_cs_inactive | CS_low_three_bits_then_high | partial_discard_1 | partial_discard_sampled | 4 | PASS |
| opcode_00_no_operation | opcode_00 | opcode_00 | no_side_effect_opcode_latched | spi_opcode_00h | 4 | PASS |
| opcode_08_write_tx_control | opcode_08 | opcode_08_data_15h | tx_control_15h | tx_control_sampled | 4 | PASS |
| opcode_10_write_rx1_control | opcode_10 | opcode_10_data_00h | rx1_control_00h | rx1_control_sampled | 4 | PASS |
| opcode_24_write_rx2_control | opcode_24 | opcode_24_data_00h | rx2_control_00h | rx2_control_sampled | 4 | PASS |
| opcode_84_read_tx_control | opcode_84 | opcode_84_read | read_opcode_latched | spi_opcode_84h | 4 | PASS |
| opcode_80_read_tx_status | opcode_80 | opcode_80_read | read_opcode_latched | spi_opcode_80h | 4 | PASS |
| opcode_ff_no_operation | opcode_FF | opcode_ff | no_side_effect_opcode_latched | spi_opcode_ffh | 4 | PASS |
| opcode_14_write_rx1_label_memory | opcode_14 | opcode_14_32_bytes | rx1_label_memory_pattern | rx1_label_memory_sampled | 32 | PASS |
| opcode_98_read_rx1_label_memory | opcode_98 | opcode_98_read_32 | rx1_label_read_opcode_latched | spi_opcode_98h | 4 | PASS |
| opcode_48_set_all_rx1_labels | opcode_48 | opcode_48 | rx1_label_memory_all_ones | rx1_label_all_sampled | 4 | PASS |
| opcode_b8_read_rx2_label_memory | opcode_B8 | opcode_b8_read_32 | rx2_label_read_opcode_latched | spi_opcode_b8h | 4 | PASS |
| opcode_4c_set_all_rx2_labels | opcode_4C | opcode_4c | rx2_label_memory_all_ones | rx2_label_all_sampled | 4 | PASS |
| opcode_18_write_rx1_priority_labels | opcode_18 | opcode_18_112233 | rx1_priority_labels_112233 | priority_labels_sampled | 4 | PASS |
| opcode_9c_read_rx1_priority_labels | opcode_9C | opcode_9c_read | rx1_priority_read_opcode_latched | spi_opcode_9ch | 4 | PASS |
| opcode_bc_read_rx2_priority_labels | opcode_BC | opcode_bc_read | rx2_priority_read_opcode_latched | spi_opcode_bch | 4 | PASS |
| rx1_priority_mailbox_slot1 | rx1_label_33 | OUT1_word_label_33 | MB1_1_valid_mailbox_aabbcc | mailbox_sampled | 6 | PASS |
| opcode_a4_read_rx1_mailbox_1 | opcode_A4 | opcode_a4_read | MB1_1_cleared_after_read | mb1_1_clear_sampled | 4 | PASS |
| opcode_34_write_flag_interrupt_assignment | opcode_34 | opcode_34_55h | flag_assignment_55h | flag_assignment_sampled | 4 | PASS |
| opcode_38_write_aclk_division | opcode_38 | opcode_38_b2h | aclk_division_b2h | aclk_division_sampled | 4 | PASS |
| opcode_d0_read_flag_interrupt_assignment | opcode_D0 | opcode_d0_read | flag_read_opcode_latched | spi_opcode_d0h | 4 | PASS |
| opcode_d4_read_aclk_division | opcode_D4 | opcode_d4_read | aclk_read_opcode_latched | spi_opcode_d4h | 4 | PASS |
| tx_fifo_full_ignore_opcode_0c | fill_to_32 | opcode_0c_x32 | tx_fifo_count_32_full_1 | tx_fifo_full_sampled | 32 | PASS |
| tx_fifo_full_ignore | write_when_full | opcode_0c_extra_word | tx_count_stays_32_no_overflow | tx_full_ignore_sampled | 4 | PASS |
| master_reset_keeps_control_register_opcode44_boundary | opcode_44 | opcode_44_fifo_mailbox_reset | tx_control_kept_fifo_clear | opcode_44_boundary_sampled | 6 | PASS |
| opcode_04_master_reset | opcode_04 | opcode_04_master_reset | control_and_fifo_cleared | master_reset_sampled | 10 | PASS |
| rx_location32_overwrite | rx1_33_words | OUT1A_OUT1B_33_words | rx_count_32_overflow_seen | rx_overwrite_sampled | 33 | PASS |
| opcode_a0_read_rx1_fifo | opcode_A0 | opcode_a0_read | rx1_read_opcode_latched | spi_opcode_a0h | 4 | PASS |
| opcode_c0_read_rx2_fifo | opcode_C0 | opcode_c0_read | rx2_read_opcode_latched | spi_opcode_c0h | 4 | PASS |
| opcode_40_transmit_enable | opcode_40 | opcode_40_after_tx_fifo_word | tx_driver_activity | tx_activity_sampled | 80 | PASS |
| selftest_null_driver | selftest | tx_control_selftest_then_opcode_40 | tx1in_0_tx0in_0_while_busy | selftest_null_sampled | 40 | PASS |

## 3. Failed Items
No failed checks.

## 4. Notes
Generated from structured HDLFLOW events.
