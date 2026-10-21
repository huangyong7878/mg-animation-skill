"""Task-driven R4 validation does not depend on project-specific IDs."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from studio.r4_runner import validate_assignment, valid_path

class R4StudioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo=Path(self.tmp.name)
        self.path=self.repo/"work/r4_inbox/demo_task/assignment.json"
        self.path.parent.mkdir(parents=True)
        self.task={"schema_version":"1.0","kind":"r4_rework_assignment",
            "status":"approved_for_rework_only",
            "approval":{"approved_by":"Project owner","explicit_cli_authorization":True},
            "project_id":"different_project","spec_sha256":"a"*64,
            "source_implementation_commit":"b"*40,
            "approved_finding_ids":["X-1"],
            "findings":[{"id":"X-1","severity":"P1","fix_request":"fix label","evidence":"frame 1"}],
            "execution_policy":{"allowed_files":["scripts/demo.py"],"max_runtime_seconds":120}}
        self.write()

    def write(self):
        self.path.write_text(json.dumps(self.task))

    def check(self):
        with patch("studio.r4_runner.git",return_value=""):
            return validate_assignment(self.repo,self.path)

    def test_generic_assignment(self):
        self.assertEqual(self.check()["project_id"],"different_project")

    def test_approval_required(self):
        self.task["approval"]["explicit_cli_authorization"]=False
        self.write()
        with self.assertRaisesRegex(ValueError,"Invalid executable"):
            self.check()

    def test_scope_binding(self):
        self.task["approved_finding_ids"]=["X-2"]
        self.write()
        with self.assertRaisesRegex(ValueError,"scope"):
            self.check()

    def test_protected_file_rejected(self):
        self.task["execution_policy"]["allowed_files"]=["work/orders_pilot/voice_lock.json"]
        self.write()
        with self.assertRaisesRegex(ValueError,"Forbidden"):
            self.check()

    def test_path_traversal(self):
        self.assertFalse(valid_path("../scripts/demo.py"))
        self.assertFalse(valid_path("scripts/../../etc/passwd"))
        self.assertTrue(valid_path("scripts/demo.py"))

if __name__=="__main__":
    unittest.main()
