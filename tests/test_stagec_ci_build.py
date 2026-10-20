"""Offline Stage C CI smoke-test contract and safety checks.

The separate GitHub Actions job actually runs eSpeak + real ffmpeg render.
Tests here do not claim an AI independently reviewed audiovisual content.
"""
import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from workflow.build_stagec_artifact import (
    SOURCE_PATHS, require_plan, check_timing_files,
    check_preview_video, build,
)
from workflow.check_handoff import validate_bundle

SPEC = json.loads((ROOT / "examples/workflow_orders_spec.json").read_text())
SCENE = json.loads((ROOT / "work/orders_pilot/scene.json").read_text())
PLAN = json.loads((ROOT / "work/orders_pilot/stagec_narration.json").read_text())


class StageCSmokeTest(unittest.TestCase):
    def test_test_only_plan_and_draft_director(self):
        segments = require_plan(SPEC, SCENE, PLAN)
        self.assertEqual(len(segments), 3)
        self.assertEqual(SPEC["approval"]["status"], "draft")
        self.assertEqual(SPEC["narration"]["status"], "draft")
        self.assertTrue(PLAN["test_only"])
        for path in SOURCE_PATHS:
            self.assertTrue((ROOT / path).is_file(), path)

    def test_reject_fake_formal_approval_and_mismatch(self):
        invalid = json.loads(json.dumps(SPEC))
        invalid["narration"]["status"] = "locked"
        with self.assertRaises(ValueError):
            require_plan(invalid, SCENE, PLAN)

        invalid = json.loads(json.dumps(PLAN))
        invalid["test_only"] = False
        with self.assertRaisesRegex(ValueError, "test_only"):
            require_plan(SPEC, SCENE, invalid)

        scene = json.loads(json.dumps(SCENE))
        scene["canvas"]["fps"] = 30
        with self.assertRaisesRegex(ValueError, "fps"):
            require_plan(SPEC, scene, PLAN)

    def test_wrong_wav_duration_or_segments_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            wav = path / "voice.wav"
            with wave.open(str(wav), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(22050)
                output.writeframes(b"\0\0" * 22050)
            srt = path / "timings.srt"
            srt.write_text("test", encoding="utf-8")
            timings = {
                "duration": 13,
                "segments": [{"id": s["id"], "text": s["text"],
                              "start": 0, "end": 1,
                              "alignment": "synthesized_segment_exact"}
                             for s in PLAN["narration"]["segments"]],
            }
            with self.assertRaisesRegex(ValueError, "WAV frame duration"):
                check_timing_files(PLAN, timings, wav, srt, 13)
            timings["segments"].pop()
            with self.assertRaisesRegex(ValueError, "segment count"):
                check_timing_files(PLAN, timings, wav, srt, 13)

    def test_av_metadata_checks_real_audio_and_video(self):
        probe = {
            "format": {"duration": "13.000"},
            "streams": [
                {"codec_type": "video", "codec_name": "h264",
                 "width": 960, "height": 540, "nb_frames": "312"},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
        }
        check_preview_video(probe, SPEC)
        bad = json.loads(json.dumps(probe))
        bad["streams"].pop()
        with self.assertRaisesRegex(ValueError, "audio stream"):
            check_preview_video(bad, SPEC)
        bad = json.loads(json.dumps(probe))
        bad["streams"][0]["nb_frames"] = "311"
        with self.assertRaisesRegex(ValueError, "missing expected"):
            check_preview_video(bad, SPEC)

    def test_invalid_source_sha_fails_without_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact_dir = Path(directory) / "output"
            with self.assertRaisesRegex(ValueError, "40 hex"):
                build(ROOT / "examples/workflow_orders_spec.json",
                      ROOT / "work/orders_pilot/scene.json",
                      ROOT / "work/orders_pilot/stagec_narration.json",
                      "invalid", artifact_dir, "artifact-name",
                      "https://github.com/a/b/actions/runs/1")
            self.assertFalse(artifact_dir.exists())

    def test_stage_c_is_not_a_release(self):
        spec = json.loads(json.dumps(SPEC))
        self.assertNotEqual(spec["approval"]["status"], "approved")
        errs = validate_bundle(spec, release=True, artifact_root=ROOT)
        self.assertTrue(any("not approved" in err for err in errs))

    def test_r5_remains_bound_to_stage_b_and_opt_in(self):
        r5 = (ROOT / "workflow/r5_review.py").read_text()
        self.assertIn('delivery["stage"] != "B"', r5)
        workflow = (ROOT / ".github/workflows/r5-visual-qa.yml").read_text()
        self.assertIn("vars.R5_ENABLED == 'true'", workflow)
        self.assertIn("vars.R5_PROVIDER == 'gemini'", workflow)
        pilot = (ROOT / ".github/workflows/pilot-render-artifacts.yml").read_text()
        self.assertIn("work/orders_pilot/stagec_narration.json", pilot)

    def test_stage_c_workflow_is_safe_offline_and_uploads(self):
        workflow = (ROOT / ".github/workflows/stagec-audio-artifacts.yml").read_text()
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("espeak ffmpeg", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertIn("if-no-files-found: error", workflow)
        self.assertNotIn("pull_request_target:", workflow)
        self.assertNotIn("secrets.", workflow)
        self.assertNotIn("R5_ENABLED: true", workflow)


if __name__ == "__main__":
    unittest.main()
