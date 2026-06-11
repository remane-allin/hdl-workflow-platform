# HDL Workflow Hooks

These hooks are scoped to the current HDL workflow layout.

They use:

- `config/` for workspace and project configuration
- `prj/<project_name>/work/memory/` for project memory
- `prj/<project_name>/output/` for canonical editable deliverables
- `.omx/` only as runtime summary state

They do not use the old platform contract.

## Requirements Front Door Guard

`Invoke-HdlPreToolGuard.ps1` blocks write-like commands that touch formal
implementation artifact roots before DocParse/front-door evidence exists for
the active project. Guarded roots include:

- `output/rtl`
- `output/tb`
- `output/uvm`
- `work/loop3_fpga_proto`
- `output/fpga`

Allowed preparation work remains under `input` and `work/docparse`, including
`requirements-frontdoor-init`, `requirements-frontdoor-check`, and the
Spec/DocParse gates.

After a loop gate baseline exists, requirement-impacting source edits in that
loop are blocked until the project has a complete approved change request,
impact analysis that records changed requirements/artifacts/verification, a
fresh requirements front-door check, and a regenerated design document. Loop1
guards RTL/TB source edits; Loop2 guards UVM source edits; Loop3 guards
prototype and FPGA source edits.

When `HDLFLOW_AGENT_ROLE` is set, the same hook also enforces six-agent write
isolation. Spec, Arch, Exec, Sim, Review, and Arbtr may write only their
configured roots; Review writes defects and risks only, while Arbtr writes
memory, loop state, gate reports, and freeze reports only.
