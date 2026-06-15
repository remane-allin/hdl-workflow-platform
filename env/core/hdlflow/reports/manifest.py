"""Command and manifest writers for unified reports."""

from __future__ import annotations

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

from ..project import require_project_instance
from .constants import COMMAND_SCHEMA, REPORT_MANIFEST_SCHEMA, RUN_MANIFEST_SCHEMA, StageReportDefinition


def ensure_command_record(project_path: Path, definition: StageReportDefinition, *, command: list[str] | None = None, exit_code: int | None = None, change_id: str | None = None) -> Path:
    project = require_project_instance(project_path)
    path = project / definition.command_json
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().isoformat(timespec="seconds")
    payload = {
        "schema": COMMAND_SCHEMA,
        "project": project.name,
        "stage": definition.stage,
        "tool": definition.tool,
        "cwd": str(project),
        "command": command or [definition.tool],
        "start_time": now,
        "end_time": now,
        "exit_code": exit_code,
        "change_id": change_id,
        "inputs": [definition.log_rel],
        "outputs": [definition.report_md, definition.report_json],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    (project / definition.command_md).write_text(_command_markdown(payload), encoding="utf-8")
    return path


def write_current_manifest(project_path: Path, definition: StageReportDefinition) -> Path:
    project = require_project_instance(project_path)
    report_md = project / definition.report_md
    report_json = project / definition.report_json
    command_json = project / definition.command_json
    log_path = project / definition.log_rel
    payload: dict[str, Any] = {
        "schema": RUN_MANIFEST_SCHEMA,
        "stage": definition.stage,
        "command": _file_entry(project, command_json),
        "logs": [_file_entry(project, log_path)],
        "generated_reports": [_file_entry(project, report_md), _file_entry(project, report_json)],
    }
    path = project / definition.current_manifest
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_report_manifest(project_path: Path, definition: StageReportDefinition) -> Path:
    project = require_project_instance(project_path)
    path = project / definition.report_manifest
    source_manifest = project / definition.current_manifest
    payload = {
        "schema": REPORT_MANIFEST_SCHEMA,
        "stage": definition.report_type,
        "report_md": definition.report_md,
        "report_json": definition.report_json,
        "source_run_manifest": definition.current_manifest,
        "report_sha256": sha256_file(project / definition.report_md),
        "report_json_sha256": sha256_file(project / definition.report_json),
        "source_manifest_sha256": sha256_file(source_manifest) if source_manifest.exists() else "MISSING",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file_entry(project: Path, path: Path) -> dict[str, str]:
    rel = str(path.relative_to(project)).replace("\\", "/") if path.is_absolute() else str(path).replace("\\", "/")
    return {
        "path": rel,
        "sha256": sha256_file(path) if path.exists() else "MISSING",
    }


def _command_markdown(payload: dict[str, Any]) -> str:
    command = " ".join(str(item) for item in payload.get("command", []))
    return "\n".join(
        [
            "# Command Record",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Stage | `{payload.get('stage', '')}` |",
            f"| Tool | `{payload.get('tool', '')}` |",
            f"| Exit Code | `{payload.get('exit_code')}` |",
            f"| CWD | `{payload.get('cwd', '')}` |",
            "",
            "```text",
            command,
            "```",
            "",
        ]
    )
