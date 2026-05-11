"""Normalize UG835 into command-level Vivado Tcl database artifacts."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DOC_ID = "xilinx.ug835.2024_2"
TOOL = "vivado"
TOOL_VERSION = "2024.2"
VENDOR = "xilinx"


@dataclass(frozen=True)
class Line:
    page: int
    text: str


def extract_ug835(workspace: Path, pdf_path: Path | None = None) -> Path:
    """Extract command-level records from the local UG835 PDF.

    The PDF is larger than MinerU flash limits. This normalizer intentionally
    uses local text extraction and does not call flash extraction.
    """

    workspace = workspace.resolve()
    if pdf_path is None:
        pdf_path = workspace / "library" / "files" / "fpga_ug_pdfs" / "UG835.pdf"
    pdf_path = pdf_path.resolve()
    if not pdf_path.is_file():
        raise FileNotFoundError(f"missing UG835 PDF: {pdf_path}")

    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - environment boundary
        raise RuntimeError("pypdf is required to extract UG835") from exc

    reader = PdfReader(str(pdf_path))
    command_names = _extract_command_names(reader)
    cleaned_lines = _extract_clean_lines(reader)
    boundaries = _find_command_boundaries(cleaned_lines, command_names)
    commands, duplicate_boundaries = _extract_commands(cleaned_lines, boundaries, command_names, pdf_path, workspace)
    intro_chunks = _extract_intro_chunks(reader, pdf_path, workspace)

    out_dir = workspace / "library" / "parsed" / "software_ug_mineru" / "xilinx_ug835" / "2024_2"
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "schema_version": 1,
        "doc_id": DOC_ID,
        "title": "Vivado Design Suite Tcl Command Reference Guide (UG835)",
        "vendor": VENDOR,
        "tool": TOOL,
        "tool_version": TOOL_VERSION,
        "source_file": _relpath(pdf_path, workspace),
        "source_type": "pdf",
        "parser": "pypdf command normalizer; MinerU flash channel not used",
        "page_count": len(reader.pages),
        "command_count": len(commands),
        "toc_command_count": len(command_names),
        "parsed_dir": _relpath(out_dir, workspace / "library"),
        "structured_artifacts": [
            _relpath(out_dir / "commands.json", workspace / "library"),
            _relpath(out_dir / "chunks.jsonl", workspace / "library"),
            _relpath(out_dir / "quality_report.json", workspace / "library"),
        ],
        "notes": [
            "Built for AI-assisted Vivado Tcl script generation, testing, and debug.",
            "Command entries are split by UG835 command headers instead of raw pages.",
            "Original PDF remains the source of truth for signoff.",
        ],
    }

    command_ids = {item["command"] for item in commands}
    missing = [name for name in command_names if name not in command_ids]
    quality = {
        "doc_id": DOC_ID,
        "page_count": len(reader.pages),
        "toc_command_count": len(command_names),
        "extracted_command_count": len(commands),
        "missing_commands": missing,
        "duplicate_boundaries": duplicate_boundaries,
        "commands_without_syntax": [item["command"] for item in commands if not item["syntax"]],
        "commands_without_examples": [item["command"] for item in commands if not item["examples_text"]],
    }

    chunks = _build_chunks(commands, intro_chunks)

    _write_json(out_dir / "metadata.json", metadata)
    _write_json(out_dir / "commands.json", {"schema_version": 1, "doc_id": DOC_ID, "commands": commands})
    _write_json(out_dir / "quality_report.json", quality)
    with (out_dir / "chunks.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    return out_dir


def _extract_command_names(reader: Any) -> list[str]:
    command_re = re.compile(r"^[a-z][a-z0-9_]*$")
    names: list[str] = []
    for page_index in range(1, min(17, len(reader.pages))):
        text = reader.pages[page_index].extract_text() or ""
        for raw in text.splitlines():
            line = _normalize_text(raw)
            if command_re.match(line) and line not in names:
                names.append(line)
    return names


def _extract_clean_lines(reader: Any) -> list[Line]:
    lines: list[Line] = []
    for page_index in range(47, len(reader.pages)):
        text = reader.pages[page_index].extract_text() or ""
        page = page_index + 1
        for raw in text.splitlines():
            line = _normalize_text(raw)
            if not line:
                continue
            if line.startswith("Vivado Design Suite Tcl Command Reference Guide"):
                continue
            if line == "Displayed in the footer":
                continue
            if re.match(r"^Page \d+ of \d+$", line):
                continue
            if line in {"★", "✎", "‼", "⚠ CAUTION!"}:
                continue
            lines.append(Line(page=page, text=line))
    return lines


def _find_command_boundaries(lines: list[Line], command_names: list[str]) -> list[int]:
    known = set(command_names)
    boundaries: list[int] = []
    seen: set[str] = set()
    for index, line in enumerate(lines):
        command = line.text
        if command not in known:
            continue
        if not _looks_like_header(lines, index, known):
            continue
        if command in seen:
            continue
        seen.add(command)
        boundaries.append(index)
    return boundaries


def _looks_like_header(lines: list[Line], index: int, known: set[str]) -> bool:
    for offset in range(1, 20):
        probe_index = index + offset
        if probe_index >= len(lines):
            return False
        probe = lines[probe_index].text
        if probe in known:
            return False
        if probe == "Syntax":
            return True
    return False


def _extract_commands(
    lines: list[Line],
    boundaries: list[int],
    command_names: list[str],
    pdf_path: Path,
    workspace: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    commands: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    known = set(command_names)
    seen: set[str] = set()

    for position, start in enumerate(boundaries):
        end = boundaries[position + 1] if position + 1 < len(boundaries) else len(lines)
        block = lines[start:end]
        command = block[0].text
        if command in seen:
            duplicates.append({"command": command, "page": block[0].page})
            continue
        seen.add(command)
        commands.append(_parse_command_block(command, block, known, pdf_path, workspace))
    return commands, duplicates


def _parse_command_block(command: str, block: list[Line], known: set[str], pdf_path: Path, workspace: Path) -> dict[str, Any]:
    texts = [item.text for item in block]
    pages = sorted({item.page for item in block})
    headings = _heading_positions(texts)

    summary_end = headings.get("Syntax", len(texts))
    summary = _join_text(texts[1:summary_end])
    syntax = _section(texts, headings, "Syntax")
    returns_text = _section(texts, headings, "Returns")
    categories = _section(texts, headings, "Categories")
    description = _section(texts, headings, "Description")
    arguments_text = _section(texts, headings, "Arguments")
    examples_text = _section(texts, headings, "Examples") or _section(texts, headings, "Example")
    see_also_text = _section(texts, headings, "See Also")
    see_also = [line for line in see_also_text.split() if line in known and line != command]
    options = _extract_options(syntax, arguments_text)

    full_text = _join_text(texts)
    return {
        "command_id": f"vivado.{command}",
        "doc_id": DOC_ID,
        "tool": TOOL,
        "tool_version": TOOL_VERSION,
        "command": command,
        "summary": summary,
        "syntax": syntax,
        "returns_text": returns_text,
        "categories": categories,
        "description": description,
        "arguments_text": arguments_text,
        "examples_text": examples_text,
        "see_also": see_also,
        "options": options,
        "source_pages": {"start": min(pages), "end": max(pages)},
        "source_file": _relpath(pdf_path, workspace),
        "full_text": full_text,
    }


def _heading_positions(texts: list[str]) -> dict[str, int]:
    wanted = {"Syntax", "Returns", "Usage", "Categories", "Description", "Arguments", "Examples", "Example", "See Also"}
    positions: dict[str, int] = {}
    for index, text in enumerate(texts):
        if text in wanted and text not in positions:
            positions[text] = index
    return positions


def _section(texts: list[str], headings: dict[str, int], name: str) -> str:
    if name not in headings:
        return ""
    start = headings[name] + 1
    next_positions = [pos for heading, pos in headings.items() if pos > headings[name] and heading != name]
    end = min(next_positions) if next_positions else len(texts)
    return _join_text(texts[start:end])


def _extract_options(syntax: str, arguments_text: str) -> list[dict[str, str]]:
    option_names = sorted(set(re.findall(r"(?<![\w])-+[A-Za-z][A-Za-z0-9_]*", f"{syntax} {arguments_text}")))
    descriptions = _extract_argument_descriptions(arguments_text)
    options: list[dict[str, str]] = []
    for name in option_names:
        description = descriptions.get(name, "")
        options.append({"name": name, "description": description, "source": "syntax_arguments"})
    return options


def _extract_argument_descriptions(arguments_text: str) -> dict[str, str]:
    descriptions: dict[str, str] = {}
    current_name = ""
    current_lines: list[str] = []
    option_start = re.compile(r"^(-[A-Za-z][A-Za-z0-9_]*)(?:\s+<[^>]+>)?\s+-\s+(.*)$")
    for raw in arguments_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        match = option_start.match(line)
        if match:
            if current_name:
                descriptions[current_name] = _join_inline(current_lines)
            current_name = match.group(1)
            current_lines = [match.group(2)]
            continue
        if current_name:
            current_lines.append(line)
    if current_name:
        descriptions[current_name] = _join_inline(current_lines)
    return descriptions


def _join_inline(lines: list[str]) -> str:
    return " ".join(line for line in lines if line).strip()


def _extract_intro_chunks(reader: Any, pdf_path: Path, workspace: Path) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for page_index in range(17, 47):
        if page_index >= len(reader.pages):
            break
        text = reader.pages[page_index].extract_text() or ""
        cleaned = "\n".join(
            line
            for line in (_normalize_text(raw) for raw in text.splitlines())
            if line
            and not line.startswith("Vivado Design Suite Tcl Command Reference Guide")
            and line != "Displayed in the footer"
            and not re.match(r"^Page \d+ of \d+$", line)
        )
        if not cleaned:
            continue
        page = page_index + 1
        chunks.append(
            {
                "chunk_id": f"{DOC_ID}.intro.p{page}",
                "doc_id": DOC_ID,
                "tool": TOOL,
                "tool_version": TOOL_VERSION,
                "section_type": "intro",
                "anchor": f"intro.page_{page}",
                "page_start": page,
                "page_end": page,
                "text": cleaned,
                "source_file": _relpath(pdf_path, workspace),
            }
        )
    return chunks


def _build_chunks(commands: list[dict[str, Any]], intro_chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks = list(intro_chunks)
    for command in commands:
        pages = command["source_pages"]
        chunks.append(
            {
                "chunk_id": f"{DOC_ID}.command.{command['command']}",
                "doc_id": DOC_ID,
                "tool": TOOL,
                "tool_version": TOOL_VERSION,
                "section_type": "command",
                "anchor": command["command_id"],
                "page_start": pages["start"],
                "page_end": pages["end"],
                "text": command["full_text"],
                "source_file": command["source_file"],
            }
        )
    return chunks


def _join_text(lines: list[str]) -> str:
    return "\n".join(line for line in lines if line).strip()


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
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _relpath(path: Path, parent: Path) -> str:
    try:
        return str(path.resolve().relative_to(parent.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
