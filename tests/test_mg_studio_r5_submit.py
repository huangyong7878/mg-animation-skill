"""Paid R5 UI must fail closed without key/explicit enable; no API call in tests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from studio.r5_submit import review_preflight

class R5SubmitTests(unittest.TestCase):
    def test_missing_key_blocks_paid_submission(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            folder=root/"work/orders_pilot/stage_d_studio_0123456789abcdef"
            folder.mkdir(parents=True)
            (folder/"delivery.json").write_text(json.dumps({
                "implementation_commit":"a"*40,"spec_sha256":"b"*64}))
            (folder/"media_manifest.json").write_text(json.dumps({
                "implementation_commit":"a"*40}))
            with patch("studio.delivery_viewer.inspect",return_value={
                "manifest_ok":True,"status":"ready_for_qa"}):
                with patch.dict("os.environ",{"R5_ENABLED":"false"},clear=True):
                    result=review_preflight(root,folder.name)
            self.assertFalse(result["ready"])
            self.assertIn("DEEPSEEK_API_KEY",str(result["issues"]))
            self.assertIn("R5_ENABLED",str(result["issues"]))
            self.assertFalse(result["r5_pass"])
            self.assertFalse(result["r7_authorized"])

    def test_invalid_delivery_id_fails(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                review_preflight(Path(d),"../../etc/passwd")

if __name__=="__main__":
    unittest.main()
