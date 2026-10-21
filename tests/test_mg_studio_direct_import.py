"""Direct-script startup should resolve all studio package imports."""
import subprocess
import sys
import unittest
from pathlib import Path

class StudioScriptImports(unittest.TestCase):
    def test_direct_script_python_path(self):
        root=Path(__file__).resolve().parents[1]
        server=(root/"studio/server.py").read_text()
        self.assertIn("sys.path.insert(0, str(ROOT))",server)
        proc=subprocess.run([sys.executable,"-c",
             "import runpy; runpy.run_path('studio/server.py', run_name='studio_import_check'); from studio.settings import public_status; from studio.r5_submit import review_preflight"],
             cwd=root,capture_output=True,text=True,timeout=20)
        self.assertEqual(proc.returncode,0,proc.stderr)

if __name__=="__main__":
    unittest.main()
