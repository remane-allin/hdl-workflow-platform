# Module Plan Template

Use this structure when summarizing the RTL plan:

## Scope

- design name
- top module
- primary protocols

## Module Hierarchy

- top
- register/control blocks
- datapath blocks
- adapters or bridges

## Ownership

- clock/reset owner
- register owner
- external interface owner

## Risks

- unresolved timing
- unresolved reset behavior
- spec ambiguity

## Implementation Order

1. leaves and shared packages
2. control and register blocks
3. datapath
4. top integration
