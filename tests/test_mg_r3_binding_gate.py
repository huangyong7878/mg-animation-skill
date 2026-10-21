import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from studio.r3_binding_gate import check

class TestR3BindingGate(unittest.TestCase):
    def source(self):
        return Path("scripts/primitives/orderflow.py").read_text()

    def execute(self, modified):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            file=root/"scripts/primitives/orderflow.py"
            file.parent.mkdir(parents=True)
            file.write_text(modified)
            class Result:
                stdout=self.source()
            with patch("studio.r3_binding_gate.subprocess.run",return_value=Result()):
                return check(root,root,"a"*40)

    def test_unchanged_approved_binding_passes(self):
        self.assertTrue(self.execute(self.source())["passed"])

    def test_synchronized_early_fade_is_blocked(self):
        s=self.source()
        s=s.replace("def card(cx, cy, letter, color, dark, appear_t, scale_extra=1.0):",
                    "def card(cx, cy, letter, color, dark, scale_extra=1.0):")
        s=s.replace("_fade(t, appear_t, appear_t + 0.6)","_fade(t, 0.4, 1.0)")
        s=s.replace('PILOT_EVENT_SECONDS["order_b_appears"])',' )')
        s=s.replace('PILOT_EVENT_SECONDS["order_a_appears"])',' )')
        self.assertFalse(self.execute(s)["passed"])

if __name__=="__main__":
    unittest.main()
