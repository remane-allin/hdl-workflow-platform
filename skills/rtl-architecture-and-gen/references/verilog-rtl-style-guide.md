# Verilog RTL Style Guide

Source:
- Project Verilog coding-standard references under `docs/` or the local project document area
- User RTL coding rules updated on 2026-04-30
- Existing project policy and Huawei-style RTL review practice

Authority:
- Project config and user requirements override this guide.
- Spec, register map, timing rules, and interface contract override existing RTL behavior.
- Official bus/protocol/IP naming from vendor UG, protocol specifications, or generated IP is authoritative. Preserve those names exactly at the official boundary; do not append `_i` / `_o` or other local direction suffixes to official protocol signal names.
- Local project aliases may use direction suffixes only for non-official, module-private, or adapter-side signals when they do not obscure official naming.

Purpose:
- This guide is structured for loop use.
- `Hard Rules` are stop-conditions: do not treat RTL as complete if any hard rule is violated.
- `Recommended Style` captures the default project preference when multiple legal implementations exist.
- `Review Checklist` is the compact close-out list to run before claiming RTL completion.

## Hard Rules

### File And Module

- A project must have exactly one project top module.
- The project top module must be hierarchy-only: it may declare ports, parameters, and interconnect wires, and may instantiate submodules, but it must not contain behavioral logic such as `always`, `initial`, continuous `assign`, functions, tasks, local datapath/control mutation, or protocol decisions.
- Use one primary module per file.
- Match file name and module name.
- Use Verilog-2001 ANSI-style declarations for synthesizable modules.
- Do not use Verilog-1995 style port-name-only headers followed by repeated redeclarations in the module body.
- Do not use `include` to connect or concatenate RTL modules.

### Naming And Declarations

- Declare every port direction and width explicitly.
- Declare all internal nets and variables explicitly; do not rely on implicit wires.
- Keep vector ranges in `MSB:LSB` order.
- Do not drive input ports internally.
- Do not leave unused or undriven signals in checked-in RTL.
- Use named port connections for every instance. Do not use positional instance connections.
- Use `_n` only for active-low signals.
- For official bus/protocol/IP interfaces, preserve the documented signal names exactly at the boundary. Do not add `_i` / `_o`, change case, abbreviate, or translate them.
- If a local module needs internal direction-qualified names, place the rename in a wrapper or adapter and document the one-to-one mapping to the official UG/IP name.

### Sequential Logic

- Assign each register in exactly one sequential process.
- Use nonblocking assignments (`<=`) in sequential logic.
- Do not mix blocking and nonblocking assignments in the same sequential process.
- Do not use blocking assignments for flops, state registers, counters, valid bits, pulse outputs, or stored datapath values.
- A sequential sensitivity list should contain only the owning clock edge and approved asynchronous reset edges for that domain.
- A sequential sensitivity list may contain at most one asynchronous reset or set edge, typically the global system reset for that domain.
- Do not model business control such as `cs_n`, opcode events, or local transaction aborts as additional asynchronous reset or set conditions. Handle them synchronously inside the owning clocked process.
- Do not use business pulses, valids, enables, toggles, or decoded command events as pseudo-clocks.
- Do not mix edge-triggered items with level-sensitive items in one clocked sensitivity list.
- Use one clock edge convention per module. Do not use both edges for ordinary RTL.
- Do not let one register be assigned from multiple sequential `always` blocks, from different clock edges, or from different pseudo-event sources.
- Reset all control registers, FSM states, valids, enables, and counters unless valid/control logic makes an unreset datapath register safe by construction.
- If asynchronous reset is used, keep the reset branch in standard `if (rst) ... else ...` form.
- Do not gate or qualify the top-level reset branch with extra data/control conditions.
- Every `if` / `else if` decision chain must close with an explicit final `else` branch.
- The `else` keyword must start on its own line. Do not write `end else begin` or `end else if (...) begin`.

### Combinational Logic

- Use blocking assignments (`=`) in combinational logic.
- Use `always @(*)` for Verilog-2001 combinational processes.
- Give default assignments at the top of combinational processes.
- Cover every `if` branch and every `case` branch.
- Every `if` / `else if` decision chain must close with an explicit final `else` branch.
- Every `case` must have a `default`.
- Do not infer latches unless the latch is intentional, documented, and reviewed.

### FSM And Structure

