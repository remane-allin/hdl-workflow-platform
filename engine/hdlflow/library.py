"""Local SQLite-backed library index for agent retrieval."""

from __future__ import annotations

import sqlite3
import json
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
        _import_fpga_io_tables(conn, library_root)
        _import_fpga_schematics(conn, library_root)
        _import_fpga_hardware_guides(conn, library_root)
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
        clauses.append("(description LIKE ? OR resource_group LIKE ? OR io_table_links LIKE ? OR schematic_links LIKE ?)")
        params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
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
