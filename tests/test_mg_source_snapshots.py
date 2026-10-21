import tempfile
import unittest
from pathlib import Path
from studio.source_snapshots import snapshot,verify

class SourceSnapshotTests(unittest.TestCase):
    def test_content_addressed_and_tamper_detected(self):
        with tempfile.TemporaryDirectory() as d:
            repo=Path(d)/"repo"; tree=Path(d)/"working"
            repo.mkdir();(tree/"scripts").mkdir(parents=True)
            (tree/"scripts/demo.py").write_text("print('v2')\n")
            args=dict(base_commit="a"*40,allowed_files=["scripts/demo.py"],
                      changed_files=["scripts/demo.py"],approved_finding_ids=["F1"])
            item=snapshot(repo,tree,**args)
            self.assertTrue(verify(repo,item["snapshot_id"])["valid"])
            self.assertFalse(verify(repo,item["snapshot_id"])["formal_stage_d_authorized"])
            self.assertTrue(snapshot(repo,tree,**args)["reused"])
            path=Path(item["path"])/"source/scripts/demo.py"
            path.chmod(0o644)
            path.write_text("tampered")
            self.assertFalse(verify(repo,item["snapshot_id"])["valid"])

    def test_rejects_out_of_scope_and_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            repo=Path(d)/"repo";tree=Path(d)/"tree"
            repo.mkdir();(tree/"scripts").mkdir(parents=True)
            (tree/"scripts/demo.py").symlink_to(Path(d)/"outside")
            common=dict(base_commit="a"*40,allowed_files=["scripts/demo.py"],
                        approved_finding_ids=["F1"])
            with self.assertRaises(ValueError):
                snapshot(repo,tree,changed_files=["../outside"],**common)
            with self.assertRaises(ValueError):
                snapshot(repo,tree,changed_files=["scripts/demo.py"],**common)

if __name__=="__main__":
    unittest.main()
