"""Architecture impact review helpers for merged requirement changes."""

from __future__ import annotations

from pathlib import Path


ARCHITECTURE_IMPACT_FILENAMES = (
    "architecture_impact_review.yaml",
    "design_replanning_record.md",
    "verification_replanning_record.md",
)


def required_change_artifacts(change_id: str) -> list[str]:
    return [f"work/docparse/change/{change_id}/{name}" for name in ARCHITECTURE_IMPACT_FILENAMES]


def missing_change_artifacts(project: Path, change_id: str) -> list[str]:
    return [rel for rel in required_change_artifacts(change_id) if not (project / rel).exists()]
