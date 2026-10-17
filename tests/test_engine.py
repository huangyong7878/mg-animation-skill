import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from engine import Box, Renderer, calculate_grid, layout_scene, load, timeline_state
from validate import validate

class TestMGEngine(unittest.TestCase):
    def test_all_examples_validate(self):
        for p in (ROOT/'examples').glob('*.json'):
            with self.subTest(example=p):self.assertEqual(validate(load(p)),[])

    def test_arbitrary_grid_dimensions(self):
        for cols,rows in [(1,1),(2,3),(4,5),(7,2)]:
            cells=calculate_grid(Box(0,0,700,400),cols,rows)
            self.assertEqual(len(cells),cols*rows)
            self.assertAlmostEqual(cells[-1].x+cells[-1].w,700)
            self.assertAlmostEqual(cells[-1].y+cells[-1].h,400)

    def test_layout_flow_adapts_to_children(self):
        node={'type':'row','rect':{'w':'100%','h':'100%'},'gap':10,'children':[{'type':'card','text':'x'} for _ in range(6)]}
        out=layout_scene({'elements':[node]},800,300)
        self.assertEqual(len(out),6)
        self.assertAlmostEqual(out[0][1].w,(800-50)/6)
        self.assertAlmostEqual(out[-1][1].x+out[-1][1].w,800)

    def test_bad_table_rejected(self):
        d=load(ROOT/'examples'/'table_2x3.json')
        d['scenes'][0]['elements'][1]['rows'][0].append('extra')
        self.assertTrue(any('Table row' in x for x in validate(d)))

    def test_grain_is_static_and_frame_deterministic(self):
        d=load(ROOT/'examples'/'table_2x3.json')
        r=Renderer(d)
        self.assertEqual(r.frame(1.5).tobytes(),r.frame(1.5).tobytes())
        self.assertEqual(r.frame(.0).getpixel((10,10)),r.frame(1.5).getpixel((10,10)))

    def test_pop_returns_to_one(self):
        x={'animations':[{'type':'pop','start':.3,'duration':.5}]}
        self.assertAlmostEqual(timeline_state(x,1.0)['scale'],1.0)
        self.assertAlmostEqual(timeline_state(x,1.0)['alpha'],1.0)

    def test_move_interpolates_position(self):
        x={'animations':[{'type':'move','start':1.0,'duration':2.0,'easing':'linear',
                          'from_x':100,'from_y':-50,'to_x':0,'to_y':0}]}
        # before start: at from-offset
        s0=timeline_state(x,0.5)
        self.assertAlmostEqual(s0['dx'],100); self.assertAlmostEqual(s0['dy'],-50)
        # mid: halfway (linear)
        s1=timeline_state(x,2.0)
        self.assertAlmostEqual(s1['dx'],50); self.assertAlmostEqual(s1['dy'],-25)
        # after: at to-offset
        s2=timeline_state(x,4.0)
        self.assertAlmostEqual(s2['dx'],0); self.assertAlmostEqual(s2['dy'],0)

    def test_future_pulse_does_not_hide(self):
        x={'animations':[
            {'type':'pop','start':.3,'duration':.5},
            {'type':'pop','start':1.8,'duration':.4,'hide_before':False},
        ]}
        s=timeline_state(x,1.0)  # entrance done, pulse not started
        self.assertAlmostEqual(s['alpha'],1.0)
        self.assertAlmostEqual(s['scale'],1.0)

if __name__=='__main__':unittest.main()
