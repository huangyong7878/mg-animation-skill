"""R5 Stage C PR-comment 403 recovery: offline/authz regression only."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.r5_av_control import (
    REVIEW_NAME, REVIEW_PATH, selected_saved_review,
    validate_saved_evidence, validated_selection,
)
from workflow.r5_review import sha256

ROOT = Path(__file__).resolve().parents[1]
REPO = "huangyong7878/mg-animation-skill"
SHA = "a" * 40
SELECTION = {
    "source_run_id": 10001,
    "implementation_commit": SHA,
    "pr": 8,
    "source_artifact": f"mg-orders-stagec-draft-10001-{SHA[:12]}",
}
REVIEW_RUN = 20001


class TestManualRecoveryAuthorization(unittest.TestCase):
    def setUp(self):
        self.info = {
            "id": REVIEW_RUN, "name": REVIEW_NAME,
            "path": REVIEW_PATH + "@refs/heads/main",
            "event": "workflow_dispatch",
            "status": "completed",
            "conclusion": "failure",  # original model succeeded, post failed
            "head_branch": "main",
            "repository": {"full_name": REPO},
            "head_repository": {"full_name": REPO},
        }

    def api(self, method, endpoint, payload):
        self.assertEqual(method, "GET")
        self.assertTrue(endpoint.endswith(f"/actions/runs/{REVIEW_RUN}"))
        return self.info

    def test_accepts_review_failed_only_during_comment_publication(self):
        data = selected_saved_review(REPO, str(REVIEW_RUN), SELECTION,
                                     "test-gh-token", self.api)
        self.assertEqual(data["review_run_id"], REVIEW_RUN)
        self.assertEqual(data["review_artifact_name"],
                         f"r5-stagec-av-10001-{SHA}")

    def test_invalid_run_id_never_hits_network(self):
        def forbidden(*args):
            raise AssertionError("Untrusted run ID contacted GitHub")
        for value in ("", "-1", "0", " 20001", "2x", "0" * 25):
            with self.subTest(value=value), self.assertRaises(ValueError):
                selected_saved_review(REPO, value, SELECTION,
                                      "test-gh-token", forbidden)

    def test_wrong_run_cannot_supply_alleged_gemini_report(self):
        cases = [
            ("name", "Unrelated workflow"),
            ("path", ".github/workflows/attack.yml"),
            ("event", "pull_request"),
            ("status", "in_progress"),
            ("conclusion", "cancelled"),
            ("head_branch", "test/r5-review"),
            ("repository", {"full_name": "another/repo"}),
            ("head_repository", {"full_name": "another/fork"}),
        ]
        for key, value in cases:
            with self.subTest(key=key):
                original = self.info[key]
                self.info[key] = value
                try:
                    with self.assertRaisesRegex(ValueError, "trusted completed"):
                        selected_saved_review(REPO, str(REVIEW_RUN),
                                              SELECTION, "token", self.api)
                finally:
                    self.info[key] = original

    def test_recovery_workflow_never_calls_paid_model(self):
        recovery = (ROOT / ".github/workflows/r5-stagec-av-publish-saved.yml").read_text()
        review = (ROOT / ".github/workflows/r5-stagec-av-qa.yml").read_text()
        visual = (ROOT / ".github/workflows/r5-visual-qa.yml").read_text()
        self.assertIn("on:\n  workflow_dispatch:", recovery)
        self.assertNotIn("\n  workflow_run:", recovery)
        self.assertNotIn("\n  pull_request:", recovery)
        self.assertNotIn("\n  push:", recovery)
        self.assertIn("issues: write", recovery)
        self.assertIn("pull-requests: write", recovery)
        self.assertIn("pull-requests: write", review)
        self.assertIn("pull-requests: write", visual)
        self.assertNotIn("secrets.GEMINI_API_KEY", recovery)
        self.assertNotIn("R5_ENABLED", recovery)
        self.assertNotIn("R5_AV_ENABLED", recovery)
        self.assertNotIn("r5_av_review.py \\", recovery)
        self.assertIn("r5_av_control.py --mode select-review", recovery)
        self.assertIn("r5_av_control.py --mode publish", recovery)
        self.assertIn("steps.gate.outputs.should_run == 'true'", recovery)

    def test_recovered_report_rechecks_verified_media_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            v, a = root / "video.mp4", root / "audio.wav"
            v.write_bytes(b"original media video")
            a.write_bytes(b"original media audio")
            spec = {"output": {"duration_s": 13.0}}
            report = {
                "report_kind": "r5_stagec_av",
                "stage": "C", "status": "prototype", "release_approved": False,
                "implementation_commit": SHA, "source_run_id": 10001,
                "source_artifact": SELECTION["source_artifact"],
                "decision": "pass", "audio_evaluated": True,
                "video_evaluated": True, "findings": [],
                "summary": "Original model checked each source media segment.",
                "video_sha256": sha256(v),
                "audio_sha256": sha256(a),
                "checks": [{"segment_id": "intro", "result": "pass"}],
            }
            audit = {
                "provider": "gemini", "model": "gemini-2.5-flash",
                "pr": 8, "source_run_id": 10001,
                "implementation_commit": SHA,
                "source_artifact": SELECTION["source_artifact"],
                "decision": "pass", "video_sha256": sha256(v),
                "audio_sha256": sha256(a),
            }
            with patch("workflow.r5_av_review.verify_inputs") as verified, \
                 patch("workflow.r5_av_review.validate_observations") as validate:
                verified.return_value = (spec, {}, {}, {}, {}, {}, v, a)
                self.assertTrue(validate_saved_evidence(
                    SELECTION, report, audit, root))
                self.assertTrue(verified.called)
                self.assertTrue(validate.called)
                report["audio_sha256"] = "b" * 64
                with self.assertRaisesRegex(ValueError, "original MP4/WAV"):
                    validate_saved_evidence(SELECTION, report, audit, root)
                report["audio_sha256"] = sha256(a)
                audit["provider"] = "untrusted"
                with self.assertRaisesRegex(ValueError, "selected Stage C source"):
                    validate_saved_evidence(SELECTION, report, audit, root)


if __name__ == "__main__":
    unittest.main()
