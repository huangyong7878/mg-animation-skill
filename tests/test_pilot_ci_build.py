"""Regression tests for the real Pilot 001 render-and-upload path.

These tests do not claim video QA passed; the Actions smoke job renders MP4.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from workflow.build_pilot_artifact import (
    SOURCE_FILES, check_pilot_scene, check_video_metadata, build,
)

SPEC = json.loads((ROOT / "examples/workflow_orders_spec.json").read_text(encoding="utf-8"))
SCENE = json.loads((ROOT / "work/orders_pilot/scene.json").read_text(encoding="utf-8"))


def video_info(*, audio=False, codec="h264", frames="312"):
    streams = [{
        "codec_type": "video", "codec_name": codec,
        "width": 960, "height": 540, "r_frame_rate": "24/1",
        "nb_frames": frames,
    }]
    if audio:
        streams.append({"codec_type": "audio", "codec_name": "aac"})
    return {"streams": streams, "format": {"duration": "13.000000"}}


class TestPilotCIBuild(unittest.TestCase):
    def test_pilot_spec_and_scene_match(self):
        check_pilot_scene(SPEC, SCENE)
        self.assertEqual(len(SOURCE_FILES), 3)
        for source in SOURCE_FILES:
            self.assertTrue((ROOT / source).is_file(), source)

    def test_mismatch_fails_closed(self):
        invalid = json.loads(json.dumps(SCENE))
        invalid["canvas"]["width"] = 640
        with self.assertRaisesRegex(ValueError, "width"):
            check_pilot_scene(SPEC, invalid)

    def test_correct_real_video_metadata_shape(self):
        check_video_metadata(video_info(), SPEC)

    def test_reject_bad_codec_audio_or_missing_frames(self):
        for metadata in (
            video_info(audio=True),
            video_info(codec="mpeg4"),
            video_info(frames="311"),
        ):
            with self.subTest(metadata=metadata):
                with self.assertRaises(ValueError):
                    check_video_metadata(metadata, SPEC)

    def test_invalid_git_sha_fails_before_output_or_render(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "build"
            with self.assertRaisesRegex(ValueError, "40-character"):
                build(ROOT / "examples/workflow_orders_spec.json",
                      ROOT / "work/orders_pilot/scene.json",
                      "incorrect_sha", artifact, "mg-test", "https://github.com/a/b/actions/runs/1")
            self.assertFalse(artifact.exists())

    def test_workflow_retains_no_privileged_token(self):
        workflow = (ROOT / ".github/workflows/pilot-render-artifacts.yml").read_text()
        self.assertIn("contents: read", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("pull_request:", workflow)
        self.assertIn("retention-days: 30", workflow)
        self.assertNotIn("pull_request_target:", workflow)


if __name__ == "__main__":
    unittest.main()
