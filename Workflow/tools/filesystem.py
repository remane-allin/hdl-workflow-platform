from __future__ import annotations

import json
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def replace_directory(staging: Path, target: Path) -> None:
    """Replace target with staging while retaining at most one previous directory."""
    target.parent.mkdir(parents=True, exist_ok=True)
    previous = target.with_name(f".{target.name}.previous")
    if previous.exists():
        shutil.rmtree(previous)
    if target.exists():
        os.replace(target, previous)
    try:
        os.replace(staging, target)
    except BaseException:
        if previous.exists() and not target.exists():
            os.replace(previous, target)
        raise
    if previous.exists():
        shutil.rmtree(previous)


def remove_owned(path: Path) -> None:
    def remove_read_only(function, target, error):
        if isinstance(error, PermissionError):
            os.chmod(target, stat.S_IWRITE)
            function(target)
            return
        raise error

    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, onexc=remove_read_only)
    else:
        if path.exists():
            os.chmod(path, stat.S_IWRITE)
        path.unlink(missing_ok=True)
