# Project Memory

Project memory is the recovery and audit surface for a local HDL project.

- `index.yaml` links each iteration to its node, reports, snapshots, deliverables, and gate result.
- `active_versions.md` lists signed or currently valid memory records.
- `archive/` stores permanent memory that should be reviewed and committed in a project repository.
- `transient/` stores local notes, session cache, and temporary debug memory. Keep it out of Git.
- `recovery/` stores checkpoints, rollback manifests, and failure records.
- Node directories keep node-local memory, iteration lists, archived records, and transient notes.

Do not use chat history as the source of truth. Persist decisions here.

## Write Rule

`memory/index.yaml` is the canonical machine-readable iteration index. Do not
edit only one memory view by hand.

Use the workflow CLI to write a closed iteration:

```powershell
python -m hdlflow.cli memory-record --project <project> --iteration-id <id> --node 04_Loop3_FPGA_Prototype --gate-level process --gate-result PASS --memory-record memory/00_global/DECISIONS.md --report 05_Output/reports/loop3/preflight/prototype_plan_check.md --notes "short note"
```

Then validate synchronization:

```powershell
python -m hdlflow.cli memory-check --project <project>
```

The record command updates:

- `memory/index.yaml`
- the node-local `iterations.md`
- `memory/active_versions.md` for passing/complete gates
- `memory/00_global/CURRENT_STATE.md` only when explicit summary fields are provided

Automated workflow commands record their own successful micro-steps without
overwriting `CURRENT_STATE.md`. Use explicit summary fields only for a real
stage handoff or user-visible checkpoint.
