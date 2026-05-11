"""Local SQLite-backed library index for agent retrieval."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .simple_yaml import load_yaml


INDEX_SPECS = [
    ("flow_index.yaml", "flows", "flow"),
    ("command_index.yaml", "commands", "command"),
    ("template_index.yaml", "templates", "template"),
    ("document_index.yaml", "documents", "document"),
    ("connection_index.yaml", "connections", "connection"),
    ("diagnostic_index.yaml", "diagnostics", "diagnostic"),
]


@dataclass(frozen=True)
class LibraryEntry:
    id: str
    kind: str
    domain: str
    title: str
    workflow_id: str
    workflow_node: str
    tool: str
    vendor: str
    stage: str
    short_description: str
    detail_path: str
    tags: str
    source_index: str


def build_library(workspace: Path) -> Path:
    workspace = workspace.resolve()
    library_root = workspace / "library"
    schema = library_root / "schema" / "library_schema.sql"
    index_root = library_root / "indexes"
    db_path = library_root / ".local" / "library.sqlite"

    if not schema.is_file():
        raise FileNotFoundError(f"missing library schema: {schema}")
    if not index_root.is_dir():
        raise FileNotFoundError(f"missing library indexes: {index_root}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema.read_text(encoding="utf-8"))
        for index_name, root_key, kind in INDEX_SPECS:
            index_path = index_root / index_name
            if not index_path.exists():
                continue
            data = load_yaml(index_path)
            entries = data.get(root_key, {})
            if not isinstance(entries, dict):
                raise ValueError(f"{index_path} root '{root_key}' must be a mapping")
            for entry_id, raw in entries.items():
                if not isinstance(raw, dict):
                    raise ValueError(f"{index_path}:{entry_id} must be a mapping")
                entry = _entry_from_mapping(str(entry_id), kind, raw, index_name)
                conn.execute(
                    """
                    INSERT INTO library_entries (
                        id, kind, domain, title, workflow_id, workflow_node,
                        tool, vendor, stage, short_description, detail_path,
                        tags, source_index
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry.id,
                        entry.kind,
                        entry.domain,
                        entry.title,
                        entry.workflow_id,
                        entry.workflow_node,
                        entry.tool,
                        entry.vendor,
                        entry.stage,
                        entry.short_description,
                        entry.detail_path,
                        entry.tags,
                        entry.source_index,
                    ),
                )
    return db_path


def query_toc(
    workspace: Path,
    *,
    flow: str | None = None,
    node: str | None = None,
    tool: str | None = None,
    stage: str | None = None,
    domain: str | None = None,
) -> list[LibraryEntry]:
    db_path = _ensure_db(workspace)
    clauses: list[str] = []
    params: list[str] = []

    if flow:
        clauses.append("(id = ? OR workflow_id = ?)")
        params.extend([flow, flow])
    if node:
        clauses.append("workflow_node = ?")
        params.append(node)
    if tool:
        clauses.append("(tool = ? OR tool = '')")
        params.append(tool)
    if stage:
        clauses.append("(stage = ? OR stage = '')")
        params.append(stage)
    if domain:
        clauses.append("domain = ?")
        params.append(domain)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT id, kind, domain, title, workflow_id, workflow_node, tool,
               vendor, stage, short_description, detail_path, tags, source_index
        FROM library_entries
        {where}
        ORDER BY kind, id
    """
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_entry_from_row(row) for row in rows]


def get_entry(workspace: Path, entry_id: str, *, expected_kind: str | None = None) -> tuple[LibraryEntry, str]:
    db_path = _ensure_db(workspace)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT id, kind, domain, title, workflow_id, workflow_node, tool,
                   vendor, stage, short_description, detail_path, tags, source_index
            FROM library_entries
            WHERE id = ?
            """,
            (entry_id,),
        ).fetchone()
    if row is None:
        raise KeyError(f"library entry not found: {entry_id}")
    entry = _entry_from_row(row)
    if expected_kind and entry.kind != expected_kind:
        raise ValueError(f"library entry '{entry_id}' is kind '{entry.kind}', expected '{expected_kind}'")

    detail = ""
    if entry.detail_path:
        path = workspace.resolve() / "library" / entry.detail_path
        if path.is_file():
            detail = path.read_text(encoding="utf-8")
        else:
            detail = f"detail file missing: {entry.detail_path}"
    return entry, detail


def query_diagnostics(workspace: Path, *, tool: str | None = None, text: str | None = None) -> list[LibraryEntry]:
    entries = [entry for entry in query_toc(workspace, tool=tool, domain="fpga") if entry.kind == "diagnostic"]
    if not text:
        return entries

    needle = text.lower()
    scored: list[tuple[int, LibraryEntry]] = []
    for entry in entries:
        detail = get_entry(workspace, entry.id)[1].lower()
        haystack = " ".join(
            [
                entry.id,
                entry.title,
                entry.short_description,
                entry.tags,
                detail,
            ]
        ).lower()
        score = sum(1 for token in _tokens(needle) if token in haystack)
        if score:
            scored.append((score, entry))
    scored.sort(key=lambda item: (-item[0], item[1].id))
    return [entry for _, entry in scored] or entries


def format_toc(entries: list[LibraryEntry]) -> list[str]:
    if not entries:
        return ["no matching library entries"]
    lines = ["id | kind | title | short_description"]
    lines.append("--- | --- | --- | ---")
    for entry in entries:
        lines.append(f"{entry.id} | {entry.kind} | {entry.title} | {entry.short_description}")
    return lines


def format_detail(entry: LibraryEntry, detail: str) -> list[str]:
    lines = [
        f"id: {entry.id}",
        f"kind: {entry.kind}",
        f"domain: {entry.domain}",
        f"title: {entry.title}",
        f"workflow_id: {entry.workflow_id}",
        f"workflow_node: {entry.workflow_node}",
        f"tool: {entry.tool}",
        f"vendor: {entry.vendor}",
        f"stage: {entry.stage}",
        f"tags: {entry.tags}",
        f"detail_path: {entry.detail_path}",
        "",
        detail.rstrip(),
    ]
    return lines


def _entry_from_mapping(entry_id: str, kind: str, raw: dict[str, Any], source_index: str) -> LibraryEntry:
    return LibraryEntry(
        id=entry_id,
        kind=kind,
        domain=_as_text(raw.get("domain")),
        title=_as_text(raw.get("title", entry_id)),
        workflow_id=_as_text(raw.get("workflow_id")),
        workflow_node=_as_text(raw.get("workflow_node")),
        tool=_as_text(raw.get("tool")),
        vendor=_as_text(raw.get("vendor")),
        stage=_as_text(raw.get("stage")),
        short_description=_as_text(raw.get("short_description")),
        detail_path=_as_text(raw.get("detail_path")),
        tags=_as_tags(raw.get("tags")),
        source_index=source_index,
    )


def _entry_from_row(row: tuple[Any, ...]) -> LibraryEntry:
    return LibraryEntry(*(str(value or "") for value in row))


def _ensure_db(workspace: Path) -> Path:
    db_path = workspace.resolve() / "library" / ".local" / "library.sqlite"
    if not db_path.exists():
        return build_library(workspace)
    return db_path


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return ""
    return str(value)


def _as_tags(value: Any) -> str:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def _tokens(text: str) -> list[str]:
    normalized = "".join(char.lower() if char.isalnum() else " " for char in text)
    return [token for token in normalized.split() if len(token) >= 3]
