"""Requirements front-door guards for formal implementation artifacts."""

from __future__ import annotations

import re
import os
import json
from dataclasses import dataclass
from pathlib import Path

from .layout import project_memory_path

FORMAL_IMPLEMENTATION_PREFIXES = (
    "output/rtl",
    "output/tb",
    "output/uvm",
    "work/loop3_fpga_proto",
    "output/fpga",
)

DESIGN_REPORT_PREFIX = "output/docs"
SPEC_INPUT_PREFIX = "input/spec"
LEGACY_SPLIT_INPUT_PREFIXES = tuple(f"input/{name}" for name in ("raw_" + "docs", "require" + "ments"))

NODE_MANIFEST_STEMS = {
    "input": ("input",),
    "work/docparse": ("work_docparse",),
    "work/loop1_rtl_tb": ("work_loop1_rtl_tb",),
    "work/loop2_uvm": ("work_loop2_uvm",),
    "work/loop3_fpga_proto": ("work_loop3_fpga_proto",),
    "output": ("output",),
}

STAGE_ALIASES = {
    "docparse": "docparse",
    "work/docparse": "docparse",
    "loop1": "loop1",
    "work/loop1_rtl_tb": "loop1",
    "loop2": "loop2",
    "work/loop2_uvm": "loop2",
    "loop3": "loop3",
    "work/loop3_fpga_proto": "loop3",
    "loop3-preflight": "loop3-preflight",
    "loop3_preflight": "loop3-preflight",
    "loop3-generation": "loop3-preflight",
    "loop3_generation": "loop3-preflight",
}

WRITE_INTENT_PATTERNS = (
    r"\bapply_patch\b",
    r"\bset-content\b",
    r"\badd-content\b",
    r"\bout-file\b",
    r"\bnew-item\b",
    r"\bremove-item\b",
    r"\bmove-item\b",
    r"\bcopy-item\b",
    r"\bni\b",
    r"\bdel\b",
    r"\brm\b",
    r"\bmkdir\b",
    r">\s*['\"]?[^|]",
    r">>",
    r"\bprototype-preflight\b",
    r"\bvalidate-prototype-plan\b",
    r"\bgenerate-xdc\b",
    r"\bgenerate-ps-pl-bd\b",
    r"\bgenerate-vitis-boot\b",
    r"\bloop1-refresh-reports\b",
    r"\bloop1-waveform-gate\b",
    r"\bloop2-refresh-reports\b",
    r"\bloop2-build-bindings\b",
    r"\bloop2-database-preflight\b",
    r"\binvoke-hdlmodelsim\.ps1\b",
    r"\binvoke-hdlvivado\.ps1\b",
    r"\binvoke-hdlvitis\.ps1\b",
    r"\bbuild-bootimage\.ps1\b",
    r"\bxsct(?:\.bat|\.exe)?\b",
    r"\bvitis(?:\.bat|\.exe)?\b",
    r"\bbootgen(?:\.bat|\.exe)?\b",
    r"\bvsim\b",
    r"\bvlog\b",
)

SOURCE_EDIT_INTENT_PATTERNS = (
    r"\bapply_patch\b",
    r"\bset-content\b",
    r"\badd-content\b",
    r"\bout-file\b",
    r"\bnew-item\b",
    r"\bremove-item\b",
    r"\bmove-item\b",
    r"\bcopy-item\b",
    r"\bni\b",
    r"\bdel\b",
    r"\brm\b",
    r"\bmkdir\b",
    r">\s*['\"]?[^|]",
    r">>",
)

AGENT_ALIASES = {
    "spec_agent": "spec",
    "arch_agent": "arch",
    "exec_agent": "exec",
    "sim_agent": "sim",
    "review_agent": "review",
    "arbtr_agent": "arbtr",
    "arbitration": "arbtr",
}

AGENT_WRITE_PREFIXES = {
    "spec": (
        SPEC_INPUT_PREFIX,
        "work/docparse/frontdoor",
        "work/docparse/structured_spec",
        "work/docparse/req_decompose",
        "work/docparse/trace_matrix",
    ),
    "arch": (
        "work/docparse/architecture",
    ),
    "exec": (
        "output/rtl",
        "output/tb",
    ),
    "sim": (
        "output/uvm",
        "output/reports/loop1",
        "output/reports/loop2",
        "output/reports/loop3",
        "work/loop1_rtl_tb/_runtime",
        "work/loop1_rtl_tb/sim",
        "work/loop2_uvm/_runtime",
        "work/loop2_uvm/sim",
        "work/loop3_fpga_proto/_runtime",
    ),
    "review": (
        "work/docparse/review",
        "output/reports/review",
    ),
    "arbtr": (
        "work/memory/",
        "work/gates/",
        "output/reports/gates",
        "output/reports/freeze",
    ),
}

CONTROLLED_PREFIXES = tuple(
    sorted({prefix for prefixes in AGENT_WRITE_PREFIXES.values() for prefix in prefixes}, key=len, reverse=True)
)

