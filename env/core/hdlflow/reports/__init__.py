"""Unified report generation helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..layout import project_memory_path
from ..pipeline import PipelineNode

from .loop1_report import generate_loop1_report
from .loop2_report import generate_loop2_report
from .parser_hdlflow_events import parse_hdlflow_events, parse_loop1_events, parse_loop2_events


def write_config_run_report(
    project_path: Path,
    pipeline: list[PipelineNode],
    validation_messages: list[str],
) -> Path:
    report_path = project_memory_path(project_path) / "00_global" / "CONFIG_RUN_REPORT.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    status = "PASS" if not validation_messages else "FAIL"
    lines = [
        "# Configuration Run Report",
        "",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- status: {status}",
        f"- project: {project_path.name}",
        "",
        "## Pipeline",
        "",
    ]
    lines.extend(f"- {node.name}" for node in pipeline)
    lines.extend(["", "## Validation", ""])
    if validation_messages:
        lines.extend(f"- ERROR: {message}" for message in validation_messages)
    else:
        lines.append("- all configuration checks passed")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


__all__ = [
    "generate_loop1_report",
    "generate_loop2_report",
    "parse_hdlflow_events",
    "parse_loop1_events",
    "parse_loop2_events",
    "write_config_run_report",
]
