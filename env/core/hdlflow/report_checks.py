"""Independent checks for generated Loop report contracts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .project import require_project_instance
from .reports.constants import LOOP1_REPORT, LOOP2_REPORT, REPORT_MANIFEST_SCHEMA, REPORT_SCHEMA, RUN_MANIFEST_SCHEMA, StageReportDefinition
from .reports.manifest import sha256_file


REPORT_CHECK_REL = "output/reports/report_check.md"
REPORT_DEFINITIONS = {
    "loop1": LOOP1_REPORT,
    "loop2": LOOP2_REPORT,
}


@dataclass(frozen=True)
class ReportIssue:
    stage: str
    severity: str
    message: str


@dataclass(frozen=True)
class ReportCheckResult:
    report_path: Path
    issues: list[ReportIssue]

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)


def check_reports(project_path: Path, *, stage: str = "all", write_report: bool = True) -> ReportCheckResult:
    project = require_project_instance(project_path)
    stage = stage.lower().strip()
    if stage == "all":
        definitions = list(REPORT_DEFINITIONS.values())
    elif stage in REPORT_DEFINITIONS:
        definitions = [REPORT_DEFINITIONS[stage]]
    else:
        raise ValueError("stage must be loop1, loop2, or all")

    issues: list[ReportIssue] = []
    for definition in definitions:
        _check_definition(project, definition, issues)

    report = project / REPORT_CHECK_REL
    if write_report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(_format_report(project, stage, issues), encoding="utf-8")
    return ReportCheckResult(report_path=report, issues=issues)


def _check_definition(project: Path, definition: StageReportDefinition, issues: list[ReportIssue]) -> None:
    stage = definition.report_type
    required_paths = [
        definition.command_json,
        definition.command_md,
        definition.log_rel,
        definition.current_manifest,
        definition.report_md,
        definition.report_json,
        definition.report_manifest,
    ]
    for rel in required_paths:
        if not (project / rel).exists():
            issues.append(ReportIssue(stage, "error", f"missing required artifact: {rel}"))

    payload = _load_json(project / definition.report_json)
    _check_report_payload(definition, payload, issues)
    _check_markdown_shape(project, definition, issues)
    _check_manifests(project, definition, issues)
    _check_no_raw_logs(project, definition, issues)
    _check_no_default_runs(project, definition, issues)


def _check_report_payload(definition: StageReportDefinition, payload: dict[str, Any], issues: list[ReportIssue]) -> None:
    stage = definition.report_type
    if not payload:
        issues.append(ReportIssue(stage, "error", f"{definition.report_json} is missing or invalid JSON"))
        return
    if payload.get("schema") != definition.report_json_schema:
        issues.append(ReportIssue(stage, "error", f"{definition.report_json} schema must be {definition.report_json_schema}"))
    if payload.get("stage") != definition.stage:
        issues.append(ReportIssue(stage, "error", f"{definition.report_json} stage must be {definition.stage}"))
    result = str(payload.get("result", "")).upper()
    if result not in {"PASS", "FAIL", "BLOCKED"}:
        issues.append(ReportIssue(stage, "error", f"{definition.report_json} result must be PASS, FAIL, or BLOCKED"))
    if result == "BLOCKED" and not isinstance(payload.get("blocked_reason"), dict):
        issues.append(ReportIssue(stage, "error", f"{definition.report_json} BLOCKED result must include blocked_reason"))
    source = payload.get("source")
    if source != {"cmd": definition.command_json, "manifest": definition.current_manifest}:
        issues.append(ReportIssue(stage, "error", f"{definition.report_json} source must point to current command and manifest"))
    transactions = payload.get("transactions")
    if result == "PASS" and (not isinstance(transactions, list) or not transactions):
        issues.append(ReportIssue(stage, "error", f"{definition.report_json} PASS result must include checked transactions"))


def _check_markdown_shape(project: Path, definition: StageReportDefinition, issues: list[ReportIssue]) -> None:
    path = project / definition.report_md
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8", errors="ignore")
    required = [
        f"report_schema: {REPORT_SCHEMA}",
        "## 0. Result",
        "## 1. Summary",
        "## 2. Main Results",
        "## 3. Failed Items",
        "## 4. Notes",
    ]
    missing = [marker for marker in required if marker not in text]
    if missing:
        issues.append(ReportIssue(definition.report_type, "error", f"{definition.report_md} missing section(s): " + ", ".join(missing)))
    if re.search(r"(?im)^##\s+.*Evidence\b", text):
        issues.append(ReportIssue(definition.report_type, "error", f"{definition.report_md} must not contain an Evidence section"))


def _check_manifests(project: Path, definition: StageReportDefinition, issues: list[ReportIssue]) -> None:
    stage = definition.report_type
    current = _load_json(project / definition.current_manifest)
    report_manifest = _load_json(project / definition.report_manifest)
    if current and current.get("schema") != RUN_MANIFEST_SCHEMA:
        issues.append(ReportIssue(stage, "error", f"{definition.current_manifest} schema must be {RUN_MANIFEST_SCHEMA}"))
    if report_manifest and report_manifest.get("schema") != REPORT_MANIFEST_SCHEMA:
        issues.append(ReportIssue(stage, "error", f"{definition.report_manifest} schema must be {REPORT_MANIFEST_SCHEMA}"))
    if report_manifest:
        expected = {
            "report_sha256": project / definition.report_md,
            "report_json_sha256": project / definition.report_json,
            "source_manifest_sha256": project / definition.current_manifest,
        }
        for key, path in expected.items():
            if not path.is_file() or report_manifest.get(key) != sha256_file(path):
                issues.append(ReportIssue(stage, "error", f"{definition.report_manifest} hash mismatch: {key}"))


def _check_no_raw_logs(project: Path, definition: StageReportDefinition, issues: list[ReportIssue]) -> None:
    root = project / definition.output_dir
    if not root.exists():
        return
    raw = [
        str(path.relative_to(project)).replace("\\", "/")
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".log", ".out", ".txt"}
    ]
    if raw:
        issues.append(ReportIssue(definition.report_type, "error", "raw log artifact(s) under output/reports: " + ", ".join(raw[:6])))


def _check_no_default_runs(project: Path, definition: StageReportDefinition, issues: list[ReportIssue]) -> None:
    for rel in [f"{definition.stage_dir}/runs", f"{definition.output_dir}/runs"]:
        if (project / rel).exists():
            issues.append(ReportIssue(definition.report_type, "error", f"default run archive is not allowed: {rel}"))


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _format_report(project: Path, stage: str, issues: list[ReportIssue]) -> str:
    errors = [issue for issue in issues if issue.severity == "error"]
    lines = [
        "# Report Contract Check",
        "",
        f"- project: {project.name}",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- stage: {stage}",
        f"- result: {'PASS' if not errors else 'FAIL'}",
        f"- errors: {len(errors)}",
        "",
        "## Issues",
        "",
    ]
    if not issues:
        lines.append("- none")
    else:
        for issue in issues:
            lines.append(f"- {issue.severity}: {issue.stage}: {issue.message}")
    lines.extend(
        [
            "",
            "## Policy",
            "",
            "- Gates consume report JSON and manifests for machine decisions.",
            "- Markdown reports are human-readable projections and are checked only for shape.",
            "- Raw logs belong under work/<stage>/current/log, not under output/reports.",
            "",
        ]
    )
    return "\n".join(lines)
