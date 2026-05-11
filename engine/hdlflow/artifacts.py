"""Output directory checks for the canonical 05_Output source layout."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OutputEnsureResult:
    messages: list[str]


def ensure_output_dirs(project_path: Path) -> OutputEnsureResult:
    project = project_path.resolve()
    output = project / "05_Output"
    messages: list[str] = []

    required = [
        output / "rtl",
        output / "tb",
        output / "uvm",
        output / "fpga",
        output / "reports" / "loop1",
        output / "reports" / "loop2",
        output / "reports" / "loop3",
        output / "reports" / "trace_matrix",
    ]
    for path in required:
        path.mkdir(parents=True, exist_ok=True)
        messages.append(f"canonical: {path.relative_to(project)}")

    return OutputEnsureResult(messages=messages)
