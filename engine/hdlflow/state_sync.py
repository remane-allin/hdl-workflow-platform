"""Synchronize project loop runtime state from gate evidence."""

from __future__ import annotations

import json
import os
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .project import require_project_instance


NODE_ORDER = [
    "00_SPEC",
    "01_DocParse",
    "02_Loop1_RTL_TB",
    "03_Loop2_UVM_Verify",
    "04_Loop3_FPGA_Prototype",
    "05_Output",
]

NODE_TO_LOOP = {
    "00_SPEC": "docparse",
    "01_DocParse": "loop1",
    "02_Loop1_RTL_TB": "loop2",
    "03_Loop2_UVM_Verify": "loop3",
    "04_Loop3_FPGA_Prototype": "final",
    "05_Output": "complete",
}


@dataclass(frozen=True)
class StateSyncResult:
    updated_files: list[Path]
    passed_nodes: list[str]
    failed_nodes: list[str]
    current_loop: str
    overall_status: str


def sync_project_state(project_path: Path) -> StateSyncResult:
    """Update loop/*.json state files from passed gate manifests and reports."""

    project = require_project_instance(project_path)
    loop_dir = project / "loop"
    loop_dir.mkdir(parents=True, exist_ok=True)
    with _state_sync_lock(loop_dir):
        stamp = datetime.now().isoformat(timespec="seconds")
        statuses = _node_statuses(project)
        passed = _contiguous_passed_nodes(statuses)
        failed = [node for node in NODE_ORDER if statuses.get(node) == "fail"]
        furthest = passed[-1] if passed else ""
        current_loop = NODE_TO_LOOP.get(furthest, "docparse")
        if failed:
            current_loop = _failed_node_loop(failed[0])
        overall_status = _overall_status(furthest, failed)
        updated: list[Path] = []

        updated.append(_update_json(loop_dir / "gate_status.json", _gate_status(project, statuses)))
        updated.append(_update_json(loop_dir / "loop_state.json", _loop_state(project, current_loop, overall_status, stamp, passed)))
        updated.extend(_update_loop_states(project, loop_dir, passed, statuses, stamp))
        updated.append(_update_json(loop_dir / "task_board.json", _task_board(project, loop_dir / "task_board.json", passed, statuses, stamp)))
        updated.append(_update_json(loop_dir / "trace_status.json", _trace_status(project, loop_dir / "trace_status.json")))
        updated.append(_update_json(loop_dir / "coverage_status.json", _coverage_status(project, loop_dir / "coverage_status.json", passed, statuses)))
        updated.append(_update_json(loop_dir / "bug_closure_status.json", _bug_status(project, loop_dir / "bug_closure_status.json", passed, statuses)))
        updated.append(_update_current_state(project, current_loop, overall_status, stamp, passed, failed))

        return StateSyncResult(
            updated_files=updated,
            passed_nodes=passed,
            failed_nodes=failed,
            current_loop=current_loop,
            overall_status=overall_status,
        )


def _node_statuses(project: Path) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for node in NODE_ORDER:
        pass_path = _latest_manifest(project, node) or _latest_pass_report(project, node)
        latest_report = _latest_gate_report(project, node)
        if latest_report:
            report_path, result = latest_report
            if not pass_path or report_path.stat().st_mtime >= pass_path.stat().st_mtime:
                statuses[node] = result.lower()
                continue
        statuses[node] = "pass" if pass_path else "pending"
    return statuses


def _contiguous_passed_nodes(statuses: dict[str, str]) -> list[str]:
    passed: list[str] = []
    for node in NODE_ORDER:
        if statuses.get(node) != "pass":
            break
        passed.append(node)
    return passed


def _latest_manifest(project: Path, node: str) -> Path | None:
    root = project / "memory" / "recovery" / "rollback_manifests"
    matches = sorted(root.glob(f"{node}_*.json")) if root.exists() else []
    return matches[-1] if matches else None


