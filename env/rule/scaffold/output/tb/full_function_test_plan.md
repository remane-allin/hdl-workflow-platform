# Directed TB Full Function Test Plan

- owner: Loop1 directed TB
- source_root: `output/tb`
- report_script: `python -m hdlflow.cli loop1-refresh-reports --project <project>`
- waveform_script: `python -m hdlflow.cli loop1-waveform-gate --project <project> --manifest work/loop1_rtl_tb/config/top_wave_manifest.yaml`
- log_source: `work/loop1_rtl_tb/current/log/modelsim.log`
- report_output: `output/reports/loop1/loop1_report.md`
- report_json: `output/reports/loop1/loop1_report.json`
- waveform_manifest: `work/loop1_rtl_tb/config/top_wave_manifest.yaml`
- waveform_query_report: `output/reports/loop1/waveform_query_report.md`
- waveform_gate: `output/reports/loop1/waveform_gate.json`
- query_transcript: `output/reports/loop1/query_transcript.json`
- waveform_files: `output/sim/loop1/wave/*.wlf`, `output/sim/loop1/wave/*.vcd`

## Required Coverage

| Test Set | Stimulus Plan | Expected Result | Log Evidence |
| --- | --- | --- | --- |
| Baseline entry checks | Reset, idle, and minimum legal transaction checks | Zero failed structured checks | `HDLFLOW|CHECK` |
| Full function matrix | One directed case per required function, opcode, register field, and boundary condition | Every item has sent/expected/actual comparison and PASS/FAIL result | `HDLFLOW|CHECK` |
| Boundary checks | Empty/full/half-full, reset, overwrite, partial transfer, and documented edge conditions | Boundary behavior matches spec and docset | `HDLFLOW|CHECK` |
| Waveform windows | Mark the time span around each meaningful function check after score comparison passes | Top-level VCD has clock activity, no X/Z, non-clock activity, and manifest-selected query checks in every marked span | `HDLFLOW_WAVE_BEGIN` / `HDLFLOW_WAVE_END` |

Waveform analysis reads the WLF/VCD files in `output/sim/loop1/wave/` in place.
Do not create a second VCD/WLF copy for waveform analysis.
The controlled top-port query flow uses pywellen as the extractor and a
deterministic signal-rule engine to write `waveform_query_report.md`,
`waveform_gate.json`, and `query_transcript.json`. Waveform rule failures are
structured verification gaps for review; Loop1 pass/fail is decided by the
deterministic hard gate from TB PASS, zero simulator errors, zero fatal markers,
and assertion PASS when assertions are enabled.

## Required Log Events

Every run must emit a begin event, one check event per checked item, and one
summary event:

```text
HDLFLOW|TEST_BEGIN|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=<test_id>|scope=<feature_or_module>
HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=<test_id>|txn_id=<transaction_id>|sent=<what_was_sent>|expected=<expected_rx>|actual=<actual_rx>|latency_cycles=<n>|result=<PASS_or_FAIL>
HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|total_tests=<n>|passed_tests=<n>|failed_tests=<n>|total_checks=<n>|passed_checks=<n>|failed_checks=<n>|result=<PASS_or_FAIL>
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
