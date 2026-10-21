import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from studio import settings

class SettingsTests(unittest.TestCase):
    def test_proxy_and_toggle_persist_without_secret(self):
        with tempfile.TemporaryDirectory() as d:
            repo=Path(d)
            data={"r5_enabled":True,"proxy_mode":"custom","proxy_url":"http://127.0.0.1:7897"}
            settings.save(repo,data)
            self.assertEqual(settings.load(repo),data)
            self.assertNotIn("api_key",settings.settings_path(repo).read_text())
            self.assertEqual(settings.settings_path(repo).stat().st_mode & 0o777,0o600)

    def test_invalid_proxy_and_unknown_fields_rejected(self):
        with self.assertRaises(ValueError):
            settings.validate({"r5_enabled":True,"proxy_mode":"custom",
                               "proxy_url":"http://user:password@proxy.local:7897"})
        with self.assertRaises(ValueError):
            settings.validate({**settings.DEFAULT,"api_key":"should-not-be-here"})

    def test_key_saved_only_via_security_stdin(self):
        class Response:
            returncode=0
        with patch("studio.settings._security",return_value=Response()) as call:
            settings.save_key("sk-example")
            args=call.call_args.args
            self.assertNotIn("sk-example",args)
            self.assertIn("sk-example",call.call_args.kwargs["input_text"])

if __name__=="__main__":
    unittest.main()
