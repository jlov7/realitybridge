"""Run the frozen duplicate-row probe on one owned loopback reference."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from reality_bridge import reference as ref


def _save(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")
    temporary.replace(path)


def run(manifest_path: Path, output: Path) -> dict:
    if os.environ.get("REALITYBRIDGE_OWNED_REFERENCE") != "1":
        raise RuntimeError("the owned reference lifecycle is required")
    if output.exists():
        raise FileExistsError(output)
    manifest = json.loads(manifest_path.read_text())
    for name, digest in manifest["source_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"source hash mismatch: {name}")
    receipt = {
        "status": "running",
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "cases": [],
        "requests": 0,
        "interrupted_case": None,
    }
    _save(output, receipt)
    try:
        with ref.count_reference_calls(limit=manifest["hard_request_cap"]) as meter:
            ref.reset(with_seed=True)
            token = ref.token()
            for case in manifest["cases"]:
                receipt["interrupted_case"] = case["id"]
                _save(output, receipt)
                ref.soft_reset(token)
                row = {"id": case["id"], "steps": [], "initial": ref.export_declared_state(token)}
                for action in case["actions"]:
                    step = {"action": action, "request_before": meter.requests}
                    try:
                        step["response"] = ref.step_reference(action, token)
                    except ref.ReferenceStepError as exc:
                        step["error"] = {"status": exc.status, "body": exc.body}
                    step["state"] = ref.export_declared_state(token)
                    step["request_after"] = meter.requests
                    row["steps"].append(step)
                    receipt["interrupted_case"] = row
                    receipt["requests"] = meter.requests
                    _save(output, receipt)
                receipt["cases"].append(row)
                receipt["interrupted_case"] = None
                receipt["requests"] = meter.requests
                _save(output, receipt)
            receipt["status"] = "complete"
    except Exception as exc:  # noqa: BLE001 - retain partial evidence
        receipt["status"] = "incomplete"
        receipt["error"] = f"{type(exc).__name__}: {str(exc)[:240]}"
    _save(output, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    receipt = run(args.manifest.resolve(), args.output.resolve())
    print(json.dumps({"status": receipt["status"], "requests": receipt["requests"]}))
    return 0 if receipt["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
