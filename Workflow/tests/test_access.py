import tempfile
import unittest
from pathlib import Path

from Workflow.core.access import authorize_project_write, discover_project
from Workflow.core.contracts import GateError


class AccessTests(unittest.TestCase):
    def test_project_and_gate_boundaries(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            (root / "prj" / "p1" / "output" / "rtl").mkdir(parents=True)
            (root / "prj" / "p2").mkdir()
            context = discover_project(root, "p1")
            with self.assertRaises(GateError):
                authorize_project_write(
                    context, context.project_root / "output" / "rtl" / "x.v",
                    gate_a_passed=False,
                )
            with self.assertRaises(GateError):
                authorize_project_write(
                    context, root / "prj" / "p2" / "x.v", gate_a_passed=True
                )
            with self.assertRaisesRegex(GateError, "stage"):
                authorize_project_write(
                    context, context.project_root / "output" / "rtl" / "x.v",
                    gate_a_passed=True,
                )
            with self.assertRaisesRegex(GateError, "cannot write"):
                authorize_project_write(
                    context, context.project_root / "output" / "rtl" / "x.v",
                    gate_a_passed=True,
                    stage="route",
                )
            self.assertTrue(authorize_project_write(
                context, context.project_root / "output" / "rtl" / "x.v",
                gate_a_passed=True,
                stage="rtl",
            ).is_absolute())

    def test_invalid_project_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            with self.assertRaises(GateError):
                discover_project(Path(temporary), "../escape")


if __name__ == "__main__":
    unittest.main()
