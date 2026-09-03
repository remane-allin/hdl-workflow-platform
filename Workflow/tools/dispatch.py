from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from Workflow.core.contracts import WorkflowError, ProjectContext
from Workflow.tools.filesystem import read_json


STAGE_RESOURCES = {
    "design": (),
    "rtl": ("vivado",),
    "verify": ("vivado", "xsim"),
    "synth": ("vivado",),
    "route": ("vivado",),
    "release": ("vivado",),
}


def _process_is_active(process_id: int) -> bool:
    if process_id <= 0:
        return False
    if os.name != "nt":
        raise WorkflowError("resource dispatch is supported only on Windows")

    import ctypes
    from ctypes import wintypes

    process_query_limited_information = 0x1000
    still_active = 259
    error_access_denied = 5
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    open_process = kernel32.OpenProcess
    open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    open_process.restype = wintypes.HANDLE
    get_exit_code = kernel32.GetExitCodeProcess
    get_exit_code.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    get_exit_code.restype = wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    handle = open_process(process_query_limited_information, False, process_id)
    if not handle:
        return ctypes.get_last_error() == error_access_denied
    try:
        exit_code = wintypes.DWORD()
        return bool(get_exit_code(handle, ctypes.byref(exit_code))) and exit_code.value == still_active
    finally:
        close_handle(handle)


class ResourceLease:
    def __init__(
        self,
        workflow_root: Path,
        resource: str,
        capacity: int,
        project_id: str,
        stage: str,
    ):
        if not resource or capacity < 1:
            raise WorkflowError("resource dispatch requires a name and positive capacity")
        self.workflow_root = workflow_root
        self.resource = resource
        self.capacity = capacity
        self.project_id = project_id
        self.stage = stage
        self.path: Path | None = None

    def _try_slot(self, path: Path) -> bool:
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                owner = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return False
            if not isinstance(owner, dict) or not isinstance(owner.get("process_id"), int):
                return False
            if _process_is_active(owner["process_id"]):
                return False
            path.unlink(missing_ok=True)
            try:
                descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                return False
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(
                {
                    "resource": self.resource,
                    "project_id": self.project_id,
                    "stage": self.stage,
                    "process_id": os.getpid(),
                    "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                },
                stream,
                ensure_ascii=False,
            )
            stream.write("\n")
        self.path = path
        return True

    def __enter__(self):
        root = self.workflow_root / "work" / "dispatch" / self.resource
        root.mkdir(parents=True, exist_ok=True)
        for index in range(self.capacity):
            if self._try_slot(root / f"slot-{index}.lease"):
                return self
        self._remove_empty_parents(root)
        raise WorkflowError(f"resource unavailable: {self.resource}")

    def _remove_empty_parents(self, start: Path) -> None:
        stop = self.workflow_root
        current = start
        while current != stop:
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent

    def __exit__(self, exc_type, exc, tb):
        if self.path is None:
            return
        parent = self.path.parent
        self.path.unlink(missing_ok=True)
        self._remove_empty_parents(parent)
        self.path = None


def dispatch_capacities(workflow_root: Path) -> dict[str, int]:
    profile = read_json(workflow_root / "tools" / "tool-profiles.json")
    value = profile.get("dispatch")
    if not isinstance(value, dict) or not value:
        raise WorkflowError("tool profile lacks dispatch capacities")
    capacities: dict[str, int] = {}
    for name, capacity in value.items():
        if not isinstance(name, str) or not isinstance(capacity, int) or capacity < 1:
            raise WorkflowError("dispatch capacities must be positive integers")
        capacities[name] = capacity
    return capacities


class StageDispatch:
    def __init__(self, context: ProjectContext, design: dict[str, Any], stage: str):
        if stage not in STAGE_RESOURCES:
            raise WorkflowError(f"unsupported dispatch stage: {stage}")
        resources = list(STAGE_RESOURCES[stage])
        if stage == "release" and design["implementation"]["vitis"].get("enabled"):
            resources.append("vitis")
        capacities = dispatch_capacities(context.workflow_root) if resources else {}
        missing = sorted(set(resources) - set(capacities))
        if missing:
            raise WorkflowError("tool profile lacks dispatch capacity: " + ", ".join(missing))
        self.leases = [
            ResourceLease(context.workflow_root, resource, capacities[resource], context.project_id, stage)
            for resource in sorted(resources)
        ]
        self.acquired: list[ResourceLease] = []

    def __enter__(self):
        try:
            for lease in self.leases:
                lease.__enter__()
                self.acquired.append(lease)
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, exc_type, exc, tb):
        for lease in reversed(self.acquired):
            lease.__exit__(exc_type, exc, tb)
        self.acquired.clear()
