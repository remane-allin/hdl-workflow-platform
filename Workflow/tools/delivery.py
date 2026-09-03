from __future__ import annotations

import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any, Iterable

from Workflow.core.access import is_within, require_workspace_write
from Workflow.core.contracts import GateError, ProjectContext, WorkflowError
from Workflow.reports.tools.extract import report_path
from Workflow.tools.assets import require_released_project
from Workflow.tools.design import load_design, validate_design
from Workflow.tools.filesystem import read_json, remove_owned


OUTPUT_DIRECTORIES = ("rtl", "tb", "uvm", "constraints", "vivado", "vitis", "release")


def release_pathspecs(context: ProjectContext) -> list[Path]:
    candidates = [
        context.project_root / "input" / "current",
        context.project_root / "input" / "sources",
        *(context.project_root / "output" / name for name in OUTPUT_DIRECTORIES),
        context.project_root / "output" / "report" / "current",
        context.project_root / "output" / "report" / "issue-report.csv",
        context.project_root / "output" / "report" / "archive",
        context.project_root / "README.md",
    ]
    return [path for path in candidates if path.exists()]


def _git(
    project_root: Path,
    arguments: list[str],
    *,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("git")
    if executable is None:
        raise WorkflowError("git executable is unavailable")
    try:
        result = subprocess.run(
            [
                executable,
                "-c", "core.hooksPath=NUL",
                "-c", "commit.gpgSign=false",
                "-c", "tag.gpgSign=false",
                "-c", "gc.auto=0",
                "-c", "maintenance.auto=false",
                "-C", str(project_root),
                *arguments,
            ],
            input=input_text,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=120,
        )
    except subprocess.TimeoutExpired as error:
        raise WorkflowError("git command timed out") from error
    if result.returncode:
        message = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise WorkflowError(message)
    return result


def _pathspec_input(paths: list[str]) -> str:
    return "\0".join(paths) + "\0"


def _approved_tracked_path(relative: Path, declared_results: set[str]) -> bool:
    text = relative.as_posix()
    roots = (
        "input/current/",
        "input/sources/",
        *(f"output/{name}/" for name in OUTPUT_DIRECTORIES),
        "output/report/current/",
    )
    if text in {"README.md", "output/report/issue-report.csv"}:
        return _archive_file_allowed(relative, declared_results)
    if text.startswith("output/report/archive/"):
        return False
    return any(text.startswith(root) for root in roots) and _archive_file_allowed(
        relative, declared_results
    )


def deliver_git(
    context: ProjectContext,
    message: str,
    *,
    initialize: bool = False,
    tag: str | None = None,
    remote: str | None = None,
    push: bool = False,
) -> dict[str, Any]:
    require_released_project(context)
    if not message.strip():
        raise WorkflowError("git delivery requires a commit message")
    repository = context.project_root / ".git"
    if not repository.exists():
        if not initialize:
            raise WorkflowError("project is not a Git repository; use --init for local initialization")
        _git(context.project_root, ["init"])
    top = Path(_git(context.project_root, ["rev-parse", "--show-toplevel"]).stdout.strip()).resolve()
    if top != context.project_root.resolve():
        raise WorkflowError("Git delivery requires the project root to be the repository root")
    design = load_design(context.design_path)
    declared = _declared_results(design)
    paths = {
        path.relative_to(context.project_root).as_posix()
        for path in _release_files(context, design)
    }
    tracked = _git(context.project_root, ["ls-files", "-z"]).stdout.split("\0")
    paths.update(
        item for item in tracked
        if item and _approved_tracked_path(Path(item), declared)
    )
    paths = sorted(paths)
    if not paths:
        raise WorkflowError("the approved release set is empty")
    pathspec = _pathspec_input(paths)
    _git(
        context.project_root,
        ["add", "-A", "--pathspec-from-file=-", "--pathspec-file-nul"],
        input_text=pathspec,
    )
    staged = set(
        _git(context.project_root, ["diff", "--cached", "--name-only", "-z"])
        .stdout.split("\0")
    )
    committed = bool(staged.intersection(paths))
    if committed:
        _git(
            context.project_root,
            [
                "-c", "user.name=Workflow",
                "-c", "user.email=workflow@local",
                "commit", "--only", "-m", message,
                "--pathspec-from-file=-", "--pathspec-file-nul",
            ],
            input_text=pathspec,
        )
    if tag:
        _git(context.project_root, ["tag", tag])
    if push:
        if not remote:
            raise WorkflowError("remote push requires an explicit remote name")
        _git(context.project_root, ["push", remote, "HEAD"])
        if tag:
            _git(context.project_root, ["push", remote, tag])
    return {
        "status": "PASS",
        "project_id": context.project_id,
        "committed": committed,
        "tag": tag or "",
        "remote_push": push,
        "release_paths": paths,
    }


def _declared_results(design: dict[str, Any]) -> set[str]:
    results = {
        value for value in design["implementation"]["vivado"].get("results", {}).values() if value
    }
    results.update(
        value for value in design["implementation"]["vitis"].get("results", {}).values() if value
    )
    return results


def _archive_file_allowed(relative: Path, declared_results: set[str]) -> bool:
    text = relative.as_posix()
    lowered = [part.lower() for part in relative.parts]
    if any(part in {".git", ".xil", "__pycache__", "last-failure", ".staging"} for part in lowered):
        return False
    if any(part.startswith(".release.") for part in lowered):
        return False
    if relative.name.startswith(".") and relative.suffix == ".tmp":
        return False
    if relative.suffix.lower() in {".pyc", ".pb", ".log", ".jou", ".str"}:
        return False
    if ".backup." in relative.name.lower():
        return False
    if text.startswith("output/vivado/"):
        if any(part.endswith(".cache") for part in lowered):
            return False
        if any(part.endswith(".runs") for part in lowered) and text not in declared_results:
            return False
    return True


def _release_files(context: ProjectContext, design: dict[str, Any]) -> Iterable[Path]:
    declared = _declared_results(design)
    for root in release_pathspecs(context):
        if root == context.project_root / "output" / "report" / "archive":
            continue
        paths = [root] if root.is_file() else root.rglob("*")
        for path in paths:
            if path.is_file():
                relative = path.relative_to(context.project_root)
                if _archive_file_allowed(relative, declared):
                    yield path


def create_archive(context: ProjectContext, destination: Path) -> dict[str, Any]:
    design, _ = require_released_project(context)
    destination = require_workspace_write(destination, context.workflow_root.parent)
    if destination.suffix.lower() != ".zip":
        raise WorkflowError("archive output must use the .zip extension")
    if destination.exists():
        raise WorkflowError("archive output already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(set(_release_files(context, design)))
    manifest = {
        "format_version": 1,
        "project_id": context.project_id,
        "design_version": design["design_version"],
        "files": [
            {"path": path.relative_to(context.project_root).as_posix(), "bytes": path.stat().st_size}
            for path in files
        ],
    }
    temporary = destination.with_name(f".{destination.name}.tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("_archive/manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
            for path in files:
                archive.write(path, path.relative_to(context.project_root).as_posix())
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return {
        "status": "PASS",
        "project_id": context.project_id,
        "design_version": design["design_version"],
        "archive": destination.relative_to(context.workflow_root.parent).as_posix(),
        "file_count": len(files),
    }


def _safe_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    members = archive.infolist()
    names: set[str] = set()
    for member in members:
        path = Path(member.filename)
        normalized = path.as_posix().rstrip("/").casefold()
        if path.is_absolute() or ".." in path.parts or not normalized or normalized in names:
            raise GateError("archive contains an unsafe or duplicate path")
        names.add(normalized)
    return members


def restore_archive(workflow_root: Path, source: Path, target: Path) -> dict[str, Any]:
    target = require_workspace_write(target, workflow_root.parent)
    if is_within(target, workflow_root / "prj"):
        raise WorkflowError("archive recovery must use an isolated directory outside Workflow/prj")
    if target.exists():
        raise WorkflowError("archive recovery target already exists")
    staging = target.with_name(f".{target.name}.staging")
    if staging.exists():
        remove_owned(staging)
    staging.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(source, "r") as archive:
            members = _safe_members(archive)
            if "_archive/manifest.json" not in {item.filename for item in members}:
                raise GateError("archive manifest is missing")
            archive.extractall(staging)
        manifest = read_json(staging / "_archive" / "manifest.json")
        entries = manifest.get("files")
        if not isinstance(entries, list) or not entries:
            raise GateError("archive manifest has no files")
        expected = {"_archive/manifest.json"}
        for entry in entries:
            relative = _relative_manifest_path(entry)
            if relative.as_posix() in expected:
                raise GateError("archive manifest contains a duplicate path")
            expected.add(relative.as_posix())
            restored = staging / relative
            if not restored.is_file() or restored.stat().st_size != entry.get("bytes"):
                raise GateError(f"archive file is missing or incomplete: {relative.as_posix()}")
        actual = {
            item.filename.rstrip("/") for item in members
            if not item.is_dir()
        }
        if actual != expected:
            raise GateError("archive contains files outside its manifest")
        design = load_design(staging / "input" / "current" / "design.json")
        if design["project"].get("project_id") != manifest.get("project_id"):
            raise GateError("archive project identity does not match its design")
        errors = validate_design(design, staging, manifest["project_id"])
        if errors:
            raise GateError("restored design is invalid: " + "; ".join(errors))
        declared = _declared_results(design)
        disallowed = sorted(
            path for path in expected - {"_archive/manifest.json"}
            if not _archive_file_allowed(Path(path), declared)
        )
        if disallowed:
            raise GateError("archive manifest contains disallowed release files")
        report = read_json(report_path(ProjectContext(workflow_root, manifest["project_id"], staging)))
        if report.get("context", {}).get("design_version") != design["design_version"]:
            raise GateError("restored report design version does not match")
        if report.get("release", {}).get("status") != "PASS":
            raise GateError("restored archive has no released report")
        remove_owned(staging / "_archive")
        os.replace(staging, target)
    except BaseException:
        if staging.exists():
            remove_owned(staging)
        raise
    return {
        "status": "PASS",
        "project_id": manifest["project_id"],
        "design_version": manifest["design_version"],
        "target": target.relative_to(workflow_root.parent).as_posix(),
        "state_restored": False,
    }


def _relative_manifest_path(entry: Any) -> Path:
    if not isinstance(entry, dict):
        raise GateError("archive manifest entry must be an object")
    path = Path(entry.get("path", ""))
    if not path.parts or path.is_absolute() or ".." in path.parts:
        raise GateError("archive manifest entry has an unsafe path")
    if not isinstance(entry.get("bytes"), int) or entry["bytes"] < 0:
        raise GateError("archive manifest entry has an invalid size")
    return path
