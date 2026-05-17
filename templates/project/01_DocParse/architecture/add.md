# Architecture Design Document

## RTL Planning Rules

- Architecture planning must consume `01_DocParse/architecture/rtl_planning_rules.yaml` before Loop1 RTL generation.
- Top-level RTL must be hierarchy-only; behavior belongs in owned submodules.
- RTL and directed TB are Verilog-2001 `.v` only; SystemVerilog is reserved for UVM.
- Official bus/protocol/IP signal names must match vendor UG/IP naming; do not append `_i`/`_o` at official boundaries.
- Non-trivial FSMs must plan separate state, next-state, and datapath/control ownership.

## Module Partition

## Data Flow

## State Machines

## Timing Model

## Loop Handoff

- Loop1 consumes module plan and interface contracts.
- Loop2 consumes architecture plus verification plans.
- Loop3 consumes architecture plus prototype plans.
