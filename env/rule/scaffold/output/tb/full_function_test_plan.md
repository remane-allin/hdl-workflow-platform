# Directed TB Full Function Test Plan

- owner: Loop1 directed TB
- source_root: `output/tb`
- report_script: `python -m hdlflow.cli loop1-refresh-reports --project <project>`
- waveform_script: `python -m hdlflow.cli loop1-waveform-check --project <project>`
- log_source: `output/reports/loop1/modelsim_loop1.log`
- report_output: `output/reports/loop1/loop1_rtl_tb_run_report.md`
- waveform_output: `output/reports/loop1/waveform_check.json`
- waveform_hierarchy: `output/reports/loop1/waveform_hierarchy.json`
- waveform_files: `output/sim/loop1/wave/*.wlf`, `output/sim/loop1/wave/*.vcd`

## Required Coverage

| Test Set | Stimulus Plan | Expected Result | Log Evidence |
| --- | --- | --- | --- |
| Baseline entry checks | Reset, idle, and minimum legal transaction checks | Zero runtime errors and deterministic PASS markers | `HDLFLOW_TEST_CASE` |
| Full function matrix | One directed case per required function, opcode, register field, and boundary condition | Every item has expected/actual comparison and PASS/FAIL result | `HDLFLOW_TEST_CASE` |
| Boundary checks | Empty/full/half-full, reset, overwrite, partial transfer, and documented edge conditions | Boundary behavior matches spec and docset | `HDLFLOW_TEST_CASE` |
| Waveform windows | Mark the time span around each meaningful function check after score comparison passes | Top-level VCD has clock activity, no X/Z, and non-clock activity in every marked span | `HDLFLOW_WAVE_BEGIN` / `HDLFLOW_WAVE_END` |

Waveform analysis reads the WLF/VCD files in `output/sim/loop1/wave/` in place.
Do not create a second VCD/WLF copy for AI-side analysis.
Use `waveform_hierarchy.json` to choose the relevant module scope before
requesting detailed signal-level analysis.

## Required Log Marker

Every checked TB item must print:

```text
========== HDLFLOW_TEST_CASE ==========
HDLFLOW_TEST_CASE id=<test_id> stimulus=<what_was_sent> expected=<expected_behavior> actual=<observed_behavior> result=<PASS_or_FAIL> transactions=<count> stimuli=<count>
========== END_HDLFLOW_TEST_CASE ==========
```

Every functionally passing checked item must also mark a waveform window:

```text
HDLFLOW_WAVE_BEGIN id=<test_id> time=<simulation_time>
HDLFLOW_WAVE_END id=<test_id> time=<simulation_time>
```

For a fixed known range, the TB may emit a single-line marker instead:

```text
HDLFLOW_WAVE_WINDOW id=<test_id> start=<simulation_time> end=<simulation_time>
```
