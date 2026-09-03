from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from Workflow.core.access import discover_project
from Workflow.core.contracts import STAGES, GateError, ProjectContext, WorkflowError
from Workflow.core.state import load_state
from Workflow.reports.tools.extract import load_report
from Workflow.tools.design import load_design
from Workflow.tools.filesystem import atomic_write_json, read_json, remove_owned


RELEASE_MANIFEST_FORMAT_VERSION = 1


def require_released_project(context: ProjectContext) -> tuple[dict[str, Any], dict[str, Any]]:
    design = load_design(context.design_path)
    state = load_state(context, create=False, design_version=design["design_version"])
    if state["current_action"] is not None:
        raise GateError(f"project {context.project_id} has an incomplete action")
    missing = [stage for stage in STAGES if state["stages"][stage]["status"] != "PASS"]
    if missing:
        raise GateError(
            f"project {context.project_id} is not locally released: {', '.join(missing)}"
        )
    report = load_report(context, design)
    if report.get("release", {}).get("status") != "PASS":
        raise GateError(f"project {context.project_id} has no matching release report")
    return design, report


def _relative_path(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise GateError(f"{label} must be a non-empty project-relative path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise GateError(f"{label} must stay inside its source project")
    return path


def release_manifest_path(context: ProjectContext) -> Path:
    return context.project_root / "output" / "release" / "manifest.json"


def _declared_results(design: dict[str, Any]) -> dict[str, tuple[str, str]]:
    results: dict[str, tuple[str, str]] = {}
    allowed = {
        "vivado": ("bitstream", "xsa", "checkpoint"),
        "vitis": ("elf",),
    }
    for owner, names in allowed.items():
        declared = design["implementation"][owner].get("results", {})
        for name in names:
            path = declared.get(name)
            if path:
                kind = "platform" if owner == "vivado" else "file"
                results[f"{owner}.{name}"] = (path, kind)
    return results


def publish_release_assets(
    context: ProjectContext,
    result_ids: list[str],
) -> dict[str, Any]:
    design, _ = require_released_project(context)
    if not result_ids or len(result_ids) != len(set(result_ids)):
        raise WorkflowError("published result ids must be a non-empty unique list")
    declared = _declared_results(design)
    unknown = sorted(set(result_ids) - set(declared))
    if unknown:
        raise GateError("published results are not declared: " + ", ".join(unknown))

    release_root = context.project_root / "output" / "release"
    staging = release_root.with_name(".release.staging")
    if staging.exists():
        remove_owned(staging)
    assets_root = staging / "assets"
    assets_root.mkdir(parents=True)
    assets: list[dict[str, Any]] = []
    try:
        for result_id in result_ids:
            source_text, kind = declared[result_id]
            source_relative = _relative_path(source_text, f"published result {result_id}")
            source = context.project_root / source_relative
            if not source.is_file():
                raise GateError(f"published result is missing: {source_relative.as_posix()}")
            owner, name = result_id.split(".", 1)
            published = assets_root / f"{owner}-{name}{source.suffix.lower()}"
            shutil.copy2(source, published)
            assets.append(
                {
                    "id": result_id,
                    "kind": kind,
                    "path": (
                        release_root.relative_to(context.project_root) / "assets" / published.name
                    ).as_posix(),
                }
            )
        manifest = {
            "format_version": RELEASE_MANIFEST_FORMAT_VERSION,
            "project_id": context.project_id,
            "design_version": design["design_version"],
            "platform": design["project"].get("platform", ""),
            "part": design["project"].get("part", ""),
            "assets": assets,
        }
        atomic_write_json(staging / "manifest.json", manifest)
        previous = release_root.with_name(".release.previous")
        if previous.exists():
            remove_owned(previous)
        if release_root.exists():
            os.replace(release_root, previous)
        try:
            os.replace(staging, release_root)
        except BaseException:
            if previous.exists():
                os.replace(previous, release_root)
            raise
        if previous.exists():
            remove_owned(previous)
    except BaseException:
        if staging.exists():
            remove_owned(staging)
        raise
    return manifest


def load_release_manifest(context: ProjectContext) -> dict[str, Any]:
    path = release_manifest_path(context)
    if not path.is_file():
        raise GateError(f"project {context.project_id} has no published release manifest")
    manifest = read_json(path)
    if manifest.get("format_version") != RELEASE_MANIFEST_FORMAT_VERSION:
        raise GateError(f"project {context.project_id} has an invalid release manifest")
    if manifest.get("project_id") != context.project_id:
        raise GateError(f"project {context.project_id} release manifest identity does not match")
    version = manifest.get("design_version")
    if not isinstance(version, int) or version < 1:
        raise GateError(f"project {context.project_id} release manifest version is invalid")
    assets = manifest.get("assets")
    if not isinstance(assets, list) or not assets:
        raise GateError(f"project {context.project_id} release manifest has no assets")
    seen: set[str] = set()
    for asset in assets:
        if not isinstance(asset, dict) or not isinstance(asset.get("id"), str):
            raise GateError(f"project {context.project_id} release manifest has an invalid asset")
        if asset["id"] in seen:
            raise GateError(f"project {context.project_id} release manifest has duplicate assets")
        seen.add(asset["id"])
        if asset.get("kind") not in {"file", "platform"}:
            raise GateError(f"project {context.project_id} release manifest has an invalid asset kind")
        relative = _relative_path(asset.get("path"), f"published asset {asset['id']}")
        if not relative.as_posix().startswith("output/release/assets/"):
            raise GateError(f"published asset {asset['id']} escapes the release asset directory")
    return manifest


def resolve_reuse_assets(
    context: ProjectContext,
    design: dict[str, Any],
) -> list[dict[str, Any]]:
    references = design["implementation"].get("reuse_assets", [])
    if not isinstance(references, list):
        raise GateError("implementation.reuse_assets must be a list")
    resolved: list[dict[str, Any]] = []
    seen: set[str] = set()
    for reference in references:
        if not isinstance(reference, dict):
            raise GateError("each reuse asset must be an object")
        identifier = reference.get("id")
        if not isinstance(identifier, str) or not identifier.startswith("ASSET-"):
            raise GateError("reuse asset id must start with ASSET-")
        if identifier in seen:
            raise GateError(f"duplicate reuse asset id: {identifier}")
        seen.add(identifier)
        source_project = reference.get("source_project")
        if not isinstance(source_project, str) or not source_project:
            raise GateError(f"reuse asset {identifier} lacks a source project")
        if source_project == context.project_id:
            raise GateError(f"reuse asset {identifier} must come from another project")
        source_context = discover_project(context.workflow_root, source_project)
        manifest = load_release_manifest(source_context)
        if reference.get("source_design_version") != manifest["design_version"]:
            raise GateError(f"reuse asset {identifier} does not match the released design version")
        relative = _relative_path(reference.get("source_path"), f"reuse asset {identifier}")
        relative_text = relative.as_posix()
        kind = reference.get("kind")
        if kind not in {"file", "platform"}:
            raise GateError(f"reuse asset {identifier} has unsupported kind: {kind}")
        published = [
            asset for asset in manifest["assets"]
            if asset["path"] == relative_text and asset["kind"] == kind
        ]
        if len(published) != 1:
            raise GateError(f"reuse asset {identifier} is not in the published release manifest")
        source = source_context.project_root / relative
        if not source.is_file():
            raise GateError(f"reuse asset {identifier} is missing: {relative_text}")
        if kind == "platform":
            for field in ("platform", "part"):
                if manifest.get(field) != design["project"].get(field):
                    raise GateError(f"reuse asset {identifier} has incompatible project.{field}")
        if not reference.get("purpose"):
            raise GateError(f"reuse asset {identifier} lacks purpose")
        resolved.append(
            {
                "id": identifier,
                "kind": kind,
                "source": source.relative_to(context.workflow_root).as_posix(),
                "source_design_version": manifest["design_version"],
            }
        )
    return resolved
