# Shared Skills

This directory stores the HDL workflow skills used by whichever HDL workflow
workspace is currently active.

The active set is workspace-local and has been rewritten for the numbered
three-loop layout:

- `prj/<project_name>/work/config/project_config.yaml`
- `input/`
- `work/docparse/`
- `work/loop1_rtl_tb/`
- `work/loop2_uvm/`
- `output/`
- `work/memory/`

Codex surfaces should reference this directory through the current workspace
root. Do not create `.codex/skills` junctions for publication.

Project instances should record which skill versions were used in project memory instead of copying mutable skill implementations into each project.

`mineru-spec-normalizer` is workspace-local here so external document parsing
follows the same project-relative layout and approved MinerU high-precision API
evidence path no matter which project is active. Chat-only requirements are the
only DocParse exception: capture them under `input/spec/` with
`source_type: chat_request` and bind them from `document_analysis.yaml` with
`parser_output: manual_chat_capture`, non-empty `analysis_units`, and non-empty
`evidence_map`.

The `input -> work/docparse` handoff is now an isolated six-agent workflow:
Spec, Arch, Exec, Sim, Review, and Arbtr. Their outputs are stored as
YAML/Markdown artifacts and checked by `requirements-frontdoor-check` before
Loop1/Loop2/Loop3 consume them as engineering evidence layers.

AI agents must not automatically modify gate rules, guard code, protected gate
policy, gate manifests, or gate reports to make a project pass. Suspected gate
defects are recorded as review or memory findings and handled only through an
explicit platform-maintenance task with regression evidence.
