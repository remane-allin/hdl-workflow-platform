import os
import json
import tempfile
import unittest
from pathlib import Path

from hdlflow.cli import _tool_launcher_value
from hdlflow.design_doc import check_design_document, generate_design_document
from hdlflow.gates import _loop2_coverage_triage_check, _loop3_serial_echo_check
from hdlflow.prototype import _check_prototype_mode_intent, _is_placeholder
from hdlflow.simple_yaml import parse_yaml
from hdlflow.state_sync import sync_project_state


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
            (project / "01_DocParse" / "prototype").mkdir(parents=True)
            (project / "01_DocParse" / "prototype" / "prototype_plan.yaml").write_text(
                "assumptions:\n  - Prototype uses pure PL resources.\n",
                encoding="utf-8",
            )
            errors = []
            warnings = []

            _check_prototype_mode_intent(project, "ps_pl", {}, errors, warnings)

            self.assertTrue(any("mode conflict" in item for item in errors))


class Loop2RiskGateTests(unittest.TestCase):
    def test_unclassified_coverage_triage_blocks_loop2_closure(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            check = _loop2_coverage_triage_check(
                project,
                "| pl_uart_rx.v toggle | 70.0% | Classify as missing legal stimulus, unreachable-by-spec, or waiver before Loop2 closure. |",
            )

            self.assertEqual(check.status, "FAIL")
            self.assertEqual(check.name, "loop2_coverage_triage_closed")


class Loop3RiskGateTests(unittest.TestCase):
    def test_serial_echo_requires_matching_payload_and_raw_rx_log(self):
        validation = "\n".join(
            [
                "# COM3 UART Loopback Validation",
                "- TX[2026-05-18 16:51:07.517]：HDLFLOW_UART_LOOP3",
                "- RX[2026-05-18 16:51:07.518]：HDLFLOW_UART_LOOP3",
                "- result: PASS",
            ]
        )
        raw = "RX[2026-05-18 16:51:07.518]：HDLFLOW_UART_LOOP3"

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
        raw = "RX[2026-05-18 16:51:07.518]：OTHER"

        check = _loop3_serial_echo_check(validation, raw)

        self.assertEqual(check.status, "FAIL")


class DesignDocTests(unittest.TestCase):
    def test_generate_design_doc_tracks_rtl_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            rtl_dir = project / "05_Output" / "rtl"
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

            result = generate_design_document(project)
            self.assertTrue(result.ok)
            self.assertTrue(result.report_path.exists())
            self.assertTrue(result.manifest_path.exists())

            text = result.report_path.read_text(encoding="utf-8")
            self.assertIn("## 1. 需求分析与系统设计", text)
            self.assertIn("## 2. RTL 设计说明", text)
            self.assertIn("`demo_top`", text)

            check = check_design_document(project, sections=["requirements", "rtl", "uvm", "fpga"])
            self.assertTrue(check.ok)


class StateSyncTests(unittest.TestCase):
    def test_sync_marks_loop2_passed_from_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "00_SPEC_develop_20260517000001.json").write_text("{}", encoding="utf-8")
            (manifest_dir / "01_DocParse_develop_20260517000101.json").write_text("{}", encoding="utf-8")
            (manifest_dir / "02_Loop1_RTL_TB_develop_20260517010101.json").write_text("{}", encoding="utf-8")
            (manifest_dir / "03_Loop2_UVM_Verify_develop_20260517020202.json").write_text("{}", encoding="utf-8")
            report_dir = project / "05_Output" / "reports" / "loop2"
            report_dir.mkdir(parents=True)
            (report_dir / "coverage_index.md").write_text("legal_scenario_cg=100.0\nAggregate | 83.2%\n", encoding="utf-8")

            result = sync_project_state(project)

            self.assertEqual(result.overall_status, "loop2_passed")
            self.assertEqual(result.current_loop, "loop3")
            gate_status = json.loads((project / "loop" / "gate_status.json").read_text(encoding="utf-8"))
            self.assertEqual(gate_status["loop2_exit"], "pass")

    def test_latest_failed_gate_overrides_older_pass_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "00_SPEC_develop_20260517000001.json").write_text("{}", encoding="utf-8")
            (manifest_dir / "01_DocParse_develop_20260517000101.json").write_text("{}", encoding="utf-8")
            (manifest_dir / "02_Loop1_RTL_TB_develop_20260517010101.json").write_text("{}", encoding="utf-8")
            (manifest_dir / "03_Loop2_UVM_Verify_develop_20260517020202.json").write_text("{}", encoding="utf-8")
            gate_dir = project / "05_Output" / "reports" / "gates"
            gate_dir.mkdir(parents=True)
            (gate_dir / "03_Loop2_UVM_Verify_develop_20260517030303.md").write_text("- result: FAIL\n", encoding="utf-8")

            result = sync_project_state(project)

            self.assertEqual(result.overall_status, "loop2_blocked")
            self.assertEqual(result.failed_nodes, ["03_Loop2_UVM_Verify"])
            gate_status = json.loads((project / "loop" / "gate_status.json").read_text(encoding="utf-8"))
            self.assertEqual(gate_status["loop2_exit"], "fail")
            task_board = json.loads((project / "loop" / "task_board.json").read_text(encoding="utf-8"))
            criteria = {item["id"]: item["status"] for item in task_board["done_criteria"]}
            self.assertEqual(criteria["loop2-uvm-pass"], "blocked")

    def test_sync_records_loop3_vivado_and_board_evidence_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _create_minimal_project(project)
            manifest_dir = project / "memory" / "recovery" / "rollback_manifests"
            manifest_dir.mkdir(parents=True)
            for node in [
                "00_SPEC",
                "01_DocParse",
                "02_Loop1_RTL_TB",
                "03_Loop2_UVM_Verify",
                "04_Loop3_FPGA_Prototype",
            ]:
                (manifest_dir / f"{node}_develop_20260517000001.json").write_text("{}", encoding="utf-8")
            vivado_report = project / "05_Output" / "fpga" / "vivado" / "reports" / "pure_pl_uart_led_proto_run.md"
            board_report = project / "05_Output" / "reports" / "loop3" / "serial" / "latest_serial_validation_report.md"
            vivado_report.parent.mkdir(parents=True)
            board_report.parent.mkdir(parents=True)
            vivado_report.write_text("result: PASS\n", encoding="utf-8")
            board_report.write_text("- result: PASS\n", encoding="utf-8")

            result = sync_project_state(project)

            self.assertEqual(result.overall_status, "loop3_passed")
            loop3_state = json.loads((project / "loop" / "loop3_state.json").read_text(encoding="utf-8"))
            self.assertEqual(loop3_state["latest_vivado_report"], "05_Output/fpga/vivado/reports/pure_pl_uart_led_proto_run.md")
            self.assertEqual(loop3_state["latest_board_log"], "05_Output/reports/loop3/serial/latest_serial_validation_report.md")


def _create_minimal_project(project: Path) -> None:
    project.mkdir(parents=True)
    (project / "05_Output").mkdir()
    (project / "loop").mkdir()
    (project / "project_scaffold.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                f"project: {project.name}",
                "creation_mode: script_only",
                "template_source: templates/project",
                "manual_project_directory_creation: forbidden",
                "created_by: unittest",
                "created_at: 2026-05-17T00:00:00",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (project / "loop" / "task_board.json").write_text(
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


if __name__ == "__main__":
    unittest.main()
