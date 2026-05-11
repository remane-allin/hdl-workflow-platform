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
    if workspace_name != "Test":
        errors.append(f"workspace name must be Test, got {workspace_name!r}")

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

    gate_rules = workspace.data.get("gates", {}).get("gates", {})
    if not isinstance(gate_rules, dict) or not gate_rules:
        errors.append("global gate rules are required")

    return errors
