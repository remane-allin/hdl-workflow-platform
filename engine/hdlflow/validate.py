"""Project layout validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


REQUIRED_PATHS = [
    "project_scaffold.yaml",
    "memory/00_global/PROJECT_BRIEF.md",
    "memory/00_global/CURRENT_STATE.md",
    "memory/index.yaml",
    "memory/active_versions.md",
    "memory/archive",
    "memory/transient",
    "memory/recovery/checkpoints",
    "memory/recovery/rollback_manifests",
    "memory/recovery/failure_records",
    "memory/00_global/iterations.md",
    "memory/00_global/archive",
    "memory/00_global/transient",
    "memory/01_docparse/iterations.md",
    "memory/01_docparse/archive",
    "memory/01_docparse/transient",
    "memory/02_loop1/iterations.md",
    "memory/02_loop1/archive",
    "memory/02_loop1/transient",
    "memory/03_loop2/iterations.md",
    "memory/03_loop2/archive",
    "memory/03_loop2/transient",
    "memory/04_loop3/iterations.md",
    "memory/04_loop3/archive",
    "memory/04_loop3/transient",
    "change_control/requests",
    "change_control/impact_analysis",
    "change_control/approvals",
    "change_control/trace_updates",
    "00_SPEC/raw_docs",
    "00_SPEC/requirements",
    "01_DocParse/structured_spec",
    "01_DocParse/req_decompose",
    "01_DocParse/trace_matrix",
    "02_Loop1_RTL_TB/sim",
    "02_Loop1_RTL_TB/_runtime",
    "03_Loop2_UVM_Verify/sim",
    "03_Loop2_UVM_Verify/_runtime",
    "03_Loop2_UVM_Verify/bug_tracking",
    "03_Loop2_UVM_Verify/coverage_tracking",
    "04_Loop3_FPGA_Prototype/scripts",
    "04_Loop3_FPGA_Prototype/_runtime",
    "04_Loop3_FPGA_Prototype/board_tests/prototype_plan.yaml",
    "04_Loop3_FPGA_Prototype/board_tests/board_test_config.yaml",
    "05_Output/rtl",
    "05_Output/tb",
    "05_Output/uvm",
    "05_Output/fpga",
    "05_Output/fpga/vivado",
    "05_Output/fpga/vivado/project",
    "05_Output/fpga/vivado/scripts",
    "05_Output/fpga/vivado/constraints",
    "05_Output/fpga/vivado/bitstream",
    "05_Output/fpga/vivado/hw_platform",
    "05_Output/fpga/vivado/reports",
    "05_Output/fpga/vitis",
    "05_Output/fpga/vitis/workspace",
    "05_Output/fpga/vitis/src",
    "05_Output/fpga/vitis/platform",
    "05_Output/fpga/vitis/apps",
    "05_Output/fpga/vitis/boot",
    "05_Output/fpga/vitis/reports",
    "05_Output/reports",
    "05_Output/reports/loop3/preflight",
    "05_Output/manifest.yaml",
    "_archive",
]


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    messages: list[str]


def validate_project(project_path: Path) -> ValidationResult:
    project_path = project_path.resolve()
    messages: list[str] = []

    if not project_path.is_dir():
        return ValidationResult(False, [f"missing project directory: {project_path}"])

    missing = [rel for rel in REQUIRED_PATHS if not (project_path / rel).exists()]
    if missing:
        messages.append(f"FAIL: {project_path}")
        messages.extend(f"missing: {rel}" for rel in missing)
        return ValidationResult(False, messages)

    messages.append(f"PASS: {project_path}")
    messages.append(f"checked_paths: {len(REQUIRED_PATHS)}")
    return ValidationResult(True, messages)