- Keep combinational and sequential logic in separate processes.
- Use a three-process FSM structure for all FSMs unless a written project waiver says otherwise.
- Do not hide non-trivial FSM state transition, next-state decode, and outputs inside one monolithic `always` block.
- Encode FSM states with `localparam` in this Verilog-2001 project code.
- Provide illegal-state recovery through `default`.
- Keep control path and datapath physically decoupled in non-trivial protocol logic.
- Do not perform concrete datapath mutation inside FSM branches when the same behavior can be expressed through explicit enables in datapath-owned logic.

### Clock, Reset, And CDC

- Do not create clocks with ordinary combinational RTL.
- Do not gate clocks with expressions such as `assign gated_clk = clk & en`.
- Do not gate reset with combinational logic.
- Do not treat SPI byte-valid pulses, FIFO pop pulses, mailbox clear pulses, capture pulses, software reset pulses, or similar architectural events as substitute clocks.
- Synchronize every asynchronous single-bit input before use.
- Do not synchronize multi-bit buses with independent 2FF synchronizers.
- Use handshake, Gray-coded pointers, or async FIFO for multi-bit CDC.
- Use toggle, stretched pulse, or handshake synchronizers for pulse CDC.
- Do not mix clock domains in one `always` block.
- When a reset or clear request originates in another domain, synchronize it or transfer it through a CDC-safe request mechanism before consumption.

### Synthesis Safety

- Keep synthesizable RTL free of `initial`, `#delay`, `force`, `release`, `wait`, `fork/join`, dynamic arrays, `real`, and `shortreal`.
- Keep testbench-only code out of design RTL.
- Use explicit constant widths in arithmetic, compare, concat, and shift expressions.
- Avoid combinational loops.
- Avoid unexplained magic numbers for protocol constants, state encodings, widths, or fixed bounds.
- Use `localparam` for module-internal constants such as states, opcodes, local addresses, and fixed limits.

### Function And Task

- Use ANSI-style Verilog-2001 declarations for `function` and `task` arguments.
- A synthesizable `function` must remain purely combinational and use blocking assignments only.
- Do not place edge-sensitive behavior, nonblocking assignments, or hidden state updates inside a synthesizable `task`.
- Do not call a state-updating `task` from synthesizable clocked RTL.

## Recommended Style

### File And Naming

- Use lowercase module and file names with underscores for new RTL.
- Keep header comments short: module, file, author, date, description, scope, notes, revision.
- Use meaningful names that describe hardware intent.
- Use `clk` or `<domain>_clk` for clocks.
- Use `rst_n` or `<domain>_rst_n` for active-low resets.
- Use uppercase for parameters, localparams, and compile-time constants.
- Use `state_cur` / `state_nxt` or a consistent project equivalent for FSM state.
- Use `_q` or `_r` for flopped values when it improves clarity.
- Use `_d`, `_nxt`, or `_comb` for next-state or combinational values when it improves clarity.
- Keep the same signal meaning under the same name across hierarchy whenever practical.
- Avoid vague names such as `tmp`, `flag1`, `data2`, and `ctrl`.

### Ports And Instances

- Declare one port per line for non-trivial modules.
- Keep instance connection expressions simple; create named wires for non-trivial glue logic.
- For standard bus/IP ports, prefer official interface names over local style suffixes; wrapper aliases must be one-to-one documented.
- Keep function and task definitions local unless they are reviewed shared utilities.

### Structure And Ownership

- Keep top-level modules focused on integration and interconnect.
- Keep strongly related combinational logic in the same module unless there is a clear boundary reason.
- Separate logic with different timing, clocking, reset, DFT, or synthesis goals.
- Put clock generation, reset synchronization, CDC synchronization, and memory wrappers in explicit modules.
- Keep one clock domain per ordinary module.
- If a module must cross clock domains, isolate and document the CDC boundary.
- Register module outputs by default. Allow combinational outputs only when low-latency intent is explicit and reviewed.
- Avoid unnecessary empty hierarchy.
- Avoid large mixed-purpose modules; split by ownership, clock domain, datapath/control, or verification boundary.

### Sequential And Combinational Style

- Prefer smaller ownership-clean processes over one big process that mixes state, control, storage updates, and mux decode.
- Inside one sequential or combinational process, collapse one decision family into one readable `if / else if / else` chain.
- Format every decision chain with `else` on a standalone line:
  ```verilog
  if (condition_a) begin
      ...
  end
  else if (condition_b) begin
      ...
  end
  else begin
      ...
  end
  ```
