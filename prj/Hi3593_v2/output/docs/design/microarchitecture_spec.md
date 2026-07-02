---
doc_type: microarchitecture_specification
project: Hi3593_v2
ip_name: hi3593_v2_top
version: DRAFT
status: DRAFT
generated_at: 2026-07-02T15:57:21
generator: hdlflow.docgen.microarchitecture_specification
source_manifest: output/docs/manifests/microarchitecture_doc_manifest.json
owner_agent: Arch
review_agents: [Exec, Sim, Review, Arbtr]
change_id: CR-20260702155634-forbid-directed-tb-markdown-sidecar
---

# hi3593_v2_top Microarchitecture Specification

<!-- HDL-UARCH-DOC START -->

## 0. Document Status
| Item | Value |
| --- | --- |
| Project | Hi3593_v2 |
| IP / Module | hi3593_v2_top |
| Status | DRAFT |
| Owner Agent | Arch |
| Review Agents | Exec, Sim, Review, Arbtr |
| Generated At | 2026-07-02T15:57:21 |
| Change ID | CR-20260702155634-forbid-directed-tb-markdown-sidecar |

## 1. Design Overview
hierarchy_only_top
## 2. Requirement-to-Architecture Summary
| Requirement | Domain | Design Sections | Affected Modules | Verification Hooks |
| --- | --- | --- | --- | --- |
| ASM-BOUNDARY-001 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_ASM_BOUNDARY_001, vcd=OP_ASM_BOUNDARY_001, uvm=OP_ASM_BOUNDARY_001, fpga=ASM-BOUNDARY-001 |
| BASELINE-SEED-001 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_BASELINE_SEED_001, vcd=OP_BASELINE_SEED_001, uvm=OP_BASELINE_SEED_001, fpga=BASELINE-SEED-001 |
| REQ-ACLK-001 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_REQ_ACLK_001, vcd=OP_REQ_ACLK_001, uvm=OP_REQ_ACLK_001, fpga=REQ-ACLK-001 |
| REQ-ARINC-001 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_REQ_ARINC_001, vcd=OP_REQ_ARINC_001, uvm=OP_REQ_ARINC_001, fpga=REQ-ARINC-001 |
| REQ-FIFO-001 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_REQ_FIFO_001, vcd=OP_REQ_FIFO_001, uvm=OP_REQ_FIFO_001, fpga=REQ-FIFO-001 |
| REQ-FLAGINT-001 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_REQ_FLAGINT_001, vcd=OP_REQ_FLAGINT_001, uvm=OP_REQ_FLAGINT_001, fpga=REQ-FLAGINT-001 |
| REQ-INST-001 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_REQ_INST_001, vcd=OP_REQ_INST_001, uvm=OP_REQ_INST_001, fpga=REQ-INST-001 |
| REQ-LABEL-001 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_REQ_LABEL_001, vcd=OP_REQ_LABEL_001, uvm=OP_REQ_LABEL_001, fpga=REQ-LABEL-001 |
| REQ-MAILBOX-001 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_REQ_MAILBOX_001, vcd=OP_REQ_MAILBOX_001, uvm=OP_REQ_MAILBOX_001, fpga=REQ-MAILBOX-001 |
| REQ-MB-PINS-001 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_REQ_MB_PINS_001, vcd=OP_REQ_MB_PINS_001, uvm=OP_REQ_MB_PINS_001, fpga=REQ-MB-PINS-001 |
| REQ-PLABEL-001 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_REQ_PLABEL_001, vcd=OP_REQ_PLABEL_001, uvm=OP_REQ_PLABEL_001, fpga=REQ-PLABEL-001 |
| REQ-PROTO-001 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_REQ_PROTO_001, vcd=OP_REQ_PROTO_001, uvm=OP_REQ_PROTO_001, fpga=REQ-PROTO-001 |
| REQ-RST-001 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_REQ_RST_001, vcd=OP_REQ_RST_001, uvm=OP_REQ_RST_001, fpga=REQ-RST-001 |
| REQ-RST-002 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_REQ_RST_002, vcd=OP_REQ_RST_002, uvm=OP_REQ_RST_002, fpga=REQ-RST-002 |
| REQ-RX-001 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_REQ_RX_001, vcd=OP_REQ_RX_001, uvm=OP_REQ_RX_001, fpga=REQ-RX-001 |
| REQ-RX-FILTER-001 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_REQ_RX_FILTER_001, vcd=OP_REQ_RX_FILTER_001, uvm=OP_REQ_RX_FILTER_001, fpga=REQ-RX-FILTER-001 |
| REQ-SPI-001 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_REQ_SPI_001, vcd=OP_REQ_SPI_001, uvm=OP_REQ_SPI_001, fpga=REQ-SPI-001 |
| REQ-SPI-002 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_REQ_SPI_002, vcd=OP_REQ_SPI_002, uvm=OP_REQ_SPI_002, fpga=REQ-SPI-002 |
| REQ-STATUS-001 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_REQ_STATUS_001, vcd=OP_REQ_STATUS_001, uvm=OP_REQ_STATUS_001, fpga=REQ-STATUS-001 |
| REQ-TX-001 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_REQ_TX_001, vcd=OP_REQ_TX_001, uvm=OP_REQ_TX_001, fpga=REQ-TX-001 |
| REQ-TX-FULL-001 | unassigned | Microarchitecture Specification / Requirement-to-Architecture Summary, Microarchitecture Specification / Module Ownership Matrix, Verification Plan / Operation Model, Verification Plan / TB VCD UVM FPGA Semantic Obligations | hi3593_v2_top | tb=OP_REQ_TX_FULL_001, vcd=OP_REQ_TX_FULL_001, uvm=OP_REQ_TX_FULL_001, fpga=REQ-TX-FULL-001 |

