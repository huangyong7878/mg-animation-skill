#!/usr/bin/env python3
"""Validate MG director/executor/QA JSON handoffs, version locks and release gating.

This is a metadata gate: it cannot verify video appearance, physics, narration,
facts or whether an AI truly performed independent visual review.
"""
import argparse
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {kind: ROOT / 'contracts' / filename for kind, filename in {
    'spec': 'director_spec.schema.json',
    'delivery': 'delivery.schema.json',
    'qa': 'qa.schema.json',
}.items()}


def canonical_digest(value):
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def schema_errors(kind, value):
    schema = json.loads(SCHEMAS[kind].read_text(encoding='utf-8'))
    return [f'{kind} schema: {error.message} at /' +
            '/'.join(map(str, error.absolute_path))
            for error in Draft202012Validator(schema).iter_errors(value)]


def required_checks(spec):
    return {(shot['id'], requirement['id']) for shot in spec['shots']
            for requirement in (shot['visual_contract']['must_show'] +
                                shot['visual_contract'].get('continuous_motion', []))}


def verify_release_files(spec, delivery, artifact_root):
    """Validate local file existence and locked voice hashes; do not run code."""
    if delivery is None:
        return []
    root = Path(artifact_root).resolve()
    items = [('script', spec['narration']['script_path'])]
    items += [('source', filename) for filename in delivery['artifacts']['source_paths']]
    for key in ('video_path', 'audio_path', 'timings_path'):
        path = delivery['artifacts'].get(key)
        if path:
            items.append((key, path))
    for key in ('audio_path', 'timings_path'):
        if spec['narration'].get(key):
            items.append((f'locked_{key}', spec['narration'][key]))
    errors = []
    for kind, relative in items:
        target = (root / relative).resolve()
        if not target.is_relative_to(root):
            errors.append(f'release: {kind} must stay inside artifact root: {relative}')
        elif not target.is_file() or target.stat().st_size == 0:
            errors.append(f'release: missing/empty {kind}: {relative}')
    for key, sha_key in (('audio_path', 'audio_sha256'),
                         ('timings_path', 'timings_sha256')):
        relative = spec['narration'].get(key)
        expected = spec['narration'].get(sha_key)
        if relative and expected:
            target = (root / relative).resolve()
            if target.is_relative_to(root) and target.is_file():
                actual = hashlib.sha256(target.read_bytes()).hexdigest()
                if actual != expected:
                    errors.append(f'release: {key} contents differ from locked {sha_key}')
    return errors


