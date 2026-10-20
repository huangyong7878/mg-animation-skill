"""Evidence sampling and portable QA bundle integration tests (no real video claim)."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from workflow.check_handoff import canonical_digest
from workflow.qa_evidence import (
    create_evidence, verify_evidence, timeline_samples, check_spec, load_json,
)
from workflow.role_pack import main as role_pack_main

ROOT = Path(__file__).resolve().parents[1]


class FakeMediaRunner:
    """Return synthetic ffprobe metadata and valid generated PNGs, no real MP4."""

    def __init__(self, width=960):
        self.commands = []
        self.width = width

    def __call__(self, argv, check=True, capture_output=True, text=True):
        self.commands.append(argv)
        if argv[0] == "ffprobe":
            payload = {"streams": [{
                "width": self.width, "height": 540,
                "avg_frame_rate": "24/1", "nb_frames": "312",
            }], "format": {"duration": "13.000"}}
            return SimpleNamespace(stdout=json.dumps(payload))
        if argv[0] == "ffmpeg":
            Image.new("RGB", (320, 180), "purple").save(argv[-1])
            return SimpleNamespace(stdout="")
        raise AssertionError(f"unexpected command: {argv}")


class QAEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.spec_path = ROOT / "examples/workflow_orders_spec.json"
        self.spec = load_json(self.spec_path)
        self.video = self.root / "silent.mp4"
        self.video.write_bytes(b"synthetic test bytes; not an actual mp4")
        self.evidence_dir = self.root / "evidence"

    def make_evidence(self):
        return create_evidence(
            self.spec_path, self.video, self.evidence_dir,
            interval=3, focus=[5.3], radius=0.4,
            focus_step=0.2, max_frames=40,
            runner=FakeMediaRunner())

    def test_focus_produces_contiguous_timestamped_frames(self):
        result = self.make_evidence()
        self.assertEqual(result["video"]["width"], 960)
        self.assertEqual(result["video"]["duration_s"], 13)
        self.assertEqual(result["director"]["spec_sha256"], canonical_digest(self.spec))
        stamps = [round(f["requested_time_s"], 1) for f in result["frames"]]
        for target in (4.9, 5.1, 5.3, 5.5, 5.7):
            self.assertIn(target, stamps)
        self.assertTrue(all(f["shot_id"] == "shot_01" for f in result["frames"]))
        self.assertTrue(any("focus_center" in f["reasons"] for f in result["frames"]))
        self.assertEqual(verify_evidence(self.evidence_dir, self.video, self.spec_path), [])
        self.assertTrue((self.evidence_dir / "contact_sheet_01.jpg").is_file())

    def test_tamper_detected(self):
        record = self.make_evidence()
        file = self.evidence_dir / record["frames"][0]["filename"]
        file.write_bytes(b"tampered")
        self.assertTrue(any("checksum mismatch" in e for e in
                            verify_evidence(self.evidence_dir, self.video, self.spec_path)))

    def test_spec_hash_or_video_hash_mismatch_detected(self):
        self.make_evidence()
        self.video.write_bytes(b"replaced video")
        self.assertTrue(any("video SHA" in e for e in
                            verify_evidence(self.evidence_dir, self.video, self.spec_path)))

    def test_wrong_resolution_blocks_before_extraction(self):
        fake = FakeMediaRunner(width=640)
        with self.assertRaisesRegex(ValueError, "resolution"):
            create_evidence(self.spec_path, self.video, self.evidence_dir, runner=fake)
        self.assertFalse(self.evidence_dir.exists())

    def test_sampling_cap_and_out_of_range_focus(self):
        with self.assertRaisesRegex(ValueError, "max.frames|exceed"):
            timeline_samples(self.spec, 13, 24, 0.05, [], 0.5, 0.1, 20)
        with self.assertRaisesRegex(ValueError, "outside video"):
            timeline_samples(self.spec, 13, 24, 1, [99], 0.4, 0.2, 50)

    def test_refuses_evidence_output_overwrite(self):
        self.make_evidence()
        with self.assertRaisesRegex(ValueError, "not empty"):
            self.make_evidence()

    def test_role_pack_qa_includes_verified_evidence_and_pending_template(self):
        self.make_evidence()
        delivery = load_json(ROOT / "examples/workflow_orders_delivery.json")
        delivery["status"] = "ready_for_qa"
        delivery["spec_sha256"] = canonical_digest(self.spec)
        delivery_path = self.root / "delivery.json"
        delivery_path.write_text(json.dumps(delivery), encoding="utf-8")
        output = self.root / "qa_package"
        args = ["qa", "--spec", str(self.spec_path),
                "--delivery", str(delivery_path), "--video", str(self.video),
                "--evidence-dir", str(self.evidence_dir), "--out", str(output)]
        self.assertEqual(role_pack_main(args), 0)
        with zipfile.ZipFile(output.with_suffix(".zip")) as archive:
            names = archive.namelist()
            self.assertIn("media/evidence/evidence_index.json", names)
            self.assertIn("media/evidence/contact_sheet_01.jpg", names)
            self.assertTrue(any(path.startswith("media/evidence/frames/") for path in names))
            qa = json.loads(archive.read("outputs/qa_template.json"))
            self.assertEqual(qa["decision"], "pending")
        # A changed evidence image must reject the bundle.
        first_file = load_json(self.evidence_dir / "evidence_index.json")["frames"][0]["filename"]
        (self.evidence_dir / first_file).write_bytes(b"changed")
        self.assertEqual(role_pack_main(args[:-1] + [str(self.root / "qa_bad")]), 1)


class AgentRouterDocumentTests(unittest.TestCase):
    def test_root_agent_routing_and_guardrails(self):
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for role in ("R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7"):
            self.assertIn(role, text)
        for required in ("docs/MULTI_MODEL_PLAYBOOK.md", "roles/REVIEWER.md",
                         "roles/DIRECTOR.md", "roles/REWORK_SUPERVISOR.md",
                         "workflow/qa_evidence.py", "workflow/check_handoff.py",
                         "workflow/role_pack.py"):
            self.assertIn(required, text)
            self.assertTrue((ROOT / required).is_file(), required)
        self.assertIn("pending", text)
        self.assertIn("不自行合并", text)


if __name__ == "__main__":
    unittest.main()
