"""Command-line entry point for the HDL workflow platform scaffold."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .artifacts import ensure_output_dirs
from .config import load_project, load_workspace, validate_config
from .doctor import run_doctor
from .pipeline import build_pipeline, format_pipeline
from .reports import write_config_run_report
from .scaffold import create_project
from .validate import validate_project


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hdlflow",
        description="Manage the clean HDL workflow platform layout.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-project", help="Create a project from the standard template.")
    init_parser.add_argument("name", help="Project directory name under projects/.")
    init_parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace root containing templates/ and projects/. Defaults to current directory.",
    )
    init_parser.add_argument("--force", action="store_true", help="Overwrite an existing empty project directory.")

    check_parser = subparsers.add_parser("check-project", help="Validate required project layout files.")
    check_parser.add_argument("project_path", help="Path to a project directory.")

    doctor_parser = subparsers.add_parser("doctor", help="Validate workspace config, project config, and layout.")
    doctor_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    doctor_parser.add_argument(
        "--project",
        required=True,
        help="Project path to validate, for example projects/<project_name>.",
    )

    plan_parser = subparsers.add_parser("plan", help="Print the active config-derived pipeline.")
    plan_parser.add_argument("--project", required=True, help="Project path.")

    run_parser = subparsers.add_parser("run-config", help="Run the configuration pipeline checks and write a report.")
    run_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    run_parser.add_argument("--project", required=True, help="Project path.")

    ensure_parser = subparsers.add_parser("ensure-output", help="Ensure canonical 05_Output directories exist.")
    ensure_parser.add_argument("--project", required=True, help="Project path.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init-project":
            project_path = create_project(Path(args.workspace), args.name, force=args.force)
            print(f"created: {project_path}")
            return 0
        if args.command == "check-project":
            result = validate_project(Path(args.project_path))
            for line in result.messages:
                print(line)
            return 0 if result.ok else 1
        if args.command == "doctor":
            result = run_doctor(Path(args.workspace), Path(args.project))
            for line in result.messages:
                print(line)
            return 0 if result.ok else 1
        if args.command == "plan":
            project = load_project(Path(args.project))
            for line in format_pipeline(build_pipeline(project.data)):
                print(line)
            return 0
        if args.command == "run-config":
            workspace = load_workspace(Path(args.workspace))
            project = load_project(Path(args.project))
            errors = validate_config(workspace, project)
            pipeline = build_pipeline(project.data)
            report = write_config_run_report(project.path, pipeline, errors)
            print(f"report: {report}")
            if errors:
                for error in errors:
                    print(f"error: {error}")
                return 1
            print("configuration run: PASS")
            return 0
        if args.command == "ensure-output":
            result = ensure_output_dirs(Path(args.project))
            for line in result.messages:
                print(line)
            return 0
    except Exception as exc:  # pragma: no cover - CLI boundary
        print(f"error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