- Use `case` for selector, opcode, slot, state, and mux decode when the choices are mutually exclusive.
- Use `if / else` for single-bit priority controls such as `enable`, `valid`, and `pulse`.
- For large combinational decision trees, refine behavior from safe defaults at the top of the block.
- Avoid `casex`; use `casez` only for intentional wildcard matching.
- Avoid continuous `assign` for complex combinational behavior; prefer a named combinational process.

### FSM Style

- Require the standard three-process FSM structure for FSMs:
  - one sequential process for current state
  - one combinational process for next-state decode
  - one combinational or sequential process for outputs/datapath control
- Use `state_cur` / `state_nxt` or a project-approved equivalent for FSM state registers.
- Treat the FSM as a scheduler whose outputs are control intents such as enables, load strobes, selectors, and transaction qualifiers.
- Document non-obvious transition priority and terminal conditions.
- If two states differ only by channel or resource selection while timing behavior is identical, merge them and track the selection with explicit selectors or control registers.
- Prefer a shared transaction state plus selectors over duplicated per-channel state trees.
- For transaction aborts such as `cs_n` deassertion, prefer a clean high-priority clear or abort path rather than deep scattered overrides.

### Reset, CDC, And Timing Hygiene

- Prefer clock-enable logic for ordinary register enables.
- Keep datapath registers in dedicated sequential processes when the datapath can be described as an enable-controlled resource outside the FSM state register block.
- A datapath process should respond to enables such as `cnt_en`, `load_en`, `shift_en`, `fifo_pop_en`, or `sel_ld_en` rather than hard-coding direct state-name inspection where practical.
- For slow-to-fast or peer asynchronous single-bit CDC, use a 2-stage synchronizer by default and 3 stages when reliability margin justifies it.
- Document every CDC assumption and every reset-domain crossing.

### Comments

- Comment design intent, timing assumptions, CDC/reset policy, protocol mapping, and exceptions.
- Do not comment obvious syntax.
- Mark intentional latch, intentional combinational output, intentional no-reset flop, and intentional don't-care.
- Keep comments short and close to the logic they explain.
- Keep stale revision history and tool boilerplate out of RTL.

## Review Checklist

Use this checklist before claiming RTL completion in loop work:

- File name matches module name.
- One primary module exists per file.
- Exactly one project top module is selected.
- The project top module is hierarchy-only and contains no behavioral logic.
- Module ports use Verilog-2001 ANSI-style declaration.
- Ports and internal signals are explicit.
- Official bus/protocol/IP port names match the referenced UG/IP naming and do not have added `_i` / `_o` suffixes.
- No implicit wires remain.
- Named port connections are used consistently.
- Each register has exactly one sequential owner.
- No business event signal appears in a sequential sensitivity list as a pseudo-clock.
- Combinational and sequential logic are separated.
- Sequential logic uses `<=`.
- Combinational logic uses `=`.
- Every `if` / `else if` decision chain has a final `else`.
- Every `else` keyword starts on its own line.
- Every `case` has `default`.
- Large combinational blocks assign safe defaults up front.
- FSM states use `localparam`.
- FSM uses the required three-process structure.
- FSM has illegal-state recovery.
- FSM outputs are primarily control intents, not mixed-in datapath mutation.
- Datapath registers are updated in dedicated enable-controlled processes when practical.
- Equivalent per-channel or per-resource states are merged when timing behavior is the same.
- Transaction-abort conditions are handled with clear high-priority logic rather than scattered deep overrides.
- No accidental latch exists.
- No internal combinational clock gate exists.
- No unreviewed generated clock exists.
- Reset composition is explicit and domain-safe.
- Async single-bit inputs are synchronized before use.
- Cross-domain pulses use approved synchronizer or handshake structures.
- Multi-bit CDC uses handshake, Gray code, or async FIFO.
- Constants have explicit widths.
- No unexplained magic numbers remain for protocol or control constants.
- Synthesizable reusable logic uses `function` rather than state-updating `task`.
- No synthesis-forbidden constructs remain.
- Module outputs are registered, or the exception is documented.
- Timing, reset, CDC, and DFT exceptions are documented.
