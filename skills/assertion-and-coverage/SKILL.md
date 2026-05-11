---
name: assertion-and-coverage
description: Add spec-derived assertions and drive coverage closure after the base HDL loop is stable. Use when the user wants non-invasive SVA, bind files, functional coverage, or targeted coverage-closing tests without corrupting verification intent.
---

# Assertion And Coverage

Use this skill after the project already has a functioning RTL and UVM baseline.

## Scope

This skill owns:

- SVA and bind files under verification code areas
- coverage collector additions
- targeted coverage-closing tests
- coverage triage notes and closure decisions

It does not replace the base simulation loop.

## Assertions

1. Derive properties from normalized specs, protocol rules, reset behavior, and legal state transitions.
2. Prefer non-invasive bind-based assertions.
3. Keep properties readable and tied to spec intent.
4. Record any simulator compatibility concerns before broad rollout.

## Coverage

1. Start only after the RTL/TB functional regression and UVM baseline are stable.
2. Analyze the coverage report before generating new tests.
3. Add covergroups with verification meaning, not bin inflation.
4. Generate targeted tests only when the expected behavior is still being checked.
5. Never lower goals or exclude bins silently.
6. Treat coverage as legal-scenario evidence, not a raw cross-product target.
7. Ignore or document impossible bins before adding stimulus for them.
8. Do not count debug failure bins as closure goals; failures must be caught by scoreboard or assertions.
9. Classify code coverage holes before action: missing legal stimulus, missing checker/model, RTL bug, unreachable by spec, tool/model limitation, or intentional out-of-scope.

## Closure Strategy

For Loop2 UVM closure, use this policy:

- Functional coverage is authoritative only when sampled from complete monitored transactions.
- Cross coverage must be narrow enough that every bin has spec or test-intent meaning.
- Broad crosses such as scenario x opcode x operation-kind are allowed only when the legal bin matrix is explicitly defined.
- Impossible operation/access pairs, reserved behavior, analog/pad scope, and unreachable-by-spec paths are not automatic bug-fix targets.
- Remaining FSM transition and toggle holes become blocking only when tied to a legal requirement, risk item, or approved release gate.
- If a hole is not closed by stimulus, record the decision in the coverage triage note, waiver file, or project memory before claiming closure.

## Rules

- No fake closure by removing checks or gaming stimulus.
- Assertion intent must come from the spec, not from reverse-engineering RTL quirks.
- Human review is required before treating a hole as unreachable.

## References

- Read [references/quality-loop-rules.md](references/quality-loop-rules.md) before making closure claims.
