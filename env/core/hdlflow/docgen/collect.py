"""Collect source-bound facts for generated document snapshots."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ..config import load_project
from ..project import require_project_instance
from ..requirements_frontend import DOC_PROJECTION_REL
from ..simple_yaml import load_yaml


SOURCE_SUFFIXES = {".yaml", ".yml", ".json", ".md", ".v", ".sv", ".svh", ".xdc", ".tcl", ".rpt", ".log"}
RUNTIME_SOURCE_HASH_EXCLUDES = {
    "output/manifest.yaml",
    "work/gates/gate_status.json",
    "work/gates/release_state.json",
    "work/gates/semantic_gate_status.json",
    "work/gates/pass_invalidation.json",
}

SEMANTIC_SOURCE_RELS = (
    "work/docparse/frontdoor/baseline/active_requirements.yaml",
    "work/docparse/frontdoor/baseline/active_acceptance_criteria.yaml",
    "work/docparse/frontdoor/baseline/evidence_index.yaml",
    "work/docparse/architecture/functional_domain_model.yaml",
    "work/docparse/architecture/design_routing.yaml",
    "work/docparse/architecture/module_ownership_matrix.yaml",
    "work/docparse/verification/operation_model.yaml",
    "work/loop1_rtl_tb/trace_matrix/req_to_rtl_implementation.yaml",
    "work/loop1_rtl_tb/config/interface_contract.yaml",
    "work/loop1_rtl_tb/config/tb_obligations.yaml",
    "work/loop1_rtl_tb/config/wave_semantic_manifest.yaml",
    "work/loop2_uvm/config/uvm_obligations.yaml",
    "work/loop3_fpga_proto/config/fpga_validation_matrix.yaml",
)


def collect_project_data(project_path: Path) -> dict[str, Any]:
    project = require_project_instance(project_path)
    project_config = _load_project_config(project)
    doc_projection = _load_data(project, DOC_PROJECTION_REL)
    projected = _load_projected_sources(project, doc_projection)
    srs = projected.get("requirements", {})
    module_plan = projected.get("module_plan", {})
    data = {
        "project_name": project.name,
        "ip_name": _ip_name(project, project_config, module_plan),
        "version": _version(project_config),
        "doc_projection": doc_projection,
        "requirements": srs,
        "acceptance": projected.get("acceptance", {}),
        "interface_spec": projected.get("interface_spec", {}),
        "interface_timing": projected.get("interface_timing", {}),
        "register_map": projected.get("register_map", {}),
        "test_intent": projected.get("test_intent", {}),
        "timing_rules": projected.get("timing_rules", {}),
        "module_plan": module_plan,
        "interface_contracts": projected.get("interface_contracts", {}),
        "dataflow": projected.get("dataflow", {}),
        "state_machines": projected.get("state_machines", {}),
        "timing_model": projected.get("timing_model", {}),
        "verification_plan": projected.get("verification_plan", {}),
        "uvm_plan": projected.get("uvm_plan", {}),
        "assertion_plan": projected.get("assertion_plan", {}),
        "coverage_plan": projected.get("coverage_plan", {}),
        "prototype_plan": projected.get("prototype_plan", {}),
        "loop3_plan": projected.get("loop3_plan", {}),
        "review_findings": projected.get("review_findings", {}),
        "trace_req_to_design_intent": projected.get("trace_req_to_design_intent", {}),
        "trace_req_to_test_intent": projected.get("trace_req_to_test_intent", {}),
        "trace_req_to_uvm_intent": projected.get("trace_req_to_uvm_intent", {}),
        "trace_req_to_rtl": projected.get("trace_req_to_rtl", {}),
        "trace_req_to_test": projected.get("trace_req_to_directed_tb", {}),
        "trace_req_to_proto": projected.get("trace_req_to_fpga_evidence", {}),
        "gate_status": projected.get("gate_status", {}),
        "active_requirements": _load_data(project, "work/docparse/frontdoor/baseline/active_requirements.yaml"),
        "active_acceptance": _load_data(project, "work/docparse/frontdoor/baseline/active_acceptance_criteria.yaml"),
        "evidence_index": _load_data(project, "work/docparse/frontdoor/baseline/evidence_index.yaml"),
        "functional_domain_model": _load_data(project, "work/docparse/architecture/functional_domain_model.yaml"),
        "design_routing": _load_data(project, "work/docparse/architecture/design_routing.yaml"),
        "module_ownership_matrix": _load_data(project, "work/docparse/architecture/module_ownership_matrix.yaml"),
        "operation_model": _load_data(project, "work/docparse/verification/operation_model.yaml"),
        "req_to_rtl_implementation": _load_data(project, "work/loop1_rtl_tb/trace_matrix/req_to_rtl_implementation.yaml"),
        "interface_contract": _load_data(project, "work/loop1_rtl_tb/config/interface_contract.yaml"),
        "tb_obligations": _load_data(project, "work/loop1_rtl_tb/config/tb_obligations.yaml"),
        "wave_semantic_manifest": _load_data(project, "work/loop1_rtl_tb/config/wave_semantic_manifest.yaml"),
        "uvm_obligations": _load_data(project, "work/loop2_uvm/config/uvm_obligations.yaml"),
        "fpga_validation_matrix": _load_data(project, "work/loop3_fpga_proto/config/fpga_validation_matrix.yaml"),
        "semantic_gate_status": _load_data(project, "work/gates/semantic_gate_status.json"),
        "release_state": _load_data(project, "work/gates/release_state.json"),
        "output_manifest": projected.get("output_manifest", {}),
        "rtl_modules": _scan_rtl(project),
        "tb_files": _scan_files(project, "output/tb", (".v",)),
        "uvm_files": _scan_files(project, "output/uvm", (".sv", ".svh")),
        "fpga_files": _scan_files(project, "output/fpga/vivado", (".xdc", ".tcl", ".rpt", ".bit")),
        "loop_reports": _scan_files(project, "output/reports", (".md", ".json", ".log", ".rpt")),
    }
    data["sources"] = source_hashes(project, projection=doc_projection)
    return data


def source_hashes(project_path: Path, *, projection: dict[str, Any]) -> list[dict[str, str]]:
    project = require_project_instance(project_path)
    paths: list[Path] = []
    paths.append(project / DOC_PROJECTION_REL)
    for source in _projection_sources(projection):
        rel = str(source.get("path") or "").strip()
        if rel and rel not in RUNTIME_SOURCE_HASH_EXCLUDES:
            paths.append(project / rel)
    for rel in SEMANTIC_SOURCE_RELS:
        paths.append(project / rel)
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


def _projection_sources(projection: dict[str, Any]) -> list[dict[str, Any]]:
    documents = projection.get("documents")
    if not isinstance(documents, dict):
        return []
    sources: list[dict[str, Any]] = []
    for spec in documents.values():
        if not isinstance(spec, dict):
            continue
        for source in spec.get("sources", []):
            if isinstance(source, dict):
                sources.append(source)
    return sources


def _load_projected_sources(project: Path, projection: dict[str, Any]) -> dict[str, dict[str, Any]]:
    loaded: dict[str, dict[str, Any]] = {}
    for source in _projection_sources(projection):
        source_id = str(source.get("id") or "").strip()
        source_path = str(source.get("path") or "").strip()
        if not source_id or not source_path or source_id in loaded:
            continue
        loaded[source_id] = _load_data(project, source_path)
    return loaded


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