FRONTDOOR_COMMAND_PATTERNS = (
    r"\brequirements-frontdoor-init\b",
    r"\brequirements-frontdoor-check\b",
    r"\brun-gate\b.*\b(?:spec|input|docparse|work/docparse|00|01)\b",
)

CHANGE_CONTROL_COMMAND_PATTERNS = (
    r"\bchange-open\b",
    r"\bchange-impact\b",
    r"\bchange-approve\b",
    r"\bchange-close\b",
    r"\bchange-check\b",
)

FRONTDOOR_GENERATOR_COMMAND_PATTERNS = (
    r"\bgenerate-docs\b",
    r"\bgenerate-application-doc\b",
    r"\bgenerate-uarch-doc\b",
    r"\bgenerate-verification-doc\b",
    r"\bgenerate-delivery-doc\b",
    r"\bcheck-docset\b",
)

CONTROLLED_PROTOTYPE_COMMAND_PATTERNS = (
    r"\bprototype-preflight\b",
    r"\bvalidate-prototype-plan\b",
    r"\bgenerate-xdc\b",
    r"\bgenerate-ps-pl-bd\b",
    r"\bgenerate-vitis-boot\b",
    r"\binvoke-hdlvivado\.ps1\b",
    r"\binvoke-hdlvitis\.ps1\b",
    r"\bbuild-bootimage\.ps1\b",
)

FRONTDOOR_SOURCE_PREFIXES = (
    SPEC_INPUT_PREFIX,
    "work/docparse/frontdoor",
    "work/docparse/structured_spec",
    "work/docparse/req_decompose",
    "work/docparse/architecture",
    "work/docparse/verification",
    "work/docparse/prototype",
    "work/docparse/trace_matrix",
)

PROTOTYPE_CHANGE_PREFIXES = (
    "work/loop3_fpga_proto/board_tests",
    "work/loop3_fpga_proto/board_profiles",
    "work/loop3_fpga_proto/scripts",
    "output/fpga/vivado/constraints",
    "output/fpga/vivado/scripts",
    "output/fpga/vitis",
)

GENERATED_FPGA_OUTPUT_PREFIXES = (
    "output/fpga/vivado/constraints",
    "output/fpga/vivado/scripts",
    "output/fpga/vitis",
)

OFFICIAL_GENERATED_FPGA_COMMAND_PATTERNS = (
    r"\bgenerate-xdc\b",
    r"\bgenerate-ps-pl-bd\b",
    r"\bgenerate-vitis-boot\b",
    r"\binvoke-hdlvivado\.ps1\b",
    r"\binvoke-hdlvitis\.ps1\b",
    r"\bbuild-bootimage\.ps1\b",
)

FORMAL_REQUIREMENT_CHANGE_RULES = (
    {
        "node": "work/loop1_rtl_tb",
        "scope": "Loop1 RTL/TB requirement changes",
        "prefixes": (
            "output/rtl",
            "output/tb",
            "work/loop1_rtl_tb/sim",
        ),
        "required_sections": ("microarchitecture_specification", "verification_plan", "delivery_package"),
    },
    {
        "node": "work/loop2_uvm",
        "scope": "Loop2 UVM requirement changes",
        "prefixes": (
            "output/uvm",
            "work/loop2_uvm/sim",
        ),
        "required_sections": ("verification_plan", "delivery_package"),
    },
)

PROTECTED_GATE_POLICY_PREFIXES = (
    "env/rule/global/gates",
    "env/rule/project_default/project_config.yaml",
    "work/config",
    "env/core/hdlflow/gates.py",
    "env/core/hdlflow/frontdoor_guard.py",
    "env/core/hdlflow/ralph_loop.py",
    "env/core/hdlflow/requirements_frontend.py",
    "env/core/hdlflow/review.py",
    "env/core/hdlflow/waveform.py",
    "env/core/hooks/invoke-hdlpretoolguard.ps1",
    "env/tool/scripts/invoke-hdlloop3boardverify.ps1",
    "env/tool/scripts/invoke-hdlvitis.ps1",
)

PROJECT_FRONTDOOR_POPULATE_SCRIPT_PATTERNS = (
    r"env/tool/scripts/populate_[a-z0-9_-]+_frontdoor\.py\b",
)

ACTIVE_CHANGE_STATUSES = {"open", "impact_ready", "approved"}
APPROVED_CHANGE_STATUSES = {"approved"}

OFFICIAL_PROJECT_CREATE_PATTERNS = (
    r"env/tool/scripts/new-hdlproject\.ps1\b",
    r"env/tool/scripts/new_hdl_project\.py\b",
)

PROJECT_CREATE_BYPASS_PATTERNS = (
    r"hdlflow\.cli\s+init-project\b",
    r"\bhdlflow\s+init-project\b",
    r"\b(?:new-item|mkdir|copy-item|robocopy)\b.*\bprj/",
)

DIRECT_VIVADO_COMMAND_PATTERNS = (
    r"(?:^|[\s&;\"'])vivado(?:\.bat|\.exe)?[\"']?\s+.*-mode\b",
    r"(?:^|[\s&;\"'])[a-z]:/[^ \t\r\n\"']*/vivado(?:\.bat|\.exe)[\"']?\s+.*-mode\b",
)

