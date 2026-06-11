"""Project scaffold creation."""

from __future__ import annotations

import shutil
import re
import os
from datetime import datetime
from pathlib import Path

from .layout import PROJECT_CONFIG_REL, PROJECT_DEFAULT_ROOT, PROJECTS_ROOT, PROJECT_SCAFFOLD_ROOT


PROJECT_NAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_-]*$")
PROJECT_CREATE_ENTRYPOINT_ENV = "HDLFLOW_PROJECT_CREATE_ENTRYPOINT"
ALLOWED_PROJECT_CREATE_ENTRYPOINTS = {"new-hdlproject.ps1", "new_hdl_project.py"}


def create_project(workspace: Path, name: str, force: bool = False) -> Path:
    _require_official_project_entrypoint()
    if not PROJECT_NAME_RE.match(name):
        raise ValueError("project name must match ^[A-Za-z0-9_][A-Za-z0-9_-]*$")
    workspace = workspace.resolve()
    template = workspace / PROJECT_SCAFFOLD_ROOT
    config_template = workspace / PROJECT_DEFAULT_ROOT / "project_config.yaml"
    projects = workspace / PROJECTS_ROOT
    target = projects / name
    temp_target = projects / f".{name}.tmp"

    if not template.is_dir():
        raise FileNotFoundError(f"missing template directory: {template}")
    if not config_template.is_file():
        raise FileNotFoundError(f"missing project config template: {config_template}")

    projects.mkdir(parents=True, exist_ok=True)

    if target.exists():
        if not force:
            raise FileExistsError(f"project already exists: {target}")
        if any(target.iterdir()):
            raise FileExistsError(f"refusing to overwrite non-empty project: {target}")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)

    config_target = target / PROJECT_CONFIG_REL
    config_temp_parent = temp_target / PROJECT_CONFIG_REL.parent
    if temp_target.exists():
        shutil.rmtree(temp_target)

    try:
        shutil.copytree(template, temp_target, ignore=shutil.ignore_patterns("*.template"))
        config_temp_parent.mkdir(parents=True, exist_ok=True)
        config_temp = config_temp_parent / "project_config.yaml"
        shutil.copy2(config_template, config_temp)
        _personalize_project(temp_target, config_temp, name)

        if target.exists() and force:
            target.rmdir()
        shutil.move(str(temp_target), str(target))
    except Exception:
        if temp_target.exists():
            shutil.rmtree(temp_target, ignore_errors=True)
        raise
    return target


def _require_official_project_entrypoint() -> None:
    entrypoint = os.environ.get(PROJECT_CREATE_ENTRYPOINT_ENV, "")
    normalized = entrypoint.replace("\\", "/").rsplit("/", 1)[-1].lower()
    if normalized not in ALLOWED_PROJECT_CREATE_ENTRYPOINTS:
        allowed = ", ".join(sorted(ALLOWED_PROJECT_CREATE_ENTRYPOINTS))
        raise PermissionError(
            "project creation is script-only; use env/tool/scripts/New-HdlProject.ps1 "
            f"or env/tool/scripts/new_hdl_project.py ({PROJECT_CREATE_ENTRYPOINT_ENV}=<entrypoint>, allowed: {allowed})"
        )


def _personalize_project(project_path: Path, config_path: Path, name: str) -> None:
    entrypoint = _official_entrypoint_label()
    replacements = {
        "name: change_me": f"name: {name}",
        "owner: change_me": "owner: project_local",
        "description: change_me": f"description: {name} HDL workflow project",
        "project: change_me": f"project: {name}",
        "created_by: hdlflow.cli " + "init-project": f"created_by: {entrypoint}",
        "created_by: __PROJECT_ENTRYPOINT__": f"created_by: {entrypoint}",
        '"project": "change_me"': f'"project": "{name}"',
        "__PROJECT_NAME__": name,
        "created_at: GENERATED_AT": f"created_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    }
    text_suffixes = {".do", ".f", ".json", ".md", ".ps1", ".sv", ".template", ".tcl", ".vh", ".yaml", ".yml"}
    paths = [config_path]
    paths.extend(path for path in project_path.rglob("*") if path.is_file() and path.suffix in text_suffixes)

    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for old, new in replacements.items():
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")


def _official_entrypoint_label() -> str:
    entrypoint = os.environ.get(PROJECT_CREATE_ENTRYPOINT_ENV, "")
    normalized = entrypoint.replace("\\", "/")
    if normalized.lower().endswith("new-hdlproject.ps1"):
        return "env/tool/scripts/New-HdlProject.ps1"
    if normalized.lower().endswith("new_hdl_project.py"):
        return "env/tool/scripts/new_hdl_project.py"
    return normalized or "unknown"
