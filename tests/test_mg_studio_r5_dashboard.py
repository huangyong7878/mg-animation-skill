import json
import tempfile
import unittest
from pathlib import Path
from studio.r5_dashboard import review_history

class R5DashboardTests(unittest.TestCase):
    def test_sampled_evidence_is_never_called_full_av_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)/"work/orders_pilot/formal_r4_v2"
            report=base/"r5_deepseek"
            report.mkdir(parents=True)
            (base/"state.json").write_text(json.dumps({"status":"review_pending"}))
            (report/"observations.md").write_text("P1: badge is too small")
            (report/"evidence.json").write_text(json.dumps({
                "provider":"deepseek","scope":"sampled_frames_only",
                "sampled_frames":26,"implementation_commit":"a"*40,
                "video_sha256":"b"*64,"audio_reviewed":False,
                "full_motion_reviewed":False,
                "usage":{"total_tokens":14692}}))
            records=review_history(Path(temp))
            self.assertEqual(len(records),1)
            self.assertEqual(records[0]["decision"],"pending_full_av_review")
            self.assertFalse(records[0]["audio_reviewed"])
            self.assertEqual(records[0]["token_usage"],14692)

    def test_missing_or_unsupported_report_is_ignored(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)/"work/orders_pilot/formal_r4"
            report=base/"r5_deepseek"
            report.mkdir(parents=True)
            (report/"observations.md").write_text("unverified")
            (report/"evidence.json").write_text(json.dumps({
                "provider":"deepseek","scope":"full_av"}))
            self.assertEqual(review_history(Path(temp)),[])

if __name__=="__main__":
    unittest.main()
