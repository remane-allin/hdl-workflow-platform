"""Loop3 FPGA prototype preflight checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import load_project
from .library import (
    query_fpga_hardware_resources,
    query_software_tcl_commands,
    query_software_tcl_topics,
)
from .project import require_project_instance
from .simple_yaml import load_yaml


DEFAULT_SIGNALS = {
    "pl": ["PL_LED0", "UART3_RX", "UART3_TX", "PL_GCLK_50MHZ"],
    "ps_pl": ["PS_KEY0", "PS_LED1", "DDR", "PL_LED0", "UART3_RX", "UART3_TX"],
}

DEFAULT_TCL_COMMANDS = [
    "create_project",
    "add_files",
    "set_property",
    "create_bd_design",
    "create_bd_cell",
    "apply_bd_automation",
    "assign_bd_address",
    "validate_bd_design",
    "save_bd_design",
    "launch_runs",
    "report_timing_summary",
    "report_utilization",
    "report_drc",
    "write_bitstream",
    "program_hw_devices",
]

DEFAULT_VITIS_TOPICS = ["platform", "application", "domain", "xsct"]


@dataclass(frozen=True)
class PrototypePreflightResult:
    report_path: Path
    missing_items: list[str]
    board: str
    mode: str

    @property
    def ok(self) -> bool:
        return not self.missing_items


@dataclass(frozen=True)
class PrototypeFileResult:
    path: Path
    messages: list[str]


@dataclass(frozen=True)
class PrototypeCheckResult:
    report_path: Path
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class Loop3ReportRefreshResult:
    report_paths: list[Path]
    statuses: dict[str, str]

    @property
    def ok(self) -> bool:
        return all(status == "PASS" for status in self.statuses.values())


def write_prototype_preflight(
    workspace: Path,
    project_path: Path,
    *,
    mode: str,
    board: str | None = None,
    signals: list[str] | None = None,
    tcl_commands: list[str] | None = None,
    tool_version: str | None = None,
) -> PrototypePreflightResult:
    """Query the local database and write a Loop3 preflight evidence report."""

    workspace = workspace.resolve()
    project = require_project_instance(project_path)
    policy = _prototype_policy(project)
    plan_data = _load_prototype_plan(project, policy)
    mode_key = mode.lower()
    if mode_key not in DEFAULT_SIGNALS:
        raise ValueError(f"unsupported prototype mode: {mode}")

    selected_board = _resolve_board(board, policy, plan_data)
    selected_tool_version = _resolve_tool_version(tool_version, policy)
    selected_signals = signals or _signals_from_plan(plan_data, mode_key) or _policy_signal_defaults(policy, mode_key) or DEFAULT_SIGNALS[mode_key]
    selected_commands = tcl_commands or DEFAULT_TCL_COMMANDS
    report_path = _policy_path(project, policy, "database_preflight_report", "output/reports/loop3/preflight/database_preflight.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [
        "# Loop3 Database Preflight",
        "",
        f"- project: {project.name}",
        f"- board: {selected_board}",
        f"- mode: {mode_key}",
        f"- tool_version: {selected_tool_version}",
        "",
        "## Hardware Resources",
        "",
    ]
    missing: list[str] = []

    for signal in selected_signals:
        rows = []
        for variant in _signal_variants(signal):
            rows = query_fpga_hardware_resources(workspace, signal=variant, limit=8)
            if rows:
                break
            rows = query_fpga_hardware_resources(workspace, keyword=variant, limit=8)
            if rows:
                break
        if rows:
            lines.append(f"### {signal}")
            for row in rows:
                pin = row.get("package_pin") or row.get("mio_pin") or ""
                interface = row.get("interface") or ""
                description = _one_line(row.get("description"))
                lines.append(
                    f"- {row.get('signal_name')} | pin={pin} | interface={interface} | {description}"
                )
            lines.append("")
        else:
            missing.append(f"hardware resource not found: {signal}")
            lines.append(f"### {signal}")
            lines.append("- MISSING")
            lines.append("")

    lines.extend(["## Vivado Tcl Commands", ""])
    for command in selected_commands:
        rows = query_software_tcl_commands(
            workspace,
            command=command,
            tool="vivado",
            tool_version=selected_tool_version,
            limit=5,
        )
        if rows:
            row = rows[0]
            lines.append(f"- {command}: {row.get('summary') or row.get('syntax')}")
        else:
            missing.append(f"Vivado Tcl command not found: {command}")
            lines.append(f"- {command}: MISSING")

    lines.extend(["", "## Vitis Guide Topics", ""])
    if mode_key == "ps_pl":
        for keyword in DEFAULT_VITIS_TOPICS:
            rows = query_software_tcl_topics(
                workspace,
                keyword=keyword,
                tool_version=selected_tool_version,
                limit=3,
            )
            if rows:
                joined = "; ".join(_one_line(row.get("title"), limit=80) for row in rows)
                lines.append(f"- {keyword}: {joined}")
            else:
                missing.append(f"Vitis topic not found: {keyword}")
                lines.append(f"- {keyword}: MISSING")
    else:
        lines.append("- not required for pure PL mode")

    lines.extend(
        [
            "",
            "## Required Use",
            "",
            "- Run this preflight before generating Vivado or Vitis scripts.",
            "- Script generation must cite the hardware resource rows and Tcl command rows used.",
            "- If an item is missing, add or fix the library entry before board-specific script generation.",
            "",
            f"result: {'PASS' if not missing else 'FAIL'}",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return PrototypePreflightResult(report_path=report_path, missing_items=missing, board=selected_board, mode=mode_key)


def generate_xdc_from_database(
    workspace: Path,
    project_path: Path,
    *,
    ports: list[str] | None = None,
    output: str | None = None,
    clock_ports: list[str] | None = None,
) -> PrototypeFileResult:
    """Generate an XDC file from port=database_signal mappings."""

    workspace = workspace.resolve()
    project = require_project_instance(project_path)
    policy = _prototype_policy(project)
    plan_data = _load_prototype_plan(project, policy)
    selected_ports = ports or _port_mappings_from_plan(plan_data)
    if not selected_ports:
        raise ValueError("XDC generation requires --port entries or prototype_plan.pl_port_assignments")
    xdc_path = _project_path(project, output) if output else _policy_path(project, policy, "generated_xdc", "output/fpga/vivado/constraints/generated_board.xdc")
    xdc_path.parent.mkdir(parents=True, exist_ok=True)
    clocks = _parse_clock_ports(clock_ports or _list_value(plan_data.get("clock_ports")) or _policy_list(policy, "xdc_clock_ports"))

    lines = [
        "## Generated from local FPGA database. Do not hand-edit board facts here.",
        "## Regenerate with: hdlflow.cli generate-xdc",
        "",
    ]
    messages: list[str] = []
    used_pins: dict[str, str] = {}

    for mapping in selected_ports:
        port, signal = _split_mapping(mapping, "port")
        row = _find_hardware_resource(workspace, signal)
        if not row:
            raise ValueError(f"database resource not found for signal: {signal}")
        pin = str(row.get("package_pin") or "")
        if not pin:
            raise ValueError(f"resource has no PL package pin: {signal}")
        if pin in used_pins:
            raise ValueError(f"pin conflict: {pin} used by {used_pins[pin]} and {port}")
        used_pins[pin] = port

        iostandard = _iostandard_from_row(row)
        direction = str(row.get("direction") or "").lower()
        lines.append(f"## {port} <= {signal} ({row.get('signal_name')}, {row.get('interface')})")
        lines.append(f"set_property PACKAGE_PIN {pin} [get_ports {port}]")
        lines.append(f"set_property IOSTANDARD {iostandard} [get_ports {port}]")
        if direction == "output":
            lines.append(f"set_property DRIVE 8 [get_ports {port}]")
            lines.append(f"set_property SLEW SLOW [get_ports {port}]")
        elif "uart" in str(row.get("interface") or "").lower() and direction == "input":
            lines.append(f"set_property PULLUP true [get_ports {port}]")
        if port in clocks:
            lines.append(f"create_clock -name {port}_{clocks[port]['name']} -period {clocks[port]['period']} [get_ports {port}]")
        lines.append("")
        messages.append(f"{port}: {signal} -> {pin}")

    xdc_path.write_text("\n".join(lines), encoding="utf-8")
    return PrototypeFileResult(path=xdc_path, messages=messages)


def validate_prototype_plan(
    workspace: Path,
    project_path: Path,
    *,
    plan: str | None = None,
) -> PrototypeCheckResult:
    """Validate PS/PL planning facts before board script generation."""

    workspace = workspace.resolve()
    project = require_project_instance(project_path)
    policy = _prototype_policy(project)
    plan_path = _project_path(project, plan) if plan else _policy_path(project, policy, "prototype_plan", "work/loop3_fpga_proto/board_tests/prototype_plan.yaml")
    if not plan_path.exists():
        raise FileNotFoundError(f"missing prototype plan: {plan_path}")
    data = load_yaml(plan_path)
    report_path = _policy_path(project, policy, "prototype_plan_check_report", "output/reports/loop3/preflight/prototype_plan_check.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []
    warnings: list[str] = []

    try:
        selected_board = _resolve_board(str(data.get("board") or ""), policy, data)
    except ValueError as exc:
        selected_board = ""
        errors.append(str(exc))

    mode = str(data.get("mode") or "").lower()
    top_module = str(data.get("rtl_top_module") or "").strip()
    _check_prototype_mode_intent(project, mode, data, errors, warnings)
    if _is_placeholder(top_module):
        errors.append("rtl_top_module must be set to the real signed RTL top module; placeholder values such as change_me_top are not allowed")
    if mode == "ps_pl":
        _check_axi_regions(data.get("axi_regions", {}), errors)
        _check_axi_instances(data.get("axi_regions", {}), errors)
        _check_ddr_regions(data.get("ddr_regions", {}), errors, warnings)
        _check_cache_policy(data.get("cache_policy", {}), errors, warnings)
        _check_external_stimulus_boundary(project, data, errors, warnings)
    elif mode == "pl":
        if data.get("axi_regions"):
            _check_axi_regions(data.get("axi_regions", {}), errors)
        if data.get("ddr_regions"):
            warnings.append("ddr_regions present in pure PL mode; PS DDR checks are skipped")
    else:
        errors.append("mode must be pl or ps_pl")
    _check_resource_assignments(workspace, data, errors, warnings)

    lines = [
        "# Prototype Plan Check",
        "",
        f"- project: {project.name}",
        f"- plan: {plan_path.relative_to(project)}",
        f"- board: {selected_board or 'UNSET'}",
        f"- result: {'PASS' if not errors else 'FAIL'}",
        "",
        "## Errors",
        "",
    ]
    lines.extend([f"- {item}" for item in errors] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {item}" for item in warnings] or ["- none"])
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return PrototypeCheckResult(report_path=report_path, errors=errors, warnings=warnings)


def generate_ps_pl_bd_tcl(
    workspace: Path,
    project_path: Path,
    *,
    plan: str | None = None,
    output: str | None = None,
) -> PrototypeFileResult:
    """Generate a reusable PS7 + AXI-Lite BD Tcl skeleton from a prototype plan."""

    workspace = workspace.resolve()
    project = require_project_instance(project_path)
    policy = _prototype_policy(project)
    plan_path = _project_path(project, plan) if plan else _policy_path(project, policy, "prototype_plan", "work/loop3_fpga_proto/board_tests/prototype_plan.yaml")
    data = load_yaml(plan_path)
    mode = str(data.get("mode") or "").strip().lower()
    if mode != "ps_pl":
        raise ValueError("generate-ps-pl-bd requires prototype_plan.mode: ps_pl")

    evidence = _require_loop3_ps_pl_database_evidence(project, policy)
    boundary_errors: list[str] = []
    boundary_warnings: list[str] = []
    _check_external_stimulus_boundary(project, data, boundary_errors, boundary_warnings)
    if boundary_errors:
        raise ValueError("PS_PL BD generation blocked by external-stimulus boundary:\n- " + "\n- ".join(boundary_errors))
    db_messages = _require_ps_pl_generation_database_rows(workspace, policy)
    ps7_preset = _resolve_ps7_preset(project, policy, data)

    bd_path = _project_path(project, output) if output else _policy_path(project, policy, "generated_ps_pl_bd_tcl", "output/fpga/vivado/scripts/generated_ps_pl_bd.tcl")
    bd_path.parent.mkdir(parents=True, exist_ok=True)

    top_module = str(data.get("rtl_top_module") or "")
    if _is_placeholder(top_module):
        raise ValueError("prototype plan rtl_top_module must be set before PS_PL BD generation")
    bd_name = str(data.get("bd_name") or "ps_pl_system")
    fclk_mhz = str(data.get("fclk_mhz") or "100")
    axi_regions = data.get("axi_regions", {})
    first_region_name, first_region = _first_mapping(axi_regions)
    if not first_region:
        raise ValueError("prototype plan requires at least one axi_regions entry")
    base = str(first_region.get("base"))
    range_text = str(first_region.get("range") or "64K")
    inst_name = str(first_region.get("instance") or f"{top_module}_0")
    if _is_placeholder(inst_name):
        raise ValueError("prototype plan axi_regions.*.instance must be set before PS_PL BD generation")
    slave_intf = str(first_region.get("slave_interface") or "s00_axi")
    preset_lines = [
        "set ps7_cell_obj [get_bd_cells processing_system7_0]",
        f"set fclk_mhz {fclk_mhz}",
        f"source [file join $project_root {_tcl_file_join_parts(ps7_preset.relative_to(project))}]",
        "",
    ]

    lines = [
        "## Generated PS_PL Block Design Tcl from Loop3 database/UG-gated flow.",
        f"## database_preflight: {_project_relative_text(project, evidence['database_preflight'])}",
        f"## prototype_plan_check: {_project_relative_text(project, evidence['prototype_plan_check'])}",
        "## The command only runs after local Vivado Tcl and Vitis guide rows are found.",
        f"## ps7_preset: {_project_relative_text(project, ps7_preset)}",
        f"set bd_name {bd_name}",
        "create_bd_design $bd_name",
        "create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 processing_system7_0",
        "",
        *preset_lines,
        "set_property -dict [list \\",
        "    CONFIG.PCW_USE_M_AXI_GP0 {1} \\",
        "    CONFIG.PCW_USE_CR_FABRIC {1} \\",
        "    CONFIG.PCW_EN_CLK0_PORT {1} \\",
        f"    CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {{{fclk_mhz}}} \\",
        "    CONFIG.PCW_GPIO_MIO_GPIO_ENABLE {1} \\",
        "    CONFIG.PCW_UIPARAM_DDR_ENABLE {1} \\",
        "    CONFIG.PCW_UIPARAM_DDR_BUS_WIDTH {32 Bit} \\",
        "    CONFIG.PCW_USE_S_AXI_HP0 {0} \\",
        "    CONFIG.PCW_USE_S_AXI_HP1 {0} \\",
        "] [get_bd_cells processing_system7_0]",
        "",
        "apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 \\",
        "    -config {make_external \"FIXED_IO, DDR\" apply_board_preset \"0\" Master \"Disable\" Slave \"Disable\"} \\",
        "    [get_bd_cells processing_system7_0]",
        "",
        f"create_bd_cell -type module -reference {top_module} {inst_name}",
        "connect_bd_net [get_bd_pins processing_system7_0/FCLK_CLK0] [get_bd_pins processing_system7_0/M_AXI_GP0_ACLK]",
        f"connect_bd_net [get_bd_pins processing_system7_0/FCLK_CLK0] [get_bd_pins {inst_name}/s00_axi_aclk]",
        f"if {{[llength [get_bd_pins -quiet {inst_name}/s00_axi_aresetn]]}} {{",
        "    create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 axi_resetn_const",
        "    set_property -dict [list CONFIG.CONST_VAL {1} CONFIG.CONST_WIDTH {1}] [get_bd_cells axi_resetn_const]",
        f"    connect_bd_net [get_bd_pins axi_resetn_const/dout] [get_bd_pins {inst_name}/s00_axi_aresetn]",
        "}",
        f"if {{[llength [get_bd_pins -quiet {inst_name}/pl_resetn]]}} {{",
        "    create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 pl_resetn_const",
        "    set_property -dict [list CONFIG.CONST_VAL {1} CONFIG.CONST_WIDTH {1}] [get_bd_cells pl_resetn_const]",
        f"    connect_bd_net [get_bd_pins pl_resetn_const/dout] [get_bd_pins {inst_name}/pl_resetn]",
        "}",
        "",
        "apply_bd_automation -rule xilinx.com:bd_rule:axi4 \\",
        "    -config [list \\",
        "        Clk_master \"/processing_system7_0/FCLK_CLK0\" \\",
        "        Clk_slave \"/processing_system7_0/FCLK_CLK0\" \\",
        "        Clk_xbar \"/processing_system7_0/FCLK_CLK0\" \\",
        "        Master \"/processing_system7_0/M_AXI_GP0\" \\",
        f"        Slave \"/{inst_name}/{slave_intf}\" \\",
        "        ddr_seg \"Auto\" \\",
        "        intc_ip \"New AXI Interconnect\" \\",
        "        master_apm \"0\" \\",
        "    ] \\",
        f"    [get_bd_intf_pins {inst_name}/{slave_intf}]",
        "",
    ]
    for port_name, port_cfg in (data.get("bd_external_ports", {}) or {}).items():
        direction = str(port_cfg.get("direction") or "I")
        pin = str(port_cfg.get("bd_pin") or port_name)
        lines.append(f"set {port_name}_port [create_bd_port -dir {direction} {port_name}]")
        lines.append(f"connect_bd_net ${port_name}_port [get_bd_pins {inst_name}/{pin}]")
    lines.extend(
        [
            "",
            "assign_bd_address -target_address_space [get_bd_addr_spaces processing_system7_0/Data] \\",
            f"    -offset {base} -range {range_text} \\",
            f"    [get_bd_addr_segs {inst_name}/{slave_intf}/reg0] -force",
            "",
            "validate_bd_design",
            "save_bd_design",
            f"## first_axi_region={first_region_name}",
        ]
    )
    bd_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return PrototypeFileResult(path=bd_path, messages=[f"bd={bd_name}", f"axi_base={base}", *db_messages])


def generate_vitis_boot_files(
    project_path: Path,
    *,
    output_dir: str | None = None,
) -> PrototypeFileResult:
    """Generate Vitis boot image template files for FSBL + bitstream + app."""

    project = require_project_instance(project_path)
    policy = _prototype_policy(project)
    root = _project_path(project, output_dir) if output_dir else _policy_path(project, policy, "vitis_boot_dir", "output/fpga/vitis/boot")
    root.mkdir(parents=True, exist_ok=True)
    bif = root / "boot_image.bif"
    ps1 = root / "Build-BootImage.ps1"
    bif.write_text(
        "\n".join(
            [
                "the_ROM_image:",
                "{",
                "  [bootloader] ../workspace/<platform>/zynq_fsbl/fsbl.elf",
                "  ../../vivado/bitstream/<design>.bit",
                "  ../workspace/<app>/Debug/<app>.elf",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    ps1.write_text(
        "\n".join(
            [
                "param(",
                "    [string]$Bif = (Join-Path $PSScriptRoot 'boot_image.bif'),",
                "    [string]$Output = (Join-Path $PSScriptRoot 'BOOT.bin')",
                ")",
                "$ErrorActionPreference = 'Stop'",
                "$projectRoot = Resolve-Path (Join-Path $PSScriptRoot '..\\..\\..\\..')",
                "$workspaceRoot = Resolve-Path (Join-Path $projectRoot '..\\..')",
                "$vitisWrapper = Join-Path $workspaceRoot 'env\\tool\\scripts\\Invoke-HdlVitis.ps1'",
                "if (-not (Test-Path -LiteralPath $vitisWrapper)) { throw \"Invoke-HdlVitis wrapper not found: $vitisWrapper\" }",
                "$bootgenArgs = @('-image', $Bif, '-arch', 'zynq', '-o', $Output, '-w')",
                "& $vitisWrapper -Tool bootgen -Project $projectRoot.Path -WorkspacePath $workspaceRoot.Path -RunDir $PSScriptRoot -ToolArgs $bootgenArgs",
                "if ($LASTEXITCODE -ne 0) { throw \"Invoke-HdlVitis bootgen failed with code $LASTEXITCODE\" }",
                "Write-Host \"VITIS_BOOT_IMAGE_PASS output=$Output\"",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return PrototypeFileResult(path=root, messages=[f"bif={bif}", f"script={ps1}"])


def refresh_loop3_reports(project_path: Path) -> Loop3ReportRefreshResult:
    """Write canonical Loop3 reports from current Vivado/Vitis/board evidence."""

    project = require_project_instance(project_path)
    policy = _prototype_policy(project)
    plan = _load_prototype_plan(project, policy)
    mode = str(plan.get("mode") or "pl").strip().lower()
    board = _resolve_board(None, policy, plan)
    generated_at = _timestamp()

    reports = {
        "vivado": _policy_path(project, policy, "vivado_implementation_report", "output/reports/loop3/vivado_implementation_report.md"),
        "vitis": _policy_path(project, policy, "vitis_boot_report", "output/reports/loop3/vitis_boot_report.md"),
        "board": _policy_path(project, policy, "board_validation_report", "output/reports/loop3/board_validation_report.md"),
        "exit": _policy_path(project, policy, "loop3_exit_report", "output/reports/loop3/loop3_exit_report.md"),
    }
    for path in reports.values():
        path.parent.mkdir(parents=True, exist_ok=True)

    database_preflight = _policy_path(project, policy, "database_preflight_report", "output/reports/loop3/preflight/database_preflight.md")
    prototype_plan = _policy_path(project, policy, "prototype_plan_check_report", "output/reports/loop3/preflight/prototype_plan_check.md")
    timing = _policy_path(project, policy, "vivado_timing_report", "output/fpga/vivado/reports/post_impl_timing_summary.rpt")
    drc = _policy_path(project, policy, "vivado_drc_report", "output/fpga/vivado/reports/post_impl_drc.rpt")
    bitstreams = sorted((project / "output/fpga/vivado/bitstream").glob("*.bit"))
    xsa_files = sorted((project / "output/fpga").rglob("*.xsa"))
    elf_files = sorted((project / "output/fpga/vitis").rglob("*.elf"))
    boot_bins = sorted((project / "output/fpga/vitis/boot").glob("*.bin"))
    serial_log = _policy_path(project, policy, "serial_text_log", "output/reports/loop3/serial/latest_serial_text.log")
    serial_validation = project / "output/reports/loop3/serial/latest_serial_validation_report.md"
    program_logs = sorted((project / "output/fpga/vivado/logs").glob("program_bitstream_*.log"))
    ps_logs = sorted((project / "output/reports/loop3").glob("ps_app_download_*.log"))

    vivado_pass = (
        _report_has_pass(database_preflight)
        and _report_has_pass(prototype_plan)
        and timing.exists()
        and drc.exists()
        and bool(bitstreams)
    )
    vitis_required = mode == "ps_pl"
    vitis_pass = (not vitis_required) or bool(elf_files or boot_bins or ps_logs)
    board_pass = _report_has_pass(serial_validation) and serial_log.exists()
    exit_pass = vivado_pass and vitis_pass and board_pass

    _write_lines(
        reports["vivado"],
        [
            "# Loop3 Vivado Implementation Report",
            "",
            f"- project: {project.name}",
            f"- generated_at: {generated_at}",
            f"- mode: {mode}",
            f"- top_module: {plan.get('rtl_top_module') or ''}",
            f"- bitstream: {_first_rel(project, bitstreams)}",
            f"- xsa: {_first_rel(project, xsa_files)}",
            f"- result: {'PASS' if vivado_pass else 'FAIL'}",
            "",
            "## Evidence",
            "",
            f"- database_preflight: {_status_with_path(project, database_preflight, _report_has_pass(database_preflight))}",
            f"- prototype_plan_check: {_status_with_path(project, prototype_plan, _report_has_pass(prototype_plan))}",
            f"- timing_report: {_status_with_path(project, timing, timing.exists())}",
            f"- drc_report: {_status_with_path(project, drc, drc.exists())}",
            f"- bitstream: {_first_rel(project, bitstreams) or 'missing'}",
            f"- hw_platform: {_first_rel(project, xsa_files) or 'not-generated'}",
        ],
    )

    _write_lines(
        reports["vitis"],
        [
            "# Loop3 Vitis Boot And PS App Report",
            "",
            f"- project: {project.name}",
            f"- generated_at: {generated_at}",
            f"- mode: {mode}",
            f"- required: {'yes' if vitis_required else 'no'}",
            f"- result: {'PASS' if vitis_pass else 'FAIL'}",
            "",
            "## Evidence",
            "",
            f"- elf: {_first_rel(project, elf_files) or 'not-found'}",
            f"- boot_bin: {_first_rel(project, boot_bins) or 'not-found'}",
            f"- ps_download_log: {_first_rel(project, ps_logs) or 'not-found'}",
            f"- cache_policy: {'documented' if plan.get('cache_policy') else 'not-documented'}",
        ],
    )

    _write_lines(
        reports["board"],
        [
            "# Loop3 Board Validation Report",
            "",
            f"- project: {project.name}",
            f"- generated_at: {generated_at}",
            f"- board: {board}",
            f"- image: {_first_rel(project, bitstreams) or 'missing'}",
            f"- serial_log: {_project_relative_text(project, serial_log)}",
            f"- result: {'PASS' if board_pass else 'FAIL'}",
            "",
            "## Board Checks",
            "",
            f"- FPGA download/programming: {'PASS' if program_logs else 'FAIL'}",
            f"- serial validation: {'PASS' if _report_has_pass(serial_validation) else 'FAIL'}",
            f"- serial raw log: {'PASS' if serial_log.exists() else 'FAIL'}",
            f"- LED/GPIO observation: {'PASS' if board_pass else 'NOT_RECORDED'}",
            f"- DDR or PS/PL data path: {'PASS' if board_pass else 'FAIL'}",
        ],
    )

    _write_lines(
        reports["exit"],
        [
            "# Loop3 Exit Report",
            "",
            f"- project: {project.name}",
            f"- generated_at: {generated_at}",
            f"- result: {'PASS' if exit_pass else 'FAIL'}",
            "",
            "## Closure",
            "",
            f"- vivado_implementation_report: {'PASS' if vivado_pass else 'FAIL'}",
            f"- vitis_boot_report: {'PASS' if vitis_pass else 'FAIL'}",
            f"- board_validation_report: {'PASS' if board_pass else 'FAIL'}",
            f"- serial_validation: {'PASS' if _report_has_pass(serial_validation) else 'FAIL'}",
        ],
    )

    statuses = {
        "vivado_implementation_report": "PASS" if vivado_pass else "FAIL",
        "vitis_boot_report": "PASS" if vitis_pass else "FAIL",
        "board_validation_report": "PASS" if board_pass else "FAIL",
        "loop3_exit_report": "PASS" if exit_pass else "FAIL",
    }
    return Loop3ReportRefreshResult(report_paths=list(reports.values()), statuses=statuses)


def _prototype_policy(project: Path) -> dict[str, Any]:
    try:
        data = load_project(project).data
    except Exception:
        return {}
    nodes = data.get("nodes", {}) if isinstance(data, dict) else {}
    node = nodes.get("work/loop3_fpga_proto", {}) if isinstance(nodes, dict) else {}
    policy = node.get("prototype_policy", {}) if isinstance(node, dict) else {}
    return policy if isinstance(policy, dict) else {}


def _load_prototype_plan(project: Path, policy: dict[str, Any]) -> dict[str, Any]:
    path = _policy_path(project, policy, "prototype_plan", "work/loop3_fpga_proto/board_tests/prototype_plan.yaml")
    if not path.exists():
        return {}
    try:
        data = load_yaml(path)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _require_loop3_ps_pl_database_evidence(project: Path, policy: dict[str, Any]) -> dict[str, Path]:
    preflight_path = _policy_path(project, policy, "database_preflight_report", "output/reports/loop3/preflight/database_preflight.md")
    plan_check_path = _policy_path(project, policy, "prototype_plan_check_report", "output/reports/loop3/preflight/prototype_plan_check.md")
    preflight = _read_required_report(preflight_path, "Loop3 database preflight")
    plan_check = _read_required_report(plan_check_path, "prototype plan check")

    _require_report_marker(preflight_path, preflight, "result: PASS")
    _require_report_marker(preflight_path, preflight, "- mode: ps_pl")
    _require_report_marker(preflight_path, preflight, "## Vivado Tcl Commands")
    _require_report_marker(preflight_path, preflight, "## Vitis Guide Topics")
    _require_report_marker(plan_check_path, plan_check, "- result: PASS")
    return {"database_preflight": preflight_path, "prototype_plan_check": plan_check_path}


def _require_ps_pl_generation_database_rows(workspace: Path, policy: dict[str, Any]) -> list[str]:
    tool_version = _resolve_tool_version(None, policy)
    missing: list[str] = []
    for command in DEFAULT_TCL_COMMANDS:
        rows = query_software_tcl_commands(
            workspace,
            command=command,
            tool="vivado",
            tool_version=tool_version,
            limit=1,
        )
        if not rows:
            missing.append(f"Vivado Tcl command not found in database: {command}")
    for keyword in DEFAULT_VITIS_TOPICS:
        rows = query_software_tcl_topics(
            workspace,
            keyword=keyword,
            tool_version=tool_version,
            limit=1,
        )
        if not rows:
            missing.append(f"Vitis guide topic not found in database: {keyword}")
    if missing:
        raise ValueError("PS_PL BD generation requires local database/UG evidence:\n- " + "\n- ".join(missing))
    return [f"database_ug_checked=vivado_tcl:{len(DEFAULT_TCL_COMMANDS)}", f"database_ug_checked=vitis_topics:{len(DEFAULT_VITIS_TOPICS)}"]


def _resolve_ps7_preset(project: Path, policy: dict[str, Any], plan_data: dict[str, Any]) -> Path:
    board = _resolve_board(None, policy, plan_data)
    rel_candidates = [
        plan_data.get("ps7_preset_tcl"),
        policy.get("ps7_preset_tcl"),
        f"work/loop3_fpga_proto/board_profiles/{board}_ps7_preset.tcl",
    ]
    for candidate in rel_candidates:
        text = str(candidate or "").strip()
        if not text or _is_placeholder(text):
            continue
        path = _project_path(project, text)
        if path.exists():
            return path
    raise FileNotFoundError(
        "PS_PL BD generation requires a reviewed PS7 preset Tcl from the board profile; "
        "set prototype_plan.ps7_preset_tcl or prototype_policy.ps7_preset_tcl"
    )


def _read_required_report(path: Path, label: str) -> str:
    if not path.exists():
        raise FileNotFoundError(f"missing required {label}: {path}")
    return path.read_text(encoding="utf-8", errors="ignore")


def _require_report_marker(path: Path, text: str, marker: str) -> None:
    if marker not in text:
        raise ValueError(f"required marker not found in {path}: {marker}")


def _project_relative_text(project: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _timestamp() -> str:
    from datetime import datetime

    return datetime.now().isoformat(timespec="seconds")


def _write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _report_has_pass(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="ignore")
    return bool(re.search(r"(?mi)^\s*-?\s*result:\s*PASS\s*$", text))


def _first_rel(project: Path, paths: list[Path]) -> str:
    return _project_relative_text(project, paths[0]) if paths else ""


def _status_with_path(project: Path, path: Path, ok: bool) -> str:
    return ("PASS " if ok else "FAIL ") + _project_relative_text(project, path)


def _tcl_file_join_parts(path: Path) -> str:
    return " ".join(str(part) for part in path.parts)


def _resolve_board(board: str | None, policy: dict[str, Any], plan_data: dict[str, Any]) -> str:
    candidates = [
        board,
        policy.get("selected_board"),
        plan_data.get("board"),
        policy.get("default_board"),
        "navigator_zynq_7020",
    ]
    for candidate in candidates:
        text = str(candidate or "").strip()
        if text and not _is_placeholder(text):
            return text
    raise ValueError("prototype board is not configured; set --board or nodes.work/loop3_fpga_proto.prototype_policy.selected_board")


def _resolve_tool_version(tool_version: str | None, policy: dict[str, Any]) -> str:
    candidates = [tool_version, policy.get("tool_version"), "2024.2"]
    for candidate in candidates:
        text = str(candidate or "").strip()
        if text and not _is_placeholder(text):
            return text
    return "2024.2"


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    return (
        not normalized
        or normalized in {"change_me", "change_me_board", "prototype_board_unset", "todo", "tbd", "none", "null"}
        or "change_me" in normalized
    )


def _signals_from_plan(plan_data: dict[str, Any], mode: str) -> list[str]:
    signals: list[str] = []
    if mode == "ps_pl":
        signals.extend(_mapping_values(plan_data.get("ps_mio_assignments")))
    signals.extend(_mapping_values(plan_data.get("pl_port_assignments")))
    return _dedupe(signals)


def _policy_signal_defaults(policy: dict[str, Any], mode: str) -> list[str]:
    resource_queries = policy.get("resource_queries", {})
    if not isinstance(resource_queries, dict):
        return []
    values = resource_queries.get(mode, [])
    if not isinstance(values, list):
        return []
    return _dedupe(str(item) for item in values if str(item).strip())


def _mapping_values(mapping: Any) -> list[str]:
    if not isinstance(mapping, dict):
        return []
    return [str(value).strip() for value in mapping.values() if str(value).strip()]


def _port_mappings_from_plan(plan_data: dict[str, Any]) -> list[str]:
    assignments = plan_data.get("pl_port_assignments", {})
    if not isinstance(assignments, dict):
        return []
    return [f"{port}={signal}" for port, signal in assignments.items() if str(port).strip() and str(signal).strip()]


def _policy_list(policy: dict[str, Any], key: str) -> list[str]:
    value = policy.get(key, [])
    return _list_value(value)


def _list_value(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _dedupe(values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in result:
            result.append(text)
    return result


def _policy_path(project: Path, policy: dict[str, Any], key: str, default: str) -> Path:
    value = policy.get(key)
    rel = str(value).strip() if isinstance(value, str) and value.strip() else default
    return _project_path(project, rel)


def _project_path(project: Path, rel: str | None) -> Path:
    if not rel:
        raise ValueError("project-relative path is required")
    raw = Path(rel)
    if raw.is_absolute() or ".." in raw.parts:
        raise ValueError(f"path must stay inside project: {rel}")
    path = (project / raw).resolve()
    try:
        path.relative_to(project.resolve())
    except ValueError as exc:
        raise ValueError(f"path must stay inside project: {rel}") from exc
    return path


def _one_line(value: object, *, limit: int = 140) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _signal_variants(signal: str) -> list[str]:
    normalized = signal.upper()
    variants = [signal]
    replacements = {
        "PS_KEY0": ["PS_KEY0", "PS_KEY", "ps_key[0]", "KEY0"],
        "PS_KEY1": ["PS_KEY1", "PS_KEY", "ps_key[1]", "KEY1"],
        "PS_LED0": ["PS_LED0", "PS_LED", "ps_led[0]"],
        "PS_LED1": ["PS_LED1", "PS_LED", "ps_led[1]"],
        "PL_LED0": ["PL_LED0", "PL_LED", "led[0]"],
        "PL_LED1": ["PL_LED1", "PL_LED", "led[1]"],
        "PL_GCLK_50MHZ": ["PL_GCLK_50MHZ", "PL_GCLK", "sys_clk", "CLK"],
    }
    variants.extend(replacements.get(normalized, []))
    deduped: list[str] = []
    for item in variants:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _find_hardware_resource(workspace: Path, signal: str) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for variant in _signal_variants(signal):
        rows = query_fpga_hardware_resources(workspace, signal=variant, limit=8)
        if not rows:
            rows = query_fpga_hardware_resources(workspace, keyword=variant, limit=8)
        if rows:
            candidates.extend(rows)
    if not candidates:
        return None
    return _best_resource_row(candidates, signal)


def _best_resource_row(rows: list[dict[str, Any]], signal: str) -> dict[str, Any]:
    needle = signal.upper()
    for row in rows:
        haystack = " ".join([str(row.get("signal_name") or ""), str(row.get("aliases") or "")]).upper()
        if needle in haystack and row.get("package_pin"):
            return row
    for row in rows:
        if row.get("package_pin"):
            return row
    for row in rows:
        haystack = " ".join([str(row.get("signal_name") or ""), str(row.get("aliases") or "")]).upper()
        if needle in haystack:
            return row
    return rows[0]


def _iostandard_from_row(row: dict[str, Any]) -> str:
    text = " ".join(str(row.get(key) or "") for key in ("bank", "description", "io_table_links"))
    if "1.8" in text or "1V8" in text.upper():
        return "LVCMOS18"
    return "LVCMOS33"


def _split_mapping(value: str, label: str) -> tuple[str, str]:
    if "=" not in value:
        raise ValueError(f"{label} mapping must be NAME=SIGNAL, got: {value}")
    left, right = value.split("=", 1)
    if not left.strip() or not right.strip():
        raise ValueError(f"{label} mapping must be NAME=SIGNAL, got: {value}")
    return left.strip(), right.strip()


def _parse_clock_ports(values: list[str]) -> dict[str, dict[str, str]]:
    clocks: dict[str, dict[str, str]] = {}
    for item in values:
        port, period = _split_mapping(item, "clock")
        clocks[port] = {"period": period, "name": period.replace(".", "p").replace(" ", "")}
    return clocks


def _parse_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    text = str(value).strip()
    return int(text, 0)


def _first_mapping(mapping: Any) -> tuple[str, dict[str, Any]]:
    if not isinstance(mapping, dict) or not mapping:
        return "", {}
    key = next(iter(mapping.keys()))
    value = mapping[key]
    if not isinstance(value, dict):
        return str(key), {}
    return str(key), value


def _check_axi_regions(regions: Any, errors: list[str]) -> None:
    if not isinstance(regions, dict) or not regions:
        errors.append("axi_regions is required")
        return
    parsed: list[tuple[str, int, int]] = []
    for name, raw in regions.items():
        if not isinstance(raw, dict):
            errors.append(f"axi region {name} must be a mapping")
            continue
        try:
            base = _parse_int(raw.get("base"))
            if raw.get("high") is not None:
                high = _parse_int(raw.get("high"))
            else:
                high = base + _parse_range(raw.get("range") or "64K") - 1
        except Exception as exc:
            errors.append(f"axi region {name} has invalid address/range: {exc}")
            continue
        if high < base:
            errors.append(f"axi region {name} high address is below base")
        parsed.append((str(name), base, high))
    for index, left in enumerate(parsed):
        for right in parsed[index + 1 :]:
            if left[1] <= right[2] and right[1] <= left[2]:
                errors.append(f"axi address overlap: {left[0]} and {right[0]}")


def _check_axi_instances(regions: Any, errors: list[str]) -> None:
    if not isinstance(regions, dict):
        return
    for name, raw in regions.items():
        if not isinstance(raw, dict):
            continue
        instance = str(raw.get("instance") or "").strip()
        if _is_placeholder(instance):
            errors.append(f"axi region {name} instance must name the real RTL/BD instance; placeholder values are not allowed")
        slave_interface = str(raw.get("slave_interface") or "").strip()
        if not slave_interface or _is_placeholder(slave_interface):
            errors.append(f"axi region {name} slave_interface must be set")


def _parse_range(value: Any) -> int:
    text = str(value).strip().upper()
    if text.endswith("K"):
        return int(text[:-1], 0) * 1024
    if text.endswith("M"):
        return int(text[:-1], 0) * 1024 * 1024
    return int(text, 0)


def _check_ddr_regions(regions: Any, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(regions, dict) or not regions:
        warnings.append("ddr_regions not provided; DDR range cannot be checked")
        return
    ps_region = regions.get("ps_ddr")
    if not isinstance(ps_region, dict):
        errors.append("ddr_regions.ps_ddr is required for PS_PL plans")
        return
    try:
        ps_base = _parse_int(ps_region.get("base"))
        ps_size = _parse_range(ps_region.get("size") or ps_region.get("range") or 0)
        ps_high = ps_base + ps_size - 1
    except Exception as exc:
        errors.append(f"invalid ps_ddr region: {exc}")
        return
    for name, raw in regions.items():
        if name == "ps_ddr" or not isinstance(raw, dict):
            continue
        try:
            base = _parse_int(raw.get("base"))
            size = _parse_range(raw.get("size") or raw.get("range") or 4)
            high = base + size - 1
        except Exception as exc:
            errors.append(f"invalid DDR test region {name}: {exc}")
            continue
        if base < ps_base or high > ps_high:
            errors.append(f"DDR region {name} outside ps_ddr range")


def _check_cache_policy(policy: Any, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(policy, dict):
        errors.append("cache_policy mapping is required")
        return
    if not policy.get("flush_after_ps_write"):
        errors.append("cache_policy.flush_after_ps_write must be true")
    if not policy.get("invalidate_before_ps_read"):
        errors.append("cache_policy.invalidate_before_ps_read must be true")
    if not policy.get("document_cache_lines"):
        warnings.append("cache_policy.document_cache_lines is recommended")


def _check_external_stimulus_boundary(project: Path, plan_data: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    policy = plan_data.get("external_stimulus_policy", {})
    policy_required = not isinstance(policy, dict) or bool(policy.get("rtl_must_not_format_uart_messages", True))
    if not policy_required:
        warnings.append("external_stimulus_policy disables RTL message-format screening for PS_PL")
        return

    rtl_root = project / "output" / "rtl"
    if not rtl_root.is_dir():
        errors.append("output/rtl is missing; cannot verify external-stimulus RTL boundary")
        return

    forbidden_hits: list[str] = []
    for path in sorted(rtl_root.glob("*.v")):
        code = _strip_verilog_comments(path.read_text(encoding="utf-8", errors="ignore"))
        stem = path.stem.lower()
        if re.search(r"(^|_)(stimulus|reporter|model)($|_)", stem):
            forbidden_hits.append(f"{path.name}: generated RTL filename implies stimulus/model/reporter ownership")
        if re.search(r"\bfunction\b[\s\S]{0,160}\b(message_byte|hex_ascii|ascii)\b", code, flags=re.IGNORECASE):
            forbidden_hits.append(f"{path.name}: RTL function formats protocol/message bytes")
        if re.search(r"=\s*\"[ -~]+\"", code):
            forbidden_hits.append(f"{path.name}: synthesizable RTL contains literal ASCII/message text")
        if re.search(r"\bread\s+data\s*=", code, flags=re.IGNORECASE):
            forbidden_hits.append(f"{path.name}: RTL contains fixed read-data report text")
        if re.search(r"\b(SECOND_CYCLES|READ_CYCLES|DDR_TEST_ADDR)\b", code):
            forbidden_hits.append(f"{path.name}: RTL appears to model PS DDR/software timing")
    if forbidden_hits:
        errors.append("PS_PL/bus protocol stimulus must be external to synthesizable RTL: " + "; ".join(forbidden_hits))


def _strip_verilog_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def _check_resource_assignments(
    workspace: Path,
    data: dict[str, Any],
    errors: list[str],
    warnings: list[str],
) -> None:
    used_mio: dict[str, str] = {}
    used_pins: dict[str, str] = {}
    for name, signal in (data.get("ps_mio_assignments", {}) or {}).items():
        row = _find_mio_resource(workspace, str(signal))
        if not row:
            errors.append(f"PS MIO resource not found: {name}={signal}")
            continue
        mio = str(row.get("mio_pin") or "")
        if not mio:
            errors.append(f"PS assignment does not resolve to MIO: {name}={signal}")
            continue
        if mio in used_mio:
            errors.append(f"PS MIO conflict: {mio} used by {used_mio[mio]} and {name}")
        used_mio[mio] = str(name)

    for port, signal in (data.get("pl_port_assignments", {}) or {}).items():
        row = _find_hardware_resource(workspace, str(signal))
        if not row:
            errors.append(f"PL port resource not found: {port}={signal}")
            continue
        pin = str(row.get("package_pin") or "")
        if not pin:
            warnings.append(f"PL resource has no package pin, check manually: {port}={signal}")
            continue
        if pin in used_pins:
            errors.append(f"PL pin conflict: {pin} used by {used_pins[pin]} and {port}")
        used_pins[pin] = str(port)


def _check_prototype_mode_intent(
    project: Path,
    mode: str,
    data: dict[str, Any],
    errors: list[str],
    warnings: list[str],
) -> None:
    intent_text = _prototype_intent_text(project).lower()
    source_declares_pure_pl = "pure pl" in intent_text or "pure-pl" in intent_text
    has_ps_assignments = bool(data.get("ps_mio_assignments") or data.get("ddr_regions") or data.get("axi_regions"))
    if source_declares_pure_pl and mode == "ps_pl":
        allow_wrapper = bool(data.get("allow_ps_pl_wrapper"))
        rationale = str(data.get("mode_rationale") or "").strip()
        if not allow_wrapper or not rationale:
            errors.append(
                "prototype mode conflict: DocParse/source prototype intent says pure PL, but board_tests/prototype_plan.yaml uses ps_pl; "
                "set mode: pl or add allow_ps_pl_wrapper: true with mode_rationale"
            )
    if mode == "pl" and has_ps_assignments:
        warnings.append("pure PL mode has PS/AXI/DDR assignments; remove them or switch to ps_pl with rationale")


def _prototype_intent_text(project: Path) -> str:
    paths = [
        project / "work/docparse" / "prototype" / "prototype_plan.yaml",
        project / "work/docparse" / "prototype" / "prototype_plan.md",
        project / "input" / "spec" / "requirements.md",
    ]
    parts = []
    for path in paths:
        if path.exists():
            parts.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def _find_mio_resource(workspace: Path, signal: str) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for variant in _signal_variants(signal):
        rows = query_fpga_hardware_resources(workspace, signal=variant, limit=8)
        if not rows:
            rows = query_fpga_hardware_resources(workspace, keyword=variant, limit=8)
        candidates.extend(rows)
    for row in candidates:
        if row.get("mio_pin"):
            haystack = " ".join([str(row.get("signal_name") or ""), str(row.get("aliases") or "")]).upper()
            if signal.upper() in haystack:
                return row
    for row in candidates:
        if row.get("mio_pin"):
            return row
    return None
