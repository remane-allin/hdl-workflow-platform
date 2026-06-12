"""Collect source-bound facts for generated document snapshots."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ..config import load_project
from ..project import require_project_instance
from ..requirements_frontend import ACCEPTANCE_REL, SRS_REL
from ..simple_yaml import load_yaml


SOURCE_ROOTS = (
    "input/spec",
    "work/docparse/frontdoor",
    "work/docparse/structured_spec",
    "work/docparse/req_decompose",
    "work/docparse/architecture",
    "work/docparse/verification",
    "work/docparse/prototype",
    "work/docparse/review",
    "work/docparse/trace_matrix",
    "work/loop3_fpga_proto/board_tests",
    "work/loop3_fpga_proto/board_profiles",
    "work/gates",
    "work/change",
    "output/rtl",
    "output/tb",
    "output/uvm",
    "output/reports/loop1",
    "output/reports/loop2",
    "output/reports/loop3",
    "output/fpga/vivado/constraints",
    "output/fpga/vivado/scripts",
    "output/fpga/vivado/reports",
)

SOURCE_SUFFIXES = {".yaml", ".yml", ".json", ".md", ".v", ".sv", ".svh", ".xdc", ".tcl", ".rpt", ".log"}


def collect_project_data(project_path: Path) -> dict[str, Any]:
    project = require_project_instance(project_path)
    project_config = _load_project_config(project)
    srs = _load_data(project, SRS_REL)
    module_plan = _load_data(project, "work/docparse/architecture/module_plan.yaml")
    data = {
        "project_name": project.name,
        "ip_name": _ip_name(project, project_config, module_plan),
        "version": _version(project_config),
        "requirements": srs,
        "acceptance": _load_data(project, ACCEPTANCE_REL),
        "interface_spec": _load_data(project, "work/docparse/structured_spec/interface_spec.yaml"),
        "interface_timing": _load_data(project, "work/docparse/structured_spec/interface_timing.yaml"),
        "register_map": _load_data(project, "work/docparse/structured_spec/register_map.yaml"),
        "test_intent": _load_data(project, "work/docparse/structured_spec/test_intent.yaml"),
        "timing_rules": _load_data(project, "work/docparse/structured_spec/timing_rules.yaml"),
        "module_plan": module_plan,
        "interface_contracts": _load_data(project, "work/docparse/architecture/interface_contracts.yaml"),
        "dataflow": _load_data(project, "work/docparse/architecture/dataflow.yaml"),
        "state_machines": _load_data(project, "work/docparse/architecture/state_machines.yaml"),
        "timing_model": _load_data(project, "work/docparse/architecture/timing_model.yaml"),
        "verification_plan": _load_data(project, "work/docparse/verification/verification_plan.yaml"),
        "assertion_plan": _load_data(project, "work/docparse/verification/assertion_plan.yaml"),
        "coverage_plan": _load_data(project, "work/docparse/verification/coverage_plan.yaml"),
        "prototype_plan": _load_data(project, "work/docparse/prototype/prototype_plan.yaml"),
        "loop3_plan": _load_data(project, "work/loop3_fpga_proto/board_tests/prototype_plan.yaml"),
        "review_findings": _load_data(project, "work/docparse/review/role_findings.yaml"),
        "trace_req_to_arch": _load_data(project, "work/docparse/trace_matrix/req_to_arch.yaml"),
        "trace_req_to_rtl": _load_data(project, "work/docparse/trace_matrix/req_to_rtl.yaml"),
        "trace_req_to_test": _load_data(project, "work/docparse/trace_matrix/req_to_test.yaml"),
        "trace_req_to_proto": _load_data(project, "work/docparse/trace_matrix/req_to_proto.yaml"),
        "gate_status": _load_data(project, "work/gates/gate_status.json"),
        "output_manifest": _load_data(project, "output/manifest.yaml"),
        "rtl_modules": _scan_rtl(project),
        "tb_files": _scan_files(project, "output/tb", (".v",)),
        "uvm_files": _scan_files(project, "output/uvm", (".sv", ".svh")),
        "fpga_files": _scan_files(project, "output/fpga/vivado", (".xdc", ".tcl", ".rpt", ".bit")),
        "loop_reports": _scan_files(project, "output/reports", (".md", ".json", ".log", ".rpt")),
    }
    data["sources"] = source_hashes(project)
    return data


def source_hashes(project_path: Path) -> list[dict[str, str]]:
    project = require_project_instance(project_path)
    paths: list[Path] = []
    for rel in SOURCE_ROOTS:
        root = project / rel
        if root.is_file():
            paths.append(root)
        elif root.is_dir():
            paths.extend(_safe_rglob(root))
    try:
        paths.append(load_project(project).config_path)
    except Exception:
        pass
    entries: list[dict[str, str]] = []
    for path in sorted(set(paths), key=lambda item: _rel(project, item)):
        if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        if "_runtime" in path.parts or "workspace" in path.parts:
            continue
        entries.append({"path": _rel(project, path), "sha256": sha256_file(path)})
    return entries


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve_project_or_workspace_path(project_path: Path, rel: str) -> Path:
    project = require_project_instance(project_path)
    local = project / rel
    if local.exists():
        return local
    for ancestor in project.parents:
        candidate = ancestor / rel
        if candidate.exists():
            return candidate
    return local


def _safe_rglob(root: Path) -> list[Path]:
    result: list[Path] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            children = list(current.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_dir():
                if child.name in {"_runtime", "__pycache__", ".git"}:
                    continue
                stack.append(child)
            else:
                result.append(child)
    return result


def _scan_files(project: Path, rel_root: str, suffixes: tuple[str, ...]) -> list[dict[str, str]]:
    root = project / rel_root
    if not root.exists():
        return []
    rows: list[dict[str, str]] = []
    for path in _safe_rglob(root):
        if path.suffix.lower() not in suffixes:
            continue
        if "_runtime" in path.parts or "workspace" in path.parts:
            continue
        rows.append({"path": _rel(project, path), "sha256": sha256_file(path)})
    return sorted(rows, key=lambda item: item["path"])


def _scan_rtl(project: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in _scan_files(project, "output/rtl", (".v",)):
        path = project / item["path"]
        text = path.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r"\bmodule\s+(\w+)", text)
        rows.append(
            {
                "path": item["path"],
                "sha256": item["sha256"],
                "module": match.group(1) if match else path.stem,
                "ports": _parse_ports(text),
            }
        )
    return rows


def _parse_ports(text: str) -> list[dict[str, str]]:
    ports: list[dict[str, str]] = []
    for raw in text.splitlines():
        line = raw.split("//", 1)[0].strip().rstrip(",")
        match = re.match(r"(input|output|inout)\s+(?:wire|reg|logic)?\s*(\[[^\]]+\])?\s*(\w+)", line)
        if match:
            direction, width, name = match.groups()
            ports.append({"name": name, "direction": direction, "width": width or "1"})
    return ports


def _load_data(project: Path, rel: str) -> dict[str, Any]:
    path = project / rel
    if not path.exists():
        return {}
    try:
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = load_yaml(path)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _load_project_config(project: Path) -> dict[str, Any]:
    try:
        data = load_project(project).data
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _ip_name(project: Path, project_config: dict[str, Any], module_plan: dict[str, Any]) -> str:
    top = module_plan.get("top_level") if isinstance(module_plan.get("top_level"), dict) else {}
    for value in (
        top.get("name"),
        project_config.get("ip_name"),
        project_config.get("top_module"),
        project.name,
    ):
        if value:
            return str(value)
    return project.name


def _version(project_config: dict[str, Any]) -> str:
    version = project_config.get("version")
    if version:
        return str(version)
    project = project_config.get("project")
    if isinstance(project, dict) and project.get("version"):
        return str(project["version"])
    return "DRAFT"


def _rel(project: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")
