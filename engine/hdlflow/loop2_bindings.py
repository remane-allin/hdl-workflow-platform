"""Loop2 requirement-to-UVM binding database."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .library import get_entry
from .project import require_project_instance
from .simple_yaml import load_yaml


DEFAULT_DB_REL = Path("03_Loop2_UVM_Verify") / "_runtime" / "loop2_bindings.sqlite"
DEFAULT_PREFLIGHT_REL = Path("05_Output") / "reports" / "loop2" / "preflight" / "database_preflight.md"
REQUIRED_TEMPLATE_IDS = [
    "uvm.rkv_style_framework",
    "uvm.rkv_i2c_reference_profile",
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
    db_path = workspace / "library" / ".local" / "library.sqlite"
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

    lines.extend(["", "## Project Layout", ""])
    layout_checks = [
        ("05_Output/uvm", project / "05_Output" / "uvm"),
        ("05_Output/uvm/env", project / "05_Output" / "uvm" / "env"),
        ("05_Output/uvm/agents", project / "05_Output" / "uvm" / "agents"),
        ("05_Output/uvm/cov", project / "05_Output" / "uvm" / "cov"),
        ("05_Output/uvm/seq_lib", project / "05_Output" / "uvm" / "seq_lib"),
        ("05_Output/uvm/tests", project / "05_Output" / "uvm" / "tests"),
        ("05_Output/uvm/tb", project / "05_Output" / "uvm" / "tb"),
        ("03_Loop2_UVM_Verify/sim/regression.do", project / "03_Loop2_UVM_Verify" / "sim" / "regression.do"),
    ]
    for label, path in layout_checks:
        status = "PASS" if path.exists() else "MISSING"
        if status != "PASS":
            missing.append(label)
        lines.append(f"- {label}: {status}")

    template_files = list((project / "05_Output" / "uvm").rglob("*.template")) if (project / "05_Output" / "uvm").exists() else []
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
            "- Project-specific UVM files must still be completed from the normalized spec.",
            "",
            f"result: {'PASS' if not missing else 'FAIL'}",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return Loop2PreflightResult(report_path=report_path, missing_items=missing)


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
    db_path = workspace / "library" / ".local" / "library.sqlite"
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
                "req_to_test" if path in bound_paths else "scan",
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
            (req_id, intent_by_req.get(req_id, ""), "req_to_test.yaml"),
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
    trace_path = project / "01_DocParse" / "trace_matrix" / "req_to_test.yaml"
    if not trace_path.is_file():
        return {}
    data = load_yaml(trace_path)
    links = data.get("links", {})

    result: dict[str, set[str]] = {}
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
        return {}

    for req_id, raw_paths in items:
        paths = {_normalize_rel_path(path) for path in _as_list(raw_paths)}
        loop2_paths = {
            path
            for path in paths
            if path.startswith("05_Output/uvm/")
            or path.startswith("03_Loop2_UVM_Verify/")
            or path.startswith("05_Output/reports/loop2/")
        }
        if loop2_paths:
            result[str(req_id)] = loop2_paths
    return result


def _collect_loop2_artifacts(project: Path, req_bindings: dict[str, set[str]]) -> set[str]:
    paths = set(_all_bound_paths(req_bindings))
    for root in [
        project / "05_Output" / "uvm",
        project / "03_Loop2_UVM_Verify" / "sim",
        project / "05_Output" / "reports" / "loop2",
    ]:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".sv", ".svh", ".do", ".md", ".log", ".txt"}:
                paths.add(_normalize_rel_path(path.relative_to(project)))
    return paths


def _collect_evidence(project: Path) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    log_path = project / "05_Output" / "reports" / "loop2" / "modelsim_loop2.log"
    rel_log = "05_Output/reports/loop2/modelsim_loop2.log"
    if log_path.is_file():
        text = log_path.read_text(encoding="utf-8", errors="ignore")
        markers = [
            ("uvm_error_zero", "UVM_ERROR :    0", "PASS", "0"),
            ("uvm_fatal_zero", "UVM_FATAL :    0", "PASS", "0"),
            ("scoreboard_pass", "SCOREBOARD_PASS", "PASS", _extract_value(text, r"SCOREBOARD_PASS checks=([0-9]+)")),
            ("coverage_reported", "COVERAGE", "PASS", _extract_value(text, r"legal_scenario_cg=([0-9.]+)")),
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

    coverage_path = project / "05_Output" / "reports" / "loop2" / "modelsim_code_coverage.txt"
    if coverage_path.is_file():
        evidence.append(
            {
                "evidence_type": "code_coverage_file",
                "path": _normalize_rel_path(coverage_path.relative_to(project)),
                "marker": "coverage report exists",
                "status": "PASS",
                "value": str(coverage_path.stat().st_size),
            }
        )

    for report_name in [
        "loop2_uvm_regression_report.md",
        "coverage_index.md",
        "loop2_exit_report.md",
    ]:
        report_path = project / "05_Output" / "reports" / "loop2" / report_name
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
                "workspace not provided; cannot check library/.local/library.sqlite",
            ),
            (
                "required_template_sources",
                "FAIL",
                "workspace not provided; cannot check required UVM template entries",
            ),
        ]

    workspace = workspace.resolve()
    db_path = workspace / "library" / ".local" / "library.sqlite"
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
    path = project / "01_DocParse" / "structured_spec" / "test_intent.yaml"
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
