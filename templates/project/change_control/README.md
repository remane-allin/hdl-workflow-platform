# Change Control

All requirement, design, verification, and prototype changes should start here before they modify deliverables.

- `requests/` records the requested change and reason.
- `impact_analysis/` records affected requirements, RTL, tests, reports, and downstream nodes.
- `approvals/` records review and approval status.
- `trace_updates/` records downstream trace matrix updates after the change is accepted.

Use the CLI rather than hand-writing status fields:

```powershell
python -m hdlflow.cli change-open --project <project> --title "..." --reason "..." --scope "..." --risk low
python -m hdlflow.cli change-impact --project <project> --change-id CR-... --artifact 05_Output/rtl/foo.v --verification "run-gate loop1" --rollback "restore last rollback manifest" --risk low
python -m hdlflow.cli change-approve --project <project> --change-id CR-... --decision approved --approver reviewer --notes "reviewed"
python -m hdlflow.cli run-gate --project <project> --node loop1 --change-id CR-...
python -m hdlflow.cli change-close --project <project> --change-id CR-... --gate-report 05_Output/reports/gates/<report>.md --notes "trace updated"
```
