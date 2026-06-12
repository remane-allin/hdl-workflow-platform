"""Docset integrity checks."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..project import require_project_instance
from .collect import resolve_project_or_workspace_path, sha256_file
from .constants import DOC_DEFINITIONS, DOCSET_MANIFEST_REL, DOCSET_REPORT_REL, DOCS_BY_TYPE


@dataclass(frozen=True)
class DocsetCheckResult:
    ok: bool
    report_path: Path
    errors: list[str]
    warnings: list[str]


def check_docset(
    project_path: Path,
    *,
    level: str = "develop",
    change_id: str | None = None,
    required_docs: list[str] | None = None,
    write_report: bool = True,
) -> DocsetCheckResult:
    project = require_project_instance(project_path)
    required = set(required_docs or [definition.doc_type for definition in DOC_DEFINITIONS])
    errors: list[str] = []
    warnings: list[str] = []

    docset_path = project / DOCSET_MANIFEST_REL
    docset = _read_json(docset_path, errors, label="docset manifest")
    if docset is None:
        errors.append(f"missing docset manifest: {DOCSET_MANIFEST_REL}")
        return _result(project, errors, warnings, write_report)
    if change_id is not None and docset.get("change_id") != change_id:
        errors.append(f"docset change_id mismatch: expected {change_id}, got {docset.get('change_id')}")

    manifest_docs = {str(item.get("doc_type")): item for item in docset.get("documents", []) if isinstance(item, dict)}
    for doc_type in sorted(required):
        definition = DOCS_BY_TYPE[doc_type]
        doc_path = project / definition.doc_rel
        manifest_path = project / definition.manifest_rel
        snapshot_path = project / definition.snapshot_rel
        template_path = resolve_project_or_workspace_path(project, definition.template_rel)

        if doc_type not in manifest_docs:
            errors.append(f"docset manifest missing document: {doc_type}")
        if not doc_path.exists():
            errors.append(f"missing document: {definition.doc_rel}")
            continue
        text = doc_path.read_text(encoding="utf-8", errors="ignore")
        if definition.marker_start not in text or definition.marker_end not in text:
            errors.append(f"{definition.doc_rel} missing required marker(s)")
        for section in definition.required_sections:
            if section not in text:
                errors.append(f"{definition.doc_rel} missing required section: {section}")
        _check_placeholder_policy(definition.doc_rel, text, level, errors, warnings)

        manifest = _read_json(manifest_path, errors, label=f"{doc_type} manifest")
        if manifest is None:
            errors.append(f"missing document manifest: {definition.manifest_rel}")
            continue
        if change_id is not None and manifest.get("change_id") != change_id:
            errors.append(f"{definition.manifest_rel} change_id mismatch: expected {change_id}, got {manifest.get('change_id')}")
        if manifest.get("doc_sha256") != sha256_file(doc_path):
            errors.append(f"{definition.doc_rel} hash does not match manifest")
        if snapshot_path.exists():
            if manifest.get("snapshot_sha256") != sha256_file(snapshot_path):
                errors.append(f"{definition.snapshot_rel} hash does not match manifest")
        else:
            errors.append(f"missing snapshot: {definition.snapshot_rel}")
        if template_path.exists():
            if manifest.get("template_sha256") != sha256_file(template_path):
                errors.append(f"{definition.template_rel} hash does not match manifest")
        else:
            errors.append(f"missing template: {definition.template_rel}")
        if not manifest.get("validation", {}).get("has_required_sections", False):
            errors.append(f"{definition.manifest_rel} validation.has_required_sections is false")
        _check_source_hashes(project, definition.manifest_rel, manifest, errors)

    for item in docset.get("documents", []):
        if not isinstance(item, dict):
            continue
        path = project / str(item.get("path", ""))
        expected = item.get("sha256")
        if path.exists() and expected != sha256_file(path):
            errors.append(f"docset manifest hash mismatch for {item.get('path')}")

    return _result(project, errors, warnings, write_report)


def _check_placeholder_policy(rel: str, text: str, level: str, errors: list[str], warnings: list[str]) -> None:
    if re.search(r"\bNOT_APPLICABLE\b(?!\s*:)", text):
        errors.append(f"{rel} has NOT_APPLICABLE without reason")
    placeholders = re.findall(r"\b(?:TBD|NOT_AVAILABLE|UNKNOWN)\b", text)
    if placeholders:
        if level == "release":
            errors.append(f"{rel} contains release-blocking placeholder(s): {', '.join(sorted(set(placeholders)))}")
        else:
            warnings.append(f"{rel} contains develop placeholder(s): {', '.join(sorted(set(placeholders)))}")


def _check_source_hashes(project: Path, rel: str, manifest: dict, errors: list[str]) -> None:
    for item in manifest.get("source_hashes", []):
        if not isinstance(item, dict):
            continue
        source_rel = str(item.get("path", ""))
        if not source_rel:
            continue
        source = project / source_rel
        if not source.exists():
            errors.append(f"{rel} source missing: {source_rel}")
            continue
        if item.get("sha256") != sha256_file(source):
            errors.append(f"{rel} source drift: {source_rel}")


def _read_json(path: Path, errors: list[str], *, label: str) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"cannot read {label}: {exc}")
        return None
    return data if isinstance(data, dict) else None


def _result(project: Path, errors: list[str], warnings: list[str], write_report: bool) -> DocsetCheckResult:
    report = project / DOCSET_REPORT_REL
    if write_report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(_format_report(project, errors, warnings), encoding="utf-8")
    return DocsetCheckResult(ok=not errors, report_path=report, errors=errors, warnings=warnings)


def _format_report(project: Path, errors: list[str], warnings: list[str]) -> str:
    lines = [
        "# Docset Check",
        "",
        f"- project: {project.name}",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- result: {'PASS' if not errors else 'FAIL'}",
        "",
        "## Errors",
        "",
        *([f"- {item}" for item in errors] or ["- none"]),
        "",
        "## Warnings",
        "",
        *([f"- {item}" for item in warnings] or ["- none"]),
    ]
    return "\n".join(lines) + "\n"
