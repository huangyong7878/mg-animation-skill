import tempfile
import unittest
from pathlib import Path
from studio.job_store import JobStore

class JobStoreTests(unittest.TestCase):
    def test_persistence_and_restart_interrupt(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"jobs.sqlite3"
            s=JobStore(path)
            first=s.start("task-a")
            self.assertTrue(s.active())
            with self.assertRaises(ValueError): s.start("duplicate")
            # simulate server restart
            s=JobStore(path)
            self.assertEqual(s.list()[0]["status"],"interrupted")
            self.assertFalse(s.active())
            second=s.start("task-b")
            s.finish(second,"ready_for_manual_review",{
                "worktree":"/tmp/worktree","changed_files":["scripts/a.py"],
                "output":"sensitive-model-transcript"})
            record=s.list()[0]
            self.assertEqual(record["status"],"ready_for_manual_review")
            self.assertNotIn("output",str(record))
            self.assertEqual(s.list()[1]["id"],first)

    def test_invalid_terminal_status_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            s=JobStore(Path(d)/"db.sqlite3")
            item=s.start("task")
            with self.assertRaises(ValueError):
                s.finish(item,"qa_passed",{})
            self.assertTrue(s.active())

if __name__=="__main__":
    unittest.main()
