from __future__ import annotations

from pathlib import Path
from typing import Any

from Workflow.core.contracts import ContractError, ProjectContext, WorkflowError
from .process import run_process
from .profile import load_profiles, resolve_tool


def _vitis_failure(log: Path) -> str | None:
    text = log.read_text(encoding="utf-8", errors="replace")
    if "Traceback (most recent call last)" not in text:
        return None
    exceptions = [line.strip() for line in text.splitlines() if line.strip().startswith(("Exception:", "RuntimeError:", "ValueError:", "AttributeError:"))]
    return exceptions[-1] if exceptions else "Vitis Python script raised an exception"


def build_vitis(context: ProjectContext, design: dict[str, Any]) -> dict[str, Any]:
    configuration = design["implementation"]["vitis"]
    if not configuration.get("enabled"):
        return {"status": "NOT_APPLICABLE"}
    script = context.project_root / configuration["script"]
    xsa = context.project_root / configuration["xsa"]
    if not script.is_file() or not xsa.is_file():
        raise ContractError("Vitis requires the registered script and current XSA")
    tool_root = context.project_root / "work" / "tool" / "release" / "vitis"
    report_root = context.project_root / "output" / "report" / ".staging" / "release" / "release"
    result = run_process(
        [resolve_tool(context.workflow_root, "vitis", "vitis"), "-s", str(script), "--", str(context.design_path)],
        cwd=tool_root,
        log=report_root / "vitis.log",
        timeout=load_profiles(context.workflow_root)["vitis"]["timeout_seconds"],
    )
    script_failure = _vitis_failure(result.log)
    if result.returncode != 0 or script_failure:
        detail = f": {script_failure}" if script_failure else ""
        raise WorkflowError("Vitis workspace synchronization/build failed" + detail)
    elf = context.project_root / configuration["results"]["elf"]
    if not elf.is_file():
        raise WorkflowError(f"formal ELF is missing: {configuration['results']['elf']}")
    return {"status": "PASS", "workspace": configuration["workspace"], "elf": configuration["results"]["elf"]}
