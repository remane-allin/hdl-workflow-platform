"""Shared Loop1 waveform types and helpers for the pywellen query gate."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


LOOP1_LOG_REL = "work/loop1_rtl_tb/current/log/modelsim.log"
LOOP1_WAVE_DIR_REL = "output/sim/loop1/wave"

UNKNOWN_BITS = {"x", "X", "z", "Z"}
CLOCK_NAME_RE = re.compile(r"(^|[._])(clk|clock)([._]|$)", re.IGNORECASE)
RESET_NAME_RE = re.compile(r"(^|[._])(rst|reset|rst_n|reset_n)([._]|$)", re.IGNORECASE)


@dataclass(frozen=True)
class WaveWindow:
    window_id: str
    start: int
    end: int
    scope: str


@dataclass(frozen=True)
class VcdSignal:
    path: str
    size: int
    type_name: str
    id_code: str


def _parse_wave_windows(log_text: str) -> tuple[list[WaveWindow], list[str]]:
    windows: list[WaveWindow] = []
    errors: list[str] = []
    active: dict[str, tuple[int, str]] = {}

    for line in log_text.splitlines():
        if "HDLFLOW_WAVE_WINDOW" in line:
            fields = _parse_fields(line)
            window_id = fields.get("id") or fields.get("name")
            start = _parse_time(fields.get("start"))
            end = _parse_time(fields.get("end"))
            if not window_id or start is None or end is None:
                errors.append(f"malformed HDLFLOW_WAVE_WINDOW marker: {line.strip()}")
                continue
            windows.append(_make_window(window_id, start, end, fields.get("scope") or "top", errors))
            continue
        if "HDLFLOW_WAVE_BEGIN" in line:
            fields = _parse_fields(line)
            window_id = fields.get("id") or fields.get("name")
            start = _parse_time(fields.get("time"))
            if not window_id or start is None:
                errors.append(f"malformed HDLFLOW_WAVE_BEGIN marker: {line.strip()}")
                continue
            active[window_id] = (start, fields.get("scope") or "top")
            continue
        if "HDLFLOW_WAVE_END" in line:
            fields = _parse_fields(line)
            window_id = fields.get("id") or fields.get("name")
            end = _parse_time(fields.get("time"))
            if not window_id or end is None:
                errors.append(f"malformed HDLFLOW_WAVE_END marker: {line.strip()}")
                continue
            if window_id not in active:
                errors.append(f"HDLFLOW_WAVE_END without matching begin: {window_id}")
                continue
            start, scope = active.pop(window_id)
            windows.append(_make_window(window_id, start, end, scope, errors))

    for window_id in sorted(active):
        errors.append(f"HDLFLOW_WAVE_BEGIN without matching end: {window_id}")
    return windows, errors


def _make_window(window_id: str, start: int, end: int, scope: str, errors: list[str]) -> WaveWindow:
    if end < start:
        errors.append(f"waveform window {window_id} end time is before start time")
    return WaveWindow(window_id=str(window_id), start=start, end=end, scope=scope)


def _latest_vcd(project: Path) -> Path | None:
    wave_dir = project / LOOP1_WAVE_DIR_REL
    if not wave_dir.exists():
        return None
    matches = sorted(wave_dir.glob("*.vcd"), key=lambda path: path.stat().st_mtime)
    return matches[-1] if matches else None


def _latest_wlf(project: Path) -> Path | None:
    wave_dir = project / LOOP1_WAVE_DIR_REL
    if not wave_dir.exists():
        return None
    matches = sorted(wave_dir.glob("*.wlf"), key=lambda path: path.stat().st_mtime)
    return matches[-1] if matches else None


def _matching_wlf(project: Path, vcd_path: Path | None) -> Path | None:
    if vcd_path is None:
        return _latest_wlf(project)
    stem = vcd_path.stem
    candidates: list[Path] = []
    if stem.endswith("_top"):
        candidates.append(vcd_path.with_name(stem[:-4] + ".wlf"))
    candidates.append(vcd_path.with_suffix(".wlf"))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return _latest_wlf(project)


def _is_under_rel(project: Path, path: Path, rel: str) -> bool:
    try:
        path.resolve().relative_to((project / rel).resolve())
    except ValueError:
        return False
    return True


def _parse_fields(line: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for key, value in re.findall(r"([A-Za-z0-9_]+)=(\"[^\"]*\"|[^ \t\r\n]+)", line):
        fields[key] = value.strip('"')
    return fields


def _parse_time(value: str | None) -> int | None:
    if value is None:
        return None
    text = str(value).strip().strip('"')
    match = re.match(r"^([0-9]+)", text)
    return int(match.group(1)) if match else None


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _has_unknown(value: str) -> bool:
    return any(char in UNKNOWN_BITS for char in value)


def _is_clock(path: str) -> bool:
    return bool(CLOCK_NAME_RE.search(path))


def _is_reset(path: str) -> bool:
    return bool(RESET_NAME_RE.search(path))


def _rel(project: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")
