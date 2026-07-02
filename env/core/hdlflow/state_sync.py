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

from .gate_invalidation import pass_evidence_invalidated
from .layout import project_gates_path, project_memory_path
from .project import require_project_instance


NODE_ORDER = [
    "input",
    "work/docparse",
    "work/loop1_rtl_tb",
    "work/loop2_uvm",
    "work/loop3_fpga_proto",
    "output",
]

NODE_TO_LOOP = {
    "input": "docparse",
    "work/docparse": "loop1",
    "work/loop1_rtl_tb": "loop2",
    "work/loop2_uvm": "loop3",
    "work/loop3_fpga_proto": "final",
    "output": "complete",
}

NODE_FILE_STEMS = {
    "input": ["input"],
    "work/docparse": ["work_docparse"],
    "work/loop1_rtl_tb": ["work_loop1_rtl_tb"],
    "work/loop2_uvm": ["work_loop2_uvm"],
    "work/loop3_fpga_proto": ["work_loop3_fpga_proto"],
    "output": ["output"],
}


@dataclass(frozen=True)
class StateSyncResult:
    updated_files: list[Path]
    passed_nodes: list[str]
    failed_nodes: list[str]
    current_loop: str
    overall_status: str


def sync_project_state(project_path: Path) -> StateSyncResult:
    """Update work/gates/*.json state files from passed gate manifests and reports."""

    project = require_project_instance(project_path)
    loop_dir = project_gates_path(project)
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
        manifest_path = _latest_manifest(project, node)
        pass_path = manifest_path
        latest_report = _latest_gate_report(project, node)
        if latest_report:
            report_path, result = latest_report
            normalized = result.lower()
            if normalized == "pass" and not pass_path:
                statuses[node] = "pending"
                continue
            if normalized == "fail" and (not pass_path or report_path.stat().st_mtime >= pass_path.stat().st_mtime):
                statuses[node] = normalized
                continue
            if normalized == "pass" and pass_path and report_path.stat().st_mtime >= pass_path.stat().st_mtime:
                statuses[node] = normalized
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
    root = project_memory_path(project) / "recovery" / "rollback_manifests"
    matches = _node_file_matches(root, node, ".json")
    for path in reversed(matches):
        if _valid_gate_manifest(project, node, path):
            return path
    return None


