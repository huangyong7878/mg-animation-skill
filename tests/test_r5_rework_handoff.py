"""R5 findings -> R0 draft R4 task; no real paid model calls."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.r5_rework import prepare_rework


class ReworkHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "r0"
        self.root.mkdir()
        self.artifact = self.base / "stage_d"
        self.artifact.mkdir()
        (self.artifact / "media").mkdir()
        self.video = self.artifact / "media" / "stage_d_final.mp4"
        self.video.write_bytes(b"mock-media-for-hash-binding")
        self.spec = {"project_id": "orders_two_routes", "spec_id": "orders_shot_001",
                     "revision": 1, "shots": [{"id": "shot_01"}]}
        self.state = {"status": "review_pending", "spec_sha256": "a" * 64,
                      "implementation_commit": "b" * 40}
        (self.root / "delivery.json").write_text(json.dumps({
            "implementation_commit": "b" * 40,
            "artifacts": {"video_path": "media/stage_d_final.mp4"}}))
        self.candidate = self.base / "findings.json"
        self.payload = {
            "schema_version": "1.0", "scope": "sampled_frames_only",
            "spec_sha256": "a" * 64, "implementation_commit": "b" * 40,
            "video_sha256": hashlib.sha256(self.video.read_bytes()).hexdigest(),
            "findings": [{
                "id": "p1-contrast", "severity": "P1", "shot_id": "shot_01",
                "timestamp_s": 9.0, "expected": "B status legible",
                "observed": "Status blends into subtitle",
                "evidence": "frame18 at 9.0s", "fix_request": "move badge upward"
            }],
        }

    def run_draft(self):
        self.candidate.write_text(json.dumps(self.payload), encoding="utf-8")
        with patch("workflow.orchestrator.load_state",
                   return_value=(self.root, self.state, self.spec)):
            return prepare_rework(self.root, self.candidate, self.artifact)

    def test_creates_source_bound_draft_only(self):
        r = self.run_draft()
        self.assertEqual(r["status"], "draft_unverified")
        task = json.loads(Path(r["task_json"]).read_text())
        self.assertEqual(task["video_sha256"], self.payload["video_sha256"])
        self.assertTrue(task["requires_human_evidence_review"])
        self.assertFalse(task["audio_reviewed"])
        self.assertFalse(task["full_motion_reviewed"])
        self.assertEqual(self.state["status"], "review_pending")
        self.assertFalse((self.root / "qa_report.json").exists())

    def test_stale_commit_refused(self):
        self.payload["implementation_commit"] = "c" * 40
        with self.assertRaisesRegex(ValueError, "stale implementation"):
            self.run_draft()

    def test_wrong_video_refused(self):
        self.payload["video_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "video hash mismatch"):
            self.run_draft()

    def test_duplicate_findings_refused(self):
        self.payload["findings"].append(dict(self.payload["findings"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.run_draft()

    def test_refuses_overwrite(self):
        self.run_draft()
        with self.assertRaisesRegex(ValueError, "overwrite"):
            self.run_draft()

    def test_parser_exposes_rework_draft(self):
        from workflow.orchestrator import build_parser
        p = build_parser()
        a = p.parse_args(["rework-draft", "--workdir", "w", "--findings", "f",
                          "--artifact-root", "a"])
        self.assertEqual(a.command, "rework-draft")


if __name__ == "__main__":
    unittest.main()
