"""Run a frozen all-cell policy decision study on the owned reference."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT))

from experiments.research_completion import Goal, _policy_trial, summarize_policy
from reality_bridge import reference as ref


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _save(path: Path, result: dict) -> None:
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + '\n')
    temp.replace(path)


def run(manifest_path: Path, output: Path) -> dict:
    if os.environ.get('REALITYBRIDGE_OWNED_REFERENCE') != '1':
        raise RuntimeError('owned reference lifecycle required')
    if output.exists():
        raise FileExistsError(output)
    manifest = json.loads(manifest_path.read_text())
    for name, expected in manifest['source_sha256'].items():
        if _sha(ROOT / name) != expected:
            raise RuntimeError(f'source hash mismatch: {name}')
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    if commit != manifest['runtime_commit']:
        raise RuntimeError('runtime commit mismatch')
    result = {'status':'running', 'manifest_sha256':_sha(manifest_path), 'runtime_commit':commit,
              'selection':[], 'evaluation':[], 'requests':0, 'interrupted_cell':None}
    _save(output, result)
    try:
        with ref.count_reference_calls(limit=manifest['hard_request_cap']) as meter:
            ref.reset(with_seed=True)
            token = ref.token()
            for phase in ('selection', 'evaluation'):
                for raw_task in manifest[phase]:
                    task = Goal(**raw_task)
                    for policy in manifest['policies']:
                        if manifest['hard_request_cap'] - meter.requests < manifest['max_per_cell_requests']:
                            result['status'] = 'budget_censored'
                            return result
                        result['interrupted_cell'] = {'phase':phase, 'task':task.task_id, 'policy':policy}
                        _save(output, result)
                        row = _policy_trial(task, policy, token, [], meter)
                        result[phase].append(row)
                        result['requests'] = meter.requests
                        result['interrupted_cell'] = None
                        _save(output, result)
            result['summary'] = summarize_policy(result['selection'], result['evaluation'])
            result['status'] = 'complete'
            result['requests'] = meter.requests
    except Exception as exc:  # noqa: BLE001 - retain partial attempt
        result['status'] = 'incomplete'
        result['error'] = f'{type(exc).__name__}: {str(exc)[:240]}'
    finally:
        _save(output, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = run(args.manifest.resolve(), args.output.resolve())
    print(json.dumps({'status':result['status'], 'requests':result['requests'],
                      'selection_cells':len(result['selection']), 'evaluation_cells':len(result['evaluation'])}))
    raise SystemExit(0 if result['status'] == 'complete' else 1)
