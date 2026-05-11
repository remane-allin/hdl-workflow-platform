"""Normalize UG894 into Vivado Tcl scripting guide database artifacts."""

from __future__ import annotations

import json
import re
import unicodedata
from html import unescape
from pathlib import Path
from typing import Any


DOC_ID = "xilinx.ug894.2024_2"
TOOL = "vivado"
TOOL_VERSION = "2024.2"
VENDOR = "xilinx"


def extract_ug894(workspace: Path, *, pdf_path: Path | None = None, mineru_dir: Path | None = None) -> Path:
    workspace = workspace.resolve()
    if pdf_path is None:
        pdf_path = workspace / "library" / "files" / "fpga_ug_pdfs" / "ug894.pdf"
    pdf_path = pdf_path.resolve()
    if not pdf_path.is_file():
        raise FileNotFoundError(f"missing UG894 PDF: {pdf_path}")

    if mineru_dir is None:
        mineru_dir = workspace / "library" / "work" / "ug_ingest" / "xilinx_ug894" / "2024_2" / "mineru"
    mineru_dir = mineru_dir.resolve()
    mineru_json = mineru_dir / "ug894.json"
    mineru_md = mineru_dir / "ug894.md"
    if mineru_json.is_file():
        blocks = _load_mineru_blocks(mineru_json)
        parser = "mineru-open-api extract; flash channel not used"
    else:
        blocks = _load_pypdf_blocks(pdf_path)
        parser = "pypdf fallback normalizer; MinerU output not found"

    page_count = _pdf_page_count(pdf_path)
    sections = _build_sections(blocks)
    examples = _build_examples(blocks, sections)
    chunks = _build_chunks(sections, examples)

    out_dir = workspace / "library" / "parsed" / "software_ug_mineru" / "xilinx_ug894" / "2024_2"
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "schema_version": 1,
        "doc_id": DOC_ID,
        "title": "Vivado Design Suite User Guide: Using Tcl Scripting (UG894)",
        "vendor": VENDOR,
        "tool": TOOL,
        "tool_version": TOOL_VERSION,
        "source_file": _relpath(pdf_path, workspace),
        "source_type": "pdf",
        "parser": parser,
        "page_count": page_count,
        "section_count": len(sections),
        "example_count": len(examples),
        "command_count": 0,
        "parsed_dir": _relpath(out_dir, workspace / "library"),
        "mineru_source_dir": _relpath(mineru_dir, workspace) if mineru_dir.exists() else "",
        "structured_artifacts": [
            _relpath(out_dir / "sections.json", workspace / "library"),
            _relpath(out_dir / "examples.json", workspace / "library"),
            _relpath(out_dir / "chunks.jsonl", workspace / "library"),
            _relpath(out_dir / "quality_report.json", workspace / "library"),
        ],
        "notes": [
            "Built for AI-assisted Vivado Tcl script generation and debug.",
            "UG894 is normalized as scripting topics, examples, and full-text chunks.",
            "Use UG835 command records for precise command syntax.",
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

    _write_json(out_dir / "metadata.json", metadata)
    _write_json(out_dir / "sections.json", {"schema_version": 1, "doc_id": DOC_ID, "sections": sections})
    _write_json(out_dir / "examples.json", {"schema_version": 1, "doc_id": DOC_ID, "examples": examples})
    _write_json(out_dir / "quality_report.json", quality)
    with (out_dir / "chunks.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    return out_dir


def _load_mineru_blocks(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    blocks: list[dict[str, Any]] = []
    for item in raw:
        item_type = item.get("type")
        page = int(item.get("page_idx", 0)) + 1
        text = ""
        if item_type in {"header", "footer", "page_number", "image"}:
            continue
        if item_type == "text":
            text = _normalize_text(str(item.get("text") or ""))
        elif item_type == "list":
            text = "\n".join(_normalize_text(str(entry)) for entry in item.get("list_items", []))
        elif item_type == "code":
            text = _strip_code_fence(str(item.get("code_body") or ""))
        elif item_type == "table":
            text = _html_to_text(str(item.get("table_body") or ""))
        if not text:
            continue
        blocks.append(
            {
                "page": page,
                "type": item_type,
                "text": text,
                "is_heading": item_type == "text" and item.get("text_level") == 1,
            }
        )
    return blocks


def _load_pypdf_blocks(pdf_path: Path) -> list[dict[str, Any]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pypdf is required when MinerU output is unavailable") from exc
    reader = PdfReader(str(pdf_path))
    blocks: list[dict[str, Any]] = []
    for page_index, page in enumerate(reader.pages, start=1):
        for line in (page.extract_text() or "").splitlines():
            text = _normalize_text(line)
            if not text or text.startswith("Vivado Design Suite User Guide") or text == "Displayed in the footer":
                continue
            if re.match(r"^Page \d+ of \d+$", text):
                continue
            blocks.append({"page": page_index, "type": "text", "text": text, "is_heading": _looks_like_heading(text)})
    return blocks


def _build_sections(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    heading_indexes = [
        index
        for index, block in enumerate(blocks)
        if block["is_heading"] and block["page"] >= 3 and not _is_noise_heading(block["text"])
    ]
    sections: list[dict[str, Any]] = []
    used_slugs: dict[str, int] = {}
    for pos, start in enumerate(heading_indexes):
        end = heading_indexes[pos + 1] if pos + 1 < len(heading_indexes) else len(blocks)
        title = blocks[start]["text"].strip()
        content_blocks = blocks[start + 1 : end]
        page_start = blocks[start]["page"]
        page_end = max([page_start] + [block["page"] for block in content_blocks])
        body_parts = [_block_text(block) for block in content_blocks if block["type"] != "code"]
        text = "\n".join(part for part in body_parts if part).strip()
        slug = _unique_slug(_slug(title), used_slugs)
        tags = _tags_for(title, text)
        sections.append(
            {
                "topic_id": f"{DOC_ID}.topic.{slug}",
                "doc_id": DOC_ID,
                "tool": TOOL,
                "tool_version": TOOL_VERSION,
                "title": title,
                "section_type": _section_type(title),
                "summary": _summary(text),
                "page_start": page_start,
                "page_end": page_end,
                "tags": tags,
                "text": text,
            }
        )
    return sections


def _build_examples(blocks: list[dict[str, Any]], sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    section_by_page = sorted(sections, key=lambda item: item["page_start"])
    examples: list[dict[str, Any]] = []
    for index, block in enumerate(blocks):
        if block["type"] != "code":
            continue
        code = block["text"].strip()
        if not code:
            continue
        topic = _topic_for_page(section_by_page, block["page"])
        previous_text = _previous_text(blocks, index)
        commands = _extract_commands_from_code(code)
        examples.append(
            {
                "example_id": f"{DOC_ID}.example.{len(examples) + 1:03d}",
                "doc_id": DOC_ID,
                "topic_id": topic.get("topic_id", ""),
                "tool": TOOL,
                "tool_version": TOOL_VERSION,
                "title": topic.get("title", "UG894 Tcl example"),
                "page_start": block["page"],
                "page_end": block["page"],
                "code": code,
                "description": previous_text,
                "commands": commands,
                "tags": sorted(set(_tags_for(topic.get("title", ""), previous_text) + ["example"])),
            }
        )
    return examples


def _build_chunks(sections: list[dict[str, Any]], examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for section in sections:
        text = "\n".join([section["title"], section["summary"], section["text"]]).strip()
        chunks.append(
            {
                "chunk_id": f"{section['topic_id']}.chunk",
                "doc_id": DOC_ID,
                "tool": TOOL,
                "tool_version": TOOL_VERSION,
                "section_type": "topic",
                "anchor": section["topic_id"],
                "page_start": section["page_start"],
                "page_end": section["page_end"],
                "text": text,
            }
        )
    for example in examples:
        text = "\n".join([example["title"], example["description"], example["code"]]).strip()
        chunks.append(
            {
                "chunk_id": f"{example['example_id']}.chunk",
                "doc_id": DOC_ID,
                "tool": TOOL,
                "tool_version": TOOL_VERSION,
                "section_type": "example",
                "anchor": example["example_id"],
                "page_start": example["page_start"],
                "page_end": example["page_end"],
                "text": text,
            }
        )
    return chunks


def _topic_for_page(sections: list[dict[str, Any]], page: int) -> dict[str, Any]:
    best: dict[str, Any] = {}
    for section in sections:
        if section["page_start"] <= page:
            best = section
        if section["page_start"] > page:
            break
    return best


def _previous_text(blocks: list[dict[str, Any]], index: int) -> str:
    parts: list[str] = []
    for block in reversed(blocks[max(0, index - 4) : index]):
        if block["type"] == "text" and not block["is_heading"]:
            parts.insert(0, block["text"])
        if len(" ".join(parts)) > 280:
            break
    return _summary(" ".join(parts), limit=320)


def _extract_commands_from_code(code: str) -> list[str]:
    ignore = {
        "if", "for", "foreach", "while", "proc", "set", "puts", "return", "error",
        "catch", "expr", "else", "elseif", "switch", "namespace", "variable",
        "global", "lappend", "llength", "lindex", "lsort", "lsearch", "array",
        "incr", "append", "regsub", "regexp", "format", "open", "close", "gets",
        "flush", "break", "continue",
    }
    commands: list[str] = []
    for raw in code.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("Vivado%"):
            line = line[7:].strip() if line.startswith("Vivado%") else line
        line = re.sub(r"^\d+\.\)\s*", "", line)
        match = re.match(r"([:A-Za-z_][:\w]*)", line)
        if not match:
            continue
        command = match.group(1).split("::")[-1]
        if command in ignore or command.startswith("$"):
            continue
        if command not in commands:
            commands.append(command)
    return commands


def _block_text(block: dict[str, Any]) -> str:
    if block["type"] == "table":
        return f"Table:\n{block['text']}"
    return str(block["text"])


def _strip_code_fence(text: str) -> str:
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _html_to_text(text: str) -> str:
    text = re.sub(r"</t[dh]>\s*<t[dh][^>]*>", " | ", text)
    text = re.sub(r"</tr>\s*<tr[^>]*>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return _normalize_text(unescape(text))


def _looks_like_heading(text: str) -> bool:
    if len(text) > 80 or text.endswith("."):
        return False
    keywords = ["Tcl", "Scripts", "Objects", "Loops", "Error", "Variables", "DRC", "Vivado", "Resources"]
    return any(keyword in text for keyword in keywords)


def _is_noise_heading(text: str) -> bool:
    return text in {
        "Vivado Design Suite User Guide: Using Tcl Scripting (UG894)",
        "Additional Resources and Legal Notices",
    }


def _section_type(title: str) -> str:
    lower = title.lower()
    if "example" in lower or "script" in lower:
        return "script_flow"
    if "drc" in lower:
        return "debug_rule"
    if "object" in lower or "list" in lower:
        return "object_query"
    if "error" in lower:
        return "debug"
    if "environment" in lower or "external" in lower:
        return "integration"
    if "gui" in lower or "store" in lower:
        return "extension"
    return "guide"


def _tags_for(title: str, text: str) -> list[str]:
    haystack = f"{title} {text}".lower()
    candidates = {
        "non_project": ["non-project", "non project"],
        "project": ["project flow", "project mode"],
        "timing": ["timing", "slack"],
        "report": ["report"],
        "drc": ["drc", "design rule"],
        "object_query": ["get_cells", "get_pins", "object"],
        "error_handling": ["catch", "error"],
        "environment": ["env", "environment"],
        "external_program": ["exec", "external"],
        "hook": ["hook", "pre-hook", "post-hook"],
        "tcl_store": ["tcl store", "app"],
        "gui": ["gui", "button"],
        "ip_packager": ["ip packager", "packaging custom ip", "package ip", "packaged ip"],
        "ip_xact": ["ip-xact", "component.xml"],
        "custom_ip": ["custom ip"],
        "interface_definition": ["interface definition", "bus definition", "abstraction definition"],
        "axi": ["axi4", "axi"],
        "encryption": ["encrypt", "encryption", "ieee-1735"],
        "ip_catalog": ["ip catalog"],
        "vitis": ["vitis", "v++", "vitis-run"],
        "vitis_cli": ["command-line", "command line", "v++", "vitis-run", "xbutil", "xclbinutil"],
        "embedded": ["embedded", "zynq", "versal", "platform"],
        "platform": ["platform", "xpfm", "xsa"],
        "aie": ["ai engine", "aie"],
        "hls": ["hls", "high-level synthesis"],
        "pdm": ["power design manager", "pdm"],
        "power": ["power", "thermal", "estimation"],
        "programming": ["programming", "program device", "bitstream", "device image", "pdi"],
        "hardware_debug": ["hardware manager", "debug core", "ila", "vio", "debug probe", "logic analyzer"],
        "hw_server": ["hw_server", "hardware server", "hardware target", "xvc"],
        "jtag": ["jtag", "stapl", "svf"],
        "efuse": ["efuse", "aes key", "bbram"],
    }
    tags = [tag for tag, needles in candidates.items() if any(needle in haystack for needle in needles)]
    return sorted(set(tags))


def _summary(text: str, *, limit: int = 360) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _slug(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", normalized.lower()).strip("_")
    return slug or "section"


def _unique_slug(slug: str, used: dict[str, int]) -> str:
    count = used.get(slug, 0) + 1
    used[slug] = count
    return slug if count == 1 else f"{slug}_{count}"


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value)
    replacements = {
        "ﬁ": "fi",
        "ﬂ": "fl",
        "ﬀ": "ff",
        "ﬃ": "ffi",
        "ﬄ": "ffl",
        "‐": "-",
        "‑": "-",
        "‒": "-",
        "–": "-",
        "—": "-",
        "“": '"',
        "”": '"',
        "’": "'",
        "\u00ad": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace("AM D", "AMD")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _pdf_page_count(pdf_path: Path) -> int:
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(pdf_path)).pages)
    except Exception:
        return 0


def _relpath(path: Path, parent: Path) -> str:
    try:
        return str(path.resolve().relative_to(parent.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
