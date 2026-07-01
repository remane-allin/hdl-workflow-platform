# work/docparse/review

Review Agent records only defects, risks, assumptions, process violations, and
Arbtr handoff evidence.

`role_findings.yaml` is the machine-readable defect list. Each finding must
include:

- `id`
- `severity`
- `status`
- `category`
- `owner`
- `artifact`
- `issue`
- `impact`
- `evidence`
- `recommendation`
- `route_to`

Open `critical` and `high` findings block develop gates. Open `medium`
findings also block release gates. Close a finding only when the owning agent
has fixed the routed artifact and Review verifies the evidence.
`fixed` is not a closed status: it records the owner's claim that the routed
artifact changed. The checker treats `open`, `routed`, and `fixed` as unclosed;
use only `verified`, `closed`, or `waived` after Review evidence is complete.

```powershell
python -m hdlflow.cli review-check --project <project> --level develop
```
