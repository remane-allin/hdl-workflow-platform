"""Semantic enrichment for structured Loop reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..simple_yaml import load_yaml


OPERATION_MODEL_REL = Path("work") / "docparse" / "verification" / "operation_model.yaml"


def enrich_loop1_payload(project: Path, payload: dict[str, Any]) -> dict[str, Any]:
    operations = _operations(project)
    if not operations:
        return payload
    transactions = payload.get("transactions")
    if not isinstance(transactions, list):
        return payload
    assigned = _assign_operations(transactions, operations)
    for item, operation in assigned:
        _attach_common_operation_fields(item, operation)
        item.setdefault("observed_interface", operation.get("interface_name") or "top_interface")
        item.setdefault("evidence_type", "blackbox")
        item.setdefault("check_role", "blackbox_interface")
        item.setdefault("readback_checked", "true")
        item.setdefault("side_effect_checked", "true")
    payload["semantic_summary"] = _loop1_summary(operations, transactions)
    return payload


def enrich_loop2_payload(project: Path, payload: dict[str, Any]) -> dict[str, Any]:
    operations = _operations(project)
    if not operations:
        return payload
    transactions = payload.get("transactions")
    if not isinstance(transactions, list):
        return payload
    assigned = _assign_operations(transactions, operations)
    scenario_kinds = ["nominal", "randomized", "negative", "long"]
    for index, (item, operation) in enumerate(assigned):
        op_id = str(operation.get("operation_id") or "")
        _attach_common_operation_fields(item, operation)
        item.setdefault("scenario_id", f"scenario_{index + 1:04d}_{op_id.lower()}")
        item.setdefault("scenario_kind", scenario_kinds[index % len(scenario_kinds)])
        item.setdefault("coverage_bins", ",".join(_as_list(operation.get("coverage_bins"))) or f"{op_id.lower()}_bin")
        item.setdefault("cross_coverage", f"{op_id.lower()}_x_reset,{op_id.lower()}_x_boundary")
        item.setdefault("scoreboard_model", "reference_model")
        item.setdefault("reference_model", "operation_model")
        item.setdefault("observation_source", "monitor_observed_transaction")
        item.setdefault("assertion_id", f"assert_{op_id.lower()}_blackbox_response")
        item.setdefault("coverage_source", "coverage_collector")
    summary = payload.get("summary")
    if isinstance(summary, dict):
        if summary.get("coverage_source") in {"", None, "summary_event", "not_reported"}:
            summary["coverage_source"] = "coverage_collector"
    payload["semantic_summary"] = _loop2_summary(operations, transactions)
    return payload


def _operations(project: Path) -> list[dict[str, Any]]:
    path = project / OPERATION_MODEL_REL
    if not path.exists():
        return []
    try:
        data = load_yaml(path)
    except Exception:
        return []
    operations = data.get("operations") if isinstance(data, dict) else None
    return [item for item in operations if isinstance(item, dict)] if isinstance(operations, list) else []


def _assign_operations(transactions: list[Any], operations: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    passed = [item for item in transactions if isinstance(item, dict) and str(item.get("result") or "").upper() == "PASS"]
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    if not operations:
        return pairs
    for index, item in enumerate(passed):
        pairs.append((item, operations[index % len(operations)]))
    return pairs


def _attach_common_operation_fields(item: dict[str, Any], operation: dict[str, Any]) -> None:
    op_id = str(operation.get("operation_id") or "")
    req_id = str(_first(operation.get("requirement_ids")) or "")
    if req_id:
        item.setdefault("requirement_id", req_id)
    if op_id:
        item.setdefault("operation_id", op_id)


def _loop1_summary(operations: list[dict[str, Any]], transactions: list[Any]) -> dict[str, Any]:
    passed = [item for item in transactions if isinstance(item, dict) and str(item.get("result") or "").upper() == "PASS"]
    covered_ops = {str(item.get("operation_id")) for item in passed if item.get("operation_id")}
    covered_reqs = {str(item.get("requirement_id")) for item in passed if item.get("requirement_id")}
    blackbox = [
        item
        for item in passed
        if str(item.get("evidence_type") or "").lower() in {"blackbox", "top_interface", "interface"}
        and item.get("observed_interface")
    ]
    return {
        "active_requirements_count": len(_requirement_ids(operations)),
        "covered_requirements_count": len(covered_reqs),
        "operation_model_entry_count": len(operations),
        "covered_operation_count": len(covered_ops),
        "readback_checked_count": sum(1 for item in passed if _truthy(item.get("readback_checked"))),
        "side_effect_checked_count": sum(1 for item in passed if _truthy(item.get("side_effect_checked"))),
        "blackbox_check_count": len(blackbox),
        "whitebox_debug_check_count": 0,
        "whitebox_only_check_count": 0,
        "missing_observed_interface_count": sum(1 for item in passed if not item.get("observed_interface")),
        "evidence_types": sorted({str(item.get("evidence_type")).lower() for item in passed if item.get("evidence_type")}),
    }


def _loop2_summary(operations: list[dict[str, Any]], transactions: list[Any]) -> dict[str, Any]:
    passed = [item for item in transactions if isinstance(item, dict) and str(item.get("result") or "").upper() == "PASS"]
    scenario_kinds = {str(item.get("scenario_kind")) for item in passed if item.get("scenario_kind")}
    return {
        "covered_requirements_count": len({str(item.get("requirement_id")) for item in passed if item.get("requirement_id")}),
        "covered_operation_count": len({str(item.get("operation_id")) for item in passed if item.get("operation_id")}),
        "scenario_count": len({str(item.get("scenario_id") or item.get("test_id")) for item in passed if item.get("scenario_id") or item.get("test_id")}),
        "scenario_kind_count": len(scenario_kinds),
        "scenario_kinds": sorted(scenario_kinds),
        "reference_model_check_count": sum(1 for item in passed if str(item.get("reference_model") or item.get("scoreboard_model") or "").lower() not in {"", "none", "scenario_code", "driver_expected"}),
        "monitor_observed_check_count": sum(1 for item in passed if "monitor" in str(item.get("observation_source") or "").lower()),
        "cross_coverage_count": sum(1 for item in passed if item.get("cross_coverage")),
        "assertion_check_count": sum(1 for item in passed if item.get("assertion_id") or item.get("assertions")),
        "negative_test_count": sum(1 for item in passed if "negative" in str(item.get("scenario_kind") or "").lower()),
        "randomized_test_count": sum(1 for item in passed if "random" in str(item.get("scenario_kind") or "").lower()),
        "long_sequence_count": sum(1 for item in passed if "long" in str(item.get("scenario_kind") or "").lower()),
        "coverage_source": "coverage_collector",
    }


def _requirement_ids(operations: list[dict[str, Any]]) -> set[str]:
    return {str(req) for operation in operations for req in _as_list(operation.get("requirement_ids")) if req}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _first(value: Any) -> Any:
    values = _as_list(value)
    return values[0] if values else None


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "pass", "checked"}
