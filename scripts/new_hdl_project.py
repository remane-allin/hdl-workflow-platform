"""Cross-platform HDL project creation wrapper."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a standard HDL workflow project.")
    parser.add_argument("name", help="Project name under projects/.")
    parser.add_argument("--force", action="store_true", help="Allow replacing an existing empty project directory.")
    args = parser.parse_args(argv)

    workspace = Path(__file__).resolve().parents[1]
    engine = workspace / "engine"
    cmd = [sys.executable, "-m", "hdlflow.cli", "init-project", args.name, "--workspace", str(workspace)]
    if args.force:
        cmd.append("--force")
    env = None
    result = subprocess.run(cmd, cwd=engine, env=env)
    if result.returncode != 0:
        return result.returncode

    project = workspace / "projects" / args.name
    for followup in [
        [sys.executable, "-m", "hdlflow.cli", "doctor", "--workspace", str(workspace), "--project", str(project)],
        [sys.executable, "-m", "hdlflow.cli", "ensure-output", "--project", str(project)],
    ]:
        result = subprocess.run(followup, cwd=engine, env=env)
        if result.returncode != 0:
            return result.returncode

    print(f"HDL_PROJECT_CREATE_PASS project={project}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
