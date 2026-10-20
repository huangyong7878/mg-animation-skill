"""Stage C R5 audiovisual QA: all Gemini/GitHub interactions mocked. No paid requests."""
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from workflow.r5_av_control import (
    selected_run, preflight, publish, comment_marker, EXPECTED_NAME, EXPECTED_PATH)
from workflow.r5_av_review import (
    call_gemini_av, validate_observations, verify_inputs, review_artifact)
from workflow.av_sync_contract import validate_av_cues
from workflow.r5_av_manual import import_manual
from workflow.media_manifest import create_manifest
from workflow.check_handoff import canonical_digest
from scripts.primitives.orderflow import PILOT_EVENT_SECONDS

ROOT = Path(__file__).resolve().parents[1]
REPO = "huangyong7878/mg-animation-skill"
SHA = "a" * 40
RUN = 19001
SELECTION = {
    "source_run_id": RUN, "implementation_commit": SHA, "pr": 14,
    "source_artifact": f"mg-orders-stagec-draft-{RUN}-{SHA[:12]}",
}
PLAN = json.loads((ROOT / "work/orders_pilot/stagec_narration.json").read_text())
CUES = json.loads((ROOT / "work/orders_pilot/stagec_av_cues.json").read_text())
SPEC = json.loads((ROOT / "examples/workflow_orders_spec.json").read_text())
TIMINGS = {"duration": 13.0, "segments": [
    {"id": "intro", "text": PLAN["narration"]["segments"][0]["text"],
     "start": 0.0, "end": 2.8585, "alignment": "synthesized_segment_exact"},
    {"id": "out_of_stock", "text": PLAN["narration"]["segments"][1]["text"],
     "start": 5.9, "end": 9.24, "alignment": "synthesized_segment_exact"},
    {"id": "in_stock", "text": PLAN["narration"]["segments"][2]["text"],
     "start": 9.55, "end": 12.59, "alignment": "synthesized_segment_exact"},
]}
MECHANICAL = validate_av_cues(SPEC, PLAN, PILOT_EVENT_SECONDS, CUES, TIMINGS)


def sample_result(decision="pass"):
    return {
        "decision": decision, "audio_evaluated": True, "video_evaluated": True,
        "checks": [
            {"segment_id": x["segment_id"], "result": "pass",
             "timestamp_s": x["actual_start_s"] + .45,
             "heard_text": PLAN["narration"]["segments"][i]["text"],
             "visual_observation": ("实际看到动画中的订单" + x["segment_id"] +
                                    "沿对应路径运动并展示状态"),
             "audio_verified": True, "video_verified": True,
             "reason": "在真实声音中听到台词，且同期画面中的订单状态与文案一致"}
            for i, x in enumerate(MECHANICAL["cues"])
        ],
        "findings": [], "summary": "分别听过真实音轨，观察订单 B 缺货和 A 发货的画面事件，三段没有发现明显不一致",
    }


class TestManualAVSourceGate(unittest.TestCase):
    def setUp(self):
        self.run = {
            "id": RUN, "name": EXPECTED_NAME,
            "path": EXPECTED_PATH + "@refs/pull/14/merge",
            "event": "pull_request", "status": "completed", "conclusion": "success",
            "repository": {"full_name": REPO},
            "head_repository": {"full_name": REPO}, "head_sha": SHA,
        }
        self.comments = []

    def fake_api(self, method, endpoint, payload):
        if endpoint.endswith(f"/actions/runs/{RUN}"):
            return self.run
        if endpoint.endswith(f"/commits/{SHA}/pulls?per_page=100"):
            return [{"number": 14, "state": "open",
                     "head": {"sha": SHA, "repo": {"full_name": REPO}},
                     "base": {"repo": {"full_name": REPO}}}]
        if endpoint.endswith("/pulls/14"):
            return {"state": "open", "head": {"sha": SHA}}
        if endpoint.endswith("/issues/14/comments?per_page=100"):
            return self.comments
        if method == "POST" and endpoint.endswith("/issues/14/comments"):
            self.comments.append(payload)
            return {"html_url": "https://github.com/test/14#issuecomment-1"}
        raise AssertionError((method, endpoint))

    def test_manual_success_and_no_duplicate_billing(self):
        self.assertEqual(selected_run(REPO, str(RUN), "token", self.fake_api),
                         SELECTION)
        self.assertTrue(preflight(REPO, SELECTION, "token", self.fake_api)["should_run"])
        self.comments.append({"body": comment_marker(RUN, SHA)})
        self.assertFalse(preflight(REPO, SELECTION, "token", self.fake_api)["should_run"])

    def test_untrusted_run_ids_rejected(self):
        for value in ("0", "", "-1", "3x", " 19001", "19001\n", "0" * 20):
            with self.subTest(value=value), self.assertRaises(ValueError):
                selected_run(REPO, value, "token", self.fake_api)

    def test_mismatched_workflow_fork_failed_or_stale_cannot_bill(self):
        cases = [
            ("name", "Pilot 001 Render and QA Artifact"),
            ("path", ".github/workflows/evil.yml@refs/heads/main"),
            ("event", "workflow_dispatch"), ("status", "in_progress"),
            ("conclusion", "failure"),
            ("head_repository", {"full_name": "fork/evil"}),
            ("head_sha", "invalid"),
        ]
        for field, value in cases:
            with self.subTest(field=field):
                orig = self.run[field]
                self.run[field] = value
                try:
                    with self.assertRaises(ValueError):
                        selected_run(REPO, str(RUN), "token", self.fake_api)
                finally:
                    self.run[field] = orig

    def test_feedback_is_distinct_from_stage_b_and_bound_to_source(self):
        report = {**sample_result(), "implementation_commit": SHA,
                  "source_run_id": RUN}
        audit = {**SELECTION, "decision": "pass", "model": "gemini-2.5-flash"}
        posted = publish(REPO, SELECTION, report, audit, "token", self.fake_api)
        self.assertIn("issuecomment", posted["html_url"])
        self.assertIn("R5 Independent Stage C Audiovisual QA",
                      self.comments[0]["body"])
        self.assertIsNone(publish(REPO, SELECTION, report, audit, "token", self.fake_api))
        report["implementation_commit"] = "b" * 40
        with self.assertRaisesRegex(ValueError, "mismatch"):
            publish(REPO, SELECTION, report, audit, "token", self.fake_api)