CONTROLLED_VIVADO_MARKERS = (
    r"env/tool/scripts/invoke-hdlvivado\.ps1\b",
    r"\binvoke-hdlvivado\.ps1\b",
)

DIRECT_VITIS_COMMAND_PATTERNS = (
    r"(?:^|[\s&;\"'])xsct(?:\.bat|\.exe)?[\"']?\s+",
    r"(?:^|[\s&;\"'])vitis(?:\.bat|\.exe)?[\"']?\s+",
    r"(?:^|[\s&;\"'])bootgen(?:\.bat|\.exe)?[\"']?\s+",
    r"(?:^|[\s&;\"'])[a-z]:/[^ \t\r\n\"']*/xsct(?:\.bat|\.exe)[\"']?\s+",
    r"(?:^|[\s&;\"'])[a-z]:/[^ \t\r\n\"']*/vitis(?:\.bat|\.exe)[\"']?\s+",
    r"(?:^|[\s&;\"'])[a-z]:/[^ \t\r\n\"']*/bootgen(?:\.bat|\.exe)[\"']?\s+",
)

CONTROLLED_VITIS_MARKERS = (
    r"env/tool/scripts/invoke-hdlvitis\.ps1\b",
    r"\binvoke-hdlvitis\.ps1\b",
    r"\bbuild-bootimage\.ps1\b",
)

FORBIDDEN_PARSER_COMMAND_PATTERNS = (
    r"\bmineru-open-api\b.*\bflash-extract\b",
    r"\bflash-extract\b.*\bmineru-open-api\b",
    r"\bmineru-open-api\b.*(?:^|\s)--mode\s+flash\b",
)

ILLEGAL_DOCPARSE_RECORD_PATTERNS = (
    r"work/docparse/parsed/mineru_extract/(?:parse_operation_record|operation_record|analysis_record|process_violation_record|violation_record)\.md\b",
)

ILLEGAL_AD_HOC_ARTIFACT_PATTERNS = (
    r"input/spec/(?:srs|acceptance_criteria|forbidden_designs|open_questions|requirements|module_plan|path_partition|decomposition_notes|design_blueprint)\.(?:ya?ml|json|md)\b",
    r"output/reports/design/reviewer_plan_review\.md\b",
)

ILLEGAL_PROVENANCE_RECORD_MARKERS = (
    r"\boperation_record\b",
    r"\bprocess_violation_record\b",
    r"\bviolation_record\b",
    r"\bmanual_review\b",
    r"\bdocparse_operation_log\b",
)


@dataclass(frozen=True)
class FrontdoorGuardResult:
    ok: bool
    reason: str
    touched_prefixes: tuple[str, ...] = ()


def require_frontdoor_ready(project_path: Path, action: str) -> FrontdoorGuardResult:
    """Require a passed DocParse gate manifest before formal outputs."""

    project = project_path.resolve()
    manifest = _latest_manifest(project, "work/docparse")
    if manifest:
        return FrontdoorGuardResult(True, f"{action}: DocParse gate manifest is present: {_project_rel(project, manifest)}")
    return FrontdoorGuardResult(
        False,
        (
            f"{action}: blocked because formal implementation artifacts require "
            "a passed DocParse gate manifest first; run requirements-frontdoor-check "
            "and python -m hdlflow.cli run-gate --node docparse before implementation output generation"
        ),
    )


def require_stage_ready(project_path: Path, stage: str, action: str) -> FrontdoorGuardResult:
    """Require the stage prerequisite manifest chain used by workflow entry points."""

    normalized = STAGE_ALIASES.get(stage.lower().replace("\\", "/"), stage.lower())
    if normalized == "docparse" or normalized == "loop1":
        return require_frontdoor_ready(project_path, action)
    if normalized == "loop2":
        return _require_manifest_chain(
            project_path,
            action,
            (
                ("work/docparse", "DocParse must pass before Loop1/Loop2 work"),
                ("work/loop1_rtl_tb", "Loop1 must pass before Loop2 work"),
            ),
        )
    if normalized == "loop3":
        return _require_manifest_chain(
            project_path,
            action,
            (
                ("work/docparse", "DocParse must pass before Loop3 work"),
                ("work/loop1_rtl_tb", "Loop1 must pass before Loop3 work"),
                ("work/loop2_uvm", "Loop2 must pass before Loop3 work"),
            ),
        )
    if normalized == "loop3-preflight":
        chain = require_stage_ready(project_path, "loop3", action)
        if not chain.ok:
            return chain
        project = project_path.resolve()
        report_checks = (
            ("output/reports/loop3/preflight/database_preflight.md", "result: PASS", "Loop3 database preflight"),
            ("output/reports/loop3/preflight/prototype_plan_check.md", "- result: PASS", "Loop3 prototype plan check"),
        )
        for rel, marker, label in report_checks:
            report = project / rel
            if not report.exists():
                return FrontdoorGuardResult(
                    False,
                    f"{action}: blocked because {label} is missing; run prototype-preflight and validate-prototype-plan first",
                )
            text = report.read_text(encoding="utf-8", errors="ignore")
            if marker not in text:
                return FrontdoorGuardResult(
                    False,
                    f"{action}: blocked because {label} has not passed; rerun the Loop3 preflight path first",
                )
        return FrontdoorGuardResult(True, f"{action}: Loop3 prerequisites and preflight reports are present")
    return FrontdoorGuardResult(False, f"{action}: unknown workflow stage guard: {stage}")


