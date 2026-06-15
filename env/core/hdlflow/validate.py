"""Project layout validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .simple_yaml import load_yaml


REQUIRED_PATHS = [
    "project_scaffold.yaml",
    "work/memory/00_global/PROJECT_BRIEF.md",
    "work/memory/00_global/CURRENT_STATE.md",
    "work/memory/00_global/ACTIVE_PLAN.md",
    "work/memory/00_global/PLAN_FINDINGS.md",
    "work/memory/00_global/PLAN_ERRORS.md",
    "work/memory/index.yaml",
    "work/memory/active_versions.md",
    "work/memory/archive",
    "work/memory/transient",
    "work/memory/recovery/checkpoints",
    "work/memory/recovery/rollback_manifests",
    "work/memory/recovery/failure_records",
    "work/memory/00_global/iterations.md",
    "work/memory/00_global/archive",
    "work/memory/00_global/transient",
    "work/memory/01_docparse/iterations.md",
    "work/memory/01_docparse/archive",
    "work/memory/01_docparse/transient",
    "work/memory/02_loop1/iterations.md",
    "work/memory/02_loop1/archive",
    "work/memory/02_loop1/transient",
    "work/memory/03_loop2/iterations.md",
    "work/memory/03_loop2/archive",
    "work/memory/03_loop2/transient",
    "work/memory/04_loop3/iterations.md",
    "work/memory/04_loop3/archive",
    "work/memory/04_loop3/transient",
    "work/change/requests",
    "work/change/impact_analysis",
    "work/change/approvals",
    "work/change/trace_updates",
    "input/spec",
    "work/docparse/frontdoor",
    "work/docparse/frontdoor/srs.yaml",
    "work/docparse/frontdoor/acceptance_criteria.yaml",
    "work/docparse/structured_spec",
    "work/docparse/req_decompose",
    "work/docparse/architecture",
    "work/docparse/verification",
    "work/docparse/prototype",
    "work/docparse/review",
    "work/docparse/trace_matrix",
    "work/docparse/doc_projection.yaml",
    "work/docparse/trace_matrix/req_to_design_intent.yaml",
    "work/docparse/trace_matrix/req_to_test_intent.yaml",
    "work/loop1_rtl_tb/sim",
    "work/loop1_rtl_tb/_runtime",
    "work/loop2_uvm/sim",
    "work/loop2_uvm/_runtime",
    "work/loop2_uvm/bug_tracking",
    "work/loop2_uvm/coverage_tracking",
    "work/loop3_fpga_proto/scripts",
    "work/loop3_fpga_proto/_runtime",
    "work/loop3_fpga_proto/board_tests/prototype_plan.yaml",
    "work/loop3_fpga_proto/board_tests/board_test_config.yaml",
    "output/rtl",
    "output/tb",
    "output/uvm",
    "output/sim",
    "output/sim/loop1",
    "output/sim/loop1/wave",
    "output/fpga",
    "output/fpga/vivado",
    "output/fpga/vivado/project",
    "output/fpga/vivado/scripts",
    "output/fpga/vivado/constraints",
    "output/fpga/vivado/bitstream",
    "output/fpga/vivado/hw_platform",
    "output/fpga/vivado/reports",
    "output/fpga/vivado/logs",
    "output/fpga/vitis",
    "output/fpga/vitis/workspace",
    "output/fpga/vitis/src",
    "output/fpga/vitis/platform",
    "output/fpga/vitis/apps",
    "output/fpga/vitis/boot",
    "output/fpga/vitis/reports",
    "output/reports",
    "output/reports/loop3/preflight",
    "output/manifest.yaml",
    "work/archive",
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

    scaffold_errors = _validate_scaffold_marker(project_path)
    if scaffold_errors:
        messages.append(f"FAIL: {project_path}")
        messages.extend(f"project_scaffold: {error}" for error in scaffold_errors)
        return ValidationResult(False, messages)

    waiver_errors = _validate_coverage_waiver_schema(project_path)
    if waiver_errors:
        messages.append(f"FAIL: {project_path}")
        messages.extend(f"coverage_waiver: {error}" for error in waiver_errors)
        return ValidationResult(False, messages)

    messages.append(f"PASS: {project_path}")
    messages.append(f"checked_paths: {len(REQUIRED_PATHS)}")
    return ValidationResult(True, messages)


def _validate_scaffold_marker(project_path: Path) -> list[str]:
    path = project_path / "project_scaffold.yaml"
    try:
        data = load_yaml(path)
    except Exception as exc:
        return [f"not parseable: {exc}"]
    expected = {
        "schema_version": 1,
        "project": project_path.name,
        "creation_mode": "script_only",
        "template_source": "env/rule/scaffold",
        "manual_project_directory_creation": "forbidden",
    }
    errors = [f"{key} must be {value!r}, got {data.get(key)!r}" for key, value in expected.items() if data.get(key) != value]
    for key in ["created_by", "created_at"]:
        if not data.get(key):
            errors.append(f"{key} is required")
    return errors


def _validate_coverage_waiver_schema(project_path: Path) -> list[str]:
    path = project_path / "work" / "gates" / "coverage_waiver.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"not parseable: {exc}"]
    if not isinstance(data, dict):
        return ["must be a JSON object"]
    if data.get("schema_version") != 2:
        return ["schema_version must be 2 for row-level coverage waiver records"]
    waivers = data.get("waivers")
    if not isinstance(waivers, list):
        return ["waivers must be a list"]
    errors: list[str] = []
    for index, item in enumerate(waivers):
        if not isinstance(item, dict):
            errors.append(f"waivers[{index}] must be an object")
            continue
        missing = [field for field in ("item", "classification", "status", "evidence") if not item.get(field)]
        if missing:
            errors.append(f"waivers[{index}] missing required field(s): {', '.join(missing)}")
    return errors
