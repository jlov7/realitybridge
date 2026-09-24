"""Run frozen exposed cases against the second pinned Gitea image."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT))

from experiments.ordinary_baseline_cases import CASES
from experiments.research_completion import run_case
from reality_bridge import reference as ref

# The owned parent runs this file in a new process; its in-memory override does
# not cross the process boundary. Pin the child lifecycle separately.
ref.COMPOSE_FILE = ROOT / 'reference/compose-1.24.6.yaml'

METHODS = {
    '/repos/{owner}/{repo}/issues': {'post'},
    '/repos/{owner}/{repo}/issues/{index}': {'get', 'patch'},
    '/repos/{owner}/{repo}/issues/{index}/labels': {'post'},
    '/repos/{owner}/{repo}/issues/{index}/labels/{id}': {'delete'},
    '/repos/{owner}/{repo}/labels': {'post'},
}
IMAGE = 'gitea/gitea@sha256:fe643e27326a7fae86dedb544d9392ba662adc3083763a21bd7acc35796449fd'


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _save(path: Path, value: dict) -> None:
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + '\n')
    temporary.replace(path)


def _api_mapping(meter: ref.ReferenceCallMeter) -> dict:
    base = f'http://127.0.0.1:{ref.REFERENCE_PORT}'
    with httpx.Client(base_url=base, timeout=15, trust_env=False, follow_redirects=False) as client:
        version = ref.reference_request(client, 'GET', '/api/v1/version').raise_for_status().json()
        swagger = ref.reference_request(client, 'GET', '/swagger.v1.json').raise_for_status().json()
    paths = swagger.get('paths', {})
    mapped = {path: {method: paths.get(path, {}).get(method) for method in methods} for path, methods in METHODS.items()}
    missing = [f'{path} {method}' for path, operations in mapped.items() for method, value in operations.items() if value is None]
    return {'version_response': version, 'swagger_selected': mapped, 'missing': missing, 'requests_after_mapping': meter.requests}


def run(manifest_path: Path, output: Path) -> dict:
    if os.environ.get('REALITYBRIDGE_OWNED_REFERENCE') != '1':
        raise RuntimeError('owned second-version lifecycle required')
    if output.exists():
        raise FileExistsError(output)
    manifest = json.loads(manifest_path.read_text())
    for name, expected in manifest['source_sha256'].items():
        if _sha(ROOT / name) != expected:
            raise RuntimeError(f'source hash mismatch: {name}')
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    if commit != manifest['runtime_commit']:
        raise RuntimeError('runtime commit mismatch')
    def check_image() -> str:
        image_id = ref._compose('ps', '-q', 'gitea').strip()
        inspected = subprocess.run(['docker', 'inspect', '-f', '{{.Config.Image}}|{{.Image}}', image_id], capture_output=True, text=True, check=True).stdout.strip()
        if inspected.split('|')[0] != IMAGE:
            raise RuntimeError(f'container image mismatch: {inspected}')
        return inspected
    inspected = check_image()
    result = {'status':'running', 'manifest_sha256':_sha(manifest_path), 'runtime_commit':commit,
              'image':inspected, 'rows':[], 'requests':0, 'interrupted_case':None}
    _save(output, result)
    try:
        with ref.count_reference_calls(limit=manifest['hard_request_cap']) as meter:
            result['api_mapping'] = _api_mapping(meter)
            _save(output, result)
            if result['api_mapping']['missing']:
                result['status'] = 'api_incompatible'
                return result
            ref.reset(with_seed=True)
            result['image_after_reset'] = check_image()
            result['api_mapping_after_reset'] = _api_mapping(meter)
            if result['api_mapping_after_reset']['missing'] or result['api_mapping_after_reset']['version_response'] != result['api_mapping']['version_response']:
                result['status'] = 'api_changed_after_reset'
                return result
            token = ref.token()
            for case in CASES:
                if case.case_id not in manifest['case_ids']:
                    continue
                if manifest['hard_request_cap'] - meter.requests < 10 + 5 * len(case.actions):
                    result['status'] = 'budget_censored'
                    break
                result['interrupted_case'] = {'id':case.case_id, 'partial':None}
                _save(output, result)
                def retain(row: dict, case_id: str = case.case_id) -> None:
                    result['interrupted_case'] = {'id':case_id, 'partial':row}
                    result['requests'] = meter.requests
                    _save(output, result)
                row = run_case(case, token, [], meter, retain)
                result['rows'].append(row)
                result['interrupted_case'] = None
                result['requests'] = meter.requests
                _save(output, result)
                if row['outcome'] == 'setup_failure':
                    result['status'] = 'setup_failure'
                    break
            else:
                result['status'] = 'complete'
            result['requests'] = meter.requests
    except Exception as exc:  # noqa: BLE001 - retain partial trace
        result['status'] = 'incomplete'
        result['error'] = f'{type(exc).__name__}: {str(exc)[:240]}'
    finally:
        _save(output, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.manifest.resolve(), args.output.resolve())
    print(json.dumps({'status':result['status'], 'requests':result['requests'], 'cases':len(result['rows'])}))
    raise SystemExit(0 if result['status'] == 'complete' else 1)