def evaluate_command_frontdoor_guard(project_path: Path, command: str) -> FrontdoorGuardResult:
    """Block write-like commands touching formal artifact roots before DocParse."""

    agent_role = _normalize_agent_role(os.environ.get("HDLFLOW_AGENT_ROLE"))
    if _uses_forbidden_parser_channel(command):
        return FrontdoorGuardResult(
            False,
            (
                "DocParse formal evidence must use MinerU high-precision API "
                "(/api/v4/extract/task or /api/v4/file-urls/batch); flash extraction is forbidden"
            ),
        )
    if _is_project_creation_bypass(command):
        return FrontdoorGuardResult(
            False,
            "project creation must use env/tool/scripts/New-HdlProject.ps1 or env/tool/scripts/new_hdl_project.py",
        )
    if _looks_like_write(command) and _writes_legacy_split_input(command):
        return FrontdoorGuardResult(
            False,
            "new projects use the single front-door input root input/spec; split input roots are forbidden",
        )
    if _uses_direct_vivado_without_wrapper(command):
        return FrontdoorGuardResult(
            False,
            (
                "Vivado must be launched through env/tool/scripts/Invoke-HdlVivado.ps1 so "
                "journal and log files stay under output/fpga/vivado/logs"
            ),
        )
    if _uses_direct_vitis_without_wrapper(command):
        return FrontdoorGuardResult(
            False,
            (
                "Vitis, XSCT, and bootgen must be launched through env/tool/scripts/Invoke-HdlVitis.ps1 "
                "or a generated Build-BootImage.ps1 wrapper after Loop3 preflight"
            ),
        )
    if _looks_like_write(command) and _writes_illegal_docparse_record(command):
        return FrontdoorGuardResult(
            False,
            "DocParse parsed evidence may contain parser outputs and provenance only; store operation notes under work/docparse/review or memory",
        )
    if _looks_like_write(command) and _writes_manual_record_link_into_provenance(command):
        return FrontdoorGuardResult(
            False,
            "parser provenance must describe parser evidence only; do not link operation, violation, or manual review records from provenance.yaml",
        )
    if _looks_like_write(command) and _writes_ad_hoc_artifact(command):
        return FrontdoorGuardResult(
            False,
            "DocParse and design outputs must be produced from front-door YAML and platform generators; do not create sidecar operation, violation, review-plan, or design-blueprint files",
        )
    if _looks_like_write(command) and _writes_design_report_directly(command):
        return FrontdoorGuardResult(
            False,
            "docset documents must be generated by python -m hdlflow.cli generate-docs after requirements-frontdoor-check passes",
        )
    if _looks_like_source_edit(command) and _writes_protected_gate_policy(command):
        return FrontdoorGuardResult(
            False,
            (
                "AI agents cannot automatically modify gate policy or guard "
                "conditions to make a project pass; record suspected gate issues "
                "under review or memory and handle gate maintenance as a separate "
                "explicit platform task with regression evidence"
            ),
        )
    if _looks_like_source_edit(command) and _writes_generated_rtl_skill_audit(command):
        return FrontdoorGuardResult(
            False,
            (
                "output/reports/loop1/rtl_skill_audit.md must be generated by "
                "`python -m hdlflow.cli rtl-skill-audit --project <project>`; "
                "do not hand-edit RTL skill audit evidence"
            ),
        )
    if _looks_like_write(command) and _writes_project_frontdoor_populate_script(command):
        script_gate = require_frontdoor_sources_instead_of_populate_script(project_path)
        if not script_gate.ok:
            return script_gate
    if _looks_like_write(command) and _writes_generated_fpga_output(command) and not _is_official_generated_fpga_command(command):
        return FrontdoorGuardResult(
            False,
            (
                "generated FPGA artifacts under output/fpga must be regenerated by "
                "the platform generators or tool wrappers; do not hand-edit generated "
                "XDC, BD Tcl, Vitis, boot, or bitstream artifacts"
            ),
        )
    if _looks_like_write(command):
        stage_gate = _controlled_command_stage_gate(project_path, command)
        if not stage_gate.ok:
            return stage_gate
    if _looks_like_write(command) and _writes_frontdoor_source(command):
        change_gate = require_change_request_before_frontdoor_source_write(project_path)
        if not change_gate.ok and not _is_controlled_frontdoor_flow_command(command):
            return change_gate
    if _looks_like_write(command) and _writes_prototype_change_source(command):
        prototype_gate = require_change_request_before_prototype_change(project_path)
        if not prototype_gate.ok and not _is_controlled_prototype_command(command):
            return prototype_gate
    if _looks_like_source_edit(command):
        formal_change_gate = require_change_request_before_formal_requirement_change(project_path, command)
        if not formal_change_gate.ok:
            return formal_change_gate
    if not command or _is_controlled_frontdoor_flow_command(command):
        return FrontdoorGuardResult(True, "no formal implementation output write detected")
    if not _looks_like_write(command):
        return FrontdoorGuardResult(True, "read-only command or no write intent detected")

    controlled = _controlled_prefixes_in_text(command)
    if agent_role and controlled:
        disallowed = tuple(prefix for prefix in controlled if not _agent_can_write(agent_role, prefix))
        if disallowed:
            allowed = ", ".join(AGENT_WRITE_PREFIXES.get(agent_role, ()))
            return FrontdoorGuardResult(
                False,
                (
                    f"agent role {agent_role} cannot write: {', '.join(disallowed)}; "
                    f"allowed write roots: {allowed or 'none'}"
                ),
                disallowed,
            )

    touched = _formal_prefixes_in_text(command)
    if not touched:
        return FrontdoorGuardResult(True, "write command does not touch formal implementation outputs")

    base = require_frontdoor_ready(project_path, "pre-tool guard")
    if base.ok:
        return FrontdoorGuardResult(True, base.reason, touched)
    return FrontdoorGuardResult(False, base.reason, touched)


