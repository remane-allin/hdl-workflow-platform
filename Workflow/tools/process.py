from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from Workflow.core.contracts import WorkflowError


@dataclass(frozen=True)
class ProcessResult:
    command: tuple[str, ...]
    returncode: int
    log: Path


def run_process(
    arguments: Sequence[str | Path],
    *,
    cwd: Path,
    log: Path,
    timeout: float | None = None,
) -> ProcessResult:
    if not arguments:
        raise ValueError("command cannot be empty")
    if os.name != "nt":
        raise WorkflowError("tool execution is supported only on Windows")
    cwd.mkdir(parents=True, exist_ok=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    command = tuple(str(item) for item in arguments)
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    with log.open("w", encoding="utf-8", errors="replace") as stream:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=stream,
            stderr=subprocess.STDOUT,
            shell=False,
            creationflags=creationflags,
        )
        try:
            returncode = process.wait(timeout=timeout)
        except (KeyboardInterrupt, subprocess.TimeoutExpired) as error:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            process.wait()
            reason = "interrupted" if isinstance(error, KeyboardInterrupt) else "timed out"
            raise WorkflowError(f"tool process {reason}: {command[0]}") from error
    return ProcessResult(command, returncode, log)
