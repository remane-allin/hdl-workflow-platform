"""Compile the single active requirement baseline for semantic gates."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .project import require_project_instance
from .simple_yaml import load_yaml


ACTIVE_REQUIREMENTS_REL = "work/docparse/frontdoor/baseline/active_requirements.yaml"
ACTIVE_ACCEPTANCE_REL = "work/docparse/frontdoor/baseline/active_acceptance_criteria.yaml"
EVIDENCE_INDEX_REL = "work/docparse/frontdoor/baseline/evidence_index.yaml"
REQUIREMENT_LIFECYCLE_REL = "work/docparse/frontdoor/baseline/requirement_lifecycle.yaml"

REQUIREMENT_SOURCE_RELS = [
    "work/docparse/frontdoor/srs.yaml",
    "work/docparse/frontdoor/baseline/srs.yaml",
    "work/docparse/frontdoor/generated/active_srs.generated.yaml",
    "work/docparse/req_decompose/requirements.json",
]

ACCEPTANCE_SOURCE_RELS = [
    "work/docparse/frontdoor/acceptance_criteria.yaml",
    "work/docparse/frontdoor/baseline/acceptance_criteria.yaml",
]

LIFECYCLE_STATES = {
    "proposed",
    "analyzed",
    "designed",
    "implementation_ready",
    "verified",
    "released",
    "ambiguous",
    "assumption_backed",
    "deferred",
    "out_of_scope",
}


@dataclass(frozen=True)
class RequirementsCompileResult:
    project: Path
    requirement_count: int
    acceptance_count: int
    evidence_count: int
    written: list[Path]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return self.requirement_count > 0


def compile_requirements(project_path: Path) -> RequirementsCompileResult:
    """Write active requirement, acceptance, evidence, and lifecycle baselines."""

    project = require_project_instance(project_path)
    warnings: list[str] = []
    requirements = _collect_requirements(project, warnings)
    acceptance = _collect_acceptance(project, requirements, warnings)
    evidence = _build_evidence_index(project, requirements)
    lifecycle = _build_lifecycle(requirements)

    written = [
        _write_yaml(project / ACTIVE_REQUIREMENTS_REL, {"schema_version": 1, "requirements": requirements}),
        _write_yaml(project / ACTIVE_ACCEPTANCE_REL, {"schema_version": 1, "criteria": acceptance}),
        _write_yaml(project / EVIDENCE_INDEX_REL, {"schema_version": 1, "evidence": evidence}),
        _write_yaml(project / REQUIREMENT_LIFECYCLE_REL, {"schema_version": 1, "requirements": lifecycle}),
    ]
    return RequirementsCompileResult(
        project=project,
        requirement_count=len(requirements),
        acceptance_count=len(acceptance),
        evidence_count=len(evidence),
        written=written,
        warnings=warnings,
    )


def load_active_requirements(project_path: Path) -> list[dict[str, Any]]:
    project = require_project_instance(project_path)
    return _items_from_file(project / ACTIVE_REQUIREMENTS_REL, "requirements")


def load_active_acceptance(project_path: Path) -> list[dict[str, Any]]:
    project = require_project_instance(project_path)
    return _items_from_file(project / ACTIVE_ACCEPTANCE_REL, "criteria")


def load_evidence_index(project_path: Path) -> list[dict[str, Any]]:
    project = require_project_instance(project_path)
    return _items_from_file(project / EVIDENCE_INDEX_REL, "evidence")


def _collect_requirements(project: Path, warnings: list[str]) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for rel in REQUIREMENT_SOURCE_RELS:
        path = project / rel
        if not path.exists():
            continue
        payload = _read_structured(path, warnings)
        for raw in _find_requirement_records(payload):
            row = _normalize_requirement(project, rel, raw)
            rows[row["requirement_id"]] = {**rows.get(row["requirement_id"], {}), **row}

    intake_root = project / "work/docparse/frontdoor/intake/merged"
    if intake_root.exists():
        for path in sorted(intake_root.glob("*.yaml")) + sorted(intake_root.glob("*.yml")) + sorted(intake_root.glob("*.json")):
            payload = _read_structured(path, warnings)
            rel = _rel(project, path)
            for raw in _find_requirement_records(payload):
                row = _normalize_requirement(project, rel, raw)
                rows[row["requirement_id"]] = {**rows.get(row["requirement_id"], {}), **row}

    return sorted(rows.values(), key=lambda item: item["requirement_id"])


def _collect_acceptance(project: Path, requirements: list[dict[str, Any]], warnings: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rel in ACCEPTANCE_SOURCE_RELS:
        path = project / rel
        if not path.exists():
            continue
        payload = _read_structured(path, warnings)
        for raw in _find_acceptance_records(payload):
            row = _normalize_acceptance(raw)
            if row:
                rows.append(row)

    by_req = {str(row.get("requirement_id")) for row in rows if row.get("requirement_id")}
    for req in requirements:
        req_id = str(req.get("requirement_id"))
        req_acceptance = req.get("acceptance_criteria")
        if req_id in by_req:
            continue
        if isinstance(req_acceptance, list) and req_acceptance:
            for index, text in enumerate(req_acceptance, start=1):
                rows.append(_synthetic_acceptance(req_id, index, text))
        elif isinstance(req_acceptance, str) and req_acceptance.strip():
            rows.append(_synthetic_acceptance(req_id, 1, req_acceptance))
        else:
            rows.append(_generated_acceptance(req))
    return rows


def _build_evidence_index(project: Path, requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for req in requirements:
        refs = _as_list(req.get("source_refs")) or _as_list(req.get("source_ref"))
        if not refs:
            continue
        for index, ref in enumerate(refs, start=1):
            source_path = str((ref.get("path") if isinstance(ref, dict) else ref) or "").strip()
            parsed_path = str((ref.get("parsed_path") if isinstance(ref, dict) else "") or "").strip()
            source_path = _resolve_existing_source_path(project, source_path)
            parsed_path = _resolve_existing_source_path(project, parsed_path)
            rows.append(
                {
                    "requirement_id": req["requirement_id"],
                    "evidence_id": f"{req['requirement_id']}-E{index:03d}",
                    "source_document": _ref_value(ref, "document", source_path),
                    "source_path": source_path,
                    "parsed_path": parsed_path,
                    "source_page_or_section": _ref_value(ref, "section", _ref_value(ref, "line", "")),
                    "analysis_unit": _ref_value(ref, "analysis_unit", ""),
                    "evidence_hash": _evidence_hash(project, source_path, parsed_path),
                    "confidence": req.get("confidence") or "unknown",
                    "open_questions": [],
                }
            )
    return rows


def _ref_value(ref: Any, key: str, default: str) -> str:
    if not isinstance(ref, dict):
        return default
    value = ref.get(key)
    return str(value if value is not None else default).strip()


def _resolve_existing_source_path(project: Path, rel: str) -> str:
    if not rel or rel.startswith(("http://", "https://")):
        return rel
    path = project / rel
    if path.exists():
        return rel
    if "mineru_extract" not in rel.replace("\\", "/"):
        return rel
    parent = path.parent
    if not parent.exists():
        return rel
    wanted = _path_match_key(path.stem)
    candidates = sorted(item for item in parent.glob(f"*{path.suffix}") if item.is_file())
    for candidate in candidates:
        candidate_key = _path_match_key(candidate.stem)
        if wanted and (wanted in candidate_key or candidate_key in wanted):
            return _rel(project, candidate)
    wanted_tokens = {token for token in re.split(r"[^a-z0-9]+", path.stem.lower()) if len(token) >= 4}
    for candidate in candidates:
        candidate_tokens = {token for token in re.split(r"[^a-z0-9]+", candidate.stem.lower()) if len(token) >= 4}
        if wanted_tokens & candidate_tokens:
            return _rel(project, candidate)
    return rel


def _path_match_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _build_lifecycle(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for req in requirements:
        state = str(req.get("lifecycle_state") or req.get("status") or "proposed").lower()
        if state not in LIFECYCLE_STATES:
            state = "proposed"
        rows.append(
            {
                "requirement_id": req["requirement_id"],
                "lifecycle_state": state,
                "status": req.get("status") or state,
                "change_id": req.get("change_id") or "",
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
    return rows


def _normalize_requirement(project: Path, rel: str, raw: dict[str, Any]) -> dict[str, Any]:
    req_id = _first(raw, "requirement_id", "req_id", "id", "name")
    if not req_id:
        req_id = "REQ-" + hashlib.sha1(json.dumps(raw, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:8].upper()
    source_refs = _normalize_source_refs(raw.get("source_refs") or raw.get("source_ref") or raw.get("evidence_refs") or raw.get("evidence_ref"))
    if not source_refs:
        source_refs = [{"path": rel}]
    text = str(_first(raw, "full_text", "requirement_text", "text", "description", "title") or "")
    row = {
        "requirement_id": str(req_id),
        "title": str(_first(raw, "title", "summary", "name") or req_id),
        "full_text": text,
        "source_refs": source_refs,
        "priority": str(raw.get("priority") or "normal"),
        "scope": str(raw.get("scope") or "project"),
        "status": str(raw.get("status") or "proposed"),
        "lifecycle_state": str(raw.get("lifecycle_state") or raw.get("status") or "proposed").lower(),
        "confidence": str(raw.get("confidence") or "unknown"),
        "functional_domain": str(raw.get("functional_domain") or raw.get("domain") or "unassigned"),
        "acceptance_criteria": raw.get("acceptance_criteria") or raw.get("acceptance") or [],
        "change_id": str(raw.get("change_id") or ""),
        "derived_from": raw.get("derived_from") or rel,
    }
    row["hash"] = hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return row


def _normalize_acceptance(raw: dict[str, Any]) -> dict[str, Any] | None:
    req_id = _first(raw, "requirement_id", "req_id", "target_requirement_id")
    text = _first(raw, "criterion", "criteria", "acceptance_criterion", "text", "description")
    if not req_id or not text:
        return None
    return {
        "criterion_id": str(_first(raw, "criterion_id", "id", "name") or f"{req_id}-AC001"),
        "requirement_id": str(req_id or ""),
        "criterion": str(text or ""),
        "verification_methods": _as_list(raw.get("verification_methods") or raw.get("verification_method") or raw.get("methods") or raw.get("method")),
        "evidence_targets": _as_list(raw.get("evidence_targets") or raw.get("evidence") or raw.get("evidence_target")),
        "waiver": raw.get("waiver") or "",
    }


def _synthetic_acceptance(requirement_id: str, index: int, text: object) -> dict[str, Any]:
    return {
        "criterion_id": f"{requirement_id}-AC{index:03d}",
        "requirement_id": requirement_id,
        "criterion": str(text),
        "verification_methods": [],
        "evidence_targets": [],
        "waiver": "",
    }


def _generated_acceptance(requirement: dict[str, Any]) -> dict[str, Any]:
    req_id = str(requirement.get("requirement_id") or "REQ-UNKNOWN")
    text = str(requirement.get("full_text") or requirement.get("title") or req_id).strip()
    return {
        "criterion_id": f"{req_id}-AC001",
        "requirement_id": req_id,
        "criterion": f"Top-level observable behavior satisfies active requirement: {text}",
        "verification_methods": ["loop1_blackbox_tb", "loop2_uvm_reference_model", "loop3_fpga_validation"],
        "evidence_targets": [
            "output/reports/loop1/loop1_report.json",
            "output/reports/loop2/loop2_report.json",
            "output/reports/loop3/loop3_exit_report.md",
        ],
        "waiver": "",
        "generated_from_requirement_text": True,
    }


def _find_requirement_records(payload: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in _walk(payload):
        if not isinstance(item, dict):
            continue
        keys = set(item)
        record_id = str(_first(item, "requirement_id", "req_id", "id", "name") or "")
        if _looks_like_acceptance_id(record_id):
            continue
        if keys & {"requirement_id", "req_id"}:
            records.append(item)
        elif "id" in item and keys & {"requirement_text", "full_text", "text", "description", "acceptance_criteria", "source_refs", "evidence_refs"}:
            records.append(item)
    return records


def _find_acceptance_records(payload: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in _walk(payload):
        if not isinstance(item, dict):
            continue
        keys = set(item)
        if keys & {"requirement_id", "req_id", "target_requirement_id"} and keys & {"criterion", "acceptance_criterion", "text", "description", "method", "verification_methods"}:
            records.append(item)
    return records


def _normalize_source_refs(value: Any) -> list[Any]:
    refs: list[Any] = []
    for ref in _as_list(value):
        if isinstance(ref, dict):
            if "path" in ref or "source_path" in ref:
                refs.append({"path": ref.get("path") or ref.get("source_path"), **{key: item for key, item in ref.items() if key not in {"path", "source_path"}}})
            elif len(ref) == 1:
                key, item = next(iter(ref.items()))
                refs.extend(_normalize_source_refs(f"{key}:{item}"))
            else:
                refs.append(ref)
            continue
        text = str(ref).strip()
        if not text:
            continue
        match = re.match(r"^(.+):(\d+)$", text)
        if match:
            refs.append({"path": match.group(1), "line": match.group(2), "section": f"line {match.group(2)}"})
        else:
            refs.append({"path": text})
    return refs


def _looks_like_acceptance_id(value: str) -> bool:
    return value.upper().startswith(("AC-", "ACC-", "ACCEPT-"))


def _walk(value: Any) -> list[Any]:
    found = [value]
    if isinstance(value, dict):
        for child in value.values():
            found.extend(_walk(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk(child))
    return found


def _items_from_file(path: Path, key: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = _read_structured(path, [])
    items = payload.get(key, []) if isinstance(payload, dict) else []
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _read_structured(path: Path, warnings: list[str]) -> Any:
    try:
        if path.suffix.lower() == ".json":
            return json.loads(path.read_text(encoding="utf-8"))
        return load_yaml(path)
    except Exception as exc:
        warnings.append(f"could not parse {_path_text(path)}: {exc}")
        return {}


def _write_yaml(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump_yaml(data), encoding="utf-8")
    return path


def _dump_yaml(value: Any, indent: int = 0) -> str:
    lines: list[str] = []
    prefix = " " * indent
    if isinstance(value, dict):
        for key, child in value.items():
            if child == []:
                lines.append(f"{prefix}{key}: []")
                continue
            if child == {}:
                lines.append(f"{prefix}{key}: {{}}")
                continue
            if isinstance(child, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.append(_dump_yaml(child, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {_scalar(child)}")
    elif isinstance(value, list):
        if not value:
            lines.append(f"{prefix}[]")
        for item in value:
            if isinstance(item, dict):
                lines.append(f"{prefix}-")
                lines.append(_dump_yaml(item, indent + 2))
            elif isinstance(item, list):
                lines.append(f"{prefix}-")
                lines.append(_dump_yaml(item, indent + 2))
            else:
                lines.append(f"{prefix}- {_scalar(item)}")
    else:
        lines.append(f"{prefix}{_scalar(value)}")
    return "\n".join(line for line in lines if line != "") + ("\n" if indent == 0 else "")


def _scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "":
        return '""'
    safe = all(ch.isalnum() or ch in "._-/:" for ch in text)
    if safe and text.lower() not in {"true", "false", "null", "none"}:
        return text
    return json.dumps(text, ensure_ascii=False)


def _first(raw: dict[str, Any], *names: str) -> Any:
    for name in names:
        value = raw.get(name)
        if value not in (None, ""):
            return value
    return None


def _as_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    return value if isinstance(value, list) else [value]


def _evidence_hash(project: Path, *rels: str) -> str:
    hasher = hashlib.sha256()
    for rel in rels:
        if not rel or str(rel).startswith(("http://", "https://")):
            continue
        path = project / rel
        if path.is_file():
            hasher.update(path.read_bytes())
    return hasher.hexdigest() if hasher.digest() != hashlib.sha256().digest() else ""


def _rel(project: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _path_text(path: Path) -> str:
    return str(path).replace("\\", "/")
