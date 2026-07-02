"""Project gate PASS invalidation helpers.

The platform treats `work/gates/pass_invalidation.json` as a hard truth
boundary: gate reports and rollback manifests created before that timestamp no
longer prove a PASS claim.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PASS_INVALIDATION_REL = Path("work") / "gates" / "pass_invalidation.json"


@dataclass(frozen=True)
class PassInvalidation:
    path: Path
    invalidated_at: datetime | None
    reason: str

    @property
    def active(self) -> bool:
        return self.path.exists()


def load_pass_invalidation(project: Path) -> PassInvalidation | None:
    path = project / PASS_INVALIDATION_REL
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        payload = {}
    invalidated_at = _parse_datetime(payload.get("invalidated_at")) if isinstance(payload, dict) else None
    reason = str(payload.get("reason") or "project PASS evidence invalidated") if isinstance(payload, dict) else "project PASS evidence invalidated"
    return PassInvalidation(path=path, invalidated_at=invalidated_at, reason=reason)


def pass_evidence_invalidated(project: Path, evidence_path: Path, *, created_at: str | None = None) -> bool:
    invalidation = load_pass_invalidation(project)
    if invalidation is None:
        return False
    if invalidation.invalidated_at is None:
        return True
    evidence_time = _parse_datetime(created_at)
    if evidence_time is None and evidence_path.exists():
        evidence_time = datetime.fromtimestamp(evidence_path.stat().st_mtime).astimezone()
    if evidence_time is None:
        return True
    return evidence_time.timestamp() <= invalidation.invalidated_at.timestamp()


def invalidation_detail(project: Path) -> str:
    invalidation = load_pass_invalidation(project)
    if invalidation is None:
        return ""
    stamp = invalidation.invalidated_at.isoformat() if invalidation.invalidated_at is not None else "unknown-time"
    return f"PASS evidence invalidated at {stamp}: {invalidation.reason}"


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.astimezone() if parsed.tzinfo is not None else parsed.astimezone()
