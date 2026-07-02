"""Hook adapter utilities for semantic gate lifecycle integration."""

from __future__ import annotations

from pathlib import Path

from .semantic_gates import run_semantic_gates


def run_semantic_advisory_hook(project: Path, *, level: str = "develop") -> Path:
    """Run semantic gates in their configured mode and return the status path."""

    return run_semantic_gates(project, level=level, compile_active=False, write_status=True).status_path
