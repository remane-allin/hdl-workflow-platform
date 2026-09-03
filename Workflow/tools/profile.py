from __future__ import annotations

import json
import os
import platform
import re
import shutil
import string
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from Workflow.core.contracts import ContractError, WorkflowError


def load_profiles(workflow_root: Path) -> dict[str, Any]:
    path = workflow_root / "tools" / "tool-profiles.json"
    with path.open("r", encoding="utf-8") as stream:
        profiles = json.load(stream)
    if profiles.get("format_version") != 1:
        raise ContractError("unsupported tool profile format")
    return profiles


def _candidate_from_environment(profile: dict[str, Any], executable: str) -> Path | None:
    variable = profile.get("path_env")
    if not variable or not os.environ.get(variable):
        return None
    root = Path(os.environ[variable])
    candidates = (root / "bin" / f"{executable}.bat", root / "bin" / f"{executable}.exe")
    return next((item for item in candidates if item.is_file()), None)


def _installed_candidates(profile: dict[str, Any], executable: str) -> list[Path]:
    version = profile["version"]
    values: list[Path] = []
    for letter in string.ascii_uppercase:
        drive = Path(f"{letter}:/")
        if not drive.exists():
            continue
        for template in profile.get("install_templates", []):
            root = drive / template.format(version=version)
            for suffix in (".bat", ".exe"):
                candidate = root / "bin" / f"{executable}{suffix}"
                if candidate.is_file():
                    values.append(candidate.resolve())
    return sorted(set(values))


def _verify_version(workflow_root: Path, group: str, executable: Path, expected: str) -> None:
    if group == "vitis":
        if expected not in executable.as_posix():
            raise WorkflowError(f"Vitis executable path does not identify version {expected}")
        return
    probe_root = workflow_root / "work" / "tool" / "environment"
    probe_root.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix=f"{group}-{executable.stem}-", dir=probe_root) as temporary:
            completed = subprocess.run(
                [str(executable), "--version" if group == "xsim" else "-version"],
                cwd=temporary,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=False,
            )
    finally:
        for path in (probe_root, probe_root.parent, probe_root.parent.parent):
            try:
                path.rmdir()
            except OSError:
                break
    if re.search(rf"v?{re.escape(expected)}(?:\.0)?\b", completed.stdout) is None:
        raise WorkflowError(f"{group} version {expected} is required")


def resolve_tool(workflow_root: Path, group: str, executable: str) -> str:
    profiles = load_profiles(workflow_root)
    profile = profiles.get(group)
    if not isinstance(profile, dict) or executable not in profile.get("executables", []):
        raise ContractError(f"tool profile does not declare {group}/{executable}")
    candidate = _candidate_from_environment(profile, executable)
    if candidate is None:
        found = shutil.which(executable)
        candidate = Path(found).resolve() if found else None
    if candidate is None:
        installed = _installed_candidates(profile, executable)
        if len(installed) != 1:
            raise WorkflowError(f"cannot uniquely resolve {group}/{executable}")
        candidate = installed[0]
    _verify_version(workflow_root, group, candidate, str(profile["version"]))
    return str(candidate)


def environment_gate(workflow_root: Path) -> dict[str, Any]:
    profiles = load_profiles(workflow_root)
    if platform.system() != "Windows":
        raise WorkflowError("Workflow supports Windows only")
    pwsh = shutil.which("pwsh")
    if not pwsh:
        raise WorkflowError("PowerShell 7 is required")
    completed = subprocess.run(
        [pwsh, "-NoProfile", "-NonInteractive", "-Command", "$PSVersionTable.PSVersion.ToString()"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=False,
    )
    powershell_version = completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else ""
    if completed.returncode != 0 or not powershell_version or int(powershell_version.split(".", 1)[0]) < 7:
        raise WorkflowError("PowerShell 7 is required")
    minimum = tuple(int(item) for item in profiles["python"]["minimum"].split("."))
    if sys.version_info[: len(minimum)] < minimum:
        raise WorkflowError(f"Python {profiles['python']['minimum']} or newer is required")
    resolved = {
        executable: resolve_tool(workflow_root, group, executable)
        for group in ("vivado", "xsim", "vitis")
        for executable in profiles[group]["executables"]
    }
    return {
        "status": "PASS",
        "host": profiles["host"],
        "powershell": powershell_version,
        "python": platform.python_version(),
        "tools": resolved,
    }
