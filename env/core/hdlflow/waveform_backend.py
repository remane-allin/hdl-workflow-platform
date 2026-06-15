"""Loop1 waveform loading backend based on pywellen/wellen."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .project import require_project_instance
from .waveform import (
    LOOP1_LOG_REL,
    LOOP1_WAVE_DIR_REL,
    VcdSignal,
    WaveWindow,
    _is_under_rel,
    _latest_vcd,
    _latest_wlf,
    _matching_wlf,
    _parse_wave_windows,
    _rel,
)


@dataclass(frozen=True)
class WaveformBackendResult:
    project: Path
    backend: str
    log_path: Path
    vcd_path: Path | None
    wlf_path: Path | None
    windows: list[WaveWindow]
    signals: dict[str, VcdSignal]
    events: dict[str, list[tuple[int, str]]]
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def load_loop1_waveform(
    project_path: Path,
    *,
    vcd_path: Path | None = None,
    log_path: Path | None = None,
) -> WaveformBackendResult:
    """Load the canonical Loop1 top-port waveform evidence."""

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

    if not log.is_file():
        errors.append(f"missing Loop1 ModelSim log: {_rel(project, log)}")
    else:
        windows, marker_errors = _parse_wave_windows(log.read_text(encoding="utf-8", errors="ignore"))
        errors.extend(marker_errors)
        if not windows:
            errors.append(
                "missing HDLFLOW_WAVE_WINDOW or HDLFLOW_WAVE_BEGIN/HDLFLOW_WAVE_END markers; "
                "Loop1 TB must mark waveform query windows"
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
            signals, events = _parse_waveform_with_pywellen(vcd_path)
        except MissingPywellenError as exc:
            errors.append(str(exc))
        except Exception as exc:
            errors.append(f"failed to parse waveform with pywellen {_rel(project, vcd_path)}: {exc}")
        if not signals:
            errors.append(f"VCD waveform contains no signal declarations: {_rel(project, vcd_path)}")

    if wlf_path is None:
        errors.append(f"missing Loop1 WLF waveform under {LOOP1_WAVE_DIR_REL}")
    elif not wlf_path.is_file():
        errors.append(f"WLF waveform file does not exist: {wlf_path}")
    elif not _is_under_rel(project, wlf_path, LOOP1_WAVE_DIR_REL):
        errors.append(
            "Loop1 WLF waveform must be delivered from the canonical output directory "
            f"{LOOP1_WAVE_DIR_REL}: {_rel(project, wlf_path)}"
        )

    return WaveformBackendResult(
        project=project,
        backend="pywellen",
        log_path=log,
        vcd_path=vcd_path,
        wlf_path=wlf_path,
        windows=windows,
        signals=signals,
        events=events,
        errors=errors,
        warnings=warnings,
    )


class MissingPywellenError(RuntimeError):
    pass


def _parse_waveform_with_pywellen(path: Path) -> tuple[dict[str, VcdSignal], dict[str, list[tuple[int, str]]]]:
    try:
        from pywellen import Waveform
    except Exception as exc:  # pragma: no cover - depends on local optional native package
        if os.environ.get("HDLFLOW_PYWELLEN_SUBPROCESS") != "1":
            return _parse_waveform_with_pywellen_subprocess(path, exc)
        raise MissingPywellenError(
            "pywellen is required for Loop1 waveform parsing; install the recommended backend "
            "with `py -3.12 -m pip install pywellen==0.25.5` on Windows"
        ) from exc

    return _parse_waveform_with_pywellen_api(Waveform, path)


def _parse_waveform_with_pywellen_api(Waveform: object, path: Path) -> tuple[dict[str, VcdSignal], dict[str, list[tuple[int, str]]]]:
    wave = Waveform(path=str(path))
    signals: dict[str, VcdSignal] = {}
    events: dict[str, list[tuple[int, str]]] = {}
    for index, var in enumerate(wave.all_vars()):
        id_code = str(index)
        size = _safe_int(getattr(var, "size", None) or getattr(var, "bitwidth", None) or getattr(var, "length", None) or 1)
        signal = VcdSignal(
            path=str(var.full_name),
            size=size,
            type_name=str(getattr(var, "var_type", None) or getattr(var, "type", "") or "Unknown"),
            id_code=id_code,
        )
        signals[id_code] = signal
        events[id_code] = [
            (int(time), _pywellen_value_to_text(value, size))
            for time, value in list(var.tv)
        ]
    return signals, events


def _parse_waveform_with_pywellen_subprocess(
    path: Path,
    import_error: Exception,
) -> tuple[dict[str, VcdSignal], dict[str, list[tuple[int, str]]]]:
    command = _pywellen_subprocess_command()
    if command is None:
        raise MissingPywellenError(
            "pywellen is required for Loop1 waveform parsing; no usable Python 3.12 py launcher was found "
            f"after import failed in {sys.executable}: {import_error}. "
            "Install Python 3.12 and run `py -3.12 -m pip install pywellen==0.25.5`."
        ) from import_error

    env = os.environ.copy()
    core_dir = str(Path(__file__).resolve().parents[1])
    env["PYTHONPATH"] = core_dir + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["HDLFLOW_PYWELLEN_SUBPROCESS"] = "1"
    run = subprocess.run(
        [*command, "-m", "hdlflow.waveform_backend", "--parse-wave-json", str(path)],
        cwd=str(Path.cwd()),
        env=env,
        text=True,
        capture_output=True,
        timeout=180,
    )
    if run.returncode != 0:
        detail = (run.stderr or run.stdout or "").strip()
        raise MissingPywellenError(
            "pywellen subprocess parsing failed; install pywellen for the active Python "
            f"or fix Python 3.12 pywellen. Detail: {detail}"
        ) from import_error
    try:
        payload = json.loads(run.stdout)
    except Exception as exc:
        raise MissingPywellenError(f"pywellen subprocess returned non-JSON output: {run.stdout[:400]}") from exc
    return _waveform_payload_to_data(payload)


def _pywellen_subprocess_command() -> list[str] | None:
    if os.name == "nt":
        probe = subprocess.run(["py", "-3.12", "-c", "import pywellen"], text=True, capture_output=True)
        if probe.returncode == 0:
            return ["py", "-3.12"]
        return None
    probe = subprocess.run(["python3", "-c", "import pywellen"], text=True, capture_output=True)
    if probe.returncode == 0:
        return ["python3"]
    return None


def _waveform_data_to_payload(signals: dict[str, VcdSignal], events: dict[str, list[tuple[int, str]]]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "signals": {
            id_code: {
                "path": signal.path,
                "size": signal.size,
                "type_name": signal.type_name,
                "id_code": signal.id_code,
            }
            for id_code, signal in signals.items()
        },
        "events": {
            id_code: [[time, value] for time, value in signal_events]
            for id_code, signal_events in events.items()
        },
    }


def _waveform_payload_to_data(payload: dict[str, object]) -> tuple[dict[str, VcdSignal], dict[str, list[tuple[int, str]]]]:
    if payload.get("schema_version") != 1:
        raise ValueError("pywellen payload schema_version must be 1")
    raw_signals = payload.get("signals")
    raw_events = payload.get("events")
    if not isinstance(raw_signals, dict) or not isinstance(raw_events, dict):
        raise ValueError("pywellen payload must contain signals and events mappings")
    signals: dict[str, VcdSignal] = {}
    events: dict[str, list[tuple[int, str]]] = {}
    for id_code, item in raw_signals.items():
        if not isinstance(item, dict):
            continue
        signals[str(id_code)] = VcdSignal(
            path=str(item.get("path") or ""),
            size=_safe_int(item.get("size")),
            type_name=str(item.get("type_name") or "Unknown"),
            id_code=str(item.get("id_code") or id_code),
        )
    for id_code, items in raw_events.items():
        if not isinstance(items, list):
            continue
        converted: list[tuple[int, str]] = []
        for item in items:
            if isinstance(item, list) and len(item) == 2:
                converted.append((int(item[0]), str(item[1])))
        events[str(id_code)] = converted
    return signals, events


def _pywellen_value_to_text(value: object, size: int) -> str:
    if isinstance(value, int):
        if size <= 1:
            return "1" if value else "0"
        return format(value, "b").zfill(size)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _main() -> int:
    parser = argparse.ArgumentParser(description="Internal pywellen waveform parser helper.")
    parser.add_argument("--parse-wave-json", help="Waveform path to parse and print as JSON.")
    args = parser.parse_args()
    if not args.parse_wave_json:
        parser.error("--parse-wave-json is required")
    signals, events = _parse_waveform_with_pywellen(Path(args.parse_wave_json))
    print(json.dumps(_waveform_data_to_payload(signals, events), sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - subprocess helper
    raise SystemExit(_main())
