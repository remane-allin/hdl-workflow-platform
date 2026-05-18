"""User-readable design document generation for HDL workflow projects."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .project import require_project_instance
from .simple_yaml import load_yaml


REPORT_REL = "05_Output/reports/design/design_rule_and_architecture.md"
MANIFEST_REL = "05_Output/reports/design/design_doc_manifest.json"


@dataclass(frozen=True)
class DesignDocResult:
    report_path: Path
    manifest_path: Path
    warnings: list[str]
    errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class RtlPort:
    name: str
    direction: str
    width: str
    description: str


@dataclass(frozen=True)
class RtlModule:
    file: str
    name: str
    description: str
    scope: list[str]
    parameters: list[str]
    ports: list[RtlPort]
    instances: list[str]


@dataclass(frozen=True)
class UvmFile:
    file: str
    category: str
    classes: list[str]
    purpose: str


def generate_design_document(project_path: Path) -> DesignDocResult:
    """Generate the ordered user-facing design document and sync manifest."""

    project = require_project_instance(project_path)
    snapshot = _collect_snapshot(project)
    previous = _load_manifest(project)
    lines = _render_document(project, snapshot, previous)

    report_path = project / REPORT_REL
    manifest_path = project / MANIFEST_REL
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = _build_manifest(project, snapshot, report_path)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    warnings = list(snapshot["warnings"])
    errors: list[str] = []
    return DesignDocResult(report_path, manifest_path, warnings, errors)


def check_design_document(project_path: Path, *, sections: list[str] | None = None) -> DesignDocResult:
    """Check whether the generated design document is present and current."""

    project = require_project_instance(project_path)
    report_path = project / REPORT_REL
    manifest_path = project / MANIFEST_REL
    errors: list[str] = []
    warnings: list[str] = []

    if not report_path.exists():
        errors.append(f"missing generated design document: {REPORT_REL}")
    if not manifest_path.exists():
        errors.append(f"missing design document manifest: {MANIFEST_REL}")
        return DesignDocResult(report_path, manifest_path, warnings, errors)

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"cannot read design document manifest: {exc}")
        return DesignDocResult(report_path, manifest_path, warnings, errors)

    snapshot = _collect_snapshot(project)
    current_signature = _source_signature(snapshot["source_hashes"])
    if manifest.get("source_signature") != current_signature:
        errors.append("design document is stale; rerun generate-design-doc")

    expected_sections = sections or ["requirements", "rtl", "uvm", "fpga"]
    documented_sections = set(manifest.get("sections", []))
    missing_sections = sorted(set(expected_sections) - documented_sections)
    if missing_sections:
        errors.append("design document missing section(s): " + ", ".join(missing_sections))

    current_rtl = {item.name: item.file for item in snapshot["rtl_modules"]}
    manifest_rtl = manifest.get("rtl_modules", {})
    if "rtl" in expected_sections and current_rtl != manifest_rtl:
        errors.append("RTL module list changed since design document generation")

    current_uvm = sorted(item.file for item in snapshot["uvm_files"])
    manifest_uvm = sorted(manifest.get("uvm_files", []))
    if "uvm" in expected_sections and current_uvm != manifest_uvm:
        errors.append("UVM file list changed since design document generation")

    current_fpga = snapshot["fpga"]["mode_summary"]
    if "fpga" in expected_sections and manifest.get("fpga_mode_summary") != current_fpga:
        errors.append("FPGA prototype mode summary changed since design document generation")

    warnings.extend(snapshot["warnings"])
    return DesignDocResult(report_path, manifest_path, warnings, errors)


def design_doc_report_rel() -> str:
    return REPORT_REL


def design_doc_manifest_rel() -> str:
    return MANIFEST_REL


def _collect_snapshot(project: Path) -> dict[str, Any]:
    data: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "requirements": _load_data(project, "00_SPEC/requirements/srs.yaml"),
        "acceptance": _load_data(project, "00_SPEC/requirements/acceptance_criteria.yaml"),
        "module_plan": _load_data(project, "01_DocParse/architecture/module_plan.yaml"),
        "interfaces": _load_data(project, "01_DocParse/architecture/interface_contracts.yaml"),
        "dataflow": _load_data(project, "01_DocParse/architecture/dataflow.yaml"),
        "timing": _load_data(project, "01_DocParse/architecture/timing_model.yaml"),
        "rtl_rules": _load_data(project, "01_DocParse/architecture/rtl_planning_rules.yaml"),
        "verification": _load_data(project, "01_DocParse/verification/verification_plan.yaml"),
        "assertions": _load_data(project, "01_DocParse/verification/assertion_plan.yaml"),
        "coverage": _load_data(project, "01_DocParse/verification/coverage_plan.yaml"),
        "docparse_prototype": _load_data(project, "01_DocParse/prototype/prototype_plan.yaml"),
        "loop3_prototype": _load_data(project, "04_Loop3_FPGA_Prototype/board_tests/prototype_plan.yaml"),
        "uvm_manifest": _load_data(project, "05_Output/uvm/manifest.yaml"),
        "warnings": [],
    }
    data["rtl_modules"] = _order_rtl_modules(_scan_rtl(project), data["module_plan"], data["dataflow"])
    data["uvm_files"] = _scan_uvm(project)
    data["fpga"] = _fpga_summary(project, data["docparse_prototype"], data["loop3_prototype"])
    data["source_hashes"] = _source_hashes(project)
    data["warnings"].extend(data["fpga"]["warnings"])
    return data


def _render_document(project: Path, snapshot: dict[str, Any], previous: dict[str, Any] | None) -> list[str]:
    requirements = snapshot["requirements"]
    module_plan = snapshot["module_plan"]
    dataflow = snapshot["dataflow"]
    interfaces = snapshot["interfaces"]
    verification = snapshot["verification"]
    fpga = snapshot["fpga"]
    rtl_modules: list[RtlModule] = snapshot["rtl_modules"]
    uvm_files: list[UvmFile] = snapshot["uvm_files"]

    lines: list[str] = [
        "# 设计规则与架构设计文档",
        "",
        f"- project: {project.name}",
        f"- generated_at: {snapshot['generated_at']}",
        "- generator: hdlflow generate-design-doc",
        "- sync_manifest: `05_Output/reports/design/design_doc_manifest.json`",
        "",
        "本文档是给用户阅读的工程设计文档，不是 gate 日志汇总。文档按需求分析、RTL、UVM、FPGA 四个阶段展开；后续需求、RTL、UVM 或 FPGA plan 变化时，通过重新执行 `generate-design-doc` 在对应章节同步更新。",
        "",
        "## 同步状态",
        "",
        *_render_change_summary(snapshot, previous),
        "",
        "<!-- HDL-DOC:REQ START -->",
        "## 1. 需求分析与系统设计",
        "",
        "### 1.1 项目目标",
        "",
        _paragraph(requirements.get("purpose"), "本项目目标尚未在 SRS 中填写。"),
        "",
        "### 1.2 范围边界",
        "",
        *_scope_lines(requirements.get("scope")),
        "",
        "### 1.3 功能需求",
        "",
        *_requirement_rows(requirements.get("functional_requirements")),
        "",
        "### 1.4 非功能需求",
        "",
        *_requirement_rows(requirements.get("non_functional_requirements")),
        "",
        "### 1.5 顶层接口需求",
        "",
        *_interface_rows(requirements.get("interfaces")),
        "",
        "### 1.6 验收条件",
        "",
        *_list_lines(requirements.get("acceptance_summary"), empty="SRS 中暂无验收摘要。"),
        "",
        "### 1.7 代码架构划分",
        "",
        *_module_plan_lines(module_plan),
        "",
        "### 1.8 数据流和控制流",
        "",
        *_dataflow_lines(dataflow),
        "",
        "### 1.9 时钟、复位与边界条件",
        "",
        *_timing_lines(snapshot["timing"], requirements),
        "",
        "<!-- HDL-DOC:REQ END -->",
        "",
        "<!-- HDL-DOC:RTL START -->",
        "## 2. RTL 设计说明",
        "",
        f"本工程当前规划并生成 {len(rtl_modules)} 个 `.v` 文件。RTL 只使用 Verilog-2001；官方 UART 物理边界端口使用 `uart_rx` 和 `uart_tx`，不在官方边界追加 `_i`/`_o` 方向后缀。",
        "",
        "### 2.1 RTL 文件清单",
        "",
        "| 文件 | 模块 | 设计职责 |",
        "| --- | --- | --- |",
    ]
    lines.extend(f"| `{item.file}` | `{item.name}` | {_escape_table(item.description)} |" for item in rtl_modules)
    lines.extend(["", "### 2.2 RTL 设计规则", ""])
    lines.extend(_rtl_rule_lines(snapshot["rtl_rules"]))
    lines.extend(["", "### 2.3 RTL 模块逐项说明", ""])
    for index, item in enumerate(rtl_modules):
        if index:
            lines.extend(["", "---", ""])
        lines.extend(_rtl_module_section(item, interfaces))

    lines.extend(
        [
            "<!-- HDL-DOC:RTL END -->",
            "",
            "<!-- HDL-DOC:UVM START -->",
            "## 3. UVM 验证说明",
            "",
            "UVM 部分用于证明 UART loopback 的事务级行为。它不以 compile-only 作为关闭标准，必须保留 transaction、monitor、scoreboard、coverage 和 assertion/检查路径。",
            "",
            "### 3.1 UVM 总体结构",
            "",
            *_uvm_manifest_lines(snapshot["uvm_manifest"]),
            "",
            "### 3.2 UVM 文件清单",
            "",
            *_uvm_table_lines(uvm_files),
        ]
    )
    lines.extend(["", "### 3.3 事务、序列、检查和覆盖", ""])
    lines.extend(_verification_lines(verification, snapshot["assertions"], snapshot["coverage"]))

    lines.extend(
        [
            "<!-- HDL-DOC:UVM END -->",
            "",
            "<!-- HDL-DOC:FPGA START -->",
            "## 4. FPGA/原型架构说明",
            "",
            "FPGA 原型验证部分按 PL 和 PS_PL 两套模板组织。两种模式共用板卡、时钟、复位、UART、LED 等资源描述；差异在于 PL 模式直接把 RTL top 作为 FPGA 顶层，PS_PL 模式需要把 RTL 包装成 PL IP 或 wrapper 接入 Zynq PS block design。",
            "",
            "### 4.1 模式、板子型号与参数",
            "",
            *_fpga_mode_lines(fpga),
            "",
            "### 4.2 资源使用、引脚编号与连接关系",
            "",
            *_fpga_resource_lines(fpga),
            "",
            "### 4.3 原型验证预期表现",
            "",
            *_fpga_expected_lines(fpga),
            "",
            "### 4.4 Loop3 风险和进入条件",
            "",
            *_fpga_risk_lines(fpga),
            "",
            "<!-- HDL-DOC:FPGA END -->",
            "",
            "## 后续变更同步规则",
            "",
            "- 需求变更：更新 `00_SPEC/requirements` 或 `01_DocParse/req_decompose` 后，重新执行 `generate-design-doc`，变更会进入第 1 章。",
            "- RTL 新增或修改：扫描 `05_Output/rtl/*.v`，新增 `.v` 文件会在第 2 章新增模块小节，端口变化会刷新端口表。",
            "- UVM 新增或修改：扫描 `05_Output/uvm/**/*.sv` 和 `*.svh`，新增 transaction、agent、env、sequence、test 会在第 3 章同步。",
            "- FPGA 模式或连接变更：更新 `01_DocParse/prototype` 或 `04_Loop3_FPGA_Prototype/board_tests/prototype_plan.yaml` 后，第 4 章会同步 pure PL / PS_PL 架构和冲突风险。",
            "- Gate 同步：DocParse、Loop1、Loop2、Loop3 会检查文档 manifest 是否与源文件签名一致；不一致时需要重新生成文档。",
            "",
        ]
    )
    return lines


def _render_change_summary(snapshot: dict[str, Any], previous: dict[str, Any] | None) -> list[str]:
    current_rtl = {item.name: item.file for item in snapshot["rtl_modules"]}
    current_uvm = sorted(item.file for item in snapshot["uvm_files"])
    current_fpga = snapshot["fpga"]["mode_summary"]
    if not previous:
        return ["- 状态：首次生成设计文档。", f"- RTL 模块数：{len(current_rtl)}", f"- UVM 文件数：{len(current_uvm)}", f"- FPGA 模式摘要：{current_fpga}"]

    lines = []
    old_rtl = previous.get("rtl_modules", {})
    old_uvm = sorted(previous.get("uvm_files", []))
    old_fpga = previous.get("fpga_mode_summary")
    added_rtl = sorted(set(current_rtl) - set(old_rtl))
    removed_rtl = sorted(set(old_rtl) - set(current_rtl))
    added_uvm = sorted(set(current_uvm) - set(old_uvm))
    removed_uvm = sorted(set(old_uvm) - set(current_uvm))
    if not any([added_rtl, removed_rtl, added_uvm, removed_uvm, old_fpga != current_fpga]):
        return ["- 状态：源文件签名已刷新，模块/文件清单无结构性变化。"]
    if added_rtl:
        lines.append("- 新增 RTL 模块：" + ", ".join(f"`{item}`" for item in added_rtl))
    if removed_rtl:
        lines.append("- 移除 RTL 模块：" + ", ".join(f"`{item}`" for item in removed_rtl))
    if added_uvm:
        lines.append("- 新增 UVM 文件：" + ", ".join(f"`{item}`" for item in added_uvm))
    if removed_uvm:
        lines.append("- 移除 UVM 文件：" + ", ".join(f"`{item}`" for item in removed_uvm))
    if old_fpga != current_fpga:
        lines.append(f"- FPGA 模式摘要变化：`{old_fpga}` -> `{current_fpga}`")
    return lines


def _scope_lines(scope: Any) -> list[str]:
    if not isinstance(scope, dict):
        return ["- 范围尚未结构化填写。"]
    lines = ["- in_scope:"]
    lines.extend("  - " + str(item) for item in _as_list(scope.get("in_scope")) or ["未填写"])
    lines.append("- out_of_scope:")
    lines.extend("  - " + str(item) for item in _as_list(scope.get("out_of_scope")) or ["未填写"])
    return lines


def _requirement_rows(items: Any) -> list[str]:
    rows = ["| ID | 需求说明 |", "| --- | --- |"]
    for item in _as_list(items):
        if isinstance(item, dict):
            rows.append(f"| `{item.get('id', '-')}` | {_escape_table(item.get('text', '-'))} |")
        else:
            rows.append(f"| - | {_escape_table(item)} |")
    if len(rows) == 2:
        rows.append("| - | 暂无条目 |")
    return rows


def _interface_rows(items: Any) -> list[str]:
    rows = ["| 接口 | 方向 | 协议/说明 |", "| --- | --- | --- |"]
    for item in _as_list(items):
        if isinstance(item, dict):
            rows.append(f"| `{item.get('name', '-')}` | {item.get('direction', '-')} | {_escape_table(item.get('protocol', item.get('description', '-')))} |")
        else:
            rows.append(f"| `{item}` | - | - |")
    if len(rows) == 2:
        rows.append("| - | - | 暂无条目 |")
    return rows


def _module_plan_lines(module_plan: dict[str, Any]) -> list[str]:
    lines = []
    top = module_plan.get("top_level") if isinstance(module_plan.get("top_level"), dict) else {}
    if top:
        lines.append(f"- 顶层模块：`{top.get('name', '-')}`")
        lines.append(f"- 顶层策略：{top.get('wrapper_policy', '-')}")
    modules = _as_list(module_plan.get("modules"))
    if modules:
        lines.extend(["", "| 模块 | 职责 |", "| --- | --- |"])
        for item in modules:
            if isinstance(item, dict):
                lines.append(f"| `{item.get('name', '-')}` | {_escape_table(item.get('role', '-'))} |")
    for dependency in _as_list(module_plan.get("dependencies")):
        lines.append(f"- 依赖关系：{dependency}")
    return lines or ["- 架构划分尚未填写。"]


def _dataflow_lines(dataflow: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for flow in _as_list(dataflow.get("flows")):
        if isinstance(flow, dict):
            lines.append(f"- `{flow.get('id', 'FLOW')}`：{flow.get('path', '-')}")
        else:
            lines.append(f"- {flow}")
    if dataflow.get("datapaths"):
        lines.append("")
        lines.append("数据通路：")
        lines.extend("- " + str(item) for item in _as_list(dataflow.get("datapaths")))
    if dataflow.get("control_paths"):
        lines.append("")
        lines.append("控制通路：")
        lines.extend("- " + str(item) for item in _as_list(dataflow.get("control_paths")))
    if dataflow.get("backpressure"):
        lines.append("")
        lines.append("背压/溢出：")
        lines.extend("- " + str(item) for item in _as_list(dataflow.get("backpressure")))
    return lines or ["- 数据流尚未填写。"]


def _timing_lines(timing: dict[str, Any], requirements: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for item in _as_list(timing.get("clock_domains")):
        lines.append(f"- 时钟域：{item}")
    for item in _as_list(timing.get("resets")):
        lines.append(f"- 复位：{item}")
    for item in _as_list(timing.get("cdc_requirements")):
        lines.append(f"- CDC：{item}")
    for item in _as_list(requirements.get("boundary_conditions")):
        lines.append(f"- 边界条件：{item}")
    return lines or ["- 时钟、复位和边界条件尚未填写。"]


def _rtl_rule_lines(rules: dict[str, Any]) -> list[str]:
    lines = [
        f"- RTL 语言：{rules.get('rtl_language', '未配置')}",
        f"- RTL 根目录：`{rules.get('rtl_root', '05_Output/rtl')}`",
        f"- Directed TB 语言：{rules.get('directed_tb_language', '未配置')}",
        f"- UVM 语言：{rules.get('uvm_language', '未配置')}",
        "- 硬规则：",
    ]
    lines.extend("  - " + str(item) for item in _as_list(rules.get("hard_rules")) or ["未配置"])
    return lines


def _rtl_module_section(item: RtlModule, interfaces: dict[str, Any]) -> list[str]:
    lines = [
        f"<!-- HDL-DOC:RTL:{item.name} START -->",
        f"#### `{item.file}` / `{item.name}`",
        "",
        f"- 设计职责：{item.description or '该模块暂无 Description 头注释。'}",
        "- Scope:",
    ]
    lines.extend("  - " + text for text in item.scope or ["暂无 Scope 头注释。"])
    if item.parameters:
        lines.append("- 参数：" + ", ".join(f"`{param}`" for param in item.parameters))
    if item.instances:
        lines.append("- 子模块例化：" + ", ".join(f"`{inst}`" for inst in item.instances))
    lines.extend(["", "| 端口 | 方向 | 位宽 | 设计说明 |", "| --- | --- | --- | --- |"])
    for port in item.ports:
        lines.append(f"| `{port.name}` | {port.direction} | `{port.width}` | {_escape_table(_port_description(port, interfaces))} |")
    lines.extend(
        [
            "",
            "设计说明：",
            f"- 该模块的端口和职责来自 `{item.file}` 的实际代码扫描；端口变更后重新生成文档会刷新本节端口表。",
            "- 需求追踪：以 `01_DocParse/trace_matrix/req_to_rtl.yaml` 为准。",
            f"<!-- HDL-DOC:RTL:{item.name} END -->",
            "",
        ]
    )
    return lines


def _uvm_manifest_lines(manifest: dict[str, Any]) -> list[str]:
    lines = []
    if manifest.get("template_family"):
        lines.append(f"- 框架：{manifest.get('template_family')}")
    layout = manifest.get("layout")
    if isinstance(layout, dict):
        for name, desc in layout.items():
            lines.append(f"- `{name}`：{desc}")
    closure = manifest.get("closure_policy")
    if isinstance(closure, dict):
        lines.append("- 关闭策略：")
        for name, value in closure.items():
            lines.append(f"  - `{name}`: {value}")
    return lines or ["- UVM manifest 尚未填写。"]


def _verification_lines(verification: dict[str, Any], assertions: dict[str, Any], coverage: dict[str, Any]) -> list[str]:
    lines = ["模块级验证："]
    lines.extend("- " + str(item) for item in _as_list(verification.get("module_level")) or ["未填写"])
    lines.append("")
    lines.append("系统级验证：")
    lines.extend("- " + str(item) for item in _as_list(verification.get("system_level")) or ["未填写"])
    lines.append("")
    lines.append("Scoreboard / Reference Model：")
    lines.extend("- " + str(item) for item in _as_list(verification.get("scoreboards")) or ["未填写"])
    lines.extend("- " + str(item) for item in _as_list(verification.get("reference_models")) or [])
    lines.append("")
    lines.append("Negative / 边界测试：")
    lines.extend("- " + str(item) for item in _as_list(verification.get("negative_tests")) or ["未填写"])
    lines.append("")
    lines.append("Assertion 计划：")
    lines.extend("- " + str(item) for item in _as_list(assertions.get("assertions")) or ["未填写"])
    lines.append("")
    lines.append("Coverage 计划：")
    lines.extend("- " + str(item) for item in _as_list(coverage.get("functional_coverage")) or ["未填写"])
    return lines


def _uvm_table_lines(files: list[UvmFile]) -> list[str]:
    if not files:
        return ["| 文件 | 类别 | 主要 class/package | 作用 |", "| --- | --- | --- | --- |", "| - | - | - | UVM 文件尚未生成 |"]

    lines = ["| 文件 | 类别 | 主要 class/package | 作用 |", "| --- | --- | --- | --- |"]
    for item in files:
        classes = ", ".join(f"`{name}`" for name in item.classes) if item.classes else "-"
        lines.append(f"| `{item.file}` | {item.category} | {_escape_table(classes)} | {_escape_table(item.purpose)} |")
    return lines


def _fpga_mode_lines(fpga: dict[str, Any]) -> list[str]:
    return [
        f"- DocParse 原型模式：`{fpga.get('docparse_mode')}`",
        f"- Loop3 board_tests 原型模式：`{fpga.get('loop3_mode')}`",
        f"- 当前采用模板：{_active_template_name(fpga)}",
        f"- 板子型号：`{fpga.get('board')}`",
        f"- FPGA part：`{fpga.get('part')}`",
        f"- RTL top / IP：`{fpga.get('rtl_top_module')}`",
        f"- Vivado 版本：`{fpga.get('tool_version')}`",
        f"- 串口参数：`{fpga.get('serial_port')}` / `{fpga.get('baud_rate')}` baud",
        f"- 时钟参数：`{', '.join(fpga.get('clock_ports', [])) or '-'}`",
    ]


def _fpga_resource_lines(fpga: dict[str, Any]) -> list[str]:
    lines = [
        "| 模板 | RTL/BD 端口 | 板级资源 | 引脚编号 | 方向/类型 | 连接关系 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in fpga.get("resource_rows", []):
        lines.append(
            f"| PL 模板 | `{row.get('port', '-')}` | `{row.get('resource', '-')}` | `{row.get('pin', '-')}` | "
            f"{row.get('kind', '-')} | {row.get('connection', '-')} |"
        )
    if not fpga.get("resource_rows"):
        lines.append("| PL 模板 | - | - | - | - | 当前未生成引脚资源表 |")
    lines.extend(
        [
            "| PS_PL 模板 | `S_AXI` / `FCLK` / `peripheral_aresetn` | PS7 processing_system7 + AXI interconnect + reset controller | PS/PL 内部连接 | AXI/clock/reset | RTL 作为 PL IP 或 wrapper 接入 BD，PS 通过 AXI-Lite 访问控制/状态 |",
            "| PS_PL 模板 | `uart_rx` / `uart_tx` / `pl_led0` | 复用 PL 外部管脚资源 | 同 PL 模板 | external IO | PL IP 的外部 UART/LED 端口经 BD wrapper 导出到 XDC |",
            "",
            "资源估计：",
        ]
    )
    lines.extend("- " + str(item) for item in fpga.get("pure_pl_resources", []) or ["当前未填写资源估计"])
    if fpga.get("axi_regions"):
        lines.append("")
        lines.append("PS_PL AXI 区域：")
        lines.extend("- " + str(item) for item in fpga.get("axi_regions", []))
    return lines


def _fpga_expected_lines(fpga: dict[str, Any]) -> list[str]:
    active = _prototype_mode_key(str(fpga.get("loop3_mode") or ""))
    lines = [
        "| 模板 | 预期表现 | 验证证据 |",
        "| --- | --- | --- |",
    ]
    if active == "ps_pl":
        lines.extend(
            [
                "| PS_PL 模板 | PS7 block design 正常生成，FCLK/reset/AXI-Lite 连通，PL IP 可由 PS 访问或控制 | BD validate、address map、Vitis/XSCT/串口/ILA 证据 |",
                "| PS_PL 模板 | 若 UART/LED 仍走 PL 外部管脚，其行为与 PL 模板一致；若走 PS 外设，则需补 PS MIO/EMIO 预期 | BD wrapper、XDC、Vitis runtime log |",
            ]
        )
    else:
        for item in fpga.get("expected_board_checks", []):
            expected, evidence = _format_expected_board_check(item)
            lines.append(f"| PL 模板 | {_escape_table(expected)} | {_escape_table(evidence)} |")
        if not fpga.get("expected_board_checks"):
            lines.append("| PL 模板 | 当前未填写预期表现 | - |")
    return lines


def _format_expected_board_check(item: Any) -> tuple[str, str]:
    if isinstance(item, dict):
        expected = str(item.get("expected") or item.get("name") or item)
        check_type = str(item.get("type") or "").strip()
        blocking = item.get("blocking")
        if check_type == "human_observation" and blocking is False:
            return expected, "人工观察记录，原型阶段 non-blocking"
        if check_type == "automated_serial":
            return expected, "Vivado Tcl、bitstream、COM3 串口验证报告"
        return expected, "Vivado Tcl、bitstream、板级观察或串口验证报告"
    return str(item), "Vivado Tcl、bitstream、板级观察或串口验证报告"


def _fpga_risk_lines(fpga: dict[str, Any]) -> list[str]:
    risks = list(fpga.get("warnings", []))
    risks.extend(fpga.get("risk_items", []))
    if not risks:
        return ["- 当前未发现 FPGA 原型架构阻塞项。"]
    return ["- " + str(item) for item in risks]


def _template_state(fpga: dict[str, Any], mode: str) -> str:
    return "当前采用" if _prototype_mode_key(str(fpga.get("loop3_mode") or "")) == mode else "模板预留"


def _active_template_name(fpga: dict[str, Any]) -> str:
    return "PS_PL 模板" if _prototype_mode_key(str(fpga.get("loop3_mode") or "")) == "ps_pl" else "PL 模板"


def _fpga_resource_rows(project: Path, loop3: dict[str, Any]) -> list[dict[str, str]]:
    assignments = loop3.get("pl_port_assignments")
    if not isinstance(assignments, dict):
        return []
    xdc_ports = _parse_xdc_ports(project / "05_Output" / "fpga" / "vivado" / "constraints" / "generated_board.xdc")
    connection_notes = loop3.get("pure_pl_connections") if isinstance(loop3.get("pure_pl_connections"), dict) else {}
    rows: list[dict[str, str]] = []
    for port, resource in assignments.items():
        xdc = xdc_ports.get(str(port), {})
        rows.append(
            {
                "port": str(port),
                "resource": str(resource),
                "pin": str(xdc.get("pin") or _pin_from_note(connection_notes.get(port)) or "-"),
                "kind": str(xdc.get("kind") or _resource_kind(str(resource))),
                "connection": str(connection_notes.get(port) or f"{port} connects to {resource}"),
            }
        )
    return rows


def _parse_xdc_ports(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    ports: dict[str, dict[str, str]] = {}
    current_kind = ""
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        comment = re.match(r"##\s+(\w+)\s+<=\s+(.+?)\s+\((.*?)\)", raw)
        if comment:
            port = comment.group(1)
            tags = comment.group(3)
            current_kind = tags.split(",")[-1].strip() if tags else ""
            ports.setdefault(port, {})["resource"] = comment.group(2).strip()
            ports[port]["kind"] = current_kind
            continue
        pin = re.match(r"set_property\s+PACKAGE_PIN\s+(\S+)\s+\[get_ports\s+(\w+)\]", raw)
        if pin:
            ports.setdefault(pin.group(2), {})["pin"] = pin.group(1)
            if current_kind:
                ports[pin.group(2)]["kind"] = current_kind
    return ports


def _pin_from_note(value: Any) -> str:
    match = re.search(r"\bon\s+([A-Z]+\d+)\b", str(value or ""))
    return match.group(1) if match else ""


def _resource_kind(resource: str) -> str:
    lower = resource.lower()
    if "clk" in lower or "clock" in lower:
        return "clock"
    if "rst" in lower or "reset" in lower:
        return "reset"
    if "uart" in lower:
        return "uart"
    if "led" in lower:
        return "led"
    return "external IO"


def _scan_rtl(project: Path) -> list[RtlModule]:
    rtl_dir = project / "05_Output" / "rtl"
    if not rtl_dir.is_dir():
        return []
    modules: list[RtlModule] = []
    for path in sorted(rtl_dir.glob("*.v")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        header = _parse_header(text)
        match = re.search(r"\bmodule\s+(\w+)\s*(?:#\s*\((.*?)\)\s*)?\((.*?)\)\s*;", text, flags=re.S)
        if match:
            name = match.group(1)
            params = _parse_params(match.group(2) or "")
            ports = _parse_ports(match.group(3))
        else:
            name = path.stem
            params = []
            ports = []
        modules.append(
            RtlModule(
                file=_rel(project, path),
                name=name,
                description=header.get("description", ""),
                scope=header.get("scope", []),
                parameters=params,
                ports=ports,
                instances=_parse_instances(text, name),
            )
        )
    return modules


def _order_rtl_modules(modules: list[RtlModule], module_plan: dict[str, Any], dataflow: dict[str, Any]) -> list[RtlModule]:
    by_name = {item.name: item for item in modules}
    ordered_names: list[str] = []

    def add(name: Any) -> None:
        text = str(name or "")
        if text in by_name and text not in ordered_names:
            ordered_names.append(text)

    top = module_plan.get("top_level") if isinstance(module_plan.get("top_level"), dict) else {}
    add(top.get("name"))

    flow_text = " ".join(
        str(item.get("path", item)) if isinstance(item, dict) else str(item)
        for item in _as_list(dataflow.get("flows"))
    )
    flow_candidates = []
    for name in by_name:
        index = flow_text.find(name)
        if index >= 0:
            flow_candidates.append((index, name))
    for _, name in sorted(flow_candidates):
        add(name)

    for item in _as_list(module_plan.get("modules")):
        if isinstance(item, dict):
            add(item.get("name"))

    for name in sorted(by_name):
        add(name)

    return [by_name[name] for name in ordered_names]


def _scan_uvm(project: Path) -> list[UvmFile]:
    uvm_dir = project / "05_Output" / "uvm"
    if not uvm_dir.is_dir():
        return []
    files: list[UvmFile] = []
    for path in sorted([*uvm_dir.rglob("*.sv"), *uvm_dir.rglob("*.svh")]):
        text = path.read_text(encoding="utf-8", errors="ignore")
        classes = re.findall(r"\bclass\s+(\w+)(?:\s+extends\s+([^;]+))?;", text)
        class_names = [item[0] + (f" extends {item[1].strip()}" if item[1].strip() else "") for item in classes]
        rel = _rel(project, path)
        files.append(UvmFile(file=rel, category=_uvm_category(rel), classes=class_names, purpose=_uvm_purpose(rel)))
    return files


def _fpga_summary(project: Path, docparse: dict[str, Any], loop3: dict[str, Any]) -> dict[str, Any]:
    docparse_mode = str(docparse.get("prototype_mode") or "unknown")
    loop3_mode = str(loop3.get("mode") or "unknown")
    board = loop3.get("board") or docparse.get("board") or "unknown"
    warnings: list[str] = []
    if (
        docparse_mode != "unknown"
        and loop3_mode != "unknown"
        and _prototype_mode_key(docparse_mode) != _prototype_mode_key(loop3_mode)
    ):
        warnings.append(f"原型模式冲突：DocParse={docparse_mode}，Loop3 board_tests={loop3_mode}。进入 Loop3 前必须统一。")
    for key in ["rtl_top_module", "axi_regions"]:
        value = loop3.get(key)
        if _contains_placeholder(value):
            warnings.append(f"Loop3 prototype_plan 中 `{key}` 仍包含 change_me/todo 占位。")
    old_uart_names = False
    for name in _dict_keys(loop3.get("pl_port_assignments")) + _dict_keys(loop3.get("bd_external_ports")):
        if name in {"uart_rx_i", "uart_tx_o"}:
            old_uart_names = True
    if old_uart_names:
        warnings.append("Loop3 prototype_plan 仍使用旧 UART 边界命名 `uart_rx_i/uart_tx_o`，应统一为 `uart_rx/uart_tx`。")
    return {
        "docparse_mode": docparse_mode,
        "loop3_mode": loop3_mode,
        "board": board,
        "part": loop3.get("part") or "unknown",
        "tool_version": loop3.get("tool_version") or "unknown",
        "rtl_top_module": loop3.get("rtl_top_module") or "unknown",
        "serial_port": loop3.get("serial_port") or "unknown",
        "baud_rate": loop3.get("baud_rate") or "unknown",
        "clock_ports": _as_list(loop3.get("clock_ports")),
        "expected_board_checks": _as_list(loop3.get("expected_board_checks")),
        "mode_summary": f"DocParse={docparse_mode}; Loop3={loop3_mode}; board={board}",
        "pure_pl_resources": _as_list(docparse.get("resource_estimate")),
        "risk_items": _as_list(docparse.get("risk_items")),
        "axi_regions": _format_mapping(loop3.get("axi_regions")),
        "ps_mio": _format_mapping(loop3.get("ps_mio_assignments")),
        "pl_ports": _format_mapping(loop3.get("pl_port_assignments")),
        "bd_ports": _format_mapping(loop3.get("bd_external_ports")),
        "resource_rows": _fpga_resource_rows(project, loop3),
        "warnings": warnings,
    }


def _build_manifest(project: Path, snapshot: dict[str, Any], report_path: Path) -> dict[str, Any]:
    rtl_modules = {item.name: item.file for item in snapshot["rtl_modules"]}
    uvm_files = [item.file for item in snapshot["uvm_files"]]
    source_hashes = snapshot["source_hashes"]
    return {
        "schema_version": 1,
        "project": project.name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "report": _rel(project, report_path),
        "sections": ["requirements", "rtl", "uvm", "fpga"],
        "source_signature": _source_signature(source_hashes),
        "source_hashes": source_hashes,
        "rtl_modules": rtl_modules,
        "uvm_files": uvm_files,
        "fpga_mode_summary": snapshot["fpga"]["mode_summary"],
        "warnings": snapshot["warnings"],
    }


def _source_hashes(project: Path) -> list[dict[str, str]]:
    roots = [
        "00_SPEC/requirements",
        "01_DocParse/architecture",
        "01_DocParse/verification",
        "01_DocParse/prototype",
        "01_DocParse/trace_matrix",
        "04_Loop3_FPGA_Prototype/board_tests",
        "05_Output/rtl",
        "05_Output/uvm",
    ]
    suffixes = {".yaml", ".yml", ".json", ".md", ".v", ".sv", ".svh"}
    paths: list[Path] = []
    for rel in roots:
        root = project / rel
        if root.is_file() and root.suffix.lower() in suffixes:
            paths.append(root)
        elif root.is_dir():
            paths.extend(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in suffixes and "_runtime" not in path.parts)
    entries = []
    for path in sorted(set(paths)):
        data = path.read_bytes()
        entries.append({"path": _rel(project, path), "sha256": hashlib.sha256(data).hexdigest()})
    return entries


def _source_signature(entries: list[dict[str, str]]) -> str:
    payload = json.dumps(entries, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_data(project: Path, rel: str) -> dict[str, Any]:
    path = project / rel
    if not path.exists():
        return {}
    try:
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = load_yaml(path)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _load_manifest(project: Path) -> dict[str, Any] | None:
    path = project / MANIFEST_REL
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _parse_header(text: str) -> dict[str, Any]:
    header: dict[str, Any] = {"scope": []}
    in_scope = False
    for line in text.splitlines()[:80]:
        stripped = line.strip()
        if stripped.startswith("// Description"):
            header["description"] = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
            in_scope = False
        elif stripped.startswith("// Scope:"):
            in_scope = True
        elif in_scope and stripped.startswith("//   -"):
            header["scope"].append(stripped.split("-", 1)[1].strip())
        elif stripped.startswith("// Spec Trace:") or stripped.startswith("// Notes:") or stripped.startswith("module "):
            in_scope = False
    return header


def _parse_params(text: str) -> list[str]:
    params = []
    for match in re.finditer(r"\bparameter\s+(\w+)", text):
        params.append(match.group(1))
    return params


def _parse_ports(text: str) -> list[RtlPort]:
    ports: list[RtlPort] = []
    for raw in text.splitlines():
        line = raw.split("//", 1)[0].strip().rstrip(",")
        if not line:
            continue
        match = re.match(r"(input|output|inout)\s+(?:wire|reg|logic)?\s*(\[[^\]]+\])?\s*(\w+)", line)
        if not match:
            continue
        direction, width, name = match.groups()
        ports.append(RtlPort(name=name, direction=direction, width=width or "1", description=""))
    return ports


def _parse_instances(text: str, self_module: str) -> list[str]:
    instances: list[str] = []
    for match in re.finditer(r"^\s*(\w+)\s+(u_\w+)\s*\(", text, flags=re.M):
        mod, inst = match.groups()
        if mod != self_module:
            instances.append(f"{mod}.{inst}")
    for match in re.finditer(r"^\s*\)\s+(u_\w+)\s*\(", text, flags=re.M):
        instances.append(match.group(1))
    return sorted(set(instances))


def _port_description(port: RtlPort, interfaces: dict[str, Any]) -> str:
    for item in _as_list(interfaces.get("ports")):
        if isinstance(item, dict) and item.get("name") == port.name:
            desc = item.get("description") or item.get("protocol") or ""
            width = item.get("width")
            if desc and width:
                return f"{desc} width={width}"
            if desc:
                return str(desc)
            break
    defaults = {
        "clk": "主工作时钟",
        "rst_n": "低有效复位",
        "uart_rx": "官方 UART RX 物理输入端口",
        "uart_tx": "官方 UART TX 物理输出端口",
        "busy_o": "模块忙状态输出",
        "rx_valid_o": "RX 字节有效脉冲",
        "rx_data_o": "RX 字节数据",
        "tx_busy_o": "TX 发送忙状态",
        "overflow_o": "pending buffer 溢出脉冲",
        "framing_error_o": "UART stop bit 错误提示",
    }
    return defaults.get(port.name, f"{port.name} signal")


def _uvm_category(rel: str) -> str:
    parts = Path(rel).parts
    if "agents" in parts:
        return "agent"
    if "env" in parts:
        return "env"
    if "seq_lib" in parts:
        return "sequence"
    if "tests" in parts:
        return "test"
    if "cov" in parts:
        return "coverage"
    if "tb" in parts:
        return "tb"
    if "assertions" in parts:
        return "assertion"
    if "cfg" in parts:
        return "config"
    return "uvm"


def _uvm_purpose(rel: str) -> str:
    name = Path(rel).name
    if "item" in name:
        return "定义 UART transaction item 和 payload/scenario 字段。"
    if "driver" in name:
        return "把 transaction 转换为 DUT UART RX 激励。"
    if "monitor" in name:
        return "观察 DUT UART TX/RX 行为并发布 transaction。"
    if "scoreboard" in name:
        return "按顺序比较期望字节和观测字节。"
    if "coverage" in name:
        return "采样合法场景功能覆盖。"
    if "sequence" in name:
        return "组织基础、边界和压力场景。"
    if "test" in name or name == "tests.svh":
        return "定义 UVM testcase 和回归入口。"
    if "sva" in name:
        return "提供非侵入式 assertion/bind 检查。"
    return "UVM 环境支撑文件。"


def _format_mapping(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    rows = []
    for key, item in value.items():
        if isinstance(item, dict):
            detail = ", ".join(f"{sub_key}={sub_value}" for sub_key, sub_value in item.items())
            rows.append(f"{key}: {detail}")
        else:
            rows.append(f"{key}: {item}")
    return rows


def _dict_keys(value: Any) -> list[str]:
    return [str(key) for key in value] if isinstance(value, dict) else []


def _prototype_mode_key(value: str) -> str:
    text = str(value or "").lower()
    if text in {"pl", "pure_pl", "pure-pl"}:
        return "pl"
    return text


def _contains_placeholder(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_placeholder(key) or _contains_placeholder(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_placeholder(item) for item in value)
    text = str(value).lower()
    return any(marker in text for marker in ["change_me", "todo", "tbd", "placeholder"])


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, "", {}):
        return []
    return [value]


def _list_lines(value: Any, *, empty: str) -> list[str]:
    items = _as_list(value)
    if not items:
        return [f"- {empty}"]
    return [f"- {item}" for item in items]


def _paragraph(value: Any, empty: str) -> str:
    return str(value) if value not in (None, "") else empty


def _escape_table(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _rel(project: Path, path: Path) -> str:
    return str(path.resolve().relative_to(project.resolve())).replace("\\", "/")
