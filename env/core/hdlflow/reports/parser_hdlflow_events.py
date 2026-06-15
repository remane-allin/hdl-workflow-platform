"""Parse HDLFLOW structured simulation events."""

from __future__ import annotations

import re
from typing import Any

from .constants import EVENT_SCHEMA, EVENT_VERSION


def parse_hdlflow_events(text: str) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("HDLFLOW|"):
            continue
        parts = line.split("|")
        if len(parts) < 2:
            continue
        event: dict[str, str] = {"event": parts[1]}
        for part in parts[2:]:
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            event[key.strip()] = value.strip()
        events.append(event)
    return events


def parse_loop1_events(text: str) -> dict[str, Any]:
    events = parse_hdlflow_events(text)
    checks = [event for event in events if event.get("event") == "CHECK"]
    summary_events = [event for event in events if event.get("event") == "SUMMARY"]
    errors: list[str] = []

    if not summary_events:
        errors.append("missing_structured_summary")
    for index, event in enumerate(checks, start=1):
        errors.extend(_event_meta_errors(event, f"CHECK[{index}]", expected_stage="loop1"))
    for index, event in enumerate(summary_events, start=1):
        errors.extend(_event_meta_errors(event, f"SUMMARY[{index}]", expected_stage="loop1"))

    transactions: list[dict[str, Any]] = []
    required = ["test_id", "txn_id", "sent", "expected", "actual", "latency_cycles", "result"]
    for index, event in enumerate(checks, start=1):
        missing = [field for field in required if not event.get(field)]
        if missing:
            errors.append(f"CHECK[{index}] missing field(s): " + ", ".join(missing))
            continue
        row = {
            "test_id": event["test_id"],
            "txn_id": event["txn_id"],
            "sent": event["sent"],
            "expected": event["expected"],
            "actual": event["actual"],
            "latency_cycles": _int_or_text(event["latency_cycles"]),
            "result": event["result"],
        }
        if event.get("reason"):
            row["reason"] = event["reason"]
        transactions.append(row)

    summary = _summary_from_event(summary_events[-1] if summary_events else {}, transactions)
    failed_checks = [
        item
        for item in transactions
        if str(item.get("result", "")).upper() != "PASS"
    ]
    if errors:
        result = "BLOCKED"
    elif failed_checks or str(summary.get("result", "")).upper() == "FAIL":
        result = "FAIL"
    else:
        result = "PASS"

    return {
        "result": result,
        "summary": summary,
        "transactions": transactions,
        "failed_checks": failed_checks,
        "parser_errors": errors,
        "events_seen": len(events),
    }


def parse_loop2_events(text: str, *, coverage_text: str = "") -> dict[str, Any]:
    events = parse_hdlflow_events(text)
    checks = [event for event in events if event.get("event") == "UVM_CHECK"]
    summary_events = [event for event in events if event.get("event") == "UVM_SUMMARY"]
    errors: list[str] = []
    if not summary_events:
        errors.append("missing_structured_uvm_summary")
    for index, event in enumerate(checks, start=1):
        errors.extend(_event_meta_errors(event, f"UVM_CHECK[{index}]", expected_stage="loop2"))
    for index, event in enumerate(summary_events, start=1):
        errors.extend(_event_meta_errors(event, f"UVM_SUMMARY[{index}]", expected_stage="loop2"))

    transactions: list[dict[str, Any]] = []
    required = ["test_id", "txn_id", "sent", "expected", "actual", "result"]
    for index, event in enumerate(checks, start=1):
        missing = [field for field in required if not event.get(field)]
        if missing:
            errors.append(f"UVM_CHECK[{index}] missing field(s): " + ", ".join(missing))
            continue
        row = {
            "test_id": event["test_id"],
            "txn_id": event["txn_id"],
            "sent": event["sent"],
            "expected": event["expected"],
            "actual": event["actual"],
            "latency_cycles": _int_or_text(event.get("latency_cycles", "-")),
            "result": event["result"],
        }
        if event.get("reason"):
            row["reason"] = event["reason"]
        transactions.append(row)

    event_summary = summary_events[-1] if summary_events else {}
    summary = {
        "uvm_error": _int_or_zero(event_summary.get("uvm_error")),
        "uvm_fatal": _int_or_zero(event_summary.get("uvm_fatal")),
        "total_checks": _int_or_zero(event_summary.get("total_checks")) or len(transactions),
        "failed_checks": _int_or_zero(event_summary.get("failed_checks")),
        "coverage": event_summary.get("coverage") or _coverage_from_text(coverage_text),
        "result": event_summary.get("result", "BLOCKED" if errors else "PASS"),
    }
    failed_checks = [
        item
        for item in transactions
        if str(item.get("result", "")).upper() != "PASS"
    ]
    if errors:
        result = "BLOCKED"
    elif failed_checks or summary["uvm_error"] != 0 or summary["uvm_fatal"] != 0 or summary["failed_checks"] != 0:
        result = "FAIL"
    elif str(summary.get("result", "")).upper() == "FAIL":
        result = "FAIL"
    else:
        result = "PASS"
    summary["result"] = result
    return {
        "result": result,
        "summary": summary,
        "transactions": transactions,
        "failed_checks": failed_checks,
        "parser_errors": errors,
        "events_seen": len(events),
    }


def _summary_from_event(event: dict[str, str], transactions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total_tests": _int_or_zero(event.get("total_tests")),
        "passed_tests": _int_or_zero(event.get("passed_tests")),
        "failed_tests": _int_or_zero(event.get("failed_tests")),
        "total_checks": _int_or_zero(event.get("total_checks")) or len(transactions),
        "passed_checks": _int_or_zero(event.get("passed_checks")),
        "failed_checks": _int_or_zero(event.get("failed_checks")),
        "result": event.get("result", "BLOCKED" if not event else "PASS"),
    }


def _event_meta_errors(event: dict[str, str], label: str, *, expected_stage: str) -> list[str]:
    errors: list[str] = []
    if event.get("schema") != EVENT_SCHEMA:
        errors.append(f"{label} schema must be {EVENT_SCHEMA}")
    if event.get("version") != EVENT_VERSION:
        errors.append(f"{label} version must be {EVENT_VERSION}")
    if event.get("stage") != expected_stage:
        errors.append(f"{label} stage must be {expected_stage}")
    return errors


def _int_or_zero(value: object) -> int:
    try:
        return int(str(value))
    except Exception:
        return 0


def _int_or_text(value: object) -> int | str:
    try:
        return int(str(value))
    except Exception:
        return str(value)


def _coverage_from_text(text: str) -> str:
    patterns = [
        r"TOTAL COVERGROUP COVERAGE:\s*([0-9]+(?:\.[0-9]+)?)%",
        r"Aggregate\s*\|\s*([0-9]+(?:\.[0-9]+)?)%",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return "not_reported"
