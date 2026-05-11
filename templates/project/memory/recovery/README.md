# Recovery Memory

Use this area for restart and rollback evidence.

- `checkpoints/` records the last completed workflow step.
- `rollback_manifests/` records the files, config versions, hashes, and reports needed to return to a stable version.
- `failure_records/` records abnormal exits and blocked runs.
