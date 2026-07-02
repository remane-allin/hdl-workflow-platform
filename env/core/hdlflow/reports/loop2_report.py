"""Loop2 unified report generator."""

from __future__ import annotations

import json
from pathlib import Path

from ..project import require_project_instance
from .constants import LOOP2_REPORT
from .manifest import ensure_command_record, write_current_manifest, write_report_manifest
from .parser_hdlflow_events import parse_loop2_events
from .report_semantics import enrich_loop2_payload
from .render_report import build_report_payload, render_report_markdown


def generate_loop2_report(project_path: Path, *, change_id: str | None = None) -> tuple[list[Path], dict]:
    project = require_project_instance(project_path)
    log_path = project / LOOP2_REPORT.log_rel
    if not log_path.is_file():
        raise FileNotFoundError(f"missing Loop2 current log: {log_path}")
    coverage_path = project / "work/loop2_uvm/current/log/coverage_raw.txt"
    coverage_text = coverage_path.read_text(encoding="utf-8", errors="ignore") if coverage_path.is_file() else ""
    parsed = parse_loop2_events(log_path.read_text(encoding="utf-8", errors="ignore"), coverage_text=coverage_text)
    payload = build_report_payload(LOOP2_REPORT, project.name, parsed, change_id=change_id)
    payload = enrich_loop2_payload(project, payload)
    report_md = project / LOOP2_REPORT.report_md
    report_json = project / LOOP2_REPORT.report_json
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(render_report_markdown(LOOP2_REPORT, payload), encoding="utf-8")
    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    ensure_command_record(project, LOOP2_REPORT, command=["vsim", "-c", "-do", "work/loop2_uvm/sim/uvm_full_functional.do"], exit_code=0 if payload["result"] == "PASS" else 1, change_id=change_id)
    run_manifest = write_current_manifest(project, LOOP2_REPORT)
    report_manifest = write_report_manifest(project, LOOP2_REPORT)
    return [report_md, report_json, run_manifest, report_manifest], payload
