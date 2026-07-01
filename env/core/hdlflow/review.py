"""Structured Review Agent finding checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .project import require_project_instance
from .simple_yaml import load_yaml


REVIEW_FINDINGS_REL = "work/docparse/review/role_findings.yaml"
REVIEW_REPORT_REL = "output/reports/review/review_check.md"

REVIEW_ROLE_NAMES = ("spec", "arch", "exec", "sim", "review", "arbtr")
VALID_SEVERITIES = ("critical", "high", "medium", "low", "info")
VALID_STATUSES = ("open", "routed", "fixed", "verified", "closed", "waived")
CLOSED_STATUSES = {"verified", "closed", "waived"}
REQUIRED_FINDING_FIELDS = (
    "id",
    "severity",
    "status",
    "category",
    "owner",
    "artifact",
    "issue",
    "impact",
    "evidence",
    "recommendation",
    "route_to",
)

BLOCKING_SEVERITIES_BY_LEVEL = {
    "debug": {"critical"},
    "develop": {"critical", "high"},
    "release": {"critical", "high", "medium"},
}


@dataclass(frozen=True)
class ReviewFinding:
    finding_id: str
    role: str
    severity: str
    status: str
    owner: str
    route_to: str
    artifact: str
    issue: str
    impact: str
    evidence: str
    recommendation: str


@dataclass(frozen=True)
class ReviewPayloadResult:
    findings: list[ReviewFinding]
    errors: list[str]
    warnings: list[str]


@dataclass(frozen=True)
class ReviewCheckResult:
    report_path: Path
    ok: bool
    blocking_findings: list[str]
    errors: list[str]
    warnings: list[str]


def check_review_findings(project_path: Path, *, level: str = "develop") -> ReviewCheckResult:
    """Validate structured review findings and write a review gate report."""

    project = require_project_instance(project_path)
    level = level if level in BLOCKING_SEVERITIES_BY_LEVEL else "develop"
    findings_path = project / REVIEW_FINDINGS_REL
    errors: list[str] = []
    warnings: list[str] = []
    payload_result = ReviewPayloadResult([], [], [])

    if not findings_path.exists():
        errors.append(f"missing review findings file: {REVIEW_FINDINGS_REL}")
    else:
        try:
            data = load_yaml(findings_path)
        except Exception as exc:
            errors.append(f"{REVIEW_FINDINGS_REL} is not parseable: {exc}")
        else:
            payload_result = validate_review_payload(data, require_ready=False)
            errors.extend(payload_result.errors)
            warnings.extend(payload_result.warnings)

    _check_rtl_skill_review_coverage(project, payload_result.findings, errors)

    blocking = _blocking_finding_summaries(payload_result.findings, level)
    if blocking:
        errors.append(f"unclosed blocking review finding(s): {len(blocking)}")

    report_path = _write_review_report(project, level, payload_result.findings, blocking, errors, warnings)
    return ReviewCheckResult(
        report_path=report_path,
        ok=not errors,
        blocking_findings=blocking,
        errors=errors,
        warnings=warnings,
    )


def review_blockers(project_path: Path, *, level: str = "develop") -> list[str]:
    """Return open review blockers without treating a missing file as a Ralph blocker."""

    project = require_project_instance(project_path)
    path = project / REVIEW_FINDINGS_REL
    if not path.exists():
        return []
    try:
        data = load_yaml(path)
    except Exception:
        return []
    result = validate_review_payload(data, require_ready=False)
    return _blocking_finding_summaries(result.findings, level)


def validate_review_payload(data: dict[str, Any], *, require_ready: bool) -> ReviewPayloadResult:
    errors: list[str] = []
    warnings: list[str] = []
    findings: list[ReviewFinding] = []

    if data.get("schema_version") != 1:
        errors.append(f"{REVIEW_FINDINGS_REL} schema_version must be 1")
    roles = data.get("roles")
    if not isinstance(roles, dict):
        errors.append(f"{REVIEW_FINDINGS_REL} roles must be a mapping")
        return ReviewPayloadResult(findings, errors, warnings)

    missing_roles = sorted(set(REVIEW_ROLE_NAMES) - {str(role) for role in roles})
    if missing_roles:
        errors.append(f"{REVIEW_FINDINGS_REL} missing role(s): " + ", ".join(missing_roles))

    finding_ids: set[str] = set()
    for role_name in REVIEW_ROLE_NAMES:
        role_item = roles.get(role_name)
        if role_item is None:
            continue
        if not isinstance(role_item, dict):
            errors.append(f"{REVIEW_FINDINGS_REL} role {role_name} must be a mapping")
            continue
        if require_ready and str(role_item.get("status") or "").upper() != "READY":
            errors.append(f"{REVIEW_FINDINGS_REL} role {role_name} status must be READY")
        raw_findings = role_item.get("findings")
        if not isinstance(raw_findings, list):
            errors.append(f"{REVIEW_FINDINGS_REL} role {role_name} findings must be a list")
            continue
        if require_ready and not raw_findings:
            errors.append(f"{REVIEW_FINDINGS_REL} role {role_name} findings must be non-empty for READY")
        for index, raw_finding in enumerate(raw_findings, start=1):
            finding = _parse_finding(role_name, index, raw_finding, errors)
            if finding is None:
                continue
            if finding.finding_id in finding_ids:
                errors.append(f"{REVIEW_FINDINGS_REL} duplicate finding id: {finding.finding_id}")
            finding_ids.add(finding.finding_id)
            findings.append(finding)

        raw_blockers = role_item.get("blockers")
        if isinstance(raw_blockers, list) and raw_blockers:
            errors.append(f"{REVIEW_FINDINGS_REL} role {role_name} blockers must be represented as structured findings")

    unknown_roles = sorted(str(role) for role in roles if str(role) not in REVIEW_ROLE_NAMES)
    if unknown_roles:
        warnings.append(f"{REVIEW_FINDINGS_REL} unknown role section(s): " + ", ".join(unknown_roles))

    conflicts = data.get("cross_role_conflicts")
    if conflicts is not None and not isinstance(conflicts, list):
        errors.append(f"{REVIEW_FINDINGS_REL} cross_role_conflicts must be a list")
    assumptions = data.get("assumptions")
    if assumptions is not None and not isinstance(assumptions, list):
        errors.append(f"{REVIEW_FINDINGS_REL} assumptions must be a list")

    return ReviewPayloadResult(findings, errors, warnings)


def _parse_finding(role_name: str, index: int, value: Any, errors: list[str]) -> ReviewFinding | None:
    prefix = f"{REVIEW_FINDINGS_REL} role {role_name} findings[{index}]"
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be a mapping with structured review fields")
        return None

    missing = [field for field in REQUIRED_FINDING_FIELDS if _blank(value.get(field))]
    if missing:
        errors.append(f"{prefix} missing required field(s): " + ", ".join(missing))
        return None

    severity = _norm(value.get("severity"))
    status = _norm(value.get("status"))
    route_to = _norm(value.get("route_to"))
    owner = _norm(value.get("owner"))

    if severity not in VALID_SEVERITIES:
        errors.append(f"{prefix} severity must be one of: " + ", ".join(VALID_SEVERITIES))
    if status not in VALID_STATUSES:
        errors.append(f"{prefix} status must be one of: " + ", ".join(VALID_STATUSES))
    if route_to not in REVIEW_ROLE_NAMES:
        errors.append(f"{prefix} route_to must be one of: " + ", ".join(REVIEW_ROLE_NAMES))
    if owner not in REVIEW_ROLE_NAMES:
        errors.append(f"{prefix} owner must be one of: " + ", ".join(REVIEW_ROLE_NAMES))
    if severity not in VALID_SEVERITIES or status not in VALID_STATUSES or route_to not in REVIEW_ROLE_NAMES or owner not in REVIEW_ROLE_NAMES:
        return None

    return ReviewFinding(
        finding_id=str(value.get("id")).strip(),
        role=role_name,
        severity=severity,
        status=status,
        owner=owner,
        route_to=route_to,
        artifact=str(value.get("artifact")).strip(),
        issue=_stringify(value.get("issue")),
        impact=_stringify(value.get("impact")),
        evidence=_stringify(value.get("evidence")),
        recommendation=_stringify(value.get("recommendation")),
    )


def _blocking_finding_summaries(findings: list[ReviewFinding], level: str) -> list[str]:
    severities = BLOCKING_SEVERITIES_BY_LEVEL.get(level, BLOCKING_SEVERITIES_BY_LEVEL["develop"])
    blocking = [
        finding
        for finding in findings
        if finding.severity in severities and finding.status not in CLOSED_STATUSES
    ]
    return [_finding_summary(finding) for finding in blocking]


def _check_rtl_skill_review_coverage(project: Path, findings: list[ReviewFinding], errors: list[str]) -> None:
    review_findings = [finding for finding in findings if finding.role == "review"]
    review_text = "\n".join(_finding_text(finding) for finding in review_findings).lower()
    if not review_text and _formal_review_required(project):
        errors.append(
            "Review Agent must include structured formal artifact review findings when implementation artifacts exist"
        )
        return

    rtl_files = sorted((project / "output" / "rtl").glob("*.v"))
    if not rtl_files:
        _check_tb_review_coverage(project, review_text, errors)
        _check_uvm_review_coverage(project, review_text, errors)
        _check_loop3_review_coverage(project, review_text, errors)
        return

    if "rtl_skill_audit.md" not in review_text or "output/reports/loop1/rtl_skill_audit.md" not in review_text:
        errors.append(
            "Review Agent must cite output/reports/loop1/rtl_skill_audit.md when RTL files exist"
        )
    if "rtl-architecture-and-gen" not in review_text and "verilog-rtl-style-guide" not in review_text:
        errors.append(
            "Review Agent must cite rtl-architecture-and-gen or verilog-rtl-style-guide when reviewing RTL"
        )

    missing = [path.name for path in rtl_files if path.name.lower() not in review_text]
    if missing:
        errors.append("Review Agent RTL skill finding must mention every RTL file reviewed: " + ", ".join(missing[:8]))
    if "rtl_semantic_stub_absent" not in review_text and "semantic signoff" not in review_text:
        errors.append("Review Agent must cite rtl_semantic_stub_absent or semantic signoff when reviewing RTL")
    _check_tb_review_coverage(project, review_text, errors)
    _check_uvm_review_coverage(project, review_text, errors)
    _check_loop3_review_coverage(project, review_text, errors)


def _formal_review_required(project: Path) -> bool:
    return bool(
        list((project / "output" / "rtl").glob("*.v"))
        or list((project / "output" / "tb").glob("*.v"))
        or list((project / "output" / "uvm").rglob("*.sv"))
        or list((project / "output" / "uvm").rglob("*.svh"))
        or _has_loop3_formal_artifacts(project)
    )


def _check_tb_review_coverage(project: Path, review_text: str, errors: list[str]) -> None:
    tb_files = sorted((project / "output" / "tb").glob("*.v"))
    if not tb_files:
        return
    if "output/docs/test/verification_plan.md" not in review_text:
        errors.append("Review Agent must cite output/docs/test/verification_plan.md when directed TB files exist")
    if "loop1_waveform_blocking" not in review_text and "waveform_gate.json" not in review_text:
        errors.append("Review Agent must cite loop1_waveform_blocking or waveform_gate.json when reviewing directed TB files")
    if "loop1_task_requirement_evidence" not in review_text and "task requirement evidence" not in review_text:
        errors.append("Review Agent must cite loop1_task_requirement_evidence when reviewing directed TB files")
    if "modelsim-run-triage-debug" not in review_text and "rtl-architecture-and-gen" not in review_text:
        errors.append("Review Agent must cite modelsim-run-triage-debug or rtl-architecture-and-gen when reviewing directed TB files")
    missing = [path.name for path in tb_files if path.name.lower() not in review_text]
    if missing:
        errors.append("Review Agent directed-TB finding must mention every TB file reviewed: " + ", ".join(missing[:8]))


def _check_uvm_review_coverage(project: Path, review_text: str, errors: list[str]) -> None:
    uvm_files = sorted([*(project / "output" / "uvm").rglob("*.sv"), *(project / "output" / "uvm").rglob("*.svh")])
    if not uvm_files:
        return
    if "uvm-env-and-test-build" not in review_text:
        errors.append("Review Agent must cite uvm-env-and-test-build when UVM files exist")
    if "loop2_independent_oracle" not in review_text and "independent oracle" not in review_text:
        errors.append("Review Agent must cite loop2_independent_oracle when reviewing UVM files")
    missing = [path.name for path in uvm_files if path.name.lower() not in review_text]
    if missing:
        errors.append("Review Agent UVM finding must mention every UVM file reviewed: " + ", ".join(missing[:8]))


def _check_loop3_review_coverage(project: Path, review_text: str, errors: list[str]) -> None:
    if not _has_loop3_formal_artifacts(project):
        return
    required = ("prototype-preflight", "validate-prototype-plan", "loop3-refresh-reports")
    missing = [marker for marker in required if marker not in review_text]
    if missing:
        errors.append("Review Agent Loop3 finding must cite prototype signoff entry point(s): " + ", ".join(missing))
    if "loop3_validation_boundary_claim" not in review_text and "claim policy" not in review_text:
        errors.append("Review Agent Loop3 finding must cite loop3_validation_boundary_claim or claim policy")


def _has_loop3_formal_artifacts(project: Path) -> bool:
    loop3_roots = [
        project / "work" / "loop3_fpga_proto" / "board_tests",
        project / "work" / "loop3_fpga_proto" / "board_profiles",
        project / "output" / "fpga",
    ]
    for root in loop3_roots:
        if root.exists() and any(path.is_file() and path.name != ".gitkeep" for path in root.rglob("*")):
            return True
    return False


def _finding_text(finding: ReviewFinding) -> str:
    return "\n".join(
        [
            finding.finding_id,
            finding.artifact,
            finding.issue,
            finding.impact,
            finding.evidence,
            finding.recommendation,
        ]
    )


def _finding_summary(finding: ReviewFinding) -> str:
    return (
        f"{finding.finding_id} [{finding.severity}/{finding.status}] "
        f"{finding.role}->{finding.route_to}: {finding.issue} ({finding.artifact})"
    )


def _write_review_report(
    project: Path,
    level: str,
    findings: list[ReviewFinding],
    blocking: list[str],
    errors: list[str],
    warnings: list[str],
) -> Path:
    report_path = project / REVIEW_REPORT_REL
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Review Check",
        "",
        f"- project: {project.name}",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- level: {level}",
        f"- result: {'PASS' if not errors else 'FAIL'}",
        f"- finding_count: {len(findings)}",
        f"- blocking_count: {len(blocking)}",
        "",
        "## Blocking Findings",
        "",
        *([f"- {item}" for item in blocking] or ["- none"]),
        "",
        "## Findings",
        "",
        *([f"- {_finding_summary(item)}" for item in findings] or ["- none"]),
        "",
        "## Errors",
        "",
        *([f"- {item}" for item in errors] or ["- none"]),
        "",
        "## Warnings",
        "",
        *([f"- {item}" for item in warnings] or ["- none"]),
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def _blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return not value
    return False


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _stringify(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()
