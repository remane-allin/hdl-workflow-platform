# Workflow

`Workflow` is the single Windows/PowerShell 7 entry for deterministic FPGA RTL work in this workspace. It turns one reviewed `input/current/design.json` into gated RTL/TB verification, Vivado Project Mode synthesis/route/release, normalized project reports, and, when enabled, a Vitis PS application build.

Run from the workspace root:

```powershell
python Workflow/workflow.py environment
python Workflow/workflow.py status --project <directory-name>
python Workflow/workflow.py run --project <directory-name> --to <design|rtl|verify|synth|route|release>
python Workflow/workflow.py recover --project <directory-name>
python Workflow/workflow.py clean --project <directory-name>
python Workflow/workflow.py clean
python Workflow/workflow.py publish-assets --project <directory-name> --result <vivado.xsa|vivado.checkpoint|vitis.elf>
python Workflow/workflow.py deliver --project <directory-name> --message <text> [--tag <name>] [--init]
python Workflow/workflow.py archive --project <directory-name> --output <workspace-relative.zip>
python Workflow/workflow.py restore-archive --archive <workspace-relative.zip> --target <isolated-workspace-path>
python Workflow/workflow.py platform-status
python Workflow/workflow.py platform-upgrade --candidate <workspace-relative.json> --project <baseline> --project <baseline>
python Workflow/workflow.py platform-restore --project <baseline> [--project <baseline> ...]
```

Projects are discovered only as direct children of `Workflow/prj`. `status` is read-only. A run advances from the earliest non-PASS stage and stops on the first valid `FAIL` or operational `BLOCKED`. Design authority is `input/current/design.json`; runtime state is `work/state.json`; reports are bounded under `output/report`.

RTL is explicit ordered Verilog-2001. The flow never recursively discovers production sources, silently retries tools, upgrades IP, changes resource/timing conditions, creates project versions, or writes outside the workspace root.

Optional capabilities stay on the same control path. `publish-assets` copies only explicitly selected results from a completed local release into `output/release` and writes its stable manifest. `implementation.reuse_assets` reads only that manifest and its published files during Gate A; it never reads a sibling project's current design, runtime state, or mutable report. Tool stages use transient per-resource leases and leave no dispatch state after success, failure, or interruption. Git delivery commits only approved release files, preserves unrelated staged content, omits runtime/log/cache files, and pushes only with explicit `--push --remote`. Archives omit logs and runtime state, reject undeclared members, and restore only into a new isolated directory. Platform maintenance requires at least two distinct released baselines, qualifies the isolated descriptor before switching, and retains exactly one `platform.previous.json` recovery point.

`clean --project` removes only project-owned transient inputs, staging, tool work, and resolved failure evidence. Root `clean` removes only Workflow-owned session/runtime debris (`Workflow/.omx`, `log`, `work`, and simulator spill files); it never traverses project state or the workspace root.
