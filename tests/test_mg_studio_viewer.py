"""Viewer restricts filenames and refuses invalid media; no actual videos required."""
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from studio.delivery_viewer import resolve_delivery, inspect, list_deliveries, verified_video, display_version

class DeliveryViewerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo=Path(self.tmp.name)
        self.folder=self.repo/"work/orders_pilot/stage_d_studio_0123456789abcdef"
        self.folder.mkdir(parents=True)
        (self.folder/"media").mkdir()
        (self.folder/"media/stage_d_final.mp4").write_bytes(b"test-video")
        (self.folder/"delivery.json").write_text(json.dumps({
            "status":"ready_for_qa","implementation_commit":"a"*40,
            "spec_sha256":"b"*64,"artifacts":{"video_path":"media/stage_d_final.mp4"}}))
        (self.folder/"media_manifest.json").write_text(json.dumps({"files":[{"path":"media/stage_d_final.mp4"}]}))
        (self.folder/"director_spec.json").write_text("{}")

    def test_standard_http_range_syntax(self):
        # Regression for browsers requesting "Range: bytes=0-".
        source = (Path(__file__).resolve().parents[1] / "studio/server.py").read_text()
        self.assertIn('r"bytes=(\\d+)-(\\d*)"', source)
        self.assertIsNotNone(re.fullmatch(r"bytes=(\\d+)-(\\d*)", "bytes=0-"))
        self.assertIsNotNone(re.fullmatch(r"bytes=(\\d+)-(\\d*)", "bytes=1024-2047"))

    def test_version_and_review_are_not_inferred_from_ready_for_qa(self):
        self.assertEqual(display_version("stage_d_delivery"), "初版")
        self.assertEqual(display_version("stage_d_delivery_v2"), "V2")
        self.assertTrue(display_version("stage_d_studio_0123456789abcdef").startswith("Studio 构建"))
        with patch("workflow.media_manifest.verify_manifest", return_value=[]):
            result = inspect(self.repo, self.folder.name)
            self.assertEqual(result["review_status"], "待独立审核")
            self.assertIn(result["time_basis"], ("filesystem_birthtime", "unknown"))
            self.assertFalse(result["r5_pass"])

    def test_rejects_traversal(self):
        for value in ("../etc/passwd","stage_d_studio_bad","../../private"):
            with self.assertRaises(ValueError):
                resolve_delivery(self.repo,value)

    def test_verified_video_only_if_manifest_valid(self):
        with patch("workflow.media_manifest.verify_manifest",return_value=[]):
            result=inspect(self.repo,self.folder.name)
            self.assertTrue(result["manifest_ok"])
            self.assertEqual(verified_video(self.repo,self.folder.name).suffix,".mp4")
        with patch("workflow.media_manifest.verify_manifest",return_value=["corrupted"]):
            result=inspect(self.repo,self.folder.name)
            self.assertFalse(result["manifest_ok"])
            with self.assertRaisesRegex(ValueError,"integrity"):
                verified_video(self.repo,self.folder.name)

    def test_list_invalid_delivery_without_crashing(self):
        (self.folder/"media_manifest.json").unlink()
        result=list_deliveries(self.repo)
        self.assertEqual(result[0]["status"],"invalid")

if __name__=="__main__":
    unittest.main()
