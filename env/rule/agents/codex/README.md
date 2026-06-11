# HDL Workflow Codex Surface

This directory exposes project-local Codex surfaces for the current HDL workflow
workspace.

- `hooks.json` registers the HDL hooks with relative project paths.
- Skills live in `../skills`; do not duplicate or junction them under `.codex/` for GitHub publication.
- `prompts/` contains prompt fragments for the numbered three-loop layout.
- `agents/` is reserved for project-local agent definitions.

Do not point these files at legacy workspaces.
