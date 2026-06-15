import os
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock
from contextlib import closing
from pathlib import Path

from hdlflow.cli import _tool_launcher_value
from hdlflow.config import GLOBAL_CONFIG_FILES, load_project, load_workspace, validate_config
from hdlflow.change_control import assess_change_scope, approve_change, record_impact, validate_change_bundle
from hdlflow.design_doc import generate_design_document
from hdlflow.docgen import RemovedWorkflowError, check_docset, generate_docset, generate_single_doc
from hdlflow.docgen.constants import DOC_DEFINITIONS
from hdlflow.doctor import _workspace_root_tool_log_issues
from hdlflow.frontdoor_guard import evaluate_command_frontdoor_guard, require_frontdoor_ready, require_stage_ready
from hdlflow.gates import (
    run_final_audit,
    _check_change_control,
    _check_doc_sources,
    _check_docparse_extract_policy,
    _check_final,
    _check_forbidden_formal_text,
    _check_manifest_drift,
    _check_no_project_local_loop3_scripts,
    _check_no_ad_hoc_analysis_artifacts,
    _check_protected_gate_manifest_drift,
    _refresh_reports_for_gate,
    _check_skill_manifest_drift,
    _loop1_full_function_matrix_check,
    _loop1_deterministic_gate_check,
    _check_loop1_waveform_advisory_report,
    _loop2_coverage_triage_check,
    _loop2_configured_scenario_evidence_check,
    _loop2_scenario_count_check,
    _loop2_stress_transaction_check,
    _check_loop3,
    _loop3_configured_serial_stress_check,
    _check_source_policy,
    _loop3_serial_echo_check,
    _gate_paths,
    _rel as _gate_rel,
    _check_project_root_tool_logs,
    _check_rtl_comment_headers,
    _check_rtl_task_usage,
    _requirement_source_files,
    _structured_result_pass_check,
    _zero_count_check,
)
from hdlflow.requirements_frontend import (
    _check_module_plan_contract,
    check_requirements_frontend,
    initialize_requirements_frontend,
    required_frontend_paths,
)
from hdlflow.loop2_bindings import write_loop2_database_preflight
from hdlflow.memory import (
    _is_active_gate,
    append_plan_note,
    auto_record_workflow_event,
    check_memory,
    start_active_plan,
    update_active_plan_step,
)
from hdlflow.plan_checks import check_plan
from hdlflow.report_checks import check_reports
from hdlflow.reports.constants import BLOCKED_BANNER, FAIL_BANNER, LOOP1_REPORT, LOOP2_REPORT, PASS_BANNER
from hdlflow.reports.loop1_report import generate_loop1_report
from hdlflow.reports.parser_hdlflow_events import parse_loop1_events, parse_loop2_events
from hdlflow.reports.render_report import build_report_payload, render_report_markdown
from hdlflow.ralph_loop import ralph_check, ralph_status, ralph_step
from hdlflow.release import release_preflight
from hdlflow.repair import apply_repair_ticket, diagnose_repairs
from hdlflow.prototype import refresh_loop3_reports
from hdlflow.review import check_review_findings
from hdlflow.rtl_skill_audit import run_rtl_skill_audit
from hdlflow.sandbox import add_exploration_note, promote_exploration, start_exploration
from hdlflow.schema_contracts import schema_check
from hdlflow.prototype import _check_prototype_mode_intent, _is_placeholder, generate_vitis_boot_files
from hdlflow.scaffold import PROJECT_CREATE_ENTRYPOINT_ENV, create_project
from hdlflow.simple_yaml import parse_yaml
from hdlflow.state_sync import sync_project_state
from hdlflow.validate import REQUIRED_PATHS, validate_project
from hdlflow.waveform_gate import WAVEFORM_GATE_JSON_REL, check_loop1_waveform_gate_report, run_loop1_waveform_gate


class SimpleYamlTests(unittest.TestCase):
    def test_parse_platform_config_subset(self):
        data = parse_yaml(
            """
schema_version: 1
project:
  name: demo
flags:
  - enabled
  - mode: develop
empty: []
"""
        )

        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["project"]["name"], "demo")
        self.assertEqual(data["flags"][0], "enabled")
        self.assertEqual(data["flags"][1]["mode"], "develop")
        self.assertEqual(data["empty"], [])

    def test_parse_list_item_mapping_with_bare_dash(self):
        data = parse_yaml(
            """
findings:
  -
    id: REV-001
    severity: high
"""
        )

        self.assertEqual(data["findings"][0]["id"], "REV-001")
        self.assertEqual(data["findings"][0]["severity"], "high")


