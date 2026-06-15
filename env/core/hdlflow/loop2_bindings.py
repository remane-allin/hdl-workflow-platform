"""Loop2 requirement-to-UVM binding database."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .layout import LIB_ROOT
from .library import get_entry, query_uvm_examples, search_uvm_doc_chunks
from .project import require_project_instance
from .simple_yaml import load_yaml


DEFAULT_DB_REL = Path("work/loop2_uvm") / "_runtime" / "loop2_bindings.sqlite"
DEFAULT_PREFLIGHT_REL = Path("output") / "reports" / "loop2" / "preflight" / "database_preflight.md"
DEFAULT_FLESH_PLAN_REL = Path("output") / "reports" / "loop2" / "preflight" / "uvm_flesh_plan.md"
REQUIRED_TEMPLATE_IDS = [
    "uvm.rkv_style_framework",
    "uvm.rkv_i2c_reference_profile",
]
REQUIRED_UVM_GUIDE_ENTRIES = [
    ("uvm.methodology_reference", "flow"),
    ("accellera.uvm_users_guide.1_1", "document"),
    ("verification_academy.uvm_cookbook.complete", "document"),
]
UVM_FLESH_TOPICS = [
    ("configuration_and_virtual_interfaces", "uvm_config_db virtual interface"),
    ("agent_driver_monitor_sequencer", "uvm agent driver monitor sequencer"),
    ("sequences_and_virtual_sequences", "uvm_sequence virtual sequence sequencer"),
    ("scoreboard_and_analysis", "scoreboard analysis port analysis export"),
    ("coverage_and_sampling", "functional coverage covergroup monitor sampling"),
    ("ral_and_adapter", "uvm_reg_adapter register model bus item"),
]
UVM_EXAMPLE_QUERIES = [
    "uvm_config_db",
    "uvm_analysis_port",
    "uvm_sequence",
    "uvm_reg_adapter",
]


@dataclass(frozen=True)
class Loop2BindingResult:
    db_path: Path
    requirement_count: int
    artifact_count: int
    binding_count: int
    evidence_count: int
    missing_artifacts: int
    missing_database_items: int


@dataclass(frozen=True)
class Loop2PreflightResult:
    report_path: Path
    missing_items: list[str]
    flesh_plan_path: Path | None = None


SCHEMA = """
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS loop2_requirements (
    req_id TEXT PRIMARY KEY,
    intent_id TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS loop2_artifacts (
    artifact_id TEXT PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    artifact_type TEXT,
    role TEXT,
    exists_on_disk INTEGER NOT NULL,
    source TEXT
);

CREATE TABLE IF NOT EXISTS loop2_requirement_artifacts (
    req_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    binding_role TEXT,
    PRIMARY KEY (req_id, artifact_id)
);

CREATE TABLE IF NOT EXISTS loop2_evidence (
    evidence_id TEXT PRIMARY KEY,
    evidence_type TEXT,
    path TEXT,
    marker TEXT,
    status TEXT,
    value TEXT
);

CREATE TABLE IF NOT EXISTS loop2_artifact_evidence (
    artifact_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    PRIMARY KEY (artifact_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS loop2_checks (
    check_id TEXT PRIMARY KEY,
    status TEXT,
    detail TEXT
);

CREATE TABLE IF NOT EXISTS loop2_database_sources (
    source_id TEXT PRIMARY KEY,
    source_type TEXT,
    path TEXT,
    status TEXT
);

CREATE TABLE IF NOT EXISTS loop2_template_sources (
    template_id TEXT PRIMARY KEY,
    title TEXT,
    detail_path TEXT,
    status TEXT
);

CREATE INDEX IF NOT EXISTS idx_loop2_artifacts_type ON loop2_artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS idx_loop2_artifacts_role ON loop2_artifacts(role);
CREATE INDEX IF NOT EXISTS idx_loop2_evidence_status ON loop2_evidence(status);
"""


def write_loop2_database_preflight(workspace: Path, project_path: Path) -> Loop2PreflightResult:
    """Query the local template database and write Loop2 preflight evidence."""

    workspace = workspace.resolve()
    project = require_project_instance(project_path)
    report_path = project / DEFAULT_PREFLIGHT_REL
    report_path.parent.mkdir(parents=True, exist_ok=True)

    missing: list[str] = []
    db_path = workspace / LIB_ROOT / "local" / "library.sqlite"
    lines = [
        "# Loop2 Database Preflight",
        "",
        f"- project: {project.name}",
        f"- library_db: `{_normalize_rel_path(db_path)}`",
        "",
        "## Template Entries",
        "",
    ]

    for template_id in REQUIRED_TEMPLATE_IDS:
        try:
            entry, detail = get_entry(workspace, template_id, expected_kind="template")
        except Exception as exc:
            missing.append(template_id)
            lines.append(f"- {template_id}: MISSING ({exc})")
            continue
        lines.append(f"- {template_id}: PASS")
        lines.append(f"  - title: {entry.title}")
        lines.append(f"  - detail_path: {entry.detail_path}")
        lines.append(f"  - detail_bytes: {len(detail.encode('utf-8'))}")

    lines.extend(["", "## UVM Guide Entries", ""])
    for entry_id, expected_kind in REQUIRED_UVM_GUIDE_ENTRIES:
        try:
            entry, detail = get_entry(workspace, entry_id, expected_kind=expected_kind)
        except Exception as exc:
            missing.append(entry_id)
            lines.append(f"- {entry_id}: MISSING ({exc})")
            continue
        lines.append(f"- {entry_id}: PASS")
        lines.append(f"  - title: {entry.title}")
        lines.append(f"  - detail_path: {entry.detail_path}")
        if detail.startswith("detail file missing:"):
            lines.append("  - detail_status: DB entry only; UVM guide chunks/examples are checked below")
        elif detail:
            lines.append(f"  - detail_bytes: {len(detail.encode('utf-8'))}")

    flesh_missing = _write_uvm_flesh_plan(workspace, project, db_path)
    missing.extend(flesh_missing)

    lines.extend(["", "## Project Layout", ""])
    layout_checks = [
        ("output/uvm", project / "output" / "uvm"),
        ("output/uvm/env", project / "output" / "uvm" / "env"),
        ("output/uvm/agents", project / "output" / "uvm" / "agents"),
        ("output/uvm/cov", project / "output" / "uvm" / "cov"),
        ("output/uvm/seq_lib", project / "output" / "uvm" / "seq_lib"),
        ("output/uvm/tests", project / "output" / "uvm" / "tests"),
        ("output/uvm/tb", project / "output" / "uvm" / "tb"),
        ("work/loop2_uvm/sim/regression.do", project / "work/loop2_uvm" / "sim" / "regression.do"),
    ]
    for label, path in layout_checks:
        status = "PASS" if path.exists() else "MISSING"
        if status != "PASS":
            missing.append(label)
        lines.append(f"- {label}: {status}")

    template_files = list((project / "output" / "uvm").rglob("*.template")) if (project / "output" / "uvm").exists() else []
    lines.append(f"- instantiated_uvm_sources: {'PASS' if not template_files else 'WARN'}")
    if template_files:
        lines.append(f"  - template_files_remaining: {len(template_files)}")

    lines.extend(
        [
            "",
            "## Required Use",
            "",
            "- Run this preflight before building or closing Loop2 UVM.",
            "- UVM framework selection must come from the local template database.",
            f"- After the template skeleton is created, use `{_normalize_rel_path(project / DEFAULT_FLESH_PLAN_REL)}` to flesh out cfg, agents, sequences, scoreboard, coverage, and RAL from the UVM database.",
            "- Project-specific UVM files must still be completed from the normalized spec and checked against the database-backed flesh plan.",
            "",
            f"result: {'PASS' if not missing else 'FAIL'}",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return Loop2PreflightResult(report_path=report_path, missing_items=missing, flesh_plan_path=project / DEFAULT_FLESH_PLAN_REL)


def _write_uvm_flesh_plan(workspace: Path, project: Path, db_path: Path) -> list[str]:
    """Write a project-local plan that maps UVM database evidence onto real UVM files."""

    plan_path = project / DEFAULT_FLESH_PLAN_REL
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []
    lines = [
        "# UVM Database Flesh Plan",
        "",
        f"- project: {project.name}",
        f"- library_db: `{_normalize_rel_path(db_path)}`",
        "- purpose: turn the RKV/template skeleton into project-specific UVM implementation using local UVM guide evidence",
        "",
        "## Implementation Targets",
        "",
        "- `output/uvm/cfg/uvm_config.sv`: config object, virtual interface handles, plus `uvm_config_db` get/set ownership.",
        "- `output/uvm/tb/tb_dut_if.sv` and `output/uvm/tb/tb_uvm.sv`: concrete interface wiring and top-level config_db publication.",
        "- `output/uvm/agents/*`: item, driver, monitor, sequencer, and agent classes completed per protocol signals.",
        "- `output/uvm/seq_lib/virtual_sequences.svh` and `output/uvm/tests/tests.svh`: reset, legal, error, stress, and coverage-closing scenarios.",
        "- `output/uvm/env/scoreboard.sv`: analysis connections, reference model, ordering rules, and mismatch reporting.",
        "- `output/uvm/cov/coverage.sv`: monitor-sampled covergroups and scenario bins tied to requirements.",
        "- `output/uvm/env/uvm_pkg.sv`: explicit compile order and package exports for all real UVM sources.",
        "",
        "## Guide Retrieval",
        "",
    ]

    for topic_id, query in UVM_FLESH_TOPICS:
        lines.extend([f"### {topic_id}", "", f"- query: `{query}`"])
        try:
            chunks = search_uvm_doc_chunks(workspace, query_text=query, limit=3)
        except Exception as exc:
            missing.append(f"uvm_doc_query:{topic_id}")
            lines.append(f"- status: MISSING ({exc})")
            lines.append("")
            continue
        if not chunks:
            missing.append(f"uvm_doc_query:{topic_id}")
            lines.append("- status: MISSING (no UVM guide chunks matched)")
            lines.append("")
            continue
        lines.append("- status: PASS")
        for chunk in chunks:
            preview = _preview(chunk.get("text"), 220)
            lines.append(f"- chunk: {chunk.get('chunk_id')} | {chunk.get('doc_id')} | {chunk.get('anchor')}")
            lines.append(f"  - use_for: {_topic_use(topic_id)}")
            lines.append(f"  - preview: {preview}")
        lines.append("")

    lines.extend(["## Example Retrieval", ""])
    for keyword in UVM_EXAMPLE_QUERIES:
        lines.extend([f"### {keyword}", ""])
        try:
            examples = query_uvm_examples(workspace, keyword=keyword, language_hint="systemverilog", limit=2)
        except Exception as exc:
            missing.append(f"uvm_example_query:{keyword}")
            lines.append(f"- status: MISSING ({exc})")
            lines.append("")
            continue
        if not examples:
            missing.append(f"uvm_example_query:{keyword}")
            lines.append("- status: MISSING (no SystemVerilog example matched)")
            lines.append("")
            continue
        lines.append("- status: PASS")
        for example in examples:
            preview = _preview(example.get("code"), 180)
            caption = _preview(example.get("caption"), 120)
            lines.append(f"- example: {example.get('example_id')} | {example.get('doc_id')} | page {example.get('page')}")
            if caption:
                lines.append(f"  - caption: {caption}")
            lines.append(f"  - code_preview: {preview}")
        lines.append("")

    lines.extend(
        [
            "## Closure Rule",
            "",
            "- Do not close Loop2 with template-shaped files only.",
            "- Every real UVM file listed above must either implement the relevant mechanism or explain why the project does not need it in the Loop2 exit report.",
            "- The final UVM regression remains the authority for behavior; this plan is methodology and implementation provenance.",
            "",
            f"result: {'PASS' if not missing else 'FAIL'}",
        ]
    )
    plan_path.write_text("\n".join(lines), encoding="utf-8")
    return missing


def _topic_use(topic_id: str) -> str:
    mapping = {
        "configuration_and_virtual_interfaces": "cfg object, tb interface binding, config_db get/set checks",
        "agent_driver_monitor_sequencer": "agent internals and transaction flow",
        "sequences_and_virtual_sequences": "seq_lib and test scenario layering",
        "scoreboard_and_analysis": "analysis ports, expected/actual queues, scoreboard connections",
        "coverage_and_sampling": "monitor-owned sampling and coverage closure",
        "ral_and_adapter": "register model, adapter, and bus transaction conversion when CSRs exist",
    }
    return mapping.get(topic_id, "project-specific UVM implementation")


def _preview(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def build_loop2_binding_database(
    project: Path,
    *,
    db_path: Path | None = None,
    workspace: Path | None = None,
) -> Loop2BindingResult:
    project = require_project_instance(project)

    db_path = _resolve_project_path(project, db_path or DEFAULT_DB_REL)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    req_bindings = _collect_requirement_bindings(project)
    artifact_paths = _collect_loop2_artifacts(project, req_bindings)
    evidence = _collect_evidence(project)
    checks = _build_checks(project, req_bindings, artifact_paths, evidence)
    database_checks = _build_database_checks(workspace)

    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        _insert_metadata(conn, project)
        _insert_database_sources(conn, workspace)
        artifact_ids = _insert_artifacts(conn, project, artifact_paths, req_bindings)
        _insert_requirements(conn, project, req_bindings, artifact_ids)
        evidence_ids = _insert_evidence(conn, evidence)
        _insert_artifact_evidence(conn, artifact_ids, evidence, evidence_ids)
        for check_id, status, detail in [*database_checks, *checks]:
            conn.execute(
                "INSERT INTO loop2_checks(check_id, status, detail) VALUES (?, ?, ?)",
                (check_id, status, detail),
            )

    missing_artifacts = sum(1 for path in artifact_paths if not (project / path).exists())
    missing_database_items = sum(1 for _check_id, status, _detail in database_checks if status != "PASS")
    return Loop2BindingResult(
        db_path=db_path,
        requirement_count=len(req_bindings),
        artifact_count=len(artifact_paths),
        binding_count=sum(len(paths) for paths in req_bindings.values()),
        evidence_count=len(evidence),
        missing_artifacts=missing_artifacts,
        missing_database_items=missing_database_items,
    )


def format_loop2_binding_rows(project: Path, *, req_id: str | None = None) -> list[str]:
    project = require_project_instance(project)
    db_path = project / DEFAULT_DB_REL
    if not db_path.is_file():
        raise FileNotFoundError(f"Loop2 binding database not found: {db_path}")

    where = ""
    params: list[Any] = []
    if req_id:
        where = "WHERE r.req_id = ?"
        params.append(req_id)

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT r.req_id, r.intent_id, a.path, a.artifact_type, a.role, a.exists_on_disk
            FROM loop2_requirements r
            JOIN loop2_requirement_artifacts b ON b.req_id = r.req_id
            JOIN loop2_artifacts a ON a.artifact_id = b.artifact_id
            {where}
            ORDER BY r.req_id, a.role, a.path
            """,
            params,
        ).fetchall()
        checks = conn.execute("SELECT check_id, status, detail FROM loop2_checks ORDER BY check_id").fetchall()

    lines = ["req_id | intent_id | artifact_type | role | exists | path", "--- | --- | --- | --- | --- | ---"]
    for req, intent, path, artifact_type, role, exists in rows:
        lines.append(f"{req} | {intent} | {artifact_type} | {role} | {exists} | {path}")
    lines.extend(["", "check_id | status | detail", "--- | --- | ---"])
    for check_id, status, detail in checks:
        lines.append(f"{check_id} | {status} | {detail}")
    return lines


def _insert_metadata(conn: sqlite3.Connection, project: Path) -> None:
    metadata = {
        "project": project.name,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "schema_version": "1",
    }
    for key, value in metadata.items():
        conn.execute("INSERT INTO metadata(key, value) VALUES (?, ?)", (key, value))


def _insert_database_sources(conn: sqlite3.Connection, workspace: Path | None) -> None:
    if workspace is None:
        conn.execute(
            "INSERT INTO loop2_database_sources(source_id, source_type, path, status) VALUES (?, ?, ?, ?)",
            ("template_library", "sqlite", "", "not_checked"),
        )
        return

    workspace = workspace.resolve()
    db_path = workspace / LIB_ROOT / "local" / "library.sqlite"
    conn.execute(
        "INSERT INTO loop2_database_sources(source_id, source_type, path, status) VALUES (?, ?, ?, ?)",
        ("template_library", "sqlite", _normalize_rel_path(db_path), "PASS" if db_path.is_file() else "MISSING"),
    )
    for template_id in REQUIRED_TEMPLATE_IDS:
        try:
            entry, _detail = get_entry(workspace, template_id, expected_kind="template")
            conn.execute(
                "INSERT INTO loop2_template_sources(template_id, title, detail_path, status) VALUES (?, ?, ?, ?)",
                (template_id, entry.title, entry.detail_path, "PASS"),
            )
        except Exception as exc:
            conn.execute(
                "INSERT INTO loop2_template_sources(template_id, title, detail_path, status) VALUES (?, ?, ?, ?)",
                (template_id, "", str(exc), "MISSING"),
            )


def _insert_artifacts(
    conn: sqlite3.Connection,
    project: Path,
    artifact_paths: set[str],
    req_bindings: dict[str, set[str]],
) -> dict[str, str]:
    artifact_ids: dict[str, str] = {}
    bound_paths = _all_bound_paths(req_bindings)
    for index, path in enumerate(sorted(artifact_paths), start=1):
        artifact_id = f"artifact_{index:04d}"
        artifact_ids[path] = artifact_id
        artifact_type, role = _classify_artifact(path)
        conn.execute(
            """
            INSERT INTO loop2_artifacts(
                artifact_id, path, artifact_type, role, exists_on_disk, source
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                artifact_id,
                path,
                artifact_type,
                role,
                1 if (project / path).exists() else 0,
                "loop2_trace" if path in bound_paths else "scan",
            ),
        )
    return artifact_ids


def _insert_requirements(
    conn: sqlite3.Connection,
    project: Path,
    req_bindings: dict[str, set[str]],
    artifact_ids: dict[str, str],
) -> None:
    intent_by_req = _loop2_intents(project)
    for req_id in sorted(req_bindings):
        conn.execute(
            "INSERT INTO loop2_requirements(req_id, intent_id, source) VALUES (?, ?, ?)",
            (req_id, intent_by_req.get(req_id, ""), "loop2_trace"),
        )
        for path in sorted(req_bindings[req_id]):
            conn.execute(
                """
                INSERT INTO loop2_requirement_artifacts(req_id, artifact_id, binding_role)
                VALUES (?, ?, ?)
                """,
                (req_id, artifact_ids[path], _classify_binding_role(path)),
            )


def _insert_evidence(conn: sqlite3.Connection, evidence: list[dict[str, str]]) -> dict[str, str]:
    evidence_ids: dict[str, str] = {}
    for index, item in enumerate(evidence, start=1):
        evidence_id = f"evidence_{index:04d}"
        evidence_ids[item["path"] + item["marker"]] = evidence_id
        conn.execute(
            """
            INSERT INTO loop2_evidence(evidence_id, evidence_type, path, marker, status, value)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                evidence_id,
                item["evidence_type"],
                item["path"],
                item["marker"],
                item["status"],
                item["value"],
            ),
        )
    return evidence_ids


def _insert_artifact_evidence(
    conn: sqlite3.Connection,
    artifact_ids: dict[str, str],
    evidence: list[dict[str, str]],
    evidence_ids: dict[str, str],
) -> None:
    for artifact_path, artifact_id in artifact_ids.items():
        for item in evidence:
            if _evidence_matches_artifact(item, artifact_path):
                conn.execute(
                    """
                    INSERT OR IGNORE INTO loop2_artifact_evidence(artifact_id, evidence_id)
                    VALUES (?, ?)
                    """,
                    (artifact_id, evidence_ids[item["path"] + item["marker"]]),
                )


def _collect_requirement_bindings(project: Path) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    trace_paths = [
        project / "work/loop2_uvm" / "trace_matrix" / "req_to_uvm.yaml",
        project / "work/loop2_uvm" / "trace_matrix" / "req_to_assertion.yaml",
        project / "work/loop2_uvm" / "trace_matrix" / "req_to_coverage.yaml",
    ]
    for trace_path in trace_paths:
        if not trace_path.is_file():
            continue
        data = load_yaml(trace_path)
        links = data.get("links", {})
        if isinstance(links, dict):
            items = links.items()
        elif isinstance(links, list):
            items = []
            for item in links:
                if not isinstance(item, dict):
                    continue
                req_id = item.get("req_id") or item.get("requirement_id") or item.get("source")
                raw_paths = item.get("paths") or item.get("artifacts") or item.get("targets")
                if req_id:
                    items.append((req_id, raw_paths))
        else:
            continue
        _collect_loop2_paths_from_trace_items(items, result)
    return result


def _collect_loop2_paths_from_trace_items(items: Any, result: dict[str, set[str]]) -> None:
    for req_id, raw_paths in items:
        paths = {_normalize_rel_path(path) for path in _as_list(raw_paths)}
        loop2_paths = {
            path
            for path in paths
            if path.startswith("output/uvm/")
            or path.startswith("work/loop2_uvm/")
            or path.startswith("output/reports/loop2/")
        }
        if loop2_paths:
            result.setdefault(str(req_id), set()).update(loop2_paths)


def _collect_loop2_artifacts(project: Path, req_bindings: dict[str, set[str]]) -> set[str]:
    paths = set(_all_bound_paths(req_bindings))
    for root in [
        project / "output" / "uvm",
        project / "work/loop2_uvm" / "sim",
        project / "output" / "reports" / "loop2",
    ]:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".sv", ".svh", ".do", ".md", ".json"}:
                paths.add(_normalize_rel_path(path.relative_to(project)))
    return paths


