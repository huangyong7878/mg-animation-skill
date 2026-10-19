"""Regression checks for the multi-model role prompts and runnable manual."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "MULTI_MODEL_PLAYBOOK.md"


class MultiModelPlaybookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = DOC.read_text(encoding="utf-8")

    def test_all_eight_roles_and_handoff_outputs_documented(self):
        for role in ("R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7"):
            self.assertRegex(self.text, rf"(?m)^## [0-9]+\. {role} ")
        for output in ("storyboard.md", "director_spec.json", "director_notes.md",
                       "delivery.json", "media_manifest.json", "qa_report.json",
                       "rework_task.md"):
            self.assertIn(output, self.text)

    def test_actual_cli_entrypoints_are_present(self):
        for path in ("workflow/orchestrator.py", "workflow/role_pack.py",
                     "workflow/check_handoff.py", "workflow/media_manifest.py",
                     "scripts/render.py", "scripts/contract_check.py",
                     "scripts/validate.py", "scripts/factcheck.py"):
            self.assertTrue((ROOT / path).is_file(), path)
            self.assertIn(path, self.text)

    def test_role_pack_and_orchestrator_subcommands_are_covered(self):
        for command in ("director", "qa", "rework"):
            self.assertIn("workflow/role_pack.py " + command, self.text)
        for command in ("prepare", "publish", "receive", "review-package",
                        "record-qa", "feedback", "status", "release-check"):
            self.assertIn("workflow/orchestrator.py " + command, self.text)

    def test_safety_and_media_handoff_present(self):
        for concept in ("pending", "GitHub Actions", "implementation_commit",
                        "spec_sha256", "两轮", "Issue #4", "PR #7",
                        "af17e46", "d780dac4", "ffprobe",
                        "不进 Git", "source_paths"):
            self.assertIn(concept, self.text)
        self.assertGreaterEqual(self.text.count("~~~text"), 7)


if __name__ == "__main__":
    unittest.main()
