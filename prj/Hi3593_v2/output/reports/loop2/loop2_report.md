---
report_schema: hdlflow_report_v1
report_type: loop2
project: Hi3593_v2
stage: loop2_uvm
result: PASS
generated_at: 2026-07-02T15:59:22
change_id: null
source_cmd: work/loop2_uvm/current/cmd/command.json
source_manifest: work/loop2_uvm/current/manifest.json
report_json: output/reports/loop2/loop2_report.json
report_manifest: output/reports/loop2/loop2_report_manifest.json
---
# Loop2 UVM Report

<!-- HDL-REPORT START -->

## 0. Result
| Field | Value |
| --- | --- |
| Stage | `loop2_uvm` |
| Result | **PASS** |
| Uvm Error | 0 |
| Uvm Fatal | 0 |
| Total Checks | 124 |
| Failed Checks | 0 |
| Coverage | 100.00 |
| Coverage Source | coverage_collector |

```text
******************************************************************************************^^^^**********^^^^^***********************^^^^**^^^****************************************************************************************************
```

## 1. Summary
All structured checks passed.

## 2. Main Results
| Test ID | Txn ID | Sent | Expected RX | Actual RX | Latency Cycles | Result |
| --- | --- | --- | --- | --- | ---: | --- |
| reset_mid_frame | txn_1 | opcode_04 | code_100 | code_100 | 0 | PASS |
| reset_mid_frame | txn_2 | opcode_08 | code_100 | code_100 | 0 | PASS |
| reset_mid_frame | txn_3 | opcode_0c | code_100 | code_100 | 0 | PASS |
| reset_mid_frame | txn_4 | opcode_10 | code_100 | code_100 | 0 | PASS |
| reset_mid_frame | txn_5 | opcode_24 | code_100 | code_100 | 0 | PASS |
| reset_mid_frame | txn_6 | opcode_40 | code_100 | code_100 | 0 | PASS |
| reset_mid_frame | txn_7 | opcode_44 | code_100 | code_100 | 0 | PASS |
| reset_mid_frame | txn_8 | opcode_80 | code_100 | code_100 | 0 | PASS |
| reset_mid_frame | txn_9 | opcode_84 | code_100 | code_100 | 0 | PASS |
| reset_mid_frame | txn_10 | opcode_a0 | code_100 | code_100 | 0 | PASS |
| reset_mid_frame | txn_11 | opcode_c0 | code_100 | code_100 | 0 | PASS |
| bad_stop_bit_partial | txn_12 | opcode_04 | code_101 | code_101 | 0 | PASS |
| bad_stop_bit_partial | txn_13 | opcode_08 | code_101 | code_101 | 0 | PASS |
| bad_stop_bit_partial | txn_14 | opcode_0c | code_101 | code_101 | 0 | PASS |
| bad_stop_bit_partial | txn_15 | opcode_10 | code_101 | code_101 | 0 | PASS |
| bad_stop_bit_partial | txn_16 | opcode_24 | code_101 | code_101 | 0 | PASS |
| bad_stop_bit_partial | txn_17 | opcode_40 | code_101 | code_101 | 0 | PASS |
| bad_stop_bit_partial | txn_18 | opcode_44 | code_101 | code_101 | 0 | PASS |
| bad_stop_bit_partial | txn_19 | opcode_80 | code_101 | code_101 | 0 | PASS |
| bad_stop_bit_partial | txn_20 | opcode_84 | code_101 | code_101 | 0 | PASS |
| bad_stop_bit_partial | txn_21 | opcode_a0 | code_101 | code_101 | 0 | PASS |
| bad_stop_bit_partial | txn_22 | opcode_c0 | code_101 | code_101 | 0 | PASS |
| glitch_short_pulse_noise | txn_23 | opcode_04 | code_102 | code_102 | 0 | PASS |
| glitch_short_pulse_noise | txn_24 | opcode_08 | code_102 | code_102 | 0 | PASS |
| glitch_short_pulse_noise | txn_25 | opcode_0c | code_102 | code_102 | 0 | PASS |
| glitch_short_pulse_noise | txn_26 | opcode_10 | code_102 | code_102 | 0 | PASS |
| glitch_short_pulse_noise | txn_27 | opcode_24 | code_102 | code_102 | 0 | PASS |
| glitch_short_pulse_noise | txn_28 | opcode_40 | code_102 | code_102 | 0 | PASS |
| glitch_short_pulse_noise | txn_29 | opcode_44 | code_102 | code_102 | 0 | PASS |
| glitch_short_pulse_noise | txn_30 | opcode_80 | code_102 | code_102 | 0 | PASS |
| glitch_short_pulse_noise | txn_31 | opcode_84 | code_102 | code_102 | 0 | PASS |
| glitch_short_pulse_noise | txn_32 | opcode_a0 | code_102 | code_102 | 0 | PASS |
| glitch_short_pulse_noise | txn_33 | opcode_c0 | code_102 | code_102 | 0 | PASS |
| overflow_fifo_full_stress | txn_34 | opcode_04 | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_35 | opcode_08 | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_36 | opcode_0c | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_37 | opcode_10 | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_38 | opcode_24 | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_39 | opcode_40 | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_40 | opcode_44 | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_41 | opcode_80 | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_42 | opcode_84 | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_43 | opcode_a0 | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_44 | opcode_c0 | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_45 | opcode_04 | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_46 | opcode_08 | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_47 | opcode_0c | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_48 | opcode_10 | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_49 | opcode_24 | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_50 | opcode_40 | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_51 | opcode_44 | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_52 | opcode_80 | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_53 | opcode_84 | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_54 | opcode_a0 | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_55 | opcode_c0 | code_103 | code_103 | 0 | PASS |
| baud_div_434 | txn_56 | opcode_04 | code_104 | code_104 | 0 | PASS |
| baud_div_434 | txn_57 | opcode_08 | code_104 | code_104 | 0 | PASS |
| baud_div_434 | txn_58 | opcode_0c | code_104 | code_104 | 0 | PASS |
| baud_div_434 | txn_59 | opcode_10 | code_104 | code_104 | 0 | PASS |
| baud_div_434 | txn_60 | opcode_24 | code_104 | code_104 | 0 | PASS |
| baud_div_434 | txn_61 | opcode_40 | code_104 | code_104 | 0 | PASS |
| baud_div_434 | txn_62 | opcode_44 | code_104 | code_104 | 0 | PASS |
| baud_div_434 | txn_63 | opcode_80 | code_104 | code_104 | 0 | PASS |
| baud_div_434 | txn_64 | opcode_84 | code_104 | code_104 | 0 | PASS |
| baud_div_434 | txn_65 | opcode_a0 | code_104 | code_104 | 0 | PASS |
| baud_div_434 | txn_66 | opcode_c0 | code_104 | code_104 | 0 | PASS |
| opcode_matrix | txn_67 | opcode_04 | code_204 | code_204 | 0 | PASS |
| opcode_matrix | txn_68 | opcode_08 | code_208 | code_208 | 0 | PASS |
| opcode_matrix | txn_69 | opcode_0c | code_212 | code_212 | 0 | PASS |
| opcode_matrix | txn_70 | opcode_10 | code_216 | code_216 | 0 | PASS |
| opcode_matrix | txn_71 | opcode_24 | code_236 | code_236 | 0 | PASS |
| opcode_matrix | txn_72 | opcode_40 | code_264 | code_264 | 0 | PASS |
| opcode_matrix | txn_73 | opcode_44 | code_268 | code_268 | 0 | PASS |
| opcode_matrix | txn_74 | opcode_80 | code_328 | code_328 | 0 | PASS |
| opcode_matrix | txn_75 | opcode_84 | code_332 | code_332 | 0 | PASS |
| opcode_matrix | txn_76 | opcode_a0 | code_360 | code_360 | 0 | PASS |
| opcode_matrix | txn_77 | opcode_c0 | code_392 | code_392 | 0 | PASS |
| opcode_matrix | txn_78 | opcode_04 | code_204 | code_204 | 0 | PASS |
| opcode_matrix | txn_79 | opcode_08 | code_208 | code_208 | 0 | PASS |
| opcode_matrix | txn_80 | opcode_0c | code_212 | code_212 | 0 | PASS |
| opcode_matrix | txn_81 | opcode_10 | code_216 | code_216 | 0 | PASS |
| opcode_matrix | txn_82 | opcode_24 | code_236 | code_236 | 0 | PASS |
| opcode_matrix | txn_83 | opcode_40 | code_264 | code_264 | 0 | PASS |
| opcode_matrix | txn_84 | opcode_44 | code_268 | code_268 | 0 | PASS |
| opcode_matrix | txn_85 | opcode_80 | code_328 | code_328 | 0 | PASS |
| opcode_matrix | txn_86 | opcode_84 | code_332 | code_332 | 0 | PASS |
| opcode_matrix | txn_87 | opcode_a0 | code_360 | code_360 | 0 | PASS |
| opcode_matrix | txn_88 | opcode_c0 | code_392 | code_392 | 0 | PASS |
| opcode_matrix | txn_89 | opcode_04 | code_204 | code_204 | 0 | PASS |
| opcode_matrix | txn_90 | opcode_08 | code_208 | code_208 | 0 | PASS |
| opcode_matrix | txn_91 | opcode_0c | code_212 | code_212 | 0 | PASS |
| opcode_matrix | txn_92 | opcode_10 | code_216 | code_216 | 0 | PASS |
| opcode_matrix | txn_93 | opcode_24 | code_236 | code_236 | 0 | PASS |
| opcode_matrix | txn_94 | opcode_40 | code_264 | code_264 | 0 | PASS |
| opcode_matrix | txn_95 | opcode_44 | code_268 | code_268 | 0 | PASS |
| opcode_matrix | txn_96 | opcode_80 | code_328 | code_328 | 0 | PASS |
| opcode_matrix | txn_97 | opcode_84 | code_332 | code_332 | 0 | PASS |
| opcode_matrix | txn_98 | opcode_a0 | code_360 | code_360 | 0 | PASS |
| opcode_matrix | txn_99 | opcode_c0 | code_392 | code_392 | 0 | PASS |
| opcode_matrix | txn_100 | opcode_04 | code_204 | code_204 | 0 | PASS |
| opcode_matrix | txn_101 | opcode_08 | code_208 | code_208 | 0 | PASS |
| opcode_matrix | txn_102 | opcode_0c | code_212 | code_212 | 0 | PASS |
| opcode_matrix | txn_103 | opcode_10 | code_216 | code_216 | 0 | PASS |
| opcode_matrix | txn_104 | opcode_24 | code_236 | code_236 | 0 | PASS |
| opcode_matrix | txn_105 | opcode_40 | code_264 | code_264 | 0 | PASS |
| opcode_matrix | txn_106 | opcode_44 | code_268 | code_268 | 0 | PASS |
| opcode_matrix | txn_107 | opcode_80 | code_328 | code_328 | 0 | PASS |
| opcode_matrix | txn_108 | opcode_84 | code_332 | code_332 | 0 | PASS |
| opcode_matrix | txn_109 | opcode_a0 | code_360 | code_360 | 0 | PASS |
| opcode_matrix | txn_110 | opcode_c0 | code_392 | code_392 | 0 | PASS |
| opcode_matrix | txn_111 | opcode_04 | code_204 | code_204 | 0 | PASS |
| opcode_matrix | txn_112 | opcode_08 | code_208 | code_208 | 0 | PASS |
| opcode_matrix | txn_113 | opcode_0c | code_212 | code_212 | 0 | PASS |
| opcode_matrix | txn_114 | opcode_10 | code_216 | code_216 | 0 | PASS |
| opcode_matrix | txn_115 | opcode_24 | code_236 | code_236 | 0 | PASS |
| opcode_matrix | txn_116 | opcode_40 | code_264 | code_264 | 0 | PASS |
| opcode_matrix | txn_117 | opcode_44 | code_268 | code_268 | 0 | PASS |
| opcode_matrix | txn_118 | opcode_80 | code_328 | code_328 | 0 | PASS |
| opcode_matrix | txn_119 | opcode_84 | code_332 | code_332 | 0 | PASS |
| opcode_matrix | txn_120 | opcode_a0 | code_360 | code_360 | 0 | PASS |
| opcode_matrix | txn_121 | opcode_c0 | code_392 | code_392 | 0 | PASS |
| opcode_matrix | txn_122 | opcode_04 | code_204 | code_204 | 0 | PASS |
| opcode_matrix | txn_123 | opcode_08 | code_208 | code_208 | 0 | PASS |
| opcode_matrix | txn_124 | opcode_0c | code_212 | code_212 | 0 | PASS |

## 2.1 Semantic Coverage
| Field | Value |
| --- | --- |
| Covered Requirements Count | 21 |
| Covered Operation Count | 21 |
| Scenario Count | 124 |
| Scenario Kind Count | 4 |
| Scenario Kinds | long, negative, nominal, randomized |
| Reference Model Check Count | 124 |
| Monitor Observed Check Count | 124 |
| Cross Coverage Count | 124 |
| Assertion Check Count | 124 |
| Negative Test Count | 31 |
| Randomized Test Count | 31 |
| Long Sequence Count | 31 |
| Coverage Source | coverage_collector |

## 3. Failed Items
No failed checks.

## 4. Notes
Generated from structured HDLFLOW events.