def _latest_pass_report(project: Path, node: str) -> Path | None:
    root = project / "05_Output" / "reports" / "gates"
    matches = sorted(root.glob(f"{node}_*.md")) if root.exists() else []
    for path in reversed(matches):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"^- result:\s*PASS\s*$", text, flags=re.MULTILINE):
            return path
    return None


def _latest_gate_report(project: Path, node: str) -> tuple[Path, str] | None:
    root = project / "05_Output" / "reports" / "gates"
    matches = sorted(root.glob(f"{node}_*.md")) if root.exists() else []
    for path in reversed(matches):
        text = path.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r"^- result:\s*(PASS|FAIL)\s*$", text, flags=re.MULTILINE)
        if match:
            return path, match.group(1)
    return None


def _overall_status(furthest_node: str, failed_nodes: list[str]) -> str:
    if failed_nodes:
        return _failed_node_loop(failed_nodes[0]) + "_blocked"
    mapping = {
        "": "pending",
        "00_SPEC": "spec_passed",
        "01_DocParse": "docparse_passed",
        "02_Loop1_RTL_TB": "loop1_passed",
        "03_Loop2_UVM_Verify": "loop2_passed",
        "04_Loop3_FPGA_Prototype": "loop3_passed",
        "05_Output": "final_passed",
    }
    return mapping[furthest_node]


def _failed_node_loop(node: str) -> str:
    mapping = {
        "00_SPEC": "spec",
        "01_DocParse": "docparse",
        "02_Loop1_RTL_TB": "loop1",
        "03_Loop2_UVM_Verify": "loop2",
        "04_Loop3_FPGA_Prototype": "loop3",
        "05_Output": "final",
    }
    return mapping.get(node, "docparse")


def _gate_status(project: Path, statuses: dict[str, str]) -> dict[str, Any]:
    return {
        "project": project.name,
        "spec_exit": _status("00_SPEC", statuses),
        "loop1_exit": _status("02_Loop1_RTL_TB", statuses),
        "loop2_entry": _status("02_Loop1_RTL_TB", statuses),
        "loop2_exit": _status("03_Loop2_UVM_Verify", statuses),
        "loop3_entry": "pass" if statuses.get("03_Loop2_UVM_Verify") == "pass" else "pending",
        "loop3_exit": _status("04_Loop3_FPGA_Prototype", statuses),
        "final_gate": _status("05_Output", statuses),
    }


def _loop_state(project: Path, current_loop: str, overall_status: str, stamp: str, passed: list[str]) -> dict[str, Any]:
    notes = [f"synchronized from passed gate evidence: {', '.join(passed) if passed else 'none'}"]
    return {
        "project": project.name,
        "current_loop": current_loop,
        "overall_status": overall_status,
        "last_update": stamp,
        "notes": notes,
    }


def _update_loop_states(project: Path, loop_dir: Path, passed: list[str], statuses: dict[str, str], stamp: str) -> list[Path]:
    specs = {
        "loop1": ("02_Loop1_RTL_TB", "05_Output/reports/loop1/loop1_exit_report.md"),
        "loop2": ("03_Loop2_UVM_Verify", "05_Output/reports/loop2/loop2_exit_report.md"),
        "loop3": ("04_Loop3_FPGA_Prototype", "05_Output/reports/loop3/loop3_exit_report.md"),
    }
    updated: list[Path] = []
    for loop, (node, report_rel) in specs.items():
        path = loop_dir / f"{loop}_state.json"
        data = _read_json(path, {"project": project.name, "loop": loop})
        data["project"] = project.name
        data["loop"] = loop
        if statuses.get(node) == "fail":
            data["status"] = "failed"
        else:
            data["status"] = "passed" if node in passed else "pending"
        data["last_update"] = stamp
        report = project / report_rel
        if loop == "loop3":
            vivado_report = "05_Output/fpga/vivado/reports/pure_pl_uart_led_proto_run.md"
            timing_report = "05_Output/fpga/vivado/reports/post_impl_timing_summary.rpt"
            board_report = "05_Output/reports/loop3/serial/latest_serial_validation_report.md"
            board_log = "05_Output/reports/loop3/serial/latest_serial_text.log"
            data["latest_vivado_report"] = vivado_report if (project / vivado_report).exists() else (timing_report if (project / timing_report).exists() else "")
            data["latest_board_log"] = board_report if (project / board_report).exists() else (board_log if (project / board_log).exists() else "")
        elif report.exists():
            key = "latest_regression_log" if loop == "loop2" else "latest_report"
            data[key] = report_rel
            if loop == "loop1":
                data["latest_log"] = data.get("latest_log", "")
        data.setdefault("iteration", 0)
        if node in passed:
            data["open_blockers"] = []
        elif statuses.get(node) == "fail":
            data["open_blockers"] = ["latest gate failed; inspect 05_Output/reports/gates"]
        else:
            data["open_blockers"] = data.get("open_blockers", [])
        updated.append(_update_json(path, data))
    return updated


