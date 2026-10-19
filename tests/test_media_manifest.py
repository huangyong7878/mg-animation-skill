"""Media manifest regression tests (synthetic byte fixtures, not real video QA)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from workflow.check_handoff import canonical_digest
from workflow.media_manifest import create_manifest, verify_manifest, main


class MediaManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.spec = json.loads((ROOT/"examples/workflow_orders_spec.json").read_text(encoding="utf-8"))
        self.delivery = json.loads((ROOT/"examples/workflow_orders_delivery.json").read_text(encoding="utf-8"))
        self.delivery.update(
            spec_sha256=canonical_digest(self.spec),
            implementation_commit="a"*40,
            status="ready_for_qa")
        artifacts = self.delivery["artifacts"]
        artifacts["video_path"] = "media/shot_01_silent.mp4"
        artifacts["keyframe_paths"] = ["media/keyframes/shot_01_005000.png"]
        for relative, content in [
            ("media/shot_01_silent.mp4", b"synthetic bytes; not real mp4"),
            ("media/keyframes/shot_01_005000.png", b"synthetic bytes; not real PNG")]:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

    def test_create_verify_roundtrip(self):
        value = create_manifest(self.spec, self.delivery, self.root, "actions",
                                artifact_name="mg-orders_two_routes-r1-a1-aaaaaaaaaaaa",
                                run_url="https://github.com/example/mg/actions/runs/123")
        self.assertEqual(len(value["files"]), 2)
        self.assertEqual(value["spec_sha256"], canonical_digest(self.spec))
        self.assertEqual(verify_manifest(value, self.root, self.spec, self.delivery), [])

    def test_tamper_detection(self):
        value = create_manifest(self.spec, self.delivery, self.root, "local")
        self.root.joinpath("media/shot_01_silent.mp4").write_bytes(b"tampered")
        errors = verify_manifest(value, self.root)
        self.assertTrue(any("mismatch" in issue for issue in errors), errors)

    def test_path_escape_blocked(self):
        self.delivery["artifacts"]["video_path"] = "../other.mp4"
        with self.assertRaisesRegex(ValueError, "escapes artifact root"):
            create_manifest(self.spec, self.delivery, self.root, "local")

    def test_stale_spec_blocked(self):
        self.delivery["spec_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "Invalid handoff"):
            create_manifest(self.spec, self.delivery, self.root, "local")

    def test_actions_requires_artifact_name(self):
        with self.assertRaisesRegex(ValueError, "artifact-name"):
            create_manifest(self.spec, self.delivery, self.root, "actions")

    def test_external_requires_https(self):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            create_manifest(self.spec, self.delivery, self.root, "external")
        value = create_manifest(self.spec, self.delivery, self.root, "external",
                                location_url="https://storage.example.org/clip.zip")
        self.assertEqual(value["storage"]["location_url"],
                         "https://storage.example.org/clip.zip")

    def test_cli_create_and_verify(self):
        spec = self.root/"director_spec.json"
        delivery = self.root/"delivery.json"
        manifest = self.root/"media_manifest.json"
        spec.write_text(json.dumps(self.spec, ensure_ascii=False), encoding="utf-8")
        delivery.write_text(json.dumps(self.delivery, ensure_ascii=False), encoding="utf-8")
        args = ["--artifact-root", str(self.root)]
        self.assertEqual(main(["create", "--spec", str(spec), "--delivery", str(delivery),
                               *args, "--out", str(manifest)]), 0)
        self.assertTrue(manifest.exists())
        self.assertEqual(main(["verify", "--manifest", str(manifest), *args,
                               "--spec", str(spec), "--delivery", str(delivery)]), 0)


if __name__ == "__main__":
    unittest.main()
