"""Loop1 report refresh from the current structured RTL/TB run."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .reports.loop1_report import generate_loop1_report


@dataclass(frozen=True)
class Loop1ReportResult:
    report_paths: list[Path]
    result: str
    test_count: int
    error_count: int | None


def refresh_loop1_reports(project_path: Path) -> Loop1ReportResult:
    """Overwrite the unified Loop1 report artifacts from current structured log."""

    report_paths, payload = generate_loop1_report(project_path)
    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    parser_errors = payload.get("parser_errors", []) if isinstance(payload.get("parser_errors"), list) else []
    return Loop1ReportResult(
        report_paths=report_paths,
        result=str(payload.get("result", "BLOCKED")),
        test_count=int(summary.get("total_tests") or len(payload.get("transactions", []))),
        error_count=len(parser_errors),
    )
