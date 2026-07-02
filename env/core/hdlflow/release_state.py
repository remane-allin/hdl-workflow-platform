"""Single-source release state adapter for gate and delivery evidence."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .project import require_project_instance


RELEASE_STATE_REL = "work/gates/release_state.json"
SEMANTIC_GATE_STATUS_REL = "work/gates/semantic_gate_status.json"

RELEASE_STATES = {"DRAFT", "DEVELOP_PASS", "RELEASE_CANDIDATE", "RELEASE_PASS", "RELEASE_FAIL"}


@dataclass(frozen=True)
class ReleaseStateResult:
    project: Path
    state: str
    path: Path
    blockers: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return self.state in {"DEVELOP_PASS", "RELEASE_CANDIDATE", "RELEASE_PASS"} and not self.blockers


def update_release_state(project_path: Path, *, level: str = "develop") -> ReleaseStateResult:
    project = require_project_instance(project_path)
    state, blockers, warnings, evidence = evaluate_release_state(project, level=level)
    path = project / RELEASE_STATE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "project": project.name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "level": level,
        "state": state,
        "blockers": blockers,
        "warnings": warnings,
        "evidence": evidence,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return ReleaseStateResult(project=project, state=state, path=path, blockers=blockers, warnings=warnings)


def evaluate_release_state(project: Path, *, level: str = "develop") -> tuple[str, list[str], list[str], dict[str, Any]]:
    blockers: list[str] = []
    warnings: list[str] = []
    evidence: dict[str, Any] = {}

    output_manifest = project / "output/manifest.yaml"
    manifest_text = _read_text(output_manifest)
    evidence["output_manifest"] = _rel(project, output_manifest) if output_manifest.exists() else ""
    if not output_manifest.exists():
        blockers.append("missing output/manifest.yaml")
    else:
        evidence["manifest_final_gate"] = _yaml_value(manifest_text, "final_gate")
        for key in ("loop1_gate", "loop2_gate", "loop3_gate"):
            value = _yaml_value(manifest_text, key)
            evidence[f"manifest_{key}"] = value
            if value and value.upper() != "PASS":
                blockers.append(f"output manifest {key} is {value}, expected PASS for release truth")

    gate_status = _read_json(project / "work/gates/gate_status.json")
    evidence["gate_status"] = gate_status
    if gate_status:
        final_gate = str(gate_status.get("final_gate") or gate_status.get("output") or "").lower()
        if level == "release" and final_gate == "fail":
            blockers.append("work/gates/gate_status.json records final gate fail")
        for key in ("loop1_exit", "loop2_exit", "loop3_exit"):
            value = str(gate_status.get(key) or "").lower()
            if value == "fail":
                blockers.append(f"work/gates/gate_status.json records {key} fail")

    final_audit = project / "output/reports/final_audit_report.md"
    final_text = _read_text(final_audit)
    evidence["final_audit_report"] = _rel(project, final_audit) if final_audit.exists() else ""
    evidence["final_audit_result"] = _report_result(final_text)

    latest_release_report = _latest_gate_report(project, "output_release_*.md")
    release_result = _report_result(_read_text(latest_release_report)) if latest_release_report else ""
    evidence["latest_release_gate_report"] = _rel(project, latest_release_report) if latest_release_report else ""
    evidence["latest_release_gate_result"] = release_result
    if level == "release" and release_result == "FAIL" and evidence.get("final_audit_result") == "PASS":
        blockers.append("final audit PASS conflicts with latest release gate FAIL")

    delivery = project / "output/docs/delivery/delivery_package.md"
    delivery_text = _read_text(delivery)
    evidence["delivery_package"] = _rel(project, delivery) if delivery.exists() else ""
    delivery_result = _report_result(delivery_text) or _delivery_status(delivery_text)
    evidence["delivery_status"] = delivery_result
    if level == "release" and delivery_result in {"DRAFT", "FAIL"} and evidence.get("final_audit_result") == "PASS":
        blockers.append(f"final audit PASS conflicts with delivery package status {delivery_result}")

    semantic = _read_json(project / SEMANTIC_GATE_STATUS_REL)
    evidence["semantic_gate_status"] = semantic
    for gate in semantic.get("gates", []) if isinstance(semantic, dict) else []:
        if not isinstance(gate, dict):
            continue
        if gate.get("mode") == "blocking" and gate.get("status") == "FAIL":
            blockers.append(f"semantic blocking gate failed: {gate.get('name')}")

    if blockers:
        return "RELEASE_FAIL", _unique(blockers), _unique(warnings), evidence

    if level == "release" and evidence.get("final_audit_result") == "PASS":
        return "RELEASE_PASS", [], _unique(warnings), evidence
    if level == "release":
        return "RELEASE_CANDIDATE", [], _unique(warnings), evidence
    if all(str(evidence.get(f"manifest_{key}") or "").upper() == "PASS" for key in ("loop1_gate", "loop2_gate", "loop3_gate")):
        return "DEVELOP_PASS", [], _unique(warnings), evidence
    return "DRAFT", [], _unique(warnings), evidence


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _read_text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _yaml_value(text: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}:\s*(.+?)\s*$", text)
    return match.group(1).strip() if match else ""


def _report_result(text: str) -> str:
    match = re.search(r"(?mi)^-\s*result:\s*(PASS|FAIL|BLOCKED|DRAFT)\s*$", text)
    return match.group(1).upper() if match else ""


def _delivery_status(text: str) -> str:
    match = re.search(r"(?mi)^-\s*status:\s*(PASS|FAIL|DRAFT|RELEASE_PASS|RELEASE_FAIL)\s*$", text)
    return match.group(1).upper() if match else ""


def _latest_gate_report(project: Path, pattern: str) -> Path | None:
    root = project / "output/reports/gates"
    if not root.exists():
        return None
    matches = sorted(root.glob(pattern))
    return matches[-1] if matches else None


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _rel(project: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")
