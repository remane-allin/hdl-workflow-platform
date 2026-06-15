"""Loop1 unified report generator."""

from __future__ import annotations

import json
from pathlib import Path

from ..project import require_project_instance
from .constants import LOOP1_REPORT
from .manifest import ensure_command_record, write_current_manifest, write_report_manifest
from .parser_hdlflow_events import parse_loop1_events
from .render_report import build_report_payload, render_report_markdown


def generate_loop1_report(project_path: Path, *, change_id: str | None = None) -> tuple[list[Path], dict]:
    project = require_project_instance(project_path)
    log_path = project / LOOP1_REPORT.log_rel
    if not log_path.is_file():
        raise FileNotFoundError(f"missing Loop1 current log: {log_path}")
    parsed = parse_loop1_events(log_path.read_text(encoding="utf-8", errors="ignore"))
    payload = build_report_payload(LOOP1_REPORT, project.name, parsed, change_id=change_id)
    report_md = project / LOOP1_REPORT.report_md
    report_json = project / LOOP1_REPORT.report_json
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(render_report_markdown(LOOP1_REPORT, payload), encoding="utf-8")
    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    ensure_command_record(project, LOOP1_REPORT, command=["vsim", "-c", "-do", "work/loop1_rtl_tb/sim/rtl_functional.do"], exit_code=0 if payload["result"] == "PASS" else 1, change_id=change_id)
    run_manifest = write_current_manifest(project, LOOP1_REPORT)
    report_manifest = write_report_manifest(project, LOOP1_REPORT)
    return [report_md, report_json, run_manifest, report_manifest], payload