def _valid_gate_manifest(project: Path, node: str, path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(data, dict):
        return False
    if data.get("schema_version") != 1:
        return False
    if data.get("project") != project.name or data.get("node") != node:
        return False
    created_at = str(data.get("created_at") or "")
    if not created_at or not data.get("gate_report"):
        return False
    if pass_evidence_invalidated(project, path, created_at=created_at):
        return False
    gate_report = project / str(data.get("gate_report"))
    try:
        gate_report.resolve().relative_to(project.resolve())
    except ValueError:
        return False
    if not gate_report.is_file():
        return False
    report_text = gate_report.read_text(encoding="utf-8", errors="ignore")
    if re.search(r"(?m)^-\s*result:\s*PASS\s*$", report_text) is None:
        return False
    for key in ("sources", "evidence", "skill_constraints", "protected_gate_files"):
        if key in data and not isinstance(data[key], list):
            return False
    return True


def _latest_gate_report(project: Path, node: str) -> tuple[Path, str] | None:
    root = project / "output" / "reports" / "gates"
    matches = _node_file_matches(root, node, ".md")
    for path in reversed(matches):
        if pass_evidence_invalidated(project, path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r"^- result:\s*(PASS|FAIL)\s*$", text, flags=re.MULTILINE)
        if match:
            if match.group(1) == "FAIL" and _is_non_state_gate_invocation_failure(text):
                continue
            return path, match.group(1)
    return None


def _is_non_state_gate_invocation_failure(text: str) -> bool:
    """Return true for bad gate invocations that should not move workflow state.

    A closed or missing `--change-id` is a command binding error, not new
    evidence that the already-passed workflow node regressed.
    """

    return bool(
        re.search(
            r"\|\s*change_control_state\s*\|\s*FAIL\s*\|.*(?:expected approved|change request not found)",
            text,
            flags=re.IGNORECASE,
        )
    )


def _node_file_matches(root: Path, node: str, suffix: str) -> list[Path]:
    if not root.exists():
        return []
    matches: list[Path] = []
    for stem in NODE_FILE_STEMS.get(node, [node.replace("/", "_")]):
        matches.extend(root.glob(f"{stem}_*{suffix}"))
    return sorted(set(matches))


def _overall_status(furthest_node: str, failed_nodes: list[str]) -> str:
    if failed_nodes:
        return _failed_node_loop(failed_nodes[0]) + "_blocked"
    mapping = {
        "": "pending",
        "input": "spec_passed",
        "work/docparse": "docparse_passed",
        "work/loop1_rtl_tb": "loop1_passed",
        "work/loop2_uvm": "loop2_passed",
        "work/loop3_fpga_proto": "loop3_passed",
        "output": "final_passed",
    }
    return mapping[furthest_node]


def _failed_node_loop(node: str) -> str:
    mapping = {
        "input": "spec",
        "work/docparse": "docparse",
        "work/loop1_rtl_tb": "loop1",
        "work/loop2_uvm": "loop2",
        "work/loop3_fpga_proto": "loop3",
        "output": "final",
    }
    return mapping.get(node, "docparse")


def _gate_status(project: Path, statuses: dict[str, str]) -> dict[str, Any]:
    return {
        "project": project.name,
        "spec_exit": _status("input", statuses),
        "loop1_exit": _status("work/loop1_rtl_tb", statuses),
        "loop2_entry": _status("work/loop1_rtl_tb", statuses),
        "loop2_exit": _status("work/loop2_uvm", statuses),
        "loop3_entry": "pass" if statuses.get("work/loop2_uvm") == "pass" else "pending",
        "loop3_exit": _status("work/loop3_fpga_proto", statuses),
        "final_gate": _status("output", statuses),
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
        "loop1": ("work/loop1_rtl_tb", "output/reports/loop1/loop1_report.md"),
        "loop2": ("work/loop2_uvm", "output/reports/loop2/loop2_report.md"),
        "loop3": ("work/loop3_fpga_proto", "output/reports/loop3/loop3_exit_report.md"),
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
            vivado_report = "output/fpga/vivado/reports/pure_pl_uart_led_proto_run.md"
            timing_report = "output/fpga/vivado/reports/post_impl_timing_summary.rpt"
            board_report = "output/reports/loop3/serial/latest_serial_validation_report.md"
            board_log = "output/reports/loop3/serial/latest_serial_text.log"
            data["latest_vivado_report"] = vivado_report if (project / vivado_report).exists() else (timing_report if (project / timing_report).exists() else "")
            data["latest_board_log"] = board_report if (project / board_report).exists() else (board_log if (project / board_log).exists() else "")
        elif report.exists():
            data["latest_report"] = report_rel
            if loop == "loop1":
                data["latest_log"] = "work/loop1_rtl_tb/current/log/modelsim.log"
            if loop == "loop2":
                data["latest_log"] = "work/loop2_uvm/current/log/modelsim.log"
        data.setdefault("iteration", 0)
        if node in passed:
            data["open_blockers"] = []
        elif statuses.get(node) == "fail":
            data["open_blockers"] = ["latest gate failed; inspect output/reports/gates"]
        else:
            data["open_blockers"] = data.get("open_blockers", [])
        updated.append(_update_json(path, data))
    return updated


def _task_board(project: Path, path: Path, passed: list[str], statuses: dict[str, str], stamp: str) -> dict[str, Any]:
    data = _read_json(path, {"project": project.name, "done_criteria": [], "tasks": []})
    data["project"] = project.name
    node_by_criterion = {
        "normalized-spec-ready": "work/docparse",
        "loop1-functional-pass": "work/loop1_rtl_tb",
        "loop2-uvm-pass": "work/loop2_uvm",
        "loop3-board-pass": "work/loop3_fpga_proto",
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
    if "work/docparse" in passed:
        done_tasks.update({"ingest_source_docs", "normalize_specs"})
    if "work/loop1_rtl_tb" in passed:
        done_tasks.update({"implement_rtl", "build_functional_tb", "run_loop1"})
    if "work/loop2_uvm" in passed:
        done_tasks.update({"build_uvm_env", "run_uvm_precheck", "run_regression"})
    if "work/loop3_fpga_proto" in passed:
        done_tasks.add("run_loop3")
    if statuses.get("work/docparse") == "fail":
        blocked_tasks.update({"ingest_source_docs", "normalize_specs"})
    if statuses.get("work/loop1_rtl_tb") == "fail":
        blocked_tasks.update({"implement_rtl", "build_functional_tb", "run_loop1"})
    if statuses.get("work/loop2_uvm") == "fail":
        blocked_tasks.update({"build_uvm_env", "run_uvm_precheck", "run_regression"})
    if statuses.get("work/loop3_fpga_proto") == "fail":
        blocked_tasks.add("run_loop3")
    for task in data.get("tasks", []):
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("id"))
        if task_id in blocked_tasks:
            task["status"] = "blocked"
            task["last_update"] = stamp
            task["last_note"] = "latest gate failed; inspect output/reports/gates"
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
        "req_to_design_intent": "work/docparse/trace_matrix/req_to_design_intent.yaml",
        "req_to_test_intent": "work/docparse/trace_matrix/req_to_test_intent.yaml",
        "req_to_rtl": "work/loop1_rtl_tb/trace_matrix/req_to_rtl.yaml",
        "req_to_directed_tb": "work/loop1_rtl_tb/trace_matrix/req_to_directed_tb.yaml",
        "req_to_uvm": "work/loop2_uvm/trace_matrix/req_to_uvm.yaml",
        "req_to_assertion": "work/loop2_uvm/trace_matrix/req_to_assertion.yaml",
        "req_to_coverage": "work/loop2_uvm/trace_matrix/req_to_coverage.yaml",
        "req_to_fpga_evidence": "work/loop3_fpga_proto/trace_matrix/req_to_fpga_evidence.yaml",
        "bug_to_fix": "work/docparse/trace_matrix/bug_to_fix.yaml",
    }.items():
        data[key] = "ready" if (project / rel).exists() else "pending"
    data.setdefault("gaps", [])
    return data


def _coverage_status(project: Path, path: Path, passed: list[str], statuses: dict[str, str]) -> dict[str, Any]:
    data = _read_json(path, {"project": project.name})
    data["project"] = project.name
    loop1 = data.get("loop1", {}) if isinstance(data.get("loop1"), dict) else {}
    loop1["status"] = "passed" if "work/loop1_rtl_tb" in passed else loop1.get("status", "pending")
    data["loop1"] = loop1
    loop2_report = _read_json(project / "output" / "reports" / "loop2" / "loop2_report.json", {})
    summary = loop2_report.get("summary", {}) if isinstance(loop2_report.get("summary"), dict) else {}
    code = _metric(str(summary.get("code_coverage", "")), r"([0-9.]+)")
    functional = _metric(str(summary.get("coverage", "")), r"([0-9.]+)")
    loop2_status = "failed" if statuses.get("work/loop2_uvm") == "fail" else ("passed" if "work/loop2_uvm" in passed else "pending")
    data["loop2"] = {
        "status": loop2_status,
        "code": code,
        "functional": functional,
        "requirement": "trace_ready" if (project / "work/docparse" / "trace_matrix" / "req_to_test_intent.yaml").exists() else None,
    }
    data.setdefault("waivers", [])
    return data


def _bug_status(project: Path, path: Path, passed: list[str], statuses: dict[str, str]) -> dict[str, Any]:
    data = _read_json(path, {"project": project.name})
    data["project"] = project.name
    data["status"] = "failed" if statuses.get("work/loop2_uvm") == "fail" else ("passed" if "work/loop2_uvm" in passed else data.get("status", "pending"))
    data.setdefault("closed_bugs", [])
    data["open_critical_or_major"] = []
    return data


def _update_current_state(project: Path, current_loop: str, overall_status: str, stamp: str, passed: list[str], failed: list[str]) -> Path:
    path = project_memory_path(project) / "00_global" / "CURRENT_STATE.md"
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
        "docparse": "work/docparse",
        "spec": "input",
        "loop1": "work/loop1_rtl_tb",
        "loop2": "work/loop2_uvm",
        "loop3": "work/loop3_fpga_proto",
        "final": "output",
        "complete": "output",
    }
    return mapping.get(loop_name, "work/docparse")


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