def _collect_evidence(project: Path) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    log_path = project / "work" / "loop2_uvm" / "current" / "log" / "modelsim.log"
    rel_log = "work/loop2_uvm/current/log/modelsim.log"
    if log_path.is_file():
        text = log_path.read_text(encoding="utf-8", errors="ignore")
        markers = [
            ("uvm_summary", "HDLFLOW|UVM_SUMMARY", "PASS", _extract_value(text, r"HDLFLOW\|UVM_SUMMARY\|.*total_checks=([0-9]+)")),
            ("uvm_structured_check", "HDLFLOW|UVM_CHECK", "PASS", str(text.count("HDLFLOW|UVM_CHECK"))),
        ]
        for evidence_type, marker, status, value in markers:
            if marker in text:
                evidence.append(
                    {
                        "evidence_type": evidence_type,
                        "path": rel_log,
                        "marker": marker,
                        "status": status,
                        "value": value,
                    }
                )

    report_json = project / "output" / "reports" / "loop2" / "loop2_report.json"
    if report_json.is_file():
        try:
            payload = json.loads(report_json.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
        if isinstance(payload, dict):
            summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
            evidence.append(
                {
                    "evidence_type": "loop2_report_json",
                    "path": _normalize_rel_path(report_json.relative_to(project)),
                    "marker": str(payload.get("result", "")),
                    "status": str(payload.get("result", "")),
                    "value": str(summary.get("total_checks", "")),
                }
            )

    for report_name in [
        "loop2_report.md",
        "loop2_report.json",
        "loop2_report_manifest.json",
    ]:
        report_path = project / "output" / "reports" / "loop2" / report_name
        if report_path.is_file():
            evidence.append(
                {
                    "evidence_type": "report",
                    "path": _normalize_rel_path(report_path.relative_to(project)),
                    "marker": report_name,
                    "status": "PASS",
                    "value": str(report_path.stat().st_size),
                }
            )
    return evidence


def _build_checks(
    project: Path,
    req_bindings: dict[str, set[str]],
    artifact_paths: set[str],
    evidence: list[dict[str, str]],
) -> list[tuple[str, str, str]]:
    missing = [path for path in artifact_paths if not (project / path).exists()]
    return [
        ("requirements_bound", "PASS" if req_bindings else "FAIL", f"{len(req_bindings)} Loop2 requirements have bindings"),
        ("bound_artifacts_exist", "PASS" if not missing else "FAIL", f"{len(missing)} missing artifacts"),
        (
            "scoreboard_evidence",
            "PASS" if _has_evidence(evidence, "scoreboard_pass") else "FAIL",
            "scoreboard pass marker present" if _has_evidence(evidence, "scoreboard_pass") else "scoreboard pass marker missing",
        ),
        (
            "coverage_evidence",
            "PASS" if _has_evidence(evidence, "coverage_reported") else "FAIL",
            "functional coverage marker present" if _has_evidence(evidence, "coverage_reported") else "functional coverage marker missing",
        ),
        (
            "uvm_clean",
            "PASS" if _has_evidence(evidence, "uvm_error_zero") and _has_evidence(evidence, "uvm_fatal_zero") else "FAIL",
            "UVM_ERROR/UVM_FATAL are zero" if _has_evidence(evidence, "uvm_error_zero") and _has_evidence(evidence, "uvm_fatal_zero") else "UVM zero-error markers missing",
        ),
    ]


def _build_database_checks(workspace: Path | None) -> list[tuple[str, str, str]]:
    if workspace is None:
        return [
            (
                "template_database_available",
                "FAIL",
                "workspace not provided; cannot check lib/local/library.sqlite",
            ),
            (
                "required_template_sources",
                "FAIL",
                "workspace not provided; cannot check required UVM template entries",
            ),
        ]

    workspace = workspace.resolve()
    db_path = workspace / LIB_ROOT / "local" / "library.sqlite"
    template_status: list[str] = []
    for template_id in REQUIRED_TEMPLATE_IDS:
        try:
            get_entry(workspace, template_id, expected_kind="template")
            template_status.append(f"{template_id}=PASS")
        except Exception:
            template_status.append(f"{template_id}=MISSING")

    return [
        (
            "template_database_available",
            "PASS" if db_path.is_file() else "FAIL",
            _normalize_rel_path(db_path),
        ),
        (
            "required_template_sources",
            "PASS" if all(item.endswith("=PASS") for item in template_status) else "FAIL",
            ", ".join(template_status),
        ),
    ]


def _loop2_intents(project: Path) -> dict[str, str]:
    path = project / "work/docparse" / "structured_spec" / "test_intent.yaml"
    if not path.is_file():
        return {}
    intent_by_req: dict[str, str] = {}
    active_section = ""
    active_id = ""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.endswith(":") and not line.startswith("-"):
            active_section = line[:-1]
            active_id = ""
            continue
        if active_section != "loop2":
            continue
        if line.startswith("- id:"):
            active_id = line.split(":", 1)[1].strip()
            continue
        if line.startswith("requirements:") and active_id:
            for req_id in _as_list(line.split(":", 1)[1].strip()):
                intent_by_req[req_id] = active_id
    return intent_by_req


def _all_bound_paths(req_bindings: dict[str, set[str]]) -> set[str]:
    paths: set[str] = set()
    for req_paths in req_bindings.values():
        paths.update(req_paths)
    return paths


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    text = str(value).strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip("\"'") for item in inner.split(",") if item.strip()]
    return [text]