def validate_bundle(spec, delivery=None, qa=None, release=False, artifact_root=None):
    errors = schema_errors('spec', spec)
    if delivery is not None:
        errors.extend(schema_errors('delivery', delivery))
    if qa is not None:
        errors.extend(schema_errors('qa', qa))
    if errors:
        return errors

    ids = [shot['id'] for shot in spec['shots']]
    if len(ids) != len(set(ids)):
        errors.append('spec: duplicate shot ids')
    for shot in spec['shots']:
        if shot['visual_contract']['shot_id'] != shot['id']:
            errors.append(f"spec: contract shot_id does not match {shot['id']}")
        if shot['start_s'] + shot['duration_s'] > spec['output']['duration_s'] + 1e-6:
            errors.append(f"spec: {shot['id']} extends beyond output duration")
        names = ([item['id'] for item in shot['visual_contract']['must_show']] +
                 [item['id'] for item in shot['visual_contract'].get('continuous_motion', [])])
        if len(names) != len(set(names)):
            errors.append(f"spec: duplicate requirement ids in {shot['id']}")

    if spec['approval']['status'] == 'approved':
        if not spec['approval'].get('approved_by') or not spec['approval'].get('approved_at'):
            errors.append('spec: approved status needs approved_by and approved_at')
        if spec['narration']['status'] != 'locked':
            errors.append('spec: approved release specification must lock narration')
    if spec['narration']['status'] == 'locked':
        for key in ('audio_path', 'timings_path', 'audio_sha256', 'timings_sha256'):
            if not spec['narration'].get(key):
                errors.append(f'spec: locked narration requires {key}')

    digest = canonical_digest(spec)
    for kind, artifact in (('delivery', delivery), ('qa', qa)):
        if artifact is None:
            continue
        for key in ('project_id', 'spec_id'):
            if artifact[key] != spec[key]:
                errors.append(f'{kind}: {key} does not match specification')
        if artifact['spec_revision'] != spec['revision']:
            errors.append(f'{kind}: spec_revision does not match specification')
        if artifact['spec_sha256'] != digest:
            errors.append(f'{kind}: spec_sha256 stale or wrong; expected {digest}')

    if qa is not None:
        if delivery is None:
            errors.append('qa: delivery required to check implementation provenance')
        elif qa['implementation_commit'] != delivery['implementation_commit']:
            errors.append('qa: implementation_commit does not match delivery')
        required = required_checks(spec)
        seen = set()
        for check in qa['checks']:
            key = (check['shot_id'], check['requirement_id'])
            if key in seen:
                errors.append(f'qa: duplicate check {key}')
            seen.add(key)
            if key not in required:
                errors.append(f'qa: unknown requirement {key}')
        for finding in qa['findings']:
            if finding['shot_id'] not in ids:
                errors.append(f"qa: finding {finding['id']} targets an unknown shot")
        if qa['decision'] == 'pass':
            if not qa['reviewer']['independent_context']:
                errors.append('qa: pass requires independent review context')
            missing = required - seen
            if missing:
                errors.append(f'qa: pass requires all contract checks; missing {sorted(missing)}')
            if any(check['result'] != 'pass' for check in qa['checks']):
                errors.append('qa: pass cannot include failed or unchecked requirements')
            if any(item['severity'] in ('P0', 'P1') for item in qa['findings']):
                errors.append('qa: pass cannot include unresolved P0/P1 findings')

    if release:
        if delivery is None or qa is None:
            errors.append('release: delivery and QA report are both required')
        else:
            if spec['approval']['status'] != 'approved':
                errors.append('release: specification is not approved')
            if spec['narration']['status'] != 'locked':
                errors.append('release: narration is not locked')
            if delivery['stage'] != 'D' or delivery['status'] != 'ready_for_qa':
                errors.append('release: delivery must be ready_for_qa at stage D')
            if not delivery['artifacts'].get('video_path'):
                errors.append('release: delivery needs video_path')
            if any(item['result'] != 'pass' for item in delivery['checks']):
                errors.append('release: executor checks must all pass')
            if any(not item['approved'] for item in delivery['deviations']):
                errors.append('release: unapproved deviations are forbidden')
            commit = delivery['implementation_commit'].lower()
            if len(commit) not in (40, 64) or any(c not in '0123456789abcdef' for c in commit):
                errors.append('release: implementation_commit must be a full hexadecimal commit SHA')
            for key in ('audio_path', 'timings_path'):
                path = delivery['artifacts'].get(key)
                if path and path != spec['narration'].get(key):
                    errors.append(f'release: delivery {key} differs from locked narration')
            if qa['decision'] != 'pass':
                errors.append('release: QA decision is not pass')
        if artifact_root is None:
            errors.append('release: artifact_root is required to verify files')
        else:
            errors.extend(verify_release_files(spec, delivery, artifact_root))
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True)
    parser.add_argument('--delivery')
    parser.add_argument('--qa')
    parser.add_argument('--release', action='store_true')
    parser.add_argument('--artifact-root', default='.')
    args = parser.parse_args(argv)
    if args.qa and not args.delivery:
        parser.error('--qa requires --delivery')
    try:
        spec = json.loads(Path(args.spec).read_text(encoding='utf-8'))
        delivery = json.loads(Path(args.delivery).read_text(encoding='utf-8')) if args.delivery else None
        qa = json.loads(Path(args.qa).read_text(encoding='utf-8')) if args.qa else None
        errors = validate_bundle(spec, delivery, qa, args.release,
                                 args.artifact_root if args.release else None)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    for error in errors:
        print('ERROR:', error)
    if errors:
        return 1
    print('PASS: structured handoff gate' + (' (release)' if args.release else ''))
    print('NOTE: video, visual continuity, sync and facts need independent real QA.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
