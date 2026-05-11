# Triage Routing

Use this routing table after each run:

- syntax, missing symbol, compile order, package visibility -> verify sim setup first, then RTL or UVM ownership
- port mismatch, missing connection, top drift -> RTL integration issue
- checker mismatch with plausible DUT behavior -> inspect spec and scoreboard contract
- timeout, deadlock, or handshake stall -> inspect waveform and protocol ownership
- repeated failures after local fixes -> escalate upstream to normalized spec or architecture review

After classification, update `memory/CURRENT_STATE.md` and `NEXT_STEPS.md`.
