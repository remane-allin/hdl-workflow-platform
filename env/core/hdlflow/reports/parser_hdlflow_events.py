"""Parse HDLFLOW structured simulation events."""

from __future__ import annotations

import re
from typing import Any

from .constants import EVENT_SCHEMA, EVENT_VERSION


def parse_hdlflow_events(text: str) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            line = line[1:].strip()
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
    optional = [
        "requirement_id",
        "operation_id",
        "observed_interface",
        "evidence_type",
        "check_role",
        "readback_checked",
        "side_effect_checked",
        "expected_readback",
        "expected_side_effect",
    ]
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
        for field in optional:
            if event.get(field):
                row[field] = event[field]
        if event.get("reason"):
            row["reason"] = event["reason"]
        transactions.append(row)

    summary = _summary_from_event(summary_events[-1] if summary_events else {}, transactions)
    semantic_summary = _loop1_semantic_summary(summary_events[-1] if summary_events else {}, transactions)
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
        "semantic_summary": semantic_summary,
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
    optional = [
        "requirement_id",
        "operation_id",
        "scenario_id",
        "scenario_kind",
        "coverage_bins",
        "cross_coverage",
        "scoreboard_model",
        "reference_model",
        "observation_source",
        "assertion_id",
        "assertions",
        "coverage_source",
    ]
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
        for field in optional:
            if event.get(field):
                row[field] = event[field]
        if event.get("reason"):
            row["reason"] = event["reason"]
        transactions.append(row)

    event_summary = summary_events[-1] if summary_events else {}
    coverage_source = event_summary.get("coverage_source")
    if not coverage_source:
        coverage_source = "summary_event" if event_summary.get("coverage") else ("coverage_report" if coverage_text else "not_reported")
    summary = {
        "uvm_error": _int_or_zero(event_summary.get("uvm_error")),
        "uvm_fatal": _int_or_zero(event_summary.get("uvm_fatal")),
        "total_checks": _int_or_zero(event_summary.get("total_checks")) or len(transactions),
        "failed_checks": _int_or_zero(event_summary.get("failed_checks")),
        "coverage": event_summary.get("coverage") or _coverage_from_text(coverage_text),
        "coverage_source": coverage_source,
        "result": event_summary.get("result", "BLOCKED" if errors else "PASS"),
    }
    semantic_summary = _loop2_semantic_summary(summary, transactions)
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
        "semantic_summary": semantic_summary,
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


def _loop1_semantic_summary(event: dict[str, str], transactions: list[dict[str, Any]]) -> dict[str, Any]:
    passed = [item for item in transactions if str(item.get("result", "")).upper() == "PASS"]
    req_ids = {str(item.get("requirement_id")) for item in passed if item.get("requirement_id")}
    op_ids = {str(item.get("operation_id")) for item in passed if item.get("operation_id")}
    evidence_types = [str(item.get("evidence_type") or "").lower() for item in passed]
    whitebox_only = [
        item
        for item in passed
        if "whitebox" in str(item.get("evidence_type") or "").lower()
        and not item.get("observed_interface")
    ]
    blackbox = [
        item
        for item in passed
        if str(item.get("evidence_type") or "").lower() in {"blackbox", "top_interface", "interface"}
        or (item.get("observed_interface") and "whitebox" not in str(item.get("evidence_type") or "").lower())
    ]
    return {
        "active_requirements_count": _int_or_zero(event.get("active_requirements_count")) or len(req_ids),
        "covered_requirements_count": len(req_ids),
        "operation_model_entry_count": _int_or_zero(event.get("operation_model_entry_count")) or len(op_ids),
        "covered_operation_count": len(op_ids),
        "readback_checked_count": sum(1 for item in passed if _truthy(item.get("readback_checked")) or item.get("expected_readback")),
        "side_effect_checked_count": sum(1 for item in passed if _truthy(item.get("side_effect_checked")) or item.get("expected_side_effect")),
        "blackbox_check_count": len(blackbox),
        "whitebox_debug_check_count": sum(1 for item in passed if "whitebox_debug" in str(item.get("evidence_type") or "").lower()),
        "whitebox_only_check_count": len(whitebox_only),
        "missing_observed_interface_count": sum(1 for item in passed if not item.get("observed_interface")),
        "evidence_types": sorted({item for item in evidence_types if item}),
    }


def _loop2_semantic_summary(summary: dict[str, Any], transactions: list[dict[str, Any]]) -> dict[str, Any]:
    passed = [item for item in transactions if str(item.get("result", "")).upper() == "PASS"]
    req_ids = {str(item.get("requirement_id")) for item in passed if item.get("requirement_id")}
    op_ids = {str(item.get("operation_id")) for item in passed if item.get("operation_id")}
    scenario_kinds = {str(item.get("scenario_kind")) for item in passed if item.get("scenario_kind")}
    return {
        "covered_requirements_count": len(req_ids),
        "covered_operation_count": len(op_ids),
        "scenario_count": len({str(item.get("scenario_id") or item.get("test_id")) for item in passed if item.get("scenario_id") or item.get("test_id")}),
        "scenario_kind_count": len(scenario_kinds),
        "scenario_kinds": sorted(scenario_kinds),
        "reference_model_check_count": sum(1 for item in passed if _reference_model_declared(item)),
        "monitor_observed_check_count": sum(1 for item in passed if "monitor" in str(item.get("observation_source") or "").lower()),
        "cross_coverage_count": sum(1 for item in passed if item.get("cross_coverage")),
        "assertion_check_count": sum(1 for item in passed if item.get("assertion_id") or item.get("assertions")),
        "negative_test_count": sum(1 for item in passed if "negative" in str(item.get("scenario_kind") or item.get("test_id") or "").lower()),
        "randomized_test_count": sum(1 for item in passed if "random" in str(item.get("scenario_kind") or item.get("test_id") or "").lower()),
        "long_sequence_count": sum(1 for item in passed if "long" in str(item.get("scenario_kind") or item.get("test_id") or "").lower()),
        "coverage_source": summary.get("coverage_source", "not_reported"),
    }


def _reference_model_declared(item: dict[str, Any]) -> bool:
    model = str(item.get("scoreboard_model") or item.get("reference_model") or "").lower()
    return model not in {"", "none", "scenario_code", "scenario-only", "driver_expected"}


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "pass", "checked"}
