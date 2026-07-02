---
doc_type: application_guide
project: Hi3593_v2
ip_name: hi3593_v2_top
version: DRAFT
status: DRAFT
generated_at: 2026-07-02T15:57:20
generator: hdlflow.docgen.application_guide
source_manifest: output/docs/manifests/application_doc_manifest.json
owner_agent: Spec
review_agents: [Arch, Review, Arbtr]
change_id: CR-20260702155634-forbid-directed-tb-markdown-sidecar
---

# hi3593_v2_top Application Guide

<!-- HDL-APP-DOC START -->

## 0. Document Status
| Item | Value |
| --- | --- |
| Project | Hi3593_v2 |
| IP / Module | hi3593_v2_top |
| Status | DRAFT |
| Owner Agent | Spec |
| Review Agents | Arch, Review, Arbtr |
| Generated At | 2026-07-02T15:57:20 |
| Change ID | CR-20260702155634-forbid-directed-tb-markdown-sidecar |

## 1. Black Box View
not recorded
## 2. User Visible Features
| Requirement ID | Requirement Text |
| --- | --- |
| REQ-SPI-001 | requirement text supplied as inline item |
| REQ-SPI-002 | requirement text supplied as inline item |
| REQ-RST-001 | requirement text supplied as inline item |
| REQ-RST-002 | requirement text supplied as inline item |
| REQ-FIFO-001 | requirement text supplied as inline item |
| REQ-ARINC-001 | requirement text supplied as inline item |
| REQ-RX-001 | requirement text supplied as inline item |
| REQ-TX-001 | requirement text supplied as inline item |
| REQ-STATUS-001 | requirement text supplied as inline item |
| REQ-PROTO-001 | requirement text supplied as inline item |

## 3. Integration View
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

