# Module Plan

Fill this file before broad RTL implementation begins.

## Required Sections

1. Active top module and wrapper boundary
2. Path partition summary
3. Planned RTL file list
4. System blueprint summary
5. Module contract inventory
6. Module hierarchy and ownership
7. Clock/reset and CDC contract
8. Requirement trace notes linking contracts to requirement IDs
9. Freeze-readiness notes
10. Implementation order
11. Known open questions

## Minimal Template

- project:
- active_top:
- wrapper_only_top: yes/no
- blueprint_status: DRAFT/READY/FROZEN/CLOSED

## Planned Files

- `05_Output/rtl/<top>.v`
- `05_Output/rtl/<submodule>.v`

Use `requirements.json` `rtl_targets` and `contract_hints.modules` as the first
source for this list, even before real RTL files exist.
