import tempfile
import unittest
from pathlib import Path

from Workflow.core.contracts import ProjectContext
from Workflow.core.state import (
    initial_state,
    load_state,
    note_attempt_failure,
    rebase_state,
    recover_state,
    save_state,
    set_stage,
    status_view,
    validate_state,
)


class StateTests(unittest.TestCase):
    def test_state_without_attempts_is_not_silently_upgraded(self):
        state = initial_state("p", 1)
        del state["attempts"]
        with self.assertRaisesRegex(Exception, "attempts"):
            validate_state(state)

    def test_only_four_states_and_downstream_invalidation(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            project = root / "prj" / "p"
            project.mkdir(parents=True)
            context = ProjectContext(root, "p", project)
            state = initial_state("p", 1)
            save_state(context, state)
            state = set_stage(context, state, "design", "PASS")
            state = set_stage(context, state, "rtl", "PASS")
            state = set_stage(context, state, "design", "FAIL")
            self.assertEqual("NOT_RUN", state["stages"]["rtl"]["status"])
            self.assertEqual(state, load_state(context, design_version=1))

    def test_route_only_design_change_keeps_expensive_upstream_evidence(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            project = root / "prj" / "p"
            project.mkdir(parents=True)
            context = ProjectContext(root, "p", project)
            state = initial_state("p", 1)
            for stage in ("design", "rtl", "verify", "synth"):
                state = set_stage(context, state, stage, "PASS", summary=stage)
            state = rebase_state(context, state, 2, "route")
            self.assertEqual(2, state["design_version"])
            self.assertEqual("NOT_RUN", state["stages"]["design"]["status"])
            self.assertEqual("PASS", state["stages"]["rtl"]["status"])
            self.assertEqual("PASS", state["stages"]["verify"]["status"])
            self.assertEqual("PASS", state["stages"]["synth"]["status"])
            self.assertEqual("NOT_RUN", state["stages"]["route"]["status"])
            self.assertEqual("NOT_RUN", state["stages"]["release"]["status"])

    def test_recovery_reads_the_requested_design_version(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            project = root / "prj" / "p"
            project.mkdir(parents=True)
            context = ProjectContext(root, "p", project)
            state = initial_state("p", 4)
            state["stages"]["design"]["status"] = "PASS"
            save_state(context, state)
            recovered = recover_state(context, 4)
            self.assertEqual(4, recovered["design_version"])
            self.assertEqual("PASS", recovered["stages"]["design"]["status"])

    def test_attempt_counter_resets_only_after_pass_or_invalidating_design_change(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            project = root / "prj" / "p"
            project.mkdir(parents=True)
            context = ProjectContext(root, "p", project)
            state = initial_state("p", 1)
            save_state(context, state)
            state, attempt = note_attempt_failure(context, state, "route")
            self.assertEqual(1, attempt)
            state = rebase_state(context, state, 2, "route")
            self.assertEqual(0, state["attempts"]["route"])
            state, _ = note_attempt_failure(context, state, "rtl")
            state = set_stage(context, state, "rtl", "PASS")
            self.assertEqual(0, state["attempts"]["rtl"])

    def test_status_view_reports_elapsed_time_and_next_action(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary) / "Workflow"
            project = root / "prj" / "p"
            report = project / "output" / "report" / "current"
            report.mkdir(parents=True)
            context = ProjectContext(root, "p", project)
            state = initial_state("p", 1)
            state["stages"]["design"]["status"] = "PASS"
            (report / "flow.log").write_text(
                "time=2026-09-03T00:00:00+00:00|design_version=1|stage=design|action=execute|parameters=|status=START\n"
                "time=2026-09-03T00:00:02+00:00|design_version=1|stage=design|action=execute|parameters=|status=PASS\n",
                encoding="utf-8",
            )
            view = status_view(context, state)
            self.assertEqual(2.0, view["stages"]["design"]["elapsed_seconds"])
            self.assertEqual("run --to rtl", view["next_legal_action"])


if __name__ == "__main__":
    unittest.main()
