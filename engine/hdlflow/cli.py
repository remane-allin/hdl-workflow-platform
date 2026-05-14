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
    cleanup_library_temp_outputs,
    finalize_library_database,
    format_detail,
    format_hardware_resources,
    format_io_pins,
    format_schematic_nets,
    format_tcl_command_detail,
    format_tcl_command_rows,
    format_tcl_example_rows,
    format_tcl_topic_rows,
    format_toc,
    get_entry,
    get_software_tcl_command,
    query_diagnostics,
    query_fpga_hardware_resources,
    query_fpga_io_pins,
    query_fpga_schematic_nets,
    query_software_tcl_commands,
    query_software_tcl_examples,
    query_software_tcl_topics,
    search_software_doc_chunks,
    query_toc,
)
from .loop2_bindings import (
    build_loop2_binding_database,
    format_loop2_binding_rows,
    write_loop2_database_preflight,
)
from .memory import auto_record_workflow_event, check_memory, record_memory_iteration
from .pipeline import build_pipeline, format_pipeline
from .prototype import write_prototype_preflight
from .prototype import (
    generate_ps_pl_bd_tcl,
    generate_vitis_boot_files,
    generate_xdc_from_database,
    validate_prototype_plan,
)
from .reports import write_config_run_report
from .scaffold import create_project
from .ug1118 import extract_ug1118
from .ug835 import extract_ug835
from .ug894 import extract_ug894
from .validate import validate_project
from .vitis_guides import extract_vitis_guide


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

    preflight_parser = subparsers.add_parser(
        "prototype-preflight",
        help="Run required Loop3 database lookups and write a preflight report.",
    )
    preflight_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    preflight_parser.add_argument("--project", required=True, help="Project path.")
    preflight_parser.add_argument("--mode", choices=["pl", "ps_pl"], required=True, help="Prototype mode.")
    preflight_parser.add_argument("--board", default="navigator_zynq_7020", help="Board ID.")
    preflight_parser.add_argument("--signal", action="append", help="Hardware signal/resource to query. Repeatable.")
    preflight_parser.add_argument("--tcl-command", action="append", help="Vivado Tcl command to query. Repeatable.")
    preflight_parser.add_argument("--tool-version", default="2024.2", help="Tool database version.")

    xdc_parser = subparsers.add_parser("generate-xdc", help="Generate XDC constraints from the local FPGA database.")
    xdc_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    xdc_parser.add_argument("--project", required=True, help="Project path.")
    xdc_parser.add_argument("--port", action="append", required=True, help="Port mapping PORT=DATABASE_SIGNAL. Repeatable.")
    xdc_parser.add_argument("--clock", action="append", help="Clock mapping PORT=PERIOD_NS. Repeatable.")
    xdc_parser.add_argument("--output", help="Project-relative output XDC path.")

    plan_check_parser = subparsers.add_parser("validate-prototype-plan", help="Check AXI, MIO, PL IO, DDR, and cache plan rules.")
    plan_check_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    plan_check_parser.add_argument("--project", required=True, help="Project path.")
    plan_check_parser.add_argument("--plan", help="Project-relative prototype plan path.")

    bd_parser = subparsers.add_parser("generate-ps-pl-bd", help="Generate a PS7 + AXI-Lite Block Design Tcl skeleton.")
    bd_parser.add_argument("--project", required=True, help="Project path.")
    bd_parser.add_argument("--plan", help="Project-relative prototype plan path.")
    bd_parser.add_argument("--output", help="Project-relative Tcl output path.")

    boot_parser = subparsers.add_parser("generate-vitis-boot", help="Generate Vitis boot image template files.")
    boot_parser.add_argument("--project", required=True, help="Project path.")
    boot_parser.add_argument("--output-dir", help="Project-relative output directory.")

    launcher_parser = subparsers.add_parser("get-tool-launcher", help="Print a configured tool launcher path.")
    launcher_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    launcher_parser.add_argument("--tool", required=True, help="Tool name under config/global/toolchains/toolchains.yaml.")
    launcher_parser.add_argument("--launcher", required=True, help="Launcher key, for example vivado_bat or xsct_bat.")

    memory_record_parser = subparsers.add_parser("memory-record", help="Write a synchronized project memory iteration.")
    memory_record_parser.add_argument("--project", required=True, help="Project path.")
    memory_record_parser.add_argument("--iteration-id", required=True)
    memory_record_parser.add_argument("--node", required=True)
    memory_record_parser.add_argument("--gate-level", required=True)
    memory_record_parser.add_argument("--gate-result", required=True)
    memory_record_parser.add_argument("--memory-record", required=True)
    memory_record_parser.add_argument("--report", required=True)
    memory_record_parser.add_argument("--notes", required=True)
    memory_record_parser.add_argument("--version")
    memory_record_parser.add_argument("--artifact", action="append", help="Project-relative artifact path. Repeatable.")
    memory_record_parser.add_argument("--latest-summary")
    memory_record_parser.add_argument("--next-action")

    memory_check_parser = subparsers.add_parser("memory-check", help="Validate project memory synchronization.")
    memory_check_parser.add_argument("--project", required=True, help="Project path.")

    loop2_bind_parser = subparsers.add_parser("loop2-build-bindings", help="Build the Loop2 requirement/UVM binding SQLite database.")
    loop2_bind_parser.add_argument("--project", required=True, help="Project path.")
    loop2_bind_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    loop2_bind_parser.add_argument("--db", help="Optional project-relative or absolute SQLite output path.")

    loop2_preflight_parser = subparsers.add_parser(
        "loop2-database-preflight",
        help="Run required Loop2 template database lookups and write a preflight report.",
    )
    loop2_preflight_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    loop2_preflight_parser.add_argument("--project", required=True, help="Project path.")

    loop2_query_parser = subparsers.add_parser("loop2-query-bindings", help="Query the Loop2 binding SQLite database.")
    loop2_query_parser.add_argument("--project", required=True, help="Project path.")
    loop2_query_parser.add_argument("--req", help="Optional requirement ID filter.")

    library_build_parser = subparsers.add_parser("library-build", help="Build the local SQLite library index.")
    library_build_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")

    library_clean_parser = subparsers.add_parser("library-clean-temp", help="Remove library parser temporary outputs.")
    library_clean_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")

    library_finalize_parser = subparsers.add_parser(
        "library-finalize",
        help="Build the SQLite library index, then remove parser temporary outputs.",
    )
    library_finalize_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")

    ug835_parser = subparsers.add_parser("ingest-ug835", help="Extract UG835 into software Tcl database artifacts.")
    ug835_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    ug835_parser.add_argument("--pdf", help="Path to UG835 PDF. Defaults to library/files/fpga_ug_pdfs/UG835.pdf.")

    ug894_parser = subparsers.add_parser("ingest-ug894", help="Extract UG894 into software Tcl scripting guide artifacts.")
    ug894_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    ug894_parser.add_argument("--pdf", help="Path to UG894 PDF. Defaults to library/files/fpga_ug_pdfs/ug894.pdf.")
    ug894_parser.add_argument("--mineru-dir", help="Existing MinerU extract directory containing ug894.md/json.")

    ug1118_parser = subparsers.add_parser("ingest-ug1118", help="Extract UG1118 into software Tcl custom IP guide artifacts.")
    ug1118_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    ug1118_parser.add_argument("--pdf", help="Path to UG1118 PDF. Defaults to library/files/fpga_ug_pdfs/ug1118.pdf.")
    ug1118_parser.add_argument("--mineru-dir", help="Existing MinerU extract directory containing ug1118.md/json.")

    vitis_guide_parser = subparsers.add_parser("ingest-vitis-guide", help="Extract a Vitis/PDM guide into software guide artifacts.")
    vitis_guide_parser.add_argument("guide", choices=["ug908", "ug1553", "ug1556", "ug1701", "ug1702"], help="Guide key.")
    vitis_guide_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    vitis_guide_parser.add_argument("--pdf", help="Optional PDF path.")
    vitis_guide_parser.add_argument("--mineru-dir", help="Existing MinerU extract directory.")

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

    tcl_search_parser = subparsers.add_parser("search-tcl-commands", help="Search software Tcl commands.")
    tcl_search_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    tcl_search_parser.add_argument("--command", dest="tcl_command", help="Exact command name or command ID.")
    tcl_search_parser.add_argument("--keyword", help="Keyword in summary, syntax, arguments, examples, or description.")
    tcl_search_parser.add_argument("--option", help="Exact Tcl option name, for example -file.")
    tcl_search_parser.add_argument("--tool", default="vivado", help="Tool name. Defaults to vivado.")
    tcl_search_parser.add_argument("--version", default="2024.2", help="Tool version. Defaults to 2024.2.")
    tcl_search_parser.add_argument("--category", help="Command category substring.")
    tcl_search_parser.add_argument("--limit", type=int, default=50, help="Maximum rows to print.")

    tcl_detail_parser = subparsers.add_parser("get-tcl-command-detail", help="Read a software Tcl command by ID or name.")
    tcl_detail_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    tcl_detail_parser.add_argument("--id", required=True, help="Command ID or command name.")

    tcl_chunk_parser = subparsers.add_parser("search-tcl-doc", help="Full-text search software Tcl document chunks.")
    tcl_chunk_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    tcl_chunk_parser.add_argument("--query", required=True, help="Search text.")
    tcl_chunk_parser.add_argument("--doc-id", help="Document ID.")
    tcl_chunk_parser.add_argument("--tool", help="Tool name, for example vivado, vitis, or pdm.")
    tcl_chunk_parser.add_argument("--version", help="Tool version, for example 2024.2.")
    tcl_chunk_parser.add_argument("--limit", type=int, default=10, help="Maximum chunks to print.")

    tcl_topic_parser = subparsers.add_parser("search-tcl-topics", help="Search software Tcl guide topics.")
    tcl_topic_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    tcl_topic_parser.add_argument("--keyword", help="Keyword in title, summary, tags, or text.")
    tcl_topic_parser.add_argument("--doc-id", help="Document ID.")
    tcl_topic_parser.add_argument("--tool", help="Tool name, for example vivado, vitis, or pdm.")
    tcl_topic_parser.add_argument("--version", help="Tool version, for example 2024.2.")
    tcl_topic_parser.add_argument("--limit", type=int, default=50, help="Maximum rows to print.")

    tcl_example_parser = subparsers.add_parser("search-tcl-examples", help="Search software Tcl guide examples.")
    tcl_example_parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    tcl_example_parser.add_argument("--keyword", help="Keyword in title, description, tags, or code.")
    tcl_example_parser.add_argument("--command", dest="example_command", help="Command name used in the example.")
    tcl_example_parser.add_argument("--doc-id", help="Document ID.")
    tcl_example_parser.add_argument("--tool", help="Tool name, for example vivado, vitis, or pdm.")
    tcl_example_parser.add_argument("--version", help="Tool version, for example 2024.2.")
    tcl_example_parser.add_argument("--limit", type=int, default=50, help="Maximum rows to print.")

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
        if args.command == "prototype-preflight":
            result = write_prototype_preflight(
                Path(args.workspace),
                Path(args.project),
                mode=args.mode,
                board=args.board,
                signals=args.signal,
                tcl_commands=args.tcl_command,
                tool_version=args.tool_version,
            )
            print(f"report: {result.report_path}")
            if result.missing_items:
                for item in result.missing_items:
                    print(f"missing: {item}")
                return 1
            print("prototype preflight: PASS")
            _print_memory_messages(
                auto_record_workflow_event(
                    Path(args.project),
                    event="loop3-database-preflight",
                    node="04_Loop3_FPGA_Prototype",
                    gate_level="preflight",
                    gate_result="PASS",
                    memory_record=result.report_path,
                    report=result.report_path,
                    notes=f"Database preflight passed for {args.mode} on {args.board}",
                    artifacts=[result.report_path],
                )
            )
            return 0
        if args.command == "generate-xdc":
            result = generate_xdc_from_database(
                Path(args.workspace),
                Path(args.project),
                ports=args.port,
                output=args.output,
                clock_ports=args.clock,
            )
            print(f"xdc: {result.path}")
            for message in result.messages:
                print(message)
            _print_memory_messages(
                auto_record_workflow_event(
                    Path(args.project),
                    event="loop3-generate-xdc",
                    node="04_Loop3_FPGA_Prototype",
                    gate_level="constraints",
                    gate_result="PASS",
                    memory_record=result.path,
                    report=result.path,
                    notes="Generated database-backed XDC constraints",
                    artifacts=[result.path],
                )
            )
            return 0
        if args.command == "validate-prototype-plan":
            result = validate_prototype_plan(Path(args.workspace), Path(args.project), plan=args.plan)
            print(f"report: {result.report_path}")
            for warning in result.warnings:
                print(f"warning: {warning}")
            for error in result.errors:
                print(f"error: {error}")
            if result.ok:
                _print_memory_messages(
                    auto_record_workflow_event(
                        Path(args.project),
                        event="loop3-prototype-plan-check",
                        node="04_Loop3_FPGA_Prototype",
                        gate_level="process",
                        gate_result="PASS",
                        memory_record=result.report_path,
                        report=result.report_path,
                        notes="Prototype plan check passed",
                        artifacts=[result.report_path],
                    )
                )
            return 0 if result.ok else 1
        if args.command == "generate-ps-pl-bd":
            result = generate_ps_pl_bd_tcl(Path(args.project), plan=args.plan, output=args.output)
            print(f"bd_tcl: {result.path}")
            for message in result.messages:
                print(message)
            _print_memory_messages(
                auto_record_workflow_event(
                    Path(args.project),
                    event="loop3-generate-ps-pl-bd",
                    node="04_Loop3_FPGA_Prototype",
                    gate_level="bd_generation",
                    gate_result="PASS",
                    memory_record=result.path,
                    report=result.path,
                    notes="Generated PS_PL Block Design Tcl skeleton",
                    artifacts=[result.path],
                )
            )
            return 0
        if args.command == "generate-vitis-boot":
            result = generate_vitis_boot_files(Path(args.project), output_dir=args.output_dir)
            print(f"boot_dir: {result.path}")
            for message in result.messages:
                print(message)
            _print_memory_messages(
                auto_record_workflow_event(
                    Path(args.project),
                    event="loop3-generate-vitis-boot",
                    node="04_Loop3_FPGA_Prototype",
                    gate_level="boot_template",
                    gate_result="PASS",
                    memory_record=result.path,
                    report=result.path,
                    notes="Generated Vitis boot image template files",
                    artifacts=[result.path],
                )
            )
            return 0
        if args.command == "get-tool-launcher":
            workspace = load_workspace(Path(args.workspace))
            tool = workspace.data.get("toolchains", {}).get("toolchains", {}).get(args.tool, {})
            launchers = tool.get("launchers", {}) if isinstance(tool, dict) else {}
            value = launchers.get(args.launcher) if isinstance(launchers, dict) else None
            if not value:
                print(f"error: launcher not configured: {args.tool}.{args.launcher}", file=sys.stderr)
                return 1
            print(value)
            return 0
        if args.command == "memory-record":
            result = record_memory_iteration(
                Path(args.project),
                iteration_id=args.iteration_id,
                node=args.node,
                gate_level=args.gate_level,
                gate_result=args.gate_result,
                memory_record=args.memory_record,
                report=args.report,
                notes=args.notes,
                version=args.version,
                artifacts=args.artifact,
                latest_summary=args.latest_summary,
                next_action=args.next_action,
            )
            for message in result.messages:
                print(message)
            print("memory record: PASS")
            return 0
        if args.command == "memory-check":
            result = check_memory(Path(args.project))
            print(f"report: {result.report_path}")
            for warning in result.warnings:
                print(f"warning: {warning}")
            for error in result.errors:
                print(f"error: {error}")
            return 0 if result.ok else 1
        if args.command == "loop2-build-bindings":
            db_path = Path(args.db) if args.db else None
            result = build_loop2_binding_database(Path(args.project), db_path=db_path, workspace=Path(args.workspace))
            print(f"loop2_binding_db: {result.db_path}")
            print(f"requirements: {result.requirement_count}")
            print(f"artifacts: {result.artifact_count}")
            print(f"bindings: {result.binding_count}")
            print(f"evidence: {result.evidence_count}")
            print(f"missing_artifacts: {result.missing_artifacts}")
            print(f"missing_database_items: {result.missing_database_items}")
            ok = result.missing_artifacts == 0 and result.missing_database_items == 0
            print("loop2 binding database: PASS" if ok else "loop2 binding database: FAIL")
            return 0 if ok else 1
        if args.command == "loop2-database-preflight":
            result = write_loop2_database_preflight(Path(args.workspace), Path(args.project))
            print(f"report: {result.report_path}")
            for item in result.missing_items:
                print(f"missing: {item}")
            print("loop2 database preflight: PASS" if not result.missing_items else "loop2 database preflight: FAIL")
            return 0 if not result.missing_items else 1
        if args.command == "loop2-query-bindings":
            for line in format_loop2_binding_rows(Path(args.project), req_id=args.req):
                print(line)
            return 0
        if args.command == "library-build":
            db_path = build_library(Path(args.workspace))
            print(f"library: {db_path}")
            print("library build: PASS")
            return 0
        if args.command == "library-clean-temp":
            removed = cleanup_library_temp_outputs(Path(args.workspace))
            for path in removed:
                print(f"removed: {path}")
            print(f"library clean temp: PASS ({len(removed)} removed)")
            return 0
        if args.command == "library-finalize":
            db_path, removed = finalize_library_database(Path(args.workspace))
            print(f"library: {db_path}")
            for path in removed:
                print(f"removed: {path}")
            print(f"library finalize: PASS ({len(removed)} temp paths removed)")
            return 0
        if args.command == "ingest-ug835":
            pdf_path = Path(args.pdf) if args.pdf else None
            out_dir = extract_ug835(Path(args.workspace), pdf_path)
            db_path = build_library(Path(args.workspace))
            print(f"ug835 parsed: {out_dir}")
            print(f"library: {db_path}")
            print("ingest ug835: PASS")
            return 0
        if args.command == "ingest-ug894":
            pdf_path = Path(args.pdf) if args.pdf else None
            mineru_dir = Path(args.mineru_dir) if args.mineru_dir else None
            out_dir = extract_ug894(Path(args.workspace), pdf_path=pdf_path, mineru_dir=mineru_dir)
            db_path = build_library(Path(args.workspace))
            print(f"ug894 parsed: {out_dir}")
            print(f"library: {db_path}")
            print("ingest ug894: PASS")
            return 0
        if args.command == "ingest-ug1118":
            pdf_path = Path(args.pdf) if args.pdf else None
            mineru_dir = Path(args.mineru_dir) if args.mineru_dir else None
            out_dir = extract_ug1118(Path(args.workspace), pdf_path=pdf_path, mineru_dir=mineru_dir)
            db_path = build_library(Path(args.workspace))
            print(f"ug1118 parsed: {out_dir}")
            print(f"library: {db_path}")
            print("ingest ug1118: PASS")
            return 0
        if args.command == "ingest-vitis-guide":
            pdf_path = Path(args.pdf) if args.pdf else None
            mineru_dir = Path(args.mineru_dir) if args.mineru_dir else None
            out_dir = extract_vitis_guide(Path(args.workspace), args.guide, pdf_path=pdf_path, mineru_dir=mineru_dir)
            db_path = build_library(Path(args.workspace))
            print(f"{args.guide} parsed: {out_dir}")
            print(f"library: {db_path}")
            print(f"ingest {args.guide}: PASS")
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
        if args.command == "search-tcl-commands":
            rows = query_software_tcl_commands(
                Path(args.workspace),
                command=args.tcl_command,
                keyword=args.keyword,
                option=args.option,
                tool=args.tool,
                tool_version=args.version,
                category=args.category,
                limit=args.limit,
            )
            for line in format_tcl_command_rows(rows):
                print(line)
            return 0
        if args.command == "get-tcl-command-detail":
            row = get_software_tcl_command(Path(args.workspace), args.id)
            for line in format_tcl_command_detail(row):
                print(line)
            return 0
        if args.command == "search-tcl-doc":
            rows = search_software_doc_chunks(
                Path(args.workspace),
                query_text=args.query,
                doc_id=args.doc_id,
                tool=args.tool,
                tool_version=args.version,
                limit=args.limit,
            )
            for row in rows:
                text = " ".join(str(row.get("text") or "").split())
                print(f"{row.get('chunk_id')} | {row.get('anchor')} | {text[:240]}")
            return 0
        if args.command == "search-tcl-topics":
            rows = query_software_tcl_topics(
                Path(args.workspace),
                keyword=args.keyword,
                doc_id=args.doc_id,
                tool=args.tool,
                tool_version=args.version,
                limit=args.limit,
            )
            for line in format_tcl_topic_rows(rows):
                print(line)
            return 0
        if args.command == "search-tcl-examples":
            rows = query_software_tcl_examples(
                Path(args.workspace),
                keyword=args.keyword,
                command=args.example_command,
                doc_id=args.doc_id,
                tool=args.tool,
                tool_version=args.version,
                limit=args.limit,
            )
            for line in format_tcl_example_rows(rows):
                print(line)
            return 0
    except Exception as exc:  # pragma: no cover - CLI boundary
        print(f"error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"unknown command: {args.command}")
    return 2


def _print_memory_messages(result) -> None:
    for message in result.messages:
        print(f"memory: {message}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
