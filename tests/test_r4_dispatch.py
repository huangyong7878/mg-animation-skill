"""Test R0-approved dispatch from genuine source-bound R5 candidates."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from workflow.r4_dispatch import dispatch

def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base/"r0"
        self.root.mkdir()
        self.artifact = base/"media"
        (self.artifact/"media").mkdir(parents=True)
        self.video = self.artifact/"media"/"stage_d_final.mp4"
        self.video.write_bytes(b"original stage d bytes")
        self.inbox = base/"r4"/"v3"
        self.spec = {"revision": 1}
        self.state = {"status":"review_pending", "project_id":"orders_two_routes",
                      "spec_id":"orders_shot_001","spec_revision":1,
                      "spec_sha256":"a"*64,"production_mode":"formal",
                      "production_lock_hashes":{"script_lock_digest":"b"*64,
                                                "voice_lock_digest":"c"*64}}
        write(self.root/"delivery.json",{"implementation_commit":"d"*40,
              "artifacts":{"video_path":"media/stage_d_final.mp4"}})
        finding={"id":"p1-01","severity":"P1","shot_id":"shot_01",
                 "expected":"readable badge","observed":"small badge",
                 "fix_request":"move badge","evidence":"frame 18"}
        candidate={"spec_sha256":"a"*64,"implementation_commit":"d"*40,
                   "video_sha256":sha(self.video),"findings":[finding]}
        self.candidate=self.root/"r5_deepseek"/"findings_candidate.json"
        write(self.candidate,candidate)
        task={"status":"draft_unverified", "source_candidate_sha256":sha(self.candidate),
              "spec_sha256":"a"*64,"implementation_commit":"d"*40,
              "spec_revision":1,"video_sha256":sha(self.video),"findings":[finding]}
        self.task=self.root/"r4_rework_draft"/"rework_task_candidate.json"
        write(self.task,task)

    def go(self, **kwargs):
        args={"selected_ids":["p1-01"],"approved_by":"Project owner",
              "inbox":self.inbox,"artifact_root":self.artifact}
        args.update(kwargs)
        with patch("workflow.orchestrator.load_state",
                   return_value=(self.root,self.state,self.spec)):
            return dispatch(self.root,**args)

    def test_selective_dispatch_does_not_change_r0_state(self):
        result=self.go()
        self.assertEqual(result["status"],"dispatched_for_rework")
        assignment=json.loads((self.inbox/"assignment.json").read_text())
        self.assertEqual(assignment["approved_finding_ids"],["p1-01"])
        self.assertEqual(assignment["status"],"approved_for_rework_only")
        self.assertEqual(self.state["status"],"review_pending")

    def test_requires_explicit_ids(self):
        with self.assertRaises(ValueError):
            self.go(selected_ids=[])

    def test_rejects_tampered_findings(self):
        x=json.loads(self.task.read_text())
        x["findings"][0]["fix_request"]="change script"
        write(self.task,x)
        with self.assertRaisesRegex(ValueError,"differ from R5 evidence"):
            self.go()

    def test_rejects_changed_video(self):
        self.video.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError,"source MP4"):
            self.go()

    def test_rejects_unapproved_state(self):
        self.state["status"]="qa_passed"
        with self.assertRaisesRegex(ValueError,"review_pending"):
            self.go()

    def test_no_duplicate_issue_or_inbox(self):
        self.go()
        with self.assertRaisesRegex(ValueError,"exists"):
            self.go()

    def test_dry_run_no_side_effects(self):
        result=self.go(dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertFalse(self.inbox.exists())

if __name__ == "__main__":
    unittest.main()
