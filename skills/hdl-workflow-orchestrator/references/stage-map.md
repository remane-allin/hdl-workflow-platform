# Stage Map

Use this quick map when deciding what to do next.

## Entry

- New project request: create project, fill `PROJECT_BRIEF.md`, confirm `project.yaml`.
- Resume request: read `memory/` first, then inspect the latest report and logs.

## Handoffs

- Requirements changed -> `hdl-requirements-decompose` and requirements front-door review
- Register-heavy CSR space -> `register-spec-and-ral`
- Spec stable but RTL missing or wrong -> `rtl-architecture-and-gen`
- RTL exists but verification scaffold is weak -> `uvm-env-and-test-build`
- Sources exist and evidence is needed -> `modelsim-run-triage-debug`
- Baseline flow is stable and quality goals expand -> `assertion-and-coverage`

## Recovery

- Token loss or new chat: trust `memory/` and `01_DocParse/structured_spec/`, not prior conversation.
- Repeated sim failure with unclear ownership: route through triage before editing code again.
