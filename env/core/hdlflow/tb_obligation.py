"""Directed TB black-box obligation helpers."""

from __future__ import annotations

from pathlib import Path

from .obligations import load_obligations
from .project import require_project_instance


TB_OBLIGATIONS_REL = "work/loop1_rtl_tb/config/tb_obligations.yaml"


def load_tb_obligations(project_path: Path) -> list[dict[str, object]]:
    project = require_project_instance(project_path)
    return load_obligations(project / TB_OBLIGATIONS_REL)


def whitebox_only_passes(project_path: Path) -> list[str]:
    rows = load_tb_obligations(project_path)
    offenders: list[str] = []
    for row in rows:
        status = str(row.get("status") or "").lower()
        evidence_type = str(row.get("evidence_type") or row.get("allowed_whitebox_debug") or "").lower()
        if status in {"pass", "passed", "verified"} and "whitebox" in evidence_type:
            offenders.append(str(row.get("test_id") or row.get("operation_id") or row.get("requirement_id") or "unknown"))
    return offenders
