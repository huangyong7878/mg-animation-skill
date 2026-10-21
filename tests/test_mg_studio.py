"""MG Studio read-only MVP smoke tests (no Codex/model calls)."""
import json
import tempfile
import unittest
from pathlib import Path
from studio.server import project_snapshot, create_handler

class StudioTests(unittest.TestCase):
    def test_snapshot_reads_r0_without_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            state=root/"work/orders_pilot/formal_r4/state.json"
            state.parent.mkdir(parents=True)
            original={"status":"review_pending","attempt":1,"production_mode":"formal"}
            state.write_text(json.dumps(original))
            snapshot=project_snapshot(root)
            self.assertEqual(snapshot["workspaces"][0]["status"],"review_pending")
            self.assertFalse(snapshot["r7_release_allowed"])
            self.assertEqual(json.loads(state.read_text()),original)

    def test_broken_state_safe(self):
        with tempfile.TemporaryDirectory() as d:
            state=Path(d)/"work/orders_pilot/formal_r4/state.json"
            state.parent.mkdir(parents=True)
            state.write_text("{invalid")
            self.assertEqual(project_snapshot(Path(d))["workspaces"][0]["status"],"unreadable")

    def test_handler_factory(self):
        from http.server import BaseHTTPRequestHandler
        self.assertTrue(issubclass(create_handler(Path("."), "test-token"),BaseHTTPRequestHandler))

if __name__=="__main__":
    unittest.main()
