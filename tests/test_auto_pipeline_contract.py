"""Tests optional Visual Contract gating in the existing two-stage render entry."""
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_pipeline_with_lightweight_stubs():
    """Only test orchestration; do not require TTS, fonts, FFmpeg or web APIs."""
    narrate = types.ModuleType("narrate")
    narrate.create_narration = lambda *a, **kw: None
    validate = types.ModuleType("validate")
    validate.validate = lambda d: []
    engine = types.ModuleType("engine")
    engine.load = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
    with mock.patch.dict(sys.modules, {"narrate": narrate, "validate": validate, "engine": engine}):
        spec = importlib.util.spec_from_file_location("auto_pipeline_contract_test", ROOT/"scripts"/"auto_pipeline.py")
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(ROOT/"scripts"))
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path.pop(0)
    return module


class AutoPipelineContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = load_pipeline_with_lightweight_stubs()

    def make_data(self, root, covered):
        root.joinpath("voice.wav").write_bytes(b"mock")
        root.joinpath("timings.json").write_text('{"segments":[]}', encoding="utf-8")
        scene = root/"scene.json"
        scene.write_text(json.dumps({"scenes": [{"id": "shot_02", "elements": [
            {"type": "text", "contract": "soil"} if covered else {"type": "text"}
        ]}]}), encoding="utf-8")
        contract = root/"contract.json"
        contract.write_text(json.dumps({
            "shot_id": "shot_02", "silent_downgrade": True,
            "must_show": [{"id": "soil"}], "continuous_motion": []
        }), encoding="utf-8")
        return scene, contract

    def test_missing_tag_blocks_render_even_when_downgrade_allowed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scene, contract = self.make_data(root, False)
            with mock.patch.object(self.pipeline.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "Visual Contract blocked render"):
                    self.pipeline.stage_render(str(scene), str(root), str(contract))
                run.assert_not_called()
            report = json.loads(root.joinpath("contract_report.json").read_text(encoding="utf-8"))
            self.assertFalse(report["passed"])
            self.assertEqual(report["missing"], ["soil"])

    def test_valid_contract_passes_caption_timings_to_renderer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scene, contract = self.make_data(root, True)
            with mock.patch.object(self.pipeline.subprocess, "run") as run:
                output = self.pipeline.stage_render(str(scene), str(root), str(contract))
            self.assertEqual(output.name, "scene.mp4")
            self.assertEqual(run.call_count, 2)
            renderer_command = run.call_args_list[0].args[0]
            self.assertIn("--timings", renderer_command)
            self.assertEqual(renderer_command[renderer_command.index("--timings") + 1],
                             str(root/"timings.json"))
            self.assertTrue(json.loads(root.joinpath("contract_report.json").read_text(encoding="utf-8"))["passed"])


if __name__ == "__main__":
    unittest.main()
