"""R5 -> R0 approval requires explicit scope; does not invoke Codex."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from studio.rework_approval import approve,candidates,recommended_files

class R5ReworkApprovalTests(unittest.TestCase):
    def test_project_file_recommendation(self):
        self.assertEqual(recommended_files("orders_two_routes"), [
            "scripts/primitives/orderflow.py",
            "tests/test_pilot001_visual_fix.py"])
        self.assertEqual(recommended_files("unknown_project"), [])

    def test_no_runs(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(candidates(Path(d)),[])

    def test_path_and_selection_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            repo=Path(d)
            run=repo/"work/mg_studio/r5_runs/review_0123456789abcdef"
            run.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError,"Invalid inbox"):
                approve(repo,run_id=run.name,selected_ids=["x"],
                        allowed_files=["scripts/demo.py"],approved_by="Project owner",inbox_id="../bad")
            with self.assertRaisesRegex(ValueError,"valid editable files"):
                approve(repo,run_id=run.name,selected_ids=["x"],
                        allowed_files=["work/orders_pilot/voice_lock.json"],
                        approved_by="Project owner",inbox_id="valid_task")
            with self.assertRaisesRegex(ValueError,"project-owner"):
                approve(repo,run_id=run.name,selected_ids=["x"],
                        allowed_files=["scripts/demo.py"],approved_by="unknown",inbox_id="valid_task")

if __name__=="__main__":
    unittest.main()
