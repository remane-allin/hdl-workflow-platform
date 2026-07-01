# Loop3 Serial Validation

- port: COM3
- baud: 115200
- TX[20:58:16.705]: read
- RX[20:58:16.821]: read data=0x00000180
- suite: PASS
- result: PASS

## Captured Lines
```text
TX[20:58:16.705]: read
RX[20:58:16.714]: read data=0x00000180
TX[20:58:16.715]: suite
RX[20:58:16.722]: LOOP3_SUITE_BEGIN total_checks=14
RX[20:58:16.725]: LOOP3_CHECK id_readback PASS value=0x48335933
RX[20:58:16.730]: LOOP3_CHECK control_release PASS value=0x00000102
RX[20:58:16.732]: LOOP3_CHECK status_read PASS value=0x00000018
RX[20:58:16.738]: LOOP3_CHECK tx_sample_read PASS value=0x00000180
RX[20:58:16.744]: LOOP3_CHECK rx_drive_register_loopback PASS value=0x00003D8F
RX[20:58:16.746]: OPCODE[08] write_tx_control PASS value=0x000003D0
RX[20:58:16.752]: OPCODE[0C] write_tx_fifo PASS value=0x000003E0
RX[20:58:16.755]: OPCODE[40] tx_start PASS value=0x00003C40
RX[20:58:16.760]: LOOP3_CHECK tx_boundary_sampler_decode PASS value=0x00003C40
RX[20:58:16.766]: OPCODE[44] fifo_mailbox_reset PASS value=0x00000010
RX[20:58:16.769]: OPCODE[10] write_rx1_control PASS value=0x00000010
RX[20:58:16.775]: LOOP3_CHECK rx_symbol_injection_readback PASS value=0x00000150
RX[20:58:16.780]: LOOP3_CHECK ps_ddr_test_window PASS value=0x3593005A
RX[20:58:16.783]: OPCODE[04] master_reset PASS value=0x00000018
RX[20:58:16.792]: LOOP3_CHECK analog_boundary DEFERRED reason=external_HI8592_HI8450_instruments_not_installed
RX[20:58:16.797]: LOOP3_SUITE PASS passed=0E failed=00 deferred=01
LOOP3_RESULT PASS
```
