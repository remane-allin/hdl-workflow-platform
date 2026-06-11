"""Loop1 waveform secondary checks from ModelSim VCD evidence."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .project import require_project_instance


LOOP1_LOG_REL = "output/reports/loop1/modelsim_loop1.log"
LOOP1_WAVEFORM_JSON_REL = "output/reports/loop1/waveform_check.json"
LOOP1_WAVEFORM_MD_REL = "output/reports/loop1/waveform_check.md"
LOOP1_WAVEFORM_HIERARCHY_JSON_REL = "output/reports/loop1/waveform_hierarchy.json"
LOOP1_WAVEFORM_HIERARCHY_MD_REL = "output/reports/loop1/waveform_hierarchy.md"
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


@dataclass(frozen=True)
class WaveformCheckResult:
    report_path: Path
    json_path: Path
    hierarchy_report_path: Path
    hierarchy_json_path: Path
    ok: bool
    errors: list[str]
    warnings: list[str]
    window_count: int
    signal_count: int


def check_loop1_waveform(project_path: Path, *, vcd_path: Path | None = None, log_path: Path | None = None) -> WaveformCheckResult:
    """Check Loop1 top-level VCD windows emitted by the directed TB."""

    project = require_project_instance(project_path)
    log = log_path or project / LOOP1_LOG_REL
    if vcd_path is not None and not vcd_path.is_absolute():
        vcd_path = project / vcd_path
    if vcd_path is None:
        vcd_path = _latest_vcd(project)
    wlf_path = _matching_wlf(project, vcd_path) if vcd_path else _latest_wlf(project)

    errors: list[str] = []
    warnings: list[str] = []
    windows: list[WaveWindow] = []
    signals: dict[str, VcdSignal] = {}
    events: dict[str, list[tuple[int, str]]] = {}
    signal_count = 0
    window_results: list[dict[str, Any]] = []

    if not log.is_file():
        errors.append(f"missing Loop1 ModelSim log: {_rel(project, log)}")
    else:
        windows, marker_errors = _parse_wave_windows(log.read_text(encoding="utf-8", errors="ignore"))
        errors.extend(marker_errors)
        if not windows:
            errors.append(
                "missing HDLFLOW_WAVE_WINDOW or HDLFLOW_WAVE_BEGIN/HDLFLOW_WAVE_END markers; "
                "Loop1 TB must mark waveform check windows"
            )

    if vcd_path is None:
        errors.append(f"missing Loop1 VCD waveform under {LOOP1_WAVE_DIR_REL}")
    elif not vcd_path.is_file():
        errors.append(f"VCD waveform file does not exist: {vcd_path}")
    elif not _is_under_rel(project, vcd_path, LOOP1_WAVE_DIR_REL):
        errors.append(
            "Loop1 VCD waveform must be analyzed from the canonical output deliverable directory "
            f"{LOOP1_WAVE_DIR_REL}: {_rel(project, vcd_path)}"
        )
    else:
        try:
            signals, events = _parse_vcd(vcd_path)
        except Exception as exc:
            errors.append(f"failed to parse VCD waveform {_rel(project, vcd_path)}: {exc}")
        else:
            signal_count = len(signals)
            if not signals:
                errors.append(f"VCD waveform contains no signal declarations: {_rel(project, vcd_path)}")
            if windows:
                window_results = _evaluate_windows(windows, signals, events)
                for item in window_results:
                    for issue in item["issues"]:
                        errors.append(f"waveform window {item['id']}: {issue}")

    if wlf_path is None:
        errors.append(f"missing Loop1 WLF waveform under {LOOP1_WAVE_DIR_REL}")
    elif not wlf_path.is_file():
        errors.append(f"WLF waveform file does not exist: {wlf_path}")
    elif not _is_under_rel(project, wlf_path, LOOP1_WAVE_DIR_REL):
        errors.append(
            "Loop1 WLF waveform must be delivered from the canonical output directory "
            f"{LOOP1_WAVE_DIR_REL}: {_rel(project, wlf_path)}"
        )

    hierarchy_json_path = project / LOOP1_WAVEFORM_HIERARCHY_JSON_REL
    hierarchy_report_path = project / LOOP1_WAVEFORM_HIERARCHY_MD_REL
    hierarchy_payload = _build_hierarchy_payload(project, vcd_path, wlf_path, signals, events)
    hierarchy_json_path.parent.mkdir(parents=True, exist_ok=True)
    hierarchy_json_path.write_text(json.dumps(hierarchy_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    hierarchy_report_path.write_text(_format_hierarchy_report(hierarchy_payload), encoding="utf-8")
    if hierarchy_payload["signal_count"] <= 0:
        errors.append(f"Loop1 waveform hierarchy contains no signals: {LOOP1_WAVEFORM_HIERARCHY_JSON_REL}")

    payload = {
        "schema_version": 1,
        "project": project.name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "result": "PASS" if not errors else "FAIL",
        "log": _rel(project, log),
        "wave_dir": LOOP1_WAVE_DIR_REL,
        "vcd": _rel(project, vcd_path) if vcd_path else None,
        "wlf": _rel(project, wlf_path) if wlf_path else None,
        "hierarchy": LOOP1_WAVEFORM_HIERARCHY_JSON_REL,
        "window_count": len(windows),
        "signal_count": signal_count,
        "windows": window_results,
        "errors": errors,
        "warnings": warnings,
    }
    json_path = project / LOOP1_WAVEFORM_JSON_REL
    report_path = project / LOOP1_WAVEFORM_MD_REL
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(_format_report(payload), encoding="utf-8")
    return WaveformCheckResult(
        report_path,
        json_path,
        hierarchy_report_path,
        hierarchy_json_path,
        not errors,
        errors,
        warnings,
        len(windows),
        signal_count,
    )


def check_loop1_waveform_report(project_path: Path, report_rel: str = LOOP1_WAVEFORM_JSON_REL) -> list[str]:
    """Return gate errors for the persisted Loop1 waveform check report."""

    project = require_project_instance(project_path)
    path = project / report_rel
    if not path.is_file():
        return [f"missing Loop1 waveform check report: {report_rel}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"Loop1 waveform check report is not parseable: {exc}"]
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append(f"{report_rel} schema_version must be 1")
    if data.get("result") != "PASS":
        errors.append(f"{report_rel} result must be PASS")
    if _safe_int(data.get("window_count")) <= 0:
        errors.append(f"{report_rel} must include at least one waveform check window")
    if _safe_int(data.get("signal_count")) <= 0:
        errors.append(f"{report_rel} must include at least one checked signal")
    if data.get("wave_dir") != LOOP1_WAVE_DIR_REL:
        errors.append(f"{report_rel} wave_dir must be {LOOP1_WAVE_DIR_REL}")
    for key in ("vcd", "wlf"):
        rel = str(data.get(key) or "").replace("\\", "/")
        if not rel:
            errors.append(f"{report_rel} must record a Loop1 {key.upper()} deliverable")
            continue
        if not rel.startswith(LOOP1_WAVE_DIR_REL + "/"):
            errors.append(f"{report_rel} {key} must live under {LOOP1_WAVE_DIR_REL}: {rel}")
            continue
        if not (project / rel).is_file():
            errors.append(f"{report_rel} {key} file is missing: {rel}")
    hierarchy_rel = str(data.get("hierarchy") or "").replace("\\", "/")
    if hierarchy_rel != LOOP1_WAVEFORM_HIERARCHY_JSON_REL:
        errors.append(f"{report_rel} hierarchy must be {LOOP1_WAVEFORM_HIERARCHY_JSON_REL}")
    else:
        hierarchy_errors = _check_hierarchy_report(project, hierarchy_rel, data)
        errors.extend(hierarchy_errors)
    for item in data.get("errors") or []:
        errors.append(str(item))
    return errors


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


def _parse_vcd(path: Path) -> tuple[dict[str, VcdSignal], dict[str, list[tuple[int, str]]]]:
    signals: dict[str, VcdSignal] = {}
    events: dict[str, list[tuple[int, str]]] = {}
    scope: list[str] = []
    current_time = 0
    in_definitions = True
    event_count = 0
    event_limit = 2_000_000

    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        if in_definitions:
            if line.startswith("$scope"):
                parts = line.split()
                if len(parts) >= 3:
                    scope.append(parts[2])
                continue
            if line.startswith("$upscope"):
                if scope:
                    scope.pop()
                continue
            if line.startswith("$var"):
                match = re.match(r"\$var\s+(\S+)\s+(\d+)\s+(\S+)\s+(.+?)\s+\$end", line)
                if match:
                    type_name, size_text, id_code, name = match.groups()
                    path_name = ".".join([*scope, name.strip()])
                    signals[id_code] = VcdSignal(path=path_name, size=int(size_text), type_name=type_name, id_code=id_code)
                    events[id_code] = []
                continue
            if line.startswith("$enddefinitions"):
                in_definitions = False
                continue
            continue

        if line.startswith("#"):
            current_time = int(line[1:])
            continue
        parsed = _parse_vcd_change(line)
        if parsed is None:
            continue
        id_code, value = parsed
        if id_code not in events:
            continue
        events[id_code].append((current_time, value))
        event_count += 1
        if event_count > event_limit:
            raise ValueError("VCD contains too many tracked events; narrow the Loop1 wave dump or windows")

    return signals, events


def _parse_vcd_change(line: str) -> tuple[str, str] | None:
    if not line:
        return None
    if line[0] in {"0", "1", "x", "X", "z", "Z"}:
        return line[1:], line[0]
    if line[0] in {"b", "B"}:
        parts = line.split()
        if len(parts) == 2:
            return parts[1], parts[0][1:]
    if line[0] in {"r", "R", "s", "S"}:
        parts = line.split()
        if len(parts) == 2:
            return parts[1], parts[0][1:]
    return None


def _evaluate_windows(
    windows: list[WaveWindow],
    signals: dict[str, VcdSignal],
    events: dict[str, list[tuple[int, str]]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for window in windows:
        issues: list[str] = []
        transition_count = 0
        non_clock_transition_count = 0
        clock_edge_count = 0
        unknowns: list[str] = []
        checked_signals = 0

        for id_code, signal in signals.items():
            signal_events = events.get(id_code, [])
            if not signal_events:
                continue
            checked_signals += 1
            values = _values_covering_window(signal_events, window.start, window.end)
            if any(_has_unknown(value) for _, value in values):
                unknowns.append(signal.path)
            in_window = [(time, value) for time, value in signal_events if window.start <= time <= window.end]
            transition_count += len(in_window)
            if _is_clock(signal.path):
                clock_edge_count += len(in_window)
            elif not _is_reset(signal.path):
                non_clock_transition_count += len(in_window)

        if unknowns:
            issues.append("unknown X/Z value observed on " + ", ".join(sorted(set(unknowns))[:8]))
        if transition_count == 0:
            issues.append("no VCD transitions were observed inside the window")
        if clock_edge_count == 0 and any(_is_clock(signal.path) for signal in signals.values()):
            issues.append("no clock edge was observed inside the window")
        if non_clock_transition_count == 0:
            issues.append("no non-clock top-level activity was observed inside the window")

        results.append(
            {
                "id": window.window_id,
                "start": window.start,
                "end": window.end,
                "scope": window.scope,
                "status": "PASS" if not issues else "FAIL",
                "signals_checked": checked_signals,
                "transition_count": transition_count,
                "non_clock_transition_count": non_clock_transition_count,
                "clock_edge_count": clock_edge_count,
                "issues": issues,
            }
        )
    return results


def _values_covering_window(events: list[tuple[int, str]], start: int, end: int) -> list[tuple[int, str]]:
    values: list[tuple[int, str]] = []
    last_before: tuple[int, str] | None = None
    for time, value in events:
        if time < start:
            last_before = (time, value)
            continue
        if time > end:
            break
        values.append((time, value))
    if last_before is not None:
        values.insert(0, last_before)
    return values


def _format_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Loop1 Waveform Check",
        "",
        f"- project: {payload['project']}",
        f"- generated_at: {payload['generated_at']}",
        f"- result: {payload['result']}",
        f"- log: {payload['log']}",
        f"- wave_dir: {payload['wave_dir']}",
        f"- vcd: {payload['vcd']}",
        f"- wlf: {payload['wlf']}",
        f"- hierarchy: {payload['hierarchy']}",
        f"- window_count: {payload['window_count']}",
        f"- signal_count: {payload['signal_count']}",
        "",
        "## Windows",
        "",
        "| Window | Time Range | Status | Signals | Transitions | Issues |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in payload.get("windows", []):
        issues = "; ".join(item.get("issues") or ["none"])
        lines.append(
            f"| {item['id']} | {item['start']}..{item['end']} | {item['status']} | "
            f"{item['signals_checked']} | {item['transition_count']} | {issues} |"
        )
    lines.extend(["", "## Errors", ""])
    lines.extend([f"- {item}" for item in payload.get("errors", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {item}" for item in payload.get("warnings", [])] or ["- none"])
    return "\n".join(lines) + "\n"


def _build_hierarchy_payload(
    project: Path,
    vcd_path: Path | None,
    wlf_path: Path | None,
    signals: dict[str, VcdSignal],
    events: dict[str, list[tuple[int, str]]],
) -> dict[str, Any]:
    scopes: dict[str, dict[str, Any]] = {}
    for signal in signals.values():
        scope, name = _split_signal_scope(signal.path)
        item = scopes.setdefault(
            scope,
            {
                "scope": scope,
                "parent": _parent_scope(scope),
                "depth": 0 if not scope else len(scope.split(".")),
                "signal_count": 0,
                "clock_count": 0,
                "reset_count": 0,
                "transition_count": 0,
                "signals": [],
            },
        )
        transition_count = len(events.get(signal.id_code, []))
        kind = _signal_kind(signal.path)
        item["signal_count"] += 1
        item["transition_count"] += transition_count
        if kind == "clock":
            item["clock_count"] += 1
        if kind == "reset":
            item["reset_count"] += 1
        item["signals"].append(
            {
                "name": name,
                "path": signal.path,
                "size": signal.size,
                "type": signal.type_name,
                "kind": kind,
                "transition_count": transition_count,
            }
        )

    scope_items = []
    for item in scopes.values():
        item["signals"] = sorted(item["signals"], key=lambda signal: signal["path"])
        scope_items.append(item)
    scope_items.sort(key=lambda item: (item["depth"], item["scope"]))
    return {
        "schema_version": 1,
        "project": project.name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "wave_dir": LOOP1_WAVE_DIR_REL,
        "vcd": _rel(project, vcd_path) if vcd_path else None,
        "wlf": _rel(project, wlf_path) if wlf_path else None,
        "scope_count": len(scope_items),
        "signal_count": len(signals),
        "max_depth": max((item["depth"] for item in scope_items), default=0),
        "scopes": scope_items,
    }


def _format_hierarchy_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Loop1 Waveform Hierarchy",
        "",
        f"- project: {payload['project']}",
        f"- generated_at: {payload['generated_at']}",
        f"- wave_dir: {payload['wave_dir']}",
        f"- vcd: {payload['vcd']}",
        f"- wlf: {payload['wlf']}",
        f"- scope_count: {payload['scope_count']}",
        f"- signal_count: {payload['signal_count']}",
        f"- max_depth: {payload['max_depth']}",
        "",
        "## Scopes",
        "",
        "| Scope | Parent | Depth | Signals | Clocks | Resets | Transitions |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in payload.get("scopes", []):
        lines.append(
            f"| {item['scope']} | {item.get('parent') or 'none'} | {item['depth']} | "
            f"{item['signal_count']} | {item['clock_count']} | {item['reset_count']} | {item['transition_count']} |"
        )
    return "\n".join(lines) + "\n"


def _check_hierarchy_report(project: Path, hierarchy_rel: str, check_data: dict[str, Any]) -> list[str]:
    path = project / hierarchy_rel
    if not path.is_file():
        return [f"missing Loop1 waveform hierarchy report: {hierarchy_rel}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"Loop1 waveform hierarchy report is not parseable: {exc}"]
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append(f"{hierarchy_rel} schema_version must be 1")
    if data.get("wave_dir") != LOOP1_WAVE_DIR_REL:
        errors.append(f"{hierarchy_rel} wave_dir must be {LOOP1_WAVE_DIR_REL}")
    if data.get("vcd") != check_data.get("vcd"):
        errors.append(f"{hierarchy_rel} vcd must match {LOOP1_WAVEFORM_JSON_REL}")
    if data.get("wlf") != check_data.get("wlf"):
        errors.append(f"{hierarchy_rel} wlf must match {LOOP1_WAVEFORM_JSON_REL}")
    if _safe_int(data.get("scope_count")) <= 0:
        errors.append(f"{hierarchy_rel} must include at least one VCD scope")
    if _safe_int(data.get("signal_count")) <= 0:
        errors.append(f"{hierarchy_rel} must include at least one VCD signal")
    if not isinstance(data.get("scopes"), list) or not data.get("scopes"):
        errors.append(f"{hierarchy_rel} scopes must be a non-empty list")
    return errors


def _split_signal_scope(path: str) -> tuple[str, str]:
    if "." not in path:
        return "", path
    scope, name = path.rsplit(".", 1)
    return scope, name


def _parent_scope(scope: str) -> str | None:
    if not scope or "." not in scope:
        return None
    return scope.rsplit(".", 1)[0]


def _signal_kind(path: str) -> str:
    if _is_clock(path):
        return "clock"
    if _is_reset(path):
        return "reset"
    return "signal"


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
