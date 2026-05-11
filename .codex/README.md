# Test Codex Surface

This directory exposes project-local Codex surfaces for the `Test/` HDL workspace.

- `hooks.json` registers the Test-specific HDL hooks with relative project paths.
- Skills live in `../skills`; do not duplicate or junction them under `.codex/` for GitHub publication.
- `prompts/` contains prompt fragments rewritten for the `Test` layout.
- `agents/` is reserved for project-local agent definitions.

Do not point these files at legacy workspaces.
