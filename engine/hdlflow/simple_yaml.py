"""Small YAML reader for the platform's configuration subset.

The local Python environment has an unstable PyYAML build, so the engine uses
this dependency-free parser for simple mappings, scalar lists, and empty lists.
It is intentionally narrow and should not be treated as a general YAML parser.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return parse_yaml(text)


def parse_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = _strip_comment(raw_line).rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip().lstrip("\ufeff")

        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise ValueError(f"invalid indentation at line {lineno}: {raw_line}")

        parent = stack[-1][1]

        if content == "-" or content.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"list item without list parent at line {lineno}: {raw_line}")
            item_text = "" if content == "-" else content[2:].strip()
            if not item_text:
                child = _infer_child_container(text.splitlines(), lineno, indent)
                parent.append(child)
                stack.append((indent, child))
                continue
            if ":" in item_text and not _is_quoted(item_text):
                key, value = item_text.split(":", 1)
                item: dict[str, Any] = {}
                value = value.strip()
                if value:
                    item[key.strip()] = _parse_scalar(value)
                else:
                    child = _infer_child_container(text.splitlines(), lineno, indent)
                    item[key.strip()] = child
                parent.append(item)
                stack.append((indent, item))
                continue
            parent.append(_parse_scalar(item_text))
            continue

        if ":" not in content:
            raise ValueError(f"expected key/value at line {lineno}: {raw_line}")

        key, value = content.split(":", 1)
        key = key.strip()
        value = value.strip()

        if not isinstance(parent, dict):
            raise ValueError(f"mapping entry without mapping parent at line {lineno}: {raw_line}")

        if value:
            parent[key] = _parse_scalar(value)
            continue

        child = _infer_child_container(text.splitlines(), lineno, indent)
        parent[key] = child
        stack.append((indent, child))

    return root


def _infer_child_container(lines: list[str], current_lineno: int, current_indent: int) -> Any:
    for future in lines[current_lineno:]:
        stripped = _strip_comment(future).rstrip()
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        if indent <= current_indent:
            return {}
        return [] if stripped.strip().startswith("- ") else {}
    return {}


def _parse_scalar(value: str) -> Any:
    if value == "[]":
        return []
    if value == "{}":
        return {}
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _is_quoted(value: str) -> bool:
    return (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'"))


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for index, char in enumerate(line):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            return line[:index]
    return line
