# Loop Iteration Prompt

Use this prompt when resuming an HDL project through the outer loop.

1. Read `loop/loop_state.json`
2. Read `loop/task_board.json`
3. Read `loop/feature_backlog.json`, `loop/bug_backlog.json`, and `loop/scorecard.json`
4. Read `memory/00_global/CURRENT_STATE.md` and `memory/00_global/NEXT_STEPS.md`
5. Read the newest relevant report or log
6. Pick the smallest ready task
7. Either execute an automatable action or make one manual code change set
8. Update the loop state before stopping

Stop conditions:

- the chosen task is done
- the chosen task is blocked and needs escalation
- the loop hit the stagnation limit
- the loop hit the per-run iteration limit
