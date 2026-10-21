"""MG Studio Stage D bridge checks do not call a model or render in tests."""
import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from studio import delivery

class StageDStudioTests(unittest.TestCase):
    def test_missing_locked_assets_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(delivery,"_git",return_value="a"*40):
                result=delivery.preflight(Path(d))
        self.assertFalse(result["ready"])
        self.assertTrue(any("audio" in s for s in result["issues"]))
        self.assertFalse(result["r7_authorized"])

    def test_preflight_adds_checkout_to_module_search_path(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            with patch.object(delivery, "_git", return_value="a"*40):
                with patch.object(sys, "path", [p for p in sys.path if p != str(root)]):
                    delivery.preflight(root)
                    self.assertIn(str(root), sys.path)

    def test_bad_run_id_rejected_before_render(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"Invalid render run ID"):
                delivery.run_build(Path(d),"../../overwrite")

    def test_failed_preflight_never_starts_ffmpeg(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(delivery,"preflight",return_value={
                "ready":False,"issues":["Missing locked build input: audio"]}):
                with patch.object(delivery.subprocess,"run") as run:
                    with self.assertRaisesRegex(ValueError,"Stage D blocked"):
                        delivery.run_build(Path(d),"0123456789abcdef")
                    run.assert_not_called()

if __name__=="__main__":
    unittest.main()
