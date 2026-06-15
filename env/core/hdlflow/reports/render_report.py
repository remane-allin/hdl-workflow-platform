"""Render unified report Markdown and JSON payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .constants import BLOCKED_BANNER, FAIL_BANNER, PASS_BANNER, REPORT_SCHEMA, StageReportDefinition


def build_report_payload(definition: StageReportDefinition, project: str, parsed: dict[str, Any], *, change_id: str | None) -> dict[str, Any]:
    payload = {
        "schema": definition.report_json_schema,
        "stage": definition.stage,
        "project": project,
        "result": parsed["result"],
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "change_id": change_id,
        "summary": parsed.get("summary", {}),
        "transactions": parsed.get("transactions", []),
        "failed_checks": parsed.get("failed_checks", []),
        "parser_errors": parsed.get("parser_errors", []),
        "source": {
            "cmd": definition.command_json,
            "manifest": definition.current_manifest,
        },
    }
    if str(parsed.get("result", "")).upper() == "BLOCKED":
        payload["blocked_reason"] = _blocked_reason(definition, parsed)
    return payload


def render_report_markdown(definition: StageReportDefinition, payload: dict[str, Any]) -> str:
    result = str(payload.get("result", "BLOCKED")).upper()
    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    transactions = payload.get("transactions", []) if isinstance(payload.get("transactions"), list) else []
    failed_checks = payload.get("failed_checks", []) if isinstance(payload.get("failed_checks"), list) else []
    parser_errors = payload.get("parser_errors", []) if isinstance(payload.get("parser_errors"), list) else []
    blocked_reason = payload.get("blocked_reason") if isinstance(payload.get("blocked_reason"), dict) else {}
    banner = PASS_BANNER if result == "PASS" else (FAIL_BANNER if result == "FAIL" else BLOCKED_BANNER)
    lines = [
        "---",
        f"report_schema: {REPORT_SCHEMA}",
        f"report_type: {definition.report_type}",
        f"project: {payload.get('project', '')}",
        f"stage: {definition.stage}",
        f"result: {result}",
        f"generated_at: {payload.get('generated_at', '')}",
        f"change_id: {payload.get('change_id') if payload.get('change_id') is not None else 'null'}",
        f"source_cmd: {definition.command_json}",
        f"source_manifest: {definition.current_manifest}",
        f"report_json: {definition.report_json}",
        f"report_manifest: {definition.report_manifest}",
        "---",
        f"# {definition.title}",
        "",
        "<!-- HDL-REPORT START -->",
        "",
        "## 0. Result",
        "| Field | Value |",
        "| --- | --- |",
        f"| Stage | `{definition.stage}` |",
        f"| Result | **{result}** |",
    ]
    for key, value in summary.items():
        if key == "result":
            continue
        lines.append(f"| {_label(key)} | {value} |")
    if blocked_reason:
        lines.append(f"| Blocked Reason | {blocked_reason.get('code', 'unknown')} |")
        lines.append(f"| Blocking Owner | {blocked_reason.get('owner', 'sim_agent')} |")
    lines.extend(["", "```text", banner, "```", ""])
    lines.extend(["## 1. Summary", _summary_text(result, definition.report_type), ""])
    lines.extend(["## 2. Main Results", _transactions_table(transactions), ""])
    lines.extend(["## 3. Failed Items", _failed_table(failed_checks, parser_errors), ""])
    lines.extend(["## 4. Notes", "Generated from structured HDLFLOW events.", ""])
    return "\n".join(lines)


def _summary_text(result: str, report_type: str) -> str:
    if result == "PASS":
        return "All structured checks passed."
    if result == "FAIL":
        return "One or more structured checks failed."
    if report_type == "loop2":
        return "Report generation is blocked because the UVM structured summary or required fields are missing."
    return "Report generation is blocked because the structured summary or required fields are missing."


def _blocked_reason(definition: StageReportDefinition, parsed: dict[str, Any]) -> dict[str, str]:
    parser_errors = parsed.get("parser_errors")
    code = str(parser_errors[0]) if isinstance(parser_errors, list) and parser_errors else "blocked_without_reason"
    if definition.report_type == "loop2":
        action = "rerun Loop2 simulation with HDLFLOW UVM summary and required event fields"
    else:
        action = "rerun Loop1 simulation with HDLFLOW summary and required event fields"
    return {
        "code": code,
        "owner": "sim_agent",
        "action": action,
    }


def _transactions_table(transactions: list[Any]) -> str:
    lines = [
        "| Test ID | Txn ID | Sent | Expected RX | Actual RX | Latency Cycles | Result |",
        "| --- | --- | --- | --- | --- | ---: | --- |",
    ]
    if not transactions:
        lines.append("| none | none | none | none | none | 0 | BLOCKED |")
        return "\n".join(lines)
    for item in transactions:
        if not isinstance(item, dict):
            continue
        lines.append(
            "| {test_id} | {txn_id} | {sent} | {expected} | {actual} | {latency} | {result} |".format(
                test_id=item.get("test_id", "-"),
                txn_id=item.get("txn_id", "-"),
                sent=item.get("sent", "-"),
                expected=item.get("expected", "-"),
                actual=item.get("actual", "-"),
                latency=item.get("latency_cycles", "-"),
                result=item.get("result", "-"),
            )
        )
    return "\n".join(lines)


def _failed_table(failed_checks: list[Any], parser_errors: list[Any]) -> str:
    if parser_errors:
        lines = ["| Reason |", "| --- |"]
        for error in parser_errors:
            lines.append(f"| {error} |")
        return "\n".join(lines)
    if not failed_checks:
        return "No failed checks."
    lines = [
        "| Test ID | Txn ID | Sent | Expected RX | Actual RX | Reason |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in failed_checks:
        if not isinstance(item, dict):
            continue
        lines.append(
            "| {test_id} | {txn_id} | {sent} | {expected} | {actual} | {reason} |".format(
                test_id=item.get("test_id", "-"),
                txn_id=item.get("txn_id", "-"),
                sent=item.get("sent", "-"),
                expected=item.get("expected", "-"),
                actual=item.get("actual", "-"),
                reason=item.get("reason", "check_failed"),
            )
        )
    return "\n".join(lines)


def _label(key: str) -> str:
    return key.replace("_", " ").title()
