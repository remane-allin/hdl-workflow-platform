"""Cross-platform HDL project creation wrapper."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a standard HDL workflow project.")
    parser.add_argument("name", help="Project name under prj/.")
    parser.add_argument("--force", action="store_true", help="Allow replacing an existing empty project directory.")
    args = parser.parse_args(argv)

    workspace = Path(__file__).resolve().parents[3]
    engine = workspace / "env" / "core"
    cmd = [sys.executable, "-m", "hdlflow.cli", "init-project", args.name, "--workspace", str(workspace)]
    if args.force:
        cmd.append("--force")
    env = os.environ.copy()
    env["HDLFLOW_PROJECT_CREATE_ENTRYPOINT"] = "env/tool/scripts/new_hdl_project.py"
    env["PYTHONPATH"] = str(engine)
    result = subprocess.run(cmd, cwd=engine, env=env)
    if result.returncode != 0:
        return result.returncode

    project = workspace / "prj" / args.name
    for followup in [
        [sys.executable, "-m", "hdlflow.cli", "ensure-output", "--project", str(project)],
        [sys.executable, "-m", "hdlflow.cli", "doctor", "--workspace", str(workspace), "--project", str(project)],
        [sys.executable, "-m", "hdlflow.cli", "requirements-frontdoor-init", "--project", str(project), "--status", "DRAFT", "--force"],
        [sys.executable, "-m", "hdlflow.cli", "requirements-frontdoor-check", "--project", str(project), "--allow-draft"],
        [
            sys.executable,
            "-m",
            "hdlflow.cli",
            "memory-record",
            "--project",
            str(project),
            "--iteration-id",
            f"{args.name}_bootstrap_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "--node",
            "input",
            "--gate-level",
            "develop",
            "--gate-result",
            "PASS",
            "--memory-record",
            "work/memory/00_global/DECISIONS.md",
            "--report",
            "output/reports/docparse/requirements_frontend_report.md",
            "--notes",
            "Project created through env/tool/scripts/new_hdl_project.py.",
            "--artifact",
            "project_scaffold.yaml",
            "--artifact",
            "work/config/project.yaml",
            "--artifact",
            "work/docparse/frontdoor/srs.yaml",
            "--latest-summary",
            "Project scaffold and six-agent frontdoor artifacts initialized as DRAFT.",
            "--next-action",
            "Add source documents and requirements under input/spec, then promote Spec Agent artifacts to READY after review.",
            "--agent",
            "arbtr",
            "--flow-direction",
            "forward",
            "--arbtr-decision",
            "bootstrap_recorded",
            "--baseline-version",
            "DRAFT-bootstrap",
        ],
        [sys.executable, "-m", "hdlflow.cli", "memory-check", "--project", str(project)],
    ]:
        result = subprocess.run(followup, cwd=workspace, env=env)
        if result.returncode != 0:
            return result.returncode

    print(f"HDL_PROJECT_CREATE_PASS project={project}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