class ConfigValidationTests(unittest.TestCase):
    def test_node_io_policy_accepts_path_lists(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            for name, rel in GLOBAL_CONFIG_FILES.items():
                path = workspace / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                if name == "workspace":
                    path.write_text("workspace: demo\n", encoding="utf-8")
                elif name == "gates":
                    path.write_text("gates:\n  develop: {}\n", encoding="utf-8")
                else:
                    path.write_text("placeholder: true\n", encoding="utf-8")
            project = workspace / "prj" / "demo"
            project.mkdir(parents=True)
            config_path = workspace / "prj" / "demo" / "work" / "config" / "project_config.yaml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(
                "\n".join(
                    [
                        "schema_version: 1",
                        "project:",
                        "  name: demo",
                        "pipeline_expected:",
                        "  - work/docparse",
                        "nodes:",
                        "  work/docparse:",
                        "    outputs:",
                        "      machine_readable_specs:",
                        "        - work/docparse/structured_spec/interface_spec.yaml",
                        "        - work/docparse/structured_spec/register_map.yaml",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            errors = validate_config(load_workspace(workspace), load_project(project))

            self.assertEqual(errors, [])


class ToolLauncherTests(unittest.TestCase):
    def test_configured_environment_override_wins(self):
        old_value = os.environ.get("HDLFLOW_VIVADO_VIVADO_BAT")
        os.environ["HDLFLOW_VIVADO_VIVADO_BAT"] = "D:/tool/vivado.bat"
        try:
            value = _tool_launcher_value(
                "vivado",
                "vivado_bat",
                {
                    "env_override": {"vivado_bat": "HDLFLOW_VIVADO_VIVADO_BAT"},
                    "launchers": {"vivado_bat": "E:/Vivado/Vivado/2024.2/bin/vivado.bat"},
                },
            )
            self.assertEqual(value, "D:/tool/vivado.bat")
        finally:
            if old_value is None:
                os.environ.pop("HDLFLOW_VIVADO_VIVADO_BAT", None)
            else:
                os.environ["HDLFLOW_VIVADO_VIVADO_BAT"] = old_value


class PrototypePlanTests(unittest.TestCase):
    def test_change_me_names_are_placeholders(self):
        self.assertTrue(_is_placeholder("change_me_top"))
        self.assertTrue(_is_placeholder("todo"))
        self.assertFalse(_is_placeholder("pl_uart_loopback_top"))

    def test_pure_pl_intent_blocks_unjustified_ps_pl_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            (project / "work/docparse" / "prototype").mkdir(parents=True)
            (project / "work/docparse" / "prototype" / "prototype_plan.yaml").write_text(
                "assumptions:\n  - Prototype uses pure PL resources.\n",
                encoding="utf-8",
            )
            errors = []
            warnings = []

            _check_prototype_mode_intent(project, "ps_pl", {}, errors, warnings)

            self.assertTrue(any("mode conflict" in item for item in errors))


class Loop2RiskGateTests(unittest.TestCase):
    def test_loop2_gate_report_refresh_waits_for_loop1_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_manifest_payload(project, "work/docparse", {})

            checks = _refresh_reports_for_gate(project, "work/loop2_uvm")

            self.assertEqual(checks[0].status, "FAIL")
            self.assertIn("Loop1 prerequisite", checks[0].detail)

    def test_structured_loop1_log_markers_generate_sectioned_report(self):
        log = (
            "HDLFLOW|TEST_BEGIN|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=opcode_00|scope=spi\n"
            "HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=opcode_00|txn_id=txn_0001|sent=spi_cmd_00|expected=status_clear|actual=status_clear|latency_cycles=3|result=PASS\n"
            "HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|total_tests=1|passed_tests=1|failed_tests=0|total_checks=1|passed_checks=1|failed_checks=0|result=PASS\n"
        )
        parsed = parse_loop1_events(log)
        payload = build_report_payload(LOOP1_REPORT, "demo", parsed, change_id=None)
        report = render_report_markdown(LOOP1_REPORT, payload)

        self.assertEqual(parsed["transactions"][0]["test_id"], "opcode_00")
        self.assertIn("## 2. Main Results", report)
        self.assertIn("| opcode_00 | txn_0001 | spi_cmd_00 | status_clear | status_clear | 3 | PASS |", report)
        self.assertIn(PASS_BANNER, report)
        self.assertNotIn("## Evidence", report)

    def test_loop1_missing_summary_blocks_report(self):
        parsed = parse_loop1_events(
            "HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=opcode_00|txn_id=txn_0001|sent=spi_cmd_00|expected=status_clear|actual=status_clear|latency_cycles=3|result=PASS"
        )
        payload = build_report_payload(LOOP1_REPORT, "demo", parsed, change_id=None)
        report = render_report_markdown(LOOP1_REPORT, payload)

        self.assertEqual(parsed["result"], "BLOCKED")
        self.assertIn("missing_structured_summary", parsed["parser_errors"])
        self.assertIn(BLOCKED_BANNER, report)

    def test_loop1_missing_check_field_blocks_report(self):
        parsed = parse_loop1_events(
            "HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=opcode_00|txn_id=txn_0001|sent=spi_cmd_00|expected=status_clear|latency_cycles=3|result=PASS\n"
            "HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|total_tests=1|passed_tests=1|failed_tests=0|total_checks=1|passed_checks=1|failed_checks=0|result=PASS"
        )

        self.assertEqual(parsed["result"], "BLOCKED")
        self.assertTrue(any("missing field" in item for item in parsed["parser_errors"]))

    def test_structured_loop2_log_markers_generate_sectioned_report(self):
        log = (
            "HDLFLOW|UVM_CHECK|schema=hdlflow_event_v1|version=1|stage=loop2|test_id=stress_fifo|txn_id=txn_0064|sent=burst_write_and_read|expected=scoreboard_match|actual=scoreboard_match|latency_cycles=8|result=PASS\n"
            "HDLFLOW|UVM_SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop2|uvm_error=0|uvm_fatal=0|total_checks=64|failed_checks=0|coverage=91.5|result=PASS\n"
        )
        parsed = parse_loop2_events(log)
        payload = build_report_payload(LOOP2_REPORT, "demo", parsed, change_id=None)
        report = render_report_markdown(LOOP2_REPORT, payload)

        self.assertEqual(parsed["transactions"][0]["test_id"], "stress_fifo")
        self.assertEqual(parsed["summary"]["total_checks"], 64)
        self.assertIn("## 2. Main Results", report)
        self.assertIn("| stress_fifo | txn_0064 | burst_write_and_read | scoreboard_match | scoreboard_match | 8 | PASS |", report)
        self.assertIn(PASS_BANNER, report)
        self.assertNotIn("## Evidence", report)

    def test_loop2_failed_check_sets_fail_banner(self):
        parsed = parse_loop2_events(
            "HDLFLOW|UVM_CHECK|schema=hdlflow_event_v1|version=1|stage=loop2|test_id=stress_fifo|txn_id=txn_0064|sent=burst_write_and_read|expected=scoreboard_match|actual=mismatch|result=FAIL|reason=scoreboard_mismatch\n"
            "HDLFLOW|UVM_SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop2|uvm_error=0|uvm_fatal=0|total_checks=64|failed_checks=1|coverage=91.5|result=FAIL\n"
        )
        payload = build_report_payload(LOOP2_REPORT, "demo", parsed, change_id=None)
        report = render_report_markdown(LOOP2_REPORT, payload)

        self.assertEqual(parsed["result"], "FAIL")
        self.assertIn(FAIL_BANNER, report)
        self.assertIn("scoreboard_mismatch", report)

    def test_loop1_full_function_matrix_uses_source_bound_opcodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            register_map = project / "work/docparse/structured_spec/register_map.yaml"
            register_map.parent.mkdir(parents=True, exist_ok=True)
            register_map.write_text(
                "\n".join(
                    [
                        "schema_version: 1",
                        "opcodes:",
                        "  - name: READ",
                        "    code: 01h",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            partial_report = "\n".join(
                [
                    "opcode_00 PASS",
                    "partial",
                    "rx_location32_overwrite",
                    "master_reset_keeps_control_register",
                    "selftest",
                    "tx_fifo",
                ]
            )

            check = _loop1_full_function_matrix_check(project, partial_report)

            self.assertEqual(check.status, "FAIL")
            self.assertIn("01h", check.detail)

    def test_loop1_full_function_matrix_rejects_compat_opcode_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            register_map = project / "work/docparse/structured_spec/register_map.yaml"
            register_map.parent.mkdir(parents=True, exist_ok=True)
            register_map.write_text("opcodes:\n  - name: READ\n    code: 01h\n", encoding="utf-8")
            report = "\n".join(
                [
                    "| opcode_01 | compat | PASS | PASS | PASS |",
                    "partial",
                    "rx_location32_overwrite",
                    "master_reset_keeps_control_register",
                    "selftest",
                    "tx_fifo",
                ]
            )

            check = _loop1_full_function_matrix_check(project, report)

            self.assertEqual(check.status, "FAIL")
            self.assertIn("01h", check.detail)

    def test_loop1_deterministic_gate_rejects_simulator_error_even_with_tb_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            log_path = project / "work/loop1_rtl_tb/current/log/modelsim.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_text = "\n".join(
                [
                    "HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=case0|txn_id=txn0|sent=a|expected=b|actual=b|latency_cycles=1|result=PASS",
                    "HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|total_tests=1|passed_tests=1|failed_tests=0|total_checks=1|passed_checks=1|failed_checks=0|result=PASS",
                    "** Error: simulator reported a real error after TB summary",
                    "",
                ]
            )
            log_path.write_text(log_text, encoding="utf-8")
            payload = build_report_payload(LOOP1_REPORT, "demo", parse_loop1_events(log_text), change_id=None)

            check = _loop1_deterministic_gate_check(project, payload)

            self.assertEqual(check.status, "FAIL")
            self.assertIn("simulator_errors_nonzero", check.detail)

    def test_loop1_waveform_report_is_advisory_not_hard_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            check = _check_loop1_waveform_advisory_report(project, WAVEFORM_GATE_JSON_REL, "develop")

            self.assertEqual(check.status, "PASS")
            self.assertEqual(check.name, "loop1_waveform_advisory")
            self.assertIn("advisory waveform issue", check.detail)

    def test_doc_sources_reject_mojibake_requirement_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            req_dir = project / "input" / "spec"
            req_dir.mkdir(parents=True, exist_ok=True)
            (req_dir / "chat_requirement.md").write_text(
                "绔 鐨 锛 鏁 閲嶆柊 requirement text\n",
                encoding="utf-8",
            )

            checks = _check_doc_sources(project)

            self.assertTrue(
                any(
                    check.name == "source_encoding_integrity"
                    and check.status == "FAIL"
                    and "chat_requirement.md" in check.detail
                    for check in checks
                )
            )

    def test_loop2_configured_scenario_markers_replace_hardcoded_opcode_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            config_dir = project / "work" / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "project_config.yaml").write_text(
                "\n".join(
                    [
                        "schema_version: 1",
                        "project:",
                        "  name: demo",
                        "nodes:",
                        "  work/loop2_uvm:",
                        "    uvm_policy:",
                        "      required_scenario_markers:",
                        "        ps_pl_ddr_path:",
                        "          - PS_PL_DDR_PATH_PASS",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            missing = _loop2_configured_scenario_evidence_check(project, "OPCODE_SWEEP_PASS=1\n")
            present = _loop2_configured_scenario_evidence_check(project, "PS_PL_DDR_PATH_PASS\n")

            self.assertEqual(missing.status, "FAIL")
            self.assertIn("PS_PL_DDR_PATH_PASS", missing.detail)
            self.assertEqual(present.status, "PASS")

    def test_loop1_waveform_query_gate_writes_only_new_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_loop1_semantic_waveform_evidence(project)

            with _fake_pywellen_installed():
                result = run_loop1_waveform_gate(project)

            self.assertTrue(result.ok, result.errors)
            self.assertEqual(check_loop1_waveform_gate_report(project), [])
            payload = json.loads(result.json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["backend"], "pywellen")
            self.assertEqual(payload["window_count"], 1)
            self.assertGreaterEqual(payload["signal_count"], 4)
            self.assertTrue((project / "output/reports/loop1/waveform_query_report.md").is_file())
            self.assertTrue((project / "output/reports/loop1/waveform_gate.json").is_file())
            self.assertTrue((project / "output/reports/loop1/query_transcript.json").is_file())

    def test_loop1_waveform_query_gate_uses_output_wave_deliverables_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_loop1_semantic_waveform_evidence(project, wave_rel="work/loop1_rtl_tb/_runtime/wave")

            with _fake_pywellen_installed():
                result = run_loop1_waveform_gate(project, vcd_path=project / "work/loop1_rtl_tb/_runtime/wave/top_ports.vcd")

            self.assertFalse(result.ok)
            self.assertTrue(any("output/sim/loop1/wave" in item for item in result.errors))

    def test_loop1_waveform_query_gate_rejects_unknowns_inside_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_loop1_semantic_waveform_evidence(project, unknown=True)

            with _fake_pywellen_installed():
                result = run_loop1_waveform_gate(project)

            self.assertFalse(result.ok)
            payload = json.loads(result.json_path.read_text(encoding="utf-8"))
            details = "\n".join(str(item.get("detail", "")) for item in payload["checks"])
            self.assertIn("X/Z", details)

    def test_loop1_waveform_query_gate_report_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            errors = check_loop1_waveform_gate_report(project)

            self.assertTrue(any("missing Loop1 waveform rule-engine report" in item for item in errors))

    def test_loop1_waveform_rule_failure_stays_advisory_for_loop1_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_loop1_semantic_waveform_evidence(project, unknown=True)

            with _fake_pywellen_installed():
                result = run_loop1_waveform_gate(project)

            self.assertFalse(result.ok)
            advisory = _check_loop1_waveform_advisory_report(project, WAVEFORM_GATE_JSON_REL, "develop")
            self.assertEqual(advisory.status, "PASS")
            self.assertIn("advisory waveform issue", advisory.detail)

    def test_loop1_waveform_query_gate_passes_manifest_top_ports(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_loop1_semantic_waveform_evidence(project)

            with _fake_pywellen_installed():
                result = run_loop1_waveform_gate(project)

            self.assertTrue(result.ok, result.errors)
            self.assertEqual(check_loop1_waveform_gate_report(project), [])
            payload = json.loads(result.json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"], "PASS")
            self.assertEqual(payload["gate_policy"], "advisory")
            self.assertEqual(payload["llm_decision_source"], False)
            self.assertEqual(payload["manifest"], "work/loop1_rtl_tb/config/top_wave_manifest.yaml")
            self.assertTrue((project / "output/reports/loop1/query_transcript.json").is_file())

    def test_unclassified_coverage_triage_blocks_loop2_closure(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            check = _loop2_coverage_triage_check(
                project,
                "| pl_uart_rx.v toggle | 70.0% | Classify as missing legal stimulus, unreachable-by-spec, or waiver before Loop2 closure. |",
            )

            self.assertEqual(check.status, "FAIL")
            self.assertEqual(check.name, "loop2_coverage_triage_closed")

    def test_coverage_triage_waiver_must_match_unresolved_item(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            (project / "work" / "gates" / "coverage_waiver.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "project": "demo",
                        "waivers": [
                            {
                                "item": "other_file.v statement",
                                "classification": "unreachable-by-spec",
                                "status": "approved",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            check = _loop2_coverage_triage_check(
                project,
                "| pl_uart_rx.v toggle | 70.0% | Classify as missing legal stimulus, unreachable-by-spec, or waiver before Loop2 closure. |",
            )

            self.assertEqual(check.status, "FAIL")
            self.assertIn("pl_uart_rx.v toggle", check.detail)

    def test_coverage_triage_matching_waiver_closes_only_that_item(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            (project / "work" / "gates" / "coverage_waiver.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project": "demo",
                        "waivers": [
                            {
                                "item": "pl_uart_rx.v toggle",
                                "classification": "unreachable-by-spec",
                                "status": "approved",
                                "evidence": "REQ-DEMO-001 has no legal toggle path",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            check = _loop2_coverage_triage_check(
                project,
                "| pl_uart_rx.v toggle | 70.0% | Classify as missing legal stimulus, unreachable-by-spec, or waiver before Loop2 closure. |",
            )

            self.assertEqual(check.status, "PASS")

    def test_zero_count_check_rejects_later_nonzero_count(self):
        check = _zero_count_check("loop2_zero_uvm_error", "UVM_ERROR : 0\nUVM_ERROR : 2\n", "UVM_ERROR")

        self.assertEqual(check.status, "FAIL")
        self.assertIn("2", check.detail)

    def test_structured_result_pass_rejects_failed_case_rows(self):
        report = "\n".join(
            [
                "- result: PASS",
                "| item | stimulus | expected | actual | result |",
                "| --- | --- | --- | --- | --- |",
                "| opcode_00 | cmd | ok | mismatch | FAIL |",
            ]
        )

        check = _structured_result_pass_check("loop2_regression_pass", report)

        self.assertEqual(check.status, "FAIL")

    def test_loop2_requires_five_scenarios_and_multi_stimulus_stress(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            uvm_dir = project / "output" / "uvm" / "seq_lib"
            uvm_dir.mkdir(parents=True)
            (uvm_dir / "scenarios.svh").write_text(
                "\n".join(
                    [
                        "class reset_mid_frame_sequence; endclass",
                        "class bad_stop_bit_sequence; endclass",
                        "class glitch_sequence; endclass",
                        "class overflow_sequence; endclass",
                        "class baud_div_434_sequence; endclass",
                        "class fifo_stress_sequence;",
                        "  task body;",
                        "    start_kind(1);",
                        "    start_kind(2);",
                        "  endtask",
                        "endclass",
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(_loop2_scenario_count_check(project).status, "PASS")
            self.assertEqual(_loop2_stress_transaction_check(project).status, "PASS")

    def test_preflight_generates_uvm_database_flesh_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            _create_minimal_uvm_layout(project)
            _create_minimal_uvm_library_db(workspace)

            result = write_loop2_database_preflight(workspace, project)

            self.assertFalse(result.missing_items)
            self.assertTrue(result.report_path.exists())
            self.assertIsNotNone(result.flesh_plan_path)
            flesh_plan = result.flesh_plan_path.read_text(encoding="utf-8")
            self.assertIn("## Guide Retrieval", flesh_plan)
            self.assertIn("uvm_config_db", flesh_plan)
            self.assertIn("result: PASS", flesh_plan)


class DocparsePolicyTests(unittest.TestCase):
    def test_gate_rel_handles_workspace_global_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            global_config = workspace / "env" / "rule" / "global" / "gates" / "global_gate_rules.yaml"
            global_config.parent.mkdir(parents=True)
            global_config.write_text("schema_version: 1\n", encoding="utf-8")
            (workspace / "env" / "rule" / "global" / "workspace_config.yaml").parent.mkdir(parents=True, exist_ok=True)
            (workspace / "env" / "rule" / "global" / "workspace_config.yaml").write_text("workspace: demo\n", encoding="utf-8")

            self.assertEqual(_gate_rel(project, global_config), "workspace:env/rule/global/gates/global_gate_rules.yaml")

    def test_rtl_header_must_match_control_register_ownership(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            rtl_dir = project / "output" / "rtl"
            rtl_dir.mkdir(parents=True, exist_ok=True)
            (rtl_dir / "regs.v").write_text(
                "\n".join(
                    [
                        "// Module      : regs",
                        "// Description : Flag mapping logic.",
                        "// Scope:",
                        "//   - Maps FIFO flags.",
                        "module regs(input wire [15:0] control_reg);",
                        "endmodule",
                    ]
                ),
                encoding="utf-8",
            )

            check = _check_rtl_comment_headers(project)

            self.assertEqual(check.status, "FAIL")
            self.assertIn("control-register ownership", check.detail)

    def test_rtl_v_files_must_not_declare_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            rtl_dir = project / "output" / "rtl"
            rtl_dir.mkdir(parents=True, exist_ok=True)
            (rtl_dir / "demo_top.v").write_text(
                "\n".join(
                    [
                        "module demo_top;",
                        "  task helper;",
                        "  endtask",
                        "endmodule",
                    ]
                ),
                encoding="utf-8",
            )

            check = _check_rtl_task_usage(project)

            self.assertEqual(check.status, "FAIL")
            self.assertIn("output/rtl/demo_top.v", check.detail)

    def test_tb_v_files_may_declare_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            rtl_dir = project / "output" / "rtl"
            tb_dir = project / "output" / "tb"
            rtl_dir.mkdir(parents=True, exist_ok=True)
            tb_dir.mkdir(parents=True, exist_ok=True)
            (rtl_dir / "demo_top.v").write_text("module demo_top; endmodule\n", encoding="utf-8")
            (tb_dir / "demo_tb.v").write_text(
                "\n".join(
                    [
                        "module demo_tb;",
                        "  task drive_word;",
                        "  endtask",
                        "endmodule",
                    ]
                ),
                encoding="utf-8",
            )

            check = _check_rtl_task_usage(project)

            self.assertEqual(check.status, "PASS")

    def test_requirement_sources_include_generated_requirement_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            req = project / "input" / "spec"
            req.mkdir(parents=True)
            (req / "module_plan.md").write_text("updated plan\n", encoding="utf-8")
            (req / "path_partition.md").write_text("updated paths\n", encoding="utf-8")

            names = {path.name for path in _requirement_source_files(project)}

            self.assertIn("module_plan.md", names)
            self.assertIn("path_partition.md", names)

    def test_docparse_requires_extract_output_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            legacy = project / "work/docparse" / "parsed" / "mineru"
            legacy.mkdir(parents=True)
            (legacy / "old.md").write_text("legacy\n", encoding="utf-8")
            extract = project / "work/docparse" / "parsed" / "mineru_extract"
            extract.mkdir(parents=True)
            (extract / "new.md").write_text("extract\n", encoding="utf-8")
            (extract / "provenance.yaml").write_text(
                (
                    "tool: mineru-open-api\ncommand: extract\n"
                    "channel: mineru-open-api high_precision_api\napi_mode: high_precision\n"
                    "api_endpoints:\n  - /api/v4/extract/task\n"
                ),
                encoding="utf-8",
            )

            check = _check_docparse_extract_policy(project)

            self.assertEqual(check.status, "FAIL")
            self.assertIn("work/docparse/parsed/" + "mineru/old.md", check.detail)

    def test_docparse_rejects_local_text_parser_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            extract = project / "work/docparse" / "parsed" / "mineru_extract"
            extract.mkdir(parents=True)
            (extract / "new.md").write_text("extract\n", encoding="utf-8")
            (extract / "provenance.yaml").write_text(
                (
                    "tool: mineru-open-api\ncommand: extract\n"
                    "channel: mineru-open-api high_precision_api\napi_mode: high_precision\n"
                    "api_endpoints:\n  - /api/v4/extract/task\n"
                ),
                encoding="utf-8",
            )
            local_text = project / "work/docparse" / "parsed" / "local_text"
            local_text.mkdir(parents=True)
            (local_text / "datasheet.txt").write_text("wrong parser text\n", encoding="utf-8")

            check = _check_docparse_extract_policy(project)

            self.assertEqual(check.status, "FAIL")
            self.assertIn("outside work/docparse/parsed/mineru_extract", check.detail)

    def test_docparse_requires_mineru_open_api_extract_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            extract = project / "work/docparse" / "parsed" / "mineru_extract"
            extract.mkdir(parents=True)
            (extract / "datasheet.md").write_text("parsed content\n", encoding="utf-8")
            (extract / "provenance.yaml").write_text(
                "tool: wrong-parser\ncommand: extract\nchannel: local_text\n",
                encoding="utf-8",
            )

            check = _check_docparse_extract_policy(project)

            self.assertEqual(check.status, "FAIL")
            self.assertIn("mineru-open-api", check.detail)

    def test_docparse_rejects_extract_without_high_precision_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            extract = project / "work/docparse" / "parsed" / "mineru_extract"
            extract.mkdir(parents=True)
            (extract / "datasheet.md").write_text("parsed content\n", encoding="utf-8")
            (extract / "provenance.yaml").write_text(
                "tool: mineru-open-api\ncommand: extract\nchannel: mineru-open-api extract\n",
                encoding="utf-8",
            )

            check = _check_docparse_extract_policy(project)

            self.assertEqual(check.status, "FAIL")
            self.assertIn("high_precision_api", check.detail)

    def test_docparse_accepts_mineru_open_api_extract_with_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            extract = project / "work/docparse" / "parsed" / "mineru_extract"
            extract.mkdir(parents=True)
            (extract / "datasheet.md").write_text("parsed content\n", encoding="utf-8")
            (extract / "provenance.yaml").write_text(
                (
                    "tool: mineru-open-api\ncommand: extract\n"
                    "channel: mineru-open-api high_precision_api\napi_mode: high_precision\n"
                    "api_endpoints:\n  - /api/v4/file-urls/batch\n  - /api/v4/extract/task\n"
                ),
                encoding="utf-8",
            )

            check = _check_docparse_extract_policy(project)

            self.assertEqual(check.status, "PASS")

    def test_docparse_accepts_chat_only_requirement_without_mineru_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            chat_source = project / "input" / "spec" / "chat_request.md"
            chat_source.parent.mkdir(parents=True, exist_ok=True)
            chat_source.write_text(
                "# Request\n\n- source_type: chat_request\n\n## Normalized Intent\n\n- Build a UART LED demo.\n",
                encoding="utf-8",
            )
            analysis = project / "work" / "docparse" / "structured_spec" / "document_analysis.yaml"
            analysis.parent.mkdir(parents=True, exist_ok=True)
            analysis.write_text(
                "\n".join(
                    [
                        "schema_version: 1",
                        "status: READY",
                        "source_documents:",
                        "  - source_ref: input/spec/chat_request.md",
                        "    parser_output: manual_chat_capture",
                        "    document_type: user_requirement",
                        "analysis_units:",
                        "  - unit_id: AU-CHAT",
                        "    source_ref: input/spec/chat_request.md",
                        "    evidence_refs:",
                        "      - input/spec/chat_request.md",
                        "evidence_map:",
                        "  - requirement_id: REQ-CHAT-001",
                        "    evidence_refs:",
                        "      - input/spec/chat_request.md",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            extract = project / "work" / "docparse" / "parsed" / "mineru_extract"
            extract.mkdir(parents=True, exist_ok=True)
            (extract / "provenance.yaml").write_text("placeholder: true\n", encoding="utf-8")

            check = _check_docparse_extract_policy(project)

            self.assertEqual(check.status, "PASS")
            self.assertIn("chat requirement source", check.detail)

    def test_docparse_rejects_chat_only_requirement_without_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            chat_source = project / "input" / "spec" / "chat_request.md"
            chat_source.parent.mkdir(parents=True, exist_ok=True)
            chat_source.write_text("# Request\n\nNo source marker.\n", encoding="utf-8")
            analysis = project / "work" / "docparse" / "structured_spec" / "document_analysis.yaml"
            analysis.parent.mkdir(parents=True, exist_ok=True)
            analysis.write_text(
                "\n".join(
                    [
                        "schema_version: 1",
                        "status: READY",
                        "source_documents:",
                        "  - source_ref: input/spec/chat_request.md",
                        "    parser_output: manual_chat_capture",
                        "analysis_units:",
                        "  - unit_id: AU-CHAT",
                        "    source_ref: input/spec/chat_request.md",
                        "    evidence_refs:",
                        "      - input/spec/chat_request.md",
                        "evidence_map:",
                        "  - requirement_id: REQ-CHAT-001",
                        "    evidence_refs:",
                        "      - input/spec/chat_request.md",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            extract = project / "work" / "docparse" / "parsed" / "mineru_extract"
            extract.mkdir(parents=True, exist_ok=True)
            (extract / "provenance.yaml").write_text("placeholder: true\n", encoding="utf-8")

            check = _check_docparse_extract_policy(project)

            self.assertEqual(check.status, "FAIL")
            self.assertIn("source_type: chat_request", check.detail)

    def test_docparse_chat_only_gate_paths_ignore_placeholder_mineru_extract(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            chat_source = project / "input" / "spec" / "chat_request.md"
            chat_source.parent.mkdir(parents=True, exist_ok=True)
            chat_source.write_text(
                "# Request\n\n- source_type: chat_request\n\n## Normalized Intent\n\n- Build a UART LED demo.\n",
                encoding="utf-8",
            )
            analysis = project / "work" / "docparse" / "structured_spec" / "document_analysis.yaml"
            analysis.parent.mkdir(parents=True, exist_ok=True)
            analysis.write_text(
                "\n".join(
                    [
                        "schema_version: 1",
                        "status: READY",
                        "source_documents:",
                        "  - source_ref: input/spec/chat_request.md",
                        "    parser_output: manual_chat_capture",
                        "analysis_units:",
                        "  - unit_id: AU-CHAT",
                        "    source_ref: input/spec/chat_request.md",
                        "    evidence_refs:",
                        "      - input/spec/chat_request.md",
                        "evidence_map:",
                        "  - requirement_id: REQ-CHAT-001",
                        "    evidence_refs:",
                        "      - input/spec/chat_request.md",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            extract = project / "work" / "docparse" / "parsed" / "mineru_extract"
            extract.mkdir(parents=True, exist_ok=True)
            (extract / "provenance.yaml").write_text("placeholder: true\n", encoding="utf-8")
            generated_input = project / "input" / "spec" / "srs.yaml"
            generated_input.write_text("schema_version: 1\nstatus: READY\n", encoding="utf-8")

            source_paths, evidence_paths = _gate_paths(project, "work/docparse")

            self.assertIn(chat_source, source_paths)
            self.assertNotIn(generated_input, source_paths)
            self.assertFalse(any("mineru_extract" in str(path).replace("\\", "/") for path in evidence_paths))

    def test_docparse_rejects_operation_record_as_parsed_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            extract = project / "work/docparse" / "parsed" / "mineru_extract"
            extract.mkdir(parents=True)
            (extract / "datasheet.md").write_text("parsed content\n", encoding="utf-8")
            (extract / "parse_operation_record.md").write_text("manual command notes\n", encoding="utf-8")
            (extract / "provenance.yaml").write_text(
                (
                    "tool: mineru-open-api\ncommand: extract\n"
                    "channel: mineru-open-api high_precision_api\napi_mode: high_precision\n"
                    "api_endpoints:\n  - /api/v4/extract/task\n"
                ),
                encoding="utf-8",
            )

            check = _check_docparse_extract_policy(project)

            self.assertEqual(check.status, "FAIL")
            self.assertIn("operation records are not parser output", check.detail)

    def test_docparse_rejects_process_violation_record_as_parsed_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            extract = project / "work/docparse" / "parsed" / "mineru_extract"
            extract.mkdir(parents=True)
            (extract / "datasheet.md").write_text("parsed content\n", encoding="utf-8")
            (extract / "process_violation_record.md").write_text("manual notes\n", encoding="utf-8")
            (extract / "provenance.yaml").write_text(
                (
                    "tool: mineru-open-api\ncommand: extract\n"
                    "channel: mineru-open-api high_precision_api\napi_mode: high_precision\n"
                    "api_endpoints:\n  - /api/v4/extract/task\n"
                ),
                encoding="utf-8",
            )

            check = _check_docparse_extract_policy(project)

            self.assertEqual(check.status, "FAIL")
            self.assertIn("operation records are not parser output", check.detail)

    def test_docparse_rejects_provenance_pointing_operation_record_into_extract_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            extract = project / "work/docparse" / "parsed" / "mineru_extract"
            extract.mkdir(parents=True)
            (extract / "datasheet.md").write_text("parsed content\n", encoding="utf-8")
            (extract / "provenance.yaml").write_text(
                (
                    "tool: mineru-open-api\ncommand: extract\n"
                    "channel: mineru-open-api high_precision_api\napi_mode: high_precision\n"
                    "api_endpoints:\n  - /api/v4/extract/task\n"
                    "operation_record: work/docparse/parsed/mineru_extract/notes.md\n"
                ),
                encoding="utf-8",
            )

            check = _check_docparse_extract_policy(project)

            self.assertEqual(check.status, "FAIL")
            self.assertIn("must not link", check.detail)

    def test_docparse_rejects_provenance_linking_manual_record_outside_extract_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            extract = project / "work/docparse" / "parsed" / "mineru_extract"
            extract.mkdir(parents=True)
            (extract / "datasheet.md").write_text("parsed content\n", encoding="utf-8")
            (extract / "provenance.yaml").write_text(
                (
                    "tool: mineru-open-api\ncommand: extract\n"
                    "channel: mineru-open-api high_precision_api\napi_mode: high_precision\n"
                    "api_endpoints:\n  - /api/v4/extract/task\n"
                    "process_violation_record: work/docparse/review/process_violation_record.md\n"
                ),
                encoding="utf-8",
            )

            check = _check_docparse_extract_policy(project)

            self.assertEqual(check.status, "FAIL")
            self.assertIn("manual review records", check.detail)

    def test_gate_rejects_vivado_logs_in_project_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            (project / "vivado.jou").write_text("journal\n", encoding="utf-8")
            (project / "vivado_1234.backup.log").write_text("log\n", encoding="utf-8")

            check = _check_project_root_tool_logs(project)

            self.assertEqual(check.status, "FAIL")
            self.assertIn("project root", check.detail)
            self.assertIn("output/fpga/vivado/logs", check.detail)

    def test_gate_requires_approved_change_request_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            req_dir = project / "work/change" / "requests"
            req_dir.mkdir(parents=True, exist_ok=True)
            change_id = "CR-20260522000000-update-spec"
            (req_dir / f"{change_id}.md").write_text(
                "\n".join(
                    [
                        f"# Change Request {change_id}",
                        f"- id: {change_id}",
                        "- status: approved",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            check = _check_change_control(project, None)[0]

            self.assertEqual(check.status, "FAIL")
            self.assertIn("--change-id", check.detail)

    def test_bound_change_request_requires_impact_and_approval_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            req_dir = project / "work/change" / "requests"
            req_dir.mkdir(parents=True, exist_ok=True)
            change_id = "CR-20260522000000-update-spec"
            (req_dir / f"{change_id}.md").write_text(
                "\n".join(
                    [
                        f"# Change Request {change_id}",
                        f"- id: {change_id}",
                        "- status: approved",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            check = _check_change_control(project, change_id)[0]

            self.assertEqual(check.status, "FAIL")
            self.assertIn("impact_analysis", check.detail)
            self.assertIn("approvals", check.detail)

    def test_bound_complete_change_request_passes_change_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            change_id = "CR-20260522000000-update-spec"
            for rel in ["requests", "impact_analysis", "approvals"]:
                (project / "work/change" / rel).mkdir(parents=True, exist_ok=True)
            (project / "work/change" / "requests" / f"{change_id}.md").write_text(
                "\n".join([f"# Change Request {change_id}", f"- id: {change_id}", "- status: approved", ""]),
                encoding="utf-8",
            )
            (project / "work/change" / "impact_analysis" / f"{change_id}.md").write_text(
                "\n".join(
                    [
                        f"# Impact Analysis {change_id}",
                        "",
                        "## Requirements",
                        "",
                        "- REQ-UNIT-001",
                        "",
                        "## Artifacts",
                        "",
                        "- output/rtl/demo_top.v",
                        "",
                        "## Downstream Nodes",
                        "",
                        "- work/loop1_rtl_tb",
                        "",
                        "## Required Verification",
                        "",
                        "- rtl-skill-audit --project prj/demo",
                        "- review-check --project prj/demo --level develop",
                        "- run-gate --node loop1 --change-id CR-20260522000000-update-spec",
                        "",
                        "## Docset Decision",
                        "",
                        "- required: yes",
                        "- documents: application_guide, microarchitecture_specification, verification_plan",
                        "",
                        "## Rollback Plan",
                        "",
                        "restore last rollback manifest",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (project / "work/change" / "approvals" / f"{change_id}.md").write_text(
                "\n".join(
                    [
                        f"# Approval {change_id}",
                        "",
                        "- status: approved",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            check = _check_change_control(project, change_id)[0]

            self.assertEqual(check.status, "PASS")

    def test_change_impact_auto_records_downstream_and_docset_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            request = _write_change_request(project, "open", timestamp=1_800_000_000.0)
            change_id = request.stem

            result = record_impact(
                project,
                change_id=change_id,
                requirements=["REQ-UNIT-001"],
                artifacts=["output/rtl/demo_top.v", "output/tb/demo_tb.v"],
                verification=[],
                rollback="restore last rollback manifest",
                risk="medium",
            )

            text = result.path.read_text(encoding="utf-8")
            self.assertIn("## Downstream Nodes", text)
            self.assertIn("work/loop1_rtl_tb", text)
            self.assertIn("## Docset Decision", text)
            self.assertIn("- required: yes", text)
            self.assertIn("documents: microarchitecture_specification, verification_plan, delivery_package", text)
            self.assertIn("rtl-skill-audit --project <project>", text)
            self.assertIn("review-check --project <project> --level develop", text)
            self.assertEqual(validate_change_bundle(project, change_id, require_approval=False), [])

    def test_rtl_change_impact_requires_skill_audit_and_review_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            change_id = "CR-20260522000000-update-rtl"
            (project / "work/change" / "impact_analysis").mkdir(parents=True, exist_ok=True)
            (project / "work/change" / "impact_analysis" / f"{change_id}.md").write_text(
                "\n".join(
                    [
                        f"# Impact Analysis {change_id}",
                        "",
                        "## Requirements",
                        "",
                        "- REQ-UNIT-001",
                        "",
                        "## Artifacts",
                        "",
                        "- output/rtl/demo_top.v",
                        "",
                        "## Downstream Nodes",
                        "",
                        "- work/loop1_rtl_tb",
                        "",
                        "## Required Verification",
                        "",
                        "- run-gate --node loop1 --change-id CR-20260522000000-update-rtl",
                        "",
                        "## Docset Decision",
                        "",
                        "- required: yes",
                        "- documents: microarchitecture_specification, verification_plan, delivery_package",
                        "",
                        "## Rollback Plan",
                        "",
                        "restore last rollback manifest",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            errors = validate_change_bundle(project, change_id, require_approval=False)

            self.assertTrue(any("rtl-skill-audit" in error for error in errors))
            self.assertTrue(any("review-check" in error for error in errors))

    def test_change_approval_rejects_incomplete_impact_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            change_id = "CR-20260522000000-update-spec"
            (project / "work/change" / "requests").mkdir(parents=True, exist_ok=True)
            (project / "work/change" / "impact_analysis").mkdir(parents=True, exist_ok=True)
            (project / "work/change" / "requests" / f"{change_id}.md").write_text(
                "\n".join([f"# Change Request {change_id}", f"- id: {change_id}", "- status: impact_ready", ""]),
                encoding="utf-8",
            )
            (project / "work/change" / "impact_analysis" / f"{change_id}.md").write_text(
                f"# Impact {change_id}\n\n## Artifacts\n\n- output/rtl/demo_top.v\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                approve_change(project, change_id=change_id, approver="reviewer", decision="approved", notes="reviewed")

    def test_assess_change_scope_maps_loop3_to_docset_and_gate(self):
        assessment = assess_change_scope(
            requirements=["REQ-FPGA-001"],
            artifacts=["work/loop3_fpga_proto/board_tests/prototype_plan.yaml"],
            verification=[],
        )

        self.assertTrue(assessment.design_doc_required)
        self.assertIn("verification_plan", assessment.design_doc_sections)
        self.assertIn("delivery_package", assessment.design_doc_sections)
        self.assertIn("work/loop3_fpga_proto", assessment.downstream_nodes)
        self.assertTrue(any("prototype-preflight" in item for item in assessment.verification))

    def test_docparse_rejects_ad_hoc_scope_and_analysis_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            req = project / "input" / "spec"
            req.mkdir(parents=True, exist_ok=True)
            (req / "demo_scope.md").write_text("manual scope analysis\n", encoding="utf-8")
            arch = project / "work/docparse" / "architecture"
            arch.mkdir(parents=True, exist_ok=True)
            (arch / "demo_implementation_analysis.md").write_text("manual analysis\n", encoding="utf-8")
            req_decompose = project / "work/docparse" / "req_decompose"
            req_decompose.mkdir(parents=True, exist_ok=True)
            (req_decompose / "design_blueprint.md").write_text("manual design file\n", encoding="utf-8")

            check = _check_no_ad_hoc_analysis_artifacts(project)

            self.assertEqual(check.status, "FAIL")
            self.assertIn("demo_scope.md", check.detail)
            self.assertIn("demo_implementation_analysis.md", check.detail)
            self.assertIn("design_blueprint.md", check.detail)

    def test_docparse_allows_review_operation_and_violation_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            review = project / "work/docparse" / "review"
            review.mkdir(parents=True, exist_ok=True)
            (review / "docparse_operation_log.md").write_text("review-owned operation analysis\n", encoding="utf-8")
            (review / "process_violation_record.md").write_text("review-owned process finding\n", encoding="utf-8")
            (review / "violation_record.md").write_text("review-owned issue finding\n", encoding="utf-8")

            check = _check_no_ad_hoc_analysis_artifacts(project)

            self.assertEqual(check.status, "PASS")

    def test_formal_artifacts_reject_forbidden_workflow_vocabulary(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            verification = project / "work/docparse" / "verification"
            verification.mkdir(parents=True, exist_ok=True)
            forbidden_word = "smo" + "ke"
            (verification / "verification_plan.yaml").write_text(
                f"baseline_entry_checks:\n  - SPI {forbidden_word} read\n",
                encoding="utf-8",
            )

            check = _check_forbidden_formal_text(project)

            self.assertEqual(check.status, "FAIL")
            self.assertIn("work/docparse/verification/verification_plan.yaml", check.detail)

    def test_formal_artifacts_reject_forbidden_chinese_workflow_terms(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            review = project / "work/docparse" / "review"
            review.mkdir(parents=True, exist_ok=True)
            (review / "multi_agent_review.md").write_text(
                "forbidden label: " + "\u70df\u6d4b" + "\n",
                encoding="utf-8",
            )

            check = _check_forbidden_formal_text(project)

            self.assertEqual(check.status, "FAIL")
            self.assertIn("work/docparse/review/multi_agent_review.md", check.detail)

    def test_memory_check_warns_on_forbidden_chinese_workflow_terms(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            memory = project / "work" / "memory"
            global_memory = memory / "00_global"
            global_memory.mkdir(parents=True)
            (memory / "index.yaml").write_text(
                "schema_version: 1\nproject: demo\niterations: {}\n",
                encoding="utf-8",
            )
            (global_memory / "CURRENT_STATE.md").write_text(
                "stale term: " + "\u5192\u70df" + "\n" + "".join(["S", "M", "O", "K", "E"]) + "\n",
                encoding="utf-8",
            )

            result = check_memory(project)

            self.assertTrue(any("banned/stale memory term" in item for item in result.warnings))


class PlatformTemplateContractTests(unittest.TestCase):
    def test_platform_text_avoids_ambiguous_quick_check_label(self):
        root = Path(__file__).resolve().parents[3]
        forbidden = "smo" + "ke"
        scanned_suffixes = {
            ".do",
            ".json",
            ".md",
            ".py",
            ".sv",
            ".svh",
            ".tcl",
            ".template",
            ".txt",
            ".yaml",
            ".yml",
        }
        roots = [root / "README.md", root / "env"]
        failures: list[str] = []
        for scan_root in roots:
            paths = [scan_root] if scan_root.is_file() else scan_root.rglob("*")
            for path in paths:
                if not path.is_file() or path.suffix.lower() not in scanned_suffixes:
                    continue
                if any(part in {"__pycache__", ".pytest_cache"} for part in path.parts):
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore").lower()
                if forbidden in text:
                    failures.append(str(path.relative_to(root)).replace("\\", "/"))
        self.assertEqual([], failures)

    def test_project_creation_engine_blocks_direct_cli_entry(self):
        old_value = os.environ.get(PROJECT_CREATE_ENTRYPOINT_ENV)
        os.environ.pop(PROJECT_CREATE_ENTRYPOINT_ENV, None)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(PermissionError):
                    create_project(Path(tmp), "demo")
        finally:
            if old_value is None:
                os.environ.pop(PROJECT_CREATE_ENTRYPOINT_ENV, None)
            else:
                os.environ[PROJECT_CREATE_ENTRYPOINT_ENV] = old_value

    def test_project_creation_engine_allows_official_script_entry(self):
        old_value = os.environ.get(PROJECT_CREATE_ENTRYPOINT_ENV)
        os.environ[PROJECT_CREATE_ENTRYPOINT_ENV] = "env/tool/scripts/New-HdlProject.ps1"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                workspace = Path(tmp)
                template = workspace / "env" / "rule" / "scaffold"
                template.mkdir(parents=True)
                (template / "project_scaffold.yaml").write_text(
                    "\n".join(
                        [
                            "schema_version: 1",
                            "project: change_me",
                            "created_by: __PROJECT_ENTRYPOINT__",
                            "creation_mode: script_only",
                            "template_source: env/rule/scaffold",
                            "created_at: GENERATED_AT",
                            "manual_project_directory_creation: forbidden",
                            "",
                        ]
                    ),
                    encoding="utf-8",
                )
                config_template = workspace / "env" / "rule" / "project_default" / "project_config.yaml"
                config_template.parent.mkdir(parents=True)
                config_template.write_text(
                    "\n".join(
                        [
                            "schema_version: 1",
                            "project:",
                            "  name: change_me",
                            "  owner: change_me",
                            "  description: change_me",
                            "",
                        ]
                    ),
                    encoding="utf-8",
                )

                created = create_project(workspace, "demo")

                self.assertEqual(created, workspace / "prj" / "demo")
                scaffold = (created / "project_scaffold.yaml").read_text(encoding="utf-8")
                self.assertIn("project: demo", scaffold)
                self.assertIn("created_by: env/tool/scripts/New-HdlProject.ps1", scaffold)
                config = (workspace / "prj" / "demo" / "work" / "config" / "project_config.yaml").read_text(encoding="utf-8")
                self.assertIn("name: demo", config)
        finally:
            if old_value is None:
                os.environ.pop(PROJECT_CREATE_ENTRYPOINT_ENV, None)
            else:
                os.environ[PROJECT_CREATE_ENTRYPOINT_ENV] = old_value

    def test_new_project_template_contains_platform_supervision_contract(self):
        root = Path(__file__).resolve().parents[3]
        template_config = (root / "env" / "rule" / "project_default" / "project_config.yaml").read_text(encoding="utf-8")
        orchestrator = (root / "env" / "rule" / "skills" / "hdl-workflow-orchestrator" / "SKILL.md").read_text(encoding="utf-8")
        rtl_skill = (root / "env" / "rule" / "skills" / "rtl-architecture-and-gen" / "SKILL.md").read_text(encoding="utf-8")
        uvm_skill = (root / "env" / "rule" / "skills" / "uvm-env-and-test-build" / "SKILL.md").read_text(encoding="utf-8")
        req_skill = (root / "env" / "rule" / "skills" / "requirements-frontdoor" / "SKILL.md").read_text(encoding="utf-8")
        mineru_skill = (root / "env" / "rule" / "skills" / "mineru-spec-normalizer" / "SKILL.md").read_text(encoding="utf-8")
        all_text = "\n".join([template_config, orchestrator, rtl_skill, uvm_skill, req_skill, mineru_skill])

        required_markers = [
            "work/docparse/parsed/mineru_extract",
            "parser_channel: mineru-open-api high_precision_api",
            "/api/v4/extract/task",
            "/api/v4/file-urls/batch",
            "parser_provenance: work/docparse/parsed/mineru_extract/provenance.yaml",
            "docparse_extract_policy",
            "docparse_no_ad_hoc_analysis_artifacts",
            "forbidden_formal_text",
            "agent_model:",
            "spec_agent_ready",
            "arch_agent_ready",
            "exec_agent_boundary_ready",
            "sim_agent_plan_ready",
            "review_agent_ready",
            "arbtr_flow_ready",
            "Spec Agent",
            "Arch Agent",
            "Exec Agent",
            "Sim Agent",
            "Review Agent",
            "Arbtr Agent",
            "review_no_open_defects",
            "arbtr_confirms_compliance",
            "output/tb/full_function_test_plan.md",
            "HDLFLOW|CHECK",
            "HDLFLOW|SUMMARY",
            "HDLFLOW_WAVE_BEGIN",
            "waveform_windows",
            "waveform_comparison",
            "Loop1 waveform secondary-check planning",
            "loop1-waveform-gate",
            "loop1_deterministic_gate",
            "output/sim/loop1/wave",
            "HDLFLOW_WAVE_GROUP",
            "waveform_query_report.md",
            "waveform_gate.json",
            "query_transcript.json",
            "Do not place all behavior in one file-level FSM.",
            "min_scenario_tests: 5",
            "min_stress_stimuli_per_transaction: 2",
            "After each `.v` file is generated or edited",
            "api_mode: high_precision",
            "ad hoc scope",
            "design blueprint",
            "Do not modify gate policy, gate reports, or temporary artifacts",
            "A chat confirmation is not enough authority",
            "Do not edit `env/tool/scripts/populate_*_frontdoor.py`",
            "review-check --project <project> --level develop",
            "generate-docs --project <project>` only after steps 7 and 8 pass",
            "review_findings_gate",
            "Approved change requests are not allowed to pass a",
            "work/loop3_fpga_proto",
            "prototype-preflight",
            "validate-prototype-plan",
            "generate-xdc",
            "generate-ps-pl-bd",
            "generate-vitis-boot",
            "loop3-refresh-reports",
            "document_analysis.yaml",
            "work/docparse/frontdoor/open_questions.md",
            "question_review",
            "unresolved_count: 0",
            "requirement_questions_reviewed",
            "source_document_analysis_ready",
            "If a user asks to change prototype verification intent",
            "directed TB model",
            "After a Loop2 gate baseline exists",
            "record the changed requirements",
            "enforce_all_extensions: true",
        ]

        for marker in required_markers:
            self.assertIn(marker, all_text)

    def test_platform_template_uses_strict_gate_evidence_contracts(self):
        root = Path(__file__).resolve().parents[3]
        template_config = (root / "env" / "rule" / "project_default" / "project_config.yaml").read_text(encoding="utf-8")
        coverage_waiver = json.loads((root / "env" / "rule" / "scaffold" / "work" / "gates" / "coverage_waiver.json").read_text(encoding="utf-8"))

        self.assertNotIn("regression_pass_any", template_config)
        self.assertNotIn("regression_structured_result", template_config)
        self.assertIn("report_json: output/reports/loop2/loop2_report.json", template_config)
        self.assertIn("structured_summary:", template_config)
        self.assertIn("required_opcodes_explicit: false", template_config)
        self.assertIn("required_opcodes: []", template_config)
        self.assertIn("serial_validation: output/reports/loop3/serial/latest_serial_validation_report.md", template_config)
        self.assertIn("vivado_implementation: output/reports/loop3/vivado_implementation_report.md", template_config)
        self.assertIn("vitis_boot: output/reports/loop3/vitis_boot_report.md", template_config)
        self.assertIn("board_validation: output/reports/loop3/board_validation_report.md", template_config)
        self.assertIn("loop3_exit: output/reports/loop3/loop3_exit_report.md", template_config)
        self.assertEqual(coverage_waiver["schema_version"], 2)

    def test_loop1_modelsim_template_runs_refresh_and_waveform_gate_from_env_core(self):
        root = Path(__file__).resolve().parents[3]
        rtl_functional = (root / "env" / "rule" / "scaffold" / "work" / "loop1_rtl_tb" / "sim" / "rtl_functional.do").read_text(encoding="utf-8")
        loop2_entry = (root / "env" / "rule" / "scaffold" / "work" / "loop2_uvm" / "sim" / "uvm_full_functional.do").read_text(encoding="utf-8")

        self.assertIn("loop1-refresh-reports", rtl_functional)
        self.assertIn("loop1-waveform-gate", rtl_functional)
        self.assertIn("Loop1 waveform advisory: FAIL", rtl_functional)
        self.assertIn("set wave_dir [file join $project_root output sim loop1 wave]", rtl_functional)
        self.assertIn("HDLFLOW_WAVE_GROUP", rtl_functional)
        self.assertIn("loop1_wave_extra_groups", rtl_functional)
        self.assertNotIn("set wave_dir [file join $runtime_dir wave]", rtl_functional)
        self.assertIn("env core", rtl_functional)
        self.assertIn("env core", loop2_entry)
        self.assertNotIn("workspace_root engine", rtl_functional)
        self.assertNotIn("workspace_root engine", loop2_entry)

    def test_project_validation_flags_legacy_coverage_waiver_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _populate_required_validation_paths(project)
            (project / "work" / "gates" / "coverage_waiver.json").write_text(
                json.dumps({"schema_version": 1, "project": "demo", "waivers": []}),
                encoding="utf-8",
            )

            result = validate_project(project)

            self.assertFalse(result.ok)
            self.assertTrue(any("schema_version must be 2" in message for message in result.messages))

    def test_platform_contract_removes_rejected_comment_density_rule(self):
        root = Path(__file__).resolve().parents[3]
        text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for base in ["env"]
            for path in (root / base).rglob("*")
            if path.is_file() and path.suffix.lower() in {".py", ".md", ".yaml", ".yml", ".template"}
        )

        forbidden_markers = [
            "Comment lines must exceed " + "30%",
            "rtl_" + "comment_density",
            "comment" + "-ratio",
            "Skill Audit " + "Notes",
        ]
        for marker in forbidden_markers:
            self.assertNotIn(marker, text)

    def test_project_template_has_no_legacy_parser_or_design_blueprint_scaffold(self):
        root = Path(__file__).resolve().parents[3]

        self.assertFalse((root / "env" / "rule" / "scaffold" / "work/docparse" / "parsed" / "mineru").exists())
        self.assertFalse((root / "env" / "rule" / "scaffold" / "work/docparse" / "req_decompose" / "design_blueprint.md").exists())

    def test_project_config_template_does_not_point_manual_records_to_parsed_evidence(self):
        root = Path(__file__).resolve().parents[3]
        text = (root / "env" / "rule" / "project_default" / "project_config.yaml").read_text(encoding="utf-8")

        self.assertNotIn("work/docparse/parsed/mineru_extract/parse_operation_record.md", text)
        self.assertNotIn("work/docparse/parsed/mineru_extract/operation_record.md", text)
        self.assertIn("review_record_root: work/docparse/review", text)

    def test_vivado_wrapper_pins_journal_and_log_under_controlled_directory(self):
        root = Path(__file__).resolve().parents[3]
        text = (root / "env" / "tool" / "scripts" / "Invoke-HdlVivado.ps1").read_text(encoding="utf-8")

        self.assertIn("Move-HdlVivadoProjectRootLogs", text)
        self.assertIn("[string]$RunDir", text)
        self.assertIn("HDLFLOW_VIVADO_RUN_DIR", text)
        self.assertIn("-log", text)
        self.assertIn("-journal", text)
        self.assertIn("output\\fpga\\vivado\\logs", text)
        self.assertIn("Push-Location $ResolvedRunDir", text)
        self.assertIn("vivado_relocated_root_log", text)
        self.assertIn("vivado_run_dir", text)

    def test_vivado_logs_directory_is_canonical_output_layout(self):
        root = Path(__file__).resolve().parents[3]
        artifacts = (root / "env" / "core" / "hdlflow" / "artifacts.py").read_text(encoding="utf-8")
        validate = (root / "env" / "core" / "hdlflow" / "validate.py").read_text(encoding="utf-8")
        template = (root / "env" / "rule" / "project_default" / "project_config.yaml").read_text(encoding="utf-8")

        self.assertIn('"logs"', artifacts)
        self.assertIn("output/fpga/vivado/logs", validate)
        self.assertIn("vivado_logs_dir: output/fpga/vivado/logs", template)

    def test_loop3_scaffold_scripts_use_new_platform_root(self):
        root = Path(__file__).resolve().parents[3]
        scripts = root / "env" / "rule" / "scaffold" / "work" / "loop3_fpga_proto" / "scripts"

        for script in [
            "Generate-BoardXdc.ps1",
            "Generate-PsPlBd.ps1",
            "Generate-VitisBoot.ps1",
            "Invoke-PrototypePreflight.ps1",
        ]:
            text = (scripts / script).read_text(encoding="utf-8")
            self.assertIn("Join-Path $PSScriptRoot '..\\..\\..'", text)
            self.assertIn("env\\core", text)
            self.assertNotIn("'engine'", text)

    def test_generated_boot_image_script_uses_vitis_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = generate_vitis_boot_files(project)
            script = (result.path / "Build-BootImage.ps1").read_text(encoding="utf-8")

            self.assertIn("Invoke-HdlVitis.ps1", script)
            self.assertIn("-Tool bootgen", script)
            self.assertIn("-Project $projectRoot.Path", script)
            self.assertIn("$bootgenArgs = @('-image', $Bif, '-arch', 'zynq', '-o', $Output, '-w')", script)
            self.assertIn("-ToolArgs $bootgenArgs", script)
            self.assertNotIn("& $Bootgen", script)

    def test_loop3_board_verify_is_platform_tool_not_opcode_sweep(self):
        root = Path(__file__).resolve().parents[3]
        script = (root / "env" / "tool" / "scripts" / "Invoke-HdlLoop3BoardVerify.ps1").read_text(encoding="utf-8")

        self.assertIn("workflow-stage-guard", script)
        self.assertIn("output\\reports\\loop3\\serial", script)
        self.assertIn("read data=0x[0-9A-Fa-f]{8}", script)
        self.assertNotIn("OPCODE[", script)
        self.assertNotIn("MULTIWORD_TX_PASS", script)

    def test_doctor_rejects_vivado_logs_in_workspace_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "vivado.jou").write_text("journal\n", encoding="utf-8")
            (workspace / "vivado_1234.backup.log").write_text("log\n", encoding="utf-8")

            issues = _workspace_root_tool_log_issues(workspace)

            self.assertEqual(issues, ["vivado.jou", "vivado_1234.backup.log"])

    def test_frontdoor_contract_requires_machine_readable_specs(self):
        paths = set(required_frontend_paths())

        for rel in [
            "work/docparse/structured_spec/document_analysis.yaml",
            "work/docparse/structured_spec/interface_spec.yaml",
            "work/docparse/structured_spec/interface_timing.yaml",
            "work/docparse/structured_spec/register_map.yaml",
            "work/docparse/structured_spec/test_intent.yaml",
            "work/docparse/structured_spec/timing_rules.yaml",
            "work/docparse/doc_projection.yaml",
            "work/docparse/trace_matrix/req_to_design_intent.yaml",
            "work/docparse/trace_matrix/req_to_test_intent.yaml",
        ]:
            self.assertIn(rel, paths)

    def test_module_plan_contract_requires_structural_fields_without_blocking_unknown_values(self):
        errors: list[str] = []

        _check_module_plan_contract(
            "work/docparse/architecture/module_plan.yaml",
            {
                "top_level": {
                    "name": "demo_top",
                    "forbidden_responsibilities": [
                        "protocol_decode",
                        "register_field_update",
                        "datapath_mutation",
                        "fifo_storage",
                        "monolithic_fsm",
                    ],
                },
                "modules": [
                    {
                        "name": "demo_leaf",
                        "id": "MOD-001",
                        "type": "leaf",
                        "source_file": "demo_leaf.v",
                        "responsibility": "Own a single datapath slice",
                        "owns": {},
                    }
                ],
            },
            errors,
        )

        self.assertFalse(any(".clock_domain must be non-empty" in item for item in errors))
        self.assertFalse(any(".reset_domain must be non-empty" in item for item in errors))
        self.assertTrue(any(".status must be present" in item for item in errors))
        self.assertTrue(any(".interfaces must be a mapping" in item for item in errors))

    def test_module_plan_contract_accepts_complete_lld_module(self):
        errors: list[str] = []

        _check_module_plan_contract(
            "work/docparse/architecture/module_plan.yaml",
            {
                "top_level": {
                    "name": "demo_top",
                    "forbidden_responsibilities": [
                        "protocol_decode",
                        "register_field_update",
                        "datapath_mutation",
                        "fifo_storage",
                        "arbitration_decision",
                        "monolithic_fsm",
                    ],
                },
                "modules": [
                    {
                        "name": "demo_top",
                        "id": "MOD-001",
                        "type": "top",
                        "status": "ready",
                        "confidence": "high",
                        "known_unknowns": [],
                        "source_file": "demo_top.v",
                        "responsibility": "Instantiate child modules and expose top ports",
                        "clock_domain": "clk",
                        "reset_domain": "rst_n",
                        "children": ["demo_leaf"],
                        "owns": {
                            "registers": [],
                            "register_fields": [],
                            "fsms": [],
                            "fifos": [],
                            "memories": [],
                            "counters": [],
                            "arbiters": [],
                            "error_flags": [],
                        },
                        "interfaces": {"inputs": ["clk"], "outputs": ["valid_o"], "internal": ["demo_bus"]},
                        "dataflow": {
                            "consumes": ["clk"],
                            "produces": ["valid_o"],
                            "transforms": ["hierarchy_only_wiring"],
                        },
                        "req_ids": ["REQ-DEMO-001"],
                        "design_feature_ids": [],
                        "verification_refs": {"tests": ["TC-DEMO-001"], "assertions": [], "coverage": []},
                        "forbidden_responsibilities": ["protocol_decode"],
                    },
                    {
                        "name": "demo_leaf",
                        "id": "MOD-002",
                        "type": "leaf",
                        "status": "ready",
                        "confidence": "high",
                        "known_unknowns": [],
                        "source_file": "demo_leaf.v",
                        "parent": "demo_top",
                        "responsibility": "Own valid_o register",
                        "clock_domain": "clk",
                        "reset_domain": "rst_n",
                        "owns": {
                            "registers": ["valid_o_reg"],
                            "register_fields": [],
                            "fsms": [],
                            "fifos": [],
                            "memories": [],
                            "counters": [],
                            "arbiters": [],
                            "error_flags": [],
                        },
                        "interfaces": {"inputs": ["clk", "rst_n"], "outputs": ["valid_o"], "internal": ["demo_bus"]},
                        "dataflow": {
                            "consumes": ["clk", "rst_n"],
                            "produces": ["valid_o"],
                            "transforms": ["registered_valid_flag"],
                        },
                        "req_ids": [],
                        "design_feature_ids": ["DF-DEMO-LEAF"],
                        "verification_refs": {"tests": [], "assertions": ["SVA-DEMO-LEAF"], "coverage": []},
                        "forbidden_responsibilities": ["unowned_register_update"],
                    },
                ],
            },
            errors,
        )

        self.assertEqual(errors, [])

    def test_plan_check_grades_docparse_unknowns_before_lld_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            _create_minimal_workspace_for_frontdoor(workspace)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            (project / "input" / "spec").mkdir(parents=True)
            (project / "input" / "spec" / "source.yaml").write_text("source: demo\n", encoding="utf-8")
            initialize_requirements_frontend(project, status="DRAFT")

            docparse = check_plan(project, maturity="docparse")
            lld = check_plan(project, maturity="lld")

            self.assertTrue(docparse.ok)
            self.assertTrue(any(issue.severity == "warning" for issue in docparse.issues))
            self.assertFalse(lld.ok)
            self.assertTrue(any("source_file is unresolved" in issue.message for issue in lld.issues))
            self.assertTrue((project / "output/reports/docparse/plan_report.md").is_file())

    def test_report_check_uses_json_manifest_and_rejects_markdown_evidence_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            log_path = project / "work/loop1_rtl_tb/current/log/modelsim.log"
            log_path.parent.mkdir(parents=True)
            log_path.write_text(
                "\n".join(
                    [
                        "HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=case0|txn_id=txn0|sent=aa|expected=55|actual=55|latency_cycles=2|result=PASS",
                        "HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|total_tests=1|passed_tests=1|failed_tests=0|total_checks=1|passed_checks=1|failed_checks=0|result=PASS",
                    ]
                ),
                encoding="utf-8",
            )
            generate_loop1_report(project)

            result = check_reports(project, stage="loop1")

            self.assertTrue(result.ok)
            report_md = project / "output/reports/loop1/loop1_report.md"
            report_md.write_text(report_md.read_text(encoding="utf-8") + "\n## Evidence\nmanual note\n", encoding="utf-8")
            result = check_reports(project, stage="loop1")
            self.assertFalse(result.ok)
            self.assertTrue(any("Evidence section" in issue.message for issue in result.issues))

    def test_frontdoor_init_creates_document_analysis_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            _create_minimal_workspace_for_frontdoor(workspace)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            (project / "input" / "spec").mkdir(parents=True)
            (project / "input" / "spec" / "source.yaml").write_text("source: demo\n", encoding="utf-8")

            result = initialize_requirements_frontend(project, status="DRAFT")

            self.assertTrue((project / "work/docparse/structured_spec/document_analysis.yaml").is_file())
            self.assertIn("work/docparse/structured_spec/document_analysis.yaml", result.created)

    def test_frontdoor_ready_requires_document_analysis_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            _create_minimal_workspace_for_frontdoor(workspace)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            (project / "input" / "spec").mkdir(parents=True)
            (project / "input" / "spec" / "source.yaml").write_text("source: demo\n", encoding="utf-8")
            initialize_requirements_frontend(project, status="READY")

            result = check_requirements_frontend(project, require_ready=True)

            self.assertFalse(result.ok)
            self.assertTrue(
                any("document_analysis.yaml source_documents must be non-empty" in error for error in result.errors)
            )
            self.assertTrue(
                any("document_analysis.yaml analysis_units must be non-empty" in error for error in result.errors)
            )
            self.assertTrue(
                any("document_analysis.yaml evidence_map must be non-empty" in error for error in result.errors)
            )
            self.assertTrue(
                any("document_analysis.yaml question_review.status must be" in error for error in result.errors)
            )
            self.assertTrue(
                any("work/docparse/frontdoor/open_questions.md review summary must contain '- question_review_status: REVIEWED'" in error for error in result.errors)
            )
            self.assertTrue(any("test_intent.yaml waveform_windows must be non-empty" in error for error in result.errors))
            self.assertTrue(any("verification_plan.yaml waveform_comparison must be non-empty" in error for error in result.errors))

    def test_frontdoor_ready_requires_high_precision_mineru_for_external_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            _create_minimal_workspace_for_frontdoor(workspace)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            (project / "input" / "spec").mkdir(parents=True)
            (project / "input" / "spec" / "datasheet.pdf").write_bytes(b"%PDF demo\n")
            initialize_requirements_frontend(project, status="READY")

            result = check_requirements_frontend(project, require_ready=True)

            self.assertFalse(result.ok)
            self.assertTrue(
                any(
                    "external document DocParse requires work/docparse/parsed/mineru_extract/provenance.yaml" in error
                    for error in result.errors
                )
            )

    def test_frontdoor_rejects_temporary_text_evidence_for_external_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            _create_minimal_workspace_for_frontdoor(workspace)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            (project / "input" / "spec").mkdir(parents=True)
            (project / "input" / "spec" / "datasheet.pdf").write_bytes(b"%PDF demo\n")
            parsed = project / "work" / "docparse" / "parsed"
            extract = parsed / "mineru_extract"
            extract.mkdir(parents=True)
            (extract / "datasheet.md").write_text("# parsed\n", encoding="utf-8")
            (extract / "provenance.yaml").write_text(
                "\n".join(
                    [
                        "tool: mineru-open-api",
                        "command: extract",
                        "channel: mineru-open-api high_precision_api",
                        "api_mode: high_precision",
                        "status: complete",
                        "api_endpoints:",
                        "  - /api/v4/extract/task",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            local_text = parsed / "local_text"
            local_text.mkdir()
            (local_text / "datasheet.txt").write_text("temporary text\n", encoding="utf-8")
            initialize_requirements_frontend(project, status="READY")

            result = check_requirements_frontend(project, require_ready=True)

            self.assertFalse(result.ok)
            self.assertTrue(
                any("external document DocParse cannot use temporary/local text evidence directories" in error for error in result.errors)
            )

    def test_frontdoor_ready_blocks_unresolved_requirement_questions(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            _create_minimal_workspace_for_frontdoor(workspace)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            analysis = project / "work/docparse/structured_spec/document_analysis.yaml"
            analysis.parent.mkdir(parents=True, exist_ok=True)
            analysis.write_text(
                "\n".join(
                    [
                        "schema_version: 1",
                        "project: demo",
                        "status: READY",
                        "source_refs:",
                        "  - input/spec/source.md",
                        "source_documents:",
                        "  - source_ref: input/spec/source.md",
                        "    parser_output: manual_chat_capture",
                        "    document_type: user_requirement",
                        "analysis_units:",
                        "  - unit_id: AU-1",
                        "    source_ref: input/spec/source.md",
                        "    section: root",
                        "    summary: UART demo",
                        "    extracted_requirements:",
                        "      - REQ-1",
                        "evidence_map:",
                        "  - requirement_id: REQ-1",
                        "    evidence_refs:",
                        "      - input/spec/source.md",
                        "open_questions:",
                        "  - id: Q-1",
                        "    question: Which UART baud rate is required?",
                        "    blocking_loop: loop1",
                        "    status: OPEN",
                        "question_review:",
                        "  status: REVIEWED",
                        "  reviewed_by: user",
                        "  review_evidence: work/docparse/frontdoor/open_questions.md",
                        "  unresolved_count: 1",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            questions = project / "work/docparse/frontdoor/open_questions.md"
            questions.parent.mkdir(parents=True, exist_ok=True)
            questions.write_text(
                "\n".join(
                    [
                        "# Open Requirement Questions",
                        "",
                        "- question_review_status: REVIEWED",
                        "- reviewed_by: user",
                        "- unresolved_count: 1",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = check_requirements_frontend(project, require_ready=True)

            self.assertFalse(result.ok)
            self.assertTrue(any("unresolved requirement questions must be sent to the user" in error for error in result.errors))

    def test_platform_template_has_file_backed_planning_files(self):
        root = Path(__file__).resolve().parents[3]

        for rel in [
            "work/memory/00_global/ACTIVE_PLAN.md",
            "work/memory/00_global/PLAN_FINDINGS.md",
            "work/memory/00_global/PLAN_ERRORS.md",
        ]:
            self.assertIn(rel, REQUIRED_PATHS)
            self.assertTrue((root / "env/rule/scaffold" / rel).is_file())

    def test_file_backed_plan_records_steps_findings_and_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = start_active_plan(
                project,
                title="Demo plan",
                objective="Keep execution state outside chat context",
                steps=["Inspect state", "Apply change", "Verify"],
            )
            self.assertTrue(result.path.is_file())

            update_active_plan_step(project, step_id="P001", status="in_progress", note="reading files")
            update_active_plan_step(project, step_id="P001", status="done", evidence="files reviewed")
            append_plan_note(project, kind="finding", note="Spec input lives under input/spec", source="project_config.yaml")
            append_plan_note(project, kind="error", note="First command failed", command="demo command", detail="missing env")

            active = (project / "work/memory/00_global/ACTIVE_PLAN.md").read_text(encoding="utf-8")
            findings = (project / "work/memory/00_global/PLAN_FINDINGS.md").read_text(encoding="utf-8")
            errors = (project / "work/memory/00_global/PLAN_ERRORS.md").read_text(encoding="utf-8")
            self.assertIn("- [x] P001: Inspect state", active)
            self.assertIn("Spec input lives under input/spec", findings)
            self.assertIn("First command failed", errors)

    def test_ralph_status_prioritizes_open_change_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _create_minimal_memory(project)
            start_active_plan(project, title="Demo", objective="Close the loop", steps=["Inspect", "Verify"], force=True)
            _write_change_request(project, "open", timestamp=1_800_000_000.0)

            result = ralph_status(project)

            self.assertTrue(result.report_path.is_file())
            self.assertIn("change-impact", result.next_action)
            self.assertIn("CR-20260523120000-demo", result.open_changes)

    def test_review_check_blocks_open_high_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_structured_review_findings(project, severity="high", status="open")

            result = check_review_findings(project, level="develop")

            self.assertFalse(result.ok)
            self.assertTrue(result.report_path.is_file())
            self.assertTrue(any("REV-SPEC-001" in blocker for blocker in result.blocking_findings))
            self.assertTrue(any("unclosed blocking review finding(s)" in error for error in result.errors))

    def test_review_check_treats_fixed_high_findings_as_unclosed(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_structured_review_findings(project, severity="high", status="fixed")

            result = check_review_findings(project, level="develop")

            self.assertFalse(result.ok)
            self.assertTrue(any("REV-SPEC-001" in blocker for blocker in result.blocking_findings))
            self.assertTrue(any("unclosed blocking review finding(s)" in error for error in result.errors))

    def test_review_check_allows_verified_high_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_structured_review_findings(project, severity="high", status="verified")

            result = check_review_findings(project, level="develop")

            self.assertTrue(result.ok, result.errors)
            self.assertEqual(result.blocking_findings, [])

    def test_review_check_requires_rtl_skill_review_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            rtl_dir = project / "output" / "rtl"
            rtl_dir.mkdir(parents=True, exist_ok=True)
            (rtl_dir / "demo_core.v").write_text(
                "// Module      : demo_core\n"
                "// Description : demo core\n"
                "// Scope:\n"
                "//   - owns demo logic\n"
                "// Spec Trace:\n"
                "//   - REQ-DEMO\n"
                "module demo_core; endmodule\n",
                encoding="utf-8",
            )
            _write_structured_review_findings(project, severity="info", status="closed")

            result = check_review_findings(project, level="develop")

            self.assertFalse(result.ok)
            self.assertTrue(any("formal artifact review" in error for error in result.errors))

    def test_review_check_requires_tb_and_uvm_skill_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            tb_dir = project / "output" / "tb"
            uvm_dir = project / "output" / "uvm" / "tests"
            tb_dir.mkdir(parents=True, exist_ok=True)
            uvm_dir.mkdir(parents=True, exist_ok=True)
            (tb_dir / "demo_tb.v").write_text("module demo_tb; endmodule\n", encoding="utf-8")
            (uvm_dir / "demo_test.sv").write_text("class demo_test; endclass\n", encoding="utf-8")
            _write_review_finding_with_evidence(project, "output/reports/review/review_check.md", "generic review evidence")

            result = check_review_findings(project, level="develop")

            self.assertFalse(result.ok)
            self.assertTrue(any("full_function_test_plan" in error for error in result.errors))
            self.assertTrue(any("uvm-env-and-test-build" in error for error in result.errors))

    def test_rtl_skill_audit_rejects_monolithic_register_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            rtl_dir = project / "output" / "rtl"
            rtl_dir.mkdir(parents=True, exist_ok=True)
            body = [
                "// Module      : pl_ctrl_regs",
                "// Description : AXI-Lite command/status mailbox and TX data register.",
                "// Scope:",
                "//   - Owns command, register, AXI, and TX control behavior.",
                "// Spec Trace:",
                "//   - REQ-DEMO",
                "module pl_ctrl_regs (",
                "    input wire clk,",
                "    input wire rst_n,",
                "    input wire awvalid,",
                "    input wire wvalid,",
                "    input wire arvalid,",
                "    input wire ps_tx_ready,",
                "    output reg bvalid,",
                "    output reg rvalid,",
                "    output reg [31:0] rdata,",
                "    output reg [7:0] ps_tx_data,",
                "    output reg ps_tx_valid",
                ");",
                "reg cmd_valid_q;",
                "reg status_reg;",
                "always @(posedge clk or negedge rst_n) begin",
                "    if (!rst_n) begin",
                "        cmd_valid_q <= 1'b0;",
                "        status_reg <= 1'b0;",
                "        bvalid <= 1'b0;",
                "        rvalid <= 1'b0;",
                "        rdata <= 32'd0;",
                "        ps_tx_data <= 8'd0;",
                "        ps_tx_valid <= 1'b0;",
                "    end",
                "    else begin",
            ]
            for index in range(18):
                body.extend(
                    [
                        f"        if (awvalid && wvalid && ps_tx_ready) begin",
                        f"            bvalid <= 1'b1;",
                        f"            cmd_valid_q <= arvalid;",
                        f"            status_reg <= awvalid;",
                        f"            rvalid <= arvalid;",
                        f"            rdata <= {{24'd0, ps_tx_data}};",
                        f"            ps_tx_data <= 8'd{index};",
                        f"            ps_tx_valid <= 1'b1;",
                        "        end",
                        "        else begin",
                        "            bvalid <= bvalid;",
                        "            cmd_valid_q <= cmd_valid_q;",
                        "            status_reg <= status_reg;",
                        "            rvalid <= rvalid;",
                        "            rdata <= rdata;",
                        "            ps_tx_data <= ps_tx_data;",
                        "            ps_tx_valid <= 1'b0;",
                        "        end",
                    ]
                )
            body.extend(["    end", "end", "endmodule", ""])
            (rtl_dir / "pl_ctrl_regs.v").write_text("\n".join(body), encoding="utf-8")

            result = run_rtl_skill_audit(project)

            self.assertFalse(result.ok)
            report = result.report_path.read_text(encoding="utf-8")
            self.assertIn("monolithic", report)
            self.assertIn("pl_ctrl_regs.v", report)

    def test_ralph_status_prioritizes_review_blocker(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _create_minimal_memory(project)
            start_active_plan(project, title="Demo", objective="Close the loop", steps=["Inspect"], force=True)
            _write_structured_review_findings(project, severity="critical", status="routed")

            result = ralph_status(project)

            self.assertFalse(result.ok)
            self.assertIn("review-check", result.next_action)
            self.assertTrue(any("REV-SPEC-001" in blocker for blocker in result.review_blockers))

    def test_ralph_step_blocks_next_open_step_and_records_plan_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _create_minimal_memory(project)
            start_active_plan(project, title="Demo", objective="Close the loop", steps=["Inspect", "Verify"], force=True)

            result = ralph_step(project, status="blocked", note="gate failed", evidence="output/reports/gates/demo.md")

            active = (project / "work/memory/00_global/ACTIVE_PLAN.md").read_text(encoding="utf-8")
            errors = (project / "work/memory/00_global/PLAN_ERRORS.md").read_text(encoding="utf-8")
            self.assertEqual(result.step_id, "P001")
            self.assertIn("- [!] P001: Inspect", active)
            self.assertIn("gate failed", errors)

    def test_ralph_check_requires_plan_closed_and_no_active_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _create_minimal_memory(project)
            start_active_plan(project, title="Demo", objective="Close the loop", steps=["Inspect"], force=True)
            update_active_plan_step(project, step_id="P001", status="done", evidence="checked")

            result = ralph_check(project)

            self.assertTrue(result.ok, result.errors)
            self.assertTrue(result.report_path.is_file())


class RequirementsFrontdoorGuardTests(unittest.TestCase):
    def test_blocks_forbidden_mineru_flash_channel(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "mineru-open-api flash-extract docs/input.pdf -o prj/demo/work/docparse/parsed/mineru_extract",
            )

            self.assertFalse(result.ok)
            self.assertIn("/api/v4/extract/task", result.reason)

    def test_blocks_forbidden_mineru_flash_mode_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "mineru-open-api extract docs/input.pdf --mode flash -o prj/demo/work/docparse/parsed/mineru_extract",
            )

            self.assertFalse(result.ok)
            self.assertIn("/api/v4/file-urls/batch", result.reason)

    def test_blocks_operation_record_write_under_parsed_extract(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path prj/demo/work/docparse/parsed/mineru_extract/parse_operation_record.md -Value notes",
            )

            self.assertFalse(result.ok)
            self.assertIn("parsed evidence", result.reason)

    def test_blocks_process_violation_record_write_under_parsed_extract(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path prj/demo/work/docparse/parsed/mineru_extract/process_violation_record.md -Value notes",
            )

            self.assertFalse(result.ok)
            self.assertIn("parsed evidence", result.reason)

    def test_blocks_manual_record_link_in_parser_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path prj/demo/work/docparse/parsed/mineru_extract/provenance.yaml -Value 'operation_record: work/docparse/review/process_violation_record.md'",
            )

            self.assertFalse(result.ok)
            self.assertIn("provenance", result.reason)

    def test_allows_review_docparse_operation_log_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path prj/demo/work/docparse/review/docparse_operation_log.md -Value notes",
            )

            self.assertTrue(result.ok)

    def test_allows_review_process_violation_record_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path prj/demo/work/docparse/review/process_violation_record.md -Value notes",
            )

            self.assertTrue(result.ok)

    def test_blocks_direct_design_report_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path prj/demo/output/docs/design/microarchitecture_spec.md -Value plan",
            )

            self.assertFalse(result.ok)
            self.assertIn("generate-docs", result.reason)

    def test_blocks_manual_rtl_skill_audit_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path prj/demo/output/reports/loop1/rtl_skill_audit.md -Value 'result: PASS'",
            )

            self.assertFalse(result.ok)
            self.assertIn("rtl-skill-audit", result.reason)

    def test_allows_initial_frontdoor_source_write_before_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path prj/demo/input/spec/source.md -Value spec",
            )

            self.assertTrue(result.ok)

    def test_blocks_frontdoor_source_write_after_baseline_without_change_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "work" / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "work_docparse_develop_20260523120000.json").write_text("{}", encoding="utf-8")

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path prj/demo/work/docparse/architecture/module_plan.yaml -Value plan",
            )

            self.assertFalse(result.ok)
            self.assertIn("change-open", result.reason)

    def test_allows_frontdoor_source_write_after_baseline_with_active_change_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "work" / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "work_docparse_develop_20260523120000.json").write_text("{}", encoding="utf-8")
            requests_dir = project / "work/change" / "requests"
            requests_dir.mkdir(parents=True)
            (requests_dir / "CR-20260523120000-demo.md").write_text(
                "\n".join(
                    [
                        "# Change Request CR-20260523120000-demo",
                        "",
                        "- id: CR-20260523120000-demo",
                        "- status: open",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path prj/demo/work/docparse/architecture/module_plan.yaml -Value plan",
            )

            self.assertTrue(result.ok)

    def test_blocks_prototype_source_write_after_baseline_without_approved_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "work" / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "work_docparse_develop_20260523120000.json").write_text("{}", encoding="utf-8")

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path prj/demo/work/loop3_fpga_proto/board_tests/prototype_plan.yaml -Value plan",
            )

            self.assertFalse(result.ok)
            self.assertIn("approved front-door change", result.reason)

    def test_blocks_prototype_source_write_after_approval_without_generated_docset(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "work" / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "work_docparse_develop_20260523120000.json").write_text("{}", encoding="utf-8")
            request = _write_complete_change_request(project, timestamp=1_800_000_000.0)
            _write_frontdoor_pass_report(project, timestamp=request.stat().st_mtime + 10)

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path prj/demo/work/loop3_fpga_proto/board_tests/prototype_plan.yaml -Value plan",
            )

            self.assertFalse(result.ok)
            self.assertIn("generate-docs", result.reason)

    def test_allows_prototype_source_write_after_approved_frontdoor_and_docset(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "work" / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "work_docparse_develop_20260523120000.json").write_text("{}", encoding="utf-8")
            request = _write_complete_change_request(project, timestamp=1_800_000_000.0)
            after_request = request.stat().st_mtime + 10
            _write_frontdoor_pass_report(project, timestamp=after_request)
            _write_docset_manifest(project, timestamp=after_request, documents=("verification_plan", "delivery_package"))

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path prj/demo/work/loop3_fpga_proto/board_tests/prototype_plan.yaml -Value plan",
            )

            self.assertTrue(result.ok)

    def test_blocks_manual_generated_fpga_output_write_even_after_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "work" / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "work_docparse_develop_20260523120000.json").write_text("{}", encoding="utf-8")
            request = _write_complete_change_request(project, timestamp=1_800_000_000.0)
            after_request = request.stat().st_mtime + 10
            _write_frontdoor_pass_report(project, timestamp=after_request)
            _write_docset_manifest(project, timestamp=after_request, documents=("verification_plan", "delivery_package"))

            result = evaluate_command_frontdoor_guard(
                project,
                "apply_patch *** Update File: prj/demo/output/fpga/vivado/scripts/generated_ps_pl_bd.tcl",
            )

            self.assertFalse(result.ok)
            self.assertIn("regenerated", result.reason)

    def test_blocks_loop1_tb_write_after_loop1_baseline_without_approved_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "work" / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "work_docparse_develop_20260523120000.json").write_text("{}", encoding="utf-8")
            (manifest_dir / "work_loop1_rtl_tb_develop_20260523130000.json").write_text("{}", encoding="utf-8")

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path prj/demo/output/tb/arinc_model_tb.v -Value model",
            )

            self.assertFalse(result.ok)
            self.assertIn("Loop1 RTL/TB requirement changes", result.reason)

    def test_blocks_loop2_uvm_write_after_loop2_baseline_without_approved_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "work" / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "work_docparse_develop_20260523120000.json").write_text("{}", encoding="utf-8")
            (manifest_dir / "work_loop2_uvm_develop_20260523130000.json").write_text("{}", encoding="utf-8")

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path prj/demo/output/uvm/seq_lib/arinc_protocol_sequence.svh -Value model",
            )

            self.assertFalse(result.ok)
            self.assertIn("Loop2 UVM requirement changes", result.reason)

    def test_blocks_loop1_tb_write_after_approval_without_generated_docset(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "work" / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "work_docparse_develop_20260523120000.json").write_text("{}", encoding="utf-8")
            (manifest_dir / "work_loop1_rtl_tb_develop_20260523130000.json").write_text("{}", encoding="utf-8")
            request = _write_complete_change_request(project, timestamp=1_800_000_000.0)
            _write_frontdoor_pass_report(project, timestamp=request.stat().st_mtime + 10)

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path prj/demo/output/tb/arinc_model_tb.v -Value model",
            )

            self.assertFalse(result.ok)
            self.assertIn("generate-docs", result.reason)

    def test_allows_loop1_tb_write_after_complete_approved_frontdoor_and_docset(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "work" / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "work_docparse_develop_20260523120000.json").write_text("{}", encoding="utf-8")
            (manifest_dir / "work_loop1_rtl_tb_develop_20260523130000.json").write_text("{}", encoding="utf-8")
            request = _write_complete_change_request(project, timestamp=1_800_000_000.0)
            after_request = request.stat().st_mtime + 10
            _write_frontdoor_pass_report(project, timestamp=after_request)
            _write_docset_manifest(
                project,
                timestamp=after_request,
                documents=("microarchitecture_specification", "verification_plan", "delivery_package"),
            )

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path prj/demo/output/tb/arinc_model_tb.v -Value model",
            )

            self.assertTrue(result.ok)

    def test_blocks_controlled_prototype_generator_before_loop2_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "work" / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "work_docparse_develop_20260523120000.json").write_text("{}", encoding="utf-8")

            result = evaluate_command_frontdoor_guard(
                project,
                "python -m hdlflow.cli generate-xdc --project prj/demo --output output/fpga/vivado/constraints/generated_board.xdc",
            )

            self.assertFalse(result.ok)
            self.assertIn("Loop1 must pass before Loop3", result.reason)

    def test_allows_controlled_prototype_generator_after_loop3_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_manifest_payload(project, "work/docparse", {})
            _write_manifest_payload(project, "work/loop1_rtl_tb", {})
            _write_manifest_payload(project, "work/loop2_uvm", {})
            _write_loop3_preflight_reports(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "python -m hdlflow.cli generate-xdc --project prj/demo --output output/fpga/vivado/constraints/generated_board.xdc",
            )

            self.assertTrue(result.ok)

    def test_blocks_gate_policy_write_from_frontdoor_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path Test_new/env/rule/global/gates/global_gate_rules.yaml -Value weakened",
            )

            self.assertFalse(result.ok)
            self.assertIn("AI agents cannot automatically modify", result.reason)
            self.assertIn("gate policy", result.reason)

    def test_allows_project_frontdoor_populate_script_write_before_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path env/tool/scripts/populate_demo_frontdoor.py -Value helper",
            )

            self.assertTrue(result.ok)

    def test_blocks_project_frontdoor_populate_script_write_after_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "work" / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "work_docparse_develop_20260523120000.json").write_text("{}", encoding="utf-8")

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path env/tool/scripts/populate_demo_frontdoor.py -Value helper",
            )

            self.assertFalse(result.ok)
            self.assertIn("front-door source artifacts first", result.reason)

    def test_blocks_reviewer_plan_report_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path prj/demo/output/reports/design/reviewer_plan_review.md -Value review",
            )

            self.assertFalse(result.ok)
            self.assertIn("sidecar", result.reason)

    def test_blocks_direct_internal_project_creation_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "python -m hdlflow.cli init-project rogue",
            )

            self.assertFalse(result.ok)
            self.assertIn("project creation must use", result.reason)

    def test_blocks_manual_project_directory_creation_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "New-Item -ItemType Directory prj/rogue",
            )

            self.assertFalse(result.ok)
            self.assertIn("project creation must use", result.reason)

    def test_allows_official_project_creation_script_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "powershell -File env/tool/scripts/New-HdlProject.ps1 -Name demo2",
            )

            self.assertTrue(result.ok)

    def test_blocks_direct_vivado_command_without_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = evaluate_command_frontdoor_guard(
                project,
                '& "E:/Vivado/Vivado/2024.2/bin/vivado.bat" -mode batch -source prj/demo/output/fpga/vivado/scripts/run.tcl',
            )

            self.assertFalse(result.ok)
            self.assertIn("Invoke-HdlVivado.ps1", result.reason)

    def test_blocks_direct_xsct_command_without_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = evaluate_command_frontdoor_guard(
                project,
                '& "E:/Vivado/Vitis/2024.2/bin/xsct.bat" prj/demo/output/fpga/vitis/boot/build_loop3_app_offline.tcl',
            )

            self.assertFalse(result.ok)
            self.assertIn("Invoke-HdlVitis.ps1", result.reason)

    def test_allows_vivado_wrapper_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_manifest_payload(project, "work/docparse", {})
            _write_manifest_payload(project, "work/loop1_rtl_tb", {})
            _write_manifest_payload(project, "work/loop2_uvm", {})
            _write_loop3_preflight_reports(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "powershell -File env/tool/scripts/Invoke-HdlVivado.ps1 -Project prj/demo -Source prj/demo/output/fpga/vivado/scripts/run.tcl",
            )

            self.assertTrue(result.ok)

    def test_allows_vitis_wrapper_command_after_loop3_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_manifest_payload(project, "work/docparse", {})
            _write_manifest_payload(project, "work/loop1_rtl_tb", {})
            _write_manifest_payload(project, "work/loop2_uvm", {})
            _write_loop3_preflight_reports(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "powershell -File env/tool/scripts/Invoke-HdlVitis.ps1 -Project prj/demo -Tool xsct -Source prj/demo/output/fpga/vitis/boot/build_loop3_app_offline.tcl",
            )

            self.assertTrue(result.ok)

    def test_blocks_formal_output_write_before_docparse(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "Set-Content -Path prj/demo/output/rtl/demo_top.v -Value module",
            )

            self.assertFalse(result.ok)
            self.assertIn("DocParse gate manifest", result.reason)

    def test_allows_read_only_formal_output_inspection(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = evaluate_command_frontdoor_guard(
                project,
                "Get-Content prj/demo/output/rtl/demo_top.v",
            )

            self.assertTrue(result.ok)

    def test_frontdoor_pass_report_alone_does_not_unlock_formal_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_frontdoor_pass_report(project, timestamp=1_800_000_000.0)

            result = require_frontdoor_ready(project, "generate-xdc")

            self.assertFalse(result.ok)
            self.assertIn("DocParse gate manifest", result.reason)

    def test_allows_formal_output_write_after_docparse_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "work" / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "work_docparse_develop_20260518000101.json").write_text("{}", encoding="utf-8")

            result = require_frontdoor_ready(project, "generate-xdc")

            self.assertTrue(result.ok)

    def test_loop2_stage_guard_requires_loop1_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_manifest_payload(project, "work/docparse", {})

            result = require_stage_ready(project, "loop2", "loop2-database-preflight")

            self.assertFalse(result.ok)
            self.assertIn("Loop1 must pass before Loop2", result.reason)

    def test_loop3_generation_guard_requires_preflight_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_manifest_payload(project, "work/docparse", {})
            _write_manifest_payload(project, "work/loop1_rtl_tb", {})
            _write_manifest_payload(project, "work/loop2_uvm", {})

            result = require_stage_ready(project, "loop3-preflight", "generate-ps-pl-bd")

            self.assertFalse(result.ok)
            self.assertIn("database preflight is missing", result.reason)

    def test_agent_role_blocks_cross_scope_write(self):
        old_value = os.environ.get("HDLFLOW_AGENT_ROLE")
        os.environ["HDLFLOW_AGENT_ROLE"] = "sim"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                project = Path(tmp) / "demo"
                _create_minimal_project(project)

                result = evaluate_command_frontdoor_guard(
                    project,
                    "Set-Content -Path prj/demo/output/rtl/demo_top.v -Value module",
                )

                self.assertFalse(result.ok)
                self.assertIn("agent role sim cannot write", result.reason)
        finally:
            if old_value is None:
                os.environ.pop("HDLFLOW_AGENT_ROLE", None)
            else:
                os.environ["HDLFLOW_AGENT_ROLE"] = old_value

    def test_review_agent_can_write_review_reports_only(self):
        old_value = os.environ.get("HDLFLOW_AGENT_ROLE")
        os.environ["HDLFLOW_AGENT_ROLE"] = "review"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                project = Path(tmp) / "demo"
                _create_minimal_project(project)

                result = evaluate_command_frontdoor_guard(
                    project,
                    "Set-Content -Path prj/demo/output/reports/review/defects.md -Value defect",
                )

                self.assertTrue(result.ok)
        finally:
            if old_value is None:
                os.environ.pop("HDLFLOW_AGENT_ROLE", None)
            else:
                os.environ["HDLFLOW_AGENT_ROLE"] = old_value


class GateManifestDriftTests(unittest.TestCase):
    def test_change_id_does_not_cover_unlisted_source_hash_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            source = project / "output" / "rtl" / "demo_top.v"
            source.parent.mkdir(parents=True)
            source.write_text("module demo_top; endmodule\n", encoding="utf-8")
            _write_source_manifest(project, "work/loop1_rtl_tb", source)
            source.write_text("module demo_top; wire changed; endmodule\n", encoding="utf-8")
            change_id = "CR-20260523120000-demo"
            _write_impact_artifacts(project, change_id, ["output/tb/demo_tb.v"])

            check = _check_manifest_drift(project, "work/loop1_rtl_tb", [source], change_id)[0]

            self.assertEqual(check.status, "FAIL")
            self.assertIn("not covered", check.detail)

    def test_change_id_covers_source_hash_drift_only_when_impact_lists_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            source = project / "output" / "rtl" / "demo_top.v"
            source.parent.mkdir(parents=True)
            source.write_text("module demo_top; endmodule\n", encoding="utf-8")
            _write_source_manifest(project, "work/loop1_rtl_tb", source)
            source.write_text("module demo_top; wire changed; endmodule\n", encoding="utf-8")
            change_id = "CR-20260523120000-demo"
            _write_impact_artifacts(project, change_id, ["output/rtl/demo_top.v"])

            check = _check_manifest_drift(project, "work/loop1_rtl_tb", [source], change_id)[0]

            self.assertEqual(check.status, "PASS")
            self.assertIn("covered", check.detail)

    def test_change_id_must_cover_skill_policy_hash_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            _write_project_required_skill_config(workspace, "demo", "rtl-architecture-and-gen")
            skill = workspace / "env" / "rule" / "skills" / "rtl-architecture-and-gen" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("old skill\n", encoding="utf-8")
            _write_manifest_payload(
                project,
                "work/loop1_rtl_tb",
                {
                    "skill_constraints": [
                        {
                            "skill": "rtl-architecture-and-gen",
                            "path": "env/rule/skills/rtl-architecture-and-gen/SKILL.md",
                            "sha256": hashlib.sha256(skill.read_bytes()).hexdigest(),
                        }
                    ]
                },
            )
            skill.write_text("new skill\n", encoding="utf-8")
            change_id = "CR-20260523120000-demo"
            _write_impact_artifacts(project, change_id, ["output/rtl/demo_top.v"])

            check = _check_skill_manifest_drift(project, "work/loop1_rtl_tb", change_id)[0]

            self.assertEqual(check.status, "FAIL")
            self.assertIn("not covered", check.detail)

            _write_impact_artifacts(project, change_id, ["env/rule/skills/rtl-architecture-and-gen/SKILL.md"])
            check = _check_skill_manifest_drift(project, "work/loop1_rtl_tb", change_id)[0]

            self.assertEqual(check.status, "PASS")

    def test_change_id_must_cover_protected_gate_hash_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            gate_file = workspace / "env" / "core" / "hdlflow" / "gates.py"
            gate_file.parent.mkdir(parents=True)
            gate_file.write_text("old gate\n", encoding="utf-8")
            _write_manifest_payload(
                project,
                "work/loop1_rtl_tb",
                {
                    "protected_gate_files": [
                        {
                            "path": "env/core/hdlflow/gates.py",
                            "sha256": hashlib.sha256(gate_file.read_bytes()).hexdigest(),
                        }
                    ]
                },
            )
            gate_file.write_text("new gate\n", encoding="utf-8")
            change_id = "CR-20260523120000-demo"
            _write_impact_artifacts(project, change_id, ["output/rtl/demo_top.v"])

            check = _check_protected_gate_manifest_drift(project, "work/loop1_rtl_tb", change_id)[0]

            self.assertEqual(check.status, "FAIL")
            self.assertIn("not covered", check.detail)

            _write_impact_artifacts(project, change_id, ["env/core/hdlflow/gates.py"])
            check = _check_protected_gate_manifest_drift(project, "work/loop1_rtl_tb", change_id)[0]

            self.assertEqual(check.status, "PASS")


class MemoryGateResultTests(unittest.TestCase):
    def test_active_gate_requires_exact_pass_or_structured_result(self):
        self.assertTrue(_is_active_gate("PASS"))
        self.assertTrue(_is_active_gate("- result: PASS"))
        self.assertFalse(_is_active_gate("NOT_PASS"))
        self.assertFalse(_is_active_gate("previous PASS but current FAIL"))

    def test_auto_record_sanitizes_node_slash_event_for_rollback_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "prj" / "demo"
            _create_minimal_project(project)
            _create_minimal_memory(project)
            report = project / "output" / "reports" / "gates" / "work_docparse_develop.md"
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text("# Gate\n\n- result: PASS\n", encoding="utf-8")

            result = auto_record_workflow_event(
                project,
                event="gate-work/docparse-develop",
                node="work/docparse",
                gate_level="develop",
                gate_result="PASS",
                memory_record=report,
                report=report,
                notes="docparse develop gate passed",
            )

            self.assertFalse([message for message in result.messages if message.startswith("memory error:")])
            manifests = list((project / "work" / "memory" / "recovery" / "rollback_manifests").glob("gate-work-docparse-develop-*.json"))
            self.assertEqual(len(manifests), 1)


class HdlPreToolHookTests(unittest.TestCase):
    def test_pre_tool_guard_blocks_apply_patch_payload_without_command_field(self):
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is required for hook validation")

        root = Path(__file__).resolve().parents[3]
        hook = root / "env" / "core" / "hooks" / "Invoke-HdlPreToolGuard.ps1"
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            event = {
                "tool_name": "apply_patch",
                "tool_input": "\n".join(
                    [
                        "*** Begin Patch",
                        "*** Add File: prj/demo/output/docs/design/microarchitecture_spec.md",
                        "+plan",
                        "*** End Patch",
                    ]
                ),
            }

            result = subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(hook),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-ProjectPath",
                    str(project),
                ],
                input=json.dumps(event),
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["decision"], "block")
            self.assertFalse(payload["continue"])
            self.assertIn("generate-docs", payload["reason"])

    def test_pre_tool_guard_blocks_frontdoor_source_patch_without_change_request(self):
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is required for hook validation")

        root = Path(__file__).resolve().parents[3]
        hook = root / "env" / "core" / "hooks" / "Invoke-HdlPreToolGuard.ps1"
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "work" / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "work_docparse_develop_20260523120000.json").write_text("{}", encoding="utf-8")
            event = {
                "tool_name": "apply_patch",
                "tool_input": "\n".join(
                    [
                        "*** Begin Patch",
                        "*** Add File: prj/demo/work/docparse/architecture/module_plan.yaml",
                        "+status: READY",
                        "*** End Patch",
                    ]
                ),
            }

            result = subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(hook),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-ProjectPath",
                    str(project),
                ],
                input=json.dumps(event),
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["decision"], "block")
            self.assertFalse(payload["continue"])
            self.assertIn("change-open", payload["reason"])

    def test_pre_tool_guard_blocks_project_frontdoor_populate_script_patch_after_baseline(self):
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is required for hook validation")

        root = Path(__file__).resolve().parents[3]
        hook = root / "env" / "core" / "hooks" / "Invoke-HdlPreToolGuard.ps1"
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "work" / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "work_docparse_develop_20260523120000.json").write_text("{}", encoding="utf-8")
            event = {
                "tool_name": "apply_patch",
                "tool_input": "\n".join(
                    [
                        "*** Begin Patch",
                        "*** Update File: env/tool/scripts/populate_demo_frontdoor.py",
                        "@@",
                        "+def apply_project_change():",
                        "+    pass",
                        "*** End Patch",
                    ]
                ),
            }

            result = subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(hook),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-ProjectPath",
                    str(project),
                ],
                input=json.dumps(event),
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["decision"], "block")
            self.assertFalse(payload["continue"])
            self.assertIn("front-door source artifacts first", payload["reason"])

    def test_pre_tool_guard_blocks_prototype_patch_without_approved_frontdoor_change(self):
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is required for hook validation")

        root = Path(__file__).resolve().parents[3]
        hook = root / "env" / "core" / "hooks" / "Invoke-HdlPreToolGuard.ps1"
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "work" / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "work_docparse_develop_20260523120000.json").write_text("{}", encoding="utf-8")
            event = {
                "tool_name": "apply_patch",
                "tool_input": "\n".join(
                    [
                        "*** Begin Patch",
                        "*** Add File: prj/demo/work/loop3_fpga_proto/board_tests/prototype_plan.yaml",
                        "+status: changed",
                        "*** End Patch",
                    ]
                ),
            }

            result = subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(hook),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-ProjectPath",
                    str(project),
                ],
                input=json.dumps(event),
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["decision"], "block")
            self.assertFalse(payload["continue"])
            self.assertIn("approved front-door change", payload["reason"])

    def test_pre_tool_guard_blocks_generated_fpga_output_patch(self):
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is required for hook validation")

        root = Path(__file__).resolve().parents[3]
        hook = root / "env" / "core" / "hooks" / "Invoke-HdlPreToolGuard.ps1"
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            event = {
                "tool_name": "apply_patch",
                "tool_input": "\n".join(
                    [
                        "*** Begin Patch",
                        "*** Add File: prj/demo/output/fpga/vivado/scripts/generated_ps_pl_bd.tcl",
                        "+set bd_name hacked",
                        "*** End Patch",
                    ]
                ),
            }

            result = subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(hook),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-ProjectPath",
                    str(project),
                ],
                input=json.dumps(event),
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["decision"], "block")
            self.assertFalse(payload["continue"])
            self.assertIn("regenerated", payload["reason"])

    def test_pre_tool_guard_blocks_loop1_tb_patch_without_approved_frontdoor_change(self):
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is required for hook validation")

        root = Path(__file__).resolve().parents[3]
        hook = root / "env" / "core" / "hooks" / "Invoke-HdlPreToolGuard.ps1"
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "work" / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "work_docparse_develop_20260523120000.json").write_text("{}", encoding="utf-8")
            (manifest_dir / "work_loop1_rtl_tb_develop_20260523130000.json").write_text("{}", encoding="utf-8")
            event = {
                "tool_name": "apply_patch",
                "tool_input": "\n".join(
                    [
                        "*** Begin Patch",
                        "*** Add File: prj/demo/output/tb/arinc_model_tb.v",
                        "+module arinc_model_tb; endmodule",
                        "*** End Patch",
                    ]
                ),
            }

            result = subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(hook),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-ProjectPath",
                    str(project),
                ],
                input=json.dumps(event),
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["decision"], "block")
            self.assertFalse(payload["continue"])
            self.assertIn("Loop1 RTL/TB requirement changes", payload["reason"])

    def test_pre_tool_guard_blocks_gate_policy_patch(self):
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is required for hook validation")

        root = Path(__file__).resolve().parents[3]
        hook = root / "env" / "core" / "hooks" / "Invoke-HdlPreToolGuard.ps1"
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            event = {
                "tool_name": "apply_patch",
                "tool_input": "\n".join(
                    [
                        "*** Begin Patch",
                        "*** Update File: env/rule/global/gates/global_gate_rules.yaml",
                        "@@",
                        "+bypass: true",
                        "*** End Patch",
                    ]
                ),
            }

            result = subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(hook),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-ProjectPath",
                    str(project),
                ],
                input=json.dumps(event),
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["decision"], "block")
            self.assertFalse(payload["continue"])
            self.assertIn("AI agents cannot automatically modify", payload["reason"])
            self.assertIn("gate policy", payload["reason"])

    def test_pre_tool_guard_blocks_direct_vivado_command(self):
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is required for hook validation")

        root = Path(__file__).resolve().parents[3]
        hook = root / "env" / "core" / "hooks" / "Invoke-HdlPreToolGuard.ps1"
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            event = {
                "command": '& "E:/Vivado/Vivado/2024.2/bin/vivado.bat" -mode batch -source prj/demo/output/fpga/vivado/scripts/run.tcl',
            }

            result = subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(hook),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-ProjectPath",
                    str(project),
                ],
                input=json.dumps(event),
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["decision"], "block")
            self.assertFalse(payload["continue"])
            self.assertIn("Invoke-HdlVivado.ps1", payload["reason"])

    def test_pre_tool_guard_blocks_direct_xsct_command(self):
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is required for hook validation")

        root = Path(__file__).resolve().parents[3]
        hook = root / "env" / "core" / "hooks" / "Invoke-HdlPreToolGuard.ps1"
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            event = {
                "command": '& "E:/Vivado/Vitis/2024.2/bin/xsct.bat" prj/demo/output/fpga/vitis/boot/build_loop3_app_offline.tcl',
            }

            result = subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(hook),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-ProjectPath",
                    str(project),
                ],
                input=json.dumps(event),
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["decision"], "block")
            self.assertFalse(payload["continue"])
            self.assertIn("Invoke-HdlVitis.ps1", payload["reason"])


class Loop3RiskGateTests(unittest.TestCase):
    def test_loop3_blocks_project_local_ad_hoc_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            script_dir = project / "work" / "loop3_fpga_proto" / "scripts"
            script_dir.mkdir(parents=True, exist_ok=True)
            (script_dir / "Invoke-Loop3SerialValidation.ps1").write_text("Write-Host bypass\n", encoding="utf-8")

            check = _check_no_project_local_loop3_scripts(project)

            self.assertEqual(check.status, "FAIL")
            self.assertIn("Invoke-Loop3SerialValidation.ps1", check.detail)

    def test_loop3_report_refresh_writes_formal_reports_from_latest_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_loop3_signoff_evidence(project, mode="ps_pl")

            result = refresh_loop3_reports(project)

            self.assertTrue(result.ok, result.statuses)
            self.assertEqual(set(result.statuses.values()), {"PASS"})
            for path in result.report_paths:
                self.assertTrue(path.exists(), path)
                self.assertIn("- result: PASS", path.read_text(encoding="utf-8"))

    def test_loop3_serial_stress_is_skipped_without_project_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            check = _loop3_configured_serial_stress_check(project, "RX[12:00:00.000]: read data=0x00000000\nLOOP3_RESULT PASS\n")

            self.assertEqual(check.status, "PASS")
            self.assertIn("no Loop3 serial stress marker policy", check.detail)

    def test_loop3_serial_stress_uses_configured_markers_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            config_dir = project / "work" / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "project_config.yaml").write_text(
                "\n".join(
                    [
                        "schema_version: 1",
                        "project:",
                        "  name: demo",
                        "nodes:",
                        "  work/loop3_fpga_proto:",
                        "    evidence:",
                        "      required_markers:",
                        "        serial_stress_all:",
                        "          - CUSTOM_STRESS_PASS",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            check = _loop3_configured_serial_stress_check(project, "CUSTOM_STRESS_PASS\n")

            self.assertEqual(check.status, "PASS")

    def test_serial_echo_requires_matching_payload_and_raw_rx_log(self):
        validation = "\n".join(
            [
                "# COM3 UART Loopback Validation",
                "- TX[2026-05-18 16:51:07.517]：HDLFLOW_UART_LOOP3",
                "- RX[2026-05-18 16:51:07.518]：HDLFLOW_UART_LOOP3",
                "- result: PASS",
            ]
        )
        raw = "\n".join(
            [
                "RX[2026-05-18 16:51:07.518]：HDLFLOW_UART_LOOP3",
                "LOOP3_RESULT PASS",
            ]
        )

        check = _loop3_serial_echo_check(validation, raw)

        self.assertEqual(check.status, "PASS")

    def test_serial_echo_blocks_marker_only_report(self):
        validation = "\n".join(
            [
                "- TX[2026-05-18 16:51:07.517]：EXPECTED",
                "- RX[2026-05-18 16:51:07.518]：OTHER",
                "- result: PASS",
            ]
        )
        raw = "\n".join(
            [
                "RX[2026-05-18 16:51:07.518]：OTHER",
                "LOOP3_RESULT PASS",
            ]
        )

        check = _loop3_serial_echo_check(validation, raw)

        self.assertEqual(check.status, "FAIL")

    def test_serial_echo_requires_raw_loop3_pass_marker(self):
        validation = "\n".join(
            [
                "- TX[2026-05-18 16:51:07.517]：HDLFLOW_UART_LOOP3",
                "- RX[2026-05-18 16:51:07.518]：HDLFLOW_UART_LOOP3",
                "- result: PASS",
            ]
        )
        raw = "RX[2026-05-18 16:51:07.518]：HDLFLOW_UART_LOOP3"

        check = _loop3_serial_echo_check(validation, raw)

        self.assertEqual(check.status, "FAIL")
        self.assertIn("LOOP3_RESULT PASS", check.detail)

    def test_serial_echo_rejects_raw_protocol_fail_marker(self):
        validation = "\n".join(
            [
                "- TX[2026-05-18 16:51:07.517]：HDLFLOW_UART_LOOP3",
                "- RX[2026-05-18 16:51:07.518]：HDLFLOW_UART_LOOP3",
                "- result: PASS",
            ]
        )
        raw = "\n".join(
            [
                "RX[2026-05-18 16:51:07.518]：HDLFLOW_UART_LOOP3",
                "DUT_PROTOCOL_MODEL_FAIL",
                "LOOP3_RESULT PASS",
            ]
        )

        check = _loop3_serial_echo_check(validation, raw)

        self.assertEqual(check.status, "FAIL")
        self.assertIn("DUT_PROTOCOL_MODEL_FAIL", check.detail)

    def test_serial_echo_rejects_stale_validation_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            validation_path = root / "latest_serial_validation_report.md"
            serial_path = root / "latest_serial_text.log"
            validation_path.write_text(
                "\n".join(
                    [
                        "- TX[2026-05-18 16:51:07.517]：HDLFLOW_UART_LOOP3",
                        "- RX[2026-05-18 16:51:07.518]：HDLFLOW_UART_LOOP3",
                        "- result: PASS",
                    ]
                ),
                encoding="utf-8",
            )
            serial_path.write_text(
                "\n".join(
                    [
                        "RX[2026-05-18 16:51:07.518]：HDLFLOW_UART_LOOP3",
                        "LOOP3_RESULT PASS",
                    ]
                ),
                encoding="utf-8",
            )
            os.utime(validation_path, (1000, 1000))
            os.utime(serial_path, (2000, 2000))

            check = _loop3_serial_echo_check(
                validation_path.read_text(encoding="utf-8"),
                serial_path.read_text(encoding="utf-8"),
                validation_path,
                serial_path,
            )

            self.assertEqual(check.status, "FAIL")
            self.assertIn("older", check.detail)

    def test_loop3_source_policy_can_enforce_non_hdl_extensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            config_dir = workspace / "prj" / "demo" / "work" / "config"
            config_dir.mkdir(parents=True)
            (config_dir / "project_config.yaml").write_text(
                "\n".join(
                    [
                        "schema_version: 1",
                        "project:",
                        "  name: demo",
                        "nodes:",
                        "  work/loop3_fpga_proto:",
                        "    source_policy:",
                        "      fpga_scripts:",
                        "        language: Tcl",
                        "        root: output/fpga/vivado/scripts",
                        "        allowed_extensions:",
                        "          - .tcl",
                        "        enforce_all_extensions: true",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            scripts_dir = project / "output" / "fpga" / "vivado" / "scripts"
            scripts_dir.mkdir(parents=True)
            (scripts_dir / "manual_note.txt").write_text("not a generated Tcl script\n", encoding="utf-8")

            checks = _check_source_policy(project, "work/loop3_fpga_proto")

            self.assertTrue(
                any(
                    check.name == "source_policy:fpga_scripts"
                    and check.status == "FAIL"
                    and "manual_note.txt" in check.detail
                    for check in checks
                )
            )

    def test_loop3_gate_requires_own_skill_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            config_dir = workspace / "prj" / "demo" / "work" / "config"
            config_dir.mkdir(parents=True)
            (config_dir / "project_config.yaml").write_text(
                "\n".join(
                    [
                        "schema_version: 1",
                        "project:",
                        "  name: demo",
                        "nodes:",
                        "  work/loop3_fpga_proto:",
                        "    source_policy:",
                        "      fpga_scripts:",
                        "        language: Tcl",
                        "        root: output/fpga/vivado/scripts",
                        "        allowed_extensions:",
                        "          - .tcl",
                        "        enforce_all_extensions: true",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            checks = _check_loop3(project, "develop")

            self.assertTrue(any(check.name == "skill_policy" and check.status == "FAIL" for check in checks))


class FinalOutputGateTests(unittest.TestCase):
    def test_final_audit_writes_real_manifest_and_final_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "env" / "rule" / "global").mkdir(parents=True, exist_ok=True)
            (workspace / "env" / "rule" / "global" / "workspace_config.yaml").write_text("schema_version: 1\n", encoding="utf-8")
            protected = workspace / "env" / "core" / "hdlflow" / "gates.py"
            protected.parent.mkdir(parents=True, exist_ok=True)
            protected.write_text("# protected gate file for unit test\n", encoding="utf-8")
            project = workspace / "prj" / "demo"
            _create_minimal_project(project)
            req_dir = project / "input" / "spec"
            req_dir.mkdir(parents=True, exist_ok=True)
            (req_dir / "srs.md").write_text("# Requirement\n\nDemo requirement.\n", encoding="utf-8")
            _write_valid_state_manifest(project, "work/docparse")
            _write_valid_state_manifest(project, "work/loop1_rtl_tb")
            _write_valid_state_manifest(project, "work/loop2_uvm")
            _write_valid_state_manifest(project, "work/loop3_fpga_proto")
            (project / "output" / "rtl").mkdir(parents=True, exist_ok=True)
            (project / "output" / "rtl" / "demo_top.v").write_text("module demo_top; endmodule\n", encoding="utf-8")
            _write_empty_review_findings(project)
            _write_doc_templates(project)
            _write_docset_source_inputs(project)
            docset = generate_docset(project, allow_draft=True)
            self.assertTrue(docset.ok, docset.check_result.errors)

            result = run_final_audit(project, level="develop")

            self.assertTrue(result.ok, [f"{check.name}: {check.detail}" for check in result.checks if check.status != "PASS"])
            manifest = (project / "output" / "manifest.yaml").read_text(encoding="utf-8")
            self.assertIn("loop1_gate: PASS", manifest)
            self.assertIn("loop2_gate: PASS", manifest)
            self.assertIn("loop3_gate: PASS", manifest)
            self.assertIn("output/rtl/demo_top.v", manifest)
            self.assertIn("final_gate: PASS", manifest)
            self.assertTrue((project / "output" / "reports" / "final_audit_report.md").exists())


class DocsetTests(unittest.TestCase):
    def test_removed_design_doc_api_fails_explicitly(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            with self.assertRaises(RemovedWorkflowError) as caught:
                generate_design_document(project)

            self.assertIn("generate-design-doc has been removed", str(caught.exception))

    def test_generate_docset_refuses_when_frontdoor_is_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = generate_docset(project)

            self.assertFalse(result.ok)
            self.assertIn("generate-docs blocked: requirements-frontdoor-check did not pass", result.errors)
            self.assertFalse(result.doc_paths)

    def test_generate_docset_creates_four_documents_and_manifests(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_doc_templates(project)
            _write_docset_source_inputs(project)

            result = generate_docset(project, change_id="CR-202606120001-docset", allow_draft=True)

            self.assertTrue(result.ok, result.check_result.errors)
            self.assertEqual(
                {path.name for path in result.doc_paths},
                {"application_guide.md", "microarchitecture_spec.md", "verification_plan.md", "delivery_package.md"},
            )
            self.assertTrue(result.docset_manifest_path.exists())
            self.assertFalse((project / "output/reports/design/design_rule_and_architecture.md").exists())
            manifest = json.loads(result.docset_manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(
                {item["doc_type"] for item in manifest["documents"]},
                {definition.doc_type for definition in DOC_DEFINITIONS},
            )
            uarch_text = (project / "output/docs/design/microarchitecture_spec.md").read_text(encoding="utf-8")
            verif_text = (project / "output/docs/test/verification_plan.md").read_text(encoding="utf-8")
            app_text = (project / "output/docs/application/application_guide.md").read_text(encoding="utf-8")
            delivery_text = (project / "output/docs/delivery/delivery_package.md").read_text(encoding="utf-8")
            self.assertIn("demo_top", uarch_text)
            self.assertIn("Owns top-level pass-through behavior", uarch_text)
            self.assertIn("Logic Level Design", uarch_text)
            self.assertIn("Storage / FIFO / Counter Plan", uarch_text)
            self.assertIn("State Machines", uarch_text)
            self.assertIn("valid_o_reg", uarch_text)
            self.assertIn("demo_leaf_fsm", uarch_text)
            self.assertIn("Module Topology", uarch_text)
            self.assertIn("REQ-UNIT-001", app_text)
            self.assertIn("Decode host command opcodes", app_text)
            self.assertIn("REQ-WAVE-001", verif_text)
            self.assertIn("Waveform Secondary Check Plan", verif_text)
            self.assertNotIn("Source References", app_text)
            self.assertNotIn("Source References", uarch_text)
            self.assertNotIn("Source References", verif_text)
            self.assertNotIn("Source References", delivery_text)
            self.assertNotIn("TBD", app_text + uarch_text + verif_text + delivery_text)

    def test_generate_single_doc_supports_debug_document_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_doc_templates(project)
            _write_docset_source_inputs(project)

            result = generate_single_doc(project, "verification_plan", change_id="CR-202606120002-single")

            self.assertTrue(result.ok, result.check_result.errors)
            self.assertEqual(result.doc_paths, [project / "output/docs/test/verification_plan.md"])
            self.assertTrue((project / "output/docs/manifests/verification_doc_manifest.json").exists())
            self.assertFalse((project / "output/docs/design/microarchitecture_spec.md").exists())

    def test_check_docset_detects_document_hash_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_doc_templates(project)
            _write_docset_source_inputs(project)
            generate_docset(project, allow_draft=True)
            doc = project / "output/docs/application/application_guide.md"
            doc.write_text(doc.read_text(encoding="utf-8") + "\nmanual edit\n", encoding="utf-8")

            check = check_docset(project)

            self.assertFalse(check.ok)
            self.assertTrue(any("hash does not match manifest" in error for error in check.errors))

    def test_check_docset_detects_source_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_doc_templates(project)
            source = _write_docset_source_inputs(project)
            generate_docset(project, allow_draft=True)
            source.write_text(source.read_text(encoding="utf-8") + "\n# changed source intent\n", encoding="utf-8")

            check = check_docset(project)

            self.assertFalse(check.ok)
            self.assertTrue(any("source drift" in error for error in check.errors))

    def test_release_check_blocks_placeholders(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_doc_templates(project)
            _write_docset_source_inputs(project)
            generate_docset(project, allow_draft=True)
            doc = project / "output/docs/application/application_guide.md"
            doc.write_text(doc.read_text(encoding="utf-8") + "\nTBD\n", encoding="utf-8")

            check = check_docset(project, level="release")

            self.assertFalse(check.ok)
            self.assertTrue(any("release-blocking placeholder" in error for error in check.errors))


@unittest.skip("single design-doc workflow was replaced by DocsetTests")
class DesignDocTests(unittest.TestCase):
    def test_generate_design_doc_refuses_when_frontdoor_is_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            result = generate_design_document(project)

            self.assertFalse(result.ok)
            self.assertIn("generate-design-doc blocked: requirements-frontdoor-check did not pass", result.errors)
            self.assertTrue(any(error.startswith("frontdoor report: ") for error in result.errors))
            self.assertTrue(any(error.startswith("frontdoor: ") for error in result.errors))
            self.assertIn("next action: fix the listed frontdoor/review issues", result.errors)
            self.assertFalse(result.report_path.exists())

    def test_generate_design_doc_reports_review_check_blockers(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_structured_review_findings(project, severity="high", status="open")

            result = generate_design_document(project)

            self.assertFalse(result.ok)
            self.assertIn("generate-design-doc blocked: review-check did not pass", result.errors)
            self.assertTrue(any(error.startswith("review report: ") for error in result.errors))
            self.assertTrue(any("REV-SPEC-001" in error for error in result.errors))
            self.assertTrue(any(error.startswith("next command: python -m hdlflow.cli review-check") for error in result.errors))
            self.assertFalse(result.report_path.exists())

    def test_generate_design_doc_tracks_rtl_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            rtl_dir = project / "output" / "rtl"
            rtl_dir.mkdir(parents=True)
            (rtl_dir / "demo_top.v").write_text(
                "\n".join(
                    [
                        "//==============================================================================",
                        "// Module      : demo_top",
                        "// File        : demo_top.v",
                        "// Project     : demo",
                        "// Description : Demo top module.",
                        "// Scope:",
                        "//   - Owns a single pass-through signal.",
                        "//==============================================================================",
                        "module demo_top (",
                        "    input  wire clk,",
                        "    input  wire rst_n,",
                        "    output wire done_o",
                        ");",
                        "assign done_o = rst_n;",
                        "endmodule",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = generate_design_document(project, allow_draft=True)
            self.assertTrue(result.ok)
            self.assertTrue(result.report_path.exists())
            self.assertTrue(result.manifest_path.exists())

            text = result.report_path.read_text(encoding="utf-8")
            self.assertIn("## 第1章 需求与边界定义 (Requirements & Scope)", text)
            self.assertIn("## 第3章 RTL 实现说明 (RTL Implementation)", text)
            self.assertIn("## 第4章 验证架构与测试计划 (Verification & Test Plan)", text)
            self.assertIn("### 4.2 Directed TB 验证与计划 (Baseline Checks)", text)
            self.assertIn("### 4.5 UVM 用例计划矩阵 (Test Matrix)", text)
            self.assertIn("Directed TB 与 UVM 是分层验证路径", text)
            self.assertIn("`demo_top`", text)

            check = check_design_document(project, sections=["requirements", "rtl", "uvm", "test_plan", "fpga"])
            self.assertTrue(check.ok)

    def test_generate_design_doc_accepts_frontdoor_alias_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            (project / "work/docparse" / "frontdoor").mkdir(parents=True)
            (project / "work/docparse" / "structured_spec").mkdir(parents=True)
            (project / "work/docparse" / "architecture").mkdir(parents=True)
            (project / "work/docparse" / "frontdoor" / "srs.yaml").write_text(
                "\n".join(
                    [
                        "purpose: Demo purpose",
                        "functional_requirements:",
                        "  - id: REQ-ALIAS-001",
                        "    title: SPI command decode",
                        "    description: Decode host command opcodes",
                        "    type: functional",
                        "interfaces:",
                        "  - name: spi_host",
                        "    type: input-output",
                        "    signals:",
                        "      - sclk",
                        "      - mosi",
                        "      - miso",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (project / "work/docparse" / "structured_spec" / "interface_spec.yaml").write_text(
                "\n".join(
                    [
                        "status: READY",
                        "interfaces:",
                        "  - title: arinc_rx_logic",
                        "    description: RX digital boundary",
                        "    type: output",
                        "    signals:",
                        "      - rx_word",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (project / "work/docparse" / "architecture" / "module_plan.yaml").write_text(
                "\n".join(
                    [
                        "top_level:",
                        "  name: demo_top",
                        "modules:",
                        "  - name: spi_cmd",
                        "    responsibility: Owns command decode only",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = generate_design_document(project, allow_draft=True)

            self.assertTrue(result.ok)
            text = result.report_path.read_text(encoding="utf-8")
            self.assertIn("SPI command decode: Decode host command opcodes", text)
            self.assertIn("input-output", text)
            self.assertIn("sclk; mosi; miso", text)
            self.assertIn("arinc_rx_logic", text)
            self.assertIn("Owns command decode only", text)

    def test_generate_design_doc_includes_waveform_secondary_check_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            (project / "work/docparse" / "structured_spec").mkdir(parents=True)
            (project / "work/docparse" / "verification").mkdir(parents=True)
            (project / "work/docparse" / "structured_spec" / "test_intent.yaml").write_text(
                "\n".join(
                    [
                        "waveform_windows:",
                        "  - id: REQ-WAVE-001",
                        "    observed_signals:",
                        "      - clk",
                        "      - valid_o",
                        "    trigger: directed case valid pulse",
                        "waveform_observability:",
                        "  - top-level DUT ports",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (project / "work/docparse" / "verification" / "verification_plan.yaml").write_text(
                "\n".join(
                    [
                        "waveform_comparison:",
                        "  - requirement: REQ-WAVE-001",
                        "    signals:",
                        "      - clk",
                        "      - valid_o",
                        "    time_window: case start to scoreboard pass",
                        "    pass_criteria: no X/Z, clock activity, and valid_o toggles",
                        "    evidence: output/reports/loop1/waveform_gate.json",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = generate_design_document(project, allow_draft=True)

            self.assertTrue(result.ok)
            text = result.report_path.read_text(encoding="utf-8")
            self.assertIn("Loop1 Waveform Secondary Check Plan", text)
            self.assertIn("REQ-WAVE-001", text)
            self.assertIn("valid_o", text)
            self.assertIn("HDLFLOW_WAVE_BEGIN", text)
            self.assertIn("waveform_gate.json", text)


class StateSyncTests(unittest.TestCase):
    def test_sync_ignores_invalid_empty_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "work" / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "input_develop_20260517000001.json").write_text("{}", encoding="utf-8")
            gate_dir = project / "output" / "reports" / "gates"
            gate_dir.mkdir(parents=True, exist_ok=True)
            (gate_dir / "input_develop_20260517000001.md").write_text("- result: PASS\n", encoding="utf-8")

            result = sync_project_state(project)

            self.assertEqual(result.overall_status, "pending")
            self.assertEqual(result.passed_nodes, [])

    def test_sync_marks_loop2_passed_from_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_valid_state_manifest(project, "input")
            _write_valid_state_manifest(project, "work/docparse")
            _write_valid_state_manifest(project, "work/loop1_rtl_tb")
            _write_valid_state_manifest(project, "work/loop2_uvm")
            report_dir = project / "output" / "reports" / "loop2"
            report_dir.mkdir(parents=True)
            (report_dir / "loop2_report.json").write_text(
                json.dumps({"schema": "hdlflow_loop2_report_v1", "result": "PASS", "summary": {"coverage": "100.0"}}),
                encoding="utf-8",
            )

            result = sync_project_state(project)

            self.assertEqual(result.overall_status, "loop2_passed")
            self.assertEqual(result.current_loop, "loop3")
            gate_status = json.loads((project / "work" / "gates" / "gate_status.json").read_text(encoding="utf-8"))
            self.assertEqual(gate_status["loop2_exit"], "pass")

    def test_latest_failed_gate_overrides_older_pass_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_valid_state_manifest(project, "input")
            _write_valid_state_manifest(project, "work/docparse")
            _write_valid_state_manifest(project, "work/loop1_rtl_tb")
            _write_valid_state_manifest(project, "work/loop2_uvm")
            gate_dir = project / "output" / "reports" / "gates"
            gate_dir.mkdir(parents=True, exist_ok=True)
            (gate_dir / "work_loop2_uvm_develop_20260517030303.md").write_text("- result: FAIL\n", encoding="utf-8")

            result = sync_project_state(project)

            self.assertEqual(result.overall_status, "loop2_blocked")
            self.assertEqual(result.failed_nodes, ["work/loop2_uvm"])
            gate_status = json.loads((project / "work" / "gates" / "gate_status.json").read_text(encoding="utf-8"))
            self.assertEqual(gate_status["loop2_exit"], "fail")
            task_board = json.loads((project / "work" / "gates" / "task_board.json").read_text(encoding="utf-8"))
            criteria = {item["id"]: item["status"] for item in task_board["done_criteria"]}
            self.assertEqual(criteria["loop2-uvm-pass"], "blocked")

    def test_closed_change_id_gate_invocation_failure_does_not_regress_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_valid_state_manifest(project, "input")
            _write_valid_state_manifest(project, "work/docparse")
            gate_dir = project / "output" / "reports" / "gates"
            gate_dir.mkdir(parents=True, exist_ok=True)
            (gate_dir / "work_docparse_develop_20260517030303.md").write_text(
                "\n".join(
                    [
                        "- result: FAIL",
                        "",
                        "| Check | Status | Detail |",
                        "| --- | --- | --- |",
                        "| change_control_state | FAIL | CR-demo status is 'closed', expected approved |",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = sync_project_state(project)

            self.assertEqual(result.overall_status, "docparse_passed")
            self.assertEqual(result.current_loop, "loop1")
            self.assertEqual(result.failed_nodes, [])

    def test_sync_records_loop3_vivado_and_board_evidence_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            for node in [
                "input",
                "work/docparse",
                "work/loop1_rtl_tb",
                "work/loop2_uvm",
                "work/loop3_fpga_proto",
            ]:
                _write_valid_state_manifest(project, node)
            vivado_report = project / "output" / "fpga" / "vivado" / "reports" / "pure_pl_uart_led_proto_run.md"
            board_report = project / "output" / "reports" / "loop3" / "serial" / "latest_serial_validation_report.md"
            vivado_report.parent.mkdir(parents=True)
            board_report.parent.mkdir(parents=True)
            vivado_report.write_text("result: PASS\n", encoding="utf-8")
            board_report.write_text("- result: PASS\n", encoding="utf-8")

            result = sync_project_state(project)

            self.assertEqual(result.overall_status, "loop3_passed")
            loop3_state = json.loads((project / "work" / "gates" / "loop3_state.json").read_text(encoding="utf-8"))
            self.assertEqual(loop3_state["latest_vivado_report"], "output/fpga/vivado/reports/pure_pl_uart_led_proto_run.md")
            self.assertEqual(loop3_state["latest_board_log"], "output/reports/loop3/serial/latest_serial_validation_report.md")


class WorkflowOptimizationTests(unittest.TestCase):
    def test_release_preflight_reports_develop_evidence_not_promoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            _write_docset_manifest(project, timestamp=1_800_000_100.0, documents=("application_guide", "microarchitecture_specification", "verification_plan", "delivery_package"))
            (project / "output" / "manifest.yaml").write_text(
                "\n".join(["loop1_gate: PASS", "loop2_gate: PASS", "loop3_gate: PASS", ""]),
                encoding="utf-8",
            )
            _write_manifest_payload(project, "work/loop1_rtl_tb", {})

            result = release_preflight(project)

            self.assertFalse(result.ok)
            self.assertTrue(any("develop gate evidence but no release" in item for item in result.blockers))
            text = result.report_path.read_text(encoding="utf-8")
            self.assertIn("does not convert develop evidence into release evidence", text)
            self.assertFalse((project / "output/reports/design/design_rule_and_architecture.md").exists())

    def test_repair_diagnose_detects_generated_input_spec_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            spec_dir = project / "input" / "spec"
            spec_dir.mkdir(parents=True)
            (spec_dir / "srs.yaml").write_text("requirements: []\n", encoding="utf-8")
            (spec_dir / "acceptance_criteria.yaml").write_text("criteria: []\n", encoding="utf-8")
            (spec_dir / "requirements.md").write_text("# Requirements\n", encoding="utf-8")

            result = diagnose_repairs(project)

            categories = {ticket.category for ticket in result.tickets}
            self.assertIn("frontdoor_layout_migration", categories)
            self.assertIn("req_decompose_layout_migration", categories)
            ticket_text = "\n".join(path.read_text(encoding="utf-8") for path in (project / "work/repair/tickets").glob("*.yaml"))
            self.assertIn("does_not_write_generated_docset_documents", ticket_text)

    def test_repair_apply_quarantines_frontdoor_artifact_without_design_doc_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            spec_dir = project / "input" / "spec"
            spec_dir.mkdir(parents=True)
            (spec_dir / "srs.yaml").write_text("requirements: []\n", encoding="utf-8")

            diagnose = diagnose_repairs(project)
            ticket = next(item for item in diagnose.tickets if item.category == "frontdoor_layout_migration")
            result = apply_repair_ticket(project, ticket_id=ticket.ticket_id)

            self.assertTrue(result.applied)
            self.assertTrue((project / "work/docparse/frontdoor/srs.yaml").exists())
            self.assertTrue((project / "work/repair/quarantine" / ticket.ticket_id / "srs.yaml").exists())
            self.assertFalse((project / "input/spec/srs.yaml").exists())
            self.assertFalse((project / "output/docs/manifests/docset_manifest.json").exists())

    def test_schema_check_flags_trace_mappings_instead_of_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            trace = project / "work/docparse/trace_matrix/req_to_design_intent.yaml"
            trace.parent.mkdir(parents=True)
            trace.write_text("mappings: []\n", encoding="utf-8")

            result = schema_check(project, file_rel="work/docparse/trace_matrix/req_to_design_intent.yaml")

            self.assertFalse(result.ok)
            self.assertTrue(any("links" in issue.message for issue in result.issues))

    def test_schema_check_accepts_structured_review_findings_and_list_evidence_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            analysis = project / "work/docparse/structured_spec/document_analysis.yaml"
            analysis.parent.mkdir(parents=True, exist_ok=True)
            analysis.write_text(
                "\n".join(
                    [
                        "schema_version: 1",
                        "project: demo",
                        "status: READY",
                        "source_documents:",
                        "  - source_ref: input/spec/source.yaml",
                        "    parser_output: mineru_high_precision_markdown",
                        "    document_type: datasheet",
                        "analysis_units:",
                        "  - unit_id: AU-001",
                        "    source_ref: input/spec/source.yaml",
                        "    section: Interface",
                        "    summary: Source-backed interface requirement.",
                        "    evidence_refs:",
                        "      - input/spec/source.yaml",
                        "    extracted_requirements:",
                        "      - REQ-001",
                        "evidence_map:",
                        "  - requirement_id: REQ-001",
                        "    evidence_refs:",
                        "      - AU-001",
                        "question_review:",
                        "  status: REVIEWED",
                        "  reviewed_by: test",
                        "  review_evidence: work/docparse/frontdoor/open_questions.md",
                        "  unresolved_count: 0",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            _write_structured_review_findings(project, severity="medium", status="verified")

            analysis_result = schema_check(project, file_rel="work/docparse/structured_spec/document_analysis.yaml")
            review_result = schema_check(project, file_rel="work/docparse/review/role_findings.yaml")

            self.assertTrue(analysis_result.ok)
            self.assertTrue(review_result.ok)

    def test_exploration_sandbox_stays_out_of_formal_design_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)

            started = start_exploration(project, title="Loop3 command sketch", objective="draft repair-safe notes")
            noted = add_exploration_note(project, session_id=started.session_id, note="Candidate command remains advisory.")
            promoted = promote_exploration(project, session_id=started.session_id, target="change-request")

            self.assertTrue(started.path.is_dir())
            self.assertTrue(noted.path.exists())
            self.assertTrue(promoted.path.exists())
            self.assertTrue(str(promoted.path.relative_to(project)).replace("\\", "/").startswith("work/explore/"))
            self.assertFalse((project / "output/docs/manifests/docset_manifest.json").exists())


def _write_change_request(project: Path, status: str, *, timestamp: float) -> Path:
    change_id = "CR-20260523120000-demo"
    requests_dir = project / "work/change" / "requests"
    requests_dir.mkdir(parents=True, exist_ok=True)
    request = requests_dir / f"{change_id}.md"
    request.write_text(
        "\n".join(
            [
                f"# Change Request {change_id}",
                "",
                f"- id: {change_id}",
                f"- status: {status}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    os.utime(request, (timestamp, timestamp))
    return request


def _write_structured_review_findings(project: Path, *, severity: str, status: str) -> Path:
    review_dir = project / "work" / "docparse" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    path = review_dir / "role_findings.yaml"
    lines = [
        "schema_version: 1",
        f"project: {project.name}",
        "status: READY",
        "owner_role: review",
        "source_refs: []",
        "roles:",
    ]
    for role in ["spec", "arch", "exec", "sim", "review", "arbtr"]:
        lines.extend(
            [
                f"  {role}:",
                "    status: READY",
            ]
        )
        if role == "spec":
            lines.append("    findings:")
            lines.extend(
                [
                    "      -",
                    "        id: REV-SPEC-001",
                    f"        severity: {severity}",
                    f"        status: {status}",
                    "        category: requirement_trace",
                    "        owner: spec",
                    "        artifact: work/docparse/frontdoor/srs.yaml",
                    "        issue: Requirement trace is ambiguous",
                    "        impact: Loop1 implementation could encode the wrong behavior",
                    "        evidence: work/docparse/frontdoor/srs.yaml",
                    "        recommendation: Clarify the requirement and refresh trace links",
                    "        route_to: spec",
                ]
            )
        else:
            lines.append("    findings: []")
        lines.append("    confidence: high")
    lines.extend(["cross_role_conflicts: []", "assumptions: []", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _write_review_finding_with_evidence(project: Path, artifact: str, evidence: str) -> Path:
    review_dir = project / "work" / "docparse" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    path = review_dir / "role_findings.yaml"
    lines = [
        "schema_version: 1",
        f"project: {project.name}",
        "roles:",
    ]
    for role in ["spec", "arch", "exec", "sim", "review", "arbtr"]:
        lines.extend([f"  {role}:", "    status: READY"])
        if role == "review":
            lines.extend(
                [
                    "    findings:",
                    "      -",
                    "        id: REV-REVIEW-001",
                    "        severity: info",
                    "        status: closed",
                    "        category: formal_artifact_review",
                    "        owner: review",
                    f"        artifact: {artifact}",
                    "        issue: Formal artifact review evidence recorded",
                    "        impact: Review coverage is available for gate checks",
                    f"        evidence: {evidence}",
                    "        recommendation: Keep review evidence aligned with changed artifacts",
                    "        route_to: exec",
                ]
            )
        else:
            lines.append("    findings: []")
    lines.extend(["cross_role_conflicts: []", "assumptions: []", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _write_empty_review_findings(project: Path) -> Path:
    review_dir = project / "work" / "docparse" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    path = review_dir / "role_findings.yaml"
    rtl_files = sorted((project / "output" / "rtl").glob("*.v"))
    tb_files = sorted((project / "output" / "tb").glob("*.v"))
    uvm_files = sorted([*(project / "output" / "uvm").rglob("*.sv"), *(project / "output" / "uvm").rglob("*.svh")])
    rtl_file_names = ", ".join(path.name for path in rtl_files)
    tb_file_names = ", ".join(path.name for path in tb_files)
    uvm_file_names = ", ".join(path.name for path in uvm_files)
    review_evidence = [
        "output/reports/loop1/rtl_skill_audit.md",
        "env/rule/skills/rtl-architecture-and-gen/SKILL.md",
    ]
    if rtl_file_names:
        review_evidence.append(f"rtl files: {rtl_file_names}")
    if tb_file_names:
        review_evidence.extend(
            [
                "output/tb/full_function_test_plan.md",
                "env/rule/skills/modelsim-run-triage-debug/SKILL.md",
                f"tb files: {tb_file_names}",
            ]
        )
    if uvm_file_names:
        review_evidence.extend(
            [
                "env/rule/skills/uvm-env-and-test-build/SKILL.md",
                f"uvm files: {uvm_file_names}",
            ]
        )
    lines = [
        "schema_version: 1",
        f"project: {project.name}",
        "roles:",
    ]
    for role in ["spec", "arch", "exec", "sim", "review", "arbtr"]:
        lines.extend(
            [
                f"  {role}:",
                "    status: READY",
            ]
        )
        if role == "review" and (rtl_files or tb_files or uvm_files):
            lines.append("    findings:")
            lines.extend(
                [
                    "      -",
                    "        id: REV-RTL-SKILL-001",
                    "        severity: info",
                    "        status: closed",
                    "        category: rtl_skill_compliance",
                    "        owner: review",
                    "        artifact: output/reports/loop1/rtl_skill_audit.md",
                    "        issue: RTL skill audit evidence reviewed",
                    "        impact: RTL implementation remains bound to the platform RTL skill and style guide",
                    f"        evidence: {'; '.join(review_evidence)}",
                    "        recommendation: Keep running rtl-skill-audit after every RTL edit",
                    "        route_to: exec",
                ]
            )
        else:
            lines.append("    findings: []")
    lines.extend(["cross_role_conflicts: []", "assumptions: []", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _write_source_manifest(project: Path, node: str, source: Path) -> Path:
    manifest_dir = project / "work" / "memory" / "recovery" / "rollback_manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    node_stem = node.replace("/", "_")
    manifest = manifest_dir / f"{node_stem}_develop_20260517000001.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project": project.name,
                "node": node,
                "level": "develop",
                "sources": [
                    {
                        "path": str(source.relative_to(project)).replace("\\", "/"),
                        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest


def _write_manifest_payload(project: Path, node: str, payload: dict[str, object]) -> Path:
    manifest_dir = project / "work" / "memory" / "recovery" / "rollback_manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    node_stem = node.replace("/", "_")
    manifest = manifest_dir / f"{node_stem}_develop_20260517000001.json"
    gate_report_rel = f"output/reports/gates/{node_stem}_develop_20260517000001.md"
    gate_report = project / gate_report_rel
    gate_report.parent.mkdir(parents=True, exist_ok=True)
    gate_report.write_text("- result: PASS\n", encoding="utf-8")
    data = {
        "schema_version": 1,
        "project": project.name,
        "node": node,
        "level": "develop",
        "created_at": "2026-05-17T00:00:00",
        "gate_report": gate_report_rel,
        "sources": [],
        "evidence": [],
        "skill_constraints": [],
        "protected_gate_files": [],
    }
    data.update(payload)
    manifest.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _write_valid_state_manifest(project: Path, node: str, stamp: str = "20260517000001") -> Path:
    return _write_manifest_payload(project, node, {})


def _write_doc_templates(project: Path) -> None:
    for definition in DOC_DEFINITIONS:
        path = project / definition.template_rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {definition.title} Template\n", encoding="utf-8")


def _write_docset_source_inputs(project: Path) -> Path:
    frontdoor = project / "work/docparse/frontdoor"
    structured = project / "work/docparse/structured_spec"
    architecture = project / "work/docparse/architecture"
    verification = project / "work/docparse/verification"
    docparse = project / "work/docparse"
    rtl_dir = project / "output/rtl"
    frontdoor.mkdir(parents=True, exist_ok=True)
    structured.mkdir(parents=True, exist_ok=True)
    architecture.mkdir(parents=True, exist_ok=True)
    verification.mkdir(parents=True, exist_ok=True)
    docparse.mkdir(parents=True, exist_ok=True)
    rtl_dir.mkdir(parents=True, exist_ok=True)
    srs = frontdoor / "srs.yaml"
    srs.write_text(
        "\n".join(
            [
                "purpose: Demo purpose",
                "functional_requirements:",
                "  - id: REQ-UNIT-001",
                "    title: SPI command decode",
                "    description: Decode host command opcodes",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (frontdoor / "acceptance_criteria.yaml").write_text(
        "\n".join(
            [
                "criteria:",
                "  - id: AC-UNIT-001",
                "    description: Loop1 directed test passes",
                "    evidence: output/reports/loop1/loop1_report.json",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (structured / "interface_spec.yaml").write_text(
        "\n".join(
            [
                "interfaces:",
                "  - name: spi_host",
                "    type: input-output",
                "    description: Host command channel",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (structured / "test_intent.yaml").write_text(
        "\n".join(
            [
                "waveform_secondary_checks:",
                "  - id: REQ-WAVE-001",
                "    description: valid_o toggles during directed command",
                "    evidence: output/reports/loop1/waveform_gate.json",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (architecture / "module_plan.yaml").write_text(
        "\n".join(
            [
                "description: Demo microarchitecture",
                "top_level:",
                "  name: demo_top",
                "  wrapper_policy: hierarchy-only top",
                "  forbidden_responsibilities:",
                "    - protocol_decode",
                "    - register_field_update",
                "    - datapath_mutation",
                "    - fifo_storage",
                "    - monolithic_fsm",
                "modules:",
                "  - name: demo_top",
                "    id: MOD-001",
                "    type: top",
                "    source_file: demo_top.v",
                "    parent: \"\"",
                "    responsibility: Owns top-level pass-through behavior",
                "    clock_domain: clk",
                "    reset_domain: rst_n",
                "    children:",
                "      - demo_leaf",
                "    owns:",
                "      registers: []",
                "      register_fields: []",
                "      fsms: []",
                "      fifos: []",
                "      memories: []",
                "      counters: []",
                "      arbiters: []",
                "      error_flags: []",
                "    interfaces:",
                "      inputs:",
                "        - clk",
                "      outputs:",
                "        - valid_o",
                "      internal:",
                "        - demo_child_bus",
                "    dataflow:",
                "      consumes:",
                "        - clk",
                "      produces:",
                "        - valid_o",
                "      transforms:",
                "        - top-level pass-through behavior",
                "    req_ids:",
                "      - REQ-UNIT-001",
                "    verification_refs:",
                "      tests:",
                "        - TC-001",
                "      assertions: []",
                "      coverage: []",
                "    forbidden_responsibilities:",
                "      - protocol_decode",
                "    logic:",
                "      combinational: wire child output to top-level port",
                "      sequential: no top-level sequential state",
                "      edge_cases: reset and command legality are owned by child modules",
                "  - name: demo_leaf",
                "    id: MOD-002",
                "    type: leaf",
                "    source_file: demo_leaf.v",
                "    parent: demo_top",
                "    responsibility: Own valid_o register",
                "    clock_domain: clk",
                "    reset_domain: rst_n",
                "    owns:",
                "      registers:",
                "        - valid_o_reg",
                "      register_fields: []",
                "      fsms:",
                "        - demo_leaf_fsm",
                "      fifos: []",
                "      memories: []",
                "      counters:",
                "        - valid_delay_count",
                "      arbiters: []",
                "      error_flags: []",
                "    interfaces:",
                "      inputs:",
                "        - clk",
                "        - rst_n",
                "      outputs:",
                "        - valid_o",
                "      internal:",
                "        - demo_child_bus",
                "    dataflow:",
                "      consumes:",
                "        - clk",
                "        - rst_n",
                "      produces:",
                "        - valid_o",
                "      transforms:",
                "        - registered valid_o behavior",
                "    design_feature_ids:",
                "      - DF-DEMO-LEAF",
                "    verification_refs:",
                "      tests: []",
                "      assertions:",
                "        - SVA-DEMO-LEAF",
                "      coverage:",
                "        - COV-DEMO-LEAF",
                "    forbidden_responsibilities:",
                "      - unowned_register_update",
                "    logic:",
                "      combinational: derive next valid state from command inputs",
                "      sequential: register valid_o on clk and clear on rst_n",
                "      edge_cases: invalid command leaves valid_o low",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (architecture / "state_machines.yaml").write_text(
        "\n".join(
            [
                "state_machines:",
                "  - name: demo_leaf_fsm",
                "    owning_module: demo_leaf",
                "    reset_state: IDLE",
                "    states:",
                "      - IDLE",
                "      - ACTIVE",
                "    transitions:",
                "      - IDLE -> ACTIVE on command_valid",
                "      - ACTIVE -> IDLE after valid_o pulse",
                "    illegal_state_behavior: recover to IDLE and suppress valid_o",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (docparse / "doc_projection.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                "project: demo",
                "status: DRAFT",
                "documents:",
                "  application_guide:",
                "    output: output/docs/application/application_guide.md",
                "    sources:",
                "      - id: requirements",
                "        path: work/docparse/frontdoor/srs.yaml",
                "        required: true",
                "      - id: acceptance",
                "        path: work/docparse/frontdoor/acceptance_criteria.yaml",
                "        required: true",
                "      - id: interface_spec",
                "        path: work/docparse/structured_spec/interface_spec.yaml",
                "        required: true",
                "  microarchitecture_spec:",
                "    output: output/docs/design/microarchitecture_spec.md",
                "    sources:",
                "      - id: module_plan",
                "        path: work/docparse/architecture/module_plan.yaml",
                "        required: true",
                "      - id: state_machines",
                "        path: work/docparse/architecture/state_machines.yaml",
                "        required: true",
                "  verification_plan:",
                "    output: output/docs/test/verification_plan.md",
                "    sources:",
                "      - id: test_intent",
                "        path: work/docparse/structured_spec/test_intent.yaml",
                "        required: true",
                "      - id: verification_plan",
                "        path: work/docparse/verification/verification_plan.yaml",
                "        required: true",
                "  delivery_package:",
                "    output: output/docs/delivery/delivery_package.md",
                "    sources:",
                "      - id: requirements",
                "        path: work/docparse/frontdoor/srs.yaml",
                "        required: true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (verification / "verification_plan.yaml").write_text(
        "\n".join(
            [
                "goals:",
                "  - id: VG-001",
                "    description: Prove command decode behavior",
                "tests:",
                "  - id: TC-001",
                "    description: Directed SPI command decode",
                "    expected: scoreboard pass",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (rtl_dir / "demo_top.v").write_text("module demo_top(input wire clk, output wire valid_o); endmodule\n", encoding="utf-8")
    return srs


def _write_project_required_skill_config(workspace: Path, project_name: str, skill_name: str) -> Path:
    config = workspace / "prj" / project_name / "work" / "config" / "project_config.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "project:",
                f"  name: {project_name}",
                "nodes:",
                "  work/loop1_rtl_tb:",
                "    skill_policy:",
                "      required_skills:",
                f"        {skill_name}:",
                f"          path: env/rule/skills/{skill_name}/SKILL.md",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config


def _populate_required_validation_paths(project: Path) -> None:
    for rel in REQUIRED_PATHS:
        path = project / rel
        if path.exists():
            continue
        if path.suffix:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}\n", encoding="utf-8")
        else:
            path.mkdir(parents=True, exist_ok=True)


def _create_minimal_workspace_for_frontdoor(workspace: Path) -> None:
    (workspace / "env" / "rule" / "global").mkdir(parents=True, exist_ok=True)
    (workspace / "env" / "rule" / "global" / "workspace_config.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    rtl_skill = workspace / "env" / "rule" / "skills" / "rtl-architecture-and-gen" / "SKILL.md"
    style_guide = workspace / "env" / "rule" / "skills" / "rtl-architecture-and-gen" / "references" / "verilog-rtl-style-guide.md"
    rtl_skill.parent.mkdir(parents=True, exist_ok=True)
    style_guide.parent.mkdir(parents=True, exist_ok=True)
    rtl_skill.write_text("# RTL Architecture Skill\n", encoding="utf-8")
    style_guide.write_text("# Verilog RTL Style Guide\n", encoding="utf-8")


def _write_impact_artifacts(project: Path, change_id: str, artifacts: list[str]) -> Path:
    impact_dir = project / "work/change" / "impact_analysis"
    impact_dir.mkdir(parents=True, exist_ok=True)
    impact = impact_dir / f"{change_id}.md"
    impact.write_text(
        "\n".join(
            [
                f"# Impact Analysis {change_id}",
                "",
                "## Artifacts",
                "",
                *[f"- {artifact}" for artifact in artifacts],
                "",
                "## Required Verification",
                "",
                "- rerun owning gate",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return impact


def _write_complete_change_request(project: Path, *, timestamp: float) -> Path:
    change_id = "CR-20260523120000-demo"
    request = _write_change_request(project, "approved", timestamp=timestamp)
    impact_dir = project / "work/change" / "impact_analysis"
    approval_dir = project / "work/change" / "approvals"
    impact_dir.mkdir(parents=True, exist_ok=True)
    approval_dir.mkdir(parents=True, exist_ok=True)
    impact = impact_dir / f"{change_id}.md"
    impact.write_text(
        "\n".join(
            [
                f"# Impact Analysis {change_id}",
                "",
                f"- id: {change_id}",
                "- status: impact_ready",
                "",
                "## Requirements",
                "",
                "- REQ-UNIT-001 changed requirement intent",
                "",
                "## Artifacts",
                "",
                "- output/tb/example.v",
                "",
                "## Required Verification",
                "",
                "- rerun owning loop gate",
                "",
                "## Docset Decision",
                "",
                "- required: yes",
                "- documents: microarchitecture_specification, verification_plan, delivery_package",
                "",
                "## Rollback Plan",
                "",
                "restore last rollback manifest",
                "",
            ]
        ),
        encoding="utf-8",
    )
    approval = approval_dir / f"{change_id}.md"
    approval.write_text(
        "\n".join(
            [
                f"# Approval {change_id}",
                "",
                f"- id: {change_id}",
                "- status: approved",
                "",
                "## Notes",
                "",
                "Approved for unit test.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    os.utime(impact, (timestamp, timestamp))
    os.utime(approval, (timestamp, timestamp))
    return request


def _write_frontdoor_pass_report(project: Path, *, timestamp: float) -> Path:
    report = project / "output" / "reports" / "docparse" / "requirements_frontend_check.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("# Requirements Frontend Check\n\n- result: PASS\n", encoding="utf-8")
    os.utime(report, (timestamp, timestamp))
    return report


def _write_docset_manifest(project: Path, *, timestamp: float, documents: tuple[str, ...]) -> None:
    doc_paths = {
        "application_guide": "output/docs/application/application_guide.md",
        "microarchitecture_specification": "output/docs/design/microarchitecture_spec.md",
        "verification_plan": "output/docs/test/verification_plan.md",
        "delivery_package": "output/docs/delivery/delivery_package.md",
    }
    manifest = project / "output/docs/manifests/docset_manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    for doc_type in doc_paths:
        doc = project / doc_paths[doc_type]
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(f"# {doc_type}\n", encoding="utf-8")
        os.utime(doc, (timestamp, timestamp))
        if doc_type in documents:
            entries.append({"doc_type": doc_type, "path": doc_paths[doc_type], "sha256": "unit-test"})
    manifest.write_text(
        json.dumps({"docset_version": 1, "documents": entries}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.utime(manifest, (timestamp, timestamp))


def _write_loop3_preflight_reports(project: Path) -> None:
    preflight = project / "output" / "reports" / "loop3" / "preflight" / "database_preflight.md"
    plan = project / "output" / "reports" / "loop3" / "preflight" / "prototype_plan_check.md"
    preflight.parent.mkdir(parents=True, exist_ok=True)
    preflight.write_text("# Loop3 Database Preflight\n\nresult: PASS\n", encoding="utf-8")
    plan.write_text("# Prototype Plan Check\n\n- result: PASS\n", encoding="utf-8")


def _write_loop3_signoff_evidence(project: Path, *, mode: str = "pl") -> None:
    _write_loop3_preflight_reports(project)
    plan = project / "work" / "loop3_fpga_proto" / "board_tests" / "prototype_plan.yaml"
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text(
        "\n".join(
            [
                "schema_version: 1",
                f"mode: {mode}",
                "rtl_top_module: demo_top",
                "cache_policy: flush_before_pl_read",
                "",
            ]
        ),
        encoding="utf-8",
    )
    reports = project / "output" / "fpga" / "vivado" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "post_impl_timing_summary.rpt").write_text("Setup : 0  Failing Endpoints\nHold  : 0  Failing Endpoints\n", encoding="utf-8")
    (reports / "post_impl_drc.rpt").write_text("DRC checks complete\n", encoding="utf-8")
    bitstream_dir = project / "output" / "fpga" / "vivado" / "bitstream"
    bitstream_dir.mkdir(parents=True, exist_ok=True)
    (bitstream_dir / "demo.bit").write_bytes(b"bit")
    xsa_dir = project / "output" / "fpga" / "vivado" / "hw_platform"
    xsa_dir.mkdir(parents=True, exist_ok=True)
    (xsa_dir / "demo.xsa").write_bytes(b"xsa")
    vitis_workspace = project / "output" / "fpga" / "vitis" / "workspace" / "demo_app" / "Debug"
    vitis_workspace.mkdir(parents=True, exist_ok=True)
    (vitis_workspace / "demo_app.elf").write_bytes(b"elf")
    serial_dir = project / "output" / "reports" / "loop3" / "serial"
    serial_dir.mkdir(parents=True, exist_ok=True)
    (serial_dir / "latest_serial_validation_report.md").write_text(
        "\n".join(
            [
                "# Serial Validation",
                "",
                "- TX[2026-05-26 00:00:00.000]: read",
                "- RX[2026-05-26 00:00:00.001]: read data=0x00000001",
                "- result: PASS",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (serial_dir / "latest_serial_text.log").write_text(
        "RX[2026-05-26 00:00:00.001]: read data=0x00000001\nLOOP3_RESULT PASS\n",
        encoding="utf-8",
    )


def _create_minimal_memory(project: Path) -> None:
    for rel in [
        "work/memory/00_global",
        "work/memory/recovery/rollback_manifests",
        "work/memory/recovery/failure_records",
    ]:
        (project / rel).mkdir(parents=True, exist_ok=True)
    (project / "work/memory/index.yaml").write_text(
        f"schema_version: 1\nproject: {project.name}\niterations: {{}}\n",
        encoding="utf-8",
    )
    (project / "work/memory/active_versions.md").write_text("# Active Version Memory\n", encoding="utf-8")
    (project / "work/memory/00_global/CURRENT_STATE.md").write_text("# Current State\n", encoding="utf-8")
    (project / "work/memory/00_global/PROJECT_BRIEF.md").write_text("# Project Brief\n", encoding="utf-8")
    (project / "work/memory/00_global/ACTIVE_PLAN.md").write_text(
        "\n".join(
            [
                "# Active Plan",
                "",
                "- schema_version: 1",
                f"- project: {project.name}",
                "- plan_id:",
                "- status: idle",
                "",
                "## Steps",
                "",
                "## Step Notes",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (project / "work/memory/00_global/PLAN_FINDINGS.md").write_text("# Plan Findings\n", encoding="utf-8")
    (project / "work/memory/00_global/PLAN_ERRORS.md").write_text("# Plan Errors\n", encoding="utf-8")


def _create_minimal_project(project: Path) -> None:
    project.mkdir(parents=True, exist_ok=True)
    (project / "output").mkdir(parents=True, exist_ok=True)
    (project / "work" / "gates").mkdir(parents=True, exist_ok=True)
    (project / "project_scaffold.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                f"project: {project.name}",
                "creation_mode: script_only",
                "template_source: env/rule/scaffold",
                "manual_project_directory_creation: forbidden",
                "created_by: unittest",
                "created_at: 2026-05-17T00:00:00",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (project / "work" / "gates" / "task_board.json").write_text(
        json.dumps(
            {
                "project": project.name,
                "done_criteria": [
                    {"id": "normalized-spec-ready", "status": "pending"},
                    {"id": "loop1-functional-pass", "status": "pending"},
                    {"id": "loop2-uvm-pass", "status": "done"},
                    {"id": "loop3-board-pass", "status": "pending"},
                ],
                "tasks": [
                    {"id": "ingest_source_docs", "status": "pending"},
                    {"id": "normalize_specs", "status": "pending"},
                    {"id": "implement_rtl", "status": "pending"},
                    {"id": "build_functional_tb", "status": "pending"},
                    {"id": "run_loop1", "status": "pending"},
                    {"id": "build_uvm_env", "status": "done"},
                    {"id": "run_uvm_precheck", "status": "done"},
                    {"id": "run_regression", "status": "done"},
                    {"id": "run_loop3", "status": "pending"},
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_loop1_waveform_evidence(project: Path, *, unknown: bool = False, wave_rel: str = "output/sim/loop1/wave") -> None:
    report_dir = project / "output" / "reports" / "loop1"
    log_dir = project / "work" / "loop1_rtl_tb" / "current" / "log"
    wave_dir = project / wave_rel
    report_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    wave_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "modelsim.log").write_text(
        "\n".join(
            [
                "Loop1 running TB top: loop1_tb",
                "HDLFLOW_WAVE_BEGIN id=case0 time=10",
                "HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=case0|txn_id=txn_0001|sent=demo|expected=pass|actual=pass|latency_cycles=1|result=PASS",
                "HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|total_tests=1|passed_tests=1|failed_tests=0|total_checks=1|passed_checks=1|failed_checks=0|result=PASS",
                "HDLFLOW_WAVE_END id=case0 time=40",
                "",
            ]
        ),
        encoding="utf-8",
    )
    valid_value = "x#" if unknown else "1#"
    (wave_dir / "loop1_tb.wlf").write_bytes(b"dummy wlf\n")
    (wave_dir / "loop1_tb_top.vcd").write_text(
        "\n".join(
            [
                "$date 2026-05-25 $end",
                "$timescale 1ns $end",
                "$scope module loop1_tb $end",
                "$scope module dut $end",
                "$var wire 1 ! clk $end",
                '$var wire 1 " rst_n $end',
                "$var wire 1 # valid $end",
                "$var wire 8 $ data [7:0] $end",
                "$scope module u_rx $end",
                "$var wire 1 % rx_valid $end",
                "$upscope $end",
                "$upscope $end",
                "$upscope $end",
                "$enddefinitions $end",
                "#0",
                "0!",
                '0"',
                "0#",
                "b00000000 $",
                "0%",
                "#10",
                "1!",
                "#15",
                '1"',
                "#20",
                "0!",
                "#25",
                valid_value,
                "1%",
                "#30",
                "b10101010 $",
                "#35",
                "0#",
                "0%",
                "#40",
                "1!",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_loop1_semantic_waveform_evidence(
    project: Path,
    *,
    unknown: bool = False,
    wave_rel: str = "output/sim/loop1/wave",
) -> None:
    report_dir = project / "output" / "reports" / "loop1"
    log_dir = project / "work" / "loop1_rtl_tb" / "current" / "log"
    config_dir = project / "work" / "loop1_rtl_tb" / "config"
    wave_dir = project / wave_rel
    report_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)
    wave_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "loop1_report.json").write_text(json.dumps({"result": "PASS"}) + "\n", encoding="utf-8")
    (log_dir / "modelsim.log").write_text(
        "\n".join(
            [
                "HDLFLOW|CHECK|schema=hdlflow_event_v1|version=1|stage=loop1|test_id=baseline|txn_id=txn0|sent=start|expected=done|actual=done|latency_cycles=3|result=PASS",
                "HDLFLOW_WAVE_BEGIN id=baseline time=10",
                "HDLFLOW_WAVE_END id=baseline time=90",
                "HDLFLOW|SUMMARY|schema=hdlflow_event_v1|version=1|stage=loop1|total_tests=1|passed_tests=1|failed_tests=0|total_checks=1|passed_checks=1|failed_checks=0|result=PASS",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (config_dir / "top_wave_manifest.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                "dut_scope: /loop1_tb/dut",
                "waveform_format: vcd",
                "dump_policy: top_ports_windowed",
                "max_dump_duration: 1000",
                "max_file_size_mb: 5",
                "clock:",
                "  name: clk",
                "  required: true",
                "reset:",
                "  name: rst_n",
                "  required: true",
                "ports:",
                "  -",
                "    name: clk",
                "    direction: input",
                "    width: 1",
                "    role: clock",
                "  -",
                "    name: rst_n",
                "    direction: input",
                "    width: 1",
                "    role: reset",
                "  -",
                "    name: start",
                "    direction: input",
                "    width: 1",
                "  -",
                "    name: done",
                "    direction: output",
                "    width: 1",
                "windows:",
                "  -",
                "    name: baseline",
                "    signals:",
                "      - clk",
                "      - rst_n",
                "      - start",
                "      - done",
                "    checks:",
                "      - required_ports_present",
                "      - no_xz",
                "      - clock_edges_present",
                "      - input_event_exists",
                "      - output_response_exists",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (wave_dir / "top_ports.wlf").write_bytes(b"dummy wlf\n")
    (wave_dir / "top_ports.vcd").write_text(
        "\n".join(
            [
                "$date 2026-06-15 $end",
                "$timescale 1ns $end",
                "$scope module loop1_tb $end",
                "$scope module dut $end",
                "$var wire 1 ! clk $end",
                '$var wire 1 " rst_n $end',
                "$var wire 1 # start $end",
                "$var wire 1 $ done $end",
                "$upscope $end",
                "$upscope $end",
                "$enddefinitions $end",
                "#0",
                "0!",
                '0"',
                "0#",
                "0$",
                "#10",
                '1"',
                "#20",
                "1!",
                "#30",
                "1#",
                "#40",
                "0!",
                "#50",
                "x$" if unknown else "1$",
                "#60",
                "1!",
                "#80",
                "0#",
                "#90",
                "0!",
                "",
            ]
        ),
        encoding="utf-8",
    )


class _FakePywellenSignal:
    def __init__(self, events: list[tuple[int, object]]):
        self._events = events

    def __iter__(self):
        return iter(self._events)

    def __len__(self) -> int:
        return len(self._events)

    def __getitem__(self, index):
        return self._events[index]


class _FakePywellenVar:
    def __init__(self, full_name: str, size: int, var_type: str, events: list[tuple[int, object]]):
        self.full_name = full_name
        self.name = full_name.rsplit(".", 1)[-1]
        self.size = size
        self.bitwidth = size
        self.length = size
        self.var_type = var_type
        self.type = var_type
        self.tv = _FakePywellenSignal(events)
        self.signal = self.tv


class _FakePywellenWaveform:
    def __init__(self, path: str, *args, **kwargs):
        self.path = path
        self.file_format = "VCD"
        self._vars = _fake_pywellen_vars_for(Path(path))

    def all_vars(self):
        return list(self._vars)


def _fake_pywellen_vars_for(path: Path) -> list[_FakePywellenVar]:
    if path.name == "top_ports.vcd":
        text = path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""
        done_value = "x" if "x$" in text else 1
        return [
            _FakePywellenVar("loop1_tb.dut.clk", 1, "Wire", [(0, 0), (20, 1), (40, 0), (60, 1), (90, 0)]),
            _FakePywellenVar("loop1_tb.dut.rst_n", 1, "Wire", [(0, 0), (10, 1)]),
            _FakePywellenVar("loop1_tb.dut.start", 1, "Wire", [(0, 0), (30, 1), (80, 0)]),
            _FakePywellenVar("loop1_tb.dut.done", 1, "Wire", [(0, 0), (50, done_value)]),
        ]

    text = path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""
    valid_value = "x" if "x#" in text else 1
    return [
        _FakePywellenVar("loop1_tb.dut.clk", 1, "Wire", [(0, 0), (10, 1), (20, 0), (40, 1)]),
        _FakePywellenVar("loop1_tb.dut.rst_n", 1, "Wire", [(0, 0), (15, 1)]),
        _FakePywellenVar("loop1_tb.dut.valid", 1, "Wire", [(0, 0), (25, valid_value), (35, 0)]),
        _FakePywellenVar("loop1_tb.dut.data [7:0]", 8, "Wire", [(0, 0), (30, 0b10101010)]),
        _FakePywellenVar("loop1_tb.dut.u_rx.rx_valid", 1, "Wire", [(0, 0), (25, 1), (35, 0)]),
    ]


def _fake_pywellen_installed():
    module = types.SimpleNamespace(Waveform=_FakePywellenWaveform)
    return mock.patch.dict(sys.modules, {"pywellen": module})


def _create_minimal_uvm_layout(project: Path) -> None:
    for rel in [
        "output/uvm/env",
        "output/uvm/agents/demo",
        "output/uvm/cov",
        "output/uvm/seq_lib",
        "output/uvm/tests",
        "output/uvm/tb",
        "work/loop2_uvm/sim",
    ]:
        (project / rel).mkdir(parents=True, exist_ok=True)
    (project / "work/loop2_uvm" / "sim" / "regression.do").write_text("quit -f\n", encoding="utf-8")


def _create_minimal_uvm_library_db(workspace: Path) -> None:
    db_path = workspace / "lib" / "local" / "library.sqlite"
    db_path.parent.mkdir(parents=True)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.executescript(
            """
            CREATE TABLE library_entries (
                id TEXT PRIMARY KEY,
                kind TEXT,
                domain TEXT,
                title TEXT,
                workflow_id TEXT,
                workflow_node TEXT,
                tool TEXT,
                vendor TEXT,
                stage TEXT,
                short_description TEXT,
                detail_path TEXT,
                tags TEXT,
                source_index TEXT
            );
            CREATE VIRTUAL TABLE uvm_guide_chunks_fts USING fts5(
                chunk_id UNINDEXED,
                doc_id UNINDEXED,
                tool_version UNINDEXED,
                anchor UNINDEXED,
                text
            );
            CREATE TABLE uvm_guide_examples (
                example_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                page INTEGER,
                language_hint TEXT,
                caption TEXT,
                code TEXT
            );
            """
        )
        entries = [
            ("uvm.rkv_style_framework", "template", "uvm", "RKV-style UVM framework template"),
            ("uvm.rkv_i2c_reference_profile", "template", "uvm", "RKV I2C reference profile"),
            ("uvm.methodology_reference", "flow", "uvm", "UVM methodology reference"),
            ("accellera.uvm_users_guide.1_1", "document", "uvm", "Universal Verification Methodology User Guide"),
            ("verification_academy.uvm_cookbook.complete", "document", "uvm", "Verification Academy UVM Cookbook"),
        ]
        for entry_id, kind, domain, title in entries:
            conn.execute(
                """
                INSERT INTO library_entries (
                    id, kind, domain, title, workflow_id, workflow_node, tool,
                    vendor, stage, short_description, detail_path, tags, source_index
                ) VALUES (?, ?, ?, ?, '', '', '', '', '', '', '', '', '')
                """,
                (entry_id, kind, domain, title),
            )
        chunk_text = (
            "uvm_config_db virtual interface uvm agent driver monitor sequencer "
            "uvm_sequence virtual sequence scoreboard analysis port analysis export "
            "functional coverage covergroup monitor sampling uvm_reg_adapter register model bus item"
        )
        conn.execute(
            "INSERT INTO uvm_guide_chunks_fts(chunk_id, doc_id, tool_version, anchor, text) VALUES (?, ?, ?, ?, ?)",
            ("chunk_1", "accellera.uvm_users_guide.1_1", "1.1", "test", chunk_text),
        )
        examples = [
            ("ex_config", "uvm_config_db virtual interface example"),
            ("ex_ap", "uvm_analysis_port scoreboard example"),
            ("ex_seq", "uvm_sequence virtual sequence example"),
            ("ex_reg", "uvm_reg_adapter register model example"),
        ]
        for example_id, code in examples:
            conn.execute(
                "INSERT INTO uvm_guide_examples(example_id, doc_id, page, language_hint, caption, code) VALUES (?, ?, ?, ?, ?, ?)",
                (example_id, "accellera.uvm_users_guide.1_1", 1, "systemverilog", "", code),
            )
        conn.commit()


if __name__ == "__main__":
    unittest.main()
