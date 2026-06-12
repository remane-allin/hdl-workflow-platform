"""Removed legacy single design-document workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .docgen import RemovedWorkflowError, removed_generate_design_doc_message


@dataclass(frozen=True)
class DesignDocResult:
    report_path: Path
    manifest_path: Path
    warnings: list[str]
    errors: list[str]

    @property
    def ok(self) -> bool:
        return False


def generate_design_document(project_path: Path, *, allow_draft: bool = False) -> DesignDocResult:
    raise RemovedWorkflowError(removed_generate_design_doc_message())


def check_design_document(project_path: Path, *, sections: list[str] | None = None) -> DesignDocResult:
    raise RemovedWorkflowError("check_design_document has been removed. Use check_docset.")


def design_doc_report_rel() -> str:
    raise RemovedWorkflowError("design_doc_report_rel has been removed. Use output/docs.")


def design_doc_manifest_rel() -> str:
    raise RemovedWorkflowError("design_doc_manifest_rel has been removed. Use output/docs/manifests/docset_manifest.json.")