## 4. Interfaces
| Port | Direction | Width | Owner |
| --- | --- | --- | --- |
| ACLK | input | 1 | interface_spec |
| MR | input | 1 | interface_spec |
| CS | input | 1 | interface_spec |
| SCK | input | 1 | interface_spec |
| SI | input | 1 | interface_spec |
| SO | output | 1 | interface_spec |
| OUT1A | input | 1 | interface_spec |
| OUT1B | input | 1 | interface_spec |
| OUT2A | input | 1 | interface_spec |
| OUT2B | input | 1 | interface_spec |
| TX1IN | output | 1 | interface_spec |
| TX0IN | output | 1 | interface_spec |
| SLP | output | 1 | interface_spec |
| TEMPTY | output | 1 | interface_spec |
| TFULL | output | 1 | interface_spec |
| R1FLAG | output | 1 | interface_spec |
| R2FLAG | output | 1 | interface_spec |
| R1INT | output | 1 | interface_spec |
| R2INT | output | 1 | interface_spec |
| MB1_1 | output | 1 | interface_spec |
| MB1_2 | output | 1 | interface_spec |
| MB1_3 | output | 1 | interface_spec |
| MB2_1 | output | 1 | interface_spec |
| MB2_2 | output | 1 | interface_spec |
| MB2_3 | output | 1 | interface_spec |
| unnamed_port | direction not specified | width not specified | interface_contracts |
| unnamed_port | direction not specified | width not specified | interface_contracts |
| unnamed_port | direction not specified | width not specified | interface_contracts |
| unnamed_port | direction not specified | width not specified | interface_contracts |
| unnamed_port | direction not specified | width not specified | interface_contracts |
| unnamed_port | direction not specified | width not specified | interface_contracts |
| unnamed_port | direction not specified | width not specified | interface_contracts |
| unnamed_port | direction not specified | width not specified | interface_contracts |
| unnamed_port | direction not specified | width not specified | interface_contracts |
| ACLK | input | 1 | arinc429_rx |
| reset | input | 1 | arinc429_rx |
| OUTA | input | 1 | arinc429_rx |
| OUTB | input | 1 | arinc429_rx |
| rx_control | input | [7:0] | arinc429_rx |
| label_memory | input | [255:0] | arinc429_rx |
| priority_labels | input | [23:0] | arinc429_rx |
| rx_word_valid | output | 1 | arinc429_rx |
| rx_word_data | output | [31:0] | arinc429_rx |
| priority_match | output | 1 | arinc429_rx |
| priority_slot | output | [1:0] | arinc429_rx |
| parity_error | output | 1 | arinc429_rx |
| label_reject | output | 1 | arinc429_rx |
| ACLK | input | 1 | arinc429_tx |
| reset | input | 1 | arinc429_tx |
| tx_start_pulse | input | 1 | arinc429_tx |
| tx_control | input | [7:0] | arinc429_tx |
| fifo_empty | input | 1 | arinc429_tx |
| fifo_rdata | input | [31:0] | arinc429_tx |
| fifo_rd | output | 1 | arinc429_tx |
| TX1IN | output | 1 | arinc429_tx |
| TX0IN | output | 1 | arinc429_tx |
| SLP | output | 1 | arinc429_tx |
| busy | output | 1 | arinc429_tx |
| ACLK | input | 1 | control_status_regs |
| master_reset | input | 1 | control_status_regs |
| fifo_reset | input | 1 | control_status_regs |
| spi_cmd_valid | input | 1 | control_status_regs |
| spi_opcode | input | [7:0] | control_status_regs |
| spi_wdata | input | [255:0] | control_status_regs |
| tx_fifo_empty | input | 1 | control_status_regs |
| tx_fifo_half | input | 1 | control_status_regs |
| tx_fifo_full | input | 1 | control_status_regs |
| rx1_fifo_rdata | input | [31:0] | control_status_regs |
| rx2_fifo_rdata | input | [31:0] | control_status_regs |
| rx1_status | input | [7:0] | control_status_regs |
| rx2_status | input | [7:0] | control_status_regs |
| rx1_mailbox1 | input | [23:0] | control_status_regs |
| rx1_mailbox2 | input | [23:0] | control_status_regs |
| rx1_mailbox3 | input | [23:0] | control_status_regs |
| rx2_mailbox1 | input | [23:0] | control_status_regs |
| rx2_mailbox2 | input | [23:0] | control_status_regs |
| rx2_mailbox3 | input | [23:0] | control_status_regs |
| read_data | output | [255:0] | control_status_regs |
| opcode_04_pulse | output | 1 | control_status_regs |
| opcode_44_pulse | output | 1 | control_status_regs |
| tx_fifo_wr | output | 1 | control_status_regs |
| tx_fifo_wdata | output | [31:0] | control_status_regs |
| tx_start_pulse | output | 1 | control_status_regs |
| rx1_fifo_rd | output | 1 | control_status_regs |
| rx2_fifo_rd | output | 1 | control_status_regs |
| rx1_mailbox1_clear | output | 1 | control_status_regs |
| rx1_mailbox2_clear | output | 1 | control_status_regs |
| rx1_mailbox3_clear | output | 1 | control_status_regs |
| rx2_mailbox1_clear | output | 1 | control_status_regs |
| rx2_mailbox2_clear | output | 1 | control_status_regs |
| rx2_mailbox3_clear | output | 1 | control_status_regs |
| tx_control | output | [7:0] | control_status_regs |
| rx1_control | output | [7:0] | control_status_regs |
| rx2_control | output | [7:0] | control_status_regs |
| flag_interrupt_assignment | output | [7:0] | control_status_regs |
| aclk_division | output | [7:0] | control_status_regs |
| rx1_label_memory | output | [255:0] | control_status_regs |
| rx2_label_memory | output | [255:0] | control_status_regs |
| rx1_priority_labels | output | [23:0] | control_status_regs |
| rx2_priority_labels | output | [23:0] | control_status_regs |
| TEMPTY | output | 1 | control_status_regs |
| TFULL | output | 1 | control_status_regs |
| ACLK | input | 1 | hi3593_v2_top |
| MR | input | 1 | hi3593_v2_top |
| CS | input | 1 | hi3593_v2_top |
| SCK | input | 1 | hi3593_v2_top |
| SI | input | 1 | hi3593_v2_top |
| SO | output | 1 | hi3593_v2_top |
| OUT1A | input | 1 | hi3593_v2_top |
| OUT1B | input | 1 | hi3593_v2_top |
| OUT2A | input | 1 | hi3593_v2_top |
| OUT2B | input | 1 | hi3593_v2_top |
| TX1IN | output | 1 | hi3593_v2_top |
| TX0IN | output | 1 | hi3593_v2_top |
| SLP | output | 1 | hi3593_v2_top |
| TEMPTY | output | 1 | hi3593_v2_top |
| TFULL | output | 1 | hi3593_v2_top |
| R1FLAG | output | 1 | hi3593_v2_top |
| R2FLAG | output | 1 | hi3593_v2_top |
| R1INT | output | 1 | hi3593_v2_top |
| R2INT | output | 1 | hi3593_v2_top |
| MB1_1 | output | 1 | hi3593_v2_top |
| MB1_2 | output | 1 | hi3593_v2_top |
| MB1_3 | output | 1 | hi3593_v2_top |
| MB2_1 | output | 1 | hi3593_v2_top |
| MB2_2 | output | 1 | hi3593_v2_top |
| MB2_3 | output | 1 | hi3593_v2_top |
| ACLK | input | 1 | reset_ctrl |
| MR | input | 1 | reset_ctrl |
| opcode_04_pulse | input | 1 | reset_ctrl |
| opcode_44_pulse | input | 1 | reset_ctrl |
| master_reset | output | 1 | reset_ctrl |
| fifo_reset | output | 1 | reset_ctrl |
| ACLK | input | 1 | rx_mailbox_status |
| master_reset | input | 1 | rx_mailbox_status |
| fifo_reset | input | 1 | rx_mailbox_status |
| flag_interrupt_assignment | input | [7:0] | rx_mailbox_status |
| rx1_fifo_empty | input | 1 | rx_mailbox_status |
| rx1_fifo_half | input | 1 | rx_mailbox_status |
| rx2_fifo_empty | input | 1 | rx_mailbox_status |
| rx2_fifo_half | input | 1 | rx_mailbox_status |
| rx1_word_valid | input | 1 | rx_mailbox_status |
| rx2_word_valid | input | 1 | rx_mailbox_status |
| rx1_word_data | input | [31:0] | rx_mailbox_status |
| rx2_word_data | input | [31:0] | rx_mailbox_status |
| rx1_priority_match | input | 1 | rx_mailbox_status |
| rx2_priority_match | input | 1 | rx_mailbox_status |
| rx1_priority_slot | input | [1:0] | rx_mailbox_status |
| rx2_priority_slot | input | [1:0] | rx_mailbox_status |
| rx1_parity_error | input | 1 | rx_mailbox_status |
| rx2_parity_error | input | 1 | rx_mailbox_status |
| rx1_label_reject | input | 1 | rx_mailbox_status |
| rx2_label_reject | input | 1 | rx_mailbox_status |
| rx1_mailbox1_clear | input | 1 | rx_mailbox_status |
| rx1_mailbox2_clear | input | 1 | rx_mailbox_status |
| rx1_mailbox3_clear | input | 1 | rx_mailbox_status |
| rx2_mailbox1_clear | input | 1 | rx_mailbox_status |
| rx2_mailbox2_clear | input | 1 | rx_mailbox_status |
| rx2_mailbox3_clear | input | 1 | rx_mailbox_status |
| rx1_status | output | [7:0] | rx_mailbox_status |
| rx2_status | output | [7:0] | rx_mailbox_status |
| rx1_mailbox1 | output | [23:0] | rx_mailbox_status |
| rx1_mailbox2 | output | [23:0] | rx_mailbox_status |
| rx1_mailbox3 | output | [23:0] | rx_mailbox_status |
| rx2_mailbox1 | output | [23:0] | rx_mailbox_status |
| rx2_mailbox2 | output | [23:0] | rx_mailbox_status |
| rx2_mailbox3 | output | [23:0] | rx_mailbox_status |
| R1FLAG | output | 1 | rx_mailbox_status |
| R2FLAG | output | 1 | rx_mailbox_status |
| R1INT | output | 1 | rx_mailbox_status |
| R2INT | output | 1 | rx_mailbox_status |
| MB1_1 | output | 1 | rx_mailbox_status |
| MB1_2 | output | 1 | rx_mailbox_status |
| MB1_3 | output | 1 | rx_mailbox_status |
| MB2_1 | output | 1 | rx_mailbox_status |
| MB2_2 | output | 1 | rx_mailbox_status |
| MB2_3 | output | 1 | rx_mailbox_status |
| select | input | [1:0] | rx_mailbox_status |
| fifo_not_empty | input | 1 | rx_mailbox_status |
| mailbox_any | input | 1 | rx_mailbox_status |
| word_valid | input | 1 | rx_mailbox_status |
| error_seen | input | 1 | rx_mailbox_status |
| ACLK | input | 1 | spi_cmd_cdc |
| SCK | input | 1 | spi_cmd_cdc |
| MR | input | 1 | spi_cmd_cdc |
| sck_cmd_req | input | 1 | spi_cmd_cdc |
| sck_opcode | input | [7:0] | spi_cmd_cdc |
| sck_wdata | input | [255:0] | spi_cmd_cdc |
| read_data_aclk | input | [255:0] | spi_cmd_cdc |
| sck_cmd_ack | output | 1 | spi_cmd_cdc |
| read_data_sck | output | [255:0] | spi_cmd_cdc |
| aclk_cmd_valid | output | 1 | spi_cmd_cdc |
| aclk_opcode | output | [7:0] | spi_cmd_cdc |
| aclk_wdata | output | [255:0] | spi_cmd_cdc |
| SCK | input | 1 | spi_slave_if |
| MR | input | 1 | spi_slave_if |
| CS | input | 1 | spi_slave_if |
| SI | input | 1 | spi_slave_if |
| read_data | input | [255:0] | spi_slave_if |
| spi_cmd_ack | input | 1 | spi_slave_if |
| SO | output | 1 | spi_slave_if |
| spi_cmd_req | output | 1 | spi_slave_if |
| spi_opcode | output | [7:0] | spi_slave_if |
| spi_wdata | output | [255:0] | spi_slave_if |
| spi_byte_count | output | [5:0] | spi_slave_if |
| partial_discard | output | 1 | spi_slave_if |
| opcode | input | [7:0] | spi_slave_if |
| opcode | input | [7:0] | spi_slave_if |
| opcode | input | [7:0] | spi_slave_if |
| clk | input | 1 | sync_fifo |
| rst | input | 1 | sync_fifo |
| clear | input | 1 | sync_fifo |
| wr_en | input | 1 | sync_fifo |
| rd_en | input | 1 | sync_fifo |
| wr_data | input | [31:0] | sync_fifo |
| rd_data | output | [31:0] | sync_fifo |
| empty | output | 1 | sync_fifo |
| half | output | 1 | sync_fifo |
| full | output | 1 | sync_fifo |
| count | output | [5:0] | sync_fifo |
| overflow_seen | output | 1 | sync_fifo |

