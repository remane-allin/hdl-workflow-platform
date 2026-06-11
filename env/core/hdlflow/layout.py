"""Workspace and project path contract for the env/lib/prj/local layout."""

from __future__ import annotations

from pathlib import Path


ENV_ROOT = Path("env")
CORE_ROOT = ENV_ROOT / "core"
RULE_ROOT = ENV_ROOT / "rule"
TOOL_ROOT = ENV_ROOT / "tool"
TEST_ROOT = ENV_ROOT / "test"

GLOBAL_RULE_ROOT = RULE_ROOT / "global"
PROJECT_DEFAULT_ROOT = RULE_ROOT / "project_default"
PROJECT_SCAFFOLD_ROOT = RULE_ROOT / "scaffold"
SKILLS_ROOT = RULE_ROOT / "skills"
PROJECTS_ROOT = Path("prj")
LIB_ROOT = Path("lib")
LOCAL_ROOT = Path("local")

WORKSPACE_CONFIG_REL = GLOBAL_RULE_ROOT / "workspace_config.yaml"
PROJECT_CONFIG_REL = Path("work") / "config" / "project_config.yaml"
PROJECT_GATES_REL = Path("work") / "gates"
PROJECT_MEMORY_REL = Path("work") / "memory"
PROJECT_CHANGE_REL = Path("work") / "change"


def find_workspace_root(path: Path) -> Path:
    """Find the nearest workspace root using the new env/rule marker."""

    resolved = path.resolve()
    candidates = [resolved, *resolved.parents]
    for candidate in candidates:
        if (candidate / WORKSPACE_CONFIG_REL).exists():
            return candidate
    if resolved.parent.name == PROJECTS_ROOT.name:
        return resolved.parent.parent
    raise FileNotFoundError(f"could not find workspace config from: {path}")


def project_config_path(project_path: Path) -> Path:
    return project_path.resolve() / PROJECT_CONFIG_REL


def project_memory_path(project_path: Path) -> Path:
    return project_path.resolve() / PROJECT_MEMORY_REL


def project_gates_path(project_path: Path) -> Path:
    return project_path.resolve() / PROJECT_GATES_REL


def project_change_path(project_path: Path) -> Path:
    return project_path.resolve() / PROJECT_CHANGE_REL