def _task_board(project: Path, path: Path, passed: list[str], statuses: dict[str, str], stamp: str) -> dict[str, Any]:
    data = _read_json(path, {"project": project.name, "done_criteria": [], "tasks": []})
    data["project"] = project.name
    node_by_criterion = {
        "normalized-spec-ready": "01_DocParse",
        "loop1-functional-pass": "02_Loop1_RTL_TB",
        "loop2-uvm-pass": "03_Loop2_UVM_Verify",
        "loop3-board-pass": "04_Loop3_FPGA_Prototype",
    }
    for item in data.get("done_criteria", []):
        if not isinstance(item, dict):
            continue
        node = node_by_criterion.get(str(item.get("id")))
        if not node:
            continue
        if statuses.get(node) == "fail":
            item["status"] = "blocked"
        elif node in passed:
            item["status"] = "done"
        else:
            item["status"] = "pending"
    done_tasks = set()
    blocked_tasks = set()
    if "01_DocParse" in passed:
        done_tasks.update({"ingest_source_docs", "normalize_specs"})
    if "02_Loop1_RTL_TB" in passed:
        done_tasks.update({"implement_rtl", "build_functional_tb", "run_loop1"})
    if "03_Loop2_UVM_Verify" in passed:
        done_tasks.update({"build_uvm_env", "run_uvm_precheck", "run_regression"})
    if "04_Loop3_FPGA_Prototype" in passed:
        done_tasks.add("run_loop3")
    if statuses.get("01_DocParse") == "fail":
        blocked_tasks.update({"ingest_source_docs", "normalize_specs"})
    if statuses.get("02_Loop1_RTL_TB") == "fail":
        blocked_tasks.update({"implement_rtl", "build_functional_tb", "run_loop1"})
    if statuses.get("03_Loop2_UVM_Verify") == "fail":
        blocked_tasks.update({"build_uvm_env", "run_uvm_precheck", "run_regression"})
    if statuses.get("04_Loop3_FPGA_Prototype") == "fail":
        blocked_tasks.add("run_loop3")
    for task in data.get("tasks", []):
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("id"))
        if task_id in blocked_tasks:
            task["status"] = "blocked"
            task["last_update"] = stamp
            task["last_note"] = "latest gate failed; inspect 05_Output/reports/gates"
        elif task_id in done_tasks:
            task["status"] = "done"
            task["last_update"] = stamp
            task["last_note"] = "synchronized from passed gate evidence"
        elif task_id in {
            "ingest_source_docs",
            "normalize_specs",
            "implement_rtl",
            "build_functional_tb",
            "run_loop1",
            "build_uvm_env",
            "run_uvm_precheck",
            "run_regression",
            "run_loop3",
        }:
            task["status"] = "pending"
    return data


def _trace_status(project: Path, path: Path) -> dict[str, Any]:
    data = _read_json(path, {"project": project.name, "gaps": []})
    data["project"] = project.name
    for key, rel in {
        "req_to_rtl": "01_DocParse/trace_matrix/req_to_rtl.yaml",
        "req_to_test": "01_DocParse/trace_matrix/req_to_test.yaml",
        "bug_to_fix": "01_DocParse/trace_matrix/bug_to_fix.yaml",
    }.items():
        data[key] = "ready" if (project / rel).exists() else "pending"
    data.setdefault("gaps", [])
    return data


