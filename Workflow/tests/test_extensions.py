import json
import os
import subprocess
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

from Workflow.core.contracts import STAGES, ProjectContext, WorkflowError
from Workflow.core.execution import clean_workflow
from Workflow.core.review import review_design
from Workflow.core.state import initial_state, save_state
from Workflow.tools.assets import publish_release_assets
from Workflow.tools.delivery import create_archive, deliver_git, restore_archive
from Workflow.tools.dispatch import ResourceLease, StageDispatch, _process_is_active
from Workflow.tools.filesystem import atomic_write_json
from Workflow.tools.platform import load_platform, restore_platform, upgrade_platform


def released_project(workflow_root: Path, project_id: str, version: int = 1) -> ProjectContext:
    project = workflow_root / "prj" / project_id
    files = {
        "output/rtl/dut.v": "`default_nettype none\nmodule dut; endmodule\n",
        "output/tb/tb_top.v": "module tb_top; endmodule\n",
        "output/vivado/scripts/project.tcl": "# native project\n",
        "output/vivado/release.dcp": "checkpoint\n",
        "input/sources/vector.hex": "00\n",
    }
    for relative, content in files.items():
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    design = {
        "format_version": 1,
        "design_version": version,
        "project": {
            "project_id": project_id,
            "platform": "test-platform",
            "part": "test-part",
            "rtl_language": "Verilog-2001",
            "tool_profile": "test-tools",
        },
        "requirements": {
            "items": [{"id": "REQ-1", "statement": "pass through", "acceptance": "exact"}]
        },
        "architecture": {
            "items": [{
                "id": "ARCH-1",
                "requirements": ["REQ-1"],
                "blocks": ["dut"],
                "dataflow": "input to output",
                "control": "one transfer",
                "storage": "none",
                "reuse": "one reviewed datapath",
            }]
        },
        "interfaces": {
            "items": [{
                "id": "IF-1",
                "name": "stream",
                "endpoints": ["source", "dut"],
                "direction": "input",
                "width": 1,
                "protocol": "valid",
                "clock": "clk",
                "reset": "active low",
                "ordering": "in order",
                "lifecycle": "one transfer",
            }]
        },
        "implementation": {
            "rtl": {"top": "dut", "sources": ["output/rtl/dut.v"]},
            "constraints": {"sources": []},
            "verification_sources": {
                "top": "tb_top",
                "top_file": "output/tb/tb_top.v",
                "models": [],
                "initialization_files": [{"path": "input/sources/vector.hex"}],
            },
            "vivado": {
                "project_name": project_id,
                "project_script": "output/vivado/scripts/project.tcl",
                "xpr": f"output/vivado/{project_id}.xpr",
                "results": {"checkpoint": "output/vivado/release.dcp"},
            },
            "vitis": {"enabled": False},
        },
        "budgets": {
            "items": [{
                "id": "BUD-1",
                "metric": "lut",
                "planned": 1,
                "estimate_tolerance_percent": 10,
                "maximum": 2,
                "evidence_stage": "synth",
                "requirements": ["REQ-1"],
            }]
        },
        "verification": {
            "cases": [{
                "id": "VER-1",
                "stage": "verify",
                "requirements": ["REQ-1"],
                "interfaces": ["IF-1"],
                "stimulus": "one bit",
                "oracle": "exact output",
                "expected": "pass",
                "key_waves": ["valid"],
            }]
        },
    }
    atomic_write_json(project / "input" / "current" / "design.json", design)
    context = ProjectContext(workflow_root, project_id, project)
    state = initial_state(project_id, version)
    for stage in STAGES:
        state["stages"][stage]["status"] = "PASS"
    save_state(context, state)
    atomic_write_json(
        project / "output" / "report" / "current" / "report.json",
        {
            "context": {"project_id": project_id, "design_version": version},
            "rtl_tb": {"status": "PASS"},
            "verification": {"status": "PASS"},
            "physical": {"synth": {"status": "PASS"}, "route": {"status": "PASS"}},
            "review": {"gate_a": "PASS", "gate_b": "PASS"},
            "release": {"status": "PASS"},
        },
    )
    return context


