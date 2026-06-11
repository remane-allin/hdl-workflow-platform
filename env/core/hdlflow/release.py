"""Release preflight helpers.

Release preflight is advisory. It reports what must be rerun or refreshed before
`final-audit --level release`; it does not promote develop evidence into release
evidence and it does not write generated design documents.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .project import require_project_instance
from .state_sync import NODE_ORDER


RELEASE_REPORT_REL = "output/reports/release/release_preflight.md"


@dataclass(frozen=True)
class ReleasePreflightResult:
    report_path: Path
    ok: bool
    blockers: list[str]
    warnings: list[str]
    required_commands: list[str]


def release_preflight(project_path: Path, *, write_report: bool = True) -> ReleasePreflightResult:
    project = require_project_instance(project_path)
    blockers: list[str] = []
    warnings: list[str] = []
    commands: list[str] = []

    manifests = _read_gate_manifests(project)
    manifest_by_node = {node: [item for item in manifests if item.get("node") == node] for node in NODE_ORDER}

    for node in NODE_ORDER[:-1]:
        release_manifest = _latest_level_manifest(manifest_by_node.get(node, []), "release")
        develop_manifest = _latest_level_manifest(manifest_by_node.get(node, []), "develop")
        if release_manifest:
            continue
        if develop_manifest:
            blockers.append(f"{node} has develop gate evidence but no release gate manifest")
        else:
            blockers.append(f"{node} has no passed release gate manifest")
        alias = _node_alias(node)
        commands.append(f"python -m hdlflow.cli run-gate --project <project> --node {alias} --level release")

    design_manifest = project / "output/reports/design/design_doc_manifest.json"
    if not design_manifest.exists():
        blockers.append("missing generated design document manifest")
        commands.insert(0, "python -m hdlflow.cli generate-design-doc --project <project>")

    output_manifest = project / "output/manifest.yaml"
    if not output_manifest.exists():
        blockers.append("missing output/manifest.yaml")
    else:
        text = output_manifest.read_text(encoding="utf-8", errors="ignore")
        for marker in ("loop1_gate: PASS", "loop2_gate: PASS", "loop3_gate: PASS"):
            if marker not in text:
                warnings.append(f"output manifest missing marker: {marker}")

    final_report = _latest_gate_report(project, "output")
    if final_report:
        text = final_report.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"^- result:\s*FAIL\s*$", text, flags=re.MULTILINE):
            warnings.append(f"latest final gate is failing: {_rel(project, final_report)}")

    commands.append("python -m hdlflow.cli final-audit --project <project> --level release")
    commands = _unique(commands)
    report = project / RELEASE_REPORT_REL
    if write_report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(_format_release_report(project, blockers, warnings, commands, manifest_by_node), encoding="utf-8")
    return ReleasePreflightResult(report_path=report, ok=not blockers, blockers=blockers, warnings=warnings, required_commands=commands)


def _read_gate_manifests(project: Path) -> list[dict[str, Any]]:
    root = project / "work/memory/recovery/rollback_manifests"
    rows: list[dict[str, Any]] = []
    if not root.exists():
        return rows
    for path in sorted(root.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict) or data.get("project") != project.name:
            continue
        if not data.get("node") or not data.get("level"):
            continue
        rows.append({**data, "_path": path})
    return rows


def _latest_level_manifest(rows: list[dict[str, Any]], level: str) -> dict[str, Any] | None:
    matches = [row for row in rows if str(row.get("level")) == level]
    if not matches:
        return None
    return sorted(matches, key=lambda item: str(item.get("created_at") or ""))[-1]


def _latest_gate_report(project: Path, node: str) -> Path | None:
    root = project / "output/reports/gates"
    if not root.exists():
        return None
    stems = {"output": "output"}.get(node, node.replace("/", "_"))
    matches = sorted(root.glob(f"{stems}_*.md"))
    return matches[-1] if matches else None


def _node_alias(node: str) -> str:
    return {
        "input": "input",
        "work/docparse": "docparse",
        "work/loop1_rtl_tb": "loop1",
        "work/loop2_uvm": "loop2",
        "work/loop3_fpga_proto": "loop3",
        "output": "final",
    }[node]


def _format_release_report(
    project: Path,
    blockers: list[str],
    warnings: list[str],
    commands: list[str],
    manifests_by_node: dict[str, list[dict[str, Any]]],
) -> str:
    lines = [
        "# Release Preflight",
        "",
        f"- project: {project.name}",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- result: {'PASS' if not blockers else 'BLOCKED'}",
        "",
        "## Gate Evidence",
        "",
    ]
    for node in NODE_ORDER:
        rows = manifests_by_node.get(node, [])
        levels = sorted({str(row.get("level")) for row in rows})
        lines.append(f"- {node}: {', '.join(levels) if levels else 'none'}")
    lines.extend(["", "## Blockers", ""])
    lines.extend([f"- {item}" for item in blockers] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {item}" for item in warnings] or ["- none"])
    lines.extend(["", "## Required Commands", ""])
    lines.extend([f"- `{item}`" for item in commands])
    lines.extend(
        [
            "",
            "## Guardrail",
            "",
            "- This preflight does not convert develop evidence into release evidence.",
            "- Generated design documents remain owned only by `generate-design-doc`.",
        ]
    )
    return "\n".join(lines) + "\n"


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _rel(project: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)