## 5. Clocks and Resets
| Field | Value |
| --- | --- |
| no entries | not recorded |

## 6. Register / Config
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

## 7. Operation Sequence
| Step | Expected Result |
| --- | --- |
| OP_ASM_BOUNDARY_001 | observable functional response satisfies requirement: ASM-BOUNDARY-001 |
| OP_BASELINE_SEED_001 | observable functional response satisfies requirement: BASELINE-SEED-001 |
| OP_REQ_ACLK_001 | observable read response satisfies requirement: REQ-ACLK-001 |
| OP_REQ_ARINC_001 | observable stream response satisfies requirement: REQ-ARINC-001 |
| OP_REQ_FIFO_001 | observable write response satisfies requirement: REQ-FIFO-001 |
| OP_REQ_FLAGINT_001 | observable read response satisfies requirement: REQ-FLAGINT-001 |
| OP_REQ_INST_001 | observable write response satisfies requirement: REQ-INST-001 |
| OP_REQ_LABEL_001 | observable read response satisfies requirement: REQ-LABEL-001 |
| OP_REQ_MAILBOX_001 | observable read response satisfies requirement: REQ-MAILBOX-001 |
| OP_REQ_MB_PINS_001 | observable read response satisfies requirement: REQ-MB-PINS-001 |
| OP_REQ_PLABEL_001 | observable reset response satisfies requirement: REQ-PLABEL-001 |
| OP_REQ_PROTO_001 | observable read response satisfies requirement: REQ-PROTO-001 |
| OP_REQ_RST_001 | observable functional response satisfies requirement: REQ-RST-001 |
| OP_REQ_RST_002 | observable read response satisfies requirement: REQ-RST-002 |
| OP_REQ_RX_001 | observable stream response satisfies requirement: REQ-RX-001 |
| OP_REQ_RX_FILTER_001 | observable stream response satisfies requirement: REQ-RX-FILTER-001 |
| OP_REQ_SPI_001 | observable functional response satisfies requirement: REQ-SPI-001 |
| OP_REQ_SPI_002 | observable write response satisfies requirement: REQ-SPI-002 |
| OP_REQ_STATUS_001 | observable read response satisfies requirement: REQ-STATUS-001 |
| OP_REQ_TX_001 | observable write response satisfies requirement: REQ-TX-001 |
| OP_REQ_TX_FULL_001 | observable stream response satisfies requirement: REQ-TX-FULL-001 |

