"""Loop2 report refresh from the current structured UVM run."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .reports.loop2_report import generate_loop2_report


@dataclass(frozen=True)
class Loop2ReportResult:
    report_paths: list[Path]
    result: str
    transactions_total: int
    uvm_error_count: int | None
    uvm_fatal_count: int | None
    functional_coverage: float | None
    code_coverage: float | None


def refresh_loop2_reports(project_path: Path) -> Loop2ReportResult:
    """Overwrite the unified Loop2 report artifacts from current structured log."""

    report_paths, payload = generate_loop2_report(project_path)
    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    return Loop2ReportResult(
        report_paths=report_paths,
        result=str(payload.get("result", "BLOCKED")),
        transactions_total=int(summary.get("total_checks") or len(payload.get("transactions", []))),
        uvm_error_count=int(summary.get("uvm_error", 0)),
        uvm_fatal_count=int(summary.get("uvm_fatal", 0)),
        functional_coverage=_coverage_value(summary.get("coverage")),
        code_coverage=None,
    )


def _coverage_value(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip().rstrip("%")
    try:
        return float(text)
    except ValueError:
        return None