def require_change_request_before_frontdoor_source_write(project_path: Path) -> FrontdoorGuardResult:
    """Require an active change request before changing front-door sources after baseline."""

    project = project_path.resolve()
    if not _has_frontdoor_baseline(project):
        return FrontdoorGuardResult(True, "initial front-door source write before baseline")
    if _has_active_change_request(project):
        return FrontdoorGuardResult(True, "front-door source write is bound to an active change request")
    return FrontdoorGuardResult(
        False,
        (
            "front-door source changes after a gate baseline require change control first; "
            "run python -m hdlflow.cli change-open, then record impact/approval before "
            "rerunning requirements-frontdoor-check, generate-docs, and the DocParse gate"
        ),
    )


def require_change_request_before_prototype_change(project_path: Path) -> FrontdoorGuardResult:
    """Require the front-door change sequence before prototype verification changes."""

    project = project_path.resolve()
    if not _has_frontdoor_baseline(project):
        return FrontdoorGuardResult(True, "prototype change before baseline")
    approved_request = _latest_complete_approved_change_request(project)
    if approved_request is None:
        return FrontdoorGuardResult(
            False,
            (
                "prototype verification requirement changes after a gate baseline require "
                "a complete approved front-door change first; run python -m hdlflow.cli "
                "change-open, change-impact, and change-approve, and record changed "
                "requirements, artifacts, and verification before Loop3 or FPGA edits"
            ),
        )
    frontdoor_ready, frontdoor_reason = _has_post_change_frontdoor_and_design_doc(
        project,
        approved_request,
        scope="prototype verification changes",
        required_sections=("verification_plan", "delivery_package"),
    )
    if not frontdoor_ready:
        return FrontdoorGuardResult(False, frontdoor_reason)
    return FrontdoorGuardResult(
        True,
        "prototype change is bound to an approved front-door change with regenerated docset",
    )


def require_change_request_before_formal_requirement_change(project_path: Path, command: str) -> FrontdoorGuardResult:
    """Require a recorded change sequence before post-baseline RTL/TB/UVM edits."""

    project = project_path.resolve()
    for rule in _formal_requirement_change_rules_for_command(command):
        node = str(rule["node"])
        if not _has_node_baseline(project, node):
            continue
        scope = str(rule["scope"])
        approved_request = _latest_complete_approved_change_request(project)
        if approved_request is None:
            return FrontdoorGuardResult(
                False,
                (
                    f"{scope} after a {node} gate baseline require a complete approved "
                    "front-door change first; run python -m hdlflow.cli change-open, "
                    "change-impact, and change-approve, and record changed requirements, "
                    "artifacts, and verification before editing formal sources"
                ),
            )
        ready, reason = _has_post_change_frontdoor_and_design_doc(
            project,
            approved_request,
            scope=scope,
            required_sections=tuple(rule["required_sections"]),
        )
        if not ready:
            return FrontdoorGuardResult(False, reason)
    return FrontdoorGuardResult(True, "formal source edit is before baseline or bound to a complete approved change")


def require_frontdoor_sources_instead_of_populate_script(project_path: Path) -> FrontdoorGuardResult:
    """Prevent project requirement changes from being hidden in populate scripts."""

    project = project_path.resolve()
    if not _has_frontdoor_baseline(project):
        return FrontdoorGuardResult(True, "front-door populate script write before baseline")
    return FrontdoorGuardResult(
        False,
        (
            "project requirement changes after a gate baseline must update the "
            "front-door source artifacts first; do not modify populate/front-door "
            "helper scripts to implement project-specific requirements"
        ),
    )


def _has_docparse_manifest(project: Path) -> bool:
    return _latest_manifest(project, "work/docparse") is not None


def _has_frontdoor_baseline(project: Path) -> bool:
    manifest_dir = project_memory_path(project) / "recovery" / "rollback_manifests"
    return (
        any(manifest_dir.glob("input_*.json"))
        or any(manifest_dir.glob("work_docparse_*.json"))
    )


