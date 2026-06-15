"""Planning maturity checks for DocParse architecture artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .project import require_project_instance
from .simple_yaml import load_yaml


PLAN_REPORT_REL = "output/reports/docparse/plan_report.md"
VALID_MATURITIES = {"docparse", "loop1", "lld"}


@dataclass(frozen=True)
class PlanIssue:
    path: str
    severity: str
    message: str


@dataclass(frozen=True)
class PlanCheckResult:
    report_path: Path
    maturity: str
    issues: list[PlanIssue]

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)


def check_plan(project_path: Path, *, maturity: str = "docparse", write_report: bool = True) -> PlanCheckResult:
    project = require_project_instance(project_path)
    maturity = maturity.lower().strip()
    if maturity not in VALID_MATURITIES:
        raise ValueError("maturity must be one of: " + ", ".join(sorted(VALID_MATURITIES)))

    issues: list[PlanIssue] = []
    module_plan = _load(project, "work/docparse/architecture/module_plan.yaml", issues)
    interface_contracts = _load(project, "work/docparse/architecture/interface_contracts.yaml", issues)
    dataflow = _load(project, "work/docparse/architecture/dataflow.yaml", issues)
    state_machines = _load(project, "work/docparse/architecture/state_machines.yaml", issues)
    timing_model = _load(project, "work/docparse/architecture/timing_model.yaml", issues)
    doc_projection = _load(project, "work/docparse/doc_projection.yaml", issues)

    module_names, module_clocks, module_fsms = _check_module_plan(module_plan, issues, maturity)
    interface_names = _check_interface_contracts(interface_contracts, issues, maturity, module_names)
    _check_dataflow(dataflow, issues, maturity, module_names)
    _check_state_machines(state_machines, issues, maturity, module_names, module_fsms)
    _check_timing_model(timing_model, issues, maturity, module_names, module_clocks, interface_names)
    _check_doc_projection(project, doc_projection, issues, maturity)

    report = project / PLAN_REPORT_REL
    if write_report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(_format_report(project, maturity, issues), encoding="utf-8")
    return PlanCheckResult(report_path=report, maturity=maturity, issues=issues)


def _load(project: Path, rel: str, issues: list[PlanIssue]) -> dict[str, Any]:
    path = project / rel
    if not path.is_file():
        issues.append(PlanIssue(rel, "error", "missing planning source"))
        return {}
    try:
        data = load_yaml(path)
    except Exception as exc:
        issues.append(PlanIssue(rel, "error", f"not parseable: {exc}"))
        return {}
    if not isinstance(data, dict):
        issues.append(PlanIssue(rel, "error", "planning source must be a mapping"))
        return {}
    return data


def _check_module_plan(data: dict[str, Any], issues: list[PlanIssue], maturity: str) -> tuple[set[str], dict[str, str], dict[str, set[str]]]:
    rel = "work/docparse/architecture/module_plan.yaml"
    module_names: set[str] = set()
    module_clocks: dict[str, str] = {}
    module_fsms: dict[str, set[str]] = {}

    top = data.get("top_level") if isinstance(data.get("top_level"), dict) else {}
    _require_mapping_key(issues, rel, "top_level", top, maturity, "loop1")
    top_name = _text(top.get("name"))
    if not top_name:
        _issue(issues, rel, "top_level.name is not resolved", maturity, required_at="loop1")

    policy = data.get("module_partition_policy") if isinstance(data.get("module_partition_policy"), dict) else {}
    for key in [
        "top_down_partitioning",
        "cohesive_responsibility_per_file",
        "no_over_fragmentation",
        "no_under_fragmentation",
        "protocol_module_names_follow_official_standard",
    ]:
        if not _truthy(policy.get(key)):
            _issue(issues, rel, f"module_partition_policy.{key} should be true", maturity, required_at="loop1")

    modules = data.get("modules")
    if not isinstance(modules, list) or not modules:
        _issue(issues, rel, "modules must contain at least one planned module", maturity, required_at="loop1")
        return module_names, module_clocks, module_fsms

    for index, module in enumerate(modules, start=1):
        label = f"modules[{index}]"
        if not isinstance(module, dict):
            issues.append(PlanIssue(rel, "error", f"{label} must be a mapping"))
            continue
        name = _text(module.get("name"))
        if name:
            if name in module_names:
                issues.append(PlanIssue(rel, "error", f"duplicate module name: {name}"))
            module_names.add(name)
        module_clocks[name] = _text(module.get("clock_domain"))
        owns = module.get("owns") if isinstance(module.get("owns"), dict) else {}
        module_fsms[name] = _string_set(owns.get("fsms"))

        _check_module_skeleton(issues, rel, label, module, maturity)
        _check_module_lld_fields(issues, rel, label, module, top_name, maturity)
        _check_module_granularity(issues, rel, label, module, maturity)

    if top_name and top_name not in module_names:
        _issue(issues, rel, f"top_level.name {top_name} is not listed in modules", maturity, required_at="loop1")
    return module_names, module_clocks, module_fsms


def _check_module_skeleton(issues: list[PlanIssue], rel: str, label: str, module: dict[str, Any], maturity: str) -> None:
    for key in ["id", "name", "type", "responsibility", "status", "confidence", "known_unknowns"]:
        if key not in module:
            _issue(issues, rel, f"{label}.{key} is missing from the module item contract", maturity, required_at="loop1")
            continue
        if key in {"status", "confidence", "known_unknowns"}:
            continue
        if not _text(module.get(key)):
            _issue(issues, rel, f"{label}.{key} is unresolved", maturity, required_at="loop1")

    module_type = _text(module.get("type")).lower()
    if module_type and module_type not in {"top", "composite", "leaf"}:
        issues.append(PlanIssue(rel, "error", f"{label}.type must be one of top, composite, leaf"))
    status = _text(module.get("status")).lower()
    if status and status not in {"draft", "partial", "ready", "unknown"}:
        issues.append(PlanIssue(rel, "warning", f"{label}.status should be draft, partial, ready, or unknown"))
    confidence = _text(module.get("confidence")).lower()
    if confidence and confidence not in {"low", "medium", "high", "unknown"}:
        issues.append(PlanIssue(rel, "warning", f"{label}.confidence should be low, medium, high, or unknown"))


def _check_module_lld_fields(issues: list[PlanIssue], rel: str, label: str, module: dict[str, Any], top_name: str, maturity: str) -> None:
    name = _text(module.get("name"))
    required_scalars = ["source_file", "clock_domain", "reset_domain"]
    if name != top_name:
        required_scalars.append("parent")
    for key in required_scalars:
        if not _text(module.get(key)):
            _issue(issues, rel, f"{label}.{key} is unresolved", maturity, required_at="lld")

    owns = module.get("owns")
    if not isinstance(owns, dict):
        _issue(issues, rel, f"{label}.owns must be a mapping", maturity, required_at="loop1")
        owns = {}
    for key in ["registers", "register_fields", "fsms", "fifos", "memories", "counters", "arbiters", "error_flags"]:
        if key not in owns:
            _issue(issues, rel, f"{label}.owns.{key} is missing", maturity, required_at="loop1")
        elif not isinstance(owns.get(key), list):
            issues.append(PlanIssue(rel, "error", f"{label}.owns.{key} must be a list"))

    interfaces = module.get("interfaces")
    if not isinstance(interfaces, dict):
        _issue(issues, rel, f"{label}.interfaces must be a mapping", maturity, required_at="loop1")
        interfaces = {}
    for key in ["inputs", "outputs", "internal"]:
        if key not in interfaces:
            _issue(issues, rel, f"{label}.interfaces.{key} is missing", maturity, required_at="loop1")
        elif not isinstance(interfaces.get(key), list):
            issues.append(PlanIssue(rel, "error", f"{label}.interfaces.{key} must be a list"))
    if not _list_has_value(interfaces.get("inputs")):
        _issue(issues, rel, f"{label}.interfaces.inputs has no resolved item", maturity, required_at="lld")
    if not _list_has_value(interfaces.get("outputs")):
        _issue(issues, rel, f"{label}.interfaces.outputs has no resolved item", maturity, required_at="lld")

    dataflow = module.get("dataflow")
    if not isinstance(dataflow, dict):
        _issue(issues, rel, f"{label}.dataflow must be a mapping", maturity, required_at="loop1")
        dataflow = {}
    for key in ["consumes", "produces", "transforms"]:
        if key not in dataflow:
            _issue(issues, rel, f"{label}.dataflow.{key} is missing", maturity, required_at="loop1")
        elif not isinstance(dataflow.get(key), list):
            issues.append(PlanIssue(rel, "error", f"{label}.dataflow.{key} must be a list"))
    if not _list_has_value(dataflow.get("consumes")):
        _issue(issues, rel, f"{label}.dataflow.consumes has no resolved item", maturity, required_at="lld")
    if not _list_has_value(dataflow.get("produces")):
        _issue(issues, rel, f"{label}.dataflow.produces has no resolved item", maturity, required_at="lld")

    if not (_list_has_value(module.get("req_ids")) or _list_has_value(module.get("design_feature_ids"))):
        _issue(issues, rel, f"{label} has no req_ids or design_feature_ids", maturity, required_at="lld")


def _check_module_granularity(issues: list[PlanIssue], rel: str, label: str, module: dict[str, Any], maturity: str) -> None:
    responsibility = _text(module.get("responsibility")).lower()
    broad_terms = ["decode", "fifo", "fsm", "arbiter", "register", "datapath", "memory", "control"]
    hit_count = sum(1 for term in broad_terms if term in responsibility)
    if hit_count > 4:
        _issue(issues, rel, f"{label}.responsibility appears too broad; split ownership or justify boundary", maturity, required_at="lld")
    module_type = _text(module.get("type")).lower()
    owns = module.get("owns") if isinstance(module.get("owns"), dict) else {}
    dataflow = module.get("dataflow") if isinstance(module.get("dataflow"), dict) else {}
    owns_anything = any(_list_has_value(value) for value in owns.values())
    dataflow_anything = any(_list_has_value(value) for value in dataflow.values())
    if module_type == "leaf" and not owns_anything and not dataflow_anything:
        _issue(issues, rel, f"{label} leaf has no ownership or dataflow; it may be over-fragmented", maturity, required_at="lld")


def _check_interface_contracts(data: dict[str, Any], issues: list[PlanIssue], maturity: str, module_names: set[str]) -> set[str]:
    rel = "work/docparse/architecture/interface_contracts.yaml"
    interface_names: set[str] = set()
    interfaces = data.get("interfaces")
    if not isinstance(interfaces, list):
        _issue(issues, rel, "interfaces must be a list", maturity, required_at="loop1")
        return interface_names
    for index, item in enumerate(interfaces, start=1):
        if not isinstance(item, dict):
            issues.append(PlanIssue(rel, "error", f"interfaces[{index}] must be a mapping"))
            continue
        label = f"interfaces[{index}]"
        name = _text(item.get("name") or item.get("id"))
        if name:
            interface_names.add(name)
        else:
            _issue(issues, rel, f"{label}.name is unresolved", maturity, required_at="loop1")
        for key in ["producer_module", "consumer_module"]:
            _check_module_ref(issues, rel, f"{label}.{key}", item.get(key), module_names, maturity)
    return interface_names


def _check_dataflow(data: dict[str, Any], issues: list[PlanIssue], maturity: str, module_names: set[str]) -> None:
    rel = "work/docparse/architecture/dataflow.yaml"
    flows = data.get("flows")
    if not isinstance(flows, list):
        _issue(issues, rel, "flows must be a list", maturity, required_at="loop1")
        return
    for index, item in enumerate(flows, start=1):
        if not isinstance(item, dict):
            issues.append(PlanIssue(rel, "error", f"flows[{index}] must be a mapping"))
            continue
        label = f"flows[{index}]"
        _check_module_ref(issues, rel, f"{label}.producer_module", item.get("producer_module"), module_names, maturity)
        _check_module_ref(issues, rel, f"{label}.consumer_module", item.get("consumer_module"), module_names, maturity)


def _check_state_machines(data: dict[str, Any], issues: list[PlanIssue], maturity: str, module_names: set[str], module_fsms: dict[str, set[str]]) -> None:
    rel = "work/docparse/architecture/state_machines.yaml"
    fsms = data.get("state_machines")
    if fsms in (None, []):
        return
    if not isinstance(fsms, list):
        issues.append(PlanIssue(rel, "error", "state_machines must be a list"))
        return
    for index, item in enumerate(fsms, start=1):
        if not isinstance(item, dict):
            issues.append(PlanIssue(rel, "error", f"state_machines[{index}] must be a mapping"))
            continue
        label = f"state_machines[{index}]"
        owner = _text(item.get("owning_module"))
        _check_module_ref(issues, rel, f"{label}.owning_module", owner, module_names, maturity)
        name = _text(item.get("name") or item.get("id"))
        if owner in module_fsms and name and name not in module_fsms[owner]:
            _issue(issues, rel, f"{label}.name is not listed in module_plan owns.fsms for {owner}", maturity, required_at="lld")


def _check_timing_model(
    data: dict[str, Any],
    issues: list[PlanIssue],
    maturity: str,
    module_names: set[str],
    module_clocks: dict[str, str],
    interface_names: set[str],
) -> None:
    rel = "work/docparse/architecture/timing_model.yaml"
    clock_domains = data.get("clock_domains")
    if not isinstance(clock_domains, list):
        _issue(issues, rel, "clock_domains must be a list", maturity, required_at="loop1")
        return
    clock_names = {
        _text(item.get("name"))
        for item in clock_domains
        if isinstance(item, dict) and _text(item.get("name"))
    }
    for module, clock in sorted(module_clocks.items()):
        if module and clock and clock not in clock_names:
            _issue(issues, rel, f"clock_domains does not cover module {module} clock_domain {clock}", maturity, required_at="loop1")

    cdc_items = data.get("cdc_requirements")
    if cdc_items in (None, []):
        return
    if not isinstance(cdc_items, list):
        issues.append(PlanIssue(rel, "error", "cdc_requirements must be a list"))
        return
    for index, item in enumerate(cdc_items, start=1):
        if not isinstance(item, dict):
            issues.append(PlanIssue(rel, "error", f"cdc_requirements[{index}] must be a mapping"))
            continue
        label = f"cdc_requirements[{index}]"
        interface = _text(item.get("interface"))
        if interface and interface not in interface_names:
            _issue(issues, rel, f"{label}.interface references unknown interface {interface}", maturity, required_at="loop1")
        for key in ["producer_module", "consumer_module"]:
            _check_module_ref(issues, rel, f"{label}.{key}", item.get(key), module_names, maturity)
        from_clock = _text(item.get("from_clock_domain"))
        to_clock = _text(item.get("to_clock_domain"))
        if from_clock and to_clock and from_clock == to_clock:
            _issue(issues, rel, f"{label} must cross two different clock domains", maturity, required_at="loop1")


def _check_doc_projection(project: Path, data: dict[str, Any], issues: list[PlanIssue], maturity: str) -> None:
    rel = "work/docparse/doc_projection.yaml"
    documents = data.get("documents")
    if not isinstance(documents, dict) or not documents:
        _issue(issues, rel, "documents must be a non-empty mapping", maturity, required_at="docparse")
        return
    for doc_name, spec in documents.items():
        if not isinstance(spec, dict):
            issues.append(PlanIssue(rel, "error", f"documents.{doc_name} must be a mapping"))
            continue
        sources = spec.get("sources")
        if not isinstance(sources, list) or not sources:
            _issue(issues, rel, f"documents.{doc_name}.sources must be a non-empty list", maturity, required_at="docparse")
            continue
        for index, source in enumerate(sources, start=1):
            if not isinstance(source, dict):
                issues.append(PlanIssue(rel, "error", f"documents.{doc_name}.sources[{index}] must be a mapping"))
                continue
            source_path = _text(source.get("path"))
            source_id = _text(source.get("id"))
            if not source_id:
                _issue(issues, rel, f"documents.{doc_name}.sources[{index}].id is unresolved", maturity, required_at="docparse")
            if not source_path:
                _issue(issues, rel, f"documents.{doc_name}.sources[{index}].path is unresolved", maturity, required_at="docparse")
            elif source.get("required", True) is not False and not (project / source_path).exists():
                _issue(issues, rel, f"documents.{doc_name}.sources[{index}].path missing required source {source_path}", maturity, required_at="docparse")


def _check_module_ref(issues: list[PlanIssue], rel: str, label: str, value: Any, module_names: set[str], maturity: str) -> None:
    text = _text(value)
    if not text:
        _issue(issues, rel, f"{label} is unresolved", maturity, required_at="loop1")
        return
    if text not in module_names:
        _issue(issues, rel, f"{label} references unknown module {text}", maturity, required_at="loop1")


def _issue(issues: list[PlanIssue], rel: str, message: str, maturity: str, *, required_at: str) -> None:
    severity = "error" if _maturity_rank(maturity) >= _maturity_rank(required_at) else "warning"
    issues.append(PlanIssue(rel, severity, message))


def _maturity_rank(value: str) -> int:
    return {"docparse": 0, "loop1": 1, "lld": 2}.get(value, 0)


def _require_mapping_key(issues: list[PlanIssue], rel: str, label: str, value: Any, maturity: str, required_at: str) -> None:
    if not isinstance(value, dict):
        _issue(issues, rel, f"{label} must be a mapping", maturity, required_at=required_at)


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "yes", "1"}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _string_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {_text(item) for item in value if _text(item)}


def _list_has_value(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    return any(_text(item) for item in value)


def _format_report(project: Path, maturity: str, issues: list[PlanIssue]) -> str:
    errors = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity == "warning"]
    lines = [
        "# Planning Quality Report",
        "",
        f"- project: {project.name}",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- maturity: {maturity}",
        f"- result: {'PASS' if not errors else 'FAIL'}",
        f"- errors: {len(errors)}",
        f"- warnings: {len(warnings)}",
        "",
        "## 1. Summary",
        "",
        "This report checks whether the architecture plan is mature enough for the requested stage.",
        "",
        "## 2. Issues",
        "",
    ]
    if not issues:
        lines.append("- none")
    else:
        for issue in issues:
            lines.append(f"- {issue.severity}: {issue.path}: {issue.message}")
    lines.extend(
        [
            "",
            "## 3. Maturity Policy",
            "",
            "- docparse: unresolved design details are allowed, but they must be visible.",
            "- loop1: module hierarchy, module references, and timing ownership should be resolved.",
            "- lld: leaf module ownership, interfaces, dataflow, and verification references should be complete enough to write code from the document.",
            "",
        ]
    )
    return "\n".join(lines)
