"""Fail-closed DeepSeek R5 contract tests; no API requests."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow import r5_provider


class DeepSeekR5Tests(unittest.TestCase):
    def test_extract_frames_requires_video_decoding(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(r5_provider.subprocess, "run", side_effect=RuntimeError("bad media")):
                with self.assertRaises(RuntimeError):
                    r5_provider.extract_frames(Path(d)/"bad.mp4", Path(d)/"frames")

    def test_missing_workdir_prevents_model_call(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises((ValueError, OSError, FileNotFoundError)):
                r5_provider.review_deepseek(Path(d)/"missing", Path(d), transport=lambda _: self.fail("called"))

    def test_schema_pending_never_pass(self):
        import json
        schema = json.loads((Path(__file__).resolve().parents[1] / "contracts/qa.schema.json").read_text())
        assert "pending" in schema["properties"]["decision"]["enum"]


if __name__ == "__main__":
    unittest.main()
