"""Stable source snapshots for generated document rendering."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..project import require_project_instance
from .collect import collect_project_data, sha256_file
from .constants import DOCS_BY_TYPE
from .schemas import SNAPSHOT_SCHEMA_VERSION


def build_snapshot(project_path: Path, doc_type: str, *, change_id: str | None = None) -> dict[str, Any]:
    project = require_project_instance(project_path)
    definition = DOCS_BY_TYPE[doc_type]
    data = collect_project_data(project)
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "doc_type": definition.doc_type,
        "project": project.name,
        "ip_name": data["ip_name"],
        "version": data["version"],
        "status": "DRAFT",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "change_id": change_id,
        "owner_agent": definition.owner_agent,
        "review_agents": list(definition.review_agents),
        "sources": data["sources"],
        "data": data,
    }


def write_snapshot(project_path: Path, snapshot: dict[str, Any]) -> Path:
    project = require_project_instance(project_path)
    definition = DOCS_BY_TYPE[str(snapshot["doc_type"])]
    path = project / definition.snapshot_rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return path


def snapshot_hash(path: Path) -> str:
    return sha256_file(path)
