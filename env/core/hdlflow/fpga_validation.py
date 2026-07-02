"""FPGA validation matrix helpers."""

from __future__ import annotations

from pathlib import Path

from .obligations import load_obligations
from .project import require_project_instance


FPGA_VALIDATION_MATRIX_REL = "work/loop3_fpga_proto/config/fpga_validation_matrix.yaml"
FPGA_CLAIM_LEVELS = {
    0: "Build / Implementation",
    1: "Wrapper / PS-PL Connectivity",
    2: "Protocol Bring-up / Connectivity Validation",
    3: "Requirement-Mapped FPGA Validation",
    4: "External Pin / Hardware Boundary",
}


def load_fpga_validation_matrix(project_path: Path) -> list[dict[str, object]]:
    project = require_project_instance(project_path)
    return load_obligations(project / FPGA_VALIDATION_MATRIX_REL, key="tests")


def hardcoded_pass_tests(project_path: Path) -> list[str]:
    offenders: list[str] = []
    for row in load_fpga_validation_matrix(project_path):
        if str(row.get("status") or "").lower() in {"hardcoded_pass", "forced_pass"}:
            offenders.append(str(row.get("test_id") or row.get("requirement_id") or "unknown"))
    return offenders
