"""User-readable design document generation for HDL workflow projects."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import load_project
from .layout import find_workspace_root
from .project import require_project_instance
from .requirements_frontend import ACCEPTANCE_REL, SPEC_INPUT_REL, SRS_REL
from .simple_yaml import load_yaml


REPORT_REL = "output/reports/design/design_rule_and_architecture.md"
MANIFEST_REL = "output/reports/design/design_doc_manifest.json"


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


def generate_design_document(project_path: Path, *, allow_draft: bool = False) -> DesignDocResult:
    """Generate the ordered user-facing design document and sync manifest."""

    project = require_project_instance(project_path)
    if not allow_draft:
        warnings, errors = _design_doc_preflight(project)
        if errors:
            return DesignDocResult(project / REPORT_REL, project / MANIFEST_REL, warnings, errors)

    snapshot = _collect_snapshot(project)
    previous = _load_manifest(project)
    lines = _render_document_v2(project, snapshot, previous)

    report_path = project / REPORT_REL
    manifest_path = project / MANIFEST_REL
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = _build_manifest(project, snapshot, report_path)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    warnings = list(snapshot["warnings"])
    errors: list[str] = []
    return DesignDocResult(report_path, manifest_path, warnings, errors)


def _design_doc_preflight(project: Path) -> tuple[list[str], list[str]]:
    """Run the formal gates that explain why the design document can be generated."""

    from .requirements_frontend import check_requirements_frontend
    from .review import check_review_findings

    warnings: list[str] = []
    errors: list[str] = []

    readiness = check_requirements_frontend(project, require_ready=True)
    warnings.extend(f"frontdoor: {warning}" for warning in readiness.warnings)
    if not readiness.ok:
        errors.extend(
            [
                "generate-design-doc blocked: requirements-frontdoor-check did not pass",
                f"frontdoor report: {_rel(project, readiness.report_path)}",
            ]
        )
        errors.extend(f"frontdoor: {error}" for error in readiness.errors)

    review = check_review_findings(project, level="develop")
    warnings.extend(f"review-check: {warning}" for warning in review.warnings)
    if not review.ok:
        errors.extend(
            [
                "generate-design-doc blocked: review-check did not pass",
                f"review report: {_rel(project, review.report_path)}",
            ]
        )
        errors.extend(f"review blocker: {blocker}" for blocker in review.blocking_findings)
        errors.extend(f"review-check: {error}" for error in review.errors)

    if errors:
        errors.extend(
            [
                "next action: fix the listed frontdoor/review issues",
                "next command: python -m hdlflow.cli requirements-frontdoor-check --project <project>",
                "next command: python -m hdlflow.cli review-check --project <project> --level develop",
                "next command: python -m hdlflow.cli generate-design-doc --project <project>",
            ]
        )

    return warnings, errors


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
        "requirements": _load_data(project, SRS_REL),
        "acceptance": _load_data(project, ACCEPTANCE_REL),
        "structured_interface": _load_data(project, "work/docparse/structured_spec/interface_spec.yaml"),
        "structured_registers": _load_data(project, "work/docparse/structured_spec/register_map.yaml"),
        "structured_test_intent": _load_data(project, "work/docparse/structured_spec/test_intent.yaml"),
        "structured_timing_rules": _load_data(project, "work/docparse/structured_spec/timing_rules.yaml"),
        "structured_interface_timing": _load_data(project, "work/docparse/structured_spec/interface_timing.yaml"),
        "module_plan": _load_data(project, "work/docparse/architecture/module_plan.yaml"),
        "interfaces": _load_data(project, "work/docparse/architecture/interface_contracts.yaml"),
        "dataflow": _load_data(project, "work/docparse/architecture/dataflow.yaml"),
        "timing": _load_data(project, "work/docparse/architecture/timing_model.yaml"),
        "rtl_rules": _load_data(project, "work/docparse/architecture/rtl_planning_rules.yaml"),
        "verification": _load_data(project, "work/docparse/verification/verification_plan.yaml"),
        "assertions": _load_data(project, "work/docparse/verification/assertion_plan.yaml"),
        "coverage": _load_data(project, "work/docparse/verification/coverage_plan.yaml"),
        "project_config": _load_project_config(project),
        "docparse_prototype": _load_data(project, "work/docparse/prototype/prototype_plan.yaml"),
        "loop3_prototype": _load_data(project, "work/loop3_fpga_proto/board_tests/prototype_plan.yaml"),
        "trace_req_to_arch": _load_data(project, "work/docparse/trace_matrix/req_to_arch.yaml"),
        "trace_req_to_rtl": _load_data(project, "work/docparse/trace_matrix/req_to_rtl.yaml"),
        "trace_req_to_test": _load_data(project, "work/docparse/trace_matrix/req_to_test.yaml"),
        "trace_req_to_proto": _load_data(project, "work/docparse/trace_matrix/req_to_proto.yaml"),
        "uvm_manifest": _load_data(project, "output/uvm/manifest.yaml"),
        "warnings": [],
    }
    data["rtl_modules"] = _order_rtl_modules(_scan_rtl(project), data["module_plan"], data["dataflow"])
    data["uvm_files"] = _scan_uvm(project)
    data["fpga"] = _fpga_summary(project, data["docparse_prototype"], data["loop3_prototype"])
    data["source_hashes"] = _source_hashes(project)
    data["warnings"].extend(data["fpga"]["warnings"])
    return data


def _render_document_v2(project: Path, snapshot: dict[str, Any], previous: dict[str, Any] | None) -> list[str]:
    requirements = snapshot["requirements"]
    acceptance = snapshot["acceptance"]
    structured_interface = snapshot["structured_interface"]
    structured_test_intent = snapshot["structured_test_intent"]
    module_plan = snapshot["module_plan"]
    dataflow = snapshot["dataflow"]
    interfaces = snapshot["interfaces"]
    verification = snapshot["verification"]
    fpga = snapshot["fpga"]
    project_config = snapshot["project_config"]
    rtl_modules: list[RtlModule] = snapshot["rtl_modules"]
    uvm_files: list[UvmFile] = snapshot["uvm_files"]

    lines: list[str] = [
        f"# {project.name} 数字核心设计文档",
        "",
        "## 第0章 文档概述",
        "",
        "### 0.1 项目基本信息",
        "",
        f"- project: {project.name}",
        f"- generated_at: {snapshot['generated_at']}",
        "- generator: `python -m hdlflow.cli generate-design-doc`",
        "- sync_manifest: `output/reports/design/design_doc_manifest.json`",
        f"- source_signature: `{_source_signature(snapshot['source_hashes'])[:16]}`",
        "",
        "本文件由平台生成器从机器可读 Spec、架构 YAML、验证计划、RTL/UVM 扫描结果和原型计划同步生成；不得手工补写设计结论。",
        "",
        "### 0.2 文档同步状态",
        "",
        *_doc_change_summary(snapshot, previous),
        "",
        "### 0.3 变更同步规则",
        "",
        "- 对话框中的需求变更必须先进入 `work/change/requests`，再由对应 Agent 更新自己权限内的机器可读文件。",
        "- 需求或边界变化回到 Spec Agent；模块划分、数据流、FSM 或接口变化回到 Arch Agent；RTL/TB/UVM/FPGA 变化只同步对应实现或验证章节。",
        "- `generate-design-doc` 只能在 requirements front door READY 后生成正文，并用 manifest 锁定源文件签名。",
        "- Review Agent 只记录缺陷、风险和整改意见；Arbtr Agent 只记录仲裁、冻结和版本锁定，不直接改正文设计内容。",
        "",
        "<!-- HDL-DOC:REQ START -->",
        "## 第1章 需求与边界定义 (Requirements & Scope)",
        "",
        "### 1.1 项目目标",
        "",
        _paragraph(_first_value(requirements, "purpose", "objective", "goal", "description"), "项目目标尚未在 SRS 中填写。"),
        "",
        "### 1.2 范围边界 (In/Out Scope)",
        "",
        *_doc_scope_lines(requirements.get("scope")),
        "",
        "### 1.3 功能需求",
        "",
        *_doc_requirement_rows(requirements.get("functional_requirements")),
        "",
        "### 1.4 非功能需求",
        "",
        *_doc_requirement_rows(requirements.get("non_functional_requirements")),
        "",
        "### 1.5 顶层接口规格",
        "",
        *_doc_interface_rows(requirements, structured_interface, interfaces),
        "",
        "### 1.6 验收条件 (Sign-off Criteria)",
        "",
        *_doc_acceptance_lines(acceptance, requirements),
        "",
        "### 1.7 规范输入文件清单",
        "",
        *_doc_structured_spec_input_lines(snapshot),
        "",
        "<!-- HDL-DOC:REQ END -->",
        "",
        "<!-- HDL-DOC:ARCH START -->",
        "## 第2章 系统与架构设计 (System Architecture)",
        "",
        "### 2.1 顶层架构与模块划分",
        "",
        *_doc_module_plan_lines(module_plan),
        "",
        "### 2.2 数据流与控制流分析",
        "",
        *_doc_dataflow_lines(dataflow),
        "",
        "### 2.3 时钟、复位与 CDC 设计",
        "",
        *_doc_timing_lines(
            snapshot["timing"],
            requirements,
            snapshot["structured_timing_rules"],
            snapshot["structured_interface_timing"],
        ),
        "",
        "### 2.4 边界条件说明",
        "",
        *_doc_boundary_lines(requirements, module_plan),
        "",
        "<!-- HDL-DOC:ARCH END -->",
        "",
        "<!-- HDL-DOC:RTL START -->",
        "## 第3章 RTL 实现说明 (RTL Implementation)",
        "",
        "### 3.1 RTL 文件清单与依赖",
        "",
        *_doc_rtl_file_table_lines(rtl_modules),
        "",
        "### 3.2 RTL 设计与编码规则",
        "",
        *_doc_rtl_rule_lines(snapshot["rtl_rules"]),
        "",
        "### 3.3 模块逐项说明",
        "",
    ]
    if rtl_modules:
        for index, item in enumerate(rtl_modules):
            if index:
                lines.extend(["", "---", ""])
            lines.extend(_doc_rtl_module_section(item, interfaces))
    else:
        lines.append("- RTL 文件尚未生成。")

    lines.extend(
        [
            "",
            "<!-- HDL-DOC:RTL END -->",
            "",
            "<!-- HDL-DOC:UVM START -->",
            "<!-- HDL-DOC:TEST START -->",
            "## 第4章 验证架构与测试计划 (Verification & Test Plan)",
            "",
            "### 4.1 验证策略与测试准则",
            "",
            *_doc_verification_strategy_lines(verification, project_config),
            "",
            "### 4.2 Directed TB 验证与计划 (Baseline Checks)",
            "",
            *_doc_directed_tb_plan_lines(verification),
            "",
            "### 4.2.1 Loop1 Waveform Secondary Check Plan",
            "",
            *_doc_waveform_plan_lines(verification, structured_test_intent),
            "",
            "### 4.3 UVM 验证架构与组件说明",
            "",
            *_doc_uvm_manifest_lines(snapshot["uvm_manifest"]),
            "",
            *_doc_uvm_table_lines(uvm_files),
            "",
            "### 4.4 UVM 覆盖率与断言计划 (Coverage & SVA)",
            "",
            *_doc_coverage_assertion_lines(snapshot["assertions"], snapshot["coverage"]),
            "",
            "### 4.5 UVM 用例计划矩阵 (Test Matrix)",
            "",
            *_doc_uvm_test_matrix_lines(verification, project_config),
            "",
            "### 4.6 日志格式规范",
            "",
            *_doc_log_format_lines(),
            "",
            "<!-- HDL-DOC:UVM END -->",
            "<!-- HDL-DOC:TEST END -->",
            "",
            "<!-- HDL-DOC:FPGA START -->",
            "## 第5章 FPGA 原型验证 (FPGA Prototyping)",
            "",
            "### 5.1 原型模式与硬件平台",
            "",
            *_doc_fpga_mode_lines(fpga),
            "",
            "### 5.2 资源使用与引脚映射",
            "",
            *_doc_fpga_resource_lines(fpga),
            "",
            "### 5.3 软硬件交互规划 (PS-PL)",
            "",
            *_doc_fpga_ps_pl_lines(fpga),
            "",
            "### 5.4 原型验证风险与进入条件",
            "",
            *_doc_fpga_risk_lines(fpga),
            "",
            "### 5.5 板级测试计划",
            "",
            *_doc_fpga_expected_lines(fpga),
            "",
            "<!-- HDL-DOC:FPGA END -->",
            "",
            "<!-- HDL-DOC:TRACE START -->",
            "## 附录A 需求追溯性矩阵",
            "",
            *_doc_traceability_lines(snapshot),
            "",
            "<!-- HDL-DOC:TRACE END -->",
        ]
    )
    return lines


def _doc_change_summary(snapshot: dict[str, Any], previous: dict[str, Any] | None) -> list[str]:
    current_rtl = {item.name: item.file for item in snapshot["rtl_modules"]}
    current_uvm = sorted(item.file for item in snapshot["uvm_files"])
    current_fpga = snapshot["fpga"]["mode_summary"]
    if not previous:
        return [
            "- 状态: 首次生成设计文档。",
            f"- RTL 模块数: {len(current_rtl)}",
            f"- UVM 文件数: {len(current_uvm)}",
            f"- FPGA 模式摘要: {current_fpga}",
        ]

    lines = []
    old_rtl = previous.get("rtl_modules", {})
    old_uvm = sorted(previous.get("uvm_files", []))
    old_fpga = previous.get("fpga_mode_summary")
    added_rtl = sorted(set(current_rtl) - set(old_rtl))
    removed_rtl = sorted(set(old_rtl) - set(current_rtl))
    added_uvm = sorted(set(current_uvm) - set(old_uvm))
    removed_uvm = sorted(set(old_uvm) - set(current_uvm))
    if not any([added_rtl, removed_rtl, added_uvm, removed_uvm, old_fpga != current_fpga]):
        return ["- 状态: 源文件签名已刷新，模块/文件清单无结构性变化。"]
    if added_rtl:
        lines.append("- 新增 RTL 模块: " + ", ".join(f"`{item}`" for item in added_rtl))
    if removed_rtl:
        lines.append("- 移除 RTL 模块: " + ", ".join(f"`{item}`" for item in removed_rtl))
    if added_uvm:
        lines.append("- 新增 UVM 文件: " + ", ".join(f"`{item}`" for item in added_uvm))
    if removed_uvm:
        lines.append("- 移除 UVM 文件: " + ", ".join(f"`{item}`" for item in removed_uvm))
    if old_fpga != current_fpga:
        lines.append(f"- FPGA 模式摘要变化: `{old_fpga}` -> `{current_fpga}`")
    return lines


def _doc_scope_lines(scope: Any) -> list[str]:
    if not isinstance(scope, dict):
        return ["- in_scope: 未填写", "- out_of_scope: 未填写"]
    lines = ["- in_scope:"]
    lines.extend("  - " + str(item) for item in _as_list(scope.get("in_scope")) or ["未填写"])
    lines.append("- out_of_scope:")
    lines.extend("  - " + str(item) for item in _as_list(scope.get("out_of_scope")) or ["未填写"])
    return lines


def _doc_requirement_rows(items: Any) -> list[str]:
    rows = ["| ID | 类型 | 需求内容 |", "| --- | --- | --- |"]
    for item in _as_list(items):
        if isinstance(item, dict):
            rows.append(
                f"| `{_doc_item_id(item)}` | {_escape_table(_string_or_dash(_first_value(item, 'type', 'category', 'level')))} | "
                f"{_escape_table(_doc_item_text(item))} |"
            )
        else:
            rows.append(f"| - | - | {_escape_table(item)} |")
    if len(rows) == 2:
        rows.append("| - | - | 暂无条目 |")
    return rows


def _doc_interface_rows(requirements: dict[str, Any], structured_interface: dict[str, Any], interfaces: dict[str, Any]) -> list[str]:
    rows = ["| 接口 | 方向/类型 | 协议/说明 | Signals/Ports |", "| --- | --- | --- | --- |"]
    items: list[Any] = []
    items.extend(_as_list(requirements.get("interfaces")))
    items.extend(_as_list(structured_interface.get("interfaces")))
    items.extend(_as_list(structured_interface.get("ports")))
    items.extend(_as_list(interfaces.get("ports")))
    seen: set[tuple[str, str]] = set()
    for item in items:
        if isinstance(item, dict):
            name = _string_or_dash(_first_value(item, "name", "id", "title", "module_name", "interface"))
            direction = _string_or_dash(_first_value(item, "direction", "type", "dir", "mode"))
            desc = _string_or_dash(_first_value(item, "protocol", "description", "text", "title", "purpose"))
            signals = _doc_compact_items(_first_value(item, "signals", "ports", "signal_list"), empty="-")
        else:
            name = str(item)
            direction = "-"
            desc = "-"
            signals = "-"
        key = (name, direction)
        if key in seen:
            continue
        seen.add(key)
        rows.append(f"| `{_escape_table(name)}` | {_escape_table(direction)} | {_escape_table(desc)} | {_escape_table(signals)} |")
    if len(rows) == 2:
        rows.append("| - | - | 暂无条目 | - |")
    return rows


def _doc_acceptance_lines(acceptance: dict[str, Any], requirements: dict[str, Any]) -> list[str]:
    rows = ["| ID | 验收条件 | 证据来源 |", "| --- | --- | --- |"]
    items = []
    for key in ["criteria", "acceptance_criteria", "signoff_criteria", "done_criteria"]:
        items.extend(_as_list(acceptance.get(key)))
    items.extend(_as_list(requirements.get("acceptance_summary")))
    for index, item in enumerate(items, 1):
        if isinstance(item, dict):
            rows.append(
                f"| `{_doc_item_id(item, default=f'AC-{index:03d}')}` | {_escape_table(_doc_item_text(item))} | "
                f"{_escape_table(_string_or_dash(_first_value(item, 'evidence', 'source', 'gate', 'verification')))} |"
            )
        else:
            rows.append(f"| `AC-{index:03d}` | {_escape_table(item)} | - |")
    if len(rows) == 2:
        rows.append("| - | 暂无条目 | - |")
    return rows


def _doc_structured_spec_input_lines(snapshot: dict[str, Any]) -> list[str]:
    rows = [
        (SRS_REL, snapshot.get("requirements", {}), ["functional_requirements", "non_functional_requirements", "interfaces"]),
        (ACCEPTANCE_REL, snapshot.get("acceptance", {}), ["criteria", "acceptance_criteria", "signoff_criteria"]),
        ("work/docparse/structured_spec/interface_spec.yaml", snapshot.get("structured_interface", {}), ["interfaces", "ports"]),
        ("work/docparse/structured_spec/register_map.yaml", snapshot.get("structured_registers", {}), ["registers", "opcodes", "commands"]),
        ("work/docparse/structured_spec/test_intent.yaml", snapshot.get("structured_test_intent", {}), ["functional_tests", "full_function_matrix", "corner_cases"]),
        ("work/docparse/structured_spec/timing_rules.yaml", snapshot.get("structured_timing_rules", {}), ["timing_constraints", "cdc_rules", "spi", "arinc429"]),
        ("work/docparse/structured_spec/interface_timing.yaml", snapshot.get("structured_interface_timing", {}), ["timing_tables", "valid_windows", "latency_bounds"]),
    ]
    lines = ["| 文件 | Status | 主要填充字段 |", "| --- | --- | --- |"]
    for name, data, keys in rows:
        if not isinstance(data, dict) or not data:
            lines.append(f"| `{name}` | missing | - |")
            continue
        status = str(data.get("status") or "UNSET")
        filled = [key for key in keys if _has_non_empty_value(data.get(key))]
        lines.append(f"| `{name}` | `{status}` | {_escape_table(', '.join(filled) if filled else '-')} |")
    return lines


def _doc_module_plan_lines(module_plan: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    top = module_plan.get("top_level") if isinstance(module_plan.get("top_level"), dict) else {}
    if top:
        lines.append(f"- 顶层模块: `{_string_or_dash(_first_value(top, 'name', 'title'))}`")
        lines.append(f"- 顶层策略: {_string_or_dash(_first_value(top, 'wrapper_policy', 'description', 'responsibility', 'role'))}")
    policy = module_plan.get("module_partition_policy")
    if isinstance(policy, dict):
        lines.append("- 模块划分策略:")
        for key, value in policy.items():
            lines.append(f"  - `{key}`: {value}")
    modules = _as_list(module_plan.get("modules"))
    if modules:
        lines.extend(["", "| 模块 | 职责 | 子模块/组成 | 依赖 |", "| --- | --- | --- | --- |"])
        for item in modules:
            if isinstance(item, dict):
                lines.append(
                    f"| `{_string_or_dash(_first_value(item, 'name', 'id', 'title'))}` | "
                    f"{_escape_table(_string_or_dash(_first_value(item, 'role', 'responsibility', 'description', 'title')))} | "
                    f"{_escape_table(_doc_compact_items(_first_value(item, 'children', 'submodules', 'composition'), empty='-'))} | "
                    f"{_escape_table(_doc_compact_items(_first_value(item, 'dependencies', 'depends_on'), empty='-'))} |"
                )
    for dependency in _as_list(module_plan.get("dependencies")):
        lines.append(f"- 全局依赖: {dependency}")
    return lines or ["- 架构划分尚未填写。"]


def _doc_dataflow_lines(dataflow: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    flows = _as_list(dataflow.get("flows"))
    if flows:
        lines.extend(["| Flow | 路径 | 说明 |", "| --- | --- | --- |"])
        for flow in flows:
            if isinstance(flow, dict):
                lines.append(
                    f"| `{_doc_item_id(flow, default='FLOW')}` | {_escape_table(_string_or_dash(_first_value(flow, 'path', 'route', 'from_to')))} | "
                    f"{_escape_table(_string_or_dash(_first_value(flow, 'description', 'text', 'title', 'purpose')))} |"
                )
            else:
                lines.append(f"| - | {_escape_table(flow)} | - |")
    for title, key in [
        ("数据通路", "datapaths"),
        ("控制通路", "control_paths"),
        ("背压/溢出", "backpressure"),
    ]:
        values = _as_list(dataflow.get(key))
        if values:
            lines.extend(["", f"{title}:"])
            lines.extend("- " + _doc_item_text(item) for item in values)
    return lines or ["- 数据流和控制流尚未填写。"]


def _doc_timing_lines(timing: dict[str, Any], requirements: dict[str, Any], timing_rules: dict[str, Any], interface_timing: dict[str, Any]) -> list[str]:
    rows = ["| 类别 | 内容 |", "| --- | --- |"]
    for item in _as_list(timing.get("clock_domains")) or _as_list(timing_rules.get("clock_domains")):
        rows.append(f"| clock | {_escape_table(_doc_item_text(item))} |")
    for item in _as_list(timing.get("resets")) or _as_list(timing_rules.get("resets")):
        rows.append(f"| reset | {_escape_table(_doc_item_text(item))} |")
    for item in _as_list(timing.get("cdc_requirements")) or _as_list(timing_rules.get("cdc_rules")):
        rows.append(f"| CDC | {_escape_table(_doc_item_text(item))} |")
    for item in _as_list(interface_timing.get("timing_tables")):
        rows.append(f"| interface_timing | {_escape_table(_doc_item_text(item))} |")
    for item in _as_list(requirements.get("metric_parameters")):
        rows.append(f"| metric | {_escape_table(_doc_item_text(item))} |")
    if len(rows) == 2:
        rows.append("| - | 时钟、复位和 CDC 尚未填写 |")
    return rows


def _doc_boundary_lines(requirements: dict[str, Any], module_plan: dict[str, Any]) -> list[str]:
    lines = []
    for title, value in [
        ("边界条件", requirements.get("boundary_conditions")),
        ("合法设计边界", requirements.get("legal_design_boundaries")),
        ("架构假设", module_plan.get("assumptions")),
    ]:
        values = _as_list(value)
        if values:
            lines.append(f"{title}:")
            lines.extend("- " + _doc_item_text(item) for item in values)
            lines.append("")
    return lines or ["- 边界条件尚未填写。"]


def _doc_rtl_file_table_lines(rtl_modules: list[RtlModule]) -> list[str]:
    rows = ["| 文件 | 模块 | 职责 | 子模块依赖 |", "| --- | --- | --- | --- |"]
    for item in rtl_modules:
        rows.append(
            f"| `{item.file}` | `{item.name}` | {_escape_table(item.description or '-')} | "
            f"{_escape_table(', '.join(f'`{inst}`' for inst in item.instances) if item.instances else '-')} |"
        )
    if len(rows) == 2:
        rows.append("| - | - | RTL 文件尚未生成 | - |")
    return rows


def _doc_rtl_rule_lines(rules: dict[str, Any]) -> list[str]:
    lines = [
        f"- RTL 语言: {_string_or_dash(rules.get('rtl_language') or 'Verilog-2001')}",
        f"- RTL 根目录: `{_string_or_dash(rules.get('rtl_root') or 'output/rtl')}`",
        f"- Directed TB 语言: {_string_or_dash(rules.get('directed_tb_language') or 'Verilog-2001')}",
        f"- UVM 语言: {_string_or_dash(rules.get('uvm_language') or 'SystemVerilog')}",
        "- 硬规则:",
    ]
    lines.extend("  - " + _doc_item_text(item) for item in _as_list(rules.get("hard_rules")) or ["未配置"])
    return lines


def _doc_rtl_module_section(item: RtlModule, interfaces: dict[str, Any]) -> list[str]:
    lines = [
        f"<!-- HDL-DOC:RTL:{item.name} START -->",
        f"#### `{item.file}` / `{item.name}`",
        "",
        f"- 设计职责: {item.description or '该模块尚未提供 Description 头注释。'}",
        "- Scope:",
    ]
    lines.extend("  - " + text for text in item.scope or ["暂无 Scope 头注释。"])
    if item.parameters:
        lines.append("- 参数: " + ", ".join(f"`{param}`" for param in item.parameters))
    if item.instances:
        lines.append("- 子模块例化: " + ", ".join(f"`{inst}`" for inst in item.instances))
    lines.extend(["", "| 端口 | 方向 | 位宽 | 说明 |", "| --- | --- | --- | --- |"])
    if item.ports:
        for port in item.ports:
            lines.append(f"| `{port.name}` | {port.direction} | `{port.width}` | {_escape_table(_doc_port_description(port, interfaces))} |")
    else:
        lines.append("| - | - | - | 未扫描到端口 |")
    lines.extend(["", f"<!-- HDL-DOC:RTL:{item.name} END -->"])
    return lines


def _doc_port_description(port: RtlPort, interfaces: dict[str, Any]) -> str:
    for item in _as_list(interfaces.get("ports")):
        if isinstance(item, dict) and item.get("name") == port.name:
            desc = _first_value(item, "description", "protocol", "text", "title")
            width = item.get("width")
            if desc and width:
                return f"{desc} width={width}"
            if desc:
                return str(desc)
            break
    defaults = {
        "clk": "主工作时钟",
        "rst_n": "低有效复位",
        "uart_rx": "UART RX 物理输入端口",
        "uart_tx": "UART TX 物理输出端口",
        "busy_o": "模块忙状态输出",
        "rx_valid_o": "RX 数据有效脉冲",
        "rx_data_o": "RX 数据",
        "tx_busy_o": "TX 发送忙状态",
        "overflow_o": "溢出提示",
        "framing_error_o": "帧错误提示",
    }
    return defaults.get(port.name, f"{port.name} signal")


def _doc_verification_strategy_lines(verification: dict[str, Any], project_config: dict[str, Any]) -> list[str]:
    loop2 = ((project_config.get("nodes") or {}).get("work/loop2_uvm") or {})
    uvm_policy = loop2.get("uvm_policy") if isinstance(loop2, dict) else {}
    if not isinstance(uvm_policy, dict):
        uvm_policy = {}
    lines = [
        "- Directed TB 与 UVM 是分层验证路径，证据、日志和关闭条件分开管理。",
        "- Directed TB 负责确定性 baseline 与全功能检查，代码位于 `output/tb/`。",
        "- UVM 负责场景、压力、scoreboard、断言和覆盖率驱动验证，代码位于 `output/uvm/`。",
        f"- UVM 最少检查事务数: `{uvm_policy.get('min_checked_transactions', 64)}`",
        f"- UVM 最少场景数: `{uvm_policy.get('min_scenario_tests', 5)}`",
    ]
    for title, key in [
        ("模块级验证", "module_level"),
        ("系统级验证", "system_level"),
        ("Scoreboard", "scoreboards"),
        ("Reference Model", "reference_models"),
        ("负向/边界测试", "negative_tests"),
    ]:
        values = _as_list(verification.get(key))
        if values:
            lines.append(f"- {title}: {_doc_compact_items(values)}")
    return lines


def _doc_directed_tb_plan_lines(verification: dict[str, Any]) -> list[str]:
    rows = ["| TB 项 | 激励计划 | 期望结果 | 证据 |", "| --- | --- | --- | --- |"]
    rows.append(
        f"| Baseline entry checks | {_escape_table(_doc_compact_items(verification.get('baseline_entry_checks')))} | "
        "所有自检查通过且无运行错误 | Loop1 运行报告 |"
    )
    rows.append(
        f"| Full function matrix | {_escape_table(_doc_compact_items(verification.get('full_function_matrix')))} | "
        "每个功能、opcode 和边界场景都有 expected/actual 比较 | Loop1 运行报告 |"
    )
    return rows


def _doc_waveform_plan_lines(verification: dict[str, Any], test_intent: dict[str, Any]) -> list[str]:
    verification_windows = _as_list(verification.get("waveform_comparison"))
    intent_windows = _as_list(test_intent.get("waveform_windows"))
    observability = _as_list(test_intent.get("waveform_observability"))
    rows = [
        "- plan_sources: `work/docparse/structured_spec/test_intent.yaml`, `work/docparse/verification/verification_plan.yaml`",
        "- capture_policy: Loop1 captures WLF plus top-level VCD first; deeper internal signals are added only after a top-level window fails.",
        "- required_markers: `HDLFLOW_WAVE_BEGIN`/`HDLFLOW_WAVE_END` or `HDLFLOW_WAVE_WINDOW`",
        "- gate_evidence: `output/reports/loop1/waveform_check.json`",
        "",
        "| Requirement / Window | Observed Scope or Signals | Trigger / Time Span | Pass Criteria | Evidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in verification_windows or intent_windows:
        if isinstance(item, dict):
            window_id = _string_or_dash(_first_value(item, "requirement", "req_id", "id", "name", "window", "title"))
            signals = _doc_compact_items(
                _first_value(item, "signals", "observed_signals", "top_level_signals", "scope", "observed_scope")
            )
            trigger = _string_or_dash(_first_value(item, "trigger", "time_window", "window", "start_end", "sampling_window"))
            criteria = _string_or_dash(
                _first_value(item, "pass_criteria", "expected", "expected_activity", "criteria", "check")
            )
            evidence = _string_or_dash(
                _first_value(item, "evidence", "report", "artifact"),
                default="HDLFLOW_WAVE markers + waveform_check.json",
            )
        else:
            window_id = str(item)
            signals = _doc_compact_items(observability, empty="top-level DUT ports")
            trigger = "defined by TB waveform markers"
            criteria = "no X/Z, clock activity, and expected non-clock activity"
            evidence = "HDLFLOW_WAVE markers + waveform_check.json"
        rows.append(
            f"| {_escape_table(window_id)} | {_escape_table(signals)} | {_escape_table(trigger)} | "
            f"{_escape_table(criteria)} | {_escape_table(evidence)} |"
        )
    if len(rows) == 7:
        rows.append(
            "| 未规划 | DocParse READY requires `waveform_windows` and `waveform_comparison` before Loop1 handoff | "
            "TBD | TBD | `waveform_check.json` |"
        )
    return rows


def _doc_uvm_manifest_lines(manifest: dict[str, Any]) -> list[str]:
    lines = []
    if manifest.get("template_family"):
        lines.append(f"- 框架: {manifest.get('template_family')}")
    layout = manifest.get("layout")
    if isinstance(layout, dict):
        for name, desc in layout.items():
            lines.append(f"- `{name}`: {desc}")
    closure = manifest.get("closure_policy")
    if isinstance(closure, dict):
        lines.append("- 关闭策略:")
        for name, value in closure.items():
            lines.append(f"  - `{name}`: {value}")
    return lines or ["- UVM manifest 尚未填写。"]


def _doc_uvm_table_lines(files: list[UvmFile]) -> list[str]:
    rows = ["| 文件 | 类别 | 主要 class/package | 作用 |", "| --- | --- | --- | --- |"]
    for item in files:
        classes = ", ".join(f"`{name}`" for name in item.classes) if item.classes else "-"
        rows.append(f"| `{item.file}` | {item.category} | {_escape_table(classes)} | {_escape_table(_doc_uvm_purpose(item.file, item.purpose))} |")
    if len(rows) == 2:
        rows.append("| - | - | - | UVM 文件尚未生成 |")
    return rows


def _doc_coverage_assertion_lines(assertions: dict[str, Any], coverage: dict[str, Any]) -> list[str]:
    rows = ["| 类型 | 计划内容 |", "| --- | --- |"]
    for item in _as_list(assertions.get("assertions")):
        rows.append(f"| SVA | {_escape_table(_doc_item_text(item))} |")
    for item in _as_list(coverage.get("functional_coverage")):
        rows.append(f"| Coverage | {_escape_table(_doc_item_text(item))} |")
    for item in _as_list(coverage.get("cross_coverage")):
        rows.append(f"| Cross Coverage | {_escape_table(_doc_item_text(item))} |")
    if len(rows) == 2:
        rows.append("| - | 暂无条目 |")
    return rows


def _doc_uvm_test_matrix_lines(verification: dict[str, Any], project_config: dict[str, Any]) -> list[str]:
    loop2 = ((project_config.get("nodes") or {}).get("work/loop2_uvm") or {})
    uvm_policy = loop2.get("uvm_policy") if isinstance(loop2, dict) else {}
    if not isinstance(uvm_policy, dict):
        uvm_policy = {}
    scenario_policy = _as_list(uvm_policy.get("required_stimulus_scenarios"))
    rows = ["| UVM 项 | Transaction / Stimulus Plan | 期望结果 | 证据 |", "| --- | --- | --- | --- |"]
    rows.append(
        f"| Scenario tests | {_escape_table(_doc_compact_items(verification.get('scenario_tests') or scenario_policy))} | "
        "场景通过 scoreboard 与断言检查 | Loop2 回归报告 |"
    )
    rows.append(
        f"| Stress tests | {_escape_table(_doc_compact_items(verification.get('stress_tests')))} | "
        "压力事务达到配置数量并产生覆盖率证据 | Loop2 回归报告与覆盖率索引 |"
    )
    rows.append(
        f"| FPGA-realistic tests | {_escape_table(_doc_compact_items(verification.get('fpga_realistic_tests')))} | "
        "外部激励路径与原型计划一致 | Loop3 验证报告 |"
    )
    return rows


def _doc_log_format_lines() -> list[str]:
    return [
        "Directed TB 和 UVM 每个检查项都必须输出结构化 case marker，供平台脚本从真实仿真日志生成报告。",
        "",
        "```text",
        "========== HDLFLOW_TEST_CASE ==========",
        "HDLFLOW_TEST_CASE id=<test_id> stimulus=<what_was_sent> expected=<expected_behavior> actual=<observed_behavior> result=<PASS_or_FAIL> transactions=<count> stimuli=<count>",
        "========== END_HDLFLOW_TEST_CASE ==========",
        "```",
    ]


def _doc_fpga_mode_lines(fpga: dict[str, Any]) -> list[str]:
    return [
        f"- DocParse 原型模式: `{fpga.get('docparse_mode')}`",
        f"- Loop3 board_tests 原型模式: `{fpga.get('loop3_mode')}`",
        f"- 当前采用模板: {_doc_active_template_name(fpga)}",
        f"- 板卡型号: `{fpga.get('board')}`",
        f"- FPGA part: `{fpga.get('part')}`",
        f"- RTL top / IP: `{fpga.get('rtl_top_module')}`",
        f"- Vivado 版本: `{fpga.get('tool_version')}`",
        f"- 串口参数: `{fpga.get('serial_port')}` / `{fpga.get('baud_rate')}` baud",
        f"- 时钟参数: `{', '.join(fpga.get('clock_ports', [])) or '-'}`",
    ]


def _doc_fpga_resource_lines(fpga: dict[str, Any]) -> list[str]:
    rows = ["| 模式 | RTL/BD 端口 | 板级资源 | 引脚编号 | 方向/类型 | 连接关系 |", "| --- | --- | --- | --- | --- | --- |"]
    for row in fpga.get("resource_rows", []):
        rows.append(
            f"| PL | `{row.get('port', '-')}` | `{row.get('resource', '-')}` | `{row.get('pin', '-')}` | "
            f"{row.get('kind', '-')} | {row.get('connection', '-')} |"
        )
    if len(rows) == 2:
        rows.append("| PL | - | - | - | - | 当前未生成引脚资源表 |")
    for item in fpga.get("pure_pl_resources", []):
        rows.append(f"| resource_estimate | - | {_escape_table(item)} | - | - | - |")
    return rows


def _doc_fpga_ps_pl_lines(fpga: dict[str, Any]) -> list[str]:
    lines = []
    for title, key in [
        ("PS_PL AXI 区域", "axi_regions"),
        ("PS MIO 分配", "ps_mio"),
        ("PL 端口", "pl_ports"),
        ("BD 外部端口", "bd_ports"),
        ("PS-PL 连接", "ps_pl_connections"),
        ("Block Design", "ps_pl_block_design"),
        ("PL IP 端口", "pl_ip_ports"),
        ("软件激励流程", "software_stimulus_flow"),
        ("FPGA 构建流程", "fpga_build_flow"),
        ("原型验证流程", "validation_flow"),
    ]:
        values = _as_list(fpga.get(key))
        if values:
            lines.append(f"{title}:")
            lines.extend("- " + str(item) for item in values)
            lines.append("")
    return lines or ["- 当前未填写 PS-PL 交互规划。"]


def _doc_fpga_risk_lines(fpga: dict[str, Any]) -> list[str]:
    risks = list(fpga.get("warnings", []))
    risks.extend(fpga.get("risk_items", []))
    if not risks:
        return ["- 当前未发现 FPGA 原型架构阻塞项。"]
    return ["- " + str(item) for item in risks]


def _doc_fpga_expected_lines(fpga: dict[str, Any]) -> list[str]:
    rows = ["| 模式 | 预期表现 | 验证证据 |", "| --- | --- | --- |"]
    active = _prototype_mode_key(str(fpga.get("loop3_mode") or ""))
    for item in fpga.get("expected_board_checks", []):
        expected, evidence = _doc_expected_board_check(item)
        rows.append(f"| {_escape_table(active or 'PL')} | {_escape_table(expected)} | {_escape_table(evidence)} |")
    if len(rows) == 2:
        rows.append("| - | 当前未填写板级测试计划 | - |")
    return rows


def _doc_traceability_lines(snapshot: dict[str, Any]) -> list[str]:
    rows = ["| 矩阵 | Requirement | Target | 说明 |", "| --- | --- | --- | --- |"]
    for name, key in [
        ("req_to_arch", "trace_req_to_arch"),
        ("req_to_rtl", "trace_req_to_rtl"),
        ("req_to_test", "trace_req_to_test"),
        ("req_to_proto", "trace_req_to_proto"),
    ]:
        data = snapshot.get(key, {})
        links = _as_list(data.get("links")) if isinstance(data, dict) else []
        for item in links:
            if isinstance(item, dict):
                rows.append(
                    f"| `{name}` | `{_string_or_dash(_first_value(item, 'requirement', 'req_id', 'source', 'from'))}` | "
                    f"`{_string_or_dash(_first_value(item, 'target', 'to', 'artifact'))}` | "
                    f"{_escape_table(_string_or_dash(_first_value(item, 'description', 'rationale', 'status', 'title')))} |"
                )
            else:
                rows.append(f"| `{name}` | - | - | {_escape_table(item)} |")
    if len(rows) == 2:
        rows.append("| - | - | - | 追溯矩阵尚未填写 |")
    return rows


def _first_value(mapping: Any, *keys: str) -> Any:
    if not isinstance(mapping, dict):
        return None
    for key in keys:
        value = mapping.get(key)
        if _has_non_empty_value(value):
            return value
    return None


def _doc_item_id(item: dict[str, Any], *, default: str = "-") -> str:
    return _string_or_dash(_first_value(item, "id", "req_id", "name", "title", "scenario"), default=default)


def _doc_item_text(item: Any) -> str:
    if not isinstance(item, dict):
        return str(item)
    title = _first_value(item, "title", "name", "id")
    detail = _first_value(item, "text", "description", "summary", "detail", "requirement", "responsibility", "role", "purpose", "expected")
    if title and detail and str(title) not in str(detail):
        return f"{title}: {detail}"
    if detail:
        return str(detail)
    if title:
        return str(title)
    return ", ".join(f"{key}={value}" for key, value in item.items())


def _doc_compact_items(items: Any, *, empty: str = "未填写") -> str:
    values = _as_list(items)
    if not values:
        return empty
    rendered = []
    for item in values[:8]:
        if isinstance(item, dict):
            rendered.append(_doc_item_text(item))
        else:
            rendered.append(str(item))
    suffix = f"; +{len(values) - 8} more" if len(values) > 8 else ""
    return "; ".join(rendered) + suffix


def _string_or_dash(value: Any, *, default: str = "-") -> str:
    if value in (None, "", [], {}):
        return default
    return str(value)


def _has_non_empty_value(value: Any) -> bool:
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, dict):
        return bool(value)
    if isinstance(value, str):
        return bool(value.strip())
    return value is not None


def _doc_uvm_purpose(rel: str, fallback: str) -> str:
    name = Path(rel).name
    if "item" in name:
        return "定义 transaction item 和协议字段。"
    if "driver" in name:
        return "把 transaction 转换为 DUT 激励。"
    if "monitor" in name:
        return "观测 DUT 行为并发布 transaction。"
    if "scoreboard" in name:
        return "比较期望结果和观测结果。"
    if "coverage" in name:
        return "采样功能覆盖率。"
    if "sequence" in name:
        return "组织基础、边界和压力场景。"
    if "test" in name or name == "tests.svh":
        return "定义 UVM testcase 和回归入口。"
    if "sva" in name:
        return "提供非侵入式 assertion/bind 检查。"
    return fallback or "UVM 环境支撑文件。"


def _doc_active_template_name(fpga: dict[str, Any]) -> str:
    return "PS_PL 模板" if _prototype_mode_key(str(fpga.get("loop3_mode") or "")) == "ps_pl" else "PL 模板"


def _doc_expected_board_check(item: Any) -> tuple[str, str]:
    if isinstance(item, dict):
        expected = str(_first_value(item, "expected", "description", "name", "title") or item)
        check_type = str(item.get("type") or "").strip()
        blocking = item.get("blocking")
        if check_type == "human_observation" and blocking is False:
            return expected, "人工观察记录，原型阶段 non-blocking"
        if check_type == "automated_serial":
            return expected, "Vivado Tcl、bitstream、串口验证报告"
        return expected, "Vivado Tcl、bitstream、板级观察或串口验证报告"
    return str(item), "Vivado Tcl、bitstream、板级观察或串口验证报告"


def _fpga_resource_rows(project: Path, loop3: dict[str, Any]) -> list[dict[str, str]]:
    assignments = loop3.get("pl_port_assignments")
    if not isinstance(assignments, dict):
        return []
    xdc_ports = _parse_xdc_ports(project / "output" / "fpga" / "vivado" / "constraints" / "generated_board.xdc")
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
    rtl_dir = project / "output" / "rtl"
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
    uvm_dir = project / "output" / "uvm"
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
        "ps_pl_connections": _format_mapping(loop3.get("ps_pl_connections")),
        "ps_pl_block_design": _format_mapping(loop3.get("ps_pl_block_design"))
        or _format_mapping(docparse.get("ps_pl_block_design")),
        "pl_ip_ports": _format_mapping(loop3.get("pl_ip_ports")),
        "software_stimulus_flow": _as_list(loop3.get("software_stimulus_flow"))
        or _as_list(docparse.get("software_stimulus_flow")),
        "fpga_build_flow": _as_list(loop3.get("fpga_build_flow"))
        or _as_list(docparse.get("fpga_build_flow")),
        "validation_flow": _as_list(loop3.get("validation_flow"))
        or _as_list(docparse.get("validation_flow")),
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
        "sections": ["requirements", "architecture", "rtl", "uvm", "test_plan", "fpga", "traceability"],
        "source_signature": _source_signature(source_hashes),
        "source_hashes": source_hashes,
        "rtl_modules": rtl_modules,
        "uvm_files": uvm_files,
        "fpga_mode_summary": snapshot["fpga"]["mode_summary"],
        "warnings": snapshot["warnings"],
    }


def _source_hashes(project: Path) -> list[dict[str, str]]:
    roots = [
        SPEC_INPUT_REL,
        "work/docparse/structured_spec",
        "work/docparse/req_decompose",
        "work/docparse/architecture",
        "work/docparse/verification",
        "work/docparse/prototype",
        "work/docparse/trace_matrix",
        "work/loop3_fpga_proto/board_tests",
        "output/rtl",
        "output/uvm",
    ]
    suffixes = {".yaml", ".yml", ".json", ".md", ".v", ".sv", ".svh"}
    paths: list[Path] = []
    for rel in roots:
        root = project / rel
        if root.is_file() and root.suffix.lower() in suffixes:
            paths.append(root)
        elif root.is_dir():
            paths.extend(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in suffixes and "_runtime" not in path.parts)
    try:
        paths.append(load_project(project).config_path)
    except Exception:
        pass
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


def _load_project_config(project: Path) -> dict[str, Any]:
    try:
        data = load_project(project).data
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
    resolved = path.resolve()
    project_resolved = project.resolve()
    try:
        return str(resolved.relative_to(project_resolved)).replace("\\", "/")
    except ValueError:
        pass

    workspace = find_workspace_root(project_resolved)
    try:
        return "workspace:" + str(resolved.relative_to(workspace)).replace("\\", "/")
    except ValueError:
        return "external:" + str(resolved).replace("\\", "/")
