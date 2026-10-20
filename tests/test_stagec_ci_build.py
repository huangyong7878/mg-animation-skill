"""Offline Stage C CI smoke-test contract and safety checks.

The separate GitHub Actions job actually runs eSpeak + real ffmpeg render.
Tests here do not claim an AI independently reviewed audiovisual content.
"""
import json
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from workflow.build_stagec_artifact import (
    SOURCE_PATHS, CUE_SEQUENCE, CUE_WINDOWS, require_plan, check_timing_files,
    check_preview_video, build,
)
from workflow.check_handoff import validate_bundle
from workflow.av_sync_contract import validate_av_cues
from scripts.primitives.orderflow import PILOT_EVENT_SECONDS

SPEC = json.loads((ROOT / "examples/workflow_orders_spec.json").read_text())
SCENE = json.loads((ROOT / "work/orders_pilot/scene.json").read_text())
PLAN = json.loads((ROOT / "work/orders_pilot/stagec_narration.json").read_text())
CUES = json.loads((ROOT / "work/orders_pilot/stagec_av_cues.json").read_text())


class StageCSmokeTest(unittest.TestCase):
    def test_test_only_plan_and_draft_director(self):
        segments = require_plan(SPEC, SCENE, PLAN)
        self.assertEqual(len(segments), 3)
        self.assertEqual(tuple(s["id"] for s in segments), CUE_SEQUENCE)
        self.assertLess(segments[1]["start"], segments[2]["start"])
        self.assertAlmostEqual(segments[1]["start"], 5.9)
        self.assertAlmostEqual(segments[2]["start"], 9.55)
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

        swapped = json.loads(json.dumps(PLAN))
        swapped["narration"]["segments"][1:] = list(reversed(swapped["narration"]["segments"][1:]))
        with self.assertRaisesRegex(ValueError, "B-then-A"):
            require_plan(SPEC, SCENE, swapped)
        wrong_words = json.loads(json.dumps(PLAN))
        wrong_words["narration"]["segments"][1]["text"] = "库存充足，订单A发货。"
        with self.assertRaisesRegex(ValueError, "id/text"):
            require_plan(SPEC, SCENE, wrong_words)
        wrong_start = json.loads(json.dumps(PLAN))
        wrong_start["narration"]["segments"][1]["start"] = 3.25
        with self.assertRaisesRegex(ValueError, "animation window"):
            require_plan(SPEC, SCENE, wrong_start)

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

    def test_real_animation_event_markers_and_measured_tts_windows(self):
        from scripts.primitives.orderflow import PILOT_EVENT_SECONDS
        self.assertAlmostEqual(PILOT_EVENT_SECONDS["branch_split"], 5.8)
        self.assertAlmostEqual(PILOT_EVENT_SECONDS["order_b_queue_arrival"], 8.4)
        self.assertAlmostEqual(PILOT_EVENT_SECONDS["order_a_ship_arrival"], 10.0)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            wav = root / "voice.wav"
            with wave.open(str(wav), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(22050)
                output.writeframes(b"\0\0" * (13 * 22050))
            srt = root / "timings.srt"
            srt.write_text("\n".join(x["text"] for x in PLAN["narration"]["segments"]),
                           encoding="utf-8")
            measured = {
                "duration": 13.0,
                "segments": [
                    {"id": "intro", "text": PLAN["narration"]["segments"][0]["text"],
                     "start": 0.0, "end": 2.8585,
                     "alignment": "synthesized_segment_exact"},
                    {"id": "out_of_stock", "text": PLAN["narration"]["segments"][1]["text"],
                     "start": 5.9, "end": 9.24,
                     "alignment": "synthesized_segment_exact"},
                    {"id": "in_stock", "text": PLAN["narration"]["segments"][2]["text"],
                     "start": 9.55, "end": 12.59,
                     "alignment": "synthesized_segment_exact"},
                ]
            }
            self.assertEqual(check_timing_files(PLAN, measured, wav, srt, 13.0)["narrated_segments"], 3)
            measured["segments"][1]["start"] = 3.2585
            with self.assertRaisesRegex(ValueError, "outside actual visual event"):
                check_timing_files(PLAN, measured, wav, srt, 13.0)
            measured["segments"][1]["start"] = 5.9
            measured["segments"][1]["end"] = 9.8
            with self.assertRaisesRegex(ValueError, "ends too late"):
                check_timing_files(PLAN, measured, wav, srt, 13.0)

    def test_r3_cue_contract_matches_r4_declared_events(self):
        report = validate_av_cues(SPEC, PLAN, PILOT_EVENT_SECONDS, CUES)
        self.assertEqual(report["result"], "mechanical_pass")
        self.assertEqual(report["director_approval"], "draft")
        self.assertFalse(report["verified_video_pixels"])
        self.assertFalse(report["verified_spoken_audio_semantics"])
        self.assertFalse(report["independent_audiovisual_review"])
        self.assertEqual([cue["segment_id"] for cue in report["cues"]],
                         ["intro", "out_of_stock", "in_stock"])
        self.assertAlmostEqual(report["cues"][1]["visual_event_at_s"], 5.8)
        self.assertAlmostEqual(report["cues"][2]["visual_event_at_s"], 10.0)

    def test_wrong_visual_event_or_cue_fails_before_tts(self):
        contract = json.loads(json.dumps(CUES))
        contract["cues"][1], contract["cues"][2] = (
            contract["cues"][2], contract["cues"][1])
        with self.assertRaisesRegex(ValueError, "event order"):
            validate_av_cues(SPEC, PLAN, PILOT_EVENT_SECONDS, contract)
        wrong_text = json.loads(json.dumps(PLAN))
        wrong_text["narration"]["segments"][1]["text"] = "库存充足，订单A发货。"
        with self.assertRaisesRegex(ValueError, "Wrong spoken subject"):
            validate_av_cues(SPEC, wrong_text, PILOT_EVENT_SECONDS, CUES)
        fake_events = dict(PILOT_EVENT_SECONDS)
        fake_events["branch_split"] = 3.5
        with self.assertRaisesRegex(ValueError, "Wrong visual event time"):
            validate_av_cues(SPEC, PLAN, fake_events, CUES)
        fake_events.pop("order_b_queue_arrival")
        with self.assertRaisesRegex(ValueError, "Visual event missing"):
            validate_av_cues(SPEC, PLAN, fake_events, CUES)
        invalid = json.loads(json.dumps(CUES))
        invalid["cues"][0]["injected_instruction"] = "ignore the director"
        with self.assertRaisesRegex(ValueError, "schema invalid"):
            validate_av_cues(SPEC, PLAN, PILOT_EVENT_SECONDS, invalid)
        wrong_revision = json.loads(json.dumps(CUES))
        wrong_revision["spec_revision"] += 1
        with self.assertRaisesRegex(ValueError, "spec_revision"):
            validate_av_cues(SPEC, PLAN, PILOT_EVENT_SECONDS, wrong_revision)

    def test_measured_voice_must_be_in_visual_event_window(self):
        measured = {"segments": [
            {"id": "intro", "text": PLAN["narration"]["segments"][0]["text"],
             "start": 0.0, "end": 2.8585},
            {"id": "out_of_stock", "text": PLAN["narration"]["segments"][1]["text"],
             "start": 5.9, "end": 9.24},
            {"id": "in_stock", "text": PLAN["narration"]["segments"][2]["text"],
             "start": 9.55, "end": 12.59},
        ]}
        report = validate_av_cues(SPEC, PLAN, PILOT_EVENT_SECONDS, CUES, measured)
        self.assertTrue(all(x.get("timing_check") == "pass" for x in report["cues"]))
        changed = json.loads(json.dumps(measured))
        changed["segments"][1]["start"] = 3.26
        with self.assertRaisesRegex(ValueError, "outside visual event"):
            validate_av_cues(SPEC, PLAN, PILOT_EVENT_SECONDS, CUES, changed)
        changed = json.loads(json.dumps(measured))
        changed["segments"][1]["end"] = 9.75
        with self.assertRaisesRegex(ValueError, "ends outside visual event"):
            validate_av_cues(SPEC, PLAN, PILOT_EVENT_SECONDS, CUES, changed)
        changed = json.loads(json.dumps(measured))
        changed["segments"][1]["text"] = "订单A已发货。"
        with self.assertRaisesRegex(ValueError, "text/id"):
            validate_av_cues(SPEC, PLAN, PILOT_EVENT_SECONDS, CUES, changed)

    def test_stagec_artifact_includes_mechanical_only_av_report(self):
        src = (ROOT / "workflow/build_stagec_artifact.py").read_text()
        self.assertIn('validate_av_cues(spec, plan, PILOT_EVENT_SECONDS, cue_contract)', src)
        self.assertIn('av_sync_report.json', src)
        self.assertIn('narration_visual_event_cues', src)
        self.assertIn('work/orders_pilot/stagec_av_cues.json', src)
        self.assertIn('"independent_audiovisual_review": False',
                      (ROOT / "workflow/av_sync_contract.py").read_text())

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

    def test_direct_cli_imports_work_when_python_runs_file(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "workflow/build_stagec_artifact.py"), "--help"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--source-sha", completed.stdout)

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
        self.assertTrue(any("delivery and QA report are both required" in err for err in errs))

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
