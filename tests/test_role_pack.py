"""Portable strong-model director/QA/rework bundle tests.

No external model API, real render, or GitHub mutation occurs in these tests.
"""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from workflow.role_pack import (
    director, qa, rework, finalize, get_dir, qa_template, read_json,
    main, ROOT,
)
from workflow.check_handoff import canonical_digest, required_checks


class PortableRolePackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.spec_path = ROOT / "examples" / "workflow_orders_spec.json"
        self.delivery_original = ROOT / "examples" / "workflow_orders_delivery.json"
        self.spec = read_json(self.spec_path)
        self.delivery = read_json(self.delivery_original)

    def path(self, name, payload):
        target = self.base / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, (bytes, bytearray)):
            target.write_bytes(payload)
        else:
            target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return target

    def test_director_creates_self_contained_zip_and_refuses_overwrite(self):
        brief = self.path("brief.md", b"Why do identical orders take different routes?")
        out = self.base / "director"
        self.assertEqual(main(["director", "--brief", str(brief), "--out", str(out)]), 0)
        archive = out.with_suffix(".zip")
        self.assertTrue(archive.is_file())
        with zipfile.ZipFile(archive) as z:
            names = set(z.namelist())
            self.assertIn("START_HERE.md", names)
            self.assertIn("role.md", names)
            self.assertIn("quality_rubric.md", names)
            self.assertIn("contract.schema.json", names)
            self.assertIn("inputs/brief.md", names)
            self.assertIn("references/creative-director.md", names)
            manifest = json.loads(z.read("manifest.json"))
            self.assertIn("role.md", manifest["files"])
        self.assertEqual(main(["director", "--brief", str(brief), "--out", str(out)]), 1)

    def test_qa_template_matches_schema_requirements_and_commit(self):
        tmpl = qa_template(self.spec, self.delivery)
        self.assertEqual(tmpl["decision"], "pending")
        self.assertFalse(tmpl["reviewer"]["independent_context"])
        self.assertEqual(tmpl["spec_sha256"], canonical_digest(self.spec))
        actual = {(x["shot_id"], x["requirement_id"]) for x in tmpl["checks"]}
        self.assertEqual(actual, required_checks(self.spec))
        self.assertTrue(all(x["result"] == "needs_review" for x in tmpl["checks"]))

    def test_qa_requires_real_media_file_and_matching_delivery(self):
        delivery = dict(self.delivery, status="ready_for_qa")
        dp = self.path("delivery.json", delivery)
        out = self.base / "qa"
        self.assertEqual(main([
            "qa", "--spec", str(self.spec_path),
            "--delivery", str(dp), "--video", str(self.base/"missing.mp4"),
            "--out", str(out),
        ]), 1)
        self.assertFalse(out.with_suffix(".zip").exists())

    def test_qa_package_has_video_and_no_source_files(self):
        delivery = dict(self.delivery, status="ready_for_qa")
        dp = self.path("delivery.json", delivery)
        video = self.path("render.mp4", b"synthetic test bytes; not an actual rendered video")
        frame = self.path("frame.png", b"synthetic test pixels")
        out = self.base / "qa"
        self.assertEqual(main([
            "qa", "--spec", str(self.spec_path), "--delivery", str(dp),
            "--video", str(video), "--frame", str(frame), "--out", str(out),
        ]), 0)
        with zipfile.ZipFile(out.with_suffix(".zip")) as z:
            names = set(z.namelist())
            self.assertIn("inputs/director_spec.json", names)
            self.assertIn("inputs/delivery.json", names)
            self.assertIn("media/render.mp4", names)
            self.assertIn("media/frames/000_frame.png", names)
            self.assertIn("outputs/qa_template.json", names)
            self.assertNotIn("shots/shot_01.py", names)
            qa_json = json.loads(z.read("outputs/qa_template.json"))
            self.assertEqual(qa_json["decision"], "pending")

    def test_qa_rejects_stale_spec_digest(self):
        delivery = dict(self.delivery, status="ready_for_qa", spec_sha256="f"*64)
        dp = self.path("delivery.json", delivery)
        video = self.path("render.mp4", b"test")
        self.assertEqual(main(["qa", "--spec", str(self.spec_path), "--delivery",
                               str(dp), "--video", str(video),
                               "--out", str(self.base/"qa")]), 1)

    def test_rework_requires_failed_qa_same_commit(self):
        report = qa_template(self.spec, self.delivery)
        report["decision"] = "rework"
        report["summary"] = "Order B wrongly shipped"
        report["findings"] = [{
            "id": "F1", "severity": "P0", "shot_id": "shot_01",
            "expected": "B waits for stock", "observed": "B is shipped",
            "fix_request": "Correct B route", "evidence": "video: 7.0–8.0s",
            "timestamp_s": 7,
        }]
        qp = self.path("qa.json", report)
        out = self.base / "rework"
        self.assertEqual(main(["rework", "--spec", str(self.spec_path),
                               "--delivery", str(self.delivery_original),
                               "--qa", str(qp), "--out", str(out)]), 0)
        self.assertIn("Correct B route", (out/"START_HERE.md").read_text(encoding="utf-8"))
        report["implementation_commit"] = "wrongcommit"
        stale = self.path("stale.json", report)
        self.assertEqual(main(["rework", "--spec", str(self.spec_path),
                               "--delivery", str(self.delivery_original),
                               "--qa", str(stale),
                               "--out", str(self.base/"stale")]), 1)

    def test_rework_rejects_pass_report(self):
        report = qa_template(self.spec, self.delivery)
        report["decision"] = "pass"
        report["reviewer"]["independent_context"] = True
        for c in report["checks"]:
            c.update(result="pass", evidence="synthetic test")
        qp = self.path("passed.json", report)
        self.assertEqual(main(["rework", "--spec", str(self.spec_path),
                               "--delivery", str(self.delivery_original),
                               "--qa", str(qp),
                               "--out", str(self.base/"reject")]), 1)


if __name__ == "__main__":
    unittest.main()
