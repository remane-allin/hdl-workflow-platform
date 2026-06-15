"""Loop1 semantic waveform gate built on the query backend."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .project import require_project_instance
from .simple_yaml import load_yaml
from .waveform import LOOP1_WAVE_DIR_REL, WaveWindow, _is_clock, _is_reset, _rel
from .waveform_backend import load_loop1_waveform
from .waveform_query import WaveformQuery


TOP_WAVE_MANIFEST_REL = "work/loop1_rtl_tb/config/top_wave_manifest.yaml"
WAVEFORM_QUERY_REPORT_REL = "output/reports/loop1/waveform_query_report.md"
WAVEFORM_GATE_JSON_REL = "output/reports/loop1/waveform_gate.json"
QUERY_TRANSCRIPT_JSON_REL = "output/reports/loop1/query_transcript.json"
LOOP1_REPORT_JSON_REL = "output/reports/loop1/loop1_report.json"


@dataclass(frozen=True)
class WaveformGateResult:
    report_path: Path
    json_path: Path
    transcript_path: Path
    ok: bool
    errors: list[str]
    warnings: list[str]
    check_count: int


def run_loop1_waveform_gate(
    project_path: Path,
    *,
    vcd_path: Path | None = None,
    log_path: Path | None = None,
    manifest_path: Path | None = None,
) -> WaveformGateResult:
    """Run the controlled top-port waveform query gate."""

    project = require_project_instance(project_path)
    manifest_file = manifest_path or project / TOP_WAVE_MANIFEST_REL
    if manifest_file is not None and not manifest_file.is_absolute():
        manifest_file = project / manifest_file

    manifest: dict[str, Any] = {}
    errors: list[str] = []
    warnings: list[str] = []
    checks: list[dict[str, Any]] = []

    if not manifest_file.is_file():
        _add_check(checks, "top_wave_manifest_exists", False, f"missing manifest: {_rel(project, manifest_file)}")
        errors.append(f"missing Loop1 top waveform manifest: {_rel(project, manifest_file)}")
    else:
        try:
            manifest = load_yaml(manifest_file)
        except Exception as exc:
            _add_check(checks, "top_wave_manifest_parse", False, f"{_rel(project, manifest_file)} is not parseable: {exc}")
            errors.append(f"failed to parse Loop1 top waveform manifest: {exc}")
            manifest = {}
        else:
            _add_check(checks, "top_wave_manifest_exists", True, _rel(project, manifest_file))
            _add_check(checks, "top_wave_manifest_parse", True, "manifest parsed")

    backend = load_loop1_waveform(project, vcd_path=vcd_path, log_path=log_path)
    query = WaveformQuery(backend)

    directed_ok, directed_detail = _directed_tb_log_pass(project, backend.log_path)
    _add_check(checks, "directed_tb_log_pass", directed_ok, directed_detail)
    sim_ok, sim_detail = _simulator_errors_zero(backend.log_path)
    _add_check(checks, "simulator_errors_zero", sim_ok, sim_detail)

    top_wave_exists = backend.vcd_path is not None and backend.vcd_path.is_file() and backend.wlf_path is not None and backend.wlf_path.is_file()
    _add_check(
        checks,
        "top_waveform_exists",
        top_wave_exists,
        f"vcd={_rel(project, backend.vcd_path) if backend.vcd_path else 'missing'}; "
        f"wlf={_rel(project, backend.wlf_path) if backend.wlf_path else 'missing'}",
    )

    backend_loaded = bool(backend.signals) and not _backend_parse_errors(backend.errors)
    _add_check(
        checks,
        "waveform_backend_loaded",
        backend_loaded,
        f"backend={backend.backend}; signals={len(backend.signals)}; windows={len(backend.windows)}",
    )
    for error in backend.errors:
        errors.append(error)
    warnings.extend(backend.warnings)

    dut_scope = str(manifest.get("dut_scope") or "").strip()
    ports = _manifest_ports(manifest)
    required_names = _required_port_names(ports, manifest)
    clock_name = _clock_name(manifest, ports)
    reset_name = _reset_name(manifest, ports)
    input_names = _port_names_by_direction(ports, "input")
    output_names = _output_port_names(ports)

    manifest_matched, missing_required, matched_detail = _manifest_matched(query, required_names, dut_scope)
    _add_check(checks, "manifest_matched", manifest_matched, matched_detail)
    if missing_required:
        errors.append("missing required manifest waveform ports: " + ", ".join(missing_required[:12]))

    internal_paths = _dut_internal_paths(backend.signals.values(), dut_scope)
    top_only = not internal_paths
    _add_check(
        checks,
        "dump_scope_is_top_only",
        top_only,
        "DUT dump contains only top-level port signals"
        if top_only
        else "DUT internal signals present: " + ", ".join(internal_paths[:12]),
    )

    duration_ok, duration_detail = _dump_duration_within_limit(project, manifest, backend.windows, backend.vcd_path)
    _add_check(checks, "dump_duration_within_limit", duration_ok, duration_detail)

    query_ok = True
    query_detail = "query interface listed scopes and resolved required ports"
    try:
        query.list_scopes()
        query.list_signals(_normalize_scope(dut_scope) if dut_scope else None)
        for name in required_names:
            query.resolve_signal(name, dut_scope or None)
    except Exception as exc:
        query_ok = False
        query_detail = f"query interface failed: {exc}"
        errors.append(query_detail)
    _add_check(checks, "query_interface_pass", query_ok, query_detail)

    window_checks = _run_window_checks(
        query,
        manifest,
        dut_scope=dut_scope,
        required_names=required_names,
        clock_name=clock_name,
        reset_name=reset_name,
        input_names=input_names,
        output_names=output_names,
    )
    checks.extend(window_checks)
    waveform_analysis_ok = all(item["status"] == "PASS" for item in window_checks)
    _add_check(
        checks,
        "waveform_analysis_pass",
        waveform_analysis_ok,
        f"{sum(1 for item in window_checks if item['status'] == 'PASS')}/{len(window_checks)} waveform query checks passed",
    )

    required_gate_names = {
        "directed_tb_log_pass",
        "simulator_errors_zero",
        "top_waveform_exists",
        "dump_scope_is_top_only",
        "dump_duration_within_limit",
        "waveform_backend_loaded",
        "manifest_matched",
        "query_interface_pass",
        "waveform_analysis_pass",
    }
    required_failures = [
        check["name"]
        for check in checks
        if check["name"] in required_gate_names and check["status"] != "PASS"
    ]
    for check in checks:
        if check["status"] == "WARN":
            warnings.append(check["detail"])
    gate_ok = not required_failures and not errors

    report_path = project / WAVEFORM_QUERY_REPORT_REL
    json_path = project / WAVEFORM_GATE_JSON_REL
    transcript_path = project / QUERY_TRANSCRIPT_JSON_REL
    for path in (report_path, json_path, transcript_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    transcript_payload = {
        "schema_version": 1,
        "project": project.name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "backend": backend.backend,
        "queries": query.transcript,
    }
    transcript_path.write_text(json.dumps(transcript_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    payload = {
        "schema_version": 1,
        "project": project.name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "result": "PASS" if gate_ok else "FAIL",
        "gate_policy": "required",
        "manifest": _rel(project, manifest_file),
        "log": _rel(project, backend.log_path),
        "wave_dir": LOOP1_WAVE_DIR_REL,
        "vcd": _rel(project, backend.vcd_path) if backend.vcd_path else None,
        "wlf": _rel(project, backend.wlf_path) if backend.wlf_path else None,
        "backend": backend.backend,
        "dut_scope": dut_scope,
        "required_ports": required_names,
        "signal_count": len(backend.signals),
        "window_count": len(backend.windows),
        "transcript": QUERY_TRANSCRIPT_JSON_REL,
        "checks": checks,
        "required_failures": required_failures,
        "errors": errors,
        "warnings": warnings,
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(_format_report(payload), encoding="utf-8")
    return WaveformGateResult(
        report_path=report_path,
        json_path=json_path,
        transcript_path=transcript_path,
        ok=gate_ok,
        errors=errors + required_failures,
        warnings=warnings,
        check_count=len(checks),
    )


def check_loop1_waveform_gate_report(project_path: Path, report_rel: str = WAVEFORM_GATE_JSON_REL) -> list[str]:
    """Return gate errors for the persisted Loop1 waveform semantic gate."""

    project = require_project_instance(project_path)
    path = project / report_rel
    if not path.is_file():
        return [f"missing Loop1 waveform semantic gate report: {report_rel}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"Loop1 waveform semantic gate report is not parseable: {exc}"]

    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append(f"{report_rel} schema_version must be 1")
    if data.get("result") != "PASS":
        errors.append(f"{report_rel} result must be PASS")
    if data.get("gate_policy") != "required":
        errors.append(f"{report_rel} gate_policy must be required")
    if data.get("backend") != "pywellen":
        errors.append(f"{report_rel} backend must be pywellen")
    for name in (
        "directed_tb_log_pass",
        "simulator_errors_zero",
        "top_waveform_exists",
        "dump_scope_is_top_only",
        "dump_duration_within_limit",
        "waveform_backend_loaded",
        "manifest_matched",
        "query_interface_pass",
        "waveform_analysis_pass",
    ):
        check = _find_persisted_check(data, name)
        if not check:
            errors.append(f"{report_rel} missing required check {name}")
        elif check.get("status") != "PASS":
            errors.append(f"{report_rel} {name} must be PASS")
    for rel_key in ("manifest", "vcd", "wlf", "transcript"):
        rel = str(data.get(rel_key) or "").replace("\\", "/")
        if not rel:
            errors.append(f"{report_rel} must record {rel_key}")
            continue
        if rel_key in {"vcd", "wlf"} and not rel.startswith(LOOP1_WAVE_DIR_REL + "/"):
            errors.append(f"{report_rel} {rel_key} must live under {LOOP1_WAVE_DIR_REL}: {rel}")
            continue
        if not (project / rel).is_file():
            errors.append(f"{report_rel} {rel_key} file is missing: {rel}")
    if data.get("transcript") != QUERY_TRANSCRIPT_JSON_REL:
        errors.append(f"{report_rel} transcript must be {QUERY_TRANSCRIPT_JSON_REL}")
    if data.get("errors"):
        errors.extend(str(item) for item in data.get("errors")[:8])
    return errors


def _run_window_checks(
    query: WaveformQuery,
    manifest: dict[str, Any],
    *,
    dut_scope: str,
    required_names: list[str],
    clock_name: str | None,
    reset_name: str | None,
    input_names: list[str],
    output_names: list[str],
) -> list[dict[str, Any]]:
    window_specs = _manifest_windows(manifest)
    if not window_specs:
        if not query.backend.windows:
            return [_check_item("wave_window:any", False, "no HDLFLOW waveform windows were available for semantic query analysis")]
        window_specs = [{"name": window.window_id, "checks": ["no_xz", "clock_edges_present", "non_clock_activity"]} for window in query.backend.windows]

    results: list[dict[str, Any]] = []
    for spec in window_specs:
        window = _resolve_window(query, spec)
        checks = _as_list(spec.get("checks")) or ["no_xz", "clock_edges_present", "non_clock_activity"]
        if window is None:
            results.append(
                _check_item(
                    f"wave_window:{spec.get('name') or spec.get('id') or 'unnamed'}",
                    False,
                    "manifest window has no matching HDLFLOW_WAVE marker and no explicit start/end",
                )
            )
            continue
        for check_name in checks:
            results.append(
                _evaluate_window_check(
                    str(check_name),
                    query,
                    window,
                    spec,
                    dut_scope=dut_scope,
                    required_names=required_names,
                    clock_name=clock_name,
                    reset_name=reset_name,
                    input_names=input_names,
                    output_names=output_names,
                )
            )
    return results


def _evaluate_window_check(
    check_name: str,
    query: WaveformQuery,
    window: WaveWindow,
    spec: dict[str, Any],
    *,
    dut_scope: str,
    required_names: list[str],
    clock_name: str | None,
    reset_name: str | None,
    input_names: list[str],
    output_names: list[str],
) -> dict[str, Any]:
    scope = dut_scope or None
    signal_names = _as_list(spec.get("signals")) or required_names
    check_id = f"wave_window:{window.window_id}:{check_name}"

    if check_name in {"required_ports_present", "ports_present"}:
        missing = [name for name in signal_names if query.resolve_signal(str(name), scope) is None]
        return _check_item(check_id, not missing, "all required signals resolved" if not missing else "missing: " + ", ".join(missing[:12]))

    if check_name in {"no_xz", "no_xz_after_reset"}:
        offenders = query.check_xz([str(name) for name in signal_names], start=window.start, end=window.end, scope=scope)
        return _check_item(check_id, not offenders, "no X/Z values observed" if not offenders else "X/Z on " + ", ".join(offenders[:12]))

    if check_name == "clock_edges_present":
        if not clock_name:
            return _check_item(check_id, False, "manifest has no clock name")
        transitions = query.get_transitions(clock_name, start=window.start, end=window.end, scope=scope)
        return _check_item(check_id, bool(transitions), f"{clock_name} transitions={len(transitions)}")

    if check_name == "non_clock_activity":
        excluded = {clock_name, reset_name, None}
        names = [str(name) for name in signal_names if str(name) not in excluded]
        count = query.transition_count(names, start=window.start, end=window.end, scope=scope)
        return _check_item(check_id, count > 0, f"non-clock transitions={count}")

    if check_name == "input_event_exists":
        names = [name for name in input_names if name not in {clock_name, reset_name}]
        count = query.transition_count(names, start=window.start, end=window.end, scope=scope)
        return _check_item(check_id, count > 0, f"input transitions={count}")

    if check_name == "output_response_exists":
        count = query.transition_count(output_names, start=window.start, end=window.end, scope=scope)
        return _check_item(check_id, count > 0, f"output transitions={count}")

    if check_name == "response_latency_in_range":
        trigger = str(spec.get("trigger_signal") or "")
        response = str(spec.get("response_signal") or "")
        max_latency = _safe_int(spec.get("max_latency"))
        if not trigger or not response or max_latency <= 0:
            return _check_item(check_id, False, "trigger_signal, response_signal, and max_latency are required")
        trigger_edges = query.find_edges(trigger, start=window.start, end=window.end, scope=scope)
        response_edges = query.find_edges(response, start=window.start, end=window.end, scope=scope)
        if not trigger_edges or not response_edges:
            return _check_item(check_id, False, f"trigger_edges={len(trigger_edges)} response_edges={len(response_edges)}")
        latency = response_edges[0][0] - trigger_edges[0][0]
        return _check_item(check_id, 0 <= latency <= max_latency, f"latency={latency}; max_latency={max_latency}")

    if check_name == "data_sequence_valid":
        expected = [str(item) for item in _as_list(spec.get("expected_sequence"))]
        data_names = [str(item) for item in _as_list(spec.get("data_signals"))] or output_names
        if not expected:
            count = query.transition_count(data_names, start=window.start, end=window.end, scope=scope)
            return _check_item(check_id, count > 0, f"data activity transitions={count}")
        observed_values: list[str] = []
        for name in data_names:
            observed_values.extend(value for _, value in query.get_transitions(name, start=window.start, end=window.end, scope=scope))
        return _check_item(
            check_id,
            _contains_subsequence(observed_values, expected),
            f"expected_sequence={expected}; observed_values={observed_values[:16]}",
        )

    return _check_item(check_id, False, f"unsupported waveform query check: {check_name}")


def _directed_tb_log_pass(project: Path, log_path: Path) -> tuple[bool, str]:
    report_path = project / LOOP1_REPORT_JSON_REL
    if report_path.is_file():
        try:
            data = json.loads(report_path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            return False, f"{LOOP1_REPORT_JSON_REL} is not parseable: {exc}"
        result = str(data.get("result") or "")
        return result == "PASS", f"{LOOP1_REPORT_JSON_REL} result={result or 'missing'}"

    if not log_path.is_file():
        return False, "Loop1 report JSON and ModelSim log are missing"
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    has_summary_pass = bool(re.search(r"HDLFLOW\|SUMMARY\|.*\bresult=PASS\b", text))
    has_check_fail = bool(re.search(r"HDLFLOW\|CHECK\|.*\bresult=FAIL\b", text))
    if has_summary_pass and not has_check_fail:
        return True, "ModelSim log has PASS summary and no failed structured checks"
    return False, "ModelSim log does not show a clean HDLFLOW PASS summary"


def _simulator_errors_zero(log_path: Path) -> tuple[bool, str]:
    if not log_path.is_file():
        return False, "ModelSim log is missing"
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    patterns = [
        r"\*\*\s+Error",
        r"\bFatal:",
        r"\bUVM_(ERROR|FATAL)\b",
        r"HDLFLOW\|CHECK\|.*\bresult=FAIL\b",
    ]
    hits = []
    for pattern in patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        if matches:
            hits.append(pattern)
    return not hits, "no simulator error/fatal markers" if not hits else "error markers found: " + ", ".join(hits)


def _backend_parse_errors(errors: list[str]) -> list[str]:
    return [
        error
        for error in errors
        if "failed to parse waveform" in error or "pywellen" in error or "contains no signal declarations" in error
    ]


def _manifest_ports(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    ports = manifest.get("ports")
    if not isinstance(ports, list):
        return []
    return [item for item in ports if isinstance(item, dict)]


def _manifest_windows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    windows = manifest.get("windows")
    if not isinstance(windows, list):
        return []
    return [item for item in windows if isinstance(item, dict)]


def _required_port_names(ports: list[dict[str, Any]], manifest: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for port in ports:
        name = str(port.get("name") or "").strip()
        if not name:
            continue
        if _as_bool(port.get("required"), default=True):
            names.append(name)
    for key in ("clock", "reset"):
        spec = manifest.get(key)
        name = _named_spec_name(spec)
        required = _named_spec_required(spec, default=bool(name))
        if name and required and name not in names:
            names.append(name)
    return names


def _clock_name(manifest: dict[str, Any], ports: list[dict[str, Any]]) -> str | None:
    name = _named_spec_name(manifest.get("clock"))
    if name:
        return name
    for port in ports:
        role = str(port.get("role") or "").lower()
        port_name = str(port.get("name") or "")
        if role == "clock" or _is_clock(port_name):
            return port_name
    return None


def _reset_name(manifest: dict[str, Any], ports: list[dict[str, Any]]) -> str | None:
    name = _named_spec_name(manifest.get("reset"))
    if name:
        return name
    for port in ports:
        role = str(port.get("role") or "").lower()
        port_name = str(port.get("name") or "")
        if role == "reset" or _is_reset(port_name):
            return port_name
    return None


def _named_spec_name(spec: Any) -> str | None:
    if isinstance(spec, dict):
        value = spec.get("name")
    else:
        value = spec
    text = str(value or "").strip()
    return text or None


def _named_spec_required(spec: Any, *, default: bool) -> bool:
    if isinstance(spec, dict):
        return _as_bool(spec.get("required"), default=default)
    return default


def _port_names_by_direction(ports: list[dict[str, Any]], direction: str) -> list[str]:
    names: list[str] = []
    for port in ports:
        port_direction = str(port.get("direction") or "").lower()
        name = str(port.get("name") or "")
        if name and port_direction.startswith(direction):
            names.append(name)
    return names


def _output_port_names(ports: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for port in ports:
        direction = str(port.get("direction") or "").lower()
        name = str(port.get("name") or "")
        if name and direction.startswith("output"):
            names.append(name)
    return names


def _manifest_matched(query: WaveformQuery, required_names: list[str], dut_scope: str) -> tuple[bool, list[str], str]:
    missing = [name for name in required_names if query.resolve_signal(name, dut_scope or None) is None]
    matched = len(required_names) - len(missing)
    return not missing, missing, f"matched {matched}/{len(required_names)} required manifest signals"


def _dut_internal_paths(signals: Any, dut_scope: str) -> list[str]:
    scope = _normalize_scope(dut_scope)
    if not scope:
        return []
    internal: list[str] = []
    for signal in signals:
        path = str(signal.path)
        if not path.startswith(scope + "."):
            continue
        remainder = path[len(scope) + 1 :]
        if "." in remainder:
            internal.append(path)
    return sorted(internal)


def _dump_duration_within_limit(
    project: Path,
    manifest: dict[str, Any],
    windows: list[WaveWindow],
    vcd_path: Path | None,
) -> tuple[bool, str]:
    max_duration = _safe_int(manifest.get("max_dump_duration"))
    max_size_mb = float(manifest.get("max_file_size_mb") or 0)
    failures: list[str] = []
    if max_duration > 0:
        too_long = [f"{window.window_id}:{window.end - window.start}" for window in windows if window.end - window.start > max_duration]
        failures.extend(f"window duration exceeds max_dump_duration={max_duration}: {item}" for item in too_long[:8])
    if max_size_mb > 0 and vcd_path is not None and vcd_path.is_file():
        size_mb = vcd_path.stat().st_size / (1024 * 1024)
        if size_mb > max_size_mb:
            failures.append(f"{_rel(project, vcd_path)} size {size_mb:.2f} MB exceeds max_file_size_mb={max_size_mb}")
    if failures:
        return False, "; ".join(failures)
    details = []
    if max_duration > 0:
        details.append(f"max_dump_duration={max_duration}")
    if max_size_mb > 0:
        details.append(f"max_file_size_mb={max_size_mb}")
    return True, "; ".join(details) if details else "no dump size/duration limit configured"


def _resolve_window(query: WaveformQuery, spec: dict[str, Any]) -> WaveWindow | None:
    name = str(spec.get("name") or spec.get("id") or "").strip()
    if name:
        found = query.window_by_name(name)
        if found is not None:
            return found
    start = _safe_int_or_none(spec.get("start"))
    end = _safe_int_or_none(spec.get("end"))
    if name and start is not None and end is not None:
        return WaveWindow(window_id=name, start=start, end=end, scope=str(spec.get("scope") or "top"))
    return None


def _contains_subsequence(observed: list[str], expected: list[str]) -> bool:
    if not expected:
        return True
    index = 0
    for value in observed:
        if value == expected[index]:
            index += 1
            if index == len(expected):
                return True
    return False


def _format_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Loop1 Waveform Query Gate",
        "",
        f"- project: {payload['project']}",
        f"- generated_at: {payload['generated_at']}",
        f"- result: {payload['result']}",
        f"- manifest: {payload['manifest']}",
        f"- backend: {payload['backend']}",
        f"- vcd: {payload['vcd']}",
        f"- wlf: {payload['wlf']}",
        f"- dut_scope: {payload['dut_scope'] or 'unspecified'}",
        f"- transcript: {payload['transcript']}",
        "",
        "## Gate Checks",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for check in payload.get("checks", []):
        lines.append(f"| {check['name']} | {check['status']} | {_escape_md(check['detail'])} |")
    lines.extend(["", "## Errors", ""])
    lines.extend([f"- {item}" for item in payload.get("errors", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {item}" for item in payload.get("warnings", [])] or ["- none"])
    return "\n".join(lines) + "\n"


def _add_check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    checks.append(_check_item(name, passed, detail))


def _check_item(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def _find_persisted_check(data: dict[str, Any], name: str) -> dict[str, Any] | None:
    for check in data.get("checks") or []:
        if isinstance(check, dict) and check.get("name") == name:
            return check
    return None


def _normalize_scope(value: str | None) -> str:
    text = str(value or "").strip().replace("\\", "/").strip("/")
    text = text.replace("/", ".")
    return text.rstrip(".*")


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _as_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "yes", "1", "required"}:
        return True
    if text in {"false", "no", "0", "optional"}:
        return False
    return default


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _escape_md(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")