## 3. Functional Domain Model
| Domain | Requirements | Owner Modules | Interfaces | Verification Focus |
| --- | --- | --- | --- | --- |
| unassigned | ASM-BOUNDARY-001, BASELINE-SEED-001, REQ-ACLK-001, REQ-ARINC-001, REQ-FIFO-001, REQ-FLAGINT-001, REQ-INST-001, REQ-LABEL-001, REQ-MAILBOX-001, REQ-MB-PINS-001, REQ-PLABEL-001, REQ-PROTO-001, REQ-RST-001, REQ-RST-002, REQ-RX-001, REQ-RX-FILTER-001, REQ-SPI-001, REQ-SPI-002, REQ-STATUS-001, REQ-TX-001, REQ-TX-FULL-001 | hi3593_v2_top | spi_host | directed_tb, waveform_semantic, uvm, fpga |

## 4. Module Ownership Matrix
| Requirement | Domain | RTL Owner | Interface Owner | Verification Owner |
| --- | --- | --- | --- | --- |
| ASM-BOUNDARY-001 | unassigned | hi3593_v2_top | spi_host | tb=OP_ASM_BOUNDARY_001, vcd=OP_ASM_BOUNDARY_001, uvm=OP_ASM_BOUNDARY_001, fpga=ASM-BOUNDARY-001 |
| BASELINE-SEED-001 | unassigned | hi3593_v2_top | spi_host | tb=OP_BASELINE_SEED_001, vcd=OP_BASELINE_SEED_001, uvm=OP_BASELINE_SEED_001, fpga=BASELINE-SEED-001 |
| REQ-ACLK-001 | unassigned | hi3593_v2_top | spi_host | tb=OP_REQ_ACLK_001, vcd=OP_REQ_ACLK_001, uvm=OP_REQ_ACLK_001, fpga=REQ-ACLK-001 |
| REQ-ARINC-001 | unassigned | hi3593_v2_top | spi_host | tb=OP_REQ_ARINC_001, vcd=OP_REQ_ARINC_001, uvm=OP_REQ_ARINC_001, fpga=REQ-ARINC-001 |
| REQ-FIFO-001 | unassigned | hi3593_v2_top | spi_host | tb=OP_REQ_FIFO_001, vcd=OP_REQ_FIFO_001, uvm=OP_REQ_FIFO_001, fpga=REQ-FIFO-001 |
| REQ-FLAGINT-001 | unassigned | hi3593_v2_top | spi_host | tb=OP_REQ_FLAGINT_001, vcd=OP_REQ_FLAGINT_001, uvm=OP_REQ_FLAGINT_001, fpga=REQ-FLAGINT-001 |
| REQ-INST-001 | unassigned | hi3593_v2_top | spi_host | tb=OP_REQ_INST_001, vcd=OP_REQ_INST_001, uvm=OP_REQ_INST_001, fpga=REQ-INST-001 |
| REQ-LABEL-001 | unassigned | hi3593_v2_top | spi_host | tb=OP_REQ_LABEL_001, vcd=OP_REQ_LABEL_001, uvm=OP_REQ_LABEL_001, fpga=REQ-LABEL-001 |
| REQ-MAILBOX-001 | unassigned | hi3593_v2_top | spi_host | tb=OP_REQ_MAILBOX_001, vcd=OP_REQ_MAILBOX_001, uvm=OP_REQ_MAILBOX_001, fpga=REQ-MAILBOX-001 |
| REQ-MB-PINS-001 | unassigned | hi3593_v2_top | spi_host | tb=OP_REQ_MB_PINS_001, vcd=OP_REQ_MB_PINS_001, uvm=OP_REQ_MB_PINS_001, fpga=REQ-MB-PINS-001 |
| REQ-PLABEL-001 | unassigned | hi3593_v2_top | spi_host | tb=OP_REQ_PLABEL_001, vcd=OP_REQ_PLABEL_001, uvm=OP_REQ_PLABEL_001, fpga=REQ-PLABEL-001 |
| REQ-PROTO-001 | unassigned | hi3593_v2_top | spi_host | tb=OP_REQ_PROTO_001, vcd=OP_REQ_PROTO_001, uvm=OP_REQ_PROTO_001, fpga=REQ-PROTO-001 |
| REQ-RST-001 | unassigned | hi3593_v2_top | spi_host | tb=OP_REQ_RST_001, vcd=OP_REQ_RST_001, uvm=OP_REQ_RST_001, fpga=REQ-RST-001 |
| REQ-RST-002 | unassigned | hi3593_v2_top | spi_host | tb=OP_REQ_RST_002, vcd=OP_REQ_RST_002, uvm=OP_REQ_RST_002, fpga=REQ-RST-002 |
| REQ-RX-001 | unassigned | hi3593_v2_top | spi_host | tb=OP_REQ_RX_001, vcd=OP_REQ_RX_001, uvm=OP_REQ_RX_001, fpga=REQ-RX-001 |
| REQ-RX-FILTER-001 | unassigned | hi3593_v2_top | spi_host | tb=OP_REQ_RX_FILTER_001, vcd=OP_REQ_RX_FILTER_001, uvm=OP_REQ_RX_FILTER_001, fpga=REQ-RX-FILTER-001 |
| REQ-SPI-001 | unassigned | hi3593_v2_top | spi_host | tb=OP_REQ_SPI_001, vcd=OP_REQ_SPI_001, uvm=OP_REQ_SPI_001, fpga=REQ-SPI-001 |
| REQ-SPI-002 | unassigned | hi3593_v2_top | spi_host | tb=OP_REQ_SPI_002, vcd=OP_REQ_SPI_002, uvm=OP_REQ_SPI_002, fpga=REQ-SPI-002 |
| REQ-STATUS-001 | unassigned | hi3593_v2_top | spi_host | tb=OP_REQ_STATUS_001, vcd=OP_REQ_STATUS_001, uvm=OP_REQ_STATUS_001, fpga=REQ-STATUS-001 |
| REQ-TX-001 | unassigned | hi3593_v2_top | spi_host | tb=OP_REQ_TX_001, vcd=OP_REQ_TX_001, uvm=OP_REQ_TX_001, fpga=REQ-TX-001 |
| REQ-TX-FULL-001 | unassigned | hi3593_v2_top | spi_host | tb=OP_REQ_TX_FULL_001, vcd=OP_REQ_TX_FULL_001, uvm=OP_REQ_TX_FULL_001, fpga=REQ-TX-FULL-001 |

