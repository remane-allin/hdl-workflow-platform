# Vivado `report_timing_summary`

## Use When

- The current flow needs a timing summary after synthesis or implementation.
- Loop3 needs WNS, TNS, failing endpoint, or clock interaction evidence.

## Required State

Open a synthesized or implemented Vivado design before running the command.

## Command

```tcl
report_timing_summary -file reports/timing_summary.rpt
```

## Useful Variants

```tcl
report_timing_summary -delay_type max -report_unconstrained -check_timing_verbose -file reports/timing_summary_max.rpt
report_timing_summary -delay_type min -file reports/timing_summary_min.rpt
```

## Agent Notes

- Prefer post-implementation timing for release evidence.
- If the command or an option is rejected, check the Vivado version and use `get_diagnostic_candidates` with the tool log.
- Record the generated report path in the Loop3 memory index.

## Official Reference

- `xilinx.ug835`
