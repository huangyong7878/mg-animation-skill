"""Regression tests for shot-scoped Visual Contract coverage."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from contract_check import audit_contract, main


def contract(downgrade=False):
    return {
        'shot_id': 'shot_02', 'silent_downgrade': downgrade,
        'must_show': [{'id': 'soil'}, {'id': 'drain'}],
        'continuous_motion': [{'id': 'water_path'}],
    }


def scene(target):
    return {'scenes': [
        {'id': 'shot_01', 'elements': [{'type': 'card', 'contract': ['soil', 'drain', 'water_path']}]},
        {'id': 'shot_02', 'elements': target},
    ]}


class ContractAuditTests(unittest.TestCase):
    def test_recursive_nested_element_coverage(self):
        data = scene([{'type': 'row', 'children': [
            {'type': 'soil', 'contract': 'soil'},
            {'type': 'column', 'children': [
                {'type': 'drainpipe', 'contract': ['drain', 'water_path']},
            ]},
        ]}])
        result = audit_contract(contract(), data)
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['missing'], [])

    def test_tags_from_other_shot_do_not_count(self):
        result = audit_contract(contract(), scene([{'type': 'soil', 'contract': 'soil'}]))
        self.assertFalse(result['passed'])
        self.assertEqual(result['missing'], ['drain', 'water_path'])

    def test_missing_shot_fails_closed(self):
        result = audit_contract(contract(), {'scenes': [{'id': 'shot_01', 'elements': []}]})
        self.assertFalse(result['passed'])
        self.assertIn('exactly one scene', result['errors'][0])

    def test_explicit_downgrade_warns_but_strict_blocks(self):
        data = scene([])
        self.assertTrue(audit_contract(contract(True), data)['passed'])
        self.assertTrue(audit_contract(contract(True), data)['warnings'])
        self.assertFalse(audit_contract(contract(True), data, strict=True)['passed'])

    def test_invalid_contract_and_duplicate_requirement_id_fail(self):
        bad = contract()
        bad['continuous_motion'].append({'id': 'soil'})
        self.assertFalse(audit_contract(bad, scene([]))['passed'])
        bad2 = contract()
        del bad2['silent_downgrade']
        self.assertFalse(audit_contract(bad2, scene([]))['passed'])

    def test_cli_writes_json_report_and_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            c, s, report = root/'contract.json', root/'scene.json', root/'report.json'
            c.write_text(json.dumps(contract()), encoding='utf-8')
            s.write_text(json.dumps(scene([])), encoding='utf-8')
            code = main([str(c), str(s), '--report', str(report)])
            self.assertEqual(code, 1)
            self.assertFalse(json.loads(report.read_text(encoding='utf-8'))['passed'])


if __name__ == '__main__':
    unittest.main()
