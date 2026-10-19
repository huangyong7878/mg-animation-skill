"""Multi-model handoff schema and release-gate regression tests."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workflow'))
from check_handoff import canonical_digest, validate_bundle, required_checks


def examples():
    base = ROOT / 'examples'
    return [json.loads((base / name).read_text(encoding='utf-8')) for name in
            ('workflow_orders_spec.json', 'workflow_orders_delivery.json',
             'workflow_orders_qa.json')]


class HandoffTests(unittest.TestCase):
    def test_draft_examples_valid_but_not_release_ready(self):
        spec, delivery, qa = examples()
        self.assertEqual(validate_bundle(spec, delivery, qa), [])
        self.assertTrue(validate_bundle(spec, delivery, qa, release=True, artifact_root=ROOT))

    def test_modified_spec_invalidates_delivery_and_qa(self):
        spec, delivery, qa = examples()
        spec['creative']['title'] += ' altered'
        self.assertTrue(any('stale' in error for error in validate_bundle(spec, delivery, qa)))

    def test_shot_mismatch_and_duplicate_requirements(self):
        spec, _, _ = examples()
        spec['shots'][0]['visual_contract']['shot_id'] = 'wrong'
        self.assertTrue(any('contract shot_id' in e for e in validate_bundle(spec)))
        spec, _, _ = examples()
        spec['shots'][0]['visual_contract']['must_show'].append(
            {'id': 'path_a', 'desc': 'duplicate'})
        self.assertTrue(any('duplicate requirement' in e for e in validate_bundle(spec)))

    def test_qa_commit_and_revision_must_match(self):
        spec, delivery, qa = examples()
        qa['implementation_commit'] = 'mismatch1234'
        self.assertTrue(any('implementation_commit' in e for e in validate_bundle(spec, delivery, qa)))
        spec, delivery, qa = examples()
        delivery['spec_revision'] += 1
        self.assertTrue(any('spec_revision' in e for e in validate_bundle(spec, delivery, qa)))

    def test_qa_pass_requires_full_coverage_and_independence(self):
        spec, delivery, qa = examples()
        qa['decision'] = 'pass'
        self.assertTrue(any('missing' in e for e in validate_bundle(spec, delivery, qa)))
        qa['checks'] = [dict(shot_id=s, requirement_id=r, result='pass', evidence='video:10s')
                        for s, r in sorted(required_checks(spec))]
        self.assertEqual(validate_bundle(spec, delivery, qa), [])
        qa['reviewer']['independent_context'] = False
        self.assertTrue(any('independent' in e for e in validate_bundle(spec, delivery, qa)))
        qa['reviewer']['independent_context'] = True
        qa['findings'] = [dict(id='f1', severity='P0', shot_id='shot_01',
                               expected='A', observed='B', fix_request='fix',
                               evidence='video:3s')]
        self.assertTrue(any('P0/P1' in e for e in validate_bundle(spec, delivery, qa)))

    def test_approved_spec_requires_locked_audio(self):
        spec, _, _ = examples()
        spec['approval'] = {'status': 'approved', 'approved_by': 'human',
                            'approved_at': '2026-10-19'}
        self.assertTrue(any('lock narration' in e for e in validate_bundle(spec)))

    def test_release_checks_files_and_locked_hashes(self):
        spec, delivery, qa = examples()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contents = {'narration.txt': b'hello', 'audio.wav': b'audio',
                        'timings.json': b'{"segments":[]}',
                        'shots/shot_01.py': b'print(1)',
                        'previews/shot_01_silent.mp4': b'mock mp4'}
            for name, data in contents.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            spec['approval'] = dict(status='approved', approved_by='human',
                                    approved_at='2026-10-19')
            spec['narration'].update(
                status='locked', audio_path='audio.wav', timings_path='timings.json',
                audio_sha256=hashlib.sha256(contents['audio.wav']).hexdigest(),
                timings_sha256=hashlib.sha256(contents['timings.json']).hexdigest())
            digest = canonical_digest(spec)
            delivery.update(spec_sha256=digest, stage='D', status='ready_for_qa',
                            implementation_commit='a' * 40,
                            checks=[dict(name='renderer', result='pass', detail='smoke')])
            qa.update(spec_sha256=digest, implementation_commit='a'*40, decision='pass')
            qa['checks'] = [dict(shot_id=s, requirement_id=r, result='pass',
                                  evidence='frames') for s, r in sorted(required_checks(spec))]
            self.assertEqual(validate_bundle(spec, delivery, qa, release=True,
                                             artifact_root=root), [])
            (root/'audio.wav').write_bytes(b'changed')
            self.assertTrue(any('audio_path contents' in e for e in
                                validate_bundle(spec, delivery, qa, release=True, artifact_root=root)))
            (root/'audio.wav').write_bytes(contents['audio.wav'])
            delivery['artifacts']['video_path'] = '../escaped.mp4'
            self.assertTrue(any('inside artifact root' in e for e in
                                validate_bundle(spec, delivery, qa, release=True, artifact_root=root)))


if __name__ == '__main__':
    unittest.main()
