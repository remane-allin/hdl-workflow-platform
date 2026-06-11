"""Design change-control records and checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .project import require_project_instance


VALID_ID = re.compile(r"^CR-[0-9]{14}-[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class ChangeResult:
    path: Path
    messages: list[str]


@dataclass(frozen=True)
class ChangeCheckResult:
    ok: bool
    report_path: Path
    messages: list[str]


@dataclass(frozen=True)
class ChangeAssessment:
    requirements: list[str]
    artifacts: list[str]
    verification: list[str]
    downstream_nodes: list[str]
    design_doc_required: bool
    design_doc_sections: list[str]
    notes: list[str]


def open_change(
    project_path: Path,
    *,
    title: str,
    reason: str,
    scope: str,
    risk: str,
    owner: str = "project_local",
) -> ChangeResult:
    project = require_project_instance(project_path)
    change_id = _new_change_id(title)
    requests_dir = project / "work/change" / "requests"
    requests_dir.mkdir(parents=True, exist_ok=True)
    path = requests_dir / f"{change_id}.md"
    lines = [
        f"# Change Request {change_id}",
        "",
        f"- id: {change_id}",
        "- status: open",
        f"- created_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- owner: {owner}",
        f"- title: {title}",
        f"- risk: {risk}",
        "",
        "## Reason",
        "",
        reason,
        "",
        "## Scope",
        "",
        scope,
        "",
        "## Required Next Records",
        "",
        "- impact analysis under `work/change/impact_analysis/`",
        "- approval under `work/change/approvals/`",
        "- trace update under `work/change/trace_updates/` when requirements, RTL, tests, or reports move",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ChangeResult(path, [f"opened: {change_id}", f"request: {path}"])


def record_impact(
    project_path: Path,
    *,
    change_id: str,
    requirements: list[str],
    artifacts: list[str],
    verification: list[str],
    rollback: str,
    risk: str,
) -> ChangeResult:
    _validate_change_id(change_id)
    project = require_project_instance(project_path)
    _require_request(project, change_id)
    assessment = assess_change_scope(
        requirements=requirements,
        artifacts=artifacts,
        verification=verification,
    )
    impact_dir = project / "work/change" / "impact_analysis"
    impact_dir.mkdir(parents=True, exist_ok=True)
    path = impact_dir / f"{change_id}.md"
    lines = [
        f"# Impact Analysis {change_id}",
        "",
        f"- id: {change_id}",
        "- status: impact_ready",
        f"- updated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- risk: {risk}",
        "",
        "## Requirements",
        "",
        *[f"- {item}" for item in assessment.requirements],
        "",
        "## Artifacts",
        "",
        *[f"- {item}" for item in assessment.artifacts],
        "",
        "## Downstream Nodes",
        "",
        *[f"- {item}" for item in assessment.downstream_nodes],
        "",
        "## Required Verification",
        "",
        *[f"- {item}" for item in assessment.verification],
        "",
        "## Design Document Decision",
        "",
        f"- required: {'yes' if assessment.design_doc_required else 'no'}",
        f"- sections: {', '.join(assessment.design_doc_sections) if assessment.design_doc_sections else 'none'}",
        f"- reason: {'changed project requirement/design/verification/prototype artifacts' if assessment.design_doc_required else 'change does not alter project-facing design intent'}",
        "",
        "## Rollback Plan",
        "",
        rollback,
        "",
        "## Assessment Notes",
        "",
        *[f"- {item}" for item in assessment.notes],
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _update_request_status(project, change_id, "impact_ready")
    return ChangeResult(
        path,
        [
            f"impact recorded: {change_id}",
            f"impact: {path}",
            "downstream_nodes: " + (", ".join(assessment.downstream_nodes) if assessment.downstream_nodes else "none"),
            "design_doc: " + ("required" if assessment.design_doc_required else "not_required"),
        ],
    )


def approve_change(
    project_path: Path,
    *,
    change_id: str,
    approver: str,
    decision: str,
    notes: str,
) -> ChangeResult:
    _validate_change_id(change_id)
    if decision not in {"approved", "rejected"}:
        raise ValueError("decision must be approved or rejected")
    project = require_project_instance(project_path)
    _require_request(project, change_id)
    impact = project / "work/change" / "impact_analysis" / f"{change_id}.md"
    if decision == "approved" and not impact.exists():
        raise FileNotFoundError(f"approval requires impact analysis first: {impact}")
    if decision == "approved":
        errors = validate_change_impact(project, change_id)
        if errors:
            raise ValueError("approval requires complete impact analysis: " + "; ".join(errors))

    approvals_dir = project / "work/change" / "approvals"
    approvals_dir.mkdir(parents=True, exist_ok=True)
    path = approvals_dir / f"{change_id}.md"
    lines = [
        f"# Approval {change_id}",
        "",
        f"- id: {change_id}",
        f"- status: {decision}",
        f"- approved_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- approver: {approver}",
        "",
        "## Notes",
        "",
        notes,
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _update_request_status(project, change_id, decision)
    return ChangeResult(path, [f"{decision}: {change_id}", f"approval: {path}"])


def close_change(project_path: Path, *, change_id: str, gate_report: str, notes: str) -> ChangeResult:
    _validate_change_id(change_id)
    project = require_project_instance(project_path)
    _require_request(project, change_id)
    report_path = project / gate_report
    if not report_path.exists():
        raise FileNotFoundError(f"gate report not found: {gate_report}")
    trace_dir = project / "work/change" / "trace_updates"
    trace_dir.mkdir(parents=True, exist_ok=True)
    path = trace_dir / f"{change_id}.md"
    lines = [
        f"# Trace Update {change_id}",
        "",
        f"- id: {change_id}",
        "- status: closed",
        f"- closed_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- gate_report: {gate_report}",
        "",
        "## Notes",
        "",
        notes,
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _update_request_status(project, change_id, "closed")
    return ChangeResult(path, [f"closed: {change_id}", f"trace_update: {path}"])


def check_changes(project_path: Path) -> ChangeCheckResult:
    project = project_path.resolve()
    messages: list[str] = []
    ok = True
    requests = sorted((project / "work/change" / "requests").glob("CR-*.md"))
    for request in requests:
        fields = _parse_fields(request)
        change_id = fields.get("id") or request.stem
        status = fields.get("status", "")
        if not VALID_ID.match(change_id):
            ok = False
            messages.append(f"FAIL {request.relative_to(project)} has invalid id: {change_id}")
        if status in {"open", "impact_ready"}:
            ok = False
            messages.append(f"FAIL {change_id} is not approved or closed: {status}")
        if status in {"approved", "closed"}:
            for error in validate_change_bundle(project, change_id, require_approval=True):
                ok = False
                messages.append(f"FAIL {change_id} {error}")
        if status == "closed" and not (project / "work/change" / "trace_updates" / f"{change_id}.md").exists():
            ok = False
            messages.append(f"FAIL {change_id} missing trace update")
    if not messages:
        messages.append("PASS no blocking change-control issues")
    report = project / "work/change" / "CHANGE_CONTROL_CHECK.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "\n".join(
            [
                "# Change Control Check",
                "",
                f"- project: {project.name}",
                f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
                f"- result: {'PASS' if ok else 'FAIL'}",
                "",
                "## Results",
                "",
                *[f"- {message}" for message in messages],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return ChangeCheckResult(ok, report, messages)


def assess_change_scope(
    *,
    requirements: list[str] | None = None,
    artifacts: list[str] | None = None,
    verification: list[str] | None = None,
) -> ChangeAssessment:
    """Infer downstream flow impact from changed artifact paths."""

    normalized_requirements = _unique_items(requirements or [])
    normalized_artifacts = _unique_paths(artifacts or [])
    explicit_verification = _unique_items(verification or [])

    downstream: list[str] = []
    sections: list[str] = []
    inferred_verification: list[str] = []
    notes: list[str] = []
    project_design_doc_required = False

    for artifact in normalized_artifacts:
        lower = artifact.lower()
        matched = False
        for rule in _CHANGE_IMPACT_RULES:
            prefixes = rule["prefixes"]
            if any(lower == prefix or lower.startswith(f"{prefix}/") for prefix in prefixes):
                matched = True
                downstream.extend(rule["downstream_nodes"])
                sections.extend(rule["design_doc_sections"])
                inferred_verification.extend(rule["verification"])
                project_design_doc_required = project_design_doc_required or bool(rule["design_doc_required"])
        if not matched:
            notes.append(f"unclassified artifact path, review manually: {artifact}")

    if not normalized_artifacts:
        notes.append("no artifact paths supplied; impact must be reviewed before approval")

    if not normalized_requirements:
        normalized_requirements = ["REQ-IMPACT-TBD: identify affected requirement ID(s) before approval"]

    combined_verification = _unique_items([*explicit_verification, *inferred_verification])
    if not combined_verification:
        combined_verification = ["review impact manually and rerun the owning gate"]

    return ChangeAssessment(
        requirements=normalized_requirements,
        artifacts=normalized_artifacts or ["ARTIFACT-IMPACT-TBD: list changed project-relative path(s)"],
        verification=combined_verification,
        downstream_nodes=_unique_items(downstream) or ["manual_review"],
        design_doc_required=project_design_doc_required,
        design_doc_sections=_unique_items(sections),
        notes=notes or ["impact inferred from supplied artifact path(s)"],
    )


def validate_change_impact(project: Path, change_id: str) -> list[str]:
    impact = project / "work/change" / "impact_analysis" / f"{change_id}.md"
    if not impact.exists():
        return [f"missing impact analysis: work/change/impact_analysis/{change_id}.md"]
    sections = _parse_sections(impact)
    errors: list[str] = []
    required_sections = {
        "requirements": "Requirements",
        "artifacts": "Artifacts",
        "downstream nodes": "Downstream Nodes",
        "required verification": "Required Verification",
        "design document decision": "Design Document Decision",
        "rollback plan": "Rollback Plan",
    }
    for key, label in required_sections.items():
        if key not in sections:
            errors.append(f"impact analysis missing ## {label}")
    for key in ("requirements", "artifacts", "downstream nodes", "required verification"):
        if key in sections and not _section_bullets(sections[key]):
            errors.append(f"impact analysis ## {required_sections[key]} must list at least one item")
    if any("tbd" in item.lower() for item in _section_bullets(sections.get("requirements", []))):
        errors.append("impact analysis requirements still contain TBD placeholder")
    if any("tbd" in item.lower() for item in _section_bullets(sections.get("artifacts", []))):
        errors.append("impact analysis artifacts still contain TBD placeholder")
    decision_lines = sections.get("design document decision", [])
    if decision_lines:
        joined = "\n".join(decision_lines).lower()
        if "required:" not in joined:
            errors.append("design document decision must state required: yes/no")
        if re.search(r"required:\s*yes", joined) and (
            "sections:" not in joined or re.search(r"sections:\s*(?:none|$)", joined)
        ):
            errors.append("design document decision requires non-empty sections when required: yes")
    rollback_lines = sections.get("rollback plan", [])
    if "rollback plan" in sections and not any(line.strip() for line in rollback_lines):
        errors.append("impact analysis ## Rollback Plan must not be empty")
    errors.extend(_validate_required_skill_verification(sections))
    return errors


def validate_change_bundle(project: Path, change_id: str, *, require_approval: bool = True) -> list[str]:
    errors = validate_change_impact(project, change_id)
    request = project / "work/change" / "requests" / f"{change_id}.md"
    if not request.exists():
        errors.append(f"missing request: work/change/requests/{change_id}.md")
    approval = project / "work/change" / "approvals" / f"{change_id}.md"
    if require_approval:
        if not approval.exists():
            errors.append(f"missing approval: work/change/approvals/{change_id}.md")
        else:
            fields = _parse_fields(approval)
            if fields.get("status") != "approved":
                errors.append(f"approval status must be approved, got {fields.get('status')!r}")
    return errors


def _new_change_id(title: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", title.strip()).strip("-").lower()
    if not slug:
        slug = "change"
    return f"CR-{datetime.now().strftime('%Y%m%d%H%M%S')}-{slug[:40]}"


def _validate_change_id(change_id: str) -> None:
    if not VALID_ID.match(change_id):
        raise ValueError(f"invalid change id: {change_id}")


def _require_request(project: Path, change_id: str) -> Path:
    path = project / "work/change" / "requests" / f"{change_id}.md"
    if not path.exists():
        raise FileNotFoundError(f"change request not found: {path}")
    return path


def _update_request_status(project: Path, change_id: str, status: str) -> None:
    path = _require_request(project, change_id)
    lines = path.read_text(encoding="utf-8").splitlines()
    updated = False
    for index, line in enumerate(lines):
        if line.startswith("- status:"):
            lines[index] = f"- status: {status}"
            updated = True
            break
    if not updated:
        lines.insert(2, f"- status: {status}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("- ") and ":" in line:
            key, value = line[2:].split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


_CHANGE_IMPACT_RULES = [
    {
        "prefixes": ("input/spec",),
        "downstream_nodes": ("input", "work/docparse", "work/loop1_rtl_tb", "work/loop2_uvm", "work/loop3_fpga_proto"),
        "design_doc_sections": ("requirements", "rtl", "uvm", "test_plan", "fpga"),
        "verification": (
            "requirements-frontdoor-check",
            "generate-design-doc",
            "run-gate --node spec --change-id <change_id>",
            "run-gate --node docparse --change-id <change_id>",
        ),
        "design_doc_required": True,
    },
    {
        "prefixes": (
            "work/docparse/structured_spec",
            "work/docparse/req_decompose",
            "work/docparse/architecture",
            "work/docparse/verification",
            "work/docparse/prototype",
            "work/docparse/trace_matrix",
        ),
        "downstream_nodes": ("work/docparse", "work/loop1_rtl_tb", "work/loop2_uvm", "work/loop3_fpga_proto"),
        "design_doc_sections": ("requirements", "rtl", "uvm", "test_plan", "fpga"),
        "verification": (
            "requirements-frontdoor-check",
            "generate-design-doc",
            "run-gate --node docparse --change-id <change_id>",
        ),
        "design_doc_required": True,
    },
    {
        "prefixes": ("output/rtl", "output/tb", "work/loop1_rtl_tb"),
        "downstream_nodes": ("work/loop1_rtl_tb", "work/loop2_uvm", "work/loop3_fpga_proto"),
        "design_doc_sections": ("requirements", "rtl", "test_plan"),
        "verification": (
            "requirements-frontdoor-check",
            "generate-design-doc",
            "rtl-skill-audit --project <project>",
            "review-check --project <project> --level develop",
            "run-gate --node loop1 --change-id <change_id>",
        ),
        "design_doc_required": True,
    },
    {
        "prefixes": ("output/uvm", "work/loop2_uvm"),
        "downstream_nodes": ("work/loop2_uvm", "work/loop3_fpga_proto"),
        "design_doc_sections": ("requirements", "uvm", "test_plan"),
        "verification": (
            "requirements-frontdoor-check",
            "generate-design-doc",
            "review-check --project <project> --level develop",
            "run-gate --node loop2 --change-id <change_id>",
        ),
        "design_doc_required": True,
    },
    {
        "prefixes": ("work/loop3_fpga_proto", "output/fpga"),
        "downstream_nodes": ("work/loop3_fpga_proto",),
        "design_doc_sections": ("requirements", "fpga"),
        "verification": (
            "requirements-frontdoor-check",
            "generate-design-doc",
            "prototype-preflight",
            "validate-prototype-plan",
            "loop3-refresh-reports",
            "review-check --project <project> --level develop",
            "run-gate --node loop3 --change-id <change_id>",
        ),
        "design_doc_required": True,
    },
    {
        "prefixes": ("env/core", "env/rule", "env/tool"),
        "downstream_nodes": ("platform",),
        "design_doc_sections": (),
        "verification": ("run platform unit tests", "run affected scaffold validation"),
        "design_doc_required": False,
    },
]


def _unique_items(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = str(item).strip()
        if not text or text.lower() in {"none", "n/a", "na"} or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _unique_paths(items: list[str]) -> list[str]:
    return _unique_items([str(item).strip().replace("\\", "/").strip("/") for item in items])


def _parse_sections(path: Path) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        header = re.match(r"^\s*##+\s+(.+?)\s*$", line)
        if header:
            current = header.group(1).strip().lower()
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)
    return sections


def _section_bullets(lines: list[str]) -> list[str]:
    items: list[str] = []
    for line in lines:
        match = re.match(r"^\s*[-*]\s+(.+?)\s*$", line)
        if match:
            item = match.group(1).strip()
            if item and item.lower() not in {"none", "n/a", "na"}:
                items.append(item)
    return items


def _validate_required_skill_verification(sections: dict[str, list[str]]) -> list[str]:
    artifacts = "\n".join(_section_bullets(sections.get("artifacts", []))).lower().replace("\\", "/")
    verification = "\n".join(_section_bullets(sections.get("required verification", []))).lower()
    errors: list[str] = []
    if "output/rtl" in artifacts:
        required = ("rtl-skill-audit", "review-check", "run-gate --node loop1")
        missing = [item for item in required if item not in verification]
        if missing:
            errors.append("RTL changes must include required verification item(s): " + ", ".join(missing))
    if "output/tb" in artifacts or "work/loop1_rtl_tb" in artifacts:
        required = ("review-check", "run-gate --node loop1")
        missing = [item for item in required if item not in verification]
        if missing:
            errors.append("Loop1 TB changes must include required verification item(s): " + ", ".join(missing))
    if "output/uvm" in artifacts or "work/loop2_uvm" in artifacts:
        required = ("review-check", "run-gate --node loop2")
        missing = [item for item in required if item not in verification]
        if missing:
            errors.append("Loop2 UVM changes must include required verification item(s): " + ", ".join(missing))
    if "work/loop3_fpga_proto" in artifacts or "output/fpga" in artifacts:
        required = ("prototype-preflight", "validate-prototype-plan", "loop3-refresh-reports", "review-check", "run-gate --node loop3")
        missing = [item for item in required if item not in verification]
        if missing:
            errors.append("Loop3 prototype changes must include required verification item(s): " + ", ".join(missing))
    return errors
