import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from Workflow.core.contracts import ProjectContext
from Workflow.reports.tools.extract import (
    initial_report,
    merge_stage_report,
    parse_xsim_log,
    rebase_report,
    record_failure,
)
from Workflow.tools.filesystem import atomic_write_json
from Workflow.tools.rtl import reliable_rule_findings
from Workflow.tools.knowledge import query, refresh_library
from Workflow.tools.profile import _verify_version
from Workflow.tools.vitis import _vitis_failure
from Workflow.tools.xilinx import _native_run_request


class ReportTests(unittest.TestCase):
    def test_tool_version_probe_is_confined_to_workflow_work(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            with patch(
                "Workflow.tools.profile.subprocess.run",
                return_value=CompletedProcess(["xvlog"], 0, "Vivado Simulator v2024.2", ""),
            ) as run:
                _verify_version(root, "xsim", Path("xvlog.bat"), "2024.2")
            probe_cwd = Path(run.call_args.kwargs["cwd"])
            self.assertTrue(probe_cwd.is_relative_to(root / "work" / "tool" / "environment"))

    def test_vivado_native_run_request_is_exact(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            log = Path(temporary) / "prepare.log"
            log.write_text("Vivado output\nWF_NATIVE_RUN=impl_1\n", encoding="utf-8")
            self.assertEqual("impl_1", _native_run_request(log))
            log.write_text("Vivado output\nWF_NATIVE_RUN=\n", encoding="utf-8")
            self.assertIsNone(_native_run_request(log))

    def test_vivado_project_run_does_not_wait_on_parent_dispatch(self):
        script = Path("Workflow/tools/tcl/vivado_run.tcl").read_text(encoding="utf-8")
        self.assertIn("launch_runs impl_1 -to_step route_design -scripts_only", script)
        self.assertNotIn("wait_on_run", script)

    def test_failure_evidence_replaces_the_previous_failure_atomically(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            project = root / "prj" / "p"
            context = ProjectContext(root, "p", project)
            design = {"design_version": 1}
            staging = project / "output" / "report" / ".staging" / "rtl" / "rtl-tb"
            staging.mkdir(parents=True)
            (staging / "first.log").write_text("first", encoding="utf-8")
            record_failure(context, design, "rtl", "ToolFailure", "first", 1)
            staging.mkdir(parents=True)
            (staging / "second.log").write_text("second", encoding="utf-8")
            record_failure(context, design, "rtl", "ToolFailure", "second", 2)
            failure = project / "output" / "report" / "last-failure" / "rtl" / "rtl-tb"
            self.assertFalse((failure / "first.log").exists())
            self.assertEqual("second", (failure / "second.log").read_text(encoding="utf-8"))
            self.assertFalse((project / "output" / "report" / ".failure-staging").exists())

    def test_empty_release_physical_staging_does_not_delete_route_evidence(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            project = root / "prj" / "p"
            context = ProjectContext(root, "p", project)
            design = {
                "design_version": 1,
                "project": {"tool_profile": "xilinx-2024.2"},
                "implementation": {"rtl": {"sources": ["output/rtl/top.v"]}},
            }
            current = project / "output" / "report" / "current"
            physical = current / "physical"
            physical.mkdir(parents=True)
            (physical / "route_timing.rpt").write_text("timing", encoding="utf-8")
            atomic_write_json(current / "report.json", initial_report(context, design))
            (project / "output" / "report" / ".staging" / "release" / "physical").mkdir(parents=True)
            merge_stage_report(context, design, "release", {"status": "PASS"})
            self.assertEqual("timing", (physical / "route_timing.rpt").read_text(encoding="utf-8"))

    def test_route_only_rebase_keeps_upstream_report_evidence(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            project = root / "prj" / "p"
            context = ProjectContext(root, "p", project)
            current = project / "output" / "report" / "current"
            current.mkdir(parents=True)
            design = {
                "design_version": 2,
                "project": {"tool_profile": "xilinx-2024.2"},
                "implementation": {"rtl": {"sources": ["output/rtl/top.v"]}},
            }
            previous = {
                "context": {"design_version": 1},
                "rtl_tb": {"status": "PASS"},
                "verification": {"status": "PASS"},
                "physical": {"synth": {"status": "PASS"}, "route": {"status": "PASS"}},
                "review": {"gate_a": "PASS", "gate_b": "PASS", "extraction_quality": 1.0},
                "release": {"status": "PASS"},
            }
            (current / "report.json").write_text(json.dumps(previous), encoding="utf-8")
            report = rebase_report(context, design, "route")
            self.assertEqual("PASS", report["rtl_tb"]["status"])
            self.assertEqual("PASS", report["verification"]["status"])
            self.assertEqual("PASS", report["physical"]["synth"]["status"])
            self.assertEqual("NOT_RUN", report["physical"]["route"]["status"])
            self.assertEqual("NOT_RUN", report["release"]["status"])

    def test_knowledge_refresh_replaces_catalog_without_external_paths(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            parsed = root / "knowledge" / "parsed" / "vendor" / "guide" / "2024_2"
            source = root / "knowledge" / "sources" / "vendor" / "2024_2"
            parsed.mkdir(parents=True)
            source.mkdir(parents=True)
            (source / "guide.pdf").write_text("source", encoding="utf-8")
            (parsed / "metadata.json").write_text(
                json.dumps({"doc_id": "vendor.guide.2024_2", "title": "Guide", "tool_version": "2024.2"}),
                encoding="utf-8",
            )
            self.assertEqual(1, refresh_library(root))
            rows = query(root, "Guide", tool_version="2024.2")
            self.assertEqual(1, len(rows))
            self.assertFalse(Path(rows[0]["parsed_path"]).is_absolute())
            (parsed / "metadata.json").unlink()
            self.assertEqual(0, refresh_library(root))
            self.assertEqual([], query(root, "Guide"))

    def test_rtl_style_allows_else_on_line_after_end(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary)
            (root / "good.v").write_text(
                "`default_nettype none\nmodule good;\ninitial begin\nif (1'b1) begin\nend\nelse begin\nend\nend\nendmodule\n",
                encoding="utf-8",
            )
            self.assertEqual([], reliable_rule_findings(root, ["good.v"]))

    def test_rtl_style_rejects_same_line_end_else(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary)
            (root / "bad.v").write_text(
                "`default_nettype none\nmodule bad;\ninitial begin\nif (1'b1) begin\nend else begin\nend\nend\nendmodule\n",
                encoding="utf-8",
            )
            findings = reliable_rule_findings(root, ["bad.v"])
            self.assertTrue(any("else must start" in item for item in findings))

    def test_vitis_traceback_is_failure_even_when_launcher_returns_zero(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            log = Path(temporary) / "vitis.log"
            log.write_text(
                "Traceback (most recent call last):\nAttributeError: invalid component record\n",
                encoding="utf-8",
            )
            self.assertEqual("AttributeError: invalid component record", _vitis_failure(log))

    def test_exact_xsim_contract(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            path = Path(temporary) / "xsim.log"
            path.write_text(
                "WF_INFO|case=VER-1|purpose=identity|input=1|expected=1|actual=1|result=PASS\n"
                "WF_SUMMARY|total=1|pass=1|fail=0\n",
                encoding="utf-8",
            )
            self.assertEqual("PASS", parse_xsim_log(path, ["VER-1"])["status"])

    def test_duplicate_summary_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            path = Path(temporary) / "xsim.log"
            path.write_text("WF_SUMMARY|total=0|pass=0|fail=0\n" * 2, encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_xsim_log(path, [])


if __name__ == "__main__":
    unittest.main()
