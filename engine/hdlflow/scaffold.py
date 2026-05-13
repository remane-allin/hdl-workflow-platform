"""Project scaffold creation."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


def create_project(workspace: Path, name: str, force: bool = False) -> Path:
    workspace = workspace.resolve()
    template = workspace / "templates" / "project"
    config_template = workspace / "config" / "templates" / "project" / "project_config.yaml"
    projects = workspace / "projects"
    target = projects / name

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
        target.mkdir(parents=True)

    shutil.copytree(template, target, dirs_exist_ok=True)
    config_target = workspace / "config" / "projects" / name / "project_config.yaml"
    config_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config_template, config_target)
    _personalize_project(target, config_target, name)
    return target


def _personalize_project(project_path: Path, config_path: Path, name: str) -> None:
    replacements = {
        "name: change_me": f"name: {name}",
        "owner: change_me": "owner: project_local",
        "description: change_me": f"description: {name} HDL workflow project",
        "project: change_me": f"project: {name}",
        "created_at: GENERATED_AT": f"created_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    }
    for path in [
        config_path,
        project_path / "project_scaffold.yaml",
        project_path / "05_Output" / "manifest.yaml",
        project_path / "memory" / "index.yaml",
    ]:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for old, new in replacements.items():
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")
