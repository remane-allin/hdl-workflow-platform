import tempfile
import unittest
from pathlib import Path

from Workflow.core.contracts import ProjectContext
from Workflow.core.execution import _design_invalidation_stage
from Workflow.core.planning import prepare_next
from Workflow.core.review import review_design
from Workflow.tools.filesystem import atomic_write_json


def sample_design():
    return {
        "format_version": 1,
        "design_version": 1,
        "project": {"project_id": "p", "rtl_language": "Verilog-2001", "tool_profile": "xilinx-2024.2"},
        "requirements": {"items": [{"id": "REQ-1", "statement": "pass through", "acceptance": "one case"}]},
        "architecture": {"items": [{
            "id": "ARCH-1", "requirements": ["REQ-1"], "blocks": ["dut"],
            "dataflow": "input to output", "control": "valid handshake",
            "storage": "none", "reuse": "single generic datapath",
        }]},
        "interfaces": {"items": [{
            "id": "IF-1", "name": "stream", "endpoints": ["source", "dut"],
            "direction": "input", "width": 1, "protocol": "valid", "clock": "clk",
            "reset": "active low", "ordering": "in order", "lifecycle": "one transfer",
        }]},
        "implementation": {
            "rtl": {"top": "dut", "sources": ["output/rtl/dut.v"]},
            "constraints": {"sources": []},
            "verification_sources": {"top": "tb_top", "top_file": "output/tb/tb_top.v"},
            "vivado": {"project_name": "p"},
            "vitis": {"enabled": False},
        },
        "budgets": {"items": [{
            "id": "BUD-1", "metric": "lut", "planned": 1,
            "estimate_tolerance_percent": 10, "maximum": 2,
            "evidence_stage": "synth", "requirements": ["REQ-1"],
        }]},
        "verification": {"cases": [{
            "id": "VER-1", "stage": "verify", "requirements": ["REQ-1"],
            "interfaces": ["IF-1"], "stimulus": "drive one bit",
            "oracle": "exact output", "expected": "pass", "key_waves": ["valid"],
        }]},
    }


class DesignReviewTests(unittest.TestCase):
    def test_prepare_next_requires_one_complete_incremented_candidate(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            project = root / "prj" / "p"
            for relative in (
                "output/rtl/dut.v",
                "output/tb/tb_top.v",
                "output/vivado/scripts/project.tcl",
            ):
                path = project / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("module x; endmodule\n", encoding="utf-8")
            current = sample_design()
            current["implementation"]["vivado"].update(
                {"project_script": "output/vivado/scripts/project.tcl", "xpr": "output/vivado/p.xpr"}
            )
            atomic_write_json(project / "input/current/design.json", current)
            candidate = sample_design()
            candidate["design_version"] = 2
            candidate["implementation"]["vivado"].update(
                {"project_script": "output/vivado/scripts/project.tcl", "xpr": "output/vivado/p.xpr"}
            )
            context = ProjectContext(root, "p", project)
            path = prepare_next(context, candidate)
            self.assertTrue(path.is_file())
            prepare_next(context, candidate)
            candidate["design_version"] = 3
            with self.assertRaisesRegex(Exception, "increment"):
                prepare_next(context, candidate)

    def test_route_directive_only_invalidates_route(self):
        previous = sample_design()
        previous["implementation"]["vivado"]["route_directive"] = "Explore"
        current = sample_design()
        current["implementation"]["vivado"]["route_directive"] = "AggressiveExplore"
        self.assertEqual("route", _design_invalidation_stage(previous, current))

    def test_synthesis_constraint_scope_invalidates_synthesis(self):
        previous = sample_design()
        previous["implementation"]["vivado"]["constraints_used_in_synthesis"] = True
        current = sample_design()
        current["implementation"]["vivado"]["constraints_used_in_synthesis"] = False
        self.assertEqual("synth", _design_invalidation_stage(previous, current))

    def test_gate_a_cross_links(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            project = root / "prj" / "p"
            for relative in ("output/rtl/dut.v", "output/tb/tb_top.v"):
                path = project / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("module x; endmodule\n", encoding="utf-8")
            script = project / "output/vivado/scripts/project.tcl"
            script.parent.mkdir(parents=True)
            script.write_text("# project\n", encoding="utf-8")
            data_root = project / "input/sources"
            data_root.mkdir(parents=True)
            candidate = sample_design()
            candidate["implementation"]["vivado"].update(
                {"project_script": "output/vivado/scripts/project.tcl", "xpr": "output/vivado/p.xpr"}
            )
            candidate["implementation"]["verification_sources"]["data_roots"] = ["input/sources"]
            design = project / "input/current/design.json"
            atomic_write_json(design, candidate)
            result = review_design(ProjectContext(root, "p", project))
            self.assertEqual("PASS", result["status"])

    def test_gate_a_rejects_project_identity_mismatch_and_extra_tb_top(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            project = root / "prj" / "p"
            for relative in (
                "output/rtl/dut.v",
                "output/tb/tb_top.v",
                "output/tb/extra_top.v",
                "output/vivado/scripts/project.tcl",
            ):
                path = project / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("module x; endmodule\n", encoding="utf-8")
            candidate = sample_design()
            candidate["project"]["project_id"] = "other"
            candidate["implementation"]["vivado"].update(
                {"project_script": "output/vivado/scripts/project.tcl", "xpr": "output/vivado/p.xpr"}
            )
            design = project / "input/current/design.json"
            atomic_write_json(design, candidate)
            with self.assertRaisesRegex(Exception, "project.project_id.*output/tb"):
                review_design(ProjectContext(root, "p", project))

    def test_gate_a_rejects_reverse_dangling_links(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            project = root / "prj" / "p"
            for relative in (
                "output/rtl/dut.v",
                "output/tb/tb_top.v",
                "output/vivado/scripts/project.tcl",
            ):
                path = project / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("module x; endmodule\n", encoding="utf-8")
            candidate = sample_design()
            candidate["architecture"]["items"][0]["requirements"].append("REQ-MISSING")
            candidate["verification"]["cases"][0]["interfaces"].append("IF-MISSING")
            candidate["implementation"]["vivado"].update(
                {"project_script": "output/vivado/scripts/project.tcl", "xpr": "output/vivado/p.xpr"}
            )
            design = project / "input/current/design.json"
            atomic_write_json(design, candidate)
            with self.assertRaisesRegex(Exception, "unknown requirement.*unknown interface"):
                review_design(ProjectContext(root, "p", project))


if __name__ == "__main__":
    unittest.main()
