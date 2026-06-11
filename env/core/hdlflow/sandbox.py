"""Lightweight exploration sandbox.

Exploration artifacts are intentionally kept under work/explore. They can be
promoted into suggested next actions, but they are not gate evidence and they
never write generated design reports.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .project import require_project_instance


EXPLORE_ROOT_REL = "work/explore"


@dataclass(frozen=True)
class ExplorationResult:
    session_id: str
    path: Path
    messages: list[str]


def start_exploration(project_path: Path, *, title: str, objective: str = "") -> ExplorationResult:
    project = require_project_instance(project_path)
    session_id = _new_session_id(title)
    session_dir = project / EXPLORE_ROOT_REL / "sessions" / session_id
    session_dir.mkdir(parents=True, exist_ok=False)
    created_at = datetime.now().isoformat(timespec="seconds")
    metadata = {
        "schema_version": 1,
        "session_id": session_id,
        "project": project.name,
        "title": title,
        "objective": objective,
        "status": "open",
        "created_at": created_at,
        "guardrails": [
            "sandbox_not_gate_evidence",
            "sandbox_does_not_modify_formal_artifacts",
            "sandbox_does_not_write_generated_design_documents",
        ],
    }
    (session_dir / "session.yaml").write_text(_yaml_doc(metadata), encoding="utf-8")
    (session_dir / "notes.md").write_text(
        "\n".join(
            [
                f"# Exploration {session_id}",
                "",
                f"- title: {title}",
                f"- objective: {objective or 'unspecified'}",
                f"- created_at: {created_at}",
                "",
                "## Notes",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return ExplorationResult(
        session_id=session_id,
        path=session_dir,
        messages=[
            f"exploration_session: {session_id}",
            f"path: {_rel(project, session_dir)}",
            "guardrail: sandbox artifacts are not gate evidence",
        ],
    )


def add_exploration_note(project_path: Path, *, session_id: str, note: str) -> ExplorationResult:
    project = require_project_instance(project_path)
    session_dir = _session_dir(project, session_id)
    notes = session_dir / "notes.md"
    if not notes.exists():
        raise FileNotFoundError(f"exploration notes not found: {notes}")
    stamp = datetime.now().isoformat(timespec="seconds")
    with notes.open("a", encoding="utf-8") as handle:
        handle.write(f"- {stamp}: {note}\n")
    return ExplorationResult(
        session_id=session_id,
        path=notes,
        messages=[f"note_added: {_rel(project, notes)}"],
    )


def promote_exploration(project_path: Path, *, session_id: str, target: str = "change-request") -> ExplorationResult:
    project = require_project_instance(project_path)
    if target not in {"change-request", "frontdoor-note", "repair-ticket"}:
        raise ValueError("target must be one of: change-request, frontdoor-note, repair-ticket")
    session_dir = _session_dir(project, session_id)
    notes = session_dir / "notes.md"
    if not notes.exists():
        raise FileNotFoundError(f"exploration notes not found: {notes}")
    promotion_dir = project / EXPLORE_ROOT_REL / "promotions"
    promotion_dir.mkdir(parents=True, exist_ok=True)
    promotion_path = promotion_dir / f"{session_id}_{target}.md"
    promotion_path.write_text(_format_promotion(project, session_id, target, notes), encoding="utf-8")
    return ExplorationResult(
        session_id=session_id,
        path=promotion_path,
        messages=[
            f"promotion: {_rel(project, promotion_path)}",
            "guardrail: promotion records a recommendation only",
        ],
    )


def _format_promotion(project: Path, session_id: str, target: str, notes: Path) -> str:
    command = {
        "change-request": "python -m hdlflow.cli change-open --project <project> --title <title> --reason <reason>",
        "frontdoor-note": "refresh work/docparse/frontdoor with the formal requirements-frontdoor command path",
        "repair-ticket": "python -m hdlflow.cli repair-diagnose --project <project>",
    }[target]
    lines = [
        "# Exploration Promotion",
        "",
        f"- project: {project.name}",
        f"- session_id: {session_id}",
        f"- target: {target}",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- notes: {_rel(project, notes)}",
        "",
        "## Recommended Next Step",
        "",
        f"- `{command}`",
        "",
        "## Guardrail",
        "",
        "- This promotion is advisory and is not gate evidence.",
        "- It does not edit formal workflow artifacts.",
        "- Generated design documents remain owned only by `generate-design-doc`.",
    ]
    return "\n".join(lines) + "\n"


def _session_dir(project: Path, session_id: str) -> Path:
    normalized = session_id.strip()
    if not re.match(r"^EX-[0-9]{14}-[a-z0-9-]+$", normalized):
        raise ValueError(f"invalid exploration session id: {session_id}")
    session_dir = project / EXPLORE_ROOT_REL / "sessions" / normalized
    if not session_dir.exists():
        raise FileNotFoundError(f"exploration session not found: {session_dir}")
    return session_dir


def _new_session_id(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
    slug = slug[:40].strip("-") or "session"
    return f"EX-{datetime.now().strftime('%Y%m%d%H%M%S')}-{slug}"


def _yaml_doc(data: dict[str, object]) -> str:
    return "\n".join(_yaml_lines(data, 0)) + "\n"


def _yaml_lines(value: object, indent: int) -> list[str]:
    prefix = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.extend(_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {_scalar(item)}")
        return lines
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.extend(_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{prefix}- {_scalar(item)}")
        return lines
    return [f"{prefix}{_scalar(value)}"]


def _scalar(value: object) -> str:
    if value is None:
        return "null"
    text = str(value)
    if not text or any(char in text for char in ":#[]{}"):
        return json.dumps(text, ensure_ascii=False)
    return text


def _rel(project: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)
