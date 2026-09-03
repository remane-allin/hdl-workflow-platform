from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from Workflow.core.contracts import ContractError, validate_design_shape
from .filesystem import read_json


ID_PREFIX = {
    "requirements": "REQ-",
    "architecture": "ARCH-",
    "interfaces": "IF-",
    "budgets": "BUD-",
    "verification": "VER-",
}


def load_design(path: Path) -> dict[str, Any]:
    return validate_design_shape(read_json(path))


def _items(section: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(section, list):
        values = section
    elif isinstance(section, dict):
        values = section.get(key, [])
    else:
        values = []
    if not isinstance(values, list) or not all(isinstance(item, dict) for item in values):
        raise ContractError(f"{key} must be a list of objects")
    return values


def _project_relative(value: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(value, str) or not value:
        errors.append(f"{label} must be a non-empty project-relative path")
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        errors.append(f"{label} is not project-relative: {value}")
        return None
    return path


def validate_design(
    document: dict[str, Any],
    project_root: Path | None = None,
    project_id: str | None = None,
) -> list[str]:
    design = validate_design_shape(document)
    errors: list[str] = []
    project = design["project"]
    if project_id is not None and project.get("project_id") != project_id:
        errors.append("project.project_id must match the selected prj directory")
    if project.get("rtl_language") != "Verilog-2001":
        errors.append("project.rtl_language must be Verilog-2001")
    seen: set[str] = set()
    for section_name, prefix in ID_PREFIX.items():
        key = "items" if section_name != "verification" else "cases"
        for item in _items(design[section_name], key):
            identifier = item.get("id")
            if not isinstance(identifier, str) or not identifier.startswith(prefix):
                errors.append(f"{section_name} item has invalid id: {identifier!r}")
            elif identifier in seen:
                errors.append(f"duplicate cross-module id: {identifier}")
            else:
                seen.add(identifier)
    implementation = design["implementation"]
    for key in ("rtl", "constraints", "verification_sources", "vivado", "vitis"):
        if not isinstance(implementation.get(key), dict):
            errors.append(f"implementation.{key} is required")
    rtl = implementation.get("rtl", {})
    sources = rtl.get("sources", [])
    if not isinstance(sources, list) or not sources:
        errors.append("implementation.rtl.sources must be a non-empty ordered list")
    elif any(not isinstance(item, str) or not item.endswith(".v") for item in sources):
        errors.append("all active RTL sources must be explicit .v paths")
    elif len(sources) != len(set(sources)):
        errors.append("implementation.rtl.sources must not contain duplicates")
    if project_root is not None:
        verification = implementation.get("verification_sources", {})
        vivado = implementation.get("vivado", {})
        required_files: list[tuple[Any, str]] = []
        required_files.extend((item, "implementation.rtl.sources") for item in sources)
        required_files.extend(
            (item, "implementation.constraints.sources")
            for item in implementation.get("constraints", {}).get("sources", [])
        )
        required_files.append((verification.get("top_file"), "implementation.verification_sources.top_file"))
        required_files.extend(
            (item, "implementation.verification_sources.models")
            for item in verification.get("models", [])
        )
        required_files.extend(
            (item.get("path"), "implementation.verification_sources.initialization_files.path")
            for item in verification.get("initialization_files", [])
            if isinstance(item, dict)
        )
        required_files.extend((item, "implementation.vivado.ip") for item in vivado.get("ip", []))
        required_files.append((vivado.get("project_script"), "implementation.vivado.project_script"))
        vitis = implementation.get("vitis", {})
        if vitis.get("enabled"):
            required_files.append((vitis.get("script"), "implementation.vitis.script"))
        for value, label in required_files:
            relative = _project_relative(value, label, errors)
            if relative is not None and not (project_root / relative).is_file():
                errors.append(f"declared implementation file is missing: {relative.as_posix()}")

        required_directories: list[tuple[Any, str]] = []
        required_directories.extend(
            (item, "implementation.rtl.include_dirs") for item in rtl.get("include_dirs", [])
        )
        required_directories.extend(
            (item, "implementation.verification_sources.include_dirs")
            for item in verification.get("include_dirs", [])
        )
        required_directories.extend(
            (item, "implementation.verification_sources.data_roots")
            for item in verification.get("data_roots", [])
        )
        if vitis.get("enabled"):
            required_directories.append((vitis.get("source_dir"), "implementation.vitis.source_dir"))
        for value, label in required_directories:
            relative = _project_relative(value, label, errors)
            if relative is not None and not (project_root / relative).is_dir():
                errors.append(f"declared implementation directory is missing: {relative.as_posix()}")

        relative_only = [
            (vivado.get("xpr"), "implementation.vivado.xpr"),
            (vivado.get("results", {}).get("bitstream"), "implementation.vivado.results.bitstream"),
            (vivado.get("results", {}).get("xsa"), "implementation.vivado.results.xsa"),
            (vivado.get("results", {}).get("checkpoint"), "implementation.vivado.results.checkpoint"),
        ]
        if vitis.get("enabled"):
            relative_only.extend(
                [
                    (vitis.get("workspace"), "implementation.vitis.workspace"),
                    (vitis.get("xsa"), "implementation.vitis.xsa"),
                    (vitis.get("results", {}).get("elf"), "implementation.vitis.results.elf"),
                ]
            )
        for value, label in relative_only:
            if value:
                _project_relative(value, label, errors)

        top_file = verification.get("top_file")
        if isinstance(top_file, str) and not top_file.endswith(".v"):
            errors.append("the formal verification top must be a Verilog .v file")
        tb_root = project_root / "output" / "tb"
        if tb_root.is_dir() and isinstance(top_file, str):
            formal_tops = [path for path in tb_root.glob("*.v") if path.is_file()]
            declared = (project_root / top_file).resolve(strict=False)
            extras = [path for path in formal_tops if path.resolve(strict=False) != declared]
            if extras:
                errors.append("output/tb must contain only one formal .v top; use include files for helpers")
    text = str(design).lower()
    if re.search(r"develop(ment)? later|开发(过程)?中再|待开发时", text):
        errors.append("structural decisions cannot be deferred to development")
    return errors


def required_case_ids(document: dict[str, Any]) -> list[str]:
    return [
        item["id"] for item in _items(document["verification"], "cases")
        if item.get("stage", "verify") == "verify"
    ]
