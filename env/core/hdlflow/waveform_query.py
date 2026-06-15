"""Queryable facade over Loop1 waveform backend data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .waveform import UNKNOWN_BITS, VcdSignal, WaveWindow
from .waveform_backend import WaveformBackendResult


@dataclass
class WaveformQuery:
    """Small query API used by the Loop1 waveform semantic gate."""

    backend: WaveformBackendResult
    transcript: list[dict[str, Any]] = field(default_factory=list)

    def list_scopes(self) -> list[str]:
        scopes = sorted({_scope_of(signal.path) for signal in self.backend.signals.values()})
        self._record("list_scopes", {}, {"count": len(scopes)})
        return scopes

    def list_signals(self, scope: str | None = None) -> list[str]:
        scope_norm = _normalize_scope(scope) if scope else None
        paths = []
        for signal in self.backend.signals.values():
            if scope_norm is None or _scope_of(signal.path) == scope_norm:
                paths.append(signal.path)
        paths = sorted(paths)
        self._record("list_signals", {"scope": scope}, {"count": len(paths)})
        return paths

    def resolve_signal(self, name: str, scope: str | None = None) -> VcdSignal | None:
        signal = self._resolve(name, scope)
        self._record(
            "resolve_signal",
            {"name": name, "scope": scope},
            {"path": signal.path if signal else None},
        )
        return signal

    def window_by_name(self, name: str) -> WaveWindow | None:
        for window in self.backend.windows:
            if window.window_id == name:
                self._record("window_by_name", {"name": name}, {"found": True})
                return window
        self._record("window_by_name", {"name": name}, {"found": False})
        return None

    def get_value(self, signal_name: str, time: int, scope: str | None = None) -> str | None:
        signal = self._resolve(signal_name, scope)
        value = self._value_for_signal(signal, time) if signal else None
        self._record(
            "get_value",
            {"signal": signal_name, "time": time, "scope": scope},
            {"value": value, "path": signal.path if signal else None},
        )
        return value

    def get_transitions(
        self,
        signal_name: str,
        *,
        start: int | None = None,
        end: int | None = None,
        scope: str | None = None,
    ) -> list[tuple[int, str]]:
        signal = self._resolve(signal_name, scope)
        transitions = self._events_in_range(signal, start, end) if signal else []
        self._record(
            "get_transitions",
            {"signal": signal_name, "start": start, "end": end, "scope": scope},
            {"count": len(transitions), "path": signal.path if signal else None},
        )
        return transitions

    def find_edges(
        self,
        signal_name: str,
        *,
        edge: str = "any",
        start: int | None = None,
        end: int | None = None,
        scope: str | None = None,
    ) -> list[tuple[int, str, str]]:
        signal = self._resolve(signal_name, scope)
        if not signal:
            self._record(
                "find_edges",
                {"signal": signal_name, "edge": edge, "start": start, "end": end, "scope": scope},
                {"count": 0, "path": None},
            )
            return []
        all_events = self.backend.events.get(signal.id_code, [])
        previous = _last_value_before(all_events, start) if start is not None else None
        edges: list[tuple[int, str, str]] = []
        for time, value in all_events:
            if start is not None and time < start:
                previous = value
                continue
            if end is not None and time > end:
                break
            if previous is not None and _edge_matches(previous, value, edge):
                edges.append((time, previous, value))
            previous = value
        self._record(
            "find_edges",
            {"signal": signal_name, "edge": edge, "start": start, "end": end, "scope": scope},
            {"count": len(edges), "path": signal.path},
        )
        return edges

    def transition_count(
        self,
        signal_names: list[str],
        *,
        start: int,
        end: int,
        scope: str | None = None,
    ) -> int:
        count = 0
        for name in signal_names:
            count += len(self.get_transitions(name, start=start, end=end, scope=scope))
        self._record(
            "transition_count",
            {"signals": signal_names, "start": start, "end": end, "scope": scope},
            {"count": count},
        )
        return count

    def check_xz(
        self,
        signal_names: list[str],
        *,
        start: int,
        end: int,
        scope: str | None = None,
    ) -> list[str]:
        offenders: list[str] = []
        for name in signal_names:
            signal = self._resolve(name, scope)
            if not signal:
                continue
            values = self._values_covering(signal, start, end)
            if any(_has_unknown(value) for _, value in values):
                offenders.append(signal.path)
        self._record(
            "check_xz",
            {"signals": signal_names, "start": start, "end": end, "scope": scope},
            {"offenders": offenders},
        )
        return offenders

    def _resolve(self, name: str, scope: str | None = None) -> VcdSignal | None:
        target = _normalize_path(name)
        scope_norm = _normalize_scope(scope) if scope else None
        candidates = list(self.backend.signals.values())
        if scope_norm:
            candidates = [
                signal
                for signal in candidates
                if signal.path == scope_norm or signal.path.startswith(scope_norm + ".")
            ]
        exact = [signal for signal in candidates if signal.path == target]
        if exact:
            return exact[0]
        suffix = [signal for signal in candidates if signal.path.endswith("." + target) or signal.path == target]
        if suffix:
            return sorted(suffix, key=lambda signal: (len(signal.path.split(".")), signal.path))[0]
        base = [signal for signal in candidates if signal.path.rsplit(".", 1)[-1] == target]
        if base:
            return sorted(base, key=lambda signal: (len(signal.path.split(".")), signal.path))[0]
        return None

    def _events_in_range(self, signal: VcdSignal | None, start: int | None, end: int | None) -> list[tuple[int, str]]:
        if signal is None:
            return []
        return [
            (time, value)
            for time, value in self.backend.events.get(signal.id_code, [])
            if (start is None or time >= start) and (end is None or time <= end)
        ]

    def _value_for_signal(self, signal: VcdSignal | None, time: int) -> str | None:
        if signal is None:
            return None
        value: str | None = None
        for event_time, event_value in self.backend.events.get(signal.id_code, []):
            if event_time > time:
                break
            value = event_value
        return value

    def _values_covering(self, signal: VcdSignal, start: int, end: int) -> list[tuple[int, str]]:
        values: list[tuple[int, str]] = []
        last_before: tuple[int, str] | None = None
        for time, value in self.backend.events.get(signal.id_code, []):
            if time < start:
                last_before = (time, value)
                continue
            if time > end:
                break
            values.append((time, value))
        if last_before is not None:
            values.insert(0, last_before)
        return values

    def _record(self, query: str, args: dict[str, Any], result: dict[str, Any]) -> None:
        self.transcript.append({"query": query, "args": args, "result": result})


def _normalize_path(value: str) -> str:
    text = str(value).strip().strip('"').strip("'")
    text = text.replace("\\", "/").strip("/")
    text = text.replace("/", ".")
    if text.startswith("."):
        text = text[1:]
    return text


def _normalize_scope(value: str | None) -> str:
    if value is None:
        return ""
    return _normalize_path(value).rstrip(".*")


def _scope_of(path: str) -> str:
    if "." not in path:
        return ""
    return path.rsplit(".", 1)[0]


def _last_value_before(events: list[tuple[int, str]], start: int | None) -> str | None:
    if start is None:
        return None
    value: str | None = None
    for time, event_value in events:
        if time >= start:
            break
        value = event_value
    return value


def _edge_matches(previous: str, value: str, edge: str) -> bool:
    if previous not in {"0", "1"} or value not in {"0", "1"} or previous == value:
        return False
    normalized = edge.lower()
    if normalized in {"any", "both"}:
        return True
    if normalized in {"rise", "posedge", "rising"}:
        return previous == "0" and value == "1"
    if normalized in {"fall", "negedge", "falling"}:
        return previous == "1" and value == "0"
    return False


def _has_unknown(value: str) -> bool:
    return any(char in UNKNOWN_BITS for char in value)
