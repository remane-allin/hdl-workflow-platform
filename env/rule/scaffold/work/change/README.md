# Change Control

All requirement, design, verification, and prototype changes must start here
before they modify deliverables after a gate baseline exists.

- `requests/` records the requested change and reason.
- `impact_analysis/` records affected requirements, RTL, tests, reports,
  downstream nodes, required verification, rollback, and design-document
  decision.
- `approvals/` records review and approval status.
- `trace_updates/` records downstream trace matrix updates after the change is accepted.

Use the CLI rather than hand-writing status fields:

```powershell
python -m hdlflow.cli change-open --project <project> --title "..." --reason "..." --scope "..." --risk low
python -m hdlflow.cli change-impact --project <project> --change-id CR-... --artifact output/rtl/foo.v --verification "run-gate loop1" --rollback "restore last rollback manifest" --risk low
python -m hdlflow.cli change-approve --project <project> --change-id CR-... --decision approved --approver reviewer --notes "reviewed"
python -m hdlflow.cli requirements-frontdoor-check --project <project>
python -m hdlflow.cli generate-design-doc --project <project>
python -m hdlflow.cli run-gate --project <project> --node loop1 --change-id CR-...
python -m hdlflow.cli change-close --project <project> --change-id CR-... --gate-report output/reports/gates/<report>.md --notes "trace updated"
```

`change-impact` infers downstream nodes, required verification, and
design-document sections from `--artifact` paths. Approval fails until the
impact record lists non-placeholder requirements, artifacts, downstream nodes,
verification, rollback, and the design-document decision.
