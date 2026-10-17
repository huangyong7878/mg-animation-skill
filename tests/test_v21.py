import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from engine import Renderer,load
from transitions import build_junctions,compose
from factcheck import check
from narrate import create_narration
from validate import validate

class TestV21(unittest.TestCase):
    def test_v21_json_valid(self):
        d=load(ROOT/'examples'/'two_scenes_with_voice.json')
        self.assertEqual(validate(d),[])
    def test_adjacent_auto_transition(self):
        scenes=[{'start':0,'duration':3},{'start':3,'duration':3}]
        junction=build_junctions(scenes)[0]
        self.assertAlmostEqual(junction.start,2.75)
        self.assertAlmostEqual(junction.end,3.25)
    def test_overlap_always_composed_not_stacked(self):
        j=build_junctions([{'start':0,'duration':4},{'start':3,'duration':3}])[0]
        self.assertEqual((j.start,j.end),(3,4))
        a=Image.new('RGB',(12,8),(100,0,0));b=Image.new('RGB',(12,8),(0,0,100))
        self.assertEqual(compose(a,b,.5,'crossfade').getpixel((3,3)),(50,0,50))
        self.assertEqual(compose(a,b,1.,'wipe_left').getpixel((3,3)),(0,0,100))
        self.assertEqual(compose(a,b,1.,'slide_left').getpixel((3,3)),(0,0,100))
    def test_time_transition_changes_pixels(self):
        d=load(ROOT/'examples'/'two_scenes_with_voice.json')
        r=Renderer(d,ROOT/'examples')
        self.assertTrue(r.junctions)
        self.assertNotEqual(r.frame(6.10).tobytes(),r.frame(6.92).tobytes())
        self.assertEqual(r.frame(6.50).tobytes(),r.frame(6.50).tobytes())
    def test_fact_gate_fail_closed(self):
        d={'claims':[{'id':'c1','statement':'example','status':'unverified','evidence':[]}],
           'scenes':[{'factual':True,'claim_ids':['c1']}]}
        self.assertTrue(check(d))
    def test_fact_gate_verified_metadata_only(self):
        d={'claims':[{'id':'c1','statement':'example','status':'verified',
                'evidence':[{'url':'https://example.org/source','quote':'A sufficiently long excerpt.'}]}],
           'scenes':[{'factual':True,'claim_ids':['c1']}]}
        self.assertEqual(check(d),[])
    def test_narration_audio_and_timings(self):
        import shutil
        if not shutil.which('espeak'):self.skipTest('espeak unavailable')
        d={'canvas':{'duration':4},'scenes':[{'start':0,'duration':4}],
           'narration':{'segments':[{'text':'Hello world','pause_after':0.1}]}}
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)
            r=create_narration(d,out/'voice.wav',out/'timing.json',engine='espeak',voice='en')
            self.assertTrue((out/'voice.wav').is_file())
            self.assertTrue((out/'timing.srt').is_file())
            self.assertGreater(r['segments'][0]['end'],r['segments'][0]['start'])

if __name__=='__main__':unittest.main()
