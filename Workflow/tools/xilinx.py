from __future__ import annotations

import os
import re
import subprocess
import shutil
from pathlib import Path
from typing import Any

from Workflow.core.contracts import ContractError, ProjectContext, ToolFailure, WorkflowError
from Workflow.reports.tools.extract import parse_xsim_log
from .filesystem import atomic_write_text
from .process import run_process
from .profile import load_profiles, resolve_tool


def _tcl_value(value: str | Path) -> str:
    text = str(value).replace("\\", "/")
    if any(token in text.lower() for token in ("\n", "\r", "[", "]", ";")):
        raise ContractError("unsafe Tcl context value")
    return "{" + text.replace("}", "\\}") + "}"


def _junction(link: Path, target: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.exists() or os.path.lexists(link):
        if os.path.isjunction(link) and link.resolve() == target.resolve():
            return
        raise ContractError(f"runtime data binding path already exists: {link}")
    completed = subprocess.run(
        [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", "mklink", "/J", str(link), str(target)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=False,
    )
    if completed.returncode != 0:
        raise WorkflowError(f"cannot bind formal verification data: {completed.stdout.strip()}")


def _write_context(context: ProjectContext, design: dict[str, Any], stage: str) -> Path:
    implementation = design["implementation"]
    vivado = implementation["vivado"]
    tool_root = context.project_root / "work" / "tool" / stage / "vivado"
    tool_root.mkdir(parents=True, exist_ok=True)
    report_root = context.project_root / "output" / "report" / ".staging" / stage / "physical"
    report_root.mkdir(parents=True, exist_ok=True)
    xpr = context.project_root / vivado["xpr"]
    bitstream_rel = vivado["results"].get("bitstream", "")
    bitstream = context.project_root / bitstream_rel if bitstream_rel else ""
    xsa_rel = vivado["results"].get("xsa", "")
    xsa = context.project_root / xsa_rel if xsa_rel else ""
    values = {
        "wf_project_root": context.project_root,
        "wf_workflow_root": context.workflow_root,
        "wf_project_name": vivado["project_name"],
        "wf_xpr": xpr,
        "wf_part": vivado["part"],
        "wf_top": implementation["rtl"]["top"],
        "wf_tb_top": implementation["verification_sources"]["top"],
        "wf_tb_file": context.project_root / implementation["verification_sources"]["top_file"],
        "wf_report_root": report_root,
        "wf_bitstream": bitstream,
        "wf_xsa": xsa,
        "wf_max_jobs": load_profiles(context.workflow_root)["vivado"]["max_jobs"],
        "wf_opt_resynth_area": 1 if vivado.get("opt_resynth_area", False) else 0,
        "wf_synthesis_strategy": vivado["synthesis_strategy"],
        "wf_synthesis_directive": vivado["synthesis_directive"],
        "wf_implementation_strategy": vivado["implementation_strategy"],
        "wf_opt_directive": vivado["opt_directive"],
        "wf_place_directive": vivado["place_directive"],
        "wf_phys_opt_enabled": 1 if vivado.get("phys_opt_directive") else 0,
        "wf_phys_opt_directive": vivado.get("phys_opt_directive", "Default"),
        "wf_route_directive": vivado["route_directive"],
        "wf_synthesis_mode": vivado.get("synthesis_mode", "top"),
        "wf_constraints_used_in_synthesis": 1 if vivado.get("constraints_used_in_synthesis", True) else 0,
    }
    lines = [f"set {key} {_tcl_value(value)}" for key, value in values.items()]
    rtl = [context.project_root / item for item in implementation["rtl"]["sources"]]
    constraints = [context.project_root / item for item in implementation["constraints"].get("sources", [])]
    ips = [context.project_root / item for item in vivado.get("ip", [])]
    bd_names = vivado.get("bd", [])
    simulation = [context.project_root / item for item in implementation["verification_sources"].get("models", [])]
    for name, entries in (
        ("wf_rtl_files", rtl), ("wf_xdc_files", constraints),
        ("wf_ip_files", ips), ("wf_sim_models", simulation),
    ):
        lines.append(f"set {name} [list {' '.join(_tcl_value(item) for item in entries)}]")
    lines.append(f"set wf_bd_names [list {' '.join(_tcl_value(item) for item in bd_names)}]")
    path = tool_root / "context.tcl"
    atomic_write_text(path, "\n".join(lines) + "\n")
    return path


def _parse_utilization(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8", errors="replace")
    patterns = {
        "lut": r"\| Slice LUTs\*?\s*\|\s*(\d+)",
        "lutram": r"\|\s+LUT as Memory\s*\|\s*(\d+)",
        "ff": r"\| Slice Registers\s*\|\s*(\d+)",
        "bram_tile": r"\| Block RAM Tile\s*\|\s*([0-9.]+)",
        "ramb36": r"\|\s+RAMB36/FIFO\*\s*\|\s*(\d+)",
        "ramb18": r"\|\s+RAMB18\s*\|\s*(\d+)",
        "dsp": r"\| DSPs\s*\|\s*(\d+)",
    }
    values: dict[str, float] = {}
    for name, pattern in patterns.items():
        match = re.search(pattern, text)
        if not match:
            raise ValueError(f"missing {name} in {path.name}")
        values[name] = float(match.group(1))
    return values


def _budget_result(design: dict[str, Any], stage: str, metrics: dict[str, float]) -> list[str]:
    failures: list[str] = []
    for budget in design["budgets"]["items"]:
        if budget.get("evidence_stage") != stage:
            continue
        metric = budget["metric"]
        if metric not in metrics:
            failures.append(f"missing metric {metric}")
            continue
        actual = metrics[metric]
        if "maximum" in budget and actual > float(budget["maximum"]):
            failures.append(f"{metric}={actual} exceeds {budget['maximum']}")
        if "minimum" in budget and actual < float(budget["minimum"]):
            failures.append(f"{metric}={actual} is below {budget['minimum']}")
        if "exclusive_minimum" in budget and actual <= float(budget["exclusive_minimum"]):
            failures.append(f"{metric}={actual} does not exceed {budget['exclusive_minimum']}")
        if "equals" in budget and actual != float(budget["equals"]):
            failures.append(f"{metric}={actual} differs from {budget['equals']}")
    return failures


def _native_run_request(log: Path) -> str | None:
    requests = [
        line.split("=", 1)[1].strip()
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.startswith("WF_NATIVE_RUN=")
    ]
    if len(requests) != 1:
        raise WorkflowError("Vivado prepare did not emit one native run request")
    if requests[0] == "":
        return None
    if requests[0] not in {"synth_1", "impl_1"}:
        raise WorkflowError(f"Vivado requested an unsupported native run: {requests[0]}")
    return requests[0]


def run_vivado(context: ProjectContext, design: dict[str, Any], stage: str) -> dict[str, Any]:
    vivado = design["implementation"]["vivado"]
    project_script = context.project_root / vivado["project_script"]
    if not project_script.is_file():
        raise ContractError(f"project Tcl is missing: {vivado['project_script']}")
    context_file = _write_context(context, design, stage)
    tool_root = context_file.parent
    workflow_root = context.workflow_root
    def vivado_command(action: str, label: str) -> tuple[list[str], Path]:
        log = tool_root / f"vivado-{label}-console.log"
        command = [
            resolve_tool(context.workflow_root, "vivado", "vivado"), "-mode", "batch",
            "-journal", str(tool_root / f"vivado-{label}.jou"),
            "-log", str(tool_root / f"vivado-{label}.log"),
            "-tempDir", str(tool_root / "temp"),
            "-source", str(workflow_root / "tools" / "tcl" / "vivado_run.tcl"),
            "-tclargs", str(context_file), stage, action, str(project_script),
            str(workflow_root / "reports" / "tools" / "tcl" / "vivado_reports.tcl"),
        ]
        return command, log

    if stage in {"synth", "route"}:
        command, prepare_log = vivado_command("prepare", "prepare")
        result = run_process(command, cwd=tool_root, log=prepare_log)
        if result.returncode != 0:
            raise WorkflowError(f"Vivado {stage} preparation did not complete; see {result.log}")
        requested_run = _native_run_request(prepare_log)
        if requested_run is not None:
            run_root = Path(vivado["xpr"]).parent / f"{vivado['project_name']}.runs" / requested_run
            run_root = context.project_root / run_root
            run_script = run_root / "runme.bat"
            if not run_script.is_file():
                raise WorkflowError(f"Vivado did not generate the native run script: {run_script}")
            native_result = run_process(
                [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", str(run_script)],
                cwd=run_root,
                log=tool_root / "vivado-run-console.log",
                timeout=load_profiles(context.workflow_root)["vivado"]["native_run_timeout_seconds"],
            )
            if native_result.returncode != 0:
                raise WorkflowError(f"Vivado native run {requested_run} did not complete; see {native_result.log}")
        command, collect_log = vivado_command("collect", "collect")
        result = run_process(command, cwd=tool_root, log=collect_log)
    else:
        command, execute_log = vivado_command("execute", "console")
        result = run_process(command, cwd=tool_root, log=execute_log)
    if result.returncode != 0:
        raise WorkflowError(f"Vivado {stage} did not complete; see {result.log}")
    report_root = context.project_root / "output" / "report" / ".staging" / stage / "physical"
    if stage == "sync":
        return {"status": "PASS", "xpr": vivado["xpr"]}
    if stage == "synth":
        metrics = _parse_utilization(report_root / "synth_utilization.rpt")
        failures = _budget_result(design, "synth", metrics)
        if failures:
            raise ToolFailure("synthesis resource gate failed: " + "; ".join(failures))
        return {"status": "PASS", "metrics": metrics, "reports": ["physical/synth_utilization.rpt"]}
    if stage == "route":
        metrics = _parse_utilization(report_root / "route_utilization.rpt")
        for line in (report_root / "route_metrics.txt").read_text(encoding="utf-8").splitlines():
            key, value = line.split("=", 1)
            metrics[key] = float(value)
        timing_text = (report_root / "route_timing.rpt").read_text(encoding="utf-8", errors="replace")
        row = re.search(r"^\s*(-?[0-9.]+)\s+(-?[0-9.]+)\s+\d+\s+\d+\s+(-?[0-9.]+)\s+(-?[0-9.]+)", timing_text, re.MULTILINE)
        if row:
            metrics["setup_tns"] = float(row.group(2))
            metrics["hold_tns"] = float(row.group(4))
        route_text = (report_root / "route_status.rpt").read_text(encoding="utf-8", errors="replace")
        unrouted = re.search(r"Unrouted Nets\s*:\s*(\d+)", route_text)
        metrics["unrouted"] = float(unrouted.group(1)) if unrouted else 0.0
        failures = _budget_result(design, "route", metrics)
        if metrics.get("drc_errors", 0) != 0 or metrics.get("unrouted", 0) != 0:
            failures.append("route contains DRC errors or unrouted nets")
        if failures:
            raise ToolFailure("route gate failed: " + "; ".join(failures))
        return {"status": "PASS", "metrics": metrics, "reports": [
            "physical/route_timing.rpt", "physical/route_utilization.rpt",
            "physical/route_drc.rpt", "physical/route_status.rpt",
        ]}
    if stage == "release":
        bitstream_value = vivado["results"].get("bitstream", "")
        xsa_value = vivado["results"].get("xsa", "")
        checkpoint_value = vivado["results"].get("checkpoint", "")
        expected = [item for item in (bitstream_value, xsa_value, checkpoint_value) if item]
        if not expected or any(not (context.project_root / item).is_file() for item in expected):
            raise WorkflowError("Vivado release products are incomplete")
        return {
            "status": "PASS",
            "bitstream": bitstream_value,
            "xsa": xsa_value,
            "checkpoint": checkpoint_value,
        }
    raise ContractError(f"unsupported Vivado stage: {stage}")


def run_xsim(context: ProjectContext, design: dict[str, Any]) -> dict[str, Any]:
    verification = design["implementation"]["verification_sources"]
    timeouts = load_profiles(context.workflow_root)["xsim"]["timeouts_seconds"]
    tool_root = context.project_root / "work" / "tool" / "verify" / "xsim"
    if tool_root.exists():
        shutil.rmtree(tool_root)
    tool_root.mkdir(parents=True)
    report_root = context.project_root / "output" / "report" / ".staging" / "verify" / "verification"
    report_root.mkdir(parents=True, exist_ok=True)
    for relative in verification.get("data_roots", []):
        target = context.project_root / relative
        if not target.is_dir():
            raise ContractError(f"verification data root is missing: {relative}")
        _junction(tool_root / relative, target)
    sources = [context.project_root / item for item in design["implementation"]["rtl"]["sources"]]
    sources.extend(context.project_root / item for item in verification.get("models", []))
    sources.append(context.project_root / verification["top_file"])
    xvlog = [resolve_tool(context.workflow_root, "xsim", "xvlog"), "--log", str(report_root / "xvlog.log")]
    for include in verification.get("include_dirs", []):
        xvlog.extend(["-i", str(context.project_root / include)])
    for define in verification.get("defines", []):
        xvlog.extend(["-d", define])
    xvlog.extend(str(item) for item in sources)
    compile_result = run_process(
        xvlog,
        cwd=tool_root,
        log=report_root / "xvlog-console.log",
        timeout=timeouts["compile"],
    )
    if compile_result.returncode != 0:
        raise ToolFailure("formal TB compilation failed")
    snapshot = "workflow_snapshot"
    elaborate = run_process(
        [resolve_tool(context.workflow_root, "xsim", "xelab"), verification["top"], "-s", snapshot,
         "--timescale", verification.get("timescale", "1ns/1ps"),
         "--debug", "typical",
         "--log", (report_root / "xelab.log").as_posix()],
        cwd=tool_root,
        log=report_root / "xelab-console.log",
        timeout=timeouts["elaborate"],
    )
    if elaborate.returncode != 0:
        raise ToolFailure("formal TB elaboration failed")
    run_tcl = tool_root / "run.tcl"
    atomic_write_text(
        run_tcl,
        f"cd {_tcl_value(context.project_root)}\n"
        "set wf_wave_objects [get_objects /tb_top/*]\n"
        "set wf_wave_objects [concat $wf_wave_objects [get_objects /tb_top/*/*]]\n"
        "set wf_wave_objects [concat $wf_wave_objects [get_objects /tb_top/*/*/*]]\n"
        "log_wave $wf_wave_objects\n"
        "run all\n"
        "quit\n",
    )
    simulation = run_process(
        [resolve_tool(context.workflow_root, "xsim", "xsim"), snapshot, "--tclbatch", run_tcl.as_posix(),
         "--tempDir", (tool_root / "temp").as_posix(),
         "--wdb", (report_root / "waves.wdb").as_posix(),
         "--log", (report_root / "xsim.log").as_posix()],
        cwd=tool_root,
        log=report_root / "xsim-console.log",
        timeout=timeouts["simulate"],
    )
    root_journal = tool_root / "xsim.jou"
    if root_journal.exists():
        shutil.move(str(root_journal), str(report_root / "xsim.jou"))
    if simulation.returncode != 0:
        raise ToolFailure("formal TB simulation failed")
    required = [
        item["id"] for item in design["verification"]["cases"]
        if item.get("stage", "verify") == "verify"
    ]
    parsed = parse_xsim_log(report_root / "xsim.log", required)
    parsed["raw_reports"] = ["verification/xsim.log", "verification/waves.wdb"]
    return parsed
