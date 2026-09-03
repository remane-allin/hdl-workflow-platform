from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from Workflow.core.contracts import ContractError, ProjectContext, ToolFailure
from .process import run_process
from .profile import resolve_tool


FORBIDDEN_RTL = (
    (re.compile(r"^\s*(?:always_ff|always_comb|typedef|interface)\b", re.MULTILINE), "SystemVerilog construct"),
    (re.compile(r"^\s*(?:(?:input|output|inout)\s+)?logic\b", re.MULTILINE), "SystemVerilog logic declaration"),
    (re.compile(r"^\s*(?:force|release)\b", re.MULTILINE), "non-synthesizable procedural construct"),
    (re.compile(r"\bend[ \t]+else\b"), "else must start on a new line after end"),
)


def reliable_rule_findings(project_root: Path, sources: list[str]) -> list[str]:
    findings: list[str] = []
    for relative in sources:
        path = project_root / relative
        text = path.read_text(encoding="utf-8", errors="replace")
        code = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        code = re.sub(r"//[^\n]*", "", code)
        if re.search(r"`default_nettype\s+none", text) is None:
            findings.append(f"{relative}: missing `default_nettype none")
        for pattern, label in FORBIDDEN_RTL:
            for match in pattern.finditer(code):
                line = code.count("\n", 0, match.start()) + 1
                findings.append(f"{relative}:{line}: {label}")
    return findings


def check_active_rtl(context: ProjectContext, design: dict[str, Any]) -> dict[str, Any]:
    sources = design["implementation"]["rtl"]["sources"]
    missing = [item for item in sources if not (context.project_root / item).is_file()]
    if missing:
        raise ContractError("missing active RTL: " + ", ".join(missing))
    findings = reliable_rule_findings(context.project_root, sources)
    if findings:
        raise ToolFailure("RTL reliable rule failure: " + "; ".join(findings[:10]))
    tool_root = context.project_root / "work" / "tool" / "rtl" / "xvlog"
    report_root = context.project_root / "output" / "report" / ".staging" / "rtl" / "rtl-tb"
    if tool_root.exists():
        import shutil as _shutil
        _shutil.rmtree(tool_root)
    tool_root.mkdir(parents=True)
    arguments = [resolve_tool(context.workflow_root, "xsim", "xvlog"), "--log", str(report_root / "xvlog.log")]
    arguments.extend(str(context.project_root / item) for item in sources)
    result = run_process(arguments, cwd=tool_root, log=report_root / "xvlog-console.log")
    if result.returncode != 0:
        raise ToolFailure("Verilog-2001 compilation failed")
    return {
        "status": "PASS",
        "source_count": len(sources),
        "rule_findings": findings,
        "raw_reports": ["rtl-tb/xvlog.log", "rtl-tb/xvlog-console.log"],
    }