## 5. Logic Level Design
| Module | Clock / Reset | Owned State | Internal Subblocks | Coding Behavior | Verification Hooks |
| --- | --- | --- | --- | --- | --- |
| hi3593_v2_top | ACLK / MR | registers=none; register_fields=none; fsms=none; fifos=none; memories=none; counters=none; arbiters=none; error_flags=none | none | Hierarchy-only top that exposes MR, SPI, status, and digital ARINC driver/receiver boundary ports. | tests=T-MR-SHARED; assertions=A-TOP-NO-SECOND-RESET; coverage=COV-TOP-PORTS |
| reset_ctrl | ACLK / MR | registers=none; register_fields=none; fsms=none; fifos=none; memories=none; counters=mr_sync_chain; arbiters=none; error_flags=none | none | Synchronize MR into ACLK, merge opcode_04 master reset request, and generate FIFO-only reset for opcode_44. | tests=T-MR-SHARED, T-SWRESET-44; assertions=A-RESET-EFFECTS; coverage=COV-RESET-MODES |
| spi_slave_if | SCK / MR | registers=none; register_fields=none; fsms=spi_frame_fsm; fifos=none; memories=none; counters=spi_bit_count, spi_byte_count; arbiters=none; error_flags=spi_partial_discard | none | Own SPI mode 0 byte framing, opcode capture, variable write/read transfer lengths, and SCK-domain command request hold. | tests=T-SPI-PARTIAL, T-OPCODE-MATRIX; assertions=A-SPI-BYTE-BOUNDARY; coverage=COV-SPI-OPCODES |
| spi_cmd_cdc | ACLK / MR | registers=none; register_fields=none; fsms=spi_cdc_response_fsm; fifos=none; memories=none; counters=none; arbiters=none; error_flags=none | none | Own bundled request/acknowledge CDC for SPI command transactions and ACLK readback response transfer. | tests=T-SPI-PARTIAL, T-OPCODE-MATRIX; assertions=A-SPI-BYTE-BOUNDARY; coverage=COV-SPI-OPCODES |
| control_status_regs | ACLK / MR | registers=tx_control, rx1_control, rx2_control, flag_interrupt_assignment, aclk_division; register_fields=TMODE, SELFTEST, TPARITY, RATE, LABREC, PLON; fsms=register_command_fsm; fifos=none; memories=rx1_label_memory, rx2_label_memory, priority_label_registers; counters=none; arbiters=read_data_mux; error_flags=none | none | Own control/status registers, label memories, priority-label registers, command side effects, FIFO commands, mailbox clear pulses, and readback muxing. | tests=T-OPCODE-MATRIX, T-SWRESET-44; assertions=A-REG-RESET; coverage=COV-REG-ACCESS |
| rx_mailbox_status | ACLK / MR | registers=rx1_mailbox1, rx1_mailbox2, rx1_mailbox3, rx2_mailbox1, rx2_mailbox2, rx2_mailbox3, MB1_1, MB1_2, MB1_3, MB2_1, MB2_2, MB2_3, R1FLAG, R2FLAG, R1INT, R2INT; register_fields=none; fsms=none; fifos=none; memories=none; counters=none; arbiters=flag_interrupt_assignment_mux; error_flags=parity_error_status, label_reject_status | none | Own RX priority mailbox payloads, MB valid pins, receiver status bytes, and R1/R2 flag-interrupt output selection. | tests=rx1_priority_mailbox_slot1, opcode_a4_read_rx1_mailbox_1; assertions=A-REG-RESET; coverage=COV-REG-ACCESS |
| sync_fifo | ACLK / MR | registers=none; register_fields=none; fsms=none; fifos=tx_fifo, rx1_fifo, rx2_fifo; memories=fifo_mem; counters=wr_ptr, rd_ptr, count; arbiters=none; error_flags=overflow_seen | none | Reusable 32-depth by 32-bit FIFO with selectable RX overwrite-on-full or TX ignore-on-full policy. | tests=rx_location32_overwrite, tx_fifo_full_ignore; assertions=A-FIFO-BOUNDS; coverage=COV-FIFO-LEVELS |
| arinc429_tx | ACLK / MR | registers=none; register_fields=none; fsms=arinc_tx_fsm; fifos=none; memories=none; counters=tx_bit_count, tx_cell_count, tx_gap_count; arbiters=none; error_flags=none | none | Own TX FIFO pop scheduling, optional parity generation, ARINC bit-cell sequencing, and HI-8592 digital driver controls TX1IN/TX0IN/SLP. | tests=selftest_null_driver, parity_odd_even; assertions=A-TX-NULL-GAP; coverage=COV-TX-RATE-PARITY |
| arinc429_rx | ACLK / MR | registers=none; register_fields=none; fsms=arinc_rx_fsm; fifos=none; memories=none; counters=rx_bit_count, rx_gap_count; arbiters=none; error_flags=parity_error, label_reject | none | Own decoded OUTA/OUTB sampling, ARINC word assembly, parity/SDI/label filtering, and accepted RX word handoff. | tests=label_filtering, parity_odd_even; assertions=A-RX-FILTER; coverage=COV-RX-FILTERS |

