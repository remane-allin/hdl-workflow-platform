from __future__ import annotations

import sqlite3
import json
import re
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    version TEXT NOT NULL,
    source_path TEXT,
    parsed_path TEXT,
    tool_version TEXT
);
CREATE INDEX IF NOT EXISTS documents_title_idx ON documents(title);
"""


def open_library(workflow_root: Path) -> sqlite3.Connection:
    database = workflow_root / "knowledge" / "library.sqlite"
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    connection.executescript(SCHEMA)
    return connection


def register_document(
    workflow_root: Path,
    *,
    document_id: str,
    title: str,
    version: str,
    source_path: str = "",
    parsed_path: str = "",
    tool_version: str = "",
) -> None:
    if Path(source_path).is_absolute() or Path(parsed_path).is_absolute():
        raise ValueError("knowledge paths must be Workflow-relative")
    connection = open_library(workflow_root)
    try:
        connection.execute(
            "INSERT OR REPLACE INTO documents VALUES (?, ?, ?, ?, ?, ?)",
            (document_id, title, version, source_path, parsed_path, tool_version),
        )
        connection.commit()
    finally:
        connection.close()


def query(workflow_root: Path, text: str, *, tool_version: str = "") -> list[dict[str, str]]:
    sql = "SELECT document_id,title,version,source_path,parsed_path,tool_version FROM documents WHERE title LIKE ?"
    values: list[str] = [f"%{text}%"]
    if tool_version:
        sql += " AND (tool_version = ? OR tool_version = '')"
        values.append(tool_version)
    sql += " ORDER BY title"
    connection = open_library(workflow_root)
    try:
        rows = connection.execute(sql, values).fetchall()
    finally:
        connection.close()
    names = ("document_id", "title", "version", "source_path", "parsed_path", "tool_version")
    return [dict(zip(names, row)) for row in rows]


def _stable_id(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9._-]+", "_", value.lower()).strip("_")
    if not normalized:
        raise ValueError("knowledge document identity is empty")
    return normalized


def _source_candidates(source_root: Path) -> dict[str, list[Path]]:
    candidates: dict[str, list[Path]] = {}
    if not source_root.exists():
        return candidates
    for path in source_root.rglob("*"):
        if path.is_dir():
            candidates.setdefault(path.name.casefold(), []).append(path)
        elif path.is_file():
            candidates.setdefault(path.stem.casefold(), []).append(path)
    return candidates


def _document_row(
    workflow_root: Path,
    metadata_path: Path,
    metadata: dict[str, Any],
    candidates: dict[str, list[Path]],
) -> tuple[str, str, str, str, str, str]:
    relative_parent = metadata_path.parent.relative_to(workflow_root / "knowledge" / "parsed")
    identity = str(metadata.get("doc_id") or metadata.get("document_id") or relative_parent.as_posix())
    title = str(metadata.get("title") or metadata.get("folder_name") or metadata_path.parent.name)
    tool_version = str(metadata.get("tool_version") or "")
    version = str(metadata.get("version") or tool_version or "unspecified")
    source_path = ""
    matches = candidates.get(metadata_path.parent.name.casefold(), [])
    if len(matches) == 1:
        source_path = matches[0].relative_to(workflow_root).as_posix()
    parsed_path = metadata_path.parent.relative_to(workflow_root).as_posix()
    return (_stable_id(identity), title, version, source_path, parsed_path, tool_version)


def refresh_library(workflow_root: Path) -> int:
    """Replace the metadata catalog from the one current parsed/source tree."""
    parsed_root = workflow_root / "knowledge" / "parsed"
    source_root = workflow_root / "knowledge" / "sources"
    candidates = _source_candidates(source_root)
    selected: dict[str, tuple[int, tuple[str, str, str, str, str, str]]] = {}
    for metadata_path in sorted(parsed_root.rglob("metadata.json")):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(metadata, dict):
            raise ValueError(f"knowledge metadata must be an object: {metadata_path}")
        row = _document_row(workflow_root, metadata_path, metadata, candidates)
        depth = len(metadata_path.parent.relative_to(parsed_root).parts)
        previous = selected.get(row[0])
        if previous is None or depth < previous[0]:
            selected[row[0]] = (depth, row)
        elif depth == previous[0] and row != previous[1]:
            raise ValueError(f"knowledge document identity is ambiguous: {row[0]}")
    rows = [item[1] for item in sorted(selected.values(), key=lambda item: item[1][0])]
    connection = open_library(workflow_root)
    try:
        connection.execute("DELETE FROM documents")
        connection.executemany("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?)", rows)
        connection.commit()
    finally:
        connection.close()
    return len(rows)
