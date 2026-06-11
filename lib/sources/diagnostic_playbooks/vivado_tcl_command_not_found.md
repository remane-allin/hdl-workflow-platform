# Vivado TCL Command Not Found

## Symptoms

- `invalid command name`
- `unknown option`
- command works in one Vivado version but fails in another

## Likely Causes

- Vivado version mismatch.
- Command is only available after opening the right design state.
- Option spelling differs across versions.
- Script is running in the wrong tool shell.

## Agent Procedure

1. Capture Vivado version.
2. Capture the rejected command and option.
3. Query command details for the intended command ID.
4. Query document index for the matching official UG version.
5. If the design state is missing, open synth or implementation results before retrying.
