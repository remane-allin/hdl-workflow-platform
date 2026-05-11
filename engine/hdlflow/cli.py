"""Command-line entry point for the HDL workflow platform scaffold."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .artifacts import ensure_output_dirs
from .config import load_project, load_workspace, validate_config
from .doctor import run_doctor
from .library import (
    build_library,
    format_detail,
    format_hardware_resources,
    format_io_pins,
    format_schematic_nets,
    format_toc,
    get_entry,
    query_diagnostics,
    query_fpga_hardware_resources,
    query_fpga_io_pins,
    query_fpga_schematic_nets,
    query_toc,
)
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

    library_build_parser = subparsers.add_parser("library-build", help="Build the local SQLite library index.")
    library_build_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")

    toc_parser = subparsers.add_parser("get-workflow-toc", help="List library entries for a workflow or context.")
    toc_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    toc_parser.add_argument("--flow", help="Flow ID, for example fpga.timing_analysis.")
    toc_parser.add_argument("--node", help="Workflow node, for example 04_Loop3_FPGA_Prototype.")
    toc_parser.add_argument("--tool", help="Tool name, for example vivado.")
    toc_parser.add_argument("--stage", help="Stage name, for example implementation.")
    toc_parser.add_argument("--domain", help="Library domain, for example fpga or rtl_templates.")

    command_parser = subparsers.add_parser("get-command-detail", help="Read a command detail entry by ID.")
    command_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    command_parser.add_argument("--id", required=True, help="Command entry ID.")

    template_parser = subparsers.add_parser("get-template-detail", help="Read a template detail entry by ID.")
    template_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    template_parser.add_argument("--id", required=True, help="Template entry ID.")

    detail_parser = subparsers.add_parser("get-library-detail", help="Read any library detail entry by ID.")
    detail_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    detail_parser.add_argument("--id", required=True, help="Library entry ID.")

    diagnostic_parser = subparsers.add_parser("get-diagnostic-candidates", help="List diagnostic library entries.")
    diagnostic_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    diagnostic_parser.add_argument("--tool", help="Tool name, for example vivado.")
    diagnostic_parser.add_argument("--text", help="Error text or log excerpt to match.")

    io_parser = subparsers.add_parser("get-fpga-io-pins", help="Query normalized FPGA IO table pins.")
    io_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    io_parser.add_argument("--table-id", help="IO table ID.")
    io_parser.add_argument("--connector", help="Connector name, for example X3.")
    io_parser.add_argument("--signal", help="Signal name substring.")
    io_parser.add_argument("--bank", help="Bank name, for example Bank35.")
    io_parser.add_argument("--category", help="Signal category, for example pl_io.")
    io_parser.add_argument("--limit", type=int, default=200, help="Maximum rows to print.")

    schematic_parser = subparsers.add_parser("get-fpga-schematic-nets", help="Query normalized FPGA schematic nets.")
    schematic_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    schematic_parser.add_argument("--schematic-id", help="Schematic ID.")
    schematic_parser.add_argument("--net", help="Net name substring, for example SD_D2 or SD D2.")
    schematic_parser.add_argument("--interface", help="Interface name, for example hdmi or sd_card.")
    schematic_parser.add_argument("--category", help="Net category, for example clock or reset.")
    schematic_parser.add_argument("--connector", help="Schematic or core connector name, for example J2 or X3.")
    schematic_parser.add_argument("--limit", type=int, default=200, help="Maximum rows to print.")

    hw_parser = subparsers.add_parser("get-fpga-hardware-resource", help="Query FPGA hardware guide resources.")
    hw_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    hw_parser.add_argument("--guide-id", help="Hardware guide ID.")
    hw_parser.add_argument("--signal", help="Signal or alias substring, for example PL_LED0 or led[0].")
    hw_parser.add_argument("--interface", help="Interface name, for example hdmi or rgb_lcd.")
    hw_parser.add_argument("--package-pin", help="FPGA package pin, for example H15.")
    hw_parser.add_argument("--mio-pin", help="PS MIO pin, for example MIO7.")
    hw_parser.add_argument("--keyword", help="Keyword in description, group, or cross references.")
    hw_parser.add_argument("--limit", type=int, default=200, help="Maximum rows to print.")

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
        if args.command == "library-build":
            db_path = build_library(Path(args.workspace))
            print(f"library: {db_path}")
            print("library build: PASS")
            return 0
        if args.command == "get-workflow-toc":
            entries = query_toc(
                Path(args.workspace),
                flow=args.flow,
                node=args.node,
                tool=args.tool,
                stage=args.stage,
                domain=args.domain,
            )
            for line in format_toc(entries):
                print(line)
            return 0
        if args.command == "get-command-detail":
            entry, detail = get_entry(Path(args.workspace), args.id, expected_kind="command")
            for line in format_detail(entry, detail):
                print(line)
            return 0
        if args.command == "get-template-detail":
            entry, detail = get_entry(Path(args.workspace), args.id, expected_kind="template")
            for line in format_detail(entry, detail):
                print(line)
            return 0
        if args.command == "get-library-detail":
            entry, detail = get_entry(Path(args.workspace), args.id)
            for line in format_detail(entry, detail):
                print(line)
            return 0
        if args.command == "get-diagnostic-candidates":
            entries = query_diagnostics(Path(args.workspace), tool=args.tool, text=args.text)
            for line in format_toc(entries):
                print(line)
            return 0
        if args.command == "get-fpga-io-pins":
            rows = query_fpga_io_pins(
                Path(args.workspace),
                table_id=args.table_id,
                connector=args.connector,
                signal=args.signal,
                bank=args.bank,
                category=args.category,
                limit=args.limit,
            )
            for line in format_io_pins(rows):
                print(line)
            return 0
        if args.command == "get-fpga-schematic-nets":
            rows = query_fpga_schematic_nets(
                Path(args.workspace),
                schematic_id=args.schematic_id,
                net=args.net,
                interface=args.interface,
                category=args.category,
                connector=args.connector,
                limit=args.limit,
            )
            for line in format_schematic_nets(rows):
                print(line)
            return 0
        if args.command == "get-fpga-hardware-resource":
            rows = query_fpga_hardware_resources(
                Path(args.workspace),
                guide_id=args.guide_id,
                signal=args.signal,
                interface=args.interface,
                package_pin=args.package_pin,
                mio_pin=args.mio_pin,
                keyword=args.keyword,
                limit=args.limit,
            )
            for line in format_hardware_resources(rows):
                print(line)
            return 0
    except Exception as exc:  # pragma: no cover - CLI boundary
        print(f"error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
