"""Output directory checks for the canonical 05_Output source layout."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .project import require_project_instance


@dataclass(frozen=True)
class OutputEnsureResult:
    messages: list[str]


def ensure_output_dirs(project_path: Path) -> OutputEnsureResult:
    project = require_project_instance(project_path)
    output = project / "05_Output"
    messages: list[str] = []

    required = [
        output / "rtl",
        output / "tb",
        output / "uvm",
        output / "fpga",
        output / "fpga" / "vivado",
        output / "fpga" / "vivado" / "project",
        output / "fpga" / "vivado" / "scripts",
        output / "fpga" / "vivado" / "constraints",
        output / "fpga" / "vivado" / "bitstream",
        output / "fpga" / "vivado" / "hw_platform",
        output / "fpga" / "vivado" / "reports",
        output / "fpga" / "vitis",
        output / "fpga" / "vitis" / "workspace",
        output / "fpga" / "vitis" / "src",
        output / "fpga" / "vitis" / "platform",
        output / "fpga" / "vitis" / "apps",
        output / "fpga" / "vitis" / "boot",
        output / "fpga" / "vitis" / "reports",
        output / "reports" / "loop1",
        output / "reports" / "loop2",
        output / "reports" / "loop3",
        output / "reports" / "loop3" / "preflight",
        output / "reports" / "trace_matrix",
    ]
    for path in required:
        path.mkdir(parents=True, exist_ok=True)
        messages.append(f"canonical: {path.relative_to(project)}")

    return OutputEnsureResult(messages=messages)
