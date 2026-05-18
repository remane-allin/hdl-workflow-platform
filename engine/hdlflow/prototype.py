"""Loop3 FPGA prototype preflight checks."""

from __future__ import annotations

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
    report_path = _policy_path(project, policy, "database_preflight_report", "05_Output/reports/loop3/preflight/database_preflight.md")
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
    xdc_path = _project_path(project, output) if output else _policy_path(project, policy, "generated_xdc", "05_Output/fpga/vivado/constraints/generated_board.xdc")
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
    plan_path = _project_path(project, plan) if plan else _policy_path(project, policy, "prototype_plan", "04_Loop3_FPGA_Prototype/board_tests/prototype_plan.yaml")
    if not plan_path.exists():
        raise FileNotFoundError(f"missing prototype plan: {plan_path}")
    data = load_yaml(plan_path)
    report_path = _policy_path(project, policy, "prototype_plan_check_report", "05_Output/reports/loop3/preflight/prototype_plan_check.md")
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
    project_path: Path,
    *,
    plan: str | None = None,
    output: str | None = None,
) -> PrototypeFileResult:
    """Generate a reusable PS7 + AXI-Lite BD Tcl skeleton from a prototype plan."""

    project = require_project_instance(project_path)
    policy = _prototype_policy(project)
    plan_path = _project_path(project, plan) if plan else _policy_path(project, policy, "prototype_plan", "04_Loop3_FPGA_Prototype/board_tests/prototype_plan.yaml")
    data = load_yaml(plan_path)
    bd_path = _project_path(project, output) if output else _policy_path(project, policy, "generated_ps_pl_bd_tcl", "05_Output/fpga/vivado/scripts/generated_ps_pl_bd.tcl")
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

    lines = [
        "## Generated PS_PL Block Design Tcl skeleton.",
        "## Fill project-specific PS presets only through reviewed database-backed plan updates.",
        f"set bd_name {bd_name}",
        "create_bd_design $bd_name",
        "create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 processing_system7_0",
        "",
        "set_property -dict [list \\",
        "    CONFIG.PCW_USE_M_AXI_GP0 {1} \\",
        "    CONFIG.PCW_USE_CR_FABRIC {1} \\",
        "    CONFIG.PCW_EN_CLK0_PORT {1} \\",
        f"    CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {{{fclk_mhz}}} \\",
        "    CONFIG.PCW_GPIO_MIO_GPIO_ENABLE {1} \\",
        "    CONFIG.PCW_UIPARAM_DDR_ENABLE {1} \\",
        "    CONFIG.PCW_UIPARAM_DDR_BUS_WIDTH {32 Bit} \\",
        "] [get_bd_cells processing_system7_0]",
        "",
        "apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 \\",
        "    -config {make_external \"FIXED_IO, DDR\" apply_board_preset \"0\" Master \"Disable\" Slave \"Disable\"} \\",
        "    [get_bd_cells processing_system7_0]",
        "",
        f"create_bd_cell -type module -reference {top_module} {inst_name}",
        "connect_bd_net [get_bd_pins processing_system7_0/FCLK_CLK0] [get_bd_pins processing_system7_0/M_AXI_GP0_ACLK]",
        f"connect_bd_net [get_bd_pins processing_system7_0/FCLK_CLK0] [get_bd_pins {inst_name}/s00_axi_aclk]",
        f"connect_bd_net [get_bd_pins processing_system7_0/FCLK_RESET0_N] [get_bd_pins {inst_name}/s00_axi_aresetn]",
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
    return PrototypeFileResult(path=bd_path, messages=[f"bd={bd_name}", f"axi_base={base}"])


def generate_vitis_boot_files(
    project_path: Path,
    *,
    output_dir: str | None = None,
) -> PrototypeFileResult:
    """Generate Vitis boot image template files for FSBL + bitstream + app."""

    project = require_project_instance(project_path)
    policy = _prototype_policy(project)
    root = _project_path(project, output_dir) if output_dir else _policy_path(project, policy, "vitis_boot_dir", "05_Output/fpga/vitis/boot")
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
                "    [string]$Bootgen = '',",
                "    [string]$Bif = (Join-Path $PSScriptRoot 'boot_image.bif'),",
                "    [string]$Output = (Join-Path $PSScriptRoot 'BOOT.bin')",
                ")",
                "$ErrorActionPreference = 'Stop'",
                "$projectRoot = Resolve-Path (Join-Path $PSScriptRoot '..\\..\\..\\..')",
                "$workspaceRoot = Resolve-Path (Join-Path $projectRoot '..\\..')",
                "$engineRoot = Join-Path $workspaceRoot 'engine'",
                "if (-not $Bootgen) {",
                "    Push-Location $engineRoot",
                "    try {",
                "        $Bootgen = (& python -m hdlflow.cli get-tool-launcher --workspace .. --tool vitis --launcher bootgen_bat).Trim()",
                "    }",
                "    finally {",
                "        Pop-Location",
                "    }",
                "}",
                "if (-not (Test-Path $Bootgen)) { throw \"bootgen not found: $Bootgen\" }",
                "& $Bootgen -image $Bif -arch zynq -o $Output -w",
                "if ($LASTEXITCODE -ne 0) { throw \"bootgen failed with code $LASTEXITCODE\" }",
                "Write-Host \"VITIS_BOOT_IMAGE_PASS output=$Output\"",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return PrototypeFileResult(path=root, messages=[f"bif={bif}", f"script={ps1}"])


def _prototype_policy(project: Path) -> dict[str, Any]:
    try:
        data = load_project(project).data
    except Exception:
        return {}
    nodes = data.get("nodes", {}) if isinstance(data, dict) else {}
    node = nodes.get("04_Loop3_FPGA_Prototype", {}) if isinstance(nodes, dict) else {}
    policy = node.get("prototype_policy", {}) if isinstance(node, dict) else {}
    return policy if isinstance(policy, dict) else {}


def _load_prototype_plan(project: Path, policy: dict[str, Any]) -> dict[str, Any]:
    path = _policy_path(project, policy, "prototype_plan", "04_Loop3_FPGA_Prototype/board_tests/prototype_plan.yaml")
    if not path.exists():
        return {}
    try:
        data = load_yaml(path)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


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
    raise ValueError("prototype board is not configured; set --board or nodes.04_Loop3_FPGA_Prototype.prototype_policy.selected_board")


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
        project / "01_DocParse" / "prototype" / "prototype_plan.yaml",
        project / "01_DocParse" / "prototype" / "prototype_plan.md",
        project / "00_SPEC" / "requirements" / "requirements.md",
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
