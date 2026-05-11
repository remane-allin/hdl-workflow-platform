# Normalized YAML Contract

## interface_spec.yaml

- module_name
- clock_domains
- reset_signals
- ports
- protocol_notes

## register_map.yaml

- registers
- fields
- notes

For each register, prefer:

- name
- offset
- width
- access
- reset
- fields

## timing_rules.yaml

- timing_rules
- latency_rules
- reset_behavior

## test_intent.yaml

- baseline_tests
- corner_cases
- coverage_targets
- scoreboard_rules

If a field is unknown, leave a clear placeholder and log the question in `01_DocParse/req_decompose/`.
