# Loop1 RX Decode Gap Audit

- recorded_at: 2026-06-24
- project: Hi3593
- scope: Loop1 RTL/TB and gate evidence
- status: OPEN_GAP

## Finding

`arinc429_rx.v` does not implement the documented ARINC RX bit-level decode intent. The current RTL uses event-level RX word injection for deterministic prototype evidence:

```text
RIN1A_DIG/RIN1B_DIG event -> rx_word_valid -> {24'hA5_0001, rx1_control_fields}
```

This is not equivalent to:

```text
RIN1A/RIN1B dual-line symbols -> ONE/ZERO/NULL/invalid decode -> bit-cell timing -> 32-bit ARINC word assembly -> RFLIP/parity handling
```

## Evidence

- `output/rtl/arinc429_rx.v` states: `Loop1 uses event-level RX word injection for deterministic status evidence.`
- `output/rtl/arinc429_rx.v` assigns `rx_word_data <= {24'hA5_0001, rx1_control_fields};` for RX1 events and `{24'h5A_0002, rx2_control_fields};` for RX2 events.
- `output/docs/design/microarchitecture_spec.md` documents the intended `arinc429_rx` responsibility as receive symbol decode, bit-cell timing, 32-bit word assembly, RFLIP label order, and parity marking.
- `output/docs/test/verification_plan.md` documents RX scoreboard intent for NULL, ONE, ZERO, invalid states, RX word assembly, RFLIP, parity, and accepted word readback.
- `output/reports/gates/work_loop1_rtl_tb_develop_20260623223827.md` passed because it checked deterministic Loop1 prototype transactions and advisory waveform evidence, not semantic implementation of the documented RX decode FSM.

## Impact

The latest Loop1 PASS proves the prototype path:

```text
RX input event -> generated prototype word -> RX FIFO -> SPI SO readback
```

It does not prove:

```text
HI-8450 RIN1A/RIN1B timing -> true ARINC 429 32-bit word decode
```

## Required Follow-Up

- Refresh design/change records to distinguish prototype event injection from deliverable RX decode.
- Implement or explicitly waive `arinc429_rx` bit-level symbol decode, bit-cell timer, 32-bit word assembly, RFLIP, and parity marking.
- Add Loop1/TB/VCD checks that reconstruct expected ARINC words from `RIN1A_DIG/RIN1B_DIG`.
- Tighten gate/review criteria so a documented RX decode responsibility cannot pass on event-level injection evidence alone.
