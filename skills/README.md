# Shared Skills

This directory stores the HDL workflow skills used by the new `Test/` workspace.

The active set is local to `Test` and has been rewritten for the new layout:

- `config/projects/<project_name>/project_config.yaml`
- `00_SPEC/`
- `01_DocParse/`
- `02_Loop1_RTL_TB/`
- `03_Loop2_UVM_Verify/`
- `05_Output/`
- `memory/`

Codex surfaces should reference this directory directly from `Test/`. Do not create `.codex/skills` junctions for publication.

Project instances should record which skill versions were used in project memory instead of copying mutable skill implementations into each project.

The `00_SPEC -> 01_DocParse` handoff is now a five-role front-door workflow:
Coordinator, PM, Architect, Verification Planner, and Prototype Planner. Their
outputs are stored as YAML/Markdown artifacts and checked by
`requirements-frontdoor-check` before downstream loops consume them.
