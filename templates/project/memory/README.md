# Project Memory

Project memory is the recovery and audit surface for a local HDL project.

- `index.yaml` links each iteration to its node, reports, snapshots, deliverables, and gate result.
- `active_versions.md` lists signed or currently valid memory records.
- `archive/` stores permanent memory that should be reviewed and committed in a project repository.
- `transient/` stores local notes, session cache, and temporary debug memory. Keep it out of Git.
- `recovery/` stores checkpoints, rollback manifests, and failure records.
- Node directories keep node-local memory, iteration lists, archived records, and transient notes.

Do not use chat history as the source of truth. Persist decisions here.
