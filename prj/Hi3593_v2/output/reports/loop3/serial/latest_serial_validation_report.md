# Loop3 Serial Validation

- port: COM3
- baud: 115200
- TX[15:41:31.387]: read
- RX[15:41:31.531]: read data=0x00000180
- suite: PASS
- result: PASS

## Captured Lines
```text
TX[15:41:31.387]: read
RX[15:41:31.417]: read data=0x00000180
TX[15:41:31.418]: suite
RX[15:41:31.425]: LOOP3_SUITE_BEGIN total_checks=14
RX[15:41:31.428]: LOOP3_CHECK id_readback PASS value=0x48335933
RX[15:41:31.434]: LOOP3_CHECK control_release PASS value=0x00000102
RX[15:41:31.436]: LOOP3_CHECK status_read PASS value=0x00000018
RX[15:41:31.441]: LOOP3_CHECK tx_sample_read PASS value=0x00000180
RX[15:41:31.447]: LOOP3_CHECK rx_drive_register_loopback PASS value=0x00003D8F
RX[15:41:31.449]: OPCODE[08] write_tx_control PASS value=0x000003D0
RX[15:41:31.456]: OPCODE[0C] write_tx_fifo PASS value=0x000003C0
RX[15:41:31.458]: OPCODE[40] tx_start PASS value=0x00003D40
RX[15:41:31.464]: LOOP3_CHECK tx_boundary_sampler_decode PASS value=0x00003D40
RX[15:41:31.469]: OPCODE[44] fifo_mailbox_reset PASS value=0x00000010
RX[15:41:31.472]: OPCODE[10] write_rx1_control PASS value=0x00000010
RX[15:41:31.478]: LOOP3_CHECK rx_symbol_injection_readback PASS value=0x00000150
RX[15:41:31.483]: LOOP3_CHECK ps_ddr_test_window PASS value=0x3593005A
RX[15:41:31.486]: OPCODE[04] master_reset PASS value=0x00000018
RX[15:41:31.495]: LOOP3_CHECK analog_boundary DEFERRED reason=external_HI8592_HI8450_instruments_not_installed
RX[15:41:31.499]: LOOP3_SUITE PASS passed=0E failed=00 deferred=01
LOOP3_RESULT PASS
```
