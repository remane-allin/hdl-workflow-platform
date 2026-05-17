"""Shared project instance guards."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .simple_yaml import load_yaml


def require_project_instance(project_path: Path) -> Path:
    """Return a resolved project path after validating script-created markers.

    This guard is intentionally stricter than "directory exists" because many
    workflow commands write reports or generated files. It keeps those commands
    from accidentally mutating templates or arbitrary folders.
    """

    project = project_path.resolve()
    if not project.is_dir():
        raise FileNotFoundError(f"missing project directory: {project}")
    marker_path = project / "project_scaffold.yaml"
    if not marker_path.is_file():
        raise FileNotFoundError(f"missing project scaffold marker: {marker_path}")
    try:
        marker: dict[str, Any] = load_yaml(marker_path)
    except Exception as exc:
        raise ValueError(f"project scaffold marker is not parseable: {marker_path}: {exc}") from exc

    expected = {
        "schema_version": 1,
        "project": project.name,
        "creation_mode": "script_only",
        "template_source": "templates/project",
        "manual_project_directory_creation": "forbidden",
    }
    errors = [f"{key}={marker.get(key)!r}, expected {value!r}" for key, value in expected.items() if marker.get(key) != value]
    if not marker.get("created_by") or not marker.get("created_at"):
        errors.append("created_by and created_at are required")
    if errors:
        raise ValueError("invalid project scaffold marker: " + "; ".join(errors))
    if not (project / "05_Output").is_dir():
        raise FileNotFoundError(f"missing canonical output directory: {project / '05_Output'}")
    return project
