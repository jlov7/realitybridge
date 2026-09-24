"""Build a verdict-free reviewer capsule from immutable historical raw traces."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALUATION = ROOT / 'artifacts/research-completion-2026-09-22/attempt-20260922T182622Z-59359/evaluation.json'
ORDINARY = ROOT / 'artifacts/ordinary-baseline-2026-09-23/amended-complete.json'
API_RAW = ROOT / 'artifacts/next-increment-2026-09-23/B-API-RAW.json'
RAW_STEP_FIELDS = ('action', 'reference_error', 'reference_response', 'reference_state', 'simulator_error', 'simulator_response', 'simulator_state')
HISTORICAL_CONTRACTS = (
    ('operations.md', ROOT / 'research/next-increment-2026-09-23/historical-operations-contract.md',
     '7564aac931eea13f5babc5de1ab5aff5acd96f6e2fc4641f74b1ed1a9015f822'),
    ('observation.md', ROOT / 'research/next-increment-2026-09-23/historical-observation-contract.md',
     '14701b0db889e274f624ce1a71c816dc9ba862a2cc28123ec4a86c2e67a9c0fc'),
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dump(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')


def build(output: Path) -> None:
    if output.exists():
        raise FileExistsError(output)
    capsule = output / 'reviewer-capsule'
    cases_dir = capsule / 'cases'
    cases_dir.mkdir(parents=True)
    source = [('historical_evaluation', item) for item in json.loads(EVALUATION.read_text())['rows']]
    source.extend(('ordinary_study', item['raw']) for item in json.loads(ORDINARY.read_text())['rows'])
    # This permutation conceals source order. It cannot erase a reviewer's prior
    # knowledge of published action traces, which remains a disclosed limit.
    random.Random(884103).shuffle(source)
    answers = []
    manifest_cases = []
    for index, (study, row) in enumerate(source, 1):
        case_id = f'R{index:03d}'
        trace = {
            'case': case_id,
            'actions': row['actions'],
            'reference_initial': row['reference_initial'],
            'simulator_initial': row['simulator_initial'],
            'steps': [{field: step.get(field) for field in RAW_STEP_FIELDS} for step in row['steps']],
        }
        path = cases_dir / f'{case_id}.json'
        _dump(path, trace)
        manifest_cases.append({'case': case_id, 'path': f'cases/{case_id}.json', 'sha256': _sha(path)})
        answers.append({'case': case_id, 'source_study': study, 'source_case': row['case_id'], 'recorded_instrument_outcome': row['outcome']})
    for name, source_path, expected_sha in HISTORICAL_CONTRACTS:
        if _sha(source_path) != expected_sha:
            raise RuntimeError(f'historical contract hash mismatch: {name}')
        (capsule / name).write_bytes(source_path.read_bytes())
    api = json.loads(API_RAW.read_text())
    if api['status'] != 'complete' or api['version'] != {'version': '1.24.7'} or api['requests'] != 2:
        raise RuntimeError('pinned API excerpt capture was incomplete')
    _dump(capsule / 'API-SCHEMA-EXCERPT.json', {
        'version': api['version'], 'image': api['image'].split('|')[0],
        'six_operation_schemas': api['swagger'],
    })
    (capsule / 'API-EXCERPT.md').write_text(
        '# Pinned API excerpt for review\n\n'
        'This readable path list accompanies `API-SCHEMA-EXCERPT.json`, captured '
        'from `/swagger.v1.json` on the pinned Gitea 1.24.7 image in a new '
        'owned loopback run. The historical study did not retain the raw schema.\n\n'
        '| Method | Path |\n| --- | --- |\n'
        '| POST | /repos/{owner}/{repo}/issues |\n'
        '| GET | /repos/{owner}/{repo}/issues/{index} |\n'
        '| PATCH | /repos/{owner}/{repo}/issues/{index} |\n'
        '| POST | /repos/{owner}/{repo}/issues/{index}/labels |\n'
        '| DELETE | /repos/{owner}/{repo}/issues/{index}/labels/{id} |\n'
        '| POST | /repos/{owner}/{repo}/labels |\n\n'
        'The review should challenge whether the declared state and normalization rules preserve '
        'every distinction relevant to these operations. Request the live raw swagger before '
        'drawing a claim that depends on a field absent from this excerpt.\n'
    )
    (capsule / 'REVIEW-PROTOCOL.md').write_text(
        '# Blind oracle review\n\n'
        'Classify against the enclosed historical 2026-09-22 observation contract. '
        'The current source has a later, stricter paired label-row rule. '
        'A difference caused only by applying that later rule is a contract change, '
        'not a missed verdict under the historical contract. Record it separately.\n\n'
        'The case IDs are opaque and randomized. Each case gives raw reference and simulator '
        'responses/errors and separately read issue/label state after each action. '
        'Classify the initial state and each step using `agree`, `diverge`, `unsupported`, '
        'or `undetermined`. Name the exact fields, API contract rule, and any uncertainty. '
        'Do not infer agreement from an absent response or an unsuccessful readback. '
        'If a raw ID matters, explain the paired identity evidence instead of comparing '
        'generated IDs directly.\n\n'
        'First submit your classifications without accessing the answer key or comparison code. '
        'Then compare against the private key with a separate adjudicator. Record every '
        'disagreement, source trace, rationale, resolution and unresolved question. '
        'A reviewer who already knows public cases should disclose that exposure. '
        'This capsule contains no comparator verdict; packet preparation is not a review.\n'
    )
    with (capsule / 'CLASSIFICATION-FORM.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['case', 'step_or_initial', 'classification', 'fields_and_reason', 'uncertainty', 'reviewer_id'])
        for entry in manifest_cases:
            writer.writerow([entry['case'], '', '', '', '', ''])
    with (output / 'B-DISCREPANCY-LOG.csv').open('w', newline='') as handle:
        csv.writer(handle).writerow(['case', 'step_or_initial', 'reviewer', 'recorded_comparator', 'raw_evidence', 'resolution', 'status'])
    _dump(output / 'B-private-answer-key.json', {'status': 'not_adjudicated', 'entries': answers})
    _dump(capsule / 'MANIFEST.json', {'status': 'awaiting_outside_review',
                                    'contract_version': 'historical 2026-09-22',
                                    'case_count': len(manifest_cases), 'cases': manifest_cases})
    # Fail if comparison outputs or historical source IDs entered reviewer JSON.
    for path in cases_dir.glob('*.json'):
        item = json.loads(path.read_text())
        forbidden = {'outcome', 'comparison', 'reason', 'evidence', 'source_case', 'source_study'}
        if any(key in forbidden for key in item):
            raise RuntimeError(f'verdict field leaked to {path.name}')
        if any(key in forbidden for step in item['steps'] for key in step):
            raise RuntimeError(f'step verdict field leaked to {path.name}')
    _dump(output / 'B-PACKET-RECEIPT.json', {
        'status': 'packet_prepared_no_outside_review',
        'historical_sources_sha256': {'evaluation': _sha(EVALUATION), 'ordinary': _sha(ORDINARY)},
        'api_capture_sha256': _sha(API_RAW),
        'capsule_sha256': {str(path.relative_to(capsule)): _sha(path) for path in sorted(capsule.rglob('*')) if path.is_file()},
        'private_answer_key_sha256': _sha(output / 'B-private-answer-key.json'),
        'case_count': len(manifest_cases),
        'contract_version': 'historical 2026-09-22',
        'generator_sha256': _sha(Path(__file__)),
    })


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    build(parser.parse_args().output.resolve())
