"""Bounded repair generalization with frozen train, regression and unseen splits.

Each mutation is authored. The existing sandboxed worker chooses among its
prewritten color transforms; it does not edit code or invent a new algorithm.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from experiments.research_completion import _snapshot_pair, _step
from reality_bridge import reference as ref
from reality_bridge.emulator import Emulator, EmulatorError
from reality_bridge.repair import RepairRule, apply_rules
from reality_bridge.repair_sandbox import run_sandboxed_repair
from reality_bridge.state_oracle import LabelPairing

WORKER = ROOT / "experiments/sandbox_repair_worker.c"
FORBIDDEN = ROOT / "research/next-increment-2026-09-23/E-EVAL-CASES.json"


class ColorHashLeak(Emulator):
    @staticmethod
    def normalize_color(color: str) -> str:
        if color in {"#123abc", "#abc123"}:
            return color
        return color.removeprefix("#")


class UnknownAddRaises(Emulator):
    def add_label(self, repo: str, number: str, label: str) -> dict:
        if label.startswith("e-unknown"):
            raise EmulatorError(404, "authored missing-label error")
        return super().add_label(repo, number, label)


class DuplicateRowOverwrite(Emulator):
    def create_label(self, repo: str, name: str, color: str) -> dict:
        prior = next((row for row in self._label_registry if row.name == name), None)
        response = super().create_label(repo, name, color)
        if prior is not None:
            prior.color = color
        return response


MUTANTS = {
    "color_hash_leak": ColorHashLeak,
    "unknown_add_error": UnknownAddRaises,
    "duplicate_row_overwrite": DuplicateRowOverwrite,
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _save(path: Path, value: dict) -> None:
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")
    temp.replace(path)


def _trial(
    case: dict,
    mutant: type[Emulator],
    token: str,
    meter: ref.ReferenceCallMeter,
    rules: list[RepairRule],
) -> dict:
    start = meter.requests
    ref.soft_reset(token)
    candidate = mutant()
    apply_rules(candidate, rules)
    candidate.reset()
    pairing = LabelPairing({}, {})
    left, right, initial = _snapshot_pair(candidate, token, pairing)
    row = {
        "case_id": case["id"],
        "actions": case["actions"],
        "reference_initial": left,
        "simulator_initial": right,
        "initial_comparison": asdict(initial),
        "steps": [],
    }
    if initial.outcome != "agree":
        row["outcome"] = "setup_failure"
    else:
        for action in case["actions"]:
            row["steps"].append(_step(candidate, token, action, meter, pairing))
        outcomes = {
            part["outcome"] for step in row["steps"] for part in (step["response"], step["state"])
        }
        row["outcome"] = (
            "undetermined"
            if "undetermined" in outcomes
            else "unsupported"
            if "unsupported" in outcomes
            else "diverge"
            if "diverge" in outcomes
            else "agree"
        )
    row["request_cost"] = meter.requests - start
    return row


def _worker_input(row: dict) -> dict:
    step = next(
        (
            step
            for step in row["steps"]
            if step["response"]["outcome"] == "diverge" or step["state"]["outcome"] == "diverge"
        ),
        None,
    )
    if step is None:
        return {"ref": {}, "sim": {}}
    return {"ref": step["reference_response"] or {}, "sim": step["simulator_response"] or {}}


def run(manifest_path: Path, output: Path) -> dict:
    if os.environ.get("REALITYBRIDGE_OWNED_REFERENCE") != "1":
        raise RuntimeError("owned reference lifecycle required")
    if output.exists():
        raise FileExistsError(output)
    manifest = json.loads(manifest_path.read_text())
    for name, digest in manifest["source_sha256"].items():
        if _sha(ROOT / name) != digest:
            raise RuntimeError(f"source hash mismatch: {name}")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    if commit != manifest["runtime_commit"]:
        raise RuntimeError("runtime commit mismatch")
    result = {
        "status": "running",
        "manifest_sha256": _sha(manifest_path),
        "runtime_commit": commit,
        "families": {},
        "requests": 0,
        "interrupted_trial": None,
        "worker_role": "selects one authored color normalization transform; no novel code patch",
    }
    _save(output, result)
    try:
        started = time.monotonic()
        with ref.count_reference_calls(limit=manifest["hard_request_cap"]) as meter:
            ref.reset(with_seed=True)
            token = ref.token()
            for family_name, splits in manifest["families"].items():
                family = {"before": {}, "after": {}, "worker": None, "status": "running"}
                result["families"][family_name] = family
                _save(output, result)
                for split in ("train", "known_regression", "unseen"):
                    case = splits[split]
                    result["interrupted_trial"] = {
                        "family": family_name,
                        "split": split,
                        "phase": "before",
                    }
                    _save(output, result)
                    family["before"][split] = _trial(case, MUTANTS[family_name], token, meter, [])
                    result["requests"] = meter.requests
                    result["interrupted_trial"] = None
                    _save(output, result)
                worker = run_sandboxed_repair(
                    _worker_input(family["before"]["train"]), WORKER, FORBIDDEN
                )
                family["worker"] = asdict(worker)
                rules = [RepairRule(**item) for item in worker.rules]
                if rules:
                    for split in ("train", "known_regression", "unseen"):
                        case = splits[split]
                        result["interrupted_trial"] = {
                            "family": family_name,
                            "split": split,
                            "phase": "after",
                        }
                        _save(output, result)
                        family["after"][split] = _trial(
                            case, MUTANTS[family_name], token, meter, rules
                        )
                        result["requests"] = meter.requests
                        result["interrupted_trial"] = None
                        _save(output, result)
                    family["status"] = "repair_tested"
                else:
                    family["status"] = "no_supported_rule"
                result["requests"] = meter.requests
                _save(output, result)
            result["status"] = "complete"
            result["requests"] = meter.requests
        result["machine_seconds"] = round(time.monotonic() - started, 3)
    except Exception as exc:  # noqa: BLE001 - retain partial attempt
        result["status"] = "incomplete"
        result["error"] = f"{type(exc).__name__}: {str(exc)[:240]}"
    _save(output, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.manifest.resolve(), args.output.resolve())
    print(
        json.dumps(
            {
                "status": result["status"],
                "requests": result["requests"],
                "families": {k: v["status"] for k, v in result["families"].items()},
            }
        )
    )
    raise SystemExit(0 if result["status"] == "complete" else 1)