## 8. Acceptance Criteria
| Criteria | Evidence |
| --- | --- |
| AC-SPI-001 | SPI write/read transactions complete only on byte boundaries while CS is active low, and partial transfers are discarded. |
| AC-RST-001 | Top RTL exposes MR and has no hard_reset, soft_reset, or sw_reset top-level input; opcode 0x04 clears architectural state through reset_ctrl. |
| AC-RST-002 | Opcode 0x44 clears TX/RX FIFO counters and priority mailboxes while retaining control register values. |
| AC-FIFO-001 | TX full ignores the 33rd write; RX full accepts the 33rd word by overwriting the 32nd storage location. |
| AC-ARINC-001 | VCD windows show reset release, SPI command activity, TX driver-control response, and receiver FIFO/status response with no X/Z on required top ports except SO high-Z policy modeled as idle zero in FPGA RTL. |
| AC-UVM-001 | UVM scoreboard checks legal label/parity/SDI/FIFO scenarios from a spec reference model, not from DUT behavior. |
| AC-PROTO-001 | Loop3 reports classify IP-level, PS/PL emulation, external pin-level, and full hardware claims under claim_policy. |

## 9. Active Requirement Baseline
| Requirement | Domain | Title / Text | Lifecycle |
| --- | --- | --- | --- |
| ASM-BOUNDARY-001 | unassigned | ASM-BOUNDARY-001 | proposed |
| BASELINE-SEED-001 | unassigned | BASELINE-SEED-001 | proposed |
| REQ-ACLK-001 | unassigned | REQ-ACLK-001 | proposed |
| REQ-ARINC-001 | unassigned | REQ-ARINC-001 | proposed |
| REQ-FIFO-001 | unassigned | REQ-FIFO-001 | proposed |
| REQ-FLAGINT-001 | unassigned | REQ-FLAGINT-001 | proposed |
| REQ-INST-001 | unassigned | REQ-INST-001 | proposed |
| REQ-LABEL-001 | unassigned | REQ-LABEL-001 | proposed |
| REQ-MAILBOX-001 | unassigned | REQ-MAILBOX-001 | proposed |
| REQ-MB-PINS-001 | unassigned | REQ-MB-PINS-001 | proposed |
| REQ-PLABEL-001 | unassigned | REQ-PLABEL-001 | proposed |
| REQ-PROTO-001 | unassigned | REQ-PROTO-001 | proposed |
| REQ-RST-001 | unassigned | REQ-RST-001 | proposed |
| REQ-RST-002 | unassigned | REQ-RST-002 | proposed |
| REQ-RX-001 | unassigned | REQ-RX-001 | proposed |
| REQ-RX-FILTER-001 | unassigned | REQ-RX-FILTER-001 | proposed |
| REQ-SPI-001 | unassigned | REQ-SPI-001 | proposed |
| REQ-SPI-002 | unassigned | REQ-SPI-002 | proposed |
| REQ-STATUS-001 | unassigned | REQ-STATUS-001 | proposed |
| REQ-TX-001 | unassigned | REQ-TX-001 | proposed |
| REQ-TX-FULL-001 | unassigned | REQ-TX-FULL-001 | proposed |

<!-- HDL-APP-DOC END -->
