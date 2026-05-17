"""Project scaffold creation."""

from __future__ import annotations

import shutil
import re
from datetime import datetime
from pathlib import Path


PROJECT_NAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_-]*$")


def create_project(workspace: Path, name: str, force: bool = False) -> Path:
    if not PROJECT_NAME_RE.match(name):
        raise ValueError("project name must match ^[A-Za-z0-9_][A-Za-z0-9_-]*$")
    workspace = workspace.resolve()
    template = workspace / "templates" / "project"
    config_template = workspace / "config" / "templates" / "project" / "project_config.yaml"
    projects = workspace / "projects"
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

    config_target = workspace / "config" / "projects" / name / "project_config.yaml"
    config_temp_parent = workspace / "config" / "projects" / f".{name}.tmp"
    if temp_target.exists():
        shutil.rmtree(temp_target)
    if config_temp_parent.exists():
        shutil.rmtree(config_temp_parent)

    try:
        shutil.copytree(template, temp_target, ignore=shutil.ignore_patterns("*.template"))
        config_temp_parent.mkdir(parents=True, exist_ok=True)
        config_temp = config_temp_parent / "project_config.yaml"
        shutil.copy2(config_template, config_temp)
        _personalize_project(temp_target, config_temp, name)

        if target.exists() and force:
            target.rmdir()
        temp_target.replace(target)
        config_target.parent.mkdir(parents=True, exist_ok=True)
        if config_target.exists():
            config_target.unlink()
        config_temp.replace(config_target)
        try:
            config_temp_parent.rmdir()
        except OSError:
            pass
    except Exception:
        if temp_target.exists():
            shutil.rmtree(temp_target, ignore_errors=True)
        if config_temp_parent.exists():
            shutil.rmtree(config_temp_parent, ignore_errors=True)
        raise
    return target


def _personalize_project(project_path: Path, config_path: Path, name: str) -> None:
    replacements = {
        "name: change_me": f"name: {name}",
        "owner: change_me": "owner: project_local",
        "description: change_me": f"description: {name} HDL workflow project",
        "project: change_me": f"project: {name}",
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