def _has_node_baseline(project: Path, node: str) -> bool:
    return _latest_manifest(project, node) is not None


def _has_active_change_request(project: Path) -> bool:
    return _latest_change_request_with_status(project, ACTIVE_CHANGE_STATUSES) is not None


def _latest_change_request_with_status(project: Path, statuses: set[str]) -> Path | None:
    requests_dir = project / "work/change" / "requests"
    matches: list[Path] = []
    for request in requests_dir.glob("CR-*.md"):
        text = request.read_text(encoding="utf-8", errors="ignore").lower()
        match = re.search(r"^\s*-\s*status:\s*([a-z_]+)\b", text, flags=re.MULTILINE)
        if match and match.group(1) in statuses:
            matches.append(request)
    if not matches:
        return None
    return max(matches, key=lambda path: path.stat().st_mtime)


def _latest_complete_approved_change_request(project: Path) -> Path | None:
    requests_dir = project / "work/change" / "requests"
    matches: list[Path] = []
    for request in requests_dir.glob("CR-*.md"):
        text = request.read_text(encoding="utf-8", errors="ignore").lower()
        match = re.search(r"^\s*-\s*status:\s*([a-z_]+)\b", text, flags=re.MULTILINE)
        if not match or match.group(1) not in APPROVED_CHANGE_STATUSES:
            continue
        change_id = _change_id_from_request(request)
        if not _change_records_describe_delta(project, change_id):
            continue
        matches.append(request)
    if not matches:
        return None
    return max(matches, key=lambda path: path.stat().st_mtime)


def _change_id_from_request(request: Path) -> str:
    text = request.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"^\s*-\s*id:\s*([A-Za-z0-9_-]+)\b", text, flags=re.MULTILINE)
    return match.group(1) if match else request.stem


def _change_records_describe_delta(project: Path, change_id: str) -> bool:
    impact = project / "work/change" / "impact_analysis" / f"{change_id}.md"
    approval = project / "work/change" / "approvals" / f"{change_id}.md"
    if not impact.exists() or not approval.exists():
        return False
    text = impact.read_text(encoding="utf-8", errors="ignore")
    required_sections = ("## Requirements", "## Artifacts", "## Required Verification")
    if not all(section in text for section in required_sections):
        return False
    if "## Docset Decision" not in text:
        return False
    if re.search(r"(?mi)^\s*-\s+.*(?:REQ-IMPACT-TBD|ARTIFACT-IMPACT-TBD)", text):
        return False
    return re.search(r"(?m)^\s*-\s+\S", text) is not None


def _has_post_change_frontdoor_and_design_doc(
    project: Path,
    approved_request: Path,
    *,
    scope: str,
    required_sections: tuple[str, ...],
) -> tuple[bool, str]:
    request_mtime = approved_request.stat().st_mtime

    report = project / "output" / "reports" / "docparse" / "requirements_frontend_check.md"
    if not report.exists():
        return (
            False,
            (
                f"{scope} must reopen the requirements front door first; "
                "run requirements-frontdoor-check after the approved change before formal source edits"
            ),
        )
    report_text = report.read_text(encoding="utf-8", errors="ignore").lower()
    if not re.search(r"(?:^|\n)\s*-?\s*result:\s*pass\b", report_text):
        return (
            False,
            f"{scope} require requirements-frontdoor-check PASS before formal source edits",
        )
    if report.stat().st_mtime < request_mtime:
        return (
            False,
            (
                f"{scope} require requirements-frontdoor-check to be rerun "
                "after the approved change before formal source edits"
            ),
        )

    docset_manifest = project / "output" / "docs" / "manifests" / "docset_manifest.json"
    doc_paths = [
        project / "output" / "docs" / "application" / "application_guide.md",
        project / "output" / "docs" / "design" / "microarchitecture_spec.md",
        project / "output" / "docs" / "test" / "verification_plan.md",
        project / "output" / "docs" / "delivery" / "delivery_package.md",
    ]
    if not docset_manifest.exists() or not all(path.exists() for path in doc_paths):
        return (
            False,
            (
                f"{scope} require regenerating the docset with "
                "python -m hdlflow.cli generate-docs before formal source edits"
            ),
        )
    if docset_manifest.stat().st_mtime < request_mtime or any(path.stat().st_mtime < request_mtime for path in doc_paths):
        return (
            False,
            (
                f"{scope} require generate-docs to be rerun "
                "after the approved change before formal source edits"
            ),
        )
    try:
        manifest = json.loads(docset_manifest.read_text(encoding="utf-8"))
    except Exception:
        return (
            False,
            f"{scope} require a valid docset_manifest.json before formal source edits",
        )
    documents = {str(item.get("doc_type")) for item in manifest.get("documents", []) if isinstance(item, dict)}
    missing_docs = sorted(set(required_sections) - documents)
    if missing_docs:
        return (
            False,
            f"{scope} require generated document(s): {', '.join(missing_docs)}",
        )
    return True, "front-door and generated docset are current for the approved change"


