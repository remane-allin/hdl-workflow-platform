# Decomposition Patterns

Use these patterns when converting a spec into structured requirements.

## Recommended Hierarchy

Prefer:

`Epic -> Feature -> Task -> Acceptance Check`

## Common Epic Sources

- protocol interface groups
- register or CSR families
- datapath stages
- control FSM domains
- reset, clocking, or integration sections

## Common Feature Sources

- one bus or protocol slice
- one register bank
- one functional mode
- one verification scenario family

## Common Task Shapes

- implement a bounded RTL block
- add a bounded focused baseline TB capability
- add a UVM agent or checker slice
- verify one acceptance condition
- resolve one document ambiguity

## Good Task Properties

- one owner layer
- explicit completion condition
- concrete dependency list
- small enough for one iteration
- linked to at least one requirement

## Bad Task Smells

- "implement the whole protocol"
- "finish all verification"
- "fix everything found in sim"
- tasks with no file, block, or acceptance target