## 6. Implementation Order / Granularity
| Order | Item | Detail |
| --- | --- | --- |
| 1 | sync_fifo | sync_fifo.v |
| 2 | reset_ctrl | reset_ctrl.v |
| 3 | spi_slave_if | spi_slave_if.v |
| 4 | spi_cmd_cdc | spi_cmd_cdc.v |
| 5 | control_status_regs | control_status_regs.v |
| 6 | rx_mailbox_status | rx_mailbox_status.v |
| 7 | arinc429_tx | arinc429_tx.v |
| 8 | arinc429_rx | arinc429_rx.v |
| 9 | hi3593_v2_top | hi3593_v2_top.v |
| policy | planning_order | top_down |
| policy | file_boundary_rule | Use one RTL file for a cohesive protocol, register, FIFO, datapath, status, or boundary block. |
| policy | split_when | a child has independent clock/reset ownership, a child has reusable storage/IP ownership, a child is a separately verifiable protocol or datapath boundary, keeping it inside the parent would create a broad monolithic FSM or hidden side effect |
| policy | keep_inside_parent_when | the logic is only a small decode, mux, counter, bit-order, parity, or pulse-generation subblock, the subblock has no independent interface contract, the subblock is only meaningful inside one protocol engine |
| policy | naming_rule | Protocol-facing modules use official or industry names such as spi_slave_if, arinc429_tx, or arinc429_rx. |

