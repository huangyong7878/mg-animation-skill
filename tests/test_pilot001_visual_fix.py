"""Pilot 001 R4 P1/P2 visual regression invariants (without approvals)."""
import unittest
from pathlib import Path
from scripts.primitives.orderflow import PILOT_EVENT_SECONDS, _travel

ROOT = Path(__file__).resolve().parents[1]

class PilotVisualFixTests(unittest.TestCase):
    def test_r3_event_contract_kept(self):
        self.assertEqual(PILOT_EVENT_SECONDS, {
            "order_a_appears": 1.0, "order_b_appears": 1.2,
            "branch_split": 5.8, "order_b_queue_arrival": 8.4,
            "order_a_ship_arrival": 10.0})

    def test_decision_node_clearance(self):
        # In the registered design, the stock diamond half-height is 46,
        # each fully visible card's half-height is 32. 100 px offset
        # retains > 20 px vertical clearance.
        a = [(1.8,100,200),(4.8,340,180),(5.8,340,180)]
        b = [(1.8,100,360),(4.8,340,380),(5.8,340,380)]
        for t in (4.8, 5.0, 5.5, 5.8):
            _, ya = _travel(a,t)
            _, yb = _travel(b,t)
            self.assertGreaterEqual(280 - ya - 46 - 32, 20)
            self.assertGreaterEqual(yb - 280 - 46 - 32, 20)

    def test_source_keeps_render_positions_separated(self):
        source = (ROOT / "scripts/primitives/orderflow.py").read_text()
        self.assertIn('check_cy - 100', source)
        self.assertIn('check_cy + 100', source)
        self.assertNotIn('check_cy - 48', source)
        self.assertNotIn('check_cy + 48', source)

if __name__ == "__main__":
    unittest.main()
