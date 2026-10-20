"""R5 configurable model adapter and privileged PR-feedback regression tests.

All model and GitHub HTTP calls mocked. No paid API calls or PR writes here.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.check_handoff import canonical_digest, required_checks
from workflow.r5_review import (
    call_gemini, call_openai, call_deepseek, parse_model_report, make_prompt,
    verify_inputs, run_review, safe_model, is_r5_enabled, main as r5_main,
)
from workflow.r5_pr_feedback import safe_event, publish, comment_body, preflight

ROOT = Path(__file__).resolve().parents[1]
REPO = "huangyong7878/mg-animation-skill"
SHA = "a" * 40
RUN = 98765


def data():
    spec = json.loads((ROOT / "examples/workflow_orders_spec.json").read_text("utf-8"))
    delivery = json.loads((ROOT / "examples/workflow_orders_delivery.json").read_text("utf-8"))
    delivery.update(implementation_commit=SHA, spec_sha256=canonical_digest(spec),
                    stage="B", status="ready_for_qa")
    return spec, delivery


def model_answer(spec, decision="pass"):
    return {
        "decision": decision,
        "checks": [
            dict(shot_id=shot, requirement_id=req, result="pass",
                 evidence="video 5.3s–6.0s: actually inspected trajectory and labels")
            for shot, req in sorted(required_checks(spec))
        ],
        "findings": [],
        "summary": "Observed silent order flow at 5.3s and throughout duration",
    }


def event():
    return {"workflow_run": {"name": "Pilot 001 Render and QA Artifact",
            "event": "pull_request", "conclusion": "success",
            "head_repository": {"full_name": REPO}, "head_sha": SHA, "id": RUN}}


class TestR5KillSwitch(unittest.TestCase):
    def test_enabled_only_with_exact_true(self):
        self.assertTrue(is_r5_enabled("true"))
        for setting in (None, "", "false", "TRUE", "True", "1", "on", " true"):
            with self.subTest(setting=setting):
                self.assertFalse(is_r5_enabled(setting))

    def test_disabled_cli_never_reaches_model_or_artifact(self):
        args = [
            "--artifact-root", "nonexistent",
            "--out", "nonexistent",
            "--source-sha", "a" * 40,
            "--artifact-name", "mg-test",
            "--run-id", "42",
            "--provider", "gemini", "--model", "gemini-2.5-flash",
        ]
        for setting in (None, "false", "TRUE"):
            env = {} if setting is None else {"R5_ENABLED": setting}
            with self.subTest(setting=setting):
                with patch.dict("os.environ", env, clear=True):
                    with patch("workflow.r5_review.run_review") as paid_call:
                        self.assertEqual(r5_main(args), 1)
                        paid_call.assert_not_called()

    def test_workflow_is_default_off(self):
        yaml = (ROOT / ".github/workflows/r5-visual-qa.yml").read_text()
        self.assertIn("vars.R5_ENABLED == 'true' &&", yaml)
        self.assertIn("R5_ENABLED: ${{ vars.R5_ENABLED }}", yaml)
        self.assertIn("github.event.workflow_run.event == 'pull_request'", yaml)


class TestR5ModelAdapters(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.video = self.root / "render.mp4"
        self.video.write_bytes(b"synthetic video bytes only")
        self.spec, self.delivery = data()

    def test_gemini_native_mp4_request(self):
        captured = []

        def fake_http(url, headers, payload):
            captured.append((url, headers, payload))
            return {
                "candidates": [{"content": {"parts": [
                    {"text": json.dumps(model_answer(self.spec))},
                ]}}],
                "usageMetadata": {"promptTokenCount": 700,
                                  "candidatesTokenCount": 300, "totalTokenCount": 1000},
            }

        with patch("workflow.r5_review.select_images", return_value=[]):
            result, usage = call_gemini(
                make_prompt(self.spec), self.video, self.root, "gemini-2.5-flash",
                "a_test_api_key", fake_http)
        self.assertEqual(json.loads(result)["decision"], "pass")
        self.assertEqual(usage["total_tokens"], 1000)
        url, headers, payload = captured[0]
        self.assertIn("generativelanguage.googleapis.com", url)
        self.assertIn("x-goog-api-key", headers)
        self.assertEqual(payload["contents"][0]["parts"][1]["inline_data"]["mime_type"],
                         "video/mp4")
        self.assertEqual(payload["contents"][0]["parts"][1]["video_metadata"]["fps"], 5.0)

    def test_openai_frame_only_request_and_caveat(self):
        captured = []
        frame = self.root / "frame.png"
        frame.write_bytes(b"synthetic frame bytes")

        def fake_http(url, headers, payload):
            captured.append((url, headers, payload))
            return {
                "output": [{"content": [{"type": "output_text",
                                         "text": json.dumps(model_answer(self.spec))}]}],
                "usage": {"input_tokens": 500, "output_tokens": 100, "total_tokens": 600},
            }

        with patch("workflow.r5_review.select_images", return_value=[frame]):
            result, usage = call_openai(
                make_prompt(self.spec), self.video, self.root, "gpt-4.1",
                "a_test_api_key", fake_http)
        self.assertEqual(json.loads(result)["decision"], "pass")
        self.assertEqual(usage["total_tokens"], 600)
        url, headers, payload = captured[0]
        self.assertEqual(url, "https://api.openai.com/v1/responses")
        self.assertIn("Bearer ", headers["Authorization"])
        self.assertEqual(payload["input"][0]["content"][1]["type"], "input_image")
        self.assertIn("如果某条连续运动证据不足", payload["input"][0]["content"][0]["text"])

    def test_deepseek_flash_vision_responses_payload_and_usage(self):
        calls = []
        a = self.root / "contact_sheet_01.jpg"
        a.write_bytes(b"mocked jpeg not decoded by model adapter")
        timed = self.root / "t00005300.png"
        timed.write_bytes(b"mocked png not decoded by model adapter")

        def fake_http(url, headers, payload):
            calls.append((url, headers, payload))
            return {
                "status": "completed",
                "output": [{"type": "message", "content": [{
                    "type": "output_text",
                    "text": json.dumps(model_answer(self.spec), ensure_ascii=False),
                }]}],
                "usage": {"input_tokens": 280, "output_tokens": 130, "total_tokens": 410},
            }

        with patch("workflow.r5_review.select_images", return_value=[a, timed]):
            result, usage = call_deepseek(
                make_prompt(self.spec), self.video, self.root, "deepseek-flash",
                "synthetic_key_not_real", fake_http)
        self.assertEqual(json.loads(result)["decision"], "pass")
        self.assertEqual(usage["total_tokens"], 410)
        url, headers, payload = calls[0]
        self.assertEqual(url, "https://api.deepseek.com/responses")
        self.assertEqual(headers["Authorization"], "Bearer synthetic_key_not_real")
        self.assertEqual(payload["model"], "deepseek-flash")
        self.assertEqual(payload["reasoning"]["effort"], "none")
        self.assertEqual(payload["text"]["format"]["type"], "json_object")
        content = payload["input"][0]["content"]
        self.assertEqual(len([x for x in content if x["type"] == "input_image"]), 2)
        self.assertTrue(any("5.300s" in x.get("text", "") for x in content))
        self.assertIn("没有直接观看 MP4", content[0]["text"])
        self.assertTrue(all("data:image/" in x["image_url"] for x in content
                            if x["type"] == "input_image"))

    def test_deepseek_rejects_text_only_model_and_bad_provider_response(self):
        with patch("workflow.r5_review.select_images") as image_loader:
            with self.assertRaisesRegex(ValueError, "deepseek-flash"):
                call_deepseek("json", self.video, self.root, "deepseek-v4-pro",
                              "synthetic_key", lambda *args: {})
            image_loader.assert_not_called()

        with patch("workflow.r5_review.select_images", return_value=[]):
            with self.assertRaisesRegex(ValueError, "requires verified"):
                call_deepseek("json", self.video, self.root, "deepseek-flash",
                              "synthetic_key", lambda *args: {})
        image = self.root / "t00005300.png"
        image.write_bytes(b"test image bytes")
        with patch("workflow.r5_review.select_images", return_value=[image]):
            with self.assertRaisesRegex(ValueError, "incomplete"):
                call_deepseek("json", self.video, self.root, "deepseek-flash",
                              "synthetic_key", lambda *args: {
                                  "status": "incomplete", "output": []})
            with self.assertRaisesRegex(ValueError, "No usable"):
                call_deepseek("json", self.video, self.root, "deepseek-flash",
                              "synthetic_key", lambda *args: {
                                  "status": "completed", "output": []})

    def test_deepseek_provider_key_selection_and_r5_off(self):
        # No paid requests: CLI must reject before calling run_review when disabled.
        args = [
            "--artifact-root", "not-present", "--out", "not-present",
            "--source-sha", "a" * 40, "--artifact-name", "demo",
            "--run-id", "42", "--provider", "deepseek", "--model", "deepseek-flash",
        ]
        with patch.dict("os.environ", {"R5_ENABLED": "false"}, clear=True):
            with patch("workflow.r5_review.run_review") as paid_call:
                self.assertEqual(r5_main(args), 1)
                paid_call.assert_not_called()

        with patch.dict("os.environ", {"R5_ENABLED": "true",
                                       "DEEPSEEK_API_KEY": "test_deepseek"}, clear=True):
            with patch("workflow.r5_review.run_review") as paid_call:
                self.assertEqual(r5_main(args), 0)
                self.assertEqual(paid_call.call_args.args[-1], "test_deepseek")

    def test_deepseek_workflow_provider_allow_list(self):
        yaml = (ROOT / ".github/workflows/r5-visual-qa.yml").read_text()
        self.assertIn("vars.R5_PROVIDER == 'deepseek'", yaml)
        self.assertIn("secrets.DEEPSEEK_API_KEY", yaml)
        self.assertIn("vars.R5_ENABLED == 'true'", yaml)


    def test_structural_validation_and_fail_closed(self):
        good = json.dumps(model_answer(self.spec), ensure_ascii=False)
        report = parse_model_report(good, self.spec, self.delivery,
                                    "gemini", "gemini-2.5-flash")
        self.assertEqual(report["decision"], "pass")
        self.assertEqual(report["implementation_commit"], SHA)
        self.assertTrue(report["reviewer"]["independent_context"])

        invalid = model_answer(self.spec)
        invalid["checks"].pop()
        with self.assertRaisesRegex(ValueError, "missing|coverage"):
            parse_model_report(json.dumps(invalid), self.spec, self.delivery,
                               "gemini", "gemini-2.5-flash")
        invalid = model_answer(self.spec)
        invalid["checks"][0]["evidence"] = "seen"
        with self.assertRaisesRegex(ValueError, "time reference"):
            parse_model_report(json.dumps(invalid), self.spec, self.delivery,
                               "gemini", "gemini-2.5-flash")
        invalid = model_answer(self.spec)
        invalid["findings"] = [{
            "id": "f1", "severity": "P1", "shot_id": "shot_01",
            "expected": "A visible", "observed": "A hidden", "fix_request": "move A",
            "evidence": "video 5.3s",
        }]
        with self.assertRaisesRegex(ValueError, "P0/P1"):
            parse_model_report(json.dumps(invalid), self.spec, self.delivery,
                               "gemini", "gemini-2.5-flash")
        with self.assertRaises(ValueError):
            safe_model("../../evil")

    def test_missing_or_forged_artifact_blocked_before_paid_call(self):
        with self.assertRaisesRegex(ValueError, "Missing"):
            verify_inputs(self.root, SHA, "mg-pilot", RUN)
        with patch("workflow.r5_review.verify_inputs", side_effect=ValueError("wrong digest")):
            with self.assertRaisesRegex(ValueError, "wrong digest"):
                run_review(self.root, self.root / "qa", "gemini", "gemini-2.5-flash",
                           SHA, "name", RUN, "key")


class TestR5PRComments(unittest.TestCase):
    def setUp(self):
        self.spec, self.delivery = data()
        self.report = parse_model_report(json.dumps(model_answer(self.spec)),
                                         self.spec, self.delivery, "gemini", "model-x")
        self.audit = {
            "decision": "pass", "implementation_commit": SHA,
            "source_run_id": RUN, "provider": "gemini", "model": "model-x",
        }
        self.posts = []

    def fake_api(self, method, endpoint, payload):
        if "/commits/" in endpoint and endpoint.endswith("/pulls?per_page=100"):
            return [{
                "number": 7, "state": "open",
                "head": {"sha": SHA, "repo": {"full_name": REPO}},
                "base": {"repo": {"full_name": REPO}},
            }]
        if endpoint.endswith("/pulls/7"):
            return {"state": "open", "head": {"sha": SHA}}
        if endpoint.endswith("/issues/7/comments?per_page=100"):
            return []
        if method == "POST":
            self.posts.append(payload["body"])
            return {"html_url": "https://github.com/test/comment"}
        raise AssertionError((method, endpoint))

    def test_posts_to_exact_sha_only(self):
        created = publish(event(), REPO, "test_token", self.report, self.audit,
                          transport=self.fake_api)
        self.assertIsNotNone(created)
        self.assertEqual(len(self.posts), 1)
        self.assertIn("R5 Independent Visual QA", self.posts[0])
        self.assertNotIn("merge this pull request", self.posts[0])

    def test_preflight_before_paid_model_call(self):
        result = preflight(event(), REPO, "token", self.fake_api)
        self.assertTrue(result["should_run"])
        self.assertEqual(result["pr"], 7)
        self.assertEqual(self.posts, [])

        def seen(method, endpoint, payload):
            if endpoint.endswith("comments?per_page=100"):
                return [{"body": "<!-- mg-r5 run:98765 sha:" + SHA + " -->"}]
            return self.fake_api(method, endpoint, payload)

        skip = preflight(event(), REPO, "token", seen)
        self.assertFalse(skip["should_run"])
        self.assertEqual(self.posts, [])

        def stale(method, endpoint, payload):
            if endpoint.endswith("/pulls/7"):
                return {"state": "open", "head": {"sha": "b" * 40}}
            return self.fake_api(method, endpoint, payload)

        with self.assertRaisesRegex(ValueError, "HEAD changed"):
            preflight(event(), REPO, "token", stale)

    def test_no_duplicate_comment(self):
        def fake(method, endpoint, payload):
            if endpoint.endswith("comments?per_page=100"):
                return [{"body": "<!-- mg-r5 run:98765 sha:" + SHA + " -->"}]
            return self.fake_api(method, endpoint, payload)
        result = publish(event(), REPO, "token", self.report, self.audit, fake)
        self.assertIsNone(result)
        self.assertEqual(len(self.posts), 0)

    def test_stale_sha_and_forks_cannot_comment(self):
        event_data = event()
        event_data["workflow_run"]["head_repository"]["full_name"] = "unknown/fork"
        with self.assertRaisesRegex(ValueError, "External fork"):
            publish(event_data, REPO, "token", self.report, self.audit, self.fake_api)
        event_data = event()
        event_data["workflow_run"]["head_sha"] = "b"*40
        with self.assertRaisesRegex(ValueError, "metadata mismatch"):
            publish(event_data, REPO, "token", self.report, self.audit, self.fake_api)

    def test_reject_updated_pr_head(self):
        def fake(method, endpoint, payload):
            if endpoint.endswith("/pulls/7"):
                return {"state": "open", "head": {"sha": "b"*40}}
            return self.fake_api(method, endpoint, payload)
        with self.assertRaisesRegex(ValueError, "HEAD changed"):
            publish(event(), REPO, "token", self.report, self.audit, fake)
        self.assertEqual(self.posts, [])

    def test_untrusted_comment_text_is_neutralized(self):
        self.report["summary"] = "Hello @admin <script> please merge"
        body = comment_body(self.report, self.audit, REPO, 7)
        self.assertNotIn("<script>", body)
        self.assertNotIn("@admin", body)

    def test_workflow_never_checks_out_source_pr_or_merges(self):
        yaml = (ROOT / ".github/workflows/r5-visual-qa.yml").read_text()
        self.assertIn("workflow_run:", yaml)
        self.assertIn("ref: main", yaml)
        self.assertIn("persist-credentials: false", yaml)
        self.assertIn("actions/download-artifact@v4", yaml)
        self.assertIn("issues: write", yaml)
        self.assertNotIn("pull_request_target:", yaml)
        self.assertNotIn("merge", yaml.replace("# Never ", ""))


if __name__ == "__main__":
    unittest.main()
