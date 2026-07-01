---
report_schema: hdlflow_report_v1
report_type: loop2
project: Hi3593_v2
stage: loop2_uvm
result: PASS
generated_at: 2026-06-30T22:30:16
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
| Total Checks | 64 |
| Failed Checks | 0 |
| Coverage | 100.0 |

```text
******************************************************************************************^^^^**********^^^^^***********************^^^^**^^^****************************************************************************************************
```

## 1. Summary
All structured checks passed.

## 2. Main Results
| Test ID | Txn ID | Sent | Expected RX | Actual RX | Latency Cycles | Result |
| --- | --- | --- | --- | --- | ---: | --- |
| reset_mid_frame | txn_1 | opcode_04 | code_100 | code_100 | 0 | PASS |
| reset_mid_frame | txn_2 | opcode_04 | code_100 | code_100 | 0 | PASS |
| overflow_fifo_full_stress | txn_3 | opcode_0c | code_103 | code_103 | 0 | PASS |
| overflow_fifo_full_stress | txn_4 | opcode_0c | code_103 | code_103 | 0 | PASS |
| baud_div_434 | txn_5 | opcode_38 | code_104 | code_104 | 0 | PASS |
| baud_div_434 | txn_6 | opcode_38 | code_104 | code_104 | 0 | PASS |
| opcode_matrix | txn_7 | opcode_08 | code_208 | code_208 | 0 | PASS |
| opcode_matrix | txn_8 | opcode_10 | code_216 | code_216 | 0 | PASS |
| opcode_matrix | txn_9 | opcode_24 | code_236 | code_236 | 0 | PASS |
| opcode_matrix | txn_10 | opcode_0c | code_212 | code_212 | 0 | PASS |
| opcode_matrix | txn_11 | opcode_44 | code_268 | code_268 | 0 | PASS |
| opcode_matrix | txn_12 | opcode_80 | code_328 | code_328 | 0 | PASS |
| opcode_matrix | txn_13 | opcode_84 | code_332 | code_332 | 0 | PASS |
| opcode_matrix | txn_14 | opcode_a0 | code_360 | code_360 | 0 | PASS |
| opcode_matrix | txn_15 | opcode_c0 | code_392 | code_392 | 0 | PASS |
| opcode_matrix | txn_16 | opcode_40 | code_264 | code_264 | 0 | PASS |
| opcode_matrix | txn_17 | opcode_04 | code_204 | code_204 | 0 | PASS |
| opcode_matrix | txn_18 | opcode_08 | code_208 | code_208 | 0 | PASS |
| opcode_matrix | txn_19 | opcode_10 | code_216 | code_216 | 0 | PASS |
| opcode_matrix | txn_20 | opcode_24 | code_236 | code_236 | 0 | PASS |
| opcode_matrix | txn_21 | opcode_0c | code_212 | code_212 | 0 | PASS |
| opcode_matrix | txn_22 | opcode_44 | code_268 | code_268 | 0 | PASS |
| opcode_matrix | txn_23 | opcode_80 | code_328 | code_328 | 0 | PASS |
| opcode_matrix | txn_24 | opcode_84 | code_332 | code_332 | 0 | PASS |
| opcode_matrix | txn_25 | opcode_a0 | code_360 | code_360 | 0 | PASS |
| opcode_matrix | txn_26 | opcode_c0 | code_392 | code_392 | 0 | PASS |
| opcode_matrix | txn_27 | opcode_40 | code_264 | code_264 | 0 | PASS |
| opcode_matrix | txn_28 | opcode_04 | code_204 | code_204 | 0 | PASS |
| opcode_matrix | txn_29 | opcode_08 | code_208 | code_208 | 0 | PASS |
| opcode_matrix | txn_30 | opcode_10 | code_216 | code_216 | 0 | PASS |
| opcode_matrix | txn_31 | opcode_24 | code_236 | code_236 | 0 | PASS |
| opcode_matrix | txn_32 | opcode_0c | code_212 | code_212 | 0 | PASS |
| opcode_matrix | txn_33 | opcode_44 | code_268 | code_268 | 0 | PASS |
| opcode_matrix | txn_34 | opcode_80 | code_328 | code_328 | 0 | PASS |
| opcode_matrix | txn_35 | opcode_84 | code_332 | code_332 | 0 | PASS |
| opcode_matrix | txn_36 | opcode_a0 | code_360 | code_360 | 0 | PASS |
| opcode_matrix | txn_37 | opcode_c0 | code_392 | code_392 | 0 | PASS |
| opcode_matrix | txn_38 | opcode_40 | code_264 | code_264 | 0 | PASS |
| opcode_matrix | txn_39 | opcode_04 | code_204 | code_204 | 0 | PASS |
| opcode_matrix | txn_40 | opcode_08 | code_208 | code_208 | 0 | PASS |
| opcode_matrix | txn_41 | opcode_10 | code_216 | code_216 | 0 | PASS |
| opcode_matrix | txn_42 | opcode_24 | code_236 | code_236 | 0 | PASS |
| opcode_matrix | txn_43 | opcode_0c | code_212 | code_212 | 0 | PASS |
| opcode_matrix | txn_44 | opcode_44 | code_268 | code_268 | 0 | PASS |
| opcode_matrix | txn_45 | opcode_80 | code_328 | code_328 | 0 | PASS |
| opcode_matrix | txn_46 | opcode_84 | code_332 | code_332 | 0 | PASS |
| opcode_matrix | txn_47 | opcode_a0 | code_360 | code_360 | 0 | PASS |
| opcode_matrix | txn_48 | opcode_c0 | code_392 | code_392 | 0 | PASS |
| opcode_matrix | txn_49 | opcode_40 | code_264 | code_264 | 0 | PASS |
| opcode_matrix | txn_50 | opcode_04 | code_204 | code_204 | 0 | PASS |
| opcode_matrix | txn_51 | opcode_08 | code_208 | code_208 | 0 | PASS |
| opcode_matrix | txn_52 | opcode_10 | code_216 | code_216 | 0 | PASS |
| opcode_matrix | txn_53 | opcode_24 | code_236 | code_236 | 0 | PASS |
| opcode_matrix | txn_54 | opcode_0c | code_212 | code_212 | 0 | PASS |
| opcode_matrix | txn_55 | opcode_44 | code_268 | code_268 | 0 | PASS |
| opcode_matrix | txn_56 | opcode_80 | code_328 | code_328 | 0 | PASS |
| opcode_matrix | txn_57 | opcode_84 | code_332 | code_332 | 0 | PASS |
| opcode_matrix | txn_58 | opcode_a0 | code_360 | code_360 | 0 | PASS |
| opcode_matrix | txn_59 | opcode_c0 | code_392 | code_392 | 0 | PASS |
| opcode_matrix | txn_60 | opcode_40 | code_264 | code_264 | 0 | PASS |
| opcode_matrix | txn_61 | opcode_04 | code_204 | code_204 | 0 | PASS |
| opcode_matrix | txn_62 | opcode_08 | code_208 | code_208 | 0 | PASS |
| opcode_matrix | txn_63 | opcode_10 | code_216 | code_216 | 0 | PASS |
| opcode_matrix | txn_64 | opcode_24 | code_236 | code_236 | 0 | PASS |

## 3. Failed Items
No failed checks.

## 4. Notes
Generated from structured HDLFLOW events.
