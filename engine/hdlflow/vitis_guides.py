"""Normalize Vitis/PDM user guides into software guide database artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import ug894


@dataclass(frozen=True)
class GuideConfig:
    key: str
    doc_id: str
    title: str
    filename: str
    tool: str
    tags: tuple[str, ...]


GUIDES = {
    "ug1553": GuideConfig(
        key="ug1553",
        doc_id="xilinx.ug1553.2024_2",
        title="Vitis Unified IDE and Common Command-Line Reference Manual (UG1553)",
        filename="UG1553.pdf",
        tool="vitis",
        tags=("vitis", "unified_ide", "command_line", "vitis_run", "vpp"),
    ),
    "ug908": GuideConfig(
        key="ug908",
        doc_id="xilinx.ug908.2024_2",
        title="Vivado Design Suite User Guide: Programming and Debugging (UG908)",
        filename="UG908.pdf",
        tool="vivado",
        tags=("vivado", "programming", "hardware_debug", "hardware_manager", "ila", "vio", "hw_server", "jtag"),
    ),
    "ug1556": GuideConfig(
        key="ug1556",
        doc_id="xilinx.ug1556.2024_2",
        title="Power Design Manager User Guide (UG1556)",
        filename="UG1556.pdf",
        tool="pdm",
        tags=("pdm", "power", "thermal", "estimation"),
    ),
    "ug1701": GuideConfig(
        key="ug1701",
        doc_id="xilinx.ug1701.2024_2",
        title="Embedded Design Development Using Vitis User Guide (UG1701)",
        filename="ug1701.pdf",
        tool="vitis",
        tags=("vitis", "embedded", "platform", "xpfm", "system_project"),
    ),
    "ug1702": GuideConfig(
        key="ug1702",
        doc_id="xilinx.ug1702.2024_2",
        title="Vitis Reference Guide (UG1702)",
        filename="UG1702.pdf",
        tool="vitis",
        tags=("vitis", "reference", "command_line", "vpp", "xbutil", "xclbinutil"),
    ),
}


def extract_vitis_guide(
    workspace: Path,
    guide_key: str,
    *,
    pdf_path: Path | None = None,
    mineru_dir: Path | None = None,
) -> Path:
    if guide_key not in GUIDES:
        raise KeyError(f"unknown Vitis guide: {guide_key}")
    config = GUIDES[guide_key]
    workspace = workspace.resolve()
    if pdf_path is None:
        pdf_path = workspace / "library" / "files" / "fpga_ug_pdfs" / config.filename
    pdf_path = pdf_path.resolve()
    if not pdf_path.is_file():
        raise FileNotFoundError(f"missing {config.key} PDF: {pdf_path}")

    if mineru_dir is None:
        mineru_dir = workspace / "library" / "work" / "ug_ingest" / f"xilinx_{config.key}" / "2024_2" / "mineru"
    mineru_dir = mineru_dir.resolve()
    mineru_json = mineru_dir / f"{config.key}.json"
    if not mineru_json.is_file() and mineru_dir.is_dir():
        candidates = sorted(mineru_dir.glob("*.json"))
        if candidates:
            mineru_json = candidates[0]

    old_doc_id = ug894.DOC_ID
    old_tool = ug894.TOOL
    old_tool_version = ug894.TOOL_VERSION
    old_vendor = ug894.VENDOR
    try:
        ug894.DOC_ID = config.doc_id
        ug894.TOOL = config.tool
        ug894.TOOL_VERSION = "2024.2"
        ug894.VENDOR = "xilinx"

        if mineru_json.is_file():
            blocks = ug894._load_mineru_blocks(mineru_json)
            parser = "mineru-open-api extract; flash channel not used"
        else:
            blocks = ug894._load_pypdf_blocks(pdf_path)
            parser = "pypdf fallback normalizer; MinerU output not found"

        page_count = ug894._pdf_page_count(pdf_path)
        sections = ug894._build_sections(blocks)
        _add_guide_tags(sections, config.tags)
        examples = ug894._build_examples(blocks, sections)
        examples.extend(_build_inline_cli_examples(blocks, sections, config, len(examples)))
        chunks = ug894._build_chunks(sections, examples)
    finally:
        ug894.DOC_ID = old_doc_id
        ug894.TOOL = old_tool
        ug894.TOOL_VERSION = old_tool_version
        ug894.VENDOR = old_vendor

    out_dir = workspace / "library" / "parsed" / "software_ug_mineru" / f"xilinx_{config.key}" / "2024_2"
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "schema_version": 1,
        "doc_id": config.doc_id,
        "title": config.title,
        "vendor": "xilinx",
        "tool": config.tool,
        "tool_version": "2024.2",
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
            "Built for AI-assisted Vitis/PDM command-line, embedded, reference, and debug workflows.",
            "This guide is normalized as topics, examples, and full-text chunks.",
            "Vitis CLI/reference content is kept out of the Vivado Tcl command table to avoid command ambiguity.",
        ],
    }
    quality = {
        "doc_id": config.doc_id,
        "page_count": page_count,
        "section_count": len(sections),
        "example_count": len(examples),
        "chunk_count": len(chunks),
        "sections_without_text": [section["topic_id"] for section in sections if not section["text"]],
        "examples_without_commands": [example["example_id"] for example in examples if not example["commands"]],
        "parser": parser,
    }

    ug894._write_json(out_dir / "metadata.json", metadata)
    ug894._write_json(out_dir / "sections.json", {"schema_version": 1, "doc_id": config.doc_id, "sections": sections})
    ug894._write_json(out_dir / "examples.json", {"schema_version": 1, "doc_id": config.doc_id, "examples": examples})
    ug894._write_json(out_dir / "quality_report.json", quality)
    with (out_dir / "chunks.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    return out_dir


def _add_guide_tags(sections: list[dict[str, object]], guide_tags: tuple[str, ...]) -> None:
    for section in sections:
        tags = list(section.get("tags") or [])
        section["tags"] = sorted(set(tags + list(guide_tags)))


def _build_inline_cli_examples(
    blocks: list[dict[str, object]],
    sections: list[dict[str, object]],
    config: GuideConfig,
    offset: int,
) -> list[dict[str, object]]:
    section_by_page = sorted(sections, key=lambda item: int(item["page_start"]))
    examples: list[dict[str, object]] = []
    seen: set[str] = set()
    for index, block in enumerate(blocks):
        if block.get("type") not in {"text", "list"}:
            continue
        for line in _candidate_lines(str(block.get("text") or "")):
            code = _clean_inline_code(line)
            if not _looks_like_cli_line(code):
                continue
            if code in seen:
                continue
            seen.add(code)
            page = int(block.get("page") or 0)
            topic = ug894._topic_for_page(section_by_page, page)
            previous_text = ug894._previous_text(blocks, index)
            commands = _extract_cli_commands(code)
            examples.append(
                {
                    "example_id": f"{config.doc_id}.example.{offset + len(examples) + 1:03d}",
                    "doc_id": config.doc_id,
                    "topic_id": topic.get("topic_id", ""),
                    "tool": config.tool,
                    "tool_version": "2024.2",
                    "title": topic.get("title", config.title),
                    "page_start": page,
                    "page_end": page,
                    "code": code,
                    "description": previous_text,
                    "commands": commands,
                    "tags": sorted(set(list(config.tags) + ["example", "inline_cli"])),
                }
            )
    return examples


def _candidate_lines(text: str) -> list[str]:
    lines = []
    for raw in text.replace(" | ", "\n").splitlines():
        raw = raw.strip()
        if raw:
            lines.append(raw)
    if len(lines) == 1 and len(lines[0]) < 220:
        return lines
    return lines


def _clean_inline_code(text: str) -> str:
    text = text.replace("\\_", "_")
    text = text.replace("\\[", "[").replace("\\]", "]")
    text = text.replace("\\*", "*")
    return " ".join(text.split()).strip()


def _looks_like_cli_line(text: str) -> bool:
    if not text or len(text) > 300:
        return False
    if text.endswith(".") or text.endswith(":"):
        return False
    starts = (
        "v++ ", "vitis ", "vitis-run ", "vitis_analyzer ", "xbutil ", "xbmgmt ",
        "xclbinutil ", "platforminfo ", "kernelinfo ", "emconfigutil ",
        "launch_emulator ", "manage_ipcache ", "xsdb ", "source ",
        "make ", "cmake ", "bootgen ",
        "open_hw_manager", "connect_hw_server", "open_hw_target", "close_hw_target",
        "current_hw_device", "program_hw_devices", "refresh_hw_device",
        "get_hw_devices", "get_hw_targets", "get_hw_ilas", "run_hw_ila",
        "wait_on_hw_ila", "upload_hw_ila_data", "display_hw_ila_data",
        "write_hw_ila_data", "read_hw_ila_data", "write_hw_stapl",
        "write_hw_svf", "create_hw_axi_txn", "run_hw_axi", "reset_hw_ila",
        "set_property ", "get_property ",
    )
    contains = (
        " --platform ", " --package ", " --link ", " --compile ", " --config ",
        " settings64.sh", "xrt.ini", "vitis-comp.json",
        "PROGRAM.FILE", "PROBES.FILE", "FULL_PROBES.FILE",
    )
    return text.startswith(starts) or any(marker in text for marker in contains)


def _extract_cli_commands(code: str) -> list[str]:
    commands: list[str] = []
    for line in code.splitlines() or [code]:
        line = line.strip()
        if not line:
            continue
        if line.startswith("source "):
            command = "source"
        else:
            command = line.split()[0]
        command = command.strip()
        if command and command not in commands:
            commands.append(command)
    return commands