## 7. Storage / FIFO / Counter Plan
| Module | Source File | Storage / Counter Ownership | Reset Rule |
| --- | --- | --- | --- |
| reset_ctrl | reset_ctrl.v | counters: mr_sync_chain | MR |
| spi_slave_if | spi_slave_if.v | counters: spi_bit_count, spi_byte_count; error_flags: spi_partial_discard | MR |
| control_status_regs | control_status_regs.v | registers: tx_control, rx1_control, rx2_control, flag_interrupt_assignment, aclk_division; register_fields: TMODE, SELFTEST, TPARITY, RATE, LABREC, PLON; memories: rx1_label_memory, rx2_label_memory, priority_label_registers | MR |
| rx_mailbox_status | rx_mailbox_status.v | registers: rx1_mailbox1, rx1_mailbox2, rx1_mailbox3, rx2_mailbox1, rx2_mailbox2, rx2_mailbox3, MB1_1, MB1_2, MB1_3, MB2_1, MB2_2, MB2_3, R1FLAG, R2FLAG, R1INT, R2INT; error_flags: parity_error_status, label_reject_status | MR |
| sync_fifo | sync_fifo.v | fifos: tx_fifo, rx1_fifo, rx2_fifo; memories: fifo_mem; counters: wr_ptr, rd_ptr, count; error_flags: overflow_seen | MR |
| arinc429_tx | arinc429_tx.v | counters: tx_bit_count, tx_cell_count, tx_gap_count | MR |
| arinc429_rx | arinc429_rx.v | counters: rx_bit_count, rx_gap_count; error_flags: parity_error, label_reject | MR |

