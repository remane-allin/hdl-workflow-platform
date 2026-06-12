"""Project repair diagnostics and safe mechanical migrations."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .gates import GENERATED_REQUIREMENT_FILES
from .project import require_project_instance
from .requirements_frontend import FRONTDOOR_REL
from .simple_yaml import load_yaml
from .validate import validate_project


FRONTDOOR_FILES = {
    "srs.yaml",
    "srs.md",
    "acceptance_criteria.yaml",
    "forbidden_designs.yaml",
    "open_questions.md",
}

REQ_DECOMPOSE_FILES = {
    "requirements.json",
    "requirements.md",
    "module_plan.md",
    "path_partition.md",
    "decomposition_notes.md",
}

DESIGN_REPORT_PREFIX = "output/docs"


@dataclass(frozen=True)
class RepairTicket:
    ticket_id: str
    category: str
    severity: str
    summary: str
    path: Path


@dataclass(frozen=True)
class RepairDiagnoseResult:
    report_path: Path
    tickets: list[RepairTicket]
    messages: list[str]

    @property
    def ok(self) -> bool:
        return not self.tickets


@dataclass(frozen=True)
class RepairApplyResult:
    ticket_id: str
    applied: bool
    messages: list[str]


def diagnose_repairs(project_path: Path, *, write_tickets: bool = True) -> RepairDiagnoseResult:
    project = require_project_instance(project_path)
    tickets: list[RepairTicket] = []
    messages: list[str] = []

    validation = validate_project(project)
    if not validation.ok:
        for message in validation.messages:
            if message.startswith("missing:"):
                tickets.append(
                    _ticket(
                        project,
                        "layout_missing",
                        "high",
                        message,
                        evidence=[message],
                        write_ticket=write_tickets,
                    )
                )

    spec_dir = project / "input/spec"
    if spec_dir.exists():
        generated_in_spec = sorted(path.name for path in spec_dir.iterdir() if path.is_file() and path.name in GENERATED_REQUIREMENT_FILES)
        frontdoor_hits = [name for name in generated_in_spec if name in FRONTDOOR_FILES]
        req_hits = [name for name in generated_in_spec if name in REQ_DECOMPOSE_FILES]
        if frontdoor_hits:
            tickets.append(
                _ticket(
                    project,
                    "frontdoor_layout_migration",
                    "high",
                    "generated front-door artifacts live under input/spec",
                    evidence=[f"input/spec/{name}" for name in frontdoor_hits],
                    write_ticket=write_tickets,
                )
            )
        if req_hits:
            tickets.append(
                _ticket(
                    project,
                    "req_decompose_layout_migration",
                    "medium",
                    "generated requirement decomposition artifacts live under input/spec",
                    evidence=[f"input/spec/{name}" for name in req_hits],
                    write_ticket=write_tickets,
                )
            )

    for path in sorted(project.glob("vivado*.log")) + sorted(project.glob("vivado*.jou")):
        tickets.append(
            _ticket(
                project,
                "project_root_tool_log",
                "medium",
                "Vivado log or journal is in the project root",
                evidence=[_rel(project, path)],
                write_ticket=write_tickets,
            )
        )

    latest_final = _latest_report(project, "output")
    if latest_final and "result: FAIL" in latest_final.read_text(encoding="utf-8", errors="ignore"):
        tickets.append(
            _ticket(
                project,
                "final_gate_blocked",
                "medium",
                "latest final gate report is failing",
                evidence=[_rel(project, latest_final)],
                write_ticket=write_tickets,
            )
        )

    messages.extend(f"{ticket.severity}: {ticket.category} - {ticket.summary}" for ticket in tickets)
    if not messages:
        messages.append("PASS no repair tickets detected")

    report_path = project / "work/repair/reports/repair_diagnose.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_format_diagnose_report(project, tickets), encoding="utf-8")
    return RepairDiagnoseResult(report_path=report_path, tickets=tickets, messages=messages)


def apply_repair_ticket(project_path: Path, *, ticket_id: str, dry_run: bool = False) -> RepairApplyResult:
    project = require_project_instance(project_path)
    ticket_path = project / "work/repair/tickets" / f"{ticket_id}.yaml"
    if not ticket_path.exists():
        raise FileNotFoundError(f"repair ticket not found: {ticket_path}")
    ticket = load_yaml(ticket_path)
    category = str(ticket.get("category") or "")
    if category not in {"frontdoor_layout_migration", "req_decompose_layout_migration"}:
        return RepairApplyResult(ticket_id=ticket_id, applied=False, messages=[f"unsupported repair category: {category}"])

    target_root = FRONTDOOR_REL if category == "frontdoor_layout_migration" else "work/docparse/req_decompose"
    evidence = ticket.get("evidence") if isinstance(ticket.get("evidence"), list) else []
    messages: list[str] = []
    quarantine = project / "work/repair/quarantine" / ticket_id
    if dry_run:
        messages.append("dry-run: no files changed")
    for rel in evidence:
        src = project / str(rel)
        if not src.exists() or not src.is_file():
            messages.append(f"skip missing source: {rel}")
            continue
        if _is_design_report(rel):
            messages.append(f"blocked design report repair target: {rel}")
            continue
        dst = project / target_root / src.name
        messages.append(f"migrate {rel} -> {target_root}/{src.name}")
        if dry_run:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        quarantine.parent.mkdir(parents=True, exist_ok=True)
        quarantine.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(quarantine / src.name))

    return RepairApplyResult(ticket_id=ticket_id, applied=not dry_run, messages=messages)


def _ticket(
    project: Path,
    category: str,
    severity: str,
    summary: str,
    *,
    evidence: list[str],
    write_ticket: bool,
) -> RepairTicket:
    safe_category = category.replace("_", "-")
    ticket_id = f"RT-{datetime.now().strftime('%Y%m%d%H%M%S%f')}-{safe_category}"
    path = project / "work/repair/tickets" / f"{ticket_id}.yaml"
    if write_ticket:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "ticket_id": ticket_id,
            "project": project.name,
            "category": category,
            "severity": severity,
            "summary": summary,
            "status": "open",
            "evidence": evidence,
            "guardrails": [
                "does_not_modify_gate_policy",
                "does_not_fabricate_gate_evidence",
                "does_not_write_generated_docset_documents",
            ],
        }
        path.write_text(_yaml_doc(payload), encoding="utf-8")
    return RepairTicket(ticket_id=ticket_id, category=category, severity=severity, summary=summary, path=path)


def _format_diagnose_report(project: Path, tickets: list[RepairTicket]) -> str:
    lines = [
        "# Repair Diagnose",
        "",
        f"- project: {project.name}",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- result: {'PASS' if not tickets else 'TICKETS_OPEN'}",
        "",
        "## Tickets",
        "",
    ]
    lines.extend([f"- {ticket.ticket_id} [{ticket.severity}/{ticket.category}] {ticket.summary}" for ticket in tickets] or ["- none"])
    lines.extend(
        [
            "",
            "## Guardrail",
            "",
            "- Repair commands must not hand-edit generated files under `output/docs/`.",
            "- Repair commands must not hand-edit `output/docs/manifests/docset_manifest.json`.",
        ]
    )
    return "\n".join(lines) + "\n"


def _latest_report(project: Path, stem: str) -> Path | None:
    root = project / "output/reports/gates"
    if not root.exists():
        return None
    matches = sorted(root.glob(f"{stem}_*.md"))
    return matches[-1] if matches else None


def _is_design_report(rel: object) -> bool:
    normalized = str(rel).replace("\\", "/").strip("/")
    return normalized == DESIGN_REPORT_PREFIX or normalized.startswith(f"{DESIGN_REPORT_PREFIX}/")


def _yaml_doc(data: dict[str, Any]) -> str:
    return "\n".join(_yaml_lines(data, 0)) + "\n"


def _yaml_lines(value: Any, indent: int) -> list[str]:
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


def _scalar(value: Any) -> str:
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
