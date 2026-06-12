"""Four-document docset generation for HDL workflow projects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..project import require_project_instance
from ..requirements_frontend import check_requirements_frontend
from .checks import DocsetCheckResult, check_docset
from .constants import DEBUG_DOC_COMMANDS, DOC_DEFINITIONS, DOCS_BY_TYPE
from .manifests import build_document_manifest, write_docset_manifest, write_document_manifest
from .render import render_document
from .snapshots import build_snapshot, write_snapshot


class RemovedWorkflowError(RuntimeError):
    """Raised when the removed single design-document workflow is invoked."""


@dataclass(frozen=True)
class GenerateDocsResult:
    doc_paths: list[Path]
    manifest_paths: list[Path]
    snapshot_paths: list[Path]
    docset_manifest_path: Path
    check_result: DocsetCheckResult
    warnings: list[str]
    errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors and self.check_result.ok


def generate_docset(project_path: Path, *, change_id: str | None = None, allow_draft: bool = False) -> GenerateDocsResult:
    project = require_project_instance(project_path)
    warnings: list[str] = []
    errors: list[str] = []
    if not allow_draft:
        frontdoor = check_requirements_frontend(project, require_ready=True)
        warnings.extend(f"frontdoor: {item}" for item in frontdoor.warnings)
        if not frontdoor.ok:
            errors.extend(["generate-docs blocked: requirements-frontdoor-check did not pass"])
            errors.extend(f"frontdoor: {item}" for item in frontdoor.errors)
            empty_check = check_docset(project, write_report=False)
            return GenerateDocsResult([], [], [], project / "output/docs/manifests/docset_manifest.json", empty_check, warnings, errors)

    doc_paths: list[Path] = []
    manifest_paths: list[Path] = []
    snapshot_paths: list[Path] = []
    for definition in DOC_DEFINITIONS:
        doc_path, snapshot_path, manifest_path = _generate_one(project, definition.doc_type, change_id=change_id)
        doc_paths.append(doc_path)
        snapshot_paths.append(snapshot_path)
        manifest_paths.append(manifest_path)
    docset_manifest = write_docset_manifest(project, change_id=change_id)
    check = check_docset(project, level="develop", change_id=change_id)
    return GenerateDocsResult(doc_paths, manifest_paths, snapshot_paths, docset_manifest, check, warnings, errors)


def generate_single_doc(project_path: Path, doc_type: str, *, change_id: str | None = None) -> GenerateDocsResult:
    project = require_project_instance(project_path)
    doc_path, snapshot_path, manifest_path = _generate_one(project, doc_type, change_id=change_id)
    docset_manifest = write_docset_manifest(project, change_id=change_id)
    check = check_docset(project, required_docs=[doc_type], change_id=change_id)
    return GenerateDocsResult([doc_path], [manifest_path], [snapshot_path], docset_manifest, check, [], [])


def removed_generate_design_doc_message() -> str:
    return "\n".join(
        [
            "ERROR: generate-design-doc has been removed.",
            "Use:",
            "  python -m hdlflow.cli generate-docs --project <project>",
            "The platform now generates a four-document docset:",
            "  application_guide.md",
            "  microarchitecture_spec.md",
            "  verification_plan.md",
            "  delivery_package.md",
        ]
    )


def _generate_one(project: Path, doc_type: str, *, change_id: str | None) -> tuple[Path, Path, Path]:
    definition = DOCS_BY_TYPE[doc_type]
    snapshot = build_snapshot(project, doc_type, change_id=change_id)
    snapshot_path = write_snapshot(project, snapshot)
    doc_text = render_document(snapshot)
    doc_path = project / definition.doc_rel
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(doc_text, encoding="utf-8")
    manifest = build_document_manifest(project, definition, snapshot_path=snapshot_path, doc_path=doc_path, change_id=change_id)
    manifest_path = write_document_manifest(project, manifest)
    return doc_path, snapshot_path, manifest_path
