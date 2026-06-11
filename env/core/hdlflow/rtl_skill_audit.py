"""Executable RTL checks derived from the RTL architecture skill."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .layout import find_workspace_root
from .project import require_project_instance


RTL_SKILL_AUDIT_REL = "output/reports/loop1/rtl_skill_audit.md"
RTL_SKILL_REL = "env/rule/skills/rtl-architecture-and-gen/SKILL.md"
RTL_STYLE_GUIDE_REL = "env/rule/skills/rtl-architecture-and-gen/references/verilog-rtl-style-guide.md"

SYSTEMVERILOG_PATTERNS = (
    (re.compile(r"(?m)^\s*logic\b"), "SystemVerilog logic declaration"),
    (re.compile(r"\balways_ff\b"), "SystemVerilog always_ff"),
    (re.compile(r"\balways_comb\b"), "SystemVerilog always_comb"),
    (re.compile(r"\btypedef\s+enum\b"), "SystemVerilog typedef enum"),
    (re.compile(r"(?m)^\s*interface\b"), "SystemVerilog interface"),
    (re.compile(r"(?m)^\s*package\b"), "SystemVerilog package"),
)

RESPONSIBILITY_PATTERNS: dict[str, tuple[str, ...]] = {
    "axi_write_channel": (r"\bawvalid\b", r"\bwvalid\b", r"\bbvalid\b", r"\bawready\b", r"\bwready\b", r"\bwrite_fire\b"),
    "axi_read_channel": (r"\barvalid\b", r"\brvalid\b", r"\brdata\b", r"\barready\b", r"\bread_fire\b"),
    "command_control": (r"\bcmd[A-Za-z0-9_]*\b", r"\bcommand[A-Za-z0-9_]*\b", r"\bopcode[A-Za-z0-9_]*\b"),
    "tx_uart_datapath": (r"\btx[A-Za-z0-9_]*\b", r"\buart[A-Za-z0-9_]*\b", r"\bps_tx[A-Za-z0-9_]*\b"),
    "register_status": (r"\bstatus[A-Za-z0-9_]*\b", r"\breg[A-Za-z0-9_]*\b", r"\brresp\b", r"\bbresp\b", r"\baddr_\w+\b"),
    "memory_fifo": (r"\bfifo\b", r"\bmem\b", r"\bddr\b", r"\bwr_ptr\b", r"\brd_ptr\b"),
}


@dataclass(frozen=True)
class RtlFileAudit:
    rel_path: str
    sha256: str
    result: str
    issues: tuple[str, ...]


@dataclass(frozen=True)
class RtlSkillAuditResult:
    project: Path
    report_path: Path
    ok: bool
    file_results: tuple[RtlFileAudit, ...]
    errors: tuple[str, ...]
    skill_path: Path | None
    skill_sha256: str | None
    style_guide_path: Path | None
    style_guide_sha256: str | None


def run_rtl_skill_audit(project_path: Path, *, write_report: bool = True) -> RtlSkillAuditResult:
    """Audit RTL files against the platform RTL skill and write the gate report."""

    project = require_project_instance(project_path)
    workspace = _workspace_root(project)
    skill_path = _first_existing(
        workspace / RTL_SKILL_REL,
        workspace / "skills" / "rtl-architecture-and-gen" / "SKILL.md",
    )
    style_guide_path = _first_existing(
        workspace / RTL_STYLE_GUIDE_REL,
        workspace / "skills" / "rtl-architecture-and-gen" / "references" / "verilog-rtl-style-guide.md",
    )
    errors: list[str] = []
    if skill_path is None:
        errors.append(f"missing RTL skill file: {RTL_SKILL_REL}")
    if style_guide_path is None:
        errors.append(f"missing RTL style guide: {RTL_STYLE_GUIDE_REL}")

    rtl_dir = project / "output" / "rtl"
    rtl_files = sorted(rtl_dir.glob("*.v")) if rtl_dir.exists() else []
    forbidden_sv = []
    if rtl_dir.exists():
        forbidden_sv = sorted([*rtl_dir.rglob("*.sv"), *rtl_dir.rglob("*.svh")])
    if forbidden_sv:
        errors.append(
            "SystemVerilog RTL files are forbidden under output/rtl: "
            + ", ".join(_rel(project, path) for path in forbidden_sv[:8])
        )
    if not rtl_files:
        errors.append("missing RTL .v files under output/rtl")

    file_results = tuple(_audit_rtl_file(project, path) for path in rtl_files)
    ok = not errors and all(item.result == "PASS" for item in file_results)
    report_path = project / RTL_SKILL_AUDIT_REL
    result = RtlSkillAuditResult(
        project=project,
        report_path=report_path,
        ok=ok,
        file_results=file_results,
        errors=tuple(errors),
        skill_path=skill_path,
        skill_sha256=_sha256(skill_path) if skill_path else None,
        style_guide_path=style_guide_path,
        style_guide_sha256=_sha256(style_guide_path) if style_guide_path else None,
    )
    if write_report:
        _write_report(result)
    return result


def _audit_rtl_file(project: Path, path: Path) -> RtlFileAudit:
    text = path.read_text(encoding="utf-8", errors="ignore")
    code = _strip_verilog_comments(text)
    issues: list[str] = []

    module_match = re.search(r"(?m)^\s*module\s+([A-Za-z_][A-Za-z0-9_$]*)\b", code)
    raw_module_match = re.search(r"(?m)^\s*module\s+([A-Za-z_][A-Za-z0-9_$]*)\b", text)
    module_name = module_match.group(1) if module_match else ""
    header = text[: raw_module_match.start()] if raw_module_match else text[:1200]

    if not module_match:
        issues.append("missing primary module declaration")
    elif module_name != path.stem:
        issues.append(f"module name {module_name} does not match file name {path.stem}")

    for marker in ("// Module", "// Description", "// Scope:", "// Spec Trace:"):
        if marker not in header[:1200]:
            issues.append(f"missing required RTL header marker: {marker}")

    for pattern, label in SYSTEMVERILOG_PATTERNS:
        if pattern.search(code):
            issues.append(f"forbidden SystemVerilog construct: {label}")

    if re.search(r"(?m)^\s*(?:automatic\s+)?task\b|^\s*endtask\b|\btask\s+(?:automatic\s+)?[A-Za-z_]", code):
        issues.append("forbidden task/endtask declaration in RTL")

    if re.search(r"(?m)^\s*initial\b|\#\s*\d+|\bforce\b|\brelease\b|\bwait\s*\(|\bfork\b|\bjoin\b", code):
        issues.append("testbench-only timing/control construct appears in RTL")

    if re.search(r"\bend[ \t]+else\b", code):
        issues.append("else must start on its own line")

    always_blocks = _extract_always_blocks(code)
    if _is_top_module(path, module_name):
        if re.search(r"(?m)^\s*(always|initial|assign|function|task)\b|\bcase\s*\(", code):
            issues.append("project top module must be hierarchy-only and cannot own behavioral logic")

    for index, block in enumerate(always_blocks, start=1):
        block_issues = _audit_always_block(block, index)
        issues.extend(block_issues)

    return RtlFileAudit(
        rel_path=_rel(project, path),
        sha256=_sha256(path),
        result="PASS" if not issues else "FAIL",
        issues=tuple(issues),
    )


def _audit_always_block(block: str, index: int) -> list[str]:
    issues: list[str] = []
    block_l = block.lower()
    nonblank_lines = [line for line in block.splitlines() if line.strip()]
    categories = _responsibility_categories(block_l)

    sequential = bool(re.search(r"always\s*@\s*\([^)]*(?:posedge|negedge)", block_l))
    if sequential and _has_blocking_assignment(block):
        issues.append(f"always block {index} mixes blocking-style assignments in sequential logic")

    if len(nonblank_lines) >= 70 and len(categories) >= 4:
        issues.append(
            f"always block {index} is monolithic ({len(nonblank_lines)} lines) and owns multiple responsibilities: "
            + ", ".join(categories)
        )
    elif len(nonblank_lines) >= 100 and len(categories) >= 3:
        issues.append(
            f"always block {index} is too large for one ownership boundary ({len(nonblank_lines)} lines): "
            + ", ".join(categories)
        )

    if "case" in block_l and "default" not in block_l:
        issues.append(f"always block {index} contains a case statement without default")
    return issues


def _responsibility_categories(block_l: str) -> list[str]:
    categories: list[str] = []
    for category, patterns in RESPONSIBILITY_PATTERNS.items():
        if any(re.search(pattern, block_l) for pattern in patterns):
            categories.append(category)
    return categories


def _has_blocking_assignment(block: str) -> bool:
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("if ", "if(", "else", "case", "for ", "while ")):
            continue
        if re.search(r"(?<![<>=!])=(?!=)", stripped):
            return True
    return False


def _extract_always_blocks(code: str) -> list[str]:
    lines = code.splitlines()
    blocks: list[str] = []
    current: list[str] = []
    depth = 0
    in_block = False

    for line in lines:
        if not in_block and re.search(r"^\s*always\b", line):
            in_block = True
            current = []
            depth = 0
        if not in_block:
            continue

        current.append(line)
        depth += len(re.findall(r"\bbegin\b", line))
        depth -= len(re.findall(r"\bend\b", line))
        if len(current) == 1 and ";" in line and "begin" not in line:
            blocks.append("\n".join(current))
            in_block = False
            current = []
            continue
        if len(current) > 1 and depth <= 0:
            blocks.append("\n".join(current))
            in_block = False
            current = []

    if in_block and current:
        blocks.append("\n".join(current))
    return blocks


def _write_report(result: RtlSkillAuditResult) -> None:
    result.report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# RTL Skill Audit",
        "",
        "- generated_by: hdlflow.rtl_skill_audit",
        f"- project: {result.project.name}",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- result: {'PASS' if result.ok else 'FAIL'}",
        f"- skill_path: {_display_path(result.skill_path)}",
        f"- skill_sha256: {result.skill_sha256 or 'missing'}",
        f"- style_guide_path: {_display_path(result.style_guide_path)}",
        f"- style_guide_sha256: {result.style_guide_sha256 or 'missing'}",
        "",
        "## File Summary",
        "",
        "| File | SHA256 | Result | Issues |",
        "| --- | --- | --- | --- |",
    ]
    if result.file_results:
        for item in result.file_results:
            lines.append(f"| {item.rel_path} | {item.sha256} | {item.result} | {len(item.issues)} |")
    else:
        lines.append("| none | n/a | FAIL | 1 |")

    lines.extend(["", "## Errors", ""])
    lines.extend([f"- {error}" for error in result.errors] or ["- none"])
    lines.extend(["", "## Issues", ""])
    if result.file_results:
        for item in result.file_results:
            lines.extend([f"### {item.rel_path}", ""])
            lines.extend([f"- {issue}" for issue in item.issues] or ["- PASS"])
            lines.append("")
    else:
        lines.append("- no RTL files audited")
        lines.append("")

    result.report_path.write_text("\n".join(lines), encoding="utf-8")


def _strip_verilog_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//.*", "", text)


def _workspace_root(project: Path) -> Path:
    try:
        return find_workspace_root(project)
    except FileNotFoundError:
        return Path(__file__).resolve().parents[3]


def _first_existing(*paths: Path) -> Path | None:
    for path in paths:
        if path.is_file():
            return path
    return None


def _is_top_module(path: Path, module_name: str) -> bool:
    stem = path.stem.lower()
    name = module_name.lower()
    return stem.endswith("_top") or name.endswith("_top") or stem == "top"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(project: Path, path: Path) -> str:
    try:
        return path.relative_to(project).as_posix()
    except ValueError:
        return path.as_posix()


def _display_path(path: Path | None) -> str:
    if path is None:
        return "missing"
    return path.as_posix()
