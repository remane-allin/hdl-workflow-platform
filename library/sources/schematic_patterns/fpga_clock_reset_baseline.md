# FPGA Clock And Reset Baseline

## Use When

Use during FPGA prototype planning or debug when clock/reset connectivity must be checked before implementation or board validation.

## Checklist

- Confirm every fabric clock has a named source and expected frequency.
- Confirm reset polarity at the FPGA pin and inside RTL.
- Confirm async resets are synchronized before use in synchronous logic.
- Confirm clock constraints exist for each primary and generated clock.
- Record board-level exceptions in Loop3 reports.
