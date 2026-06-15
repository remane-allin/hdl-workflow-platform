"""Manifest generation for HDL document sets."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..project import require_project_instance
from ..requirements_frontend import DOC_PROJECTION_REL
from .collect import resolve_project_or_workspace_path, sha256_file
from .constants import DOC_DEFINITIONS, DOCSET_MANIFEST_REL, DOCS_BY_TYPE, DocDefinition
from .schemas import DOCSET_SCHEMA_VERSION, DOCUMENT_MANIFEST_SCHEMA_VERSION


def build_document_manifest(
    project_path: Path,
    definition: DocDefinition,
    *,
    snapshot_path: Path,
    doc_path: Path,
    change_id: str | None,
) -> dict[str, Any]:
    project = require_project_instance(project_path)
    template_path = resolve_project_or_workspace_path(project, definition.template_rel)
    projection_path = project / DOC_PROJECTION_REL
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    doc_text = doc_path.read_text(encoding="utf-8")
    return {
        "schema_version": DOCUMENT_MANIFEST_SCHEMA_VERSION,
        "doc_type": definition.doc_type,
        "doc_path": definition.doc_rel,
        "snapshot_path": definition.snapshot_rel,
        "template_path": definition.template_rel,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generator": f"hdlflow.docgen.{definition.doc_type}",
        "status": "DRAFT",
        "change_id": change_id,
        "doc_sha256": sha256_file(doc_path),
        "snapshot_sha256": sha256_file(snapshot_path),
        "template_sha256": sha256_file(template_path) if template_path.exists() else "MISSING",
        "projection_path": DOC_PROJECTION_REL,
        "projection_sha256": sha256_file(projection_path) if projection_path.exists() else "MISSING",
        "markers": [definition.marker_start, definition.marker_end],
        "source_hashes": snapshot.get("sources", []),
        "validation": {
            "has_required_sections": all(section in doc_text for section in definition.required_sections),
            "has_tbd": "TBD" in doc_text,
            "release_ready": "TBD" not in doc_text and "NOT_AVAILABLE" not in doc_text and "UNKNOWN" not in doc_text,
        },
    }


def write_document_manifest(project_path: Path, manifest: dict[str, Any]) -> Path:
    project = require_project_instance(project_path)
    definition = DOCS_BY_TYPE[str(manifest["doc_type"])]
    path = project / definition.manifest_rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_docset_manifest(project_path: Path, *, change_id: str | None = None) -> Path:
    project = require_project_instance(project_path)
    documents = []
    for definition in DOC_DEFINITIONS:
        doc_path = project / definition.doc_rel
        documents.append(
            {
                "doc_type": definition.doc_type,
                "path": definition.doc_rel,
                "manifest": definition.manifest_rel,
                "sha256": sha256_file(doc_path) if doc_path.exists() else "MISSING",
                "required": True,
            }
        )
    payload = {
        "schema_version": DOCSET_SCHEMA_VERSION,
        "docset_version": 1,
        "project": project.name,
        "ip_name": project.name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "status": "DRAFT",
        "change_id": change_id,
        "documents": documents,
    }
    path = project / DOCSET_MANIFEST_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return path
