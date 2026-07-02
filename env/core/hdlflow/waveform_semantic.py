"""Generic waveform semantic decoder framework."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from .project import require_project_instance
from .simple_yaml import load_yaml


WAVE_SEMANTIC_MANIFEST_REL = "work/loop1_rtl_tb/config/wave_semantic_manifest.yaml"
WAVE_SEMANTIC_REPORT_JSON_REL = "output/reports/loop1/waveform_semantic_report.json"
WAVE_SEMANTIC_REPORT_MD_REL = "output/reports/loop1/waveform_semantic_report.md"


@dataclass(frozen=True)
class TransactionEvent:
    event_id: str
    time_start: int
    time_end: int
    interface: str
    operation_id: str
    operation: str
    payload: str
    response: str
    latency: int
    status: str


class WaveformDecoder(Protocol):
    def decode(self, window: dict[str, Any]) -> list[TransactionEvent]:
        ...


class UnsupportedDecoder:
    def decode(self, window: dict[str, Any]) -> list[TransactionEvent]:
        return [
            TransactionEvent(
                event_id=str(window.get("window_id") or "unsupported"),
                time_start=0,
                time_end=0,
                interface=str(window.get("interface_name") or ""),
                operation_id=str(window.get("operation_id") or ""),
                operation="unsupported",
                payload="",
                response="",
                latency=0,
                status="UNSUPPORTED",
            )
        ]


class EventListDecoder:
    def decode(self, window: dict[str, Any]) -> list[TransactionEvent]:
        rows = _as_list(window.get("observed_events") or window.get("decoded_events"))
        if not rows and window.get("event_source"):
            rows = _load_event_source(Path(str(window.get("_project_root") or ".")), str(window.get("event_source")))
        events: list[TransactionEvent] = []
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                continue
            events.append(
                TransactionEvent(
                    event_id=str(row.get("event_id") or row.get("txn_id") or f"{window.get('window_id', 'event')}_{index:04d}"),
                    time_start=_int_or_zero(row.get("time_start")),
                    time_end=_int_or_zero(row.get("time_end")),
                    interface=str(row.get("interface") or row.get("observed_interface") or window.get("interface_name") or ""),
                    operation_id=str(row.get("operation_id") or row.get("operation") or window.get("operation_id") or ""),
                    operation=str(row.get("operation") or row.get("operation_id") or row.get("sent") or ""),
                    payload=str(row.get("payload") or row.get("sent") or ""),
                    response=str(row.get("response") or row.get("actual") or ""),
                    latency=_int_or_zero(row.get("latency") or row.get("latency_cycles")),
                    status=str(row.get("status") or row.get("result") or "UNKNOWN").upper(),
                )
            )
        return events


class VcdSignalDecoder:
    def decode(self, window: dict[str, Any]) -> list[TransactionEvent]:
        project = Path(str(window.get("_project_root") or "."))
        vcd_path = Path(str(window.get("vcd_path") or window.get("waveform_path") or ""))
        if not vcd_path.is_absolute():
            vcd_path = project / vcd_path
        if not vcd_path.exists():
            return []
        signal_map = window.get("signal_map") if isinstance(window.get("signal_map"), dict) else {}
        valid_name = str(signal_map.get("valid") or signal_map.get("event") or signal_map.get("valid_signal") or "")
        response_name = str(signal_map.get("response") or signal_map.get("data") or signal_map.get("response_signal") or "")
        payload_name = str(signal_map.get("payload") or signal_map.get("payload_signal") or "")
        operation_name = str(signal_map.get("operation") or signal_map.get("operation_signal") or "")
        if not valid_name:
            return []
        definitions, changes = _parse_vcd(vcd_path)
        valid_symbol = _resolve_symbol(definitions, valid_name)
        if not valid_symbol:
            return []
        response_symbol = _resolve_symbol(definitions, response_name)
        payload_symbol = _resolve_symbol(definitions, payload_name)
        operation_symbol = _resolve_symbol(definitions, operation_name)
        operation_default = str(window.get("operation_id") or window.get("operation") or "")
        interface = str(window.get("interface_name") or "")
        events: list[TransactionEvent] = []
        last_valid = "0"
        values: dict[str, str] = {}
        for time, symbol, value in changes:
            values[symbol] = value
            valid = _bit_value(values.get(valid_symbol, "0"))
            if symbol != valid_symbol or valid != "1" or last_valid == "1":
                last_valid = valid
                continue
            response = _format_signal_value(values.get(response_symbol, "")) if response_symbol else ""
            payload = _format_signal_value(values.get(payload_symbol, "")) if payload_symbol else ""
            operation_value = _format_signal_value(values.get(operation_symbol, "")) if operation_symbol else operation_default
            events.append(
                TransactionEvent(
                    event_id=f"{window.get('window_id', 'vcd')}_{time}",
                    time_start=time,
                    time_end=time,
                    interface=interface,
                    operation_id=operation_default,
                    operation=operation_value or operation_default,
                    payload=payload,
                    response=response,
                    latency=0,
                    status="PASS",
                )
            )
            last_valid = valid
        return events


DECODER_REGISTRY: dict[str, WaveformDecoder] = {
    "spi_decoder": UnsupportedDecoder(),
    "axi_lite_decoder": UnsupportedDecoder(),
    "apb_decoder": UnsupportedDecoder(),
    "stream_decoder": VcdSignalDecoder(),
    "vcd_signal_decoder": VcdSignalDecoder(),
    "gpio_event_decoder": EventListDecoder(),
    "event_list_decoder": EventListDecoder(),
    "custom_decoder": EventListDecoder(),
}


def load_wave_semantic_manifest(project_path: Path) -> list[dict[str, Any]]:
    project = require_project_instance(project_path)
    path = project / WAVE_SEMANTIC_MANIFEST_REL
    if not path.exists():
        return []
    data = load_yaml(path)
    windows = data.get("windows", []) if isinstance(data, dict) else []
    return [window for window in windows if isinstance(window, dict)] if isinstance(windows, list) else []


def write_waveform_semantic_report(project_path: Path) -> Path:
    project = require_project_instance(project_path)
    windows: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    failures: list[str] = []
    for window in load_wave_semantic_manifest(project):
        window = dict(window)
        window["_project_root"] = str(project)
        decoder = DECODER_REGISTRY.get(str(window.get("decoder") or ""), UnsupportedDecoder())
        decoded = decoder.decode(window)
        decoded_rows = [asdict(event) for event in decoded]
        match_failures = _window_failures(window, decoded)
        if match_failures:
            failures.extend(match_failures)
        events.extend(decoded_rows)
        window_status = "FAIL" if match_failures else "PASS"
        windows.append(
            {
                "window_id": window.get("window_id") or window.get("name") or "",
                "operation_id": window.get("operation_id") or "",
                "interface_name": window.get("interface_name") or "",
                "decoder": window.get("decoder") or "",
                "evidence_level": window.get("evidence_level") or "",
                "expected_event_count": len(_as_list(window.get("expected_events"))),
                "decoded_event_count": len(decoded_rows),
                "status": window_status,
                "failures": match_failures,
            }
        )
    result = "PASS" if windows and not failures else "FAIL"
    json_path = project / WAVE_SEMANTIC_REPORT_JSON_REL
    md_path = project / WAVE_SEMANTIC_REPORT_MD_REL
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project": project.name,
                "result": result,
                "windows": windows,
                "decoded_transactions": events,
                "failures": failures,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    md_path.write_text(_format_report(result, windows, events, failures), encoding="utf-8")
    return json_path


def _window_failures(window: dict[str, Any], decoded: list[TransactionEvent]) -> list[str]:
    failures: list[str] = []
    window_id = str(window.get("window_id") or window.get("name") or "window")
    if not decoded:
        failures.append(f"{window_id}: decoder produced no transaction events")
        return failures
    if any(event.status == "UNSUPPORTED" for event in decoded):
        failures.append(f"{window_id}: decoder {window.get('decoder')} is unsupported")
        return failures
    expected_events = _as_list(window.get("expected_events"))
    if str(window.get("evidence_level") or "").lower() == "verification" and not expected_events:
        failures.append(f"{window_id}: verification window has no expected_events")
    for index, expected in enumerate(expected_events, start=1):
        if not isinstance(expected, dict):
            failures.append(f"{window_id}: expected_events[{index}] is not a mapping")
            continue
        if not any(_matches_expected(event, expected) for event in decoded):
            failures.append(f"{window_id}: expected_events[{index}] not observed")
    return failures


def _matches_expected(event: TransactionEvent, expected: dict[str, Any]) -> bool:
    fields = {
        "interface": event.interface,
        "interface_name": event.interface,
        "operation": event.operation,
        "operation_id": event.operation_id or event.operation,
        "payload": event.payload,
        "sent": event.payload,
        "response": event.response,
        "actual": event.response,
        "status": event.status,
        "result": event.status,
    }
    for key, expected_value in expected.items():
        if key in {"event_id", "time_start", "time_end", "latency", "latency_cycles"}:
            continue
        actual = fields.get(str(key), None)
        if actual is None:
            continue
        if str(actual).lower() != str(expected_value).lower():
            return False
    return True


def _format_report(result: str, windows: list[dict[str, Any]], events: list[dict[str, Any]], failures: list[str]) -> str:
    lines = [
        "# Waveform Semantic Report",
        "",
        f"- result: {result}",
        "",
        "## Windows",
        "| Window | Decoder | Evidence Level | Expected | Decoded | Status |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for window in windows:
        lines.append(
            f"| {window.get('window_id')} | {window.get('decoder')} | {window.get('evidence_level')} | "
            f"{window.get('expected_event_count')} | {window.get('decoded_event_count')} | {window.get('status')} |"
        )
    lines.extend(["", "## Decoded Transactions", "| Event | Interface | Operation | Response | Status |", "| --- | --- | --- | --- | --- |"])
    for event in events:
        lines.append(
            f"| {event.get('event_id')} | {event.get('interface')} | {event.get('operation')} | {event.get('response')} | {event.get('status')} |"
        )
    lines.extend(["", "## Failures"])
    if failures:
        for failure in failures:
            lines.append(f"- {failure}")
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _load_event_source(project: Path, source: str) -> list[Any]:
    path = Path(source)
    if not path.is_absolute():
        path = project / source
    if not path.exists():
        return []
    try:
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = load_yaml(path)
    except Exception:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("events", "decoded_transactions", "transactions"):
            rows = data.get(key)
            if isinstance(rows, list):
                return rows
    return []


def _parse_vcd(path: Path) -> tuple[dict[str, str], list[tuple[int, str, str]]]:
    definitions: dict[str, str] = {}
    changes: list[tuple[int, str, str]] = []
    current_time = 0
    in_definitions = True
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        if in_definitions and line.startswith("$var "):
            tokens = line.split()
            if len(tokens) >= 5:
                symbol = tokens[3]
                name = tokens[4]
                if len(tokens) >= 6 and tokens[5].startswith("["):
                    name = f"{name} {tokens[5]}"
                definitions[symbol] = name
            continue
        if line.startswith("$enddefinitions"):
            in_definitions = False
            continue
        if in_definitions:
            continue
        if line.startswith("#"):
            try:
                current_time = int(line[1:])
            except ValueError:
                current_time = 0
            continue
        if line[0] in "01xXzZ" and len(line) >= 2:
            changes.append((current_time, line[1:], line[0]))
            continue
        if line.startswith(("b", "B")) and " " in line:
            bits, symbol = line.split(None, 1)
            changes.append((current_time, symbol.strip(), bits[1:]))
    return definitions, changes


def _resolve_symbol(definitions: dict[str, str], signal_name: str) -> str:
    if not signal_name:
        return ""
    for symbol, name in definitions.items():
        if signal_name == symbol or signal_name == name or signal_name == name.split()[0]:
            return symbol
    for symbol, name in definitions.items():
        if name.endswith(signal_name) or name.split()[0].endswith(signal_name):
            return symbol
    return ""


def _bit_value(value: str) -> str:
    if not value:
        return "0"
    return value[-1].lower()


def _format_signal_value(value: str) -> str:
    if not value:
        return ""
    text = value.lower()
    if set(text) <= {"0", "1"} and len(text) > 1:
        return f"0x{int(text, 2):X}"
    return text.upper() if text.startswith(("x", "z")) else text


def _as_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    return value if isinstance(value, list) else [value]


def _int_or_zero(value: Any) -> int:
    try:
        return int(str(value))
    except Exception:
        return 0
