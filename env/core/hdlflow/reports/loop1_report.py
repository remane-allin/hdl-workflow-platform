"""Loop1 unified report generator."""

from __future__ import annotations

import json
from pathlib import Path

from ..project import require_project_instance
from .constants import LOOP1_REPORT
from .manifest import ensure_command_record, write_current_manifest, write_report_manifest
from .parser_hdlflow_events import parse_loop1_events
from .report_semantics import enrich_loop1_payload
from .render_report import build_report_payload, render_report_markdown


def generate_loop1_report(project_path: Path, *, change_id: str | None = None) -> tuple[list[Path], dict]:
    project = require_project_instance(project_path)
    log_path = project / LOOP1_REPORT.log_rel
    if not log_path.is_file():
        raise FileNotFoundError(f"missing Loop1 current log: {log_path}")
    parsed = parse_loop1_events(log_path.read_text(encoding="utf-8", errors="ignore"))
    payload = build_report_payload(LOOP1_REPORT, project.name, parsed, change_id=change_id)
    payload = enrich_loop1_payload(project, payload)
    report_md = project / LOOP1_REPORT.report_md
    report_json = project / LOOP1_REPORT.report_json
    interface_report = project / "output/reports/loop1/interface_transaction_report.json"
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(render_report_markdown(LOOP1_REPORT, payload), encoding="utf-8")
    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    interface_report.write_text(
        json.dumps(_interface_transaction_payload(project.name, payload), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    ensure_command_record(project, LOOP1_REPORT, command=["vsim", "-c", "-do", "work/loop1_rtl_tb/sim/rtl_functional.do"], exit_code=0 if payload["result"] == "PASS" else 1, change_id=change_id)
    run_manifest = write_current_manifest(project, LOOP1_REPORT)
    report_manifest = write_report_manifest(project, LOOP1_REPORT)
    return [report_md, report_json, interface_report, run_manifest, report_manifest], payload


def _interface_transaction_payload(project: str, payload: dict) -> dict:
    transactions = payload.get("transactions", []) if isinstance(payload.get("transactions"), list) else []
    events: list[dict[str, object]] = []
    for index, item in enumerate(transactions, start=1):
        if not isinstance(item, dict):
            continue
        events.append(
            {
                "event_id": str(item.get("txn_id") or f"txn_{index:04d}"),
                "requirement_id": item.get("requirement_id", ""),
                "operation_id": item.get("operation_id", ""),
                "interface": item.get("observed_interface", ""),
                "operation": item.get("operation_id") or item.get("sent", ""),
                "payload": item.get("sent", ""),
                "response": item.get("actual", ""),
                "expected_response": item.get("expected", ""),
                "latency": item.get("latency_cycles", 0),
                "status": item.get("result", ""),
                "evidence_type": item.get("evidence_type", ""),
            }
        )
    return {
        "schema_version": 1,
        "project": project,
        "source_report": LOOP1_REPORT.report_json,
        "result": payload.get("result", "BLOCKED"),
        "events": events,
    }
