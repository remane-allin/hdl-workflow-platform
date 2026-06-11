# Quality Loop Rules

- Assertions must reflect protocol, reset, register, or FSM intent from the spec.
- Prefer bind files over intrusive RTL edits.
- Coverage holes should be classified before new stimulus is generated.
- New coverage tests still need pass or fail checking, not bin chasing.
- Treat dead code or unreachable bins as review items, not automatic exclusions.