## 8. State Machines
| FSM | Owning Module | Reset State | States | Transitions | Illegal State Behavior |
| --- | --- | --- | --- | --- | --- |
| spi_frame_fsm | spi_slave_if | reset state not specified | states not specified | transitions not specified | illegal-state behavior not specified |
| register_command_fsm | control_status_regs | reset state not specified | states not specified | transitions not specified | illegal-state behavior not specified |
| spi_cdc_response_fsm | spi_cmd_cdc | reset state not specified | states not specified | transitions not specified | illegal-state behavior not specified |
| arinc_tx_fsm | arinc429_tx | reset state not specified | states not specified | transitions not specified | illegal-state behavior not specified |
| arinc_rx_fsm | arinc429_rx | reset state not specified | states not specified | transitions not specified | illegal-state behavior not specified |

## 9. Module Topology
| Module | Role | Description / Source |
| --- | --- | --- |
| hi3593_v2_top | top integration | hierarchy_only_top |
| module_partition_policy | planning policy | hierarchy_required=True; one_primary_module_per_file=True; top_down_partitioning=True; file_boundary_granularity=functional_domain; cohesive_responsibility_per_file=True; composite_modules_instantiate_children=True; allow_internal_subblocks_without_files=True; no_over_fragmentation=True; no_under_fragmentation=True; no_monolithic_fsm=True; no_free_floating_top_logic=True; protocol_module_names_follow_official_standard=True; explicit_ownership_required=True |
| clock_reset_item | clock/reset | clock/reset responsibility |
| hi3593_v2_top | Hierarchy-only top that exposes MR, SPI, status, and digital ARINC driver/receiver boundary ports. | reset_ctrl, spi_slave_if, spi_cmd_cdc, control_status_regs, rx_mailbox_status, sync_fifo, arinc429_tx, arinc429_rx |
| reset_ctrl | Synchronize MR into ACLK, merge opcode_04 master reset request, and generate FIFO-only reset for opcode_44. | source-defined module |
| spi_slave_if | Own SPI mode 0 byte framing, opcode capture, variable write/read transfer lengths, and SCK-domain command request hold. | source-defined module |
| spi_cmd_cdc | Own bundled request/acknowledge CDC for SPI command transactions and ACLK readback response transfer. | source-defined module |
| control_status_regs | Own control/status registers, label memories, priority-label registers, command side effects, FIFO commands, mailbox clear pulses, and readback muxing. | source-defined module |
| rx_mailbox_status | Own RX priority mailbox payloads, MB valid pins, receiver status bytes, and R1/R2 flag-interrupt output selection. | source-defined module |
| sync_fifo | Reusable 32-depth by 32-bit FIFO with selectable RX overwrite-on-full or TX ignore-on-full policy. | source-defined module |
| arinc429_tx | Own TX FIFO pop scheduling, optional parity generation, ARINC bit-cell sequencing, and HI-8592 digital driver controls TX1IN/TX0IN/SLP. | source-defined module |
| arinc429_rx | Own decoded OUTA/OUTB sampling, ARINC word assembly, parity/SDI/label filtering, and accepted RX word handoff. | source-defined module |
| arinc429_rx | RTL source | output/rtl/arinc429_rx.v |
| arinc429_tx | RTL source | output/rtl/arinc429_tx.v |
| control_status_regs | RTL source | output/rtl/control_status_regs.v |
| hi3593_v2_top | RTL source | output/rtl/hi3593_v2_top.v |
| reset_ctrl | RTL source | output/rtl/reset_ctrl.v |
| rx_mailbox_status | RTL source | output/rtl/rx_mailbox_status.v |
| spi_cmd_cdc | RTL source | output/rtl/spi_cmd_cdc.v |
| spi_slave_if | RTL source | output/rtl/spi_slave_if.v |
| sync_fifo | RTL source | output/rtl/sync_fifo.v |

