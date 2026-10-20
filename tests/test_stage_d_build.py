"""Stage D Pilot: approval lock, true media provenance, fail-closed release."""
import copy
import hashlib
import json
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from workflow.build_stage_d_artifact import (
    ROOT, LOCKED, SOURCES, build, verify_lock, digest,
)
from workflow.check_handoff import validate_bundle
from workflow.media_manifest import verify_manifest

SPEC = json.loads((ROOT / "examples/workflow_orders_spec.json").read_text())
SCENE = json.loads((ROOT / "work/orders_pilot/scene.json").read_text())
PLAN = json.loads((ROOT / "work/orders_pilot/stagec_narration.json").read_text())
CUES = json.loads((ROOT / "work/orders_pilot/stagec_av_cues.json").read_text())
HEAD = "a" * 40


class StageDTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.spec = copy.deepcopy(SPEC)
        self.spec["approval"] = {
            "status": "approved", "approved_by": "UNIT_TEST_ONLY_FAKE_APPROVER",
            "approved_at": "2026-10-20T00:00:00Z"}
        self.spec["narration"].update({
            "status": "locked", "audio_path": LOCKED[1],
            "timings_path": LOCKED[2]})
        self.scene = copy.deepcopy(SCENE)
        self.plan = copy.deepcopy(PLAN)
        self.plan["test_only"] = False
        self.cues = copy.deepcopy(CUES)
        self.cues["status"] = "approved"
        self.timing = {
            "duration": 13.0, "segments": [
                {"id": self.plan["narration"]["segments"][0]["id"],
                 "text": self.plan["narration"]["segments"][0]["text"],
                 "start": 0.0, "end": 2.8585},
                {"id": self.plan["narration"]["segments"][1]["id"],
                 "text": self.plan["narration"]["segments"][1]["text"],
                 "start": 5.9, "end": 9.24},
                {"id": self.plan["narration"]["segments"][2]["id"],
                 "text": self.plan["narration"]["segments"][2]["text"],
                 "start": 9.55, "end": 12.59},
            ],
        }
        self.script = self.root / "narration.txt"
        self.script.write_text(
            "\n".join(x["text"] for x in self.plan["narration"]["segments"]) + "\n",
            encoding="utf-8")
        self.wav = self.root / "voice.wav"
        with wave.open(str(self.wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(22050)
            w.writeframes(b"\x01\x00" * (13 * 22050))
        self.timings = self.root / "timings.json"
        self.timings.write_text(json.dumps(self.timing), encoding="utf-8")
        self.spec["narration"]["audio_sha256"] = digest(self.wav)
        self.spec["narration"]["timings_sha256"] = digest(self.timings)
        self.args = (self.script, self.wav, self.timings)

    def check(self):
        return verify_lock(self.spec, self.scene, self.plan,
                           self.cues, *self.args)

    def test_synthetic_locked_fixture_passes_metadata_not_release(self):
        self.assertEqual(validate_bundle(self.spec), [])
        result = self.check()
        self.assertEqual(result["director_approval"], "approved")
        self.assertEqual(result["result"], "mechanical_pass")
        self.assertFalse(result["independent_audiovisual_review"])
        self.assertEqual([x["segment_id"] for x in result["cues"]],
                         ["intro", "out_of_stock", "in_stock"])

    def test_unapproved_director_and_voice_are_blocked(self):
        self.spec["approval"] = {"status": "draft"}
        with self.assertRaises(ValueError):
            self.check()
        self.spec["approval"] = {"status": "approved",
                                 "approved_by": "UNIT_TEST_ONLY_FAKE_APPROVER",
                                 "approved_at": "2026-10-20T00:00:00Z"}
        self.spec["narration"]["status"] = "draft"
        with self.assertRaisesRegex(ValueError, "draft|locked"):
            self.check()

    def test_draft_cue_or_test_only_plan_cannot_be_staged(self):
        self.plan["test_only"] = True
        with self.assertRaisesRegex(ValueError, "test narration"):
            self.check()
        self.plan["test_only"] = False
        self.cues["status"] = "draft"
        with self.assertRaisesRegex(ValueError, "approved"):
            self.check()

    def test_audio_and_timing_locked_byte_hashes_cannot_be_bypassed(self):
        self.wav.write_bytes(self.wav.read_bytes() + b"t")
        with self.assertRaisesRegex(ValueError, "audio_sha256"):
            self.check()
        self.spec["narration"]["audio_sha256"] = digest(self.wav)
        self.timings.write_text(self.timings.read_text() + " ", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "timings_sha256"):
            self.check()

    def test_wrong_spoken_subject_or_early_voice_blocks_stage_d(self):
        self.plan["narration"]["segments"][1]["text"] = "库存充足，订单A发货。"
        with self.assertRaisesRegex(ValueError, "script"):
            self.check()
        self.plan = copy.deepcopy(PLAN)
        self.plan["test_only"] = False
        self.timing["segments"][1]["start"] = 3.2
        self.timings.write_text(json.dumps(self.timing), encoding="utf-8")
        self.spec["narration"]["timings_sha256"] = digest(self.timings)
        with self.assertRaisesRegex(ValueError, "outside visual event"):
            self.check()

    def test_mismatched_director_canvas_or_scene_rejected(self):
        self.scene["canvas"]["duration"] = 14.0
        with self.assertRaisesRegex(ValueError, "duration/canvas"):
            self.check()
        self.scene = copy.deepcopy(SCENE)
        self.scene["scenes"][0]["elements"] = [{"type": "text", "text": "FAKE"}]
        with self.assertRaisesRegex(ValueError, "approved Pilot"):
            self.check()

    def test_source_sha_failure_prevents_final_render(self):
        with self.assertRaisesRegex(ValueError, "Full Git SHA"):
            build(None, None, None, None, None, None, None,
                  "short", self.root / "out")

    def test_full_build_with_mocked_video_commands_creates_review_only_bundle(self):
        files = {}
        for name, obj in (("spec.json", self.spec), ("scene.json", self.scene),
                          ("plan.json", self.plan), ("cues.json", self.cues)):
            path = self.root / name
            path.write_text(json.dumps(obj), encoding="utf-8")
            files[name] = path
        def fake_command(argv):
            argv = list(map(str, argv))
            if argv[:3] == ["git", "rev-parse", "HEAD"]:
                return HEAD + "\n"
            if argv[0] == "ffprobe":
                return json.dumps({
                    "format": {"duration": "13.0"},
                    "streams": [
                        {"codec_type": "video", "codec_name": "h264",
                         "width": 960, "height": 540, "nb_frames": "312"},
                        {"codec_type": "audio", "codec_name": "aac"},
                    ]})
            if any("scripts/render.py" in item for item in argv):
                Path(argv[-1]).write_bytes(b"mocked MP4 (not a real CI video)")
            if argv[0] == "ffmpeg":
                Path(argv[-1]).write_bytes(b"mocked review frame")
            return ""
        out = self.root / "out"
        with patch("workflow.build_stage_d_artifact.command", fake_command):
            delivery = build(
                files["spec.json"], files["scene.json"], files["plan.json"],
                files["cues.json"], *self.args, HEAD, out)
        self.assertEqual(delivery["stage"], "D")
        self.assertEqual(delivery["status"], "ready_for_qa")
        self.assertEqual(delivery["implementation_commit"], HEAD)
        qa = json.loads((out / "qa_template.json").read_text())
        self.assertEqual(qa["decision"], "pending")
        self.assertFalse(qa["reviewer"]["independent_context"])
        self.assertTrue(all(c["result"] == "needs_review" for c in qa["checks"]))
        self.assertTrue(validate_bundle(
            self.spec, delivery, qa, release=True, artifact_root=out))
        manifest = json.loads((out / "media_manifest.json").read_text())
        self.assertEqual(verify_manifest(manifest, out, self.spec, delivery), [])
        self.assertEqual(manifest["storage"]["backend"], "local")
        (out / "media/voice.wav").write_bytes(b"tamper")
        self.assertTrue(verify_manifest(manifest, out, self.spec, delivery))
        with self.assertRaisesRegex(ValueError, "overwrite"):
            with patch("workflow.build_stage_d_artifact.command", fake_command):
                build(files["spec.json"], files["scene.json"],
                      files["plan.json"], files["cues.json"],
                      *self.args, HEAD, out)


if __name__ == "__main__":
    unittest.main()
