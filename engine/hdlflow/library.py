"""Local SQLite-backed library index for agent retrieval."""

from __future__ import annotations

import sqlite3
import json
import shutil
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


LIBRARY_TEMP_DIR_NAMES = {
    "mineru_raw",
    "mineru_extract",
    "text_raw",
    "images",
}

LIBRARY_TEMP_ROOTS = [
    "library/work",
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
        _import_fpga_io_tables(conn, library_root)
        _import_fpga_schematics(conn, library_root)
        _import_fpga_hardware_guides(conn, library_root)
        _import_software_tcl_library(conn, library_root)
    return db_path


def cleanup_library_temp_outputs(workspace: Path) -> list[Path]:
    workspace = workspace.resolve()
    removed: list[Path] = []
    library_root = workspace / "library"
    if not library_root.exists():
        return removed

    candidates: list[Path] = []
    for rel_root in LIBRARY_TEMP_ROOTS:
        candidates.append(workspace / rel_root)
    parsed_root = library_root / "parsed"
    if parsed_root.is_dir():
        for path in parsed_root.rglob("*"):
            if path.is_dir() and path.name in LIBRARY_TEMP_DIR_NAMES:
                candidates.append(path)

    for candidate in sorted(set(candidates), key=lambda item: len(item.parts), reverse=True):
        if not candidate.exists():
            continue
        resolved = candidate.resolve()
        if not _is_relative_to(resolved, workspace):
            raise ValueError(f"refusing to remove path outside workspace: {resolved}")
        if resolved == workspace or resolved == library_root:
            raise ValueError(f"refusing to remove protected path: {resolved}")
        shutil.rmtree(resolved)
        removed.append(resolved)
    return removed


def finalize_library_database(workspace: Path) -> tuple[Path, list[Path]]:
    db_path = build_library(workspace)
    removed = cleanup_library_temp_outputs(workspace)
    return db_path, removed


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


def query_fpga_io_pins(
    workspace: Path,
    *,
    table_id: str | None = None,
    connector: str | None = None,
    signal: str | None = None,
    bank: str | None = None,
    category: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    db_path = _ensure_db(workspace)
    clauses: list[str] = []
    params: list[Any] = []
    if table_id:
        clauses.append("table_id = ?")
        params.append(table_id)
    if connector:
        clauses.append("connector = ?")
        params.append(connector)
    if signal:
        clauses.append("signal_name LIKE ?")
        params.append(f"%{signal}%")
    if bank:
        clauses.append("bank = ?")
        params.append(bank)
    if category:
        clauses.append("category = ?")
        params.append(category)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT table_id, connector, connector_pin, signal_name, zynq_pin,
               raw_zynq_pin, bank, voltage, category, source_file
        FROM fpga_io_pins
        {where}
        ORDER BY table_id, connector, connector_pin
        LIMIT ?
    """
    params.append(limit)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    keys = [
        "table_id",
        "connector",
        "connector_pin",
        "signal_name",
        "zynq_pin",
        "raw_zynq_pin",
        "bank",
        "voltage",
        "category",
        "source_file",
    ]
    return [dict(zip(keys, row)) for row in rows]


def query_fpga_schematic_nets(
    workspace: Path,
    *,
    schematic_id: str | None = None,
    net: str | None = None,
    interface: str | None = None,
    category: str | None = None,
    connector: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    db_path = _ensure_db(workspace)
    clauses: list[str] = []
    params: list[Any] = []
    if schematic_id:
        clauses.append("schematic_id = ?")
        params.append(schematic_id)
    if net:
        clauses.append("(net_name LIKE ? OR linked_io_signal LIKE ? OR normalized_name LIKE ?)")
        params.extend([f"%{net}%", f"%{net}%", f"%{_normalize_signal(net)}%"])
    if interface:
        clauses.append("interface = ?")
        params.append(interface)
    if category:
        clauses.append("category = ?")
        params.append(category)
    if connector:
        clauses.append("(schematic_connector = ? OR core_connector = ?)")
        params.extend([connector, connector])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT schematic_id, net_name, interface, category,
               schematic_connector, schematic_connector_pin,
               core_connector, core_connector_pin, zynq_pin,
               bank, voltage, linked_io_signal, source_sheet,
               confidence, notes
        FROM fpga_schematic_nets
        {where}
        ORDER BY schematic_id, source_sheet, interface, net_name,
                 schematic_connector, schematic_connector_pin
        LIMIT ?
    """
    params.append(limit)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    keys = [
        "schematic_id",
        "net_name",
        "interface",
        "category",
        "schematic_connector",
        "schematic_connector_pin",
        "core_connector",
        "core_connector_pin",
        "zynq_pin",
        "bank",
        "voltage",
        "linked_io_signal",
        "source_sheet",
        "confidence",
        "notes",
    ]
    return [dict(zip(keys, row)) for row in rows]


def query_fpga_hardware_resources(
    workspace: Path,
    *,
    guide_id: str | None = None,
    signal: str | None = None,
    interface: str | None = None,
    package_pin: str | None = None,
    mio_pin: str | None = None,
    keyword: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    db_path = _ensure_db(workspace)
    clauses: list[str] = []
    params: list[Any] = []
    if guide_id:
        clauses.append("guide_id = ?")
        params.append(guide_id)
    if signal:
        clauses.append("(signal_name LIKE ? OR aliases LIKE ?)")
        params.extend([f"%{signal}%", f"%{signal}%"])
    if interface:
        clauses.append("interface = ?")
        params.append(interface)
    if package_pin:
        clauses.append("package_pin = ?")
        params.append(package_pin.upper())
    if mio_pin:
        clauses.append("mio_pin = ?")
        params.append(_normalize_mio(mio_pin))
    if keyword:
        clauses.append(
            "("
            "signal_name LIKE ? OR aliases LIKE ? OR description LIKE ? OR "
            "resource_group LIKE ? OR source_table LIKE ? OR io_table_links LIKE ? OR "
            "schematic_links LIKE ?"
            ")"
        )
        params.extend([f"%{keyword}%"] * 7)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT guide_id, domain, source_table, resource_group, signal_name,
               aliases, direction, package_pin, mio_pin, interface, description,
               io_table_links, schematic_links, source_section, source_file
        FROM fpga_hardware_resources
        {where}
        ORDER BY guide_id, domain, interface, signal_name
        LIMIT ?
    """
    params.append(limit)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    keys = [
        "guide_id",
        "domain",
        "source_table",
        "resource_group",
        "signal_name",
        "aliases",
        "direction",
        "package_pin",
        "mio_pin",
        "interface",
        "description",
        "io_table_links",
        "schematic_links",
        "source_section",
        "source_file",
    ]
    return [_decode_resource_links(dict(zip(keys, row))) for row in rows]


def query_software_tcl_commands(
    workspace: Path,
    *,
    command: str | None = None,
    keyword: str | None = None,
    option: str | None = None,
    tool: str | None = None,
    tool_version: str | None = None,
    category: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    db_path = _ensure_db(workspace)
    clauses: list[str] = []
    params: list[Any] = []
    join = ""
    if option:
        join = "JOIN software_tcl_command_options o ON o.command_id = c.command_id"
        clauses.append("o.option_name = ?")
        params.append(option)
    if command:
        clauses.append("(c.command = ? OR c.command_id = ?)")
        params.extend([command, command])
    if keyword:
        clauses.append(
            "("
            "c.command LIKE ? OR c.summary LIKE ? OR c.syntax LIKE ? OR "
            "c.categories LIKE ? OR c.description LIKE ? OR c.arguments_text LIKE ? OR "
            "c.examples_text LIKE ?"
            ")"
        )
        params.extend([f"%{keyword}%"] * 7)
    if tool:
        clauses.append("c.tool = ?")
        params.append(tool)
    if tool_version:
        clauses.append("c.tool_version = ?")
        params.append(tool_version)
    if category:
        clauses.append("c.categories LIKE ?")
        params.append(f"%{category}%")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT DISTINCT c.command_id, c.command, c.tool, c.tool_version,
               c.summary, c.syntax, c.categories, c.source_pages
        FROM software_tcl_commands c
        {join}
        {where}
        ORDER BY c.command
        LIMIT ?
    """
    params.append(limit)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    keys = ["command_id", "command", "tool", "tool_version", "summary", "syntax", "categories", "source_pages"]
    return [_decode_json_fields(dict(zip(keys, row)), ("source_pages",)) for row in rows]


def get_software_tcl_command(
    workspace: Path,
    command_id: str,
) -> dict[str, Any]:
    db_path = _ensure_db(workspace)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT command_id, doc_id, tool, tool_version, command, summary,
                   syntax, returns_text, categories, description, arguments_text,
                   examples_text, see_also, source_pages, source_file, full_text
            FROM software_tcl_commands
            WHERE command_id = ? OR command = ?
            """,
            (command_id, command_id),
        ).fetchone()
        if row is None:
            raise KeyError(f"software Tcl command not found: {command_id}")
        options = conn.execute(
            """
            SELECT option_name, description, source
            FROM software_tcl_command_options
            WHERE command_id = ?
            ORDER BY option_name
            """,
            (row[0],),
        ).fetchall()
    keys = [
        "command_id",
        "doc_id",
        "tool",
        "tool_version",
        "command",
        "summary",
        "syntax",
        "returns_text",
        "categories",
        "description",
        "arguments_text",
        "examples_text",
        "see_also",
        "source_pages",
        "source_file",
        "full_text",
    ]
    result = _decode_json_fields(dict(zip(keys, row)), ("see_also", "source_pages"))
    result["options"] = [
        {"name": option_name, "description": description or "", "source": source or ""}
        for option_name, description, source in options
    ]
    return result


def query_software_tcl_topics(
    workspace: Path,
    *,
    keyword: str | None = None,
    doc_id: str | None = None,
    tool: str | None = None,
    tool_version: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    db_path = _ensure_db(workspace)
    clauses: list[str] = []
    params: list[Any] = []
    if keyword:
        clauses.append("(title LIKE ? OR summary LIKE ? OR tags LIKE ? OR text LIKE ?)")
        params.extend([f"%{keyword}%"] * 4)
    if doc_id:
        clauses.append("doc_id = ?")
        params.append(doc_id)
    if tool:
        clauses.append("tool = ?")
        params.append(tool)
    if tool_version:
        clauses.append("tool_version = ?")
        params.append(tool_version)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT topic_id, doc_id, tool, tool_version, title, section_type,
               summary, page_start, page_end, tags
        FROM software_tcl_topics
        {where}
        ORDER BY page_start, topic_id
        LIMIT ?
    """
    params.append(limit)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    keys = ["topic_id", "doc_id", "tool", "tool_version", "title", "section_type", "summary", "page_start", "page_end", "tags"]
    return [_decode_json_fields(dict(zip(keys, row)), ("tags",)) for row in rows]


def query_software_tcl_examples(
    workspace: Path,
    *,
    keyword: str | None = None,
    command: str | None = None,
    doc_id: str | None = None,
    tool: str | None = None,
    tool_version: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    db_path = _ensure_db(workspace)
    clauses: list[str] = []
    params: list[Any] = []
    if keyword:
        clauses.append("(title LIKE ? OR description LIKE ? OR code LIKE ? OR tags LIKE ?)")
        params.extend([f"%{keyword}%"] * 4)
    if command:
        clauses.append("commands LIKE ?")
        params.append(f"%{command}%")
    if doc_id:
        clauses.append("doc_id = ?")
        params.append(doc_id)
    if tool:
        clauses.append("tool = ?")
        params.append(tool)
    if tool_version:
        clauses.append("tool_version = ?")
        params.append(tool_version)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT example_id, doc_id, topic_id, tool, tool_version, title,
               page_start, page_end, description, code, commands, tags
        FROM software_tcl_examples
        {where}
        ORDER BY page_start, example_id
        LIMIT ?
    """
    params.append(limit)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    keys = [
        "example_id", "doc_id", "topic_id", "tool", "tool_version", "title",
        "page_start", "page_end", "description", "code", "commands", "tags",
    ]
    return [_decode_json_fields(dict(zip(keys, row)), ("commands", "tags")) for row in rows]


def search_software_doc_chunks(
    workspace: Path,
    *,
    query_text: str,
    doc_id: str | None = None,
    tool: str | None = None,
    tool_version: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    db_path = _ensure_db(workspace)
    clauses = ["software_doc_chunks_fts MATCH ?"]
    params: list[Any] = [_fts_query(query_text)]
    if doc_id:
        clauses.append("doc_id = ?")
        params.append(doc_id)
    if tool:
        clauses.append("tool = ?")
        params.append(tool)
    if tool_version:
        clauses.append("tool_version = ?")
        params.append(tool_version)
    sql = f"""
        SELECT chunk_id, doc_id, tool, tool_version, anchor, text
        FROM software_doc_chunks_fts
        WHERE {' AND '.join(clauses)}
        LIMIT ?
    """
    params.append(limit)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    keys = ["chunk_id", "doc_id", "tool", "tool_version", "anchor", "text"]
    return [dict(zip(keys, row)) for row in rows]


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


def format_io_pins(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["no matching FPGA IO pins"]
    lines = ["table_id | connector | pin | signal | zynq_pin | bank | voltage | category"]
    lines.append("--- | --- | --- | --- | --- | --- | --- | ---")
    for row in rows:
        lines.append(
            " | ".join(
                [
                    str(row.get("table_id") or ""),
                    str(row.get("connector") or ""),
                    str(row.get("connector_pin") or ""),
                    str(row.get("signal_name") or ""),
                    str(row.get("zynq_pin") or ""),
                    str(row.get("bank") or ""),
                    str(row.get("voltage") or ""),
                    str(row.get("category") or ""),
                ]
            )
        )
    return lines


def format_schematic_nets(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["no matching FPGA schematic nets"]
    lines = [
        "schematic_id | net | interface | category | schematic_pin | core_pin | zynq_pin | bank | sheet | confidence"
    ]
    lines.append("--- | --- | --- | --- | --- | --- | --- | --- | --- | ---")
    for row in rows:
        schematic_pin = _join_pin(row.get("schematic_connector"), row.get("schematic_connector_pin"))
        core_pin = _join_pin(row.get("core_connector"), row.get("core_connector_pin"))
        lines.append(
            " | ".join(
                [
                    str(row.get("schematic_id") or ""),
                    str(row.get("net_name") or ""),
                    str(row.get("interface") or ""),
                    str(row.get("category") or ""),
                    schematic_pin,
                    core_pin,
                    str(row.get("zynq_pin") or ""),
                    str(row.get("bank") or ""),
                    str(row.get("source_sheet") or ""),
                    str(row.get("confidence") or ""),
                ]
            )
        )
    return lines


def format_hardware_resources(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["no matching FPGA hardware resources"]
    lines = [
        "guide_id | signal | alias | domain | dir | pin | interface | io_link | schematic_link | description"
    ]
    lines.append("--- | --- | --- | --- | --- | --- | --- | --- | --- | ---")
    for row in rows:
        io_link = _format_first_io_link(row.get("io_table_links") or [])
        sch_link = _format_first_schematic_link(row.get("schematic_links") or [])
        pin = str(row.get("package_pin") or row.get("mio_pin") or "")
        aliases = row.get("aliases") or []
        alias = ",".join(str(item) for item in aliases[:4]) if isinstance(aliases, list) else str(aliases)
        lines.append(
            " | ".join(
                [
                    str(row.get("guide_id") or ""),
                    str(row.get("signal_name") or ""),
                    alias,
                    str(row.get("domain") or ""),
                    str(row.get("direction") or ""),
                    pin,
                    str(row.get("interface") or ""),
                    io_link,
                    sch_link,
                    str(row.get("description") or ""),
                ]
            )
        )
    return lines


def format_tcl_command_rows(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["no matching software Tcl commands"]
    lines = ["command_id | command | tool | version | pages | summary"]
    lines.append("--- | --- | --- | --- | --- | ---")
    for row in rows:
        pages = row.get("source_pages") or {}
        if isinstance(pages, dict):
            page_text = f"{pages.get('start', '')}-{pages.get('end', '')}"
        else:
            page_text = ""
        lines.append(
            " | ".join(
                [
                    str(row.get("command_id") or ""),
                    str(row.get("command") or ""),
                    str(row.get("tool") or ""),
                    str(row.get("tool_version") or ""),
                    page_text,
                    _one_line(row.get("summary") or ""),
                ]
            )
        )
    return lines


def format_tcl_topic_rows(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["no matching software Tcl topics"]
    lines = ["topic_id | title | doc | pages | summary"]
    lines.append("--- | --- | --- | --- | ---")
    for row in rows:
        lines.append(
            " | ".join(
                [
                    str(row.get("topic_id") or ""),
                    str(row.get("title") or ""),
                    str(row.get("doc_id") or ""),
                    f"{row.get('page_start') or ''}-{row.get('page_end') or ''}",
                    _one_line(row.get("summary") or ""),
                ]
            )
        )
    return lines


def format_tcl_example_rows(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["no matching software Tcl examples"]
    lines = ["example_id | title | doc | pages | commands | preview"]
    lines.append("--- | --- | --- | --- | --- | ---")
    for row in rows:
        commands = row.get("commands") or []
        if isinstance(commands, list):
            command_text = ",".join(str(item) for item in commands[:8])
        else:
            command_text = str(commands)
        lines.append(
            " | ".join(
                [
                    str(row.get("example_id") or ""),
                    str(row.get("title") or ""),
                    str(row.get("doc_id") or ""),
                    f"{row.get('page_start') or ''}-{row.get('page_end') or ''}",
                    command_text,
                    _one_line(row.get("code") or ""),
                ]
            )
        )
    return lines


def format_tcl_command_detail(row: dict[str, Any]) -> list[str]:
    pages = row.get("source_pages") or {}
    page_text = f"{pages.get('start', '')}-{pages.get('end', '')}" if isinstance(pages, dict) else ""
    lines = [
        f"command_id: {row.get('command_id', '')}",
        f"doc_id: {row.get('doc_id', '')}",
        f"tool: {row.get('tool', '')}",
        f"version: {row.get('tool_version', '')}",
        f"source_pages: {page_text}",
        f"source_file: {row.get('source_file', '')}",
        f"categories: {row.get('categories', '')}",
        "",
        "summary:",
        (row.get("summary") or "").rstrip(),
        "",
        "syntax:",
        (row.get("syntax") or "").rstrip(),
        "",
        "options:",
    ]
    options = row.get("options") or []
    if options:
        for option in options:
            description = _one_line(option.get("description") or "")
            lines.append(f"- {option.get('name', '')}: {description}")
    else:
        lines.append("- none indexed")
    if row.get("description"):
        lines.extend(["", "description:", str(row.get("description")).rstrip()])
    if row.get("examples_text"):
        lines.extend(["", "examples:", str(row.get("examples_text")).rstrip()])
    if row.get("see_also"):
        see_also = row.get("see_also")
        if isinstance(see_also, list):
            lines.extend(["", f"see_also: {', '.join(str(item) for item in see_also)}"])
    return lines


def _import_fpga_io_tables(conn: sqlite3.Connection, library_root: Path) -> None:
    parsed_root = library_root / "parsed" / "fpga_io_tables"
    if not parsed_root.is_dir():
        return
    for metadata_path in parsed_root.glob("*/*/metadata.json"):
        parsed_dir = metadata_path.parent
        pins_path = parsed_dir / "pins.json"
        if not pins_path.is_file():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        pins_data = json.loads(pins_path.read_text(encoding="utf-8"))
        table_id = str(metadata.get("table_id") or pins_data.get("table_id") or "")
        if not table_id:
            continue
        conn.execute(
            """
            INSERT OR REPLACE INTO fpga_io_tables (
                table_id, title, source_file, source_type, parser,
                page_count, pin_count, parsed_dir
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                table_id,
                str(metadata.get("title") or ""),
                str(metadata.get("source_file") or ""),
                str(metadata.get("source_type") or ""),
                str(metadata.get("parser") or ""),
                metadata.get("page_count"),
                metadata.get("pin_count"),
                str(parsed_dir.relative_to(library_root)).replace("\\", "/"),
            ),
        )
        for pin in pins_data.get("pins", []):
            conn.execute(
                """
                INSERT OR REPLACE INTO fpga_io_pins (
                    table_id, connector, connector_pin, signal_name, zynq_pin,
                    raw_zynq_pin, bank, voltage, category, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    table_id,
                    str(pin.get("connector") or ""),
                    pin.get("connector_pin"),
                    str(pin.get("signal_name") or ""),
                    pin.get("zynq_pin"),
                    str(pin.get("raw_zynq_pin") or ""),
                    pin.get("bank"),
                    pin.get("voltage"),
                    str(pin.get("category") or ""),
                    str(pin.get("source_file") or ""),
                ),
            )


def _import_fpga_schematics(conn: sqlite3.Connection, library_root: Path) -> None:
    parsed_root = library_root / "parsed" / "fpga_schematics"
    if not parsed_root.is_dir():
        return
    for metadata_path in parsed_root.glob("*/*/metadata.json"):
        parsed_dir = metadata_path.parent
        nets_path = parsed_dir / "nets.json"
        sheets_path = parsed_dir / "sheets.json"
        if not nets_path.is_file():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        nets_data = json.loads(nets_path.read_text(encoding="utf-8"))
        schematic_id = str(metadata.get("schematic_id") or "")
        if not schematic_id:
            continue
        conn.execute(
            """
            INSERT OR REPLACE INTO fpga_schematics (
                schematic_id, title, source_file, source_type, parser,
                page_count, net_count, parsed_dir
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                schematic_id,
                str(metadata.get("title") or ""),
                str(metadata.get("source_file") or ""),
                str(metadata.get("source_type") or ""),
                str(metadata.get("parser") or ""),
                metadata.get("page_count"),
                metadata.get("net_count"),
                str(parsed_dir.relative_to(library_root)).replace("\\", "/"),
            ),
        )
        if sheets_path.is_file():
            sheets_data = json.loads(sheets_path.read_text(encoding="utf-8"))
            for sheet in sheets_data.get("sheets", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO fpga_schematic_sheets (
                        schematic_id, page, title, interfaces, net_count, summary
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        schematic_id,
                        sheet.get("page"),
                        str(sheet.get("title") or ""),
                        ",".join(str(item) for item in sheet.get("interfaces", [])),
                        sheet.get("net_count"),
                        str(sheet.get("summary") or ""),
                    ),
                )
        for net in nets_data.get("nets", []):
            conn.execute(
                """
                INSERT OR REPLACE INTO fpga_schematic_nets (
                    schematic_id, net_name, normalized_name, interface, category,
                    schematic_connector, schematic_connector_pin, core_connector,
                    core_connector_pin, zynq_pin, bank, voltage, linked_io_signal,
                    source_sheet, confidence, source_file, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    schematic_id,
                    str(net.get("net_name") or ""),
                    str(net.get("normalized_name") or _normalize_signal(net.get("net_name"))),
                    str(net.get("interface") or ""),
                    str(net.get("category") or ""),
                    str(net.get("schematic_connector") or ""),
                    net.get("schematic_connector_pin"),
                    str(net.get("core_connector") or ""),
                    net.get("core_connector_pin"),
                    net.get("zynq_pin"),
                    net.get("bank"),
                    net.get("voltage"),
                    str(net.get("linked_io_signal") or ""),
                    str(net.get("source_sheet") or ""),
                    str(net.get("confidence") or ""),
                    str(net.get("source_file") or ""),
                    str(net.get("notes") or ""),
                ),
            )


def _import_fpga_hardware_guides(conn: sqlite3.Connection, library_root: Path) -> None:
    parsed_root = library_root / "parsed" / "fpga_ug_mineru"
    if not parsed_root.is_dir():
        return
    for metadata_path in parsed_root.glob("*/*/metadata.json"):
        parsed_dir = metadata_path.parent
        resources_path = parsed_dir / "resources.json"
        if not resources_path.is_file():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        resources_data = json.loads(resources_path.read_text(encoding="utf-8"))
        guide_id = str(metadata.get("guide_id") or "")
        if not guide_id:
            continue
        conn.execute(
            """
            INSERT OR REPLACE INTO fpga_hardware_guides (
                guide_id, title, source_file, source_type, parser,
                page_count, chapter, chapter_title, resource_count,
                section_count, linked_io_count, linked_schematic_count,
                parsed_dir
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                guide_id,
                str(metadata.get("title") or ""),
                str(metadata.get("source_file") or ""),
                str(metadata.get("source_type") or ""),
                str(metadata.get("parser") or ""),
                metadata.get("page_count"),
                str(metadata.get("chapter") or ""),
                str(metadata.get("chapter_title") or ""),
                metadata.get("resource_count"),
                metadata.get("section_count"),
                metadata.get("linked_io_count"),
                metadata.get("linked_schematic_count"),
                str(parsed_dir.relative_to(library_root)).replace("\\", "/"),
            ),
        )
        for resource in resources_data.get("resources", []):
            conn.execute(
                """
                INSERT OR REPLACE INTO fpga_hardware_resources (
                    guide_id, domain, source_table, resource_group,
                    signal_name, aliases, direction, package_pin, mio_pin,
                    interface, description, io_table_links, schematic_links,
                    source_section, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    guide_id,
                    str(resource.get("domain") or ""),
                    str(resource.get("source_table") or ""),
                    str(resource.get("group") or ""),
                    str(resource.get("signal_name") or ""),
                    json.dumps(resource.get("aliases") or [], ensure_ascii=False),
                    str(resource.get("direction") or ""),
                    str(resource.get("package_pin") or ""),
                    str(resource.get("mio_pin") or ""),
                    str(resource.get("interface") or ""),
                    str(resource.get("description") or ""),
                    json.dumps(resource.get("io_table_links") or [], ensure_ascii=False),
                    json.dumps(resource.get("schematic_links") or [], ensure_ascii=False),
                    str(resource.get("source_section") or ""),
                    str(resource.get("source_file") or ""),
                ),
            )


def _import_software_tcl_library(conn: sqlite3.Connection, library_root: Path) -> None:
    parsed_root = library_root / "parsed" / "software_ug_mineru"
    if not parsed_root.is_dir():
        return
    for metadata_path in parsed_root.glob("*/*/metadata.json"):
        parsed_dir = metadata_path.parent
        commands_path = parsed_dir / "commands.json"
        sections_path = parsed_dir / "sections.json"
        examples_path = parsed_dir / "examples.json"
        chunks_path = parsed_dir / "chunks.jsonl"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        doc_id = str(metadata.get("doc_id") or "")
        if not doc_id:
            continue
        conn.execute(
            """
            INSERT OR REPLACE INTO software_tool_documents (
                doc_id, title, vendor, tool, tool_version, source_file,
                source_type, parser, page_count, command_count, parsed_dir, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_id,
                str(metadata.get("title") or ""),
                str(metadata.get("vendor") or ""),
                str(metadata.get("tool") or ""),
                str(metadata.get("tool_version") or ""),
                str(metadata.get("source_file") or ""),
                str(metadata.get("source_type") or ""),
                str(metadata.get("parser") or ""),
                metadata.get("page_count"),
                metadata.get("command_count"),
                str(parsed_dir.relative_to(library_root)).replace("\\", "/"),
                json.dumps(metadata.get("notes") or [], ensure_ascii=False),
            ),
        )
        if commands_path.is_file():
            commands_data = json.loads(commands_path.read_text(encoding="utf-8"))
            for command in commands_data.get("commands", []):
                command_id = str(command.get("command_id") or "")
                if not command_id:
                    continue
                conn.execute(
                    """
                    INSERT OR REPLACE INTO software_tcl_commands (
                        command_id, doc_id, tool, tool_version, command, summary,
                        syntax, returns_text, categories, description, arguments_text,
                        examples_text, see_also, source_pages, source_file, full_text
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        command_id,
                        str(command.get("doc_id") or doc_id),
                        str(command.get("tool") or ""),
                        str(command.get("tool_version") or ""),
                        str(command.get("command") or ""),
                        str(command.get("summary") or ""),
                        str(command.get("syntax") or ""),
                        str(command.get("returns_text") or ""),
                        str(command.get("categories") or ""),
                        str(command.get("description") or ""),
                        str(command.get("arguments_text") or ""),
                        str(command.get("examples_text") or ""),
                        json.dumps(command.get("see_also") or [], ensure_ascii=False),
                        json.dumps(command.get("source_pages") or {}, ensure_ascii=False),
                        str(command.get("source_file") or ""),
                        str(command.get("full_text") or ""),
                    ),
                )
                for option in command.get("options", []):
                    option_name = str(option.get("name") or "")
                    if not option_name:
                        continue
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO software_tcl_command_options (
                            command_id, option_name, description, source
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (
                            command_id,
                            option_name,
                            str(option.get("description") or ""),
                            str(option.get("source") or ""),
                        ),
                    )
        if sections_path.is_file():
            sections_data = json.loads(sections_path.read_text(encoding="utf-8"))
            for topic in sections_data.get("sections", []):
                topic_id = str(topic.get("topic_id") or topic.get("section_id") or "")
                if not topic_id:
                    continue
                conn.execute(
                    """
                    INSERT OR REPLACE INTO software_tcl_topics (
                        topic_id, doc_id, tool, tool_version, title, section_type,
                        summary, page_start, page_end, tags, text
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        topic_id,
                        str(topic.get("doc_id") or doc_id),
                        str(topic.get("tool") or ""),
                        str(topic.get("tool_version") or ""),
                        str(topic.get("title") or ""),
                        str(topic.get("section_type") or ""),
                        str(topic.get("summary") or ""),
                        topic.get("page_start"),
                        topic.get("page_end"),
                        json.dumps(topic.get("tags") or [], ensure_ascii=False),
                        str(topic.get("text") or ""),
                    ),
                )
        if examples_path.is_file():
            examples_data = json.loads(examples_path.read_text(encoding="utf-8"))
            for example in examples_data.get("examples", []):
                example_id = str(example.get("example_id") or "")
                if not example_id:
                    continue
                conn.execute(
                    """
                    INSERT OR REPLACE INTO software_tcl_examples (
                        example_id, doc_id, topic_id, tool, tool_version, title,
                        page_start, page_end, code, description, commands, tags
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        example_id,
                        str(example.get("doc_id") or doc_id),
                        str(example.get("topic_id") or ""),
                        str(example.get("tool") or ""),
                        str(example.get("tool_version") or ""),
                        str(example.get("title") or ""),
                        example.get("page_start"),
                        example.get("page_end"),
                        str(example.get("code") or ""),
                        str(example.get("description") or ""),
                        json.dumps(example.get("commands") or [], ensure_ascii=False),
                        json.dumps(example.get("tags") or [], ensure_ascii=False),
                    ),
                )
        if chunks_path.is_file():
            with chunks_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    chunk_id = str(chunk.get("chunk_id") or "")
                    if not chunk_id:
                        continue
                    values = (
                        chunk_id,
                        str(chunk.get("doc_id") or doc_id),
                        str(chunk.get("tool") or ""),
                        str(chunk.get("tool_version") or ""),
                        str(chunk.get("section_type") or ""),
                        str(chunk.get("anchor") or ""),
                        chunk.get("page_start"),
                        chunk.get("page_end"),
                        str(chunk.get("text") or ""),
                    )
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO software_doc_chunks (
                            chunk_id, doc_id, tool, tool_version, section_type,
                            anchor, page_start, page_end, text
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        values,
                    )
                    conn.execute(
                        """
                        INSERT INTO software_doc_chunks_fts (
                            chunk_id, doc_id, tool, tool_version, anchor, text
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (values[0], values[1], values[2], values[3], values[5], values[8]),
                    )


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


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


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


def _normalize_signal(value: Any) -> str:
    return "".join(char.upper() for char in str(value or "") if char.isalnum())


def _join_pin(connector: Any, pin: Any) -> str:
    if not connector and not pin:
        return ""
    if not pin:
        return str(connector or "")
    if not connector:
        return str(pin)
    return f"{connector}_{pin}"


def _decode_resource_links(row: dict[str, Any]) -> dict[str, Any]:
    for key in ("aliases", "io_table_links", "schematic_links"):
        value = row.get(key)
        if isinstance(value, str):
            try:
                row[key] = json.loads(value)
            except json.JSONDecodeError:
                row[key] = []
    return row


def _decode_json_fields(row: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    for key in keys:
        value = row.get(key)
        if isinstance(value, str):
            try:
                row[key] = json.loads(value)
            except json.JSONDecodeError:
                row[key] = {} if value.startswith("{") else []
    return row


def _one_line(value: Any, *, limit: int = 160) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _fts_query(value: str) -> str:
    tokens = _tokens(value)
    if not tokens:
        return '""'
    return " AND ".join(f'"{token}"' for token in tokens)


def _format_first_io_link(links: list[dict[str, Any]]) -> str:
    if not links:
        return ""
    link = links[0]
    connector = _join_pin(link.get("connector"), link.get("connector_pin"))
    signal = str(link.get("signal_name") or "")
    bank = str(link.get("bank") or "")
    return "/".join(item for item in [signal, connector, bank] if item)


def _format_first_schematic_link(links: list[dict[str, Any]]) -> str:
    if not links:
        return ""
    link = links[0]
    net = str(link.get("net_name") or "")
    schematic_pin = _join_pin(link.get("schematic_connector"), link.get("schematic_connector_pin"))
    core_pin = _join_pin(link.get("core_connector"), link.get("core_connector_pin"))
    return "/".join(item for item in [net, schematic_pin, core_pin] if item)


def _normalize_mio(value: Any) -> str:
    text = str(value or "").upper()
    if text.startswith("MIO"):
        suffix = text[3:]
    elif text.startswith("MI"):
        suffix = text[2:]
    else:
        suffix = text
    number = "".join(char for char in suffix if char.isdigit())
    if number:
        return f"MIO{int(number)}"
    return text
