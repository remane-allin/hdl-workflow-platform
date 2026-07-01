"""Constants for generated HDL project document sets."""

from __future__ import annotations

from dataclasses import dataclass


SNAPSHOT_ROOT = "work/docgen/snapshots"
DOCSET_REPORT_REL = "output/reports/docset/check_docset.md"
DOCSET_MANIFEST_REL = "output/docs/manifests/docset_manifest.json"


@dataclass(frozen=True)
class DocDefinition:
    doc_type: str
    title: str
    owner_agent: str
    review_agents: tuple[str, ...]
    doc_rel: str
    snapshot_rel: str
    manifest_rel: str
    template_rel: str
    marker_start: str
    marker_end: str
    required_sections: tuple[str, ...]


DOC_DEFINITIONS: tuple[DocDefinition, ...] = (
    DocDefinition(
        doc_type="application_guide",
        title="Application Guide",
        owner_agent="Spec",
        review_agents=("Arch", "Review", "Arbtr"),
        doc_rel="output/docs/application/application_guide.md",
        snapshot_rel=f"{SNAPSHOT_ROOT}/application_doc_snapshot.json",
        manifest_rel="output/docs/manifests/application_doc_manifest.json",
        template_rel="env/templates/docs/application_guide.md.j2",
        marker_start="HDL-APP-DOC START",
        marker_end="HDL-APP-DOC END",
        required_sections=("Integration View", "Interfaces", "Register / Config", "Operation Sequence"),
    ),
    DocDefinition(
        doc_type="microarchitecture_specification",
        title="Microarchitecture Specification",
        owner_agent="Arch",
        review_agents=("Exec", "Sim", "Review", "Arbtr"),
        doc_rel="output/docs/design/microarchitecture_spec.md",
        snapshot_rel=f"{SNAPSHOT_ROOT}/microarchitecture_doc_snapshot.json",
        manifest_rel="output/docs/manifests/microarchitecture_doc_manifest.json",
        template_rel="env/templates/docs/microarchitecture_spec.md.j2",
        marker_start="HDL-UARCH-DOC START",
        marker_end="HDL-UARCH-DOC END",
        required_sections=("Logic Level Design", "Module Topology", "Interfaces", "Clocks and Resets"),
    ),
    DocDefinition(
        doc_type="verification_plan",
        title="Verification Plan",
        owner_agent="Sim",
        review_agents=("Exec", "Review", "Arbtr"),
        doc_rel="output/docs/test/verification_plan.md",
        snapshot_rel=f"{SNAPSHOT_ROOT}/verification_doc_snapshot.json",
        manifest_rel="output/docs/manifests/verification_doc_manifest.json",
        template_rel="env/templates/docs/verification_plan.md.j2",
        marker_start="HDL-VERIF-DOC START",
        marker_end="HDL-VERIF-DOC END",
        required_sections=("Test Matrix", "Coverage", "Assertions", "UVM Environment Plan", "Exit Criteria"),
    ),
    DocDefinition(
        doc_type="delivery_package",
        title="Delivery Package",
        owner_agent="Arbtr",
        review_agents=("Spec", "Arch", "Exec", "Sim", "Review"),
        doc_rel="output/docs/delivery/delivery_package.md",
        snapshot_rel=f"{SNAPSHOT_ROOT}/delivery_doc_snapshot.json",
        manifest_rel="output/docs/manifests/delivery_doc_manifest.json",
        template_rel="env/templates/docs/delivery_package.md.j2",
        marker_start="HDL-DELIVERY-DOC START",
        marker_end="HDL-DELIVERY-DOC END",
        required_sections=("Delivered Document Set", "Gate Status Summary", "Verification Evidence", "Signoff Checklist"),
    ),
)

DOCS_BY_TYPE = {definition.doc_type: definition for definition in DOC_DEFINITIONS}
DEBUG_DOC_COMMANDS = {
    "generate-application-doc": "application_guide",
    "generate-uarch-doc": "microarchitecture_specification",
    "generate-verification-doc": "verification_plan",
    "generate-delivery-doc": "delivery_package",
}
