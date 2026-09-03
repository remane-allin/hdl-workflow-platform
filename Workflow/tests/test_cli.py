import json
import tempfile
import unittest
from pathlib import Path

from Workflow.core.contracts import ProjectContext
from Workflow.core.execution import run_to
from Workflow.workflow import parser


class CliTests(unittest.TestCase):
    def test_run_requires_target(self):
        value = parser().parse_args(["run", "--project", "p", "--to", "verify"])
        self.assertEqual("verify", value.to)

    def test_extension_commands_stay_on_the_root_parser(self):
        delivery = parser().parse_args(
            ["deliver", "--project", "p", "--message", "release", "--init"]
        )
        self.assertTrue(delivery.init)
        publish = parser().parse_args(
            ["publish-assets", "--project", "p", "--result", "vivado.xsa"]
        )
        self.assertEqual(["vivado.xsa"], publish.result)
        upgrade = parser().parse_args(
            [
                "platform-upgrade", "--candidate", "candidate.json",
                "--project", "p1", "--project", "p2",
            ]
        )
        self.assertEqual(["p1", "p2"], upgrade.project)
        self.assertIsNone(parser().parse_args(["clean"]).project)

    def test_first_design_refresh_starts_from_complete_next(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            workflow_root = Path(temporary) / "Workflow"
            project_root = workflow_root / "prj" / "p"
            (project_root / "input" / "next").mkdir(parents=True)
            (project_root / "output" / "rtl").mkdir(parents=True)
            (project_root / "output" / "tb").mkdir(parents=True)
            (project_root / "output" / "rtl" / "top.v").write_text(
                "`default_nettype none\nmodule top; endmodule\n", encoding="utf-8"
            )
            (project_root / "output" / "tb" / "tb_top.v").write_text(
                "module tb_top; endmodule\n", encoding="utf-8"
            )
            script = project_root / "output" / "vivado" / "scripts" / "project.tcl"
            script.parent.mkdir(parents=True)
            script.write_text("# project\n", encoding="utf-8")
            design = {
                "format_version": 1,
                "design_version": 1,
                "project": {"project_id": "p", "rtl_language": "Verilog-2001"},
                "requirements": {"items": [{"id": "REQ-1", "statement": "pass through"}]},
                "architecture": {"items": [{
                    "id": "ARCH-1", "requirements": ["REQ-1"], "blocks": ["top"],
                    "dataflow": "input to output", "control": "one transfer",
                    "storage": "none", "reuse": "generic pass through",
                }]},
                "interfaces": {"items": [{
                    "id": "IF-1", "name": "stream", "endpoints": ["source", "top"],
                    "direction": "input", "width": 1, "protocol": "valid", "clock": "clk",
                    "reset": "active low", "ordering": "in order", "lifecycle": "one transfer",
                }]},
                "implementation": {
                    "rtl": {"top": "top", "sources": ["output/rtl/top.v"]},
                    "constraints": {"sources": []},
                    "verification_sources": {"top": "tb_top", "top_file": "output/tb/tb_top.v"},
                    "vivado": {
                        "project_script": "output/vivado/scripts/project.tcl",
                        "xpr": "output/vivado/p.xpr",
                    },
                    "vitis": {"enabled": False},
                },
                "budgets": {"items": [{
                    "id": "BUD-1", "metric": "lut", "planned": 1,
                    "estimate_tolerance_percent": 10, "maximum": 2,
                    "evidence_stage": "synth", "requirements": ["REQ-1"],
                }]},
                "verification": {"cases": [{
                    "id": "VER-1", "stage": "verify", "requirements": ["REQ-1"],
                    "interfaces": ["IF-1"], "stimulus": "one bit", "oracle": "exact output",
                    "expected": "pass", "key_waves": ["valid"],
                }]},
            }
            next_path = project_root / "input" / "next" / "design.json"
            next_path.write_text(json.dumps(design), encoding="utf-8")
            context = ProjectContext(workflow_root, "p", project_root)
            state = run_to(context, "design")
            self.assertEqual("PASS", state["stages"]["design"]["status"])
            self.assertTrue(context.design_path.is_file())
            self.assertFalse(next_path.exists())


if __name__ == "__main__":
    unittest.main()