class TestIndependentAVReview(unittest.TestCase):
    def test_gemini_sees_both_real_audio_and_original_video(self):
        calls = []
        def fake_api(url, headers, payload):
            calls.append((url, headers, payload))
            return {"candidates": [{"finishReason": "STOP",
                    "content": {"parts": [{"text": json.dumps(sample_result())}]}}],
                    "usageMetadata": {"promptTokenCount": 200,
                                      "candidatesTokenCount": 400,
                                      "totalTokenCount": 600}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vid, wav = root / "real.mp4", root / "spoken.wav"
            vid.write_bytes(b"real video placeholder")
            wav.write_bytes(b"voice placeholder")
            result, usage = call_gemini_av("independent AV audit", vid, wav,
                                           "gemini-2.5-flash", "synthetic_key", fake_api)
        self.assertEqual(usage["total_tokens"], 600)
        self.assertEqual(json.loads(result)["decision"], "pass")
        url, head, body = calls[0]
        self.assertIn(":generateContent", url)
        self.assertEqual(head["x-goog-api-key"], "synthetic_key")
        parts = body["contents"][0]["parts"]
        self.assertEqual([p["inline_data"]["mime_type"] for p in parts[1:]],
                         ["video/mp4", "audio/wav"])
        self.assertEqual(parts[1]["video_metadata"]["fps"], 5.0)
        self.assertEqual(len(calls), 1)

    def test_schema_requires_listen_and_watch_observations(self):
        report = validate_observations(json.dumps(sample_result()), MECHANICAL, 13.0)
        self.assertEqual(report["decision"], "pass")
        invalid = sample_result()
        invalid["checks"][1]["audio_verified"] = False
        with self.assertRaisesRegex(ValueError, "actual audio"):
            validate_observations(json.dumps(invalid), MECHANICAL, 13.0)
        invalid = sample_result()
        invalid["audio_evaluated"] = False
        with self.assertRaisesRegex(ValueError, "both modalities"):
            validate_observations(json.dumps(invalid), MECHANICAL, 13.0)
        invalid = sample_result()
        invalid["checks"][1]["timestamp_s"] = 2.0
        with self.assertRaisesRegex(ValueError, "outside measured"):
            validate_observations(json.dumps(invalid), MECHANICAL, 13.0)

    def test_unknown_speech_cannot_produce_pass(self):
        invalid = sample_result()
        invalid["checks"][1]["result"] = "needs_review"
        invalid["checks"][1]["audio_verified"] = False
        with self.assertRaisesRegex(ValueError, "cannot ignore"):
            validate_observations(json.dumps(invalid), MECHANICAL, 13.0)
        invalid["decision"] = "pending"
        self.assertEqual(
            validate_observations(json.dumps(invalid), MECHANICAL, 13.0)["decision"],
            "pending")

    def test_wrong_visual_order_requires_rework(self):
        invalid = sample_result()
        invalid["checks"][1]["result"] = "fail"
        with self.assertRaisesRegex(ValueError, "Failed AV cue"):
            validate_observations(json.dumps(invalid), MECHANICAL, 13.0)
        invalid["decision"] = "rework"
        self.assertEqual(
            validate_observations(json.dumps(invalid), MECHANICAL, 13.0)["decision"],
            "rework")

    def test_fake_or_duplicate_cues_fail_closed(self):
        invalid = sample_result()
        invalid["checks"][2]["segment_id"] = "out_of_stock"
        with self.assertRaisesRegex(ValueError, "omitted/duplicated"):
            validate_observations(json.dumps(invalid), MECHANICAL, 13.0)
        invalid = sample_result()
        invalid["findings"] = [{
            "segment_id": "intro", "severity": "P1", "timestamp_s": 1.0,
            "expected": "A appears", "observed": "wrong", "fix_request": "change"
        }]
        with self.assertRaisesRegex(ValueError, "serious"):
            validate_observations(json.dumps(invalid), MECHANICAL, 13.0)

    def test_manifest_protects_paid_model_from_tampered_speech(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for file, content in (
                ("work/orders_pilot/stagec_narration.json", PLAN),
                ("work/orders_pilot/stagec_av_cues.json", CUES),
                ("media/timings.json", TIMINGS),
                ("av_sync_report.json", MECHANICAL),
                ("director_spec.json", SPEC),
            ):
                out = root / file
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(content), encoding="utf-8")
            video = root / "media/stagec_av_preview.mp4"
            video.write_bytes(b"synthetic H264 AAC test stub")
            audio = root / "media/voice.wav"
            with wave.open(str(audio), "wb") as sound:
                sound.setnchannels(1); sound.setsampwidth(2)
                sound.setframerate(22050)
                sound.writeframes(b"\x01\x00" * (22050 * 13))
            delivery = {
                "schema_version": "1.0", "project_id": SPEC["project_id"],
                "spec_id": SPEC["spec_id"], "spec_revision": SPEC["revision"],
                "spec_sha256": canonical_digest(SPEC),
                "implementation_commit": SHA, "attempt": 1,
                "stage": "C", "status": "prototype",
                "artifacts": {
                    "source_paths": ["work/orders_pilot/stagec_narration.json"],
                    "video_path": "media/stagec_av_preview.mp4",
                    "audio_path": "media/voice.wav",
                    "timings_path": "media/timings.json",
                },
                "checks": [{"name": "mechanical_cue", "result": "pass", "detail": "test"}],
                "deviations": [],
            }
            (root / "delivery.json").write_text(json.dumps(delivery), encoding="utf-8")
            extras = ("director_spec.json", "delivery.json", "av_sync_report.json",
                      "work/orders_pilot/stagec_av_cues.json",
                      "work/orders_pilot/stagec_narration.json")
            manifest = create_manifest(
                SPEC, delivery, root, "actions",
                artifact_name=SELECTION["source_artifact"],
                run_url=f"https://github.com/{REPO}/actions/runs/{RUN}",
                extras=extras)
            (root / "media_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with patch("workflow.r5_av_review.probe_av"):
                self.assertEqual(verify_inputs(root, SELECTION)[1]["stage"], "C")
                self.assertEqual(verify_inputs(root, None)[1]["stage"], "C")
                human_review = root / "manual_observations.json"
                human_review.write_text(json.dumps(sample_result()), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "attestation"):
                    import_manual(root, human_review, "Human Tester",
                                  root / "manual_unattested", False)
                manual = import_manual(root, human_review, "Human Tester",
                                       root / "manual_results", True)
                self.assertEqual(manual["decision"], "pass")
                self.assertFalse(manual["release_approved"])
                self.assertEqual(manual["review_origin"]["method"], "manual_import")
                self.assertTrue((root / "manual_results/av_qa_report.json").is_file())
                audio.write_bytes(audio.read_bytes() + b"TAMPERED!")
                with self.assertRaisesRegex(ValueError, "integrity"):
                    verify_inputs(root, SELECTION)
                with self.assertRaisesRegex(ValueError, "integrity"):
                    import_manual(root, human_review, "Human Tester",
                                  root / "bad_manual", True)

    def test_both_disabled_gates_protect_api_and_dispatch_is_manual(self):
        yaml = (ROOT / ".github/workflows/r5-stagec-av-qa.yml").read_text()
        self.assertIn("on:\n  workflow_dispatch:", yaml)
        self.assertNotIn("\n  workflow_run:", yaml)
        self.assertNotIn("\n  pull_request:", yaml)
        self.assertIn("vars.R5_AV_ENABLED == 'true'", yaml)
        self.assertIn("vars.R5_ENABLED == 'true'", yaml)
        self.assertIn("vars.R5_PROVIDER == 'gemini'", yaml)
        self.assertIn("persist-credentials: false", yaml)
        self.assertIn("ref: main", yaml)
        self.assertNotIn("pull_request_target:", yaml)
        self.assertIn("concurrency:", yaml)
        self.assertIn("cancel-in-progress: false", yaml)
        self.assertIn("stagec_run_id", yaml)
        self.assertIn("actions/download-artifact@v4", yaml)
        self.assertNotIn("secrets.OPENAI_API_KEY", yaml)
        self.assertNotIn("secrets.DEEPSEEK_API_KEY", yaml)
        self.assertTrue((ROOT / "workflow/r5_av_manual.py").is_file())
        manual_src = (ROOT / "workflow/r5_av_manual.py").read_text()
        self.assertNotIn("urllib", manual_src)
        self.assertNotIn("GEMINI_API_KEY", manual_src)