## 10. Interfaces
| Interface | Type / Protocol | Description |
| --- | --- | --- |
| spi_mode0 | SPI mode 0 half-duplex | CS, SCK, SI, SO |
| arinc429_driver_logic | HI-8592 digital driver control | TX1IN, TX0IN, SLP |
| arinc429_receiver_logic | HI-8450 decoded receiver logic | OUT1A, OUT1B, OUT2A, OUT2B |
| priority_mailbox_outputs | HI-3593 priority-label mailbox valid pins | MB1_1, MB1_2, MB1_3, MB2_1, MB2_2, MB2_3 |
| spi_cmd_req | SCK-domain SPI command request held until CDC acknowledgement. | One command strobe per complete SPI command/data payload., No strobe for partial byte transfers., Dummy read clocks while a command is pending do not decode a second opcode. |
| spi_cmd_aclk | Single ACLK pulse per accepted SPI command with paired readback data capture. | Register side effects occur in ACLK domain only., Readback data is captured before the CDC acknowledge returns to SCK. |
| mailbox_status_bus | Mailbox/status block owns RX mailbox state; register block owns read-clear pulses and readback muxing. | Read mailbox opcode clears the valid bit after data is available to readback., Opcode 44 clears FIFO and mailbox state while retaining control registers. |
| tx_fifo_bus | Single-cycle FIFO push/read status. | TX full ignores write. |
| tx_word_if | TX engine pops words when TMODE or opcode_40 permits transmission. | TX pop only when FIFO not empty. |
| rx_word_if | RX engine writes accepted words to RX FIFO with overwrite-on-full policy. | Accepted RX word is not dropped solely because count is full. |
| arinc_driver_logic | HI-8592 digital driver control. | TX1IN/TX0IN both zero mean NULL; both one request Hi-Z only in external driver contexts. |
| spi_host | spi | defined by source interface |

## 11. Interface Contract
| Interface | Protocol | Top Module | Ports | Observability |
| --- | --- | --- | --- | --- |
| spi_host | spi | hi3593_v2_top | name=ACLK; direction=input; width=1, name=MR; direction=input; width=1, name=CS; direction=input; width=1, name=SCK; direction=input; width=1, name=SI; direction=input; width=1, name=SO; direction=output; width=1, name=OUT1A; direction=input; width=1, name=OUT1B; direction=input; width=1, name=OUT2A; direction=input; width=1, name=OUT2B; direction=input; width=1, name=TX1IN; direction=output; width=1, name=TX0IN; direction=output; width=1, name=SLP; direction=output; width=1, name=TEMPTY; direction=output; width=1, name=TFULL; direction=output; width=1, name=R1FLAG; direction=output; width=1, name=R2FLAG; direction=output; width=1, name=R1INT; direction=output; width=1, name=R2INT; direction=output; width=1, name=MB1_1; direction=output; width=1, name=MB1_2; direction=output; width=1, name=MB1_3; direction=output; width=1, name=MB2_1; direction=output; width=1, name=MB2_2; direction=output; width=1, name=MB2_3; direction=output; width=1 | TB, waveform, UVM monitor, and FPGA evidence must observe this boundary |

## 12. Clocks and Resets
| Field | Value |
| --- | --- |
| clock_domains | name=ACLK; source=top_port, name=SCK; source=top_port |
| resets | name=MR; domain=ACLK; type=external_active_high_then_synchronized |
| latency_requirements | id=LAT-SPI; rule=SPI command side effect may appear after SCK-to-ACLK handshake., id=LAT-TX; rule=TX driver logic follows selected ARINC high/low bit timing. |
| cdc_requirements | id=CDC-SPI-ACLK; interface=spi_cmd_req; producer_module=spi_slave_if; consumer_module=spi_cmd_cdc; from_clock_domain=SCK; to_clock_domain=ACLK; synchronizer=request_ack_toggle; req_ids=REQ-SPI-001, REQ-SPI-002 |
| timing_constraints | id=TC-SCK; interface=spi_cmd_req; min_period_ns=100 |
| assumptions | not recorded |

