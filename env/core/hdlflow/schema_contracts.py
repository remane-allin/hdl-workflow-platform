"""Friendly schema checks for machine-readable workflow YAML.

The gate runner remains the authority. These validators provide earlier and
clearer diagnostics for common YAML shape errors without weakening gate rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .project import require_project_instance
from .requirements_frontend import DOCUMENT_ANALYSIS_REL
from .review import REQUIRED_FINDING_FIELDS
from .simple_yaml import load_yaml


TRACE_MATRIX_RELS = [
    "work/docparse/trace_matrix/req_to_arch.yaml",
    "work/docparse/trace_matrix/req_to_rtl.yaml",
    "work/docparse/trace_matrix/req_to_test.yaml",
    "work/docparse/trace_matrix/req_to_proto.yaml",
]

SCHEMA_REPORT_REL = "output/reports/schema/schema_check.md"


@dataclass(frozen=True)
class SchemaIssue:
    path: str
    severity: str
    message: str


@dataclass(frozen=True)
class SchemaCheckResult:
    report_path: Path
    issues: list[SchemaIssue]

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)


def schema_check(project_path: Path, *, file_rel: str | None = None, write_report: bool = True) -> SchemaCheckResult:
    project = require_project_instance(project_path)
    issues: list[SchemaIssue] = []

    rels = [file_rel] if file_rel else [DOCUMENT_ANALYSIS_REL, *TRACE_MATRIX_RELS, "work/docparse/review/role_findings.yaml"]
    for rel in rels:
        if rel is None:
            continue
        path = project / rel
        if not path.exists():
            issues.append(SchemaIssue(rel, "error", "missing schema target"))
            continue
        try:
            data = load_yaml(path)
        except Exception as exc:
            issues.append(SchemaIssue(rel, "error", f"not parseable: {exc}"))
            continue
        normalized = rel.replace("\\", "/")
        if normalized.endswith("document_analysis.yaml"):
            issues.extend(_check_document_analysis(rel, data))
        elif "/trace_matrix/" in normalized:
            issues.extend(_check_trace_matrix(rel, data))
        elif normalized.endswith("role_findings.yaml"):
            issues.extend(_check_role_findings(rel, data))
        else:
            issues.append(SchemaIssue(rel, "warning", "no specialized schema checker for this file"))

    report = project / SCHEMA_REPORT_REL
    if write_report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(_format_schema_report(project, issues), encoding="utf-8")
    return SchemaCheckResult(report_path=report, issues=issues)


def _check_document_analysis(rel: str, data: dict[str, Any]) -> list[SchemaIssue]:
    issues: list[SchemaIssue] = []
    for key in ("source_documents", "analysis_units", "evidence_map", "question_review"):
        if key not in data:
            issues.append(SchemaIssue(rel, "error", f"missing required key: {key}"))
    for index, item in enumerate(_list(data.get("source_documents")), 1):
        _require_fields(issues, rel, f"source_documents[{index}]", item, ["source_ref", "parser_output", "document_type"])
    for index, item in enumerate(_list(data.get("analysis_units")), 1):
        _require_fields(issues, rel, f"analysis_units[{index}]", item, ["unit_id", "source_ref", "section", "summary"])
        if isinstance(item, dict) and not (item.get("extracted_requirements") or item.get("evidence_refs")):
            issues.append(SchemaIssue(rel, "error", f"analysis_units[{index}] must include extracted_requirements or evidence_refs"))
    for index, item in enumerate(_list(data.get("evidence_map")), 1):
        _require_fields(issues, rel, f"evidence_map[{index}]", item, ["requirement_id", "evidence_refs"])
    review = data.get("question_review")
    if isinstance(review, dict):
        _require_fields(issues, rel, "question_review", review, ["status", "reviewed_by", "review_evidence", "unresolved_count"])
    elif "question_review" in data:
        issues.append(SchemaIssue(rel, "error", "question_review must be a mapping"))
    return issues


def _check_trace_matrix(rel: str, data: dict[str, Any]) -> list[SchemaIssue]:
    issues: list[SchemaIssue] = []
    if "mappings" in data and "links" not in data:
        issues.append(SchemaIssue(rel, "error", "trace matrices use `links`, not `mappings`"))
    links = data.get("links")
    if not isinstance(links, list):
        issues.append(SchemaIssue(rel, "error", "missing required list: links"))
        return issues
    for index, item in enumerate(links, 1):
        if not isinstance(item, dict):
            issues.append(SchemaIssue(rel, "error", f"links[{index}] must be a mapping"))
            continue
        if not any(key in item for key in ("requirement_id", "source", "from")):
            issues.append(SchemaIssue(rel, "warning", f"links[{index}] should identify a requirement/source"))
        if not any(key in item for key in ("target", "artifact", "to")):
            issues.append(SchemaIssue(rel, "warning", f"links[{index}] should identify a target artifact"))
    return issues


def _check_role_findings(rel: str, data: dict[str, Any]) -> list[SchemaIssue]:
    issues: list[SchemaIssue] = []
    for role, findings in data.items():
        if role in {"schema_version", "project", "status", "generated_at"}:
            continue
        for index, item in enumerate(_list(findings), 1):
            if not isinstance(item, dict):
                issues.append(SchemaIssue(rel, "error", f"{role}[{index}] must be a mapping"))
                continue
            missing = [field for field in REQUIRED_FINDING_FIELDS if field not in item or item.get(field) in {None, ""}]
            if missing:
                issues.append(SchemaIssue(rel, "error", f"{role}[{index}] missing field(s): {', '.join(missing)}"))
    return issues


def _require_fields(issues: list[SchemaIssue], rel: str, label: str, item: Any, fields: list[str]) -> None:
    if not isinstance(item, dict):
        issues.append(SchemaIssue(rel, "error", f"{label} must be a mapping"))
        return
    missing = [field for field in fields if field not in item or item.get(field) in {None, ""}]
    if missing:
        issues.append(SchemaIssue(rel, "error", f"{label} missing field(s): {', '.join(missing)}"))


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _format_schema_report(project: Path, issues: list[SchemaIssue]) -> str:
    lines = [
        "# Schema Check",
        "",
        f"- project: {project.name}",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- result: {'PASS' if not any(issue.severity == 'error' for issue in issues) else 'FAIL'}",
        "",
        "## Issues",
        "",
    ]
    lines.extend([f"- {issue.severity}: {issue.path}: {issue.message}" for issue in issues] or ["- none"])
    lines.extend(
        [
            "",
            "## Guardrail",
            "",
            "- Schema check reports diagnostics only; it does not repair or generate design documents.",
        ]
    )
    return "\n".join(lines) + "\n"
