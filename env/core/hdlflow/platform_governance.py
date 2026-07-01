"""Platform change governance checks and migration helpers."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .layout import PROJECT_SCAFFOLD_ROOT
from .simple_yaml import load_yaml


DEFAULT_PLATFORM_CONTRACT_VERSION = "2026.06-contract-v2"
PLATFORM_GOVERNANCE_REL = Path("env/rule/platform_governance")
PLATFORM_CONTRACT_REL = PLATFORM_GOVERNANCE_REL / "platform_contract.yaml"
PCR_REL = PLATFORM_GOVERNANCE_REL / "platform_change_request.yaml"
IMPACT_MATRIX_REL = PLATFORM_GOVERNANCE_REL / "impact_matrix.yaml"
MIGRATION_MANIFEST_REL = PLATFORM_GOVERNANCE_REL / "migration_manifest.yaml"
REGRESSION_MANIFEST_REL = PLATFORM_GOVERNANCE_REL / "regression_manifest.yaml"
AUDIT_REPORT_REL = PLATFORM_GOVERNANCE_REL / "platform_change_audit_report.md"

FRONTDOOR_REL = Path("work/docparse/frontdoor")
PROJECT_MIGRATION_REL = Path("work/migration")

ALLOWED_PCR_STATUSES = {
    "ready_for_regression",
    "ready_for_arbtr",
    "accepted",
    "accepted_with_waiver",
}
ALLOWED_ARBTR_DECISIONS = {
    "ACCEPT",
    "ACCEPT_WITH_WAIVER",
    "REWORK_REQUIRED",
    "REJECT",
    "CLAIM_DOWNGRADE_REQUIRED",
}
PASS_STATUSES = {"pass", "passed", "done", "complete", "completed"}

CHANGE_TYPE_COMPONENTS = {
    "skill_update": "skills",
    "template_update": "templates",
    "schema_update": "schemas",
    "gate_update": "gates",
    "report_generator_update": "report_generators",
    "parser_update": "parsers",
    "cli_update": "cli_commands",
    "migration_update": "migrations",
    "regression_update": "tests",
    "rule_update": "rules",
    "arbtr_update": "arbtr_review",
}

MATRIX_ALIASES = {
    "arbtr_review": {"arbtr_review", "arbtr"},
    "cli_commands": {"cli", "cli_commands"},
    "core_modules": {"core_engine", "core_modules"},
    "docs": {"docs", "user_docs"},
    "fpga_prototype": {"fpga_prototype", "prototype"},
    "gates": {"gates"},
    "migrations": {"migration", "migrations"},
    "parsers": {"parser", "parsers", "vcd_analysis"},
    "platform_governance": {"platform_governance", "pcr"},
    "regression": {"regression", "fixtures"},
    "report_generators": {"report_generator", "report_generators", "reports"},
    "requirements_planning": {"requirements_planning", "frontdoor"},
    "rules": {"rules"},
    "schemas": {"schema", "schemas"},
    "skills": {"skill", "skills"},
    "templates": {"template", "templates"},
    "tests": {"tests", "regression"},
    "tool_scripts": {"tool_scripts", "cli"},
    "uvm": {"uvm"},
    "vcd_analysis": {"vcd_analysis", "parser"},
    "directed_tb": {"directed_tb", "tb"},
}


@dataclass(frozen=True)
class PlatformGovernanceCheck:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class PlatformGovernanceResult:
    ok: bool
    report_path: Path
    checks: tuple[PlatformGovernanceCheck, ...]
    changed_files: tuple[str, ...]
    actual_components: tuple[str, ...]
    actual_stages: tuple[str, ...]
    required_fixtures: tuple[str, ...]


@dataclass(frozen=True)
class ProjectMigrationResult:
    ok: bool
    manifest_path: Path
    report_path: Path
    updated: tuple[Path, ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]


def run_platform_regression(
    workspace: Path,
    *,
    all_checks: bool = False,
    changed_files: list[str] | tuple[str, ...] | None = None,
    write_report: bool = True,
    run_tests: bool = False,
) -> PlatformGovernanceResult:
    """Run the platform-level PCR, impact, migration, and fixture checks."""

    workspace = workspace.resolve()
    normalized_files = tuple(_normalize_changed_file(path) for path in (changed_files or _git_changed_files(workspace)))
    normalized_files = tuple(path for path in normalized_files if path.startswith("env/"))

    actual_components, actual_stages, required_fixtures = _classify_changed_files(normalized_files)
    pcr = _load_governance_mapping(workspace, PCR_REL, "platform_change_request")
    impact = _load_governance_mapping(workspace, IMPACT_MATRIX_REL, "impact_matrix")
    migration = _load_governance_mapping(workspace, MIGRATION_MANIFEST_REL, "migration_manifest")
    regression = _load_governance_mapping(workspace, REGRESSION_MANIFEST_REL, "regression_manifest")
    contract = _load_governance_mapping(workspace, PLATFORM_CONTRACT_REL, "platform_contract")

    checks = [
        _platform_pcr_gate(pcr, impact, regression),
        _reduced_scope_policy_gate(workspace),
        _impact_completeness_gate(pcr, impact, actual_components, actual_stages, normalized_files),
        _template_schema_gate(pcr, actual_components),
        _regression_coverage_gate(regression, required_fixtures, all_checks=all_checks),
        _migration_readiness_gate(migration, contract, pcr, actual_components, actual_stages),
        _arbtr_platform_review_gate(pcr),
    ]
    if run_tests:
        checks.append(_platform_regression_command_gate(workspace, regression))
    ok = all(check.status != "FAIL" for check in checks)
    report_path = workspace / AUDIT_REPORT_REL
    result = PlatformGovernanceResult(
        ok=ok,
        report_path=report_path,
        checks=tuple(checks),
        changed_files=tuple(sorted(normalized_files)),
        actual_components=tuple(sorted(actual_components)),
        actual_stages=tuple(sorted(actual_stages)),
        required_fixtures=tuple(sorted(required_fixtures)),
    )
    if write_report:
        _write_platform_audit_report(result, pcr)
    return result


def migrate_project_to_contract(
    workspace: Path,
    project: Path,
    *,
    to_contract: str = DEFAULT_PLATFORM_CONTRACT_VERSION,
    dry_run: bool = False,
) -> ProjectMigrationResult:
    """Bring an older project up to the current frontdoor governance scaffold."""

    workspace = workspace.resolve()
    project = project.resolve()
    scaffold = workspace / PROJECT_SCAFFOLD_ROOT
    updated: list[Path] = []
    warnings: list[str] = []
    errors: list[str] = []

    if not project.exists():
        return ProjectMigrationResult(
            ok=False,
            manifest_path=project / PROJECT_MIGRATION_REL / "migration_manifest.yaml",
            report_path=project / PROJECT_MIGRATION_REL / "migration_report.md",
            updated=(),
            warnings=(),
            errors=(f"project does not exist: {project}",),
        )
    if not scaffold.is_dir():
        return ProjectMigrationResult(
            ok=False,
            manifest_path=project / PROJECT_MIGRATION_REL / "migration_manifest.yaml",
            report_path=project / PROJECT_MIGRATION_REL / "migration_report.md",
            updated=(),
            warnings=(),
            errors=(f"missing scaffold directory: {scaffold}",),
        )

    rels_to_copy = [
        "work/docparse/frontdoor/contract.yaml",
        "work/docparse/frontdoor/README.md",
        "work/docparse/frontdoor/baseline/srs.yaml",
        "work/docparse/frontdoor/baseline/acceptance_criteria.yaml",
        "work/docparse/frontdoor/baseline/design_intent.yaml",
        "work/docparse/frontdoor/baseline/verification_intent.yaml",
        "work/docparse/frontdoor/baseline/prototype_intent.yaml",
        "work/docparse/frontdoor/baseline/forbidden_designs.yaml",
        "work/docparse/frontdoor/templates/new_requirement.template.yaml",
        "work/docparse/frontdoor/templates/requirement_change.template.yaml",
        "work/docparse/frontdoor/templates/architecture_supplement.template.yaml",
        "work/docparse/frontdoor/templates/verification_supplement.template.yaml",
        "work/docparse/frontdoor/templates/prototype_supplement.template.yaml",
        "work/docparse/frontdoor/generated/active_srs.generated.yaml",
        "work/docparse/frontdoor/generated/active_design_intent.generated.yaml",
        "work/docparse/frontdoor/generated/active_verification_intent.generated.yaml",
        "work/docparse/frontdoor/generated/active_prototype_intent.generated.yaml",
        "work/docparse/frontdoor/generated/active_trace_matrix.generated.yaml",
        "work/docparse/verification/uvm_plan.yaml",
        "work/docparse/trace_matrix/req_to_uvm_intent.yaml",
        "work/gates/claim_policy.yaml",
    ]
    required_dirs = [
        "work/docparse/frontdoor/intake/pending",
        "work/docparse/frontdoor/intake/approved",
        "work/docparse/frontdoor/intake/rejected",
        "work/docparse/frontdoor/intake/merged",
        "work/docparse/frontdoor/history/baseline_snapshots",
        "work/docparse/frontdoor/history/merged_intake",
        "work/docparse/frontdoor/history/rejected_intake",
        "work/migration",
    ]

    for rel in required_dirs:
        path = project / rel
        if dry_run:
            updated.append(path)
        else:
            path.mkdir(parents=True, exist_ok=True)
            updated.append(path)

    for rel in rels_to_copy:
        src = scaffold / rel
        dst = project / rel
        if not src.is_file():
            warnings.append(f"missing scaffold migration source: {rel}")
            continue
        if dst.exists():
            continue
        if dry_run:
            updated.append(dst)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8").replace("change_me", project.name)
        dst.write_text(text, encoding="utf-8")
        updated.append(dst)

    if not dry_run:
        _archive_legacy_open_questions(project, updated)
        _ensure_contract_marks_legacy_inactive(project, to_contract, updated)

    manifest_path = project / PROJECT_MIGRATION_REL / "migration_manifest.yaml"
    report_path = project / PROJECT_MIGRATION_REL / "migration_report.md"
    if not dry_run:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_text = "\n".join(
            [
                "schema_version: 1",
                f"project: {project.name}",
                f"to_contract: {to_contract}",
                "status: complete",
                "legacy_frontdoor_policy: archived_and_quarantined",
                "created_artifacts:",
                *[f"  - {_relpath(project, path)}" for path in updated],
                "",
            ]
        )
        manifest_path.write_text(manifest_text, encoding="utf-8")
        report_path.write_text(
            "\n".join(
                [
                    "# Project Migration Report",
                    "",
                    f"- project: {project.name}",
                    f"- to_contract: {to_contract}",
                    "- status: complete",
                    "- legacy_open_questions: archived when present",
                    "",
                    "## Updated Artifacts",
                    *[f"- {_relpath(project, path)}" for path in updated],
                    "",
                ]
            ),
            encoding="utf-8",
        )
        updated.extend([manifest_path, report_path])

    return ProjectMigrationResult(
        ok=not errors,
        manifest_path=manifest_path,
        report_path=report_path,
        updated=tuple(updated),
        warnings=tuple(warnings),
        errors=tuple(errors),
    )


def _platform_pcr_gate(
    pcr: dict[str, Any],
    impact: dict[str, Any],
    regression: dict[str, Any],
) -> PlatformGovernanceCheck:
    missing = [
        key
        for key in (
            "id",
            "title",
            "status",
            "change_type",
            "affected_stages",
            "affected_components",
            "acceptance_criteria",
            "required_regression_fixtures",
            "arbtr_review",
        )
        if not _non_empty(pcr.get(key))
    ]
    if missing:
        return PlatformGovernanceCheck("platform_pcr_gate", "FAIL", "missing PCR field(s): " + ", ".join(missing))
    status = str(pcr.get("status", "")).strip()
    if status not in ALLOWED_PCR_STATUSES:
        return PlatformGovernanceCheck("platform_pcr_gate", "FAIL", f"PCR status must be post-draft: {status or '<empty>'}")
    pcr_id = str(pcr.get("id", "")).strip()
    mismatches = []
    if impact.get("pcr_id") not in (None, pcr_id):
        mismatches.append(f"impact_matrix.pcr_id={impact.get('pcr_id')}")
    if regression.get("pcr_id") not in (None, pcr_id):
        mismatches.append(f"regression_manifest.pcr_id={regression.get('pcr_id')}")
    if mismatches:
        return PlatformGovernanceCheck("platform_pcr_gate", "FAIL", "PCR ID mismatch: " + ", ".join(mismatches))
    return PlatformGovernanceCheck("platform_pcr_gate", "PASS", f"PCR {pcr_id} is complete and post-draft")


def _reduced_scope_policy_gate(workspace: Path) -> PlatformGovernanceCheck:
    banned = [
        "smo" + "ke",
        "\u70df\u6d4b",
        "san" + "ity run",
        "quick " + "check",
        "quick_" + "check",
        "quick-" + "check",
        "mi" + "ni_" + "pass_project",
        "mi" + "ni_" + "project",
    ]
    scanned_suffixes = {".do", ".json", ".md", ".py", ".sv", ".svh", ".tcl", ".template", ".txt", ".yaml", ".yml"}
    roots = [workspace / "README.md", workspace / "env"]
    hits: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        paths = [root] if root.is_file() else root.rglob("*")
        for path in paths:
            if not path.is_file() or path.suffix.lower() not in scanned_suffixes:
                continue
            if any(part in {"__pycache__", ".pytest_cache"} for part in path.parts):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for term in banned:
                if term in text:
                    hits.append(_relpath(workspace, path))
                    break
    if hits:
        return PlatformGovernanceCheck(
            "reduced_scope_policy_gate",
            "FAIL",
            "formal platform files contain reduced-scope validation language: " + ", ".join(sorted(set(hits))[:12]),
        )
    return PlatformGovernanceCheck("reduced_scope_policy_gate", "PASS", "formal platform files use full-contract validation language")


def _impact_completeness_gate(
    pcr: dict[str, Any],
    impact: dict[str, Any],
    actual_components: set[str],
    actual_stages: set[str],
    changed_files: tuple[str, ...],
) -> PlatformGovernanceCheck:
    if not changed_files:
        return PlatformGovernanceCheck("impact_completeness_gate", "PASS", "no env platform changes detected")
    declared_components = _declared_components(pcr)
    declared_stages = {str(item).strip() for item in _as_list(pcr.get("affected_stages")) if str(item).strip()}
    missing_components = sorted(actual_components - declared_components)
    missing_stages = sorted(actual_stages - declared_stages)
    matrix_missing = _matrix_missing_units(impact, actual_components | actual_stages)
    if missing_components or missing_stages or matrix_missing:
        parts = []
        if missing_components:
            parts.append("undeclared component(s): " + ", ".join(missing_components))
        if missing_stages:
            parts.append("undeclared stage(s): " + ", ".join(missing_stages))
        if matrix_missing:
            parts.append("missing impact matrix coverage: " + ", ".join(matrix_missing))
        return PlatformGovernanceCheck("impact_completeness_gate", "FAIL", "; ".join(parts))
    return PlatformGovernanceCheck(
        "impact_completeness_gate",
        "PASS",
        f"{len(changed_files)} changed env file(s) are covered by PCR and impact matrix",
    )


def _template_schema_gate(pcr: dict[str, Any], actual_components: set[str]) -> PlatformGovernanceCheck:
    if not ({"templates", "schemas", "requirements_planning"} & actual_components):
        return PlatformGovernanceCheck("template_schema_gate", "PASS", "no template/schema/platform contract change detected")
    declared = _declared_components(pcr)
    if "templates" not in declared or "schemas" not in declared:
        return PlatformGovernanceCheck(
            "template_schema_gate",
            "FAIL",
            "template or frontdoor contract changes must declare both templates and schemas in affected_components/change_type",
        )
    return PlatformGovernanceCheck("template_schema_gate", "PASS", "template/schema coupling is declared")


def _regression_coverage_gate(
    regression: dict[str, Any],
    required_fixtures: set[str],
    *,
    all_checks: bool,
) -> PlatformGovernanceCheck:
    fixtures = regression.get("fixtures")
    if not isinstance(fixtures, list):
        return PlatformGovernanceCheck("regression_coverage_gate", "FAIL", "regression_manifest fixtures must be a list")
    fixture_by_name = {
        str(item.get("name")): item
        for item in fixtures
        if isinstance(item, dict) and item.get("name") is not None
    }
    missing = sorted(required_fixtures - set(fixture_by_name))
    not_passed = sorted(
        name
        for name in required_fixtures
        if name in fixture_by_name and str(fixture_by_name[name].get("status", "")).strip().lower() not in PASS_STATUSES
    )
    command = str(regression.get("command", "")).strip()
    if all_checks and not command:
        return PlatformGovernanceCheck("regression_coverage_gate", "FAIL", "regression_manifest command is required for --all")
    if missing or not_passed:
        parts = []
        if missing:
            parts.append("missing fixture(s): " + ", ".join(missing))
        if not_passed:
            parts.append("fixture(s) not marked pass: " + ", ".join(not_passed))
        return PlatformGovernanceCheck("regression_coverage_gate", "FAIL", "; ".join(parts))
    return PlatformGovernanceCheck(
        "regression_coverage_gate",
        "PASS",
        f"{len(required_fixtures)} required platform fixture(s) are declared and passed",
    )


def _migration_readiness_gate(
    migration: dict[str, Any],
    contract: dict[str, Any],
    pcr: dict[str, Any],
    actual_components: set[str],
    actual_stages: set[str],
) -> PlatformGovernanceCheck:
    migration_needed = bool({"requirements_planning", "templates", "schemas", "migrations"} & (actual_components | actual_stages))
    pcr_compat = pcr.get("backward_compatibility") if isinstance(pcr.get("backward_compatibility"), dict) else {}
    if pcr_compat.get("migration_required") is True:
        migration_needed = True
    if not migration_needed:
        return PlatformGovernanceCheck("migration_readiness_gate", "PASS", "no contract migration impact detected")
    missing = []
    for key in ("platform_contract_version", "migration_required", "migration_command", "legacy_frontdoor_policy", "status"):
        if not _non_empty(migration.get(key)):
            missing.append(key)
    version = contract.get("version") or contract.get("platform_contract_version")
    if version and migration.get("platform_contract_version") not in (None, version):
        missing.append("platform_contract_version mismatch")
    if missing:
        return PlatformGovernanceCheck("migration_readiness_gate", "FAIL", "migration manifest incomplete: " + ", ".join(missing))
    return PlatformGovernanceCheck("migration_readiness_gate", "PASS", "contract migration path is declared")


def _arbtr_platform_review_gate(pcr: dict[str, Any]) -> PlatformGovernanceCheck:
    review = pcr.get("arbtr_review")
    if not isinstance(review, dict):
        return PlatformGovernanceCheck("arbtr_platform_review_gate", "FAIL", "arbtr_review must be a mapping")
    decision = str(review.get("decision", "")).strip()
    checklist = review.get("checklist")
    if decision not in ALLOWED_ARBTR_DECISIONS:
        return PlatformGovernanceCheck("arbtr_platform_review_gate", "FAIL", f"invalid Arbtr decision: {decision or '<empty>'}")
    if decision in {"REJECT", "REWORK_REQUIRED", "CLAIM_DOWNGRADE_REQUIRED"}:
        return PlatformGovernanceCheck("arbtr_platform_review_gate", "FAIL", f"Arbtr decision blocks platform change: {decision}")
    if not isinstance(checklist, list) or len(checklist) < 5:
        return PlatformGovernanceCheck("arbtr_platform_review_gate", "FAIL", "Arbtr checklist must cover the platform change")
    if decision == "ACCEPT_WITH_WAIVER" and not _non_empty(review.get("waivers")):
        return PlatformGovernanceCheck("arbtr_platform_review_gate", "FAIL", "ACCEPT_WITH_WAIVER requires waivers")
    return PlatformGovernanceCheck("arbtr_platform_review_gate", "PASS", f"Arbtr platform review decision is {decision}")


def _platform_regression_command_gate(workspace: Path, regression: dict[str, Any]) -> PlatformGovernanceCheck:
    command = str(regression.get("command", "")).strip()
    if not command:
        return PlatformGovernanceCheck("platform_regression_command_gate", "FAIL", "regression_manifest command is empty")
    env = os.environ.copy()
    core_path = str(workspace / "env" / "core")
    pythonpath = env.get("PYTHONPATH", "")
    if core_path not in pythonpath.split(os.pathsep):
        env["PYTHONPATH"] = core_path if not pythonpath else core_path + os.pathsep + pythonpath
    try:
        proc = subprocess.run(
            command,
            cwd=workspace,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
    except OSError as exc:
        return PlatformGovernanceCheck("platform_regression_command_gate", "FAIL", f"failed to launch regression command: {exc}")
    if proc.returncode != 0:
        tail = "\n".join((proc.stdout + "\n" + proc.stderr).splitlines()[-6:])
        return PlatformGovernanceCheck(
            "platform_regression_command_gate",
            "FAIL",
            f"regression command exited {proc.returncode}: {tail}",
        )
    summary = "\n".join((proc.stdout + "\n" + proc.stderr).splitlines()[-3:])
    return PlatformGovernanceCheck("platform_regression_command_gate", "PASS", summary or "regression command passed")


def _classify_changed_files(changed_files: tuple[str, ...]) -> tuple[set[str], set[str], set[str]]:
    components: set[str] = set()
    stages: set[str] = set()
    fixtures: set[str] = set()
    if changed_files:
        fixtures.add("full_contract_pass_project")

    for path in changed_files:
        if path.startswith("env/rule/platform_governance/"):
            components.update({"platform_governance", "rules"})
            stages.add("platform_governance")
        if path.startswith("env/rule/skills/"):
            components.add("skills")
        if path.startswith("env/rule/scaffold/") or path.startswith("env/templates/"):
            components.add("templates")
        if path.startswith("env/rule/global/") or path.startswith("env/rule/project_default/"):
            components.add("rules")
        if path.startswith("env/test/"):
            components.update({"tests", "regression"})
            stages.add("regression")
        if path.startswith("env/tool/scripts/"):
            components.update({"tool_scripts", "cli_commands"})
        if path == "env/core/hdlflow/cli.py":
            components.add("cli_commands")
        if path.startswith("env/core/hdlflow/"):
            components.add("core_modules")
        if "gates.py" in path or "/gates/" in path:
            components.add("gates")
        if "review.py" in path or "/agents/" in path or "/review/" in path:
            components.add("arbtr_review")
        if "/docgen/" in path or "/reports/" in path or "report" in Path(path).name:
            components.add("report_generators")
        if "waveform" in path or "vcd" in path.lower() or "parser" in path:
            components.update({"parsers", "vcd_analysis"})
            stages.add("vcd_analysis")
            fixtures.update({"vcd_required_signal_missing_project", "tb_pass_vcd_fail_project"})
        if "loop1" in path or "/tb" in path or "directed" in path:
            stages.add("directed_tb")
            fixtures.update({"vcd_required_signal_missing_project", "tb_pass_vcd_fail_project"})
        if "loop2" in path or "uvm" in path.lower():
            stages.add("uvm")
        if "loop3" in path or "prototype" in path.lower() or "claim_policy" in path:
            components.add("fpga_prototype")
            stages.add("fpga_prototype")
            fixtures.update({"loop3_emulated_boundary_claim_project", "claim_overreach_block_project"})
        if "frontdoor" in path or "requirements_frontend" in path or "req_decompose" in path:
            components.update({"schemas", "requirements_planning"})
            stages.add("requirements_planning")
            fixtures.update({"requirement_intake_refresh_project", "plan_drift_block_project", "legacy_frontdoor_contract_migration_project"})
        if "migration" in path:
            components.add("migrations")

    return components, stages, fixtures


def _git_changed_files(workspace: Path) -> tuple[str, ...]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(workspace), "status", "--short", "--", "env"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ()
    if proc.returncode != 0:
        return ()
    files: list[str] = []
    for raw in proc.stdout.splitlines():
        if len(raw) < 4:
            continue
        path = raw[3:].strip()
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[-1].strip()
        files.append(path)
    return tuple(files)


def _load_governance_mapping(workspace: Path, rel: Path, root_key: str) -> dict[str, Any]:
    path = workspace / rel
    if not path.is_file():
        return {}
    try:
        data = load_yaml(path)
    except Exception:
        return {}
    nested = data.get(root_key)
    if isinstance(nested, dict):
        return nested
    return data if isinstance(data, dict) else {}


def _declared_components(pcr: dict[str, Any]) -> set[str]:
    declared = {
        CHANGE_TYPE_COMPONENTS[item]
        for item in (str(value).strip() for value in _as_list(pcr.get("change_type")))
        if item in CHANGE_TYPE_COMPONENTS
    }
    components = pcr.get("affected_components")
    if isinstance(components, dict):
        for key, value in components.items():
            if _non_empty(value):
                declared.add(str(key).strip())
    elif isinstance(components, list):
        declared.update(str(item).strip() for item in components if str(item).strip())
    return declared


def _matrix_missing_units(impact: dict[str, Any], units: set[str]) -> list[str]:
    affected_keys = set()
    for key, value in impact.items():
        if key == "pcr_id":
            continue
        if not isinstance(value, dict):
            continue
        if value.get("affected") is True or _non_empty(value.get("required_updates")):
            affected_keys.add(str(key).strip())
    missing = []
    for unit in sorted(units):
        aliases = MATRIX_ALIASES.get(unit, {unit})
        if unit not in affected_keys and not (aliases & affected_keys):
            missing.append(unit)
    return missing


def _write_platform_audit_report(result: PlatformGovernanceResult, pcr: dict[str, Any]) -> None:
    result.report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Platform Change Audit Report",
        "",
        f"- result: {'PASS' if result.ok else 'FAIL'}",
        f"- pcr_id: {pcr.get('id', 'missing')}",
        f"- platform_contract: {DEFAULT_PLATFORM_CONTRACT_VERSION}",
        "",
        "## Changed Files",
        *(f"- {path}" for path in result.changed_files),
        "",
        "## Impact",
        "- components: " + (", ".join(result.actual_components) if result.actual_components else "none"),
        "- stages: " + (", ".join(result.actual_stages) if result.actual_stages else "none"),
        "- required_fixtures: " + (", ".join(result.required_fixtures) if result.required_fixtures else "none"),
        "",
        "## Checks",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for check in result.checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail.replace('|', '/')} |")
    lines.append("")
    result.report_path.write_text("\n".join(lines), encoding="utf-8")


def _archive_legacy_open_questions(project: Path, updated: list[Path]) -> None:
    legacy = project / FRONTDOOR_REL / "open_questions.md"
    if not legacy.is_file():
        return
    archive = project / FRONTDOOR_REL / "history" / "baseline_snapshots" / "open_questions_legacy_archived.md"
    archive.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(
        [
            "# Archived Legacy Open Questions",
            "",
            "archived_by: hdlflow.cli migrate-project",
            "inactive_legacy_file: true",
            "",
            legacy.read_text(encoding="utf-8", errors="ignore"),
        ]
    )
    archive.write_text(text, encoding="utf-8")
    updated.append(archive)


def _ensure_contract_marks_legacy_inactive(project: Path, to_contract: str, updated: list[Path]) -> None:
    contract = project / FRONTDOOR_REL / "contract.yaml"
    contract.parent.mkdir(parents=True, exist_ok=True)
    if contract.is_file():
        text = contract.read_text(encoding="utf-8")
    else:
        text = "\n".join(
            [
                "schema_version: 1",
                f"project: {project.name}",
                "status: DRAFT",
                "owner_role: arbtr",
                "source_refs: []",
            ]
        )
    if "contract_version:" not in text:
        text += "\ncontract_version: frontdoor_contract_v2\n"
    if "active_contract:" not in text:
        text += "active_contract: generated_active_baseline\n"
    if "legacy_contracts:" not in text:
        text += (
            "legacy_contracts:\n"
            "  work/docparse/frontdoor/open_questions.md:\n"
            "    status: inactive\n"
            "    replacement: work/docparse/structured_spec/document_analysis.yaml\n"
            "    reason: Migrated to frontdoor_contract_v2 intake/generated baseline model.\n"
        )
    if f"platform_contract_version: {to_contract}" not in text:
        text += f"platform_contract_version: {to_contract}\n"
    contract.write_text(text, encoding="utf-8")
    updated.append(contract)


def _normalize_changed_file(path: str) -> str:
    return path.replace("\\", "/").strip().lstrip("./")


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, "", {}):
        return []
    return [value]


def _non_empty(value: Any) -> bool:
    if value in (None, "", [], {}):
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _relpath(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")