def _is_controlled_frontdoor_flow_command(command: str) -> bool:
    normalized = command.lower()
    patterns = FRONTDOOR_COMMAND_PATTERNS + CHANGE_CONTROL_COMMAND_PATTERNS + FRONTDOOR_GENERATOR_COMMAND_PATTERNS
    return any(re.search(pattern, normalized) for pattern in patterns)


def _is_controlled_prototype_command(command: str) -> bool:
    normalized = command.lower()
    return any(re.search(pattern, normalized) for pattern in CONTROLLED_PROTOTYPE_COMMAND_PATTERNS)


def _controlled_command_stage_gate(project_path: Path, command: str) -> FrontdoorGuardResult:
    normalized = _normalize_text_paths(command)
    if _modelsim_loop(normalized) == "loop1" or "loop1-refresh-reports" in normalized or "loop1-waveform-gate" in normalized:
        return require_stage_ready(project_path, "loop1", "Loop1 tool entry")
    if (
        _modelsim_loop(normalized) == "loop2"
        or "loop2-refresh-reports" in normalized
        or "loop2-build-bindings" in normalized
        or "loop2-database-preflight" in normalized
    ):
        return require_stage_ready(project_path, "loop2", "Loop2 tool entry")
    if "prototype-preflight" in normalized or "validate-prototype-plan" in normalized:
        return require_stage_ready(project_path, "loop3", "Loop3 preflight entry")
    if (
        "generate-xdc" in normalized
        or "generate-ps-pl-bd" in normalized
        or "generate-vitis-boot" in normalized
        or "invoke-hdlvivado.ps1" in normalized
        or "invoke-hdlvitis.ps1" in normalized
        or "build-bootimage.ps1" in normalized
    ):
        return require_stage_ready(project_path, "loop3-preflight", "Loop3 generation/tool entry")
    return FrontdoorGuardResult(True, "no workflow stage entry detected")


def _modelsim_loop(normalized_command: str) -> str:
    if "invoke-hdlmodelsim.ps1" not in normalized_command:
        return ""
    if re.search(r"(?:^|\s)-loop\s+loop1\b", normalized_command) or re.search(r"\bloop1\b", normalized_command):
        return "loop1"
    if re.search(r"(?:^|\s)-loop\s+loop2\b", normalized_command) or re.search(r"\bloop2\b", normalized_command):
        return "loop2"
    return ""


def _is_project_creation_bypass(command: str) -> bool:
    if not command:
        return False
    normalized = _normalize_text_paths(command)
    if any(re.search(pattern, normalized) for pattern in OFFICIAL_PROJECT_CREATE_PATTERNS):
        return False
    return any(re.search(pattern, normalized) for pattern in PROJECT_CREATE_BYPASS_PATTERNS)


def _uses_forbidden_parser_channel(command: str) -> bool:
    if not command:
        return False
    normalized = _normalize_text_paths(command)
    return any(re.search(pattern, normalized) for pattern in FORBIDDEN_PARSER_COMMAND_PATTERNS)


def _uses_direct_vivado_without_wrapper(command: str) -> bool:
    if not command:
        return False
    normalized = _normalize_text_paths(command)
    if any(re.search(pattern, normalized) for pattern in CONTROLLED_VIVADO_MARKERS):
        return False
    return any(re.search(pattern, normalized, flags=re.DOTALL) for pattern in DIRECT_VIVADO_COMMAND_PATTERNS)


def _uses_direct_vitis_without_wrapper(command: str) -> bool:
    if not command:
        return False
    normalized = _normalize_text_paths(command)
    if any(re.search(pattern, normalized) for pattern in CONTROLLED_VITIS_MARKERS):
        return False
    return any(re.search(pattern, normalized, flags=re.DOTALL) for pattern in DIRECT_VITIS_COMMAND_PATTERNS)


def _writes_illegal_docparse_record(command: str) -> bool:
    if not command:
        return False
    normalized = _normalize_text_paths(command)
    return any(re.search(pattern, normalized) for pattern in ILLEGAL_DOCPARSE_RECORD_PATTERNS)


def _writes_ad_hoc_artifact(command: str) -> bool:
    if not command:
        return False
    normalized = _normalize_text_paths(command)
    return any(re.search(pattern, normalized) for pattern in ILLEGAL_AD_HOC_ARTIFACT_PATTERNS)


def _writes_legacy_split_input(command: str) -> bool:
    if not command:
        return False
    normalized = _normalize_text_paths(command)
    return any(prefix in normalized for prefix in LEGACY_SPLIT_INPUT_PREFIXES)


def _writes_frontdoor_source(command: str) -> bool:
    if not command:
        return False
    normalized = _normalize_text_paths(command)
    return any(prefix in normalized for prefix in FRONTDOOR_SOURCE_PREFIXES)


def _writes_prototype_change_source(command: str) -> bool:
    if not command:
        return False
    normalized = _normalize_text_paths(command)
    return any(prefix in normalized for prefix in PROTOTYPE_CHANGE_PREFIXES)


def _writes_generated_fpga_output(command: str) -> bool:
    if not command:
        return False
    normalized = _normalize_text_paths(command)
    return any(prefix in normalized for prefix in GENERATED_FPGA_OUTPUT_PREFIXES)