def _coverage_status(project: Path, path: Path, passed: list[str], statuses: dict[str, str]) -> dict[str, Any]:
    data = _read_json(path, {"project": project.name})
    data["project"] = project.name
    loop1 = data.get("loop1", {}) if isinstance(data.get("loop1"), dict) else {}
    loop1["status"] = "passed" if "02_Loop1_RTL_TB" in passed else loop1.get("status", "pending")
    data["loop1"] = loop1
    coverage_text = _read_text(project / "05_Output" / "reports" / "loop2" / "coverage_index.md")
    code = _metric(coverage_text, r"Aggregate \|\s*([0-9.]+)%")
    functional = _metric(coverage_text, r"legal_scenario_cg=([0-9.]+)")
    loop2_status = "failed" if statuses.get("03_Loop2_UVM_Verify") == "fail" else ("passed" if "03_Loop2_UVM_Verify" in passed else "pending")
    data["loop2"] = {
        "status": loop2_status,
        "code": code,
        "functional": functional,
        "requirement": "trace_ready" if (project / "01_DocParse" / "trace_matrix" / "req_to_test.yaml").exists() else None,
    }
    data.setdefault("waivers", [])
    return data


def _bug_status(project: Path, path: Path, passed: list[str], statuses: dict[str, str]) -> dict[str, Any]:
    data = _read_json(path, {"project": project.name})
    data["project"] = project.name
    data["status"] = "failed" if statuses.get("03_Loop2_UVM_Verify") == "fail" else ("passed" if "03_Loop2_UVM_Verify" in passed else data.get("status", "pending"))
    data.setdefault("closed_bugs", [])
    data["open_critical_or_major"] = []
    return data


def _update_current_state(project: Path, current_loop: str, overall_status: str, stamp: str, passed: list[str], failed: list[str]) -> Path:
    path = project / "memory" / "00_global" / "CURRENT_STATE.md"
    active_node = _loop_to_node(current_loop)
    latest_passed = passed[-1] if passed else "none"
    failed_text = ", ".join(failed) if failed else "none"
    next_action = "Resolve blocked gate evidence before advancing." if failed else "Run the next configured gate."
    lines = [
        "# Current State",
        "",
        f"- updated_at: {stamp}",
        f"- active_node: {active_node}",
        f"- current_loop: {current_loop}",
        f"- overall_status: {overall_status}",
        f"- latest_passed_node: {latest_passed}",
        f"- latest_failed_node: {failed_text}",
        f"- latest_summary: {overall_status}; passed={', '.join(passed) if passed else 'none'}; failed={failed_text}",
        f"- next_action: {next_action}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _loop_to_node(loop_name: str) -> str:
    mapping = {
        "docparse": "01_DocParse",
        "spec": "00_SPEC",
        "loop1": "02_Loop1_RTL_TB",
        "loop2": "03_Loop2_UVM_Verify",
        "loop3": "04_Loop3_FPGA_Prototype",
        "final": "05_Output",
        "complete": "05_Output",
    }
    return mapping.get(loop_name, "01_DocParse")


def _status(node: str, statuses: dict[str, str]) -> str:
    value = statuses.get(node)
    if value in {"pass", "fail"}:
        return value
    return "pending"


def _metric(text: str, pattern: str) -> float | None:
    match = re.search(pattern, text)
    return float(match.group(1)) if match else None


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(default)
    return data if isinstance(data, dict) else dict(default)


def _update_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{datetime.now().strftime('%Y%m%d%H%M%S%f')}.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


@contextmanager
def _state_sync_lock(loop_dir: Path):
    lock_path = loop_dir / ".state_sync.lock"
    fd: int | None = None
    deadline = time.time() + 30.0
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("ascii", errors="ignore"))
            break
        except FileExistsError:
            if time.time() > deadline:
                raise TimeoutError(f"timed out waiting for state sync lock: {lock_path}")
            time.sleep(0.1)
    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass
