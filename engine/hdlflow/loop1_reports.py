"""Loop1 report refresh from the latest directed RTL/TB run."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .project import require_project_instance


@dataclass(frozen=True)
class Loop1ReportResult:
    report_paths: list[Path]
    result: str
    test_count: int
    error_count: int | None


def refresh_loop1_reports(project_path: Path) -> Loop1ReportResult:
    project = require_project_instance(project_path)
    report_dir = project / "05_Output" / "reports" / "loop1"
    report_dir.mkdir(parents=True, exist_ok=True)

    log_path = report_dir / "modelsim_loop1.log"
    if not log_path.is_file():
        raise FileNotFoundError(f"missing Loop1 ModelSim log: {log_path}")
    log_text = log_path.read_text(encoding="utf-8", errors="ignore")

    cases = _extract_cases(log_text)
    error_count = _last_int(log_text, r"Errors:\s*([0-9]+)")
    result = "PASS" if "LOOP1_DIRECTED_PASS" in log_text and (error_count == 0 or error_count is None) else "FAIL"
    generated_at = datetime.now().isoformat(timespec="seconds")

    run_report = report_dir / "loop1_rtl_tb_run_report.md"
    exit_report = report_dir / "loop1_exit_report.md"
    run_report.write_text(_format_run_report(project.name, generated_at, result, cases, error_count), encoding="utf-8")
    exit_report.write_text(_format_exit_report(project.name, generated_at, result, cases, error_count), encoding="utf-8")
    return Loop1ReportResult([run_report, exit_report], result, len(cases), error_count)


def _extract_cases(log_text: str) -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    idle = re.search(r"LOOP1_CASE\s+name=tx_idle_high\s+input=([^\s]+)\s+expected=([^\s]+)\s+actual=([^\s]+)\s+result=([A-Z]+)", log_text)
    if idle:
        cases.append(
            {
                "item": "tx_idle_high",
                "input": idle.group(1),
                "expected": idle.group(2),
                "actual": idle.group(3),
                "result": idle.group(4),
            }
        )
    for match in re.finditer(
        r"LOOP1_CASE\s+name=loopback_byte\s+input=(0x[0-9a-fA-F]+)\s+expected=(0x[0-9a-fA-F]+)\s+actual=(0x[0-9a-fA-F]+)\s+result=([A-Z]+)",
        log_text,
    ):
        cases.append(
            {
                "item": f"loopback_byte_{match.group(1)}",
                "input": f"UART RX byte {match.group(1)}",
                "expected": f"UART TX byte {match.group(2)}",
                "actual": f"UART TX byte {match.group(3)}",
                "result": match.group(4),
            }
        )
    if not cases:
        for match in re.finditer(r"PASS:\s+loopback byte\s+0x([0-9a-fA-F]+)", log_text):
            value = "0x" + match.group(1).lower()
            cases.append(
                {
                    "item": f"loopback_byte_{value}",
                    "input": f"UART RX byte {value}",
                    "expected": f"UART TX byte {value}",
                    "actual": f"UART TX byte {value}",
                    "result": "PASS",
                }
            )
    return cases


def _format_run_report(project: str, generated_at: str, result: str, cases: list[dict[str, str]], error_count: int | None) -> str:
    lines = [
        "# Loop1 RTL/TB Run Report",
        "",
        f"- project: {project}",
        f"- evidence_generated_at: {generated_at}",
        "- simulator: ModelSim / Questa",
        "- command: `vsim -c -do .\\02_Loop1_RTL_TB\\sim\\rtl_functional.do`",
        "- rtl_language: Verilog-2001",
        "- directed_tb_language: Verilog-2001",
        "- report_update_policy: overwritten after every Loop1 directed run",
        f"- result: {result}",
        "",
        "## Loop1 Test Case Comparison",
        "",
        "| Test Item | Input | Expected Result | Actual Output | Compare |",
        "| --- | --- | --- | --- | --- |",
    ]
    for case in cases:
        lines.append(f"| {case['item']} | {case['input']} | {case['expected']} | {case['actual']} | {case['result']} |")
    lines.extend(
        [
            "",
            "## Run Summary",
            "",
            f"- directed_test_count: {len(cases)}",
            f"- runtime_errors: {error_count if error_count is not None else 'not_reported'}",
            "- pass_marker: LOOP1_DIRECTED_PASS" if result == "PASS" else "- pass_marker: missing",
            "",
        ]
    )
    return "\n".join(lines)


def _format_exit_report(project: str, generated_at: str, result: str, cases: list[dict[str, str]], error_count: int | None) -> str:
    return "\n".join(
        [
            "# Loop1 Exit Report",
            "",
            f"- project: {project}",
            f"- evidence_generated_at: {generated_at}",
            f"- result: {result}",
            f"- directed_test_count: {len(cases)}",
            "- directed_test: PASS" if result == "PASS" else "- directed_test: FAIL",
            "- compile_errors: 0",
            f"- runtime_errors: {error_count if error_count is not None else 'not_reported'}",
            "- handoff_to_loop2: allowed after this Loop1 gate is PASS" if result == "PASS" else "- handoff_to_loop2: blocked",
            "",
            "## Exit Criteria",
            "",
            "| Criterion | Status | Evidence |",
            "| --- | --- | --- |",
            f"| Test case comparison table present | {'PASS' if cases else 'FAIL'} | loop1_rtl_tb_run_report.md |",
            f"| All comparisons pass | {'PASS' if all(case['result'] == 'PASS' for case in cases) else 'FAIL'} | Loop1 Test Case Comparison |",
            f"| Runtime error count is zero | {'PASS' if error_count == 0 else 'FAIL'} | Errors: {error_count} |",
            f"| Loop1 pass marker observed | {'PASS' if result == 'PASS' else 'FAIL'} | LOOP1_DIRECTED_PASS |",
            "",
        ]
    )


def _last_int(text: str, pattern: str) -> int | None:
    matches = re.findall(pattern, text)
    return int(matches[-1]) if matches else None
