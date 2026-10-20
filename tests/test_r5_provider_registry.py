"""Provider registry contract: extensible without changing R0 state machine."""
import unittest
from unittest.mock import patch
from workflow import r5_registry

class RegistryTests(unittest.TestCase):
    def test_registered_provider_is_capability_limited(self):
        provider = r5_registry.select_provider("deepseek")
        self.assertIn("sampled_images", provider.modalities)
        self.assertFalse(provider.can_verify_audio)
        self.assertFalse(provider.can_verify_full_motion)

    def test_unknown_provider_rejected_before_external_call(self):
        with self.assertRaisesRegex(ValueError, "Unsupported R5 provider"):
            r5_registry.run_review("not-implemented", "unused", "unused")

    def test_visual_provider_cannot_claim_pass(self):
        with patch("workflow.r5_provider.review_deepseek",
                   return_value={"status": "pass"}):
            with self.assertRaisesRegex(ValueError, "must remain pending"):
                r5_registry.run_review("deepseek", "work", "artifacts")

    def test_provider_dispatch_preserves_pending(self):
        with patch("workflow.r5_provider.review_deepseek",
                   return_value={"status": "pending", "evidence": "x"}) as fake:
            result = r5_registry.run_review("deepseek", "work", "artifacts")
            self.assertEqual(result["status"], "pending")
            fake.assert_called_once_with("work", "artifacts")

    def test_parser_gets_implemented_choices(self):
        from workflow.orchestrator import build_parser
        parser = build_parser()
        args = parser.parse_args(["review","--workdir","w","--artifact-root","a",
                                  "--provider","deepseek"])
        self.assertEqual(args.provider, "deepseek")
        self.assertIsNone(args.model)

if __name__ == "__main__":
    unittest.main()
