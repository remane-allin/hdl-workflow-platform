# Loop Iteration Prompt

Use this prompt when resuming an HDL project through the outer loop.

1. Read `work/gates/loop_state.json`
2. Read `work/gates/task_board.json`
3. Read `work/gates/feature_backlog.json`, `work/gates/bug_backlog.json`, and `work/gates/scorecard.json`
4. Read `work/memory/00_global/ACTIVE_PLAN.md`, `PLAN_FINDINGS.md`,
   `PLAN_ERRORS.md`, and `CURRENT_STATE.md`
5. Read open or approved records under `work/change/`
6. Run `python -m hdlflow.cli ralph-status --project <project>`
7. Read the newest relevant report or log
8. Pick the smallest ready task
9. If the task changes requirements, open/impact/approve the change before editing
10. Either execute an automatable action or make one manual code change set
11. Update the Ralph plan step and loop state before stopping

Stop conditions:

- the chosen task is done
- the chosen task is blocked and needs escalation
- `ralph-check` passes for the current file-backed iteration
- the loop hit the stagnation limit
- the loop hit the per-run iteration limit