## 13. Dataflow
| Field | Value |
| --- | --- |
| flows | id=DF-SPI-REG; name=spi_command_to_registers; producer_module=spi_slave_if; consumer_module=control_status_regs; path=SI, spi_slave_if, spi_cmd_req, spi_cmd_cdc, aclk_cmd_valid, control_status_regs; payload=opcode_and_data; control=CS_active_low_and_byte_complete; latency=synchronizer_handshake; req_ids=REQ-SPI-001, REQ-SPI-002, id=DF-TX; name=tx_fifo_to_driver_logic; producer_module=sync_fifo; consumer_module=arinc429_tx; path=tx_fifo_rdata, arinc429_tx, TX1IN, TX0IN, SLP; payload=arinc429_word; control=TMODE_or_opcode_40; latency=selected_arinc_bit_timing; req_ids=REQ-TX-001, id=DF-RX; name=receiver_logic_to_rx_fifo; producer_module=arinc429_rx; consumer_module=sync_fifo; path=OUTA_OUTB, arinc429_rx, rx_word_if, rx_fifo; payload=accepted_arinc429_word; control=label_sdi_parity_filter; latency=one_aclk_after_word_accept; req_ids=REQ-RX-001, id=DF-RX-MAILBOX; name=receiver_logic_to_mailbox_status; producer_module=arinc429_rx; consumer_module=rx_mailbox_status; path=OUTA_OUTB, arinc429_rx, rx_word_if, rx_mailbox_status, MB_valid_pins, R1_R2_flags; payload=accepted_priority_arinc429_word; control=priority_label_match_and_read_clear_pulse; latency=one_aclk_after_word_accept; req_ids=REQ-MAILBOX-001, REQ-MB-PINS-001, REQ-FLAGINT-001 |
| control_paths | id=CP-RESET; path=MR, reset_ctrl, master_reset_pulse |
| datapaths | id=DP-FIFO; path=sync_fifo, control_status_regs, id=DP-SPI-CDC; path=spi_slave_if, spi_cmd_cdc, control_status_regs, id=DP-MAILBOX; path=arinc429_rx, rx_mailbox_status, control_status_regs |
| backpressure | id=BP-TX-FULL; rule=TX full ignores new writes., id=BP-RX-FULL; rule=RX full overwrites location 32 for accepted words. |
| assumptions | not recorded |

## 14. State / Registers
| Offset / Opcode | Register / Command | Access / Width | Reset | Description |
| --- | --- | --- | --- | --- |
| address assigned by opcode map | tx_control | 8 | 0x00 | [HIZ, TFLIP, TMODE, SELFTEST, ODDEVEN, TPARITY, X, RATE] |
| address assigned by opcode map | rx1_control | 8 | 0x00 | [RFLIP, SD9, SD10, SDON, PARITY, LABREC, PLON, RATE] |
| address assigned by opcode map | rx2_control | 8 | 0x00 | [RFLIP, SD9, SD10, SDON, PARITY, LABREC, PLON, RATE] |
| address assigned by opcode map | flag_interrupt_assignment | 8 | 0x00 | [R2INT_1_0, R2FLAG_1_0, R1INT_1_0, R1FLAG_1_0] |
| address assigned by opcode map | aclk_division | 8 | 0x00 | [X7, X6, X5, DIV3, DIV2, DIV1, DIV0, X0] |
| address assigned by opcode map | rx1_label_memory | 256 | 0x0000000000000000000000000000000000000000000000000000000000000000 | register fields not specified |
| address assigned by opcode map | rx2_label_memory | 256 | 0x0000000000000000000000000000000000000000000000000000000000000000 | register fields not specified |
| address assigned by opcode map | rx1_priority_label_match | 24 | 0x000000 | [PL3, PL2, PL1] |
| address assigned by opcode map | rx2_priority_label_match | 24 | 0x000000 | [PL3, PL2, PL1] |
| address assigned by opcode map | rx_priority_mailboxes | 24 | 0x000000 | register fields not specified |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |
| opcode not specified | unnamed_command | command | not applicable: opcode row | command behavior defined by opcode name |

## 15. Operation Model Hooks
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

<!-- HDL-UARCH-DOC END -->