def _normalize_rel_path(path: Any) -> str:
    return str(path).replace("\\", "/")


def _classify_artifact(path: str) -> tuple[str, str]:
    name = Path(path).name.lower()
    if path.endswith(".do"):
        return "sim_script", "run_control"
    if "reports/loop2" in path and path.endswith(".log"):
        return "log", "run_evidence"
    if "reports/loop2" in path and path.endswith(".md"):
        return "report", "closure_evidence"
    if "reports/loop2" in path and path.endswith(".txt"):
        return "coverage_report", "coverage_evidence"
    if "/assertions/" in path:
        return "assertion", "assertion"
    if "/seq_lib/" in path:
        return "uvm_sequence", "stimulus"
    if "scoreboard" in name:
        return "uvm_scoreboard", "checker"
    if "/cov/" in path or "coverage" in name:
        return "uvm_coverage", "coverage"
    if "/tests/" in path:
        return "uvm_test", "test"
    if "/agents/" in path:
        return "uvm_agent", "protocol_agent"
    if "/tb/" in path:
        return "uvm_tb", "harness"
    if "/cfg/" in path:
        return "uvm_config", "configuration"
    if "/env/" in path:
        return "uvm_env", "environment"
    return "artifact", "unknown"


def _classify_binding_role(path: str) -> str:
    return _classify_artifact(path)[1]


def _extract_value(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(1) if match else ""


def _has_evidence(evidence: list[dict[str, str]], evidence_type: str) -> bool:
    return any(item["evidence_type"] == evidence_type and item["status"] == "PASS" for item in evidence)


def _evidence_matches_artifact(evidence: dict[str, str], artifact_path: str) -> bool:
    if evidence["path"] == artifact_path:
        return True
    artifact_type = _classify_artifact(artifact_path)[0]
    if evidence["evidence_type"] in {"scoreboard_pass", "uvm_error_zero", "uvm_fatal_zero"}:
        return artifact_type in {"uvm_scoreboard", "uvm_test", "sim_script", "report"}
    if evidence["evidence_type"] in {"coverage_reported", "code_coverage_file"}:
        return artifact_type in {"uvm_coverage", "coverage_report", "report"}
    return False


def _resolve_project_path(project: Path, path: Path) -> Path:
    return path if path.is_absolute() else project / path
