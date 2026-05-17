"""Configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .simple_yaml import load_yaml


GLOBAL_CONFIG_FILES = {
    "workspace": "config/global/workspace_config.yaml",
    "gates": "config/global/gates/global_gate_rules.yaml",
    "toolchains": "config/global/toolchains/toolchains.yaml",
    "agents": "config/global/agents/requirements_frontend_roles.yaml",
    "naming": "config/global/naming/path_rules.yaml",
    "reports": "config/global/reports/report_policy.yaml",
    "snapshots": "config/global/snapshots/snapshot_policy.yaml",
}


@dataclass(frozen=True)
class WorkspaceConfig:
    root: Path
    data: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class ProjectConfig:
    path: Path
    config_path: Path
    data: dict[str, Any]


def load_workspace(workspace: Path) -> WorkspaceConfig:
    root = workspace.resolve()
    data: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for name, rel in GLOBAL_CONFIG_FILES.items():
        path = root / rel
        if not path.exists():
            missing.append(rel)
            continue
        data[name] = load_yaml(path)
    if missing:
        raise FileNotFoundError("missing global config files: " + ", ".join(missing))
    return WorkspaceConfig(root=root, data=data)


def load_project(project_path: Path) -> ProjectConfig:
    path = project_path.resolve()
    workspace_root = _find_workspace_root(path)
    config_path = workspace_root / "config" / "projects" / path.name / "project_config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"missing project_config.yaml: {config_path}")
    return ProjectConfig(path=path, config_path=config_path, data=load_yaml(config_path))


def _find_workspace_root(path: Path) -> Path:
    candidates = [path, *path.parents]
    for candidate in candidates:
        if (candidate / "config" / "global" / "workspace_config.yaml").exists():
            return candidate
    # Common case: Test/projects/<project_name>
    if path.parent.name == "projects":
        return path.parent.parent
    raise FileNotFoundError(f"could not find workspace config from: {path}")


def validate_config(workspace: WorkspaceConfig, project: ProjectConfig) -> list[str]:
    errors: list[str] = []

    workspace_name = workspace.data.get("workspace", {}).get("workspace")
    if not workspace_name:
        errors.append("workspace name is required")

    project_name = project.data.get("project", {}).get("name")
    if not project_name:
        errors.append("project.name is required")

    nodes = project.data.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        errors.append("nodes mapping is required")
        return errors

    expected = project.data.get("pipeline_expected", [])
    if not isinstance(expected, list):
        errors.append("pipeline_expected must be a list")
        expected = []

    missing_expected = [node for node in expected if node not in nodes]
    if missing_expected:
        errors.append("pipeline_expected contains missing node config: " + ", ".join(missing_expected))

    for node_name, node_cfg in nodes.items():
        if not isinstance(node_cfg, dict):
            errors.append(f"{node_name} config must be a mapping")
            continue
        for section_name in ("inputs", "outputs"):
            section = node_cfg.get(section_name, {})
            if section and not isinstance(section, dict):
                errors.append(f"{node_name}.{section_name} must be a mapping")
                continue
            for key, rel_path in section.items():
                if not isinstance(rel_path, str):
                    errors.append(f"{node_name}.{section_name}.{key} must be a relative path string")
                elif Path(rel_path).is_absolute() or ".." in Path(rel_path).parts:
                    errors.append(f"{node_name}.{section_name}.{key} must stay inside project: {rel_path}")
        errors.extend(_validate_node_path_policy(node_name, node_cfg))
        errors.extend(_validate_source_policy(node_name, node_cfg))
        errors.extend(_validate_skill_policy(workspace.root, node_name, node_cfg))

    gate_rules = workspace.data.get("gates", {}).get("gates", {})
    if not isinstance(gate_rules, dict) or not gate_rules:
        errors.append("global gate rules are required")

    return errors


def _validate_node_path_policy(node_name: str, node_cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    prototype_policy = node_cfg.get("prototype_policy", {})
    if isinstance(prototype_policy, dict):
        for key, value in prototype_policy.items():
            if key == "toolchain_config":
                continue
            if _looks_like_path_key(key):
                errors.extend(_validate_project_rel_value(f"{node_name}.prototype_policy.{key}", value, allow_glob=False))
    elif prototype_policy:
        errors.append(f"{node_name}.prototype_policy must be a mapping")

    evidence = node_cfg.get("evidence", {})
    if isinstance(evidence, dict):
        for section_name in ("reports", "artifacts"):
            section = evidence.get(section_name, {})
            if isinstance(section, dict):
                for key, value in section.items():
                    errors.extend(_validate_project_rel_value(f"{node_name}.evidence.{section_name}.{key}", value, allow_glob=False))
            elif section:
                errors.append(f"{node_name}.evidence.{section_name} must be a mapping")
        globs = evidence.get("globs", {})
        if isinstance(globs, dict):
            for key, value in globs.items():
                errors.extend(_validate_project_rel_value(f"{node_name}.evidence.globs.{key}", value, allow_glob=True))
        elif globs:
            errors.append(f"{node_name}.evidence.globs must be a mapping")
    elif evidence:
        errors.append(f"{node_name}.evidence must be a mapping")
    return errors


def _looks_like_path_key(key: str) -> bool:
    lowered = key.lower()
    return lowered.endswith(("_dir", "_root", "_report", "_log", "_plan", "_config", "_xdc", "_tcl", "_profiles")) or "path" in lowered


def _validate_project_rel_value(name: str, value: Any, *, allow_glob: bool) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        errors: list[str] = []
        for index, item in enumerate(value):
            errors.extend(_validate_project_rel_value(f"{name}[{index}]", item, allow_glob=allow_glob))
        return errors
    if not isinstance(value, str):
        return [f"{name} must be a relative path string"]
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return [f"{name} must stay inside project: {value}"]
    if not allow_glob and any("*" in part or "?" in part for part in path.parts):
        return [f"{name} must be a concrete project-relative path, not a glob: {value}"]
    return []


def _validate_source_policy(node_name: str, node_cfg: dict[str, Any]) -> list[str]:
    policy = node_cfg.get("source_policy", {})
    if not policy:
        return []
    if not isinstance(policy, dict):
        return [f"{node_name}.source_policy must be a mapping"]
    errors: list[str] = []
    for section_name, section in policy.items():
        if not isinstance(section, dict):
            errors.append(f"{node_name}.source_policy.{section_name} must be a mapping")
            continue
        root = section.get("root")
        if not root:
            errors.append(f"{node_name}.source_policy.{section_name}.root is required")
        else:
            errors.extend(_validate_project_rel_value(f"{node_name}.source_policy.{section_name}.root", root, allow_glob=False))
        for key in ("allowed_extensions", "forbidden_extensions", "template_extensions"):
            value = section.get(key, [])
            if value and not isinstance(value, list):
                errors.append(f"{node_name}.source_policy.{section_name}.{key} must be a list")
                continue
            for item in value or []:
                text = str(item)
                if not text.startswith("."):
                    errors.append(f"{node_name}.source_policy.{section_name}.{key} entries must start with '.': {text}")
    return errors


def _validate_skill_policy(workspace_root: Path, node_name: str, node_cfg: dict[str, Any]) -> list[str]:
    policy = node_cfg.get("skill_policy", {})
    if not policy:
        if node_name in {"02_Loop1_RTL_TB", "03_Loop2_UVM_Verify"}:
            return [f"{node_name}.skill_policy is required for Loop1/Loop2 closure"]
        return []
    if not isinstance(policy, dict):
        return [f"{node_name}.skill_policy must be a mapping"]

    required = policy.get("required_skills", {})
    if not isinstance(required, dict) or not required:
        return [f"{node_name}.skill_policy.required_skills must be a non-empty mapping"]

    errors: list[str] = []
    for skill_name, spec in required.items():
        if not isinstance(spec, dict):
            errors.append(f"{node_name}.skill_policy.required_skills.{skill_name} must be a mapping")
            continue
        path_value = spec.get("path") or f"skills/{skill_name}/SKILL.md"
        if not isinstance(path_value, str):
            errors.append(f"{node_name}.skill_policy.required_skills.{skill_name}.path must be a workspace-relative string")
            continue
        rel_path = Path(path_value)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            errors.append(f"{node_name}.skill_policy.required_skills.{skill_name}.path must stay inside workspace: {path_value}")
            continue
        if not (workspace_root / rel_path).is_file():
            errors.append(f"{node_name}.skill_policy.required_skills.{skill_name}.path not found: {path_value}")

        markers = spec.get("required_markers", [])
        if markers and not isinstance(markers, list):
            errors.append(f"{node_name}.skill_policy.required_skills.{skill_name}.required_markers must be a list")
            continue
        for marker in markers or []:
            if not isinstance(marker, str) or not marker.strip():
                errors.append(f"{node_name}.skill_policy.required_skills.{skill_name}.required_markers entries must be non-empty strings")
    return errors