def _is_official_generated_fpga_command(command: str) -> bool:
    if not command:
        return False
    normalized = _normalize_text_paths(command)
    return any(re.search(pattern, normalized) for pattern in OFFICIAL_GENERATED_FPGA_COMMAND_PATTERNS)


def _writes_protected_gate_policy(command: str) -> bool:
    if not command:
        return False
    normalized = _normalize_text_paths(command)
    return any(prefix in normalized for prefix in PROTECTED_GATE_POLICY_PREFIXES)


def _writes_project_frontdoor_populate_script(command: str) -> bool:
    if not command:
        return False
    normalized = _normalize_text_paths(command)
    return any(re.search(pattern, normalized) for pattern in PROJECT_FRONTDOOR_POPULATE_SCRIPT_PATTERNS)


def _writes_manual_record_link_into_provenance(command: str) -> bool:
    if not command:
        return False
    normalized = _normalize_text_paths(command)
    if "work/docparse/parsed/mineru_extract/provenance.yaml" not in normalized:
        return False
    return any(re.search(pattern, normalized) for pattern in ILLEGAL_PROVENANCE_RECORD_MARKERS)


def _writes_design_report_directly(command: str) -> bool:
    if not command:
        return False
    normalized = _normalize_text_paths(command)
    if DESIGN_REPORT_PREFIX not in normalized:
        return False
    return not re.search(r"\b(?:generate-docs|generate-application-doc|generate-uarch-doc|generate-verification-doc|generate-delivery-doc)\b", normalized)


def _looks_like_write(command: str) -> bool:
    normalized = command.lower()
    return any(re.search(pattern, normalized) for pattern in WRITE_INTENT_PATTERNS)


def _looks_like_source_edit(command: str) -> bool:
    normalized = command.lower()
    return any(re.search(pattern, normalized) for pattern in SOURCE_EDIT_INTENT_PATTERNS)


def _normalize_agent_role(role: str | None) -> str | None:
    if not role:
        return None
    normalized = role.strip().lower().replace("-", "_").replace(" ", "_")
    normalized = AGENT_ALIASES.get(normalized, normalized)
    return normalized if normalized in AGENT_WRITE_PREFIXES else None


def _agent_can_write(role: str, prefix: str) -> bool:
    return any(prefix == allowed or prefix.startswith(f"{allowed}/") for allowed in AGENT_WRITE_PREFIXES.get(role, ()))


def _controlled_prefixes_in_text(text: str) -> tuple[str, ...]:
    normalized = _normalize_text_paths(text)
    hits: list[str] = []
    for prefix in CONTROLLED_PREFIXES:
        if prefix in normalized:
            hits.append(prefix)
    return tuple(hits)


def _formal_prefixes_in_text(text: str) -> tuple[str, ...]:
    normalized = _normalize_text_paths(text)
    hits: list[str] = []
    for prefix in FORMAL_IMPLEMENTATION_PREFIXES:
        if prefix in normalized:
            hits.append(prefix)
    return tuple(hits)


def _formal_requirement_change_rules_for_command(command: str) -> tuple[dict[str, object], ...]:
    normalized = _normalize_text_paths(command)
    matches: list[dict[str, object]] = []
    for rule in FORMAL_REQUIREMENT_CHANGE_RULES:
        prefixes = rule["prefixes"]
        if any(prefix in normalized for prefix in prefixes):
            matches.append(rule)
    return tuple(matches)


def _writes_generated_rtl_skill_audit(command: str) -> bool:
    normalized = _normalize_text_paths(command)
    if "rtl-skill-audit" in normalized:
        return False
    return "output/reports/loop1/rtl_skill_audit.md" in normalized


def _normalize_text_paths(text: str) -> str:
    normalized = text.lower().replace("\\", "/")
    normalized = re.sub(r"/+", "/", normalized)
    return normalized


def _require_manifest_chain(
    project_path: Path,
    action: str,
    required: tuple[tuple[str, str], ...],
) -> FrontdoorGuardResult:
    project = project_path.resolve()
    missing: list[str] = []
    present: list[str] = []
    for node, detail in required:
        manifest = _latest_manifest(project, node)
        if manifest:
            present.append(f"{node}={_project_rel(project, manifest)}")
        else:
            missing.append(detail)
    if missing:
        return FrontdoorGuardResult(False, f"{action}: blocked because " + "; ".join(missing))
    return FrontdoorGuardResult(True, f"{action}: prerequisite gate manifests are present: " + ", ".join(present))


def _latest_manifest(project: Path, node: str) -> Path | None:
    manifest_dir = project_memory_path(project) / "recovery" / "rollback_manifests"
    if not manifest_dir.exists():
        return None
    normalized = node.replace("\\", "/")
    stems = NODE_MANIFEST_STEMS.get(normalized, (normalized.replace("/", "_"),))
    matches: list[Path] = []
    for stem in stems:
        matches.extend(manifest_dir.glob(f"{stem}_*.json"))
    if not matches:
        return None
    return sorted(set(matches))[-1]


def _project_rel(project: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")
