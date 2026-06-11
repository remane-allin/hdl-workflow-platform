# Project Memory

Project memory is the recovery and audit surface for a local HDL project.

- `index.yaml` links each iteration to its node, reports, snapshots, deliverables, and gate result.
- `00_global/ACTIVE_PLAN.md` is the live execution plan. Read it before choosing the next action and update it after each step starts, completes, or blocks.
- `00_global/PLAN_FINDINGS.md` stores durable analysis findings that must survive context compaction.
- `00_global/PLAN_ERRORS.md` stores failed attempts, blockers, and changed approaches so they are not repeated after context compaction.
- `active_versions.md` lists signed or currently valid memory records.
- `archive/` stores permanent memory that should be reviewed and committed in a project repository.
- `transient/` stores local notes, session cache, and temporary debug memory. Keep it out of Git.
- `recovery/` stores checkpoints, rollback manifests, and failure records.
- Node directories keep node-local memory, iteration lists, archived records, and transient notes.

Do not use chat history as the source of truth. Persist decisions here.

## Write Rule

`work/memory/index.yaml` is the canonical machine-readable iteration index. Do not
edit only one memory view by hand.

Use the workflow CLI to write a closed iteration:

```powershell
python -m hdlflow.cli memory-record --project <project> --iteration-id <id> --node work/loop3_fpga_proto --gate-level process --gate-result PASS --memory-record work/memory/00_global/DECISIONS.md --report output/reports/loop3/preflight/prototype_plan_check.md --notes "short note"
```

Then validate synchronization:

```powershell
python -m hdlflow.cli memory-check --project <project>
```

The record command updates:

- `work/memory/index.yaml`
- the node-local `iterations.md`
- `work/memory/active_versions.md` for passing/complete gates
- `work/memory/00_global/CURRENT_STATE.md` only when explicit summary fields are provided

Automated workflow commands record their own successful micro-steps without
overwriting `CURRENT_STATE.md`. Use explicit summary fields only for a real
stage handoff or user-visible checkpoint.

## Planning With Files

For any multi-step task, use the file-backed plan instead of chat context:

```powershell
python -m hdlflow.cli plan-start --project <project> --title "short title" --objective "target result" --step "inspect current state" --step "make scoped change" --step "verify"
python -m hdlflow.cli plan-step --project <project> --step-id P001 --status in_progress --note "reading current artifacts"
python -m hdlflow.cli plan-note --project <project> --kind finding --note "important fact" --source work/docparse/structured_spec/register_map.yaml
python -m hdlflow.cli plan-step --project <project> --step-id P001 --status done --evidence "file references reviewed"
```

Use `plan-note --kind error` whenever a command fails or an approach is
abandoned. The next agent must read `ACTIVE_PLAN.md`, `PLAN_FINDINGS.md`, and
`PLAN_ERRORS.md` before continuing.

## Ralph Loop

Use the Ralph commands to recover the next action from files instead of chat
context:

```powershell
python -m hdlflow.cli ralph-status --project <project>
python -m hdlflow.cli ralph-step --project <project> --status in_progress --note "starting next step"
python -m hdlflow.cli ralph-step --project <project> --status blocked --note "gate failed" --evidence output/reports/gates/<report>.md
python -m hdlflow.cli ralph-check --project <project>
```

`ralph-status` reads active plan, memory, gate state, and change-control
records, plus structured Review Agent blockers from
`work/docparse/review/role_findings.yaml`. Open changes and open review
blockers take priority over ordinary loop work. `ralph-check` passes only when
the active plan is closed, memory is synchronized, no gate is failed, no review
blocker is open, and no change request is still open, impact-ready, or
approved-but-not-closed.