class ExtensionTests(unittest.TestCase):
    def test_workflow_root_cleanup_removes_only_owned_transients(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            state = root / "prj" / "project" / "work" / "state.json"
            state.parent.mkdir(parents=True)
            state.write_text("{}\n", encoding="utf-8")
            with ResourceLease(root, "vivado", 1, "project", "route"):
                with self.assertRaisesRegex(WorkflowError, "resource leases exist"):
                    clean_workflow(root)
            for relative in (
                ".omx/state.json",
                "log/session.log",
                "work/tool/probe.log",
                "xsim.dir/run.bin",
                "xelab.log",
                "xelab.pb",
                "xvlog.log",
                "xvlog.pb",
                "vivado.jou",
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("transient\n", encoding="utf-8")
            removed = clean_workflow(root)
            self.assertEqual(
                {
                    ".omx", "log", "work", "xsim.dir", "xelab.log", "xelab.pb",
                    "xvlog.log", "xvlog.pb", "vivado.jou",
                },
                set(removed),
            )
            self.assertTrue(state.is_file())

    def test_cross_project_asset_requires_a_matching_release(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            source = released_project(root, "source", 2)
            consumer = released_project(root, "consumer", 1)
            publish_release_assets(source, ["vivado.checkpoint"])
            design_path = consumer.design_path
            design = json.loads(design_path.read_text(encoding="utf-8"))
            design["implementation"]["reuse_assets"] = [{
                "id": "ASSET-PLATFORM",
                "kind": "platform",
                "source_project": "source",
                "source_design_version": 2,
                "source_path": "output/release/assets/vivado-checkpoint.dcp",
                "purpose": "reuse the released integration platform contract",
            }]
            atomic_write_json(design_path, design)
            for mutable in (source.project_root / "work", source.project_root / "output" / "report" / "current"):
                for path in sorted(mutable.rglob("*"), reverse=True):
                    path.unlink() if path.is_file() else path.rmdir()
                mutable.rmdir()
            result = review_design(consumer)
            self.assertEqual("PASS", result["status"])
            self.assertEqual(
                "prj/source/output/release/assets/vivado-checkpoint.dcp",
                result["resolved_assets"][0]["source"],
            )
            self.assertFalse((consumer.project_root / "output" / "release").exists())
            (source.project_root / "output" / "release" / "assets" / "vivado-checkpoint.dcp").unlink()
            with self.assertRaisesRegex(Exception, "is missing"):
                review_design(consumer)

            design["implementation"]["reuse_assets"][0].pop("kind")
            atomic_write_json(design_path, design)
            with self.assertRaisesRegex(Exception, "unsupported kind"):
                review_design(consumer)

    def test_resource_conflict_blocks_and_release_leaves_no_state(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            self.assertTrue(_process_is_active(os.getpid()))
            with ResourceLease(root, "vivado", 1, "p1", "route"):
                with self.assertRaisesRegex(WorkflowError, "resource unavailable"):
                    with ResourceLease(root, "vivado", 1, "p2", "synth"):
                        pass
            self.assertFalse((root / "work").exists())
            with self.assertRaises(KeyboardInterrupt):
                with ResourceLease(root, "vivado", 1, "p1", "route"):
                    raise KeyboardInterrupt
            self.assertFalse((root / "work").exists())

            context = released_project(root, "project")
            design = json.loads(context.design_path.read_text(encoding="utf-8"))
            with self.assertRaisesRegex(WorkflowError, "unsupported dispatch stage"):
                StageDispatch(context, design, "unknown")

    def test_git_delivery_commits_only_release_paths(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            context = released_project(root, "project")
            unrelated = context.project_root / "notes.tmp"
            unrelated.write_text("not approved\n", encoding="utf-8")
            cache = context.project_root / "output" / "vivado" / "project.runs" / "synth_1" / "cache.bin"
            cache.parent.mkdir(parents=True)
            cache.write_text("cache\n", encoding="utf-8")
            (context.project_root / "output" / "vivado" / "vivado.log").write_text(
                "log\n", encoding="utf-8"
            )
            result = deliver_git(
                context,
                "local release",
                initialize=True,
                tag="release-test",
            )
            self.assertTrue(result["committed"])
            listed = subprocess.run(
                ["git", "-C", str(context.project_root), "ls-files"],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=True,
            ).stdout.splitlines()
            self.assertNotIn("notes.tmp", listed)
            self.assertNotIn("work/state.json", listed)
            self.assertNotIn("output/vivado/project.runs/synth_1/cache.bin", listed)
            self.assertNotIn("output/vivado/vivado.log", listed)
            self.assertIn("input/current/design.json", listed)
            tags = subprocess.run(
                ["git", "-C", str(context.project_root), "tag", "--list"],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=True,
            ).stdout.splitlines()
            self.assertEqual(["release-test"], tags)

            subprocess.run(
                ["git", "-C", str(context.project_root), "add", "notes.tmp"],
                check=True,
            )
            (context.project_root / "README.md").write_text("approved release note\n", encoding="utf-8")
            second = deliver_git(context, "second local release")
            self.assertTrue(second["committed"])
            committed_files = subprocess.run(
                ["git", "-C", str(context.project_root), "show", "--name-only", "--format="],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=True,
            ).stdout.splitlines()
            self.assertEqual(["README.md"], committed_files)
            staged_files = subprocess.run(
                ["git", "-C", str(context.project_root), "diff", "--cached", "--name-only"],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=True,
            ).stdout.splitlines()
            self.assertEqual(["notes.tmp"], staged_files)
            # Git for Windows can retain a transient handle after the subprocess exits.
            time.sleep(0.2)

    def test_archive_restores_without_state_and_rejects_a_missing_file(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            context = released_project(root, "project")
            archive = root / "archives" / "project.zip"
            result = create_archive(context, archive)
            self.assertEqual("PASS", result["status"])
            target = root / "restore" / "project"
            restored = restore_archive(root, archive, target)
            self.assertFalse(restored["state_restored"])
            self.assertTrue((target / "input/current/design.json").is_file())
            self.assertFalse((target / "work").exists())
            self.assertFalse((target / "_archive").exists())

            broken = root / "archives" / "broken.zip"
            with zipfile.ZipFile(archive, "r") as source, zipfile.ZipFile(broken, "w") as output:
                for item in source.infolist():
                    if item.filename != "input/current/design.json":
                        output.writestr(item, source.read(item.filename))
            with self.assertRaisesRegex(Exception, "missing or incomplete"):
                restore_archive(root, broken, root / "restore" / "broken")
            self.assertFalse((root / "restore" / "broken").exists())

            extra = root / "archives" / "extra.zip"
            with zipfile.ZipFile(archive, "r") as source, zipfile.ZipFile(extra, "w") as output:
                for item in source.infolist():
                    output.writestr(item, source.read(item.filename))
                output.writestr("unexpected.log", "not declared\n")
            with self.assertRaisesRegex(Exception, "outside its manifest"):
                restore_archive(root, extra, root / "restore" / "extra")
            self.assertFalse((root / "restore" / "extra").exists())

    def test_platform_upgrade_rotates_one_recovery_point(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            root.mkdir(parents=True)
            (root / "workflow.py").write_text("# entry\n", encoding="utf-8")
            profile = root / "tools" / "tool-profiles.json"
            profile.parent.mkdir(parents=True)
            profile.write_text("{}\n", encoding="utf-8")
            released_project(root, "p1")
            released_project(root, "p2")
            base = {
                "format_version": 1,
                "platform_version": 1,
                "product": "Workflow",
                "host": "Windows-PowerShell-7",
                "entry": "workflow.py",
                "tool_profile": "tools/tool-profiles.json",
            }
            atomic_write_json(root / "platform.json", base)
            candidate = dict(base)
            candidate["platform_version"] = 2
            candidate_path = root / "work" / "candidate.json"
            atomic_write_json(candidate_path, candidate)
            original = (root / "platform.json").read_bytes()
            with self.assertRaisesRegex(WorkflowError, "at least two distinct"):
                upgrade_platform(root, candidate_path, ["p1"])
            self.assertEqual(original, (root / "platform.json").read_bytes())
            self.assertFalse((root / "platform.previous.json").exists())
            upgraded = upgrade_platform(root, candidate_path, ["p1", "p2"])
            self.assertEqual(2, upgraded["platform_version"])
            self.assertEqual("workflow.py", upgraded["entry"])
            self.assertEqual(["p1", "p2"], [item["baseline_id"] for item in upgraded["baselines"]])
            self.assertEqual(1, json.loads((root / "platform.previous.json").read_text())["platform_version"])
            restored = restore_platform(root, ["p1", "p2"])
            self.assertEqual(1, restored["platform_version"])
            self.assertEqual(2, load_platform(root)["platform_version"] + 1)


if __name__ == "__main__":
    unittest.main()
