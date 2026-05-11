"""Normalize UG1118 into Vivado custom IP packaging guide artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from . import ug894


DOC_ID = "xilinx.ug1118.2024_2"
TOOL = "vivado"
TOOL_VERSION = "2024.2"
VENDOR = "xilinx"
TITLE = "Vivado Design Suite User Guide: Creating and Packaging Custom IP (UG1118)"


def extract_ug1118(workspace: Path, *, pdf_path: Path | None = None, mineru_dir: Path | None = None) -> Path:
    workspace = workspace.resolve()
    if pdf_path is None:
        pdf_path = workspace / "library" / "files" / "fpga_ug_pdfs" / "ug1118.pdf"
    pdf_path = pdf_path.resolve()
    if not pdf_path.is_file():
        raise FileNotFoundError(f"missing UG1118 PDF: {pdf_path}")

    if mineru_dir is None:
        mineru_dir = workspace / "library" / "work" / "ug_ingest" / "xilinx_ug1118" / "2024_2" / "mineru"
    mineru_dir = mineru_dir.resolve()
    mineru_json = mineru_dir / "ug1118.json"

    old_doc_id = ug894.DOC_ID
    old_tool = ug894.TOOL
    old_tool_version = ug894.TOOL_VERSION
    old_vendor = ug894.VENDOR
    try:
        ug894.DOC_ID = DOC_ID
        ug894.TOOL = TOOL
        ug894.TOOL_VERSION = TOOL_VERSION
        ug894.VENDOR = VENDOR

        if mineru_json.is_file():
            blocks = ug894._load_mineru_blocks(mineru_json)
            parser = "mineru-open-api extract; flash channel not used"
        else:
            blocks = ug894._load_pypdf_blocks(pdf_path)
            parser = "pypdf fallback normalizer; MinerU output not found"

        page_count = ug894._pdf_page_count(pdf_path)
        sections = ug894._build_sections(blocks)
        examples = ug894._build_examples(blocks, sections)
        examples.extend(_build_inline_tcl_examples(blocks, sections, len(examples)))
        chunks = ug894._build_chunks(sections, examples)
    finally:
        ug894.DOC_ID = old_doc_id
        ug894.TOOL = old_tool
        ug894.TOOL_VERSION = old_tool_version
        ug894.VENDOR = old_vendor

    out_dir = workspace / "library" / "parsed" / "software_ug_mineru" / "xilinx_ug1118" / "2024_2"
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "schema_version": 1,
        "doc_id": DOC_ID,
        "title": TITLE,
        "vendor": VENDOR,
        "tool": TOOL,
        "tool_version": TOOL_VERSION,
        "source_file": ug894._relpath(pdf_path, workspace),
        "source_type": "pdf",
        "parser": parser,
        "page_count": page_count,
        "section_count": len(sections),
        "example_count": len(examples),
        "command_count": 0,
        "parsed_dir": ug894._relpath(out_dir, workspace / "library"),
        "mineru_source_dir": ug894._relpath(mineru_dir, workspace) if mineru_dir.exists() else "",
        "structured_artifacts": [
            ug894._relpath(out_dir / "sections.json", workspace / "library"),
            ug894._relpath(out_dir / "examples.json", workspace / "library"),
            ug894._relpath(out_dir / "chunks.jsonl", workspace / "library"),
            ug894._relpath(out_dir / "quality_report.json", workspace / "library"),
        ],
        "notes": [
            "Built for AI-assisted Vivado custom IP packaging, IP-XACT, interface definition, and encryption workflows.",
            "UG1118 is normalized as IP packaging topics, Tcl examples, and full-text chunks.",
            "Use UG835 command records for precise Tcl command syntax.",
        ],
    }
    quality = {
        "doc_id": DOC_ID,
        "page_count": page_count,
        "section_count": len(sections),
        "example_count": len(examples),
        "chunk_count": len(chunks),
        "sections_without_text": [section["topic_id"] for section in sections if not section["text"]],
        "examples_without_commands": [example["example_id"] for example in examples if not example["commands"]],
        "parser": parser,
    }

    ug894._write_json(out_dir / "metadata.json", metadata)
    ug894._write_json(out_dir / "sections.json", {"schema_version": 1, "doc_id": DOC_ID, "sections": sections})
    ug894._write_json(out_dir / "examples.json", {"schema_version": 1, "doc_id": DOC_ID, "examples": examples})
    ug894._write_json(out_dir / "quality_report.json", quality)
    with (out_dir / "chunks.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    return out_dir


def _build_inline_tcl_examples(
    blocks: list[dict[str, object]],
    sections: list[dict[str, object]],
    offset: int,
) -> list[dict[str, object]]:
    section_by_page = sorted(sections, key=lambda item: int(item["page_start"]))
    examples: list[dict[str, object]] = []
    seen: set[str] = set()
    for index, block in enumerate(blocks):
        if block.get("type") != "text":
            continue
        text = _clean_inline_code(str(block.get("text") or ""))
        if not _looks_like_tcl_line(text):
            continue
        if text in seen:
            continue
        seen.add(text)
        page = int(block.get("page") or 0)
        topic = ug894._topic_for_page(section_by_page, page)
        previous_text = ug894._previous_text(blocks, index)
        commands = ug894._extract_commands_from_code(text)
        examples.append(
            {
                "example_id": f"{DOC_ID}.example.{offset + len(examples) + 1:03d}",
                "doc_id": DOC_ID,
                "topic_id": topic.get("topic_id", ""),
                "tool": TOOL,
                "tool_version": TOOL_VERSION,
                "title": topic.get("title", "UG1118 Tcl example"),
                "page_start": page,
                "page_end": page,
                "code": text,
                "description": previous_text,
                "commands": commands,
                "tags": sorted(set(ug894._tags_for(str(topic.get("title", "")), previous_text) + ["example", "inline_tcl"])),
            }
        )
    return examples


def _clean_inline_code(text: str) -> str:
    text = text.replace("\\_", "_")
    text = text.replace("\\[", "[").replace("\\]", "]")
    text = text.replace("\\*", "*")
    return " ".join(text.split()).strip()


def _looks_like_tcl_line(text: str) -> bool:
    if not text or len(text) > 260:
        return False
    if text.endswith(".") or text.endswith(":"):
        return False
    markers = [
        "ipx::",
        "set_property ",
        "get_property ",
        "encrypt ",
        "write_checkpoint ",
        "create_project ",
        "package_project",
        "ipx::package_project",
    ]
    if any(marker in text for marker in markers):
        return True
    return False
