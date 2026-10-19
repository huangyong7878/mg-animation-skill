"""Lifecycle regression tests for the GitHub-backed MG model orchestrator."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from workflow.orchestrator import (
    prepare, publish, receive, make_review, record_qa, release_check,
    feedback, load_state, canonical_digest, read_json,
)


class FakeRun:
    def __init__(self, head=None):
        self.calls = []
        self.head = head or "a"*40

    def __call__(self, args, check, capture_output, text):
        self.calls.append(args)
        if args[1:3] == ["issue", "create"]:
            stdout = "https://github.com/example/mg/issues/3\n"
        elif args[1:3] == ["pr", "view"]:
            stdout = json.dumps({"headRefOid": self.head,
                                 "url": "https://github.com/example/mg/pull/9",
                                 "state": "OPEN"})
        elif args[1:3] == ["pr", "comment"]:
            stdout = "https://github.com/example/mg/pull/9#issuecomment-1\n"
        else:
            raise AssertionError(args)
        return type("Completed", (), {"stdout": stdout})()


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workdir = self.root / "work"
        self.artifact_root = self.root / "artifacts"
        self.artifact_root.mkdir()
        self.spec_file = ROOT / "examples" / "workflow_orders_spec.json"
        self.delivery_example = ROOT / "examples" / "workflow_orders_delivery.json"
        self.prepare()

    def prepare(self):
        self.state = prepare(self.spec_file, self.workdir, "muse")
        self.spec = read_json(self.workdir/"director_spec.json")

    def delivery(self, attempt=1, commit="a"*40):
        artifact = {
            "shots/shot_01.py": b"example source",
            "previews/shot_01_silent.mp4": b"mock video",
            "previews/shot_01_frame_06.png": b"mock frame",
        }
        for relative, data in artifact.items():
            path = self.artifact_root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        value = json.loads(self.delivery_example.read_text(encoding="utf-8"))
        value.update(attempt=attempt, status="ready_for_qa",
                     spec_sha256=canonical_digest(self.spec),
                     implementation_commit=commit)
        target = self.root / ("delivery_%s.json" % attempt)
        target.write_text(json.dumps(value), encoding="utf-8")
        return target

    def qa(self, decision="pass", finding=False):
        value = read_json(self.workdir / "qa_template.json")
        value["reviewer"] = {"name": "independent_strong_model", "independent_context": True}
        value["decision"] = decision
        value["summary"] = "Reviewed mock files for a metadata-only unit test."
        if decision == "pass":
            for check in value["checks"]:
                check["result"] = "pass"
                check["evidence"] = "synthetic test, not real video QA"
        if finding:
            value["findings"] = [{
                "id": "F001", "severity": "P0", "shot_id": "shot_01",
                "expected": "Order A arrives at shipping",
                "observed": "Order A disappears",
                "fix_request": "Keep object identity and continuous path",
                "evidence": "Synthetic example",
                "timestamp_s": 5.5,
            }]
        path = self.root/"qa.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_prepare_creates_pinned_task_and_refuses_overwrite(self):
        self.assertEqual(self.state["status"], "prepared")
        self.assertIn(canonical_digest(self.spec),
                      (self.workdir/"executor_task.md").read_text(encoding="utf-8"))
        with self.assertRaisesRegex(ValueError, "not empty"):
            prepare(self.spec_file, self.workdir)

    def test_issue_publish_is_explicit_and_idempotent(self):
        fake = FakeRun()
        result = publish(self.workdir, "example/mg", dry_run=True, runner=fake)
        self.assertTrue(result["dry_run"])
        self.assertEqual(fake.calls, [])
        self.assertEqual(load_state(self.workdir)[1]["status"], "prepared")
        result = publish(self.workdir, "example/mg", runner=fake)
        self.assertIn("/issues/3", result["issue_url"])
        with self.assertRaisesRegex(ValueError, "only be published once"):
            publish(self.workdir, "example/mg", runner=fake)
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(fake.calls[0][0], "gh")

    def test_receive_review_qa_pass_and_release_blocks_draft(self):
        delivery_path = self.delivery()
        receive(self.workdir, delivery_path, self.artifact_root)
        self.assertEqual(load_state(self.workdir)[1]["status"], "implementation_received")
        paths = make_review(self.workdir)
        self.assertTrue(Path(paths["review_task"]).is_file())
        template = read_json(self.workdir / "qa_template.json")
        self.assertEqual(template["decision"], "pending")
        self.assertTrue(all(x["result"] == "needs_review" for x in template["checks"]))
        self.assertEqual(record_qa(self.workdir, self.qa())["status"], "qa_passed")
        with self.assertRaisesRegex(ValueError, "Release blocked"):
            release_check(self.workdir, self.artifact_root)

    def test_qa_two_reworks_escalate_and_old_report_does_not_carry(self):
        receive(self.workdir, self.delivery(1), self.artifact_root)
        make_review(self.workdir)
        self.assertEqual(record_qa(self.workdir, self.qa("rework", True))["status"],
                         "rework_requested")
        rework = (self.workdir/"rework_task.md").read_text(encoding="utf-8")
        self.assertIn("Keep object identity", rework)
        receive(self.workdir, self.delivery(2, "b"*40), self.artifact_root)
        make_review(self.workdir)
        self.assertEqual(record_qa(self.workdir, self.qa("rework", True), 2)["status"],
                         "escalation_required")
        with self.assertRaisesRegex(ValueError, "Cannot receive delivery"):
            receive(self.workdir, self.delivery(3, "c"*40), self.artifact_root)

    def test_qa_rejects_stale_git_commit(self):
        receive(self.workdir, self.delivery(), self.artifact_root)
        make_review(self.workdir)
        old_report = read_json(self.workdir/"qa_template.json")
        old_report["implementation_commit"] = "f"*40
        path = self.root/"old.json"
        path.write_text(json.dumps(old_report), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "implementation_commit"):
            record_qa(self.workdir, path)

    def test_receive_verifies_pr_head_and_rejects_mismatch(self):
        fake = FakeRun(head="b"*40)
        with self.assertRaisesRegex(ValueError, "does not match current PR HEAD"):
            receive(self.workdir, self.delivery(), self.artifact_root,
                    "example/mg", "9", runner=fake)
        fake.head = "a"*40
        result = receive(self.workdir, self.delivery(), self.artifact_root,
                         "example/mg", "9", runner=fake)
        self.assertEqual(result["implementation_pr_url"],
                         "https://github.com/example/mg/pull/9")

    def test_missing_or_escaping_artifacts_block_receive(self):
        target = self.delivery()
        data = read_json(target)
        data["artifacts"]["video_path"] = "../outside.mp4"
        target.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "path outside"):
            receive(self.workdir, target, self.artifact_root)
        data["artifacts"]["video_path"] = "missing.mp4"
        target.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing/empty"):
            receive(self.workdir, target, self.artifact_root)

    def test_feedback_dry_run_and_verified_head(self):
        receive(self.workdir, self.delivery(), self.artifact_root)
        make_review(self.workdir)
        record_qa(self.workdir, self.qa("rework", True))
        fake = FakeRun()
        self.assertTrue(feedback(self.workdir, "example/mg", "9", dry_run=True,
                                 runner=fake)["dry_run"])
        self.assertEqual(fake.calls, [])
        fake.head = "b"*40
        with self.assertRaisesRegex(ValueError, "PR advanced"):
            feedback(self.workdir, "example/mg", "9", runner=fake)
        fake.head = "a"*40
        self.assertIn("comment", feedback(self.workdir, "example/mg", "9",
                                          runner=fake))
        self.assertEqual(fake.calls[-1][1:3], ["pr", "comment"])


if __name__ == "__main__":
    unittest.main()
