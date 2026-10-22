"""No network or Azure dependency: guardrails for TTS previews."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from studio.tts_providers import VoiceRequest, TTSError, available_providers, synthesize_preview

class TTSBoundaryTests(unittest.TestCase):
    def test_edge_registered_without_paid_backends(self):
        self.assertIn("edge", available_providers())
        self.assertNotIn("gemini", available_providers())
        self.assertNotIn("fish", available_providers())

    def test_provider_failure_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(TTSError, "Unsupported TTS provider"):
                asyncio.run(synthesize_preview(VoiceRequest("你好"), Path(tmp)/"preview", provider="fish"))

    def test_never_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileExistsError):
                asyncio.run(synthesize_preview(VoiceRequest("你好"), Path(tmp)))

    def test_empty_text_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                asyncio.run(synthesize_preview(VoiceRequest(" "), Path(tmp)/"preview"))

    def test_requires_ffmpeg_without_network(self):
        with tempfile.TemporaryDirectory() as tmp, patch("studio.tts_providers.shutil.which", return_value=None):
            with self.assertRaisesRegex(TTSError, "ffmpeg"):
                asyncio.run(synthesize_preview(VoiceRequest("你好"), Path(tmp)/"preview"))

if __name__ == "__main__":
    unittest.main()
