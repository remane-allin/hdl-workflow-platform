# Session Bootstrap Prompt

Before starting work on an HDL project, read these files in order:

1. `work/memory/00_global/PROJECT_BRIEF.md`
2. `work/memory/00_global/CURRENT_STATE.md`
3. `work/memory/00_global/ACTIVE_PLAN.md`
4. `work/memory/00_global/PLAN_FINDINGS.md`
5. `work/memory/00_global/PLAN_ERRORS.md`
6. `work/memory/00_global/OPEN_QUESTIONS.md`
7. latest change records under `work/change/`
8. `work/docparse/structured_spec/*.yaml`
9. latest files under `output/reports/` and `work/loop1_rtl_tb/_runtime/logs/ or work/loop2_uvm/_runtime/logs/`

Then answer three questions for yourself:

1. What is the current project goal?
2. What is the current blocker?
3. What is the smallest next executable step?

Do not reread the full raw document unless the normalized spec is missing or inconsistent.

Run `python -m hdlflow.cli ralph-status --project <project>` when the next
action is unclear after reading these files.
