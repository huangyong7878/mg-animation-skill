"""MG Studio R4 runner authorization tests, no real Codex calls."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from studio.r4_runner import validate_assignment

class R4StudioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.path = self.repo / "work/r4_inbox/pilot001_v3/assignment.json"
        self.path.parent.mkdir(parents=True)
        ids = ["V2-P1-001","V2-P1-002","V2-P2-001",
               "V2-P2-002","V2-P2-003","V2-P2-004"]
        self.task = {
            "kind": "r4_rework_assignment", "status": "approved_for_rework_only",
            "approval": {"explicit_cli_authorization": True},
            "approved_finding_ids": ids,
            "findings": [{"id": i} for i in ids],
            "source_implementation_commit": "32e4ffbc676ed4c2a379d528a7f0e2632a4490ec",
            "production_lock_hashes": {
                "script_lock_digest": "a"*64, "voice_lock_digest": "b"*64}}
        self.write()

    def write(self):
        self.path.write_text(json.dumps(self.task))

    def check(self):
        with patch("studio.r4_runner._git", return_value=""):
            return validate_assignment(self.repo, self.path)

    def test_valid_assignment(self):
        self.assertEqual(len(self.check()["findings"]),6)

    def test_disallowed_scope(self):
        self.task["approved_finding_ids"].pop()
        self.write()
        with self.assertRaisesRegex(ValueError,"scope"):
            self.check()

    def test_missing_explicit_authorization(self):
        self.task["approval"]["explicit_cli_authorization"] = False
        self.write()
        with self.assertRaisesRegex(ValueError,"authorization"):
            self.check()

    def test_source_commit_must_match(self):
        self.task["source_implementation_commit"]="e"*40
        self.write()
        with self.assertRaisesRegex(ValueError,"source commit"):
            self.check()

    def test_only_fixed_assignment_path(self):
        with self.assertRaisesRegex(ValueError,"Only the approved"):
            validate_assignment(self.repo, self.repo/"random.json")

if __name__=="__main__":
    unittest.main()
