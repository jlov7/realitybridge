"""Recompute the finite study's reported outcomes from retained local JSON.

Usage: python experiments/reproduce_research_completion.py PATH/TO/attempt-...
No reference service or token is required. Fail closed on missing evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from experiments.prospective_cases import DEV_CASES, EVAL_CASES, RANDOM_ORDER_SEEDS, case_hash
from experiments.research_completion import (
    EXPECTED_PROTOCOL_HASH,
    PROTOCOL,
    SOURCE_FILES,
    _arm_summary,
    _family_outcome,
    summarize_policy,
)


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise TypeError(f"{path.name} must be a JSON object")
    return value


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reproduce(directory: Path) -> dict[str, Any]:
    receipt = _read(directory / "receipt.json")
    if receipt["status"] not in {"complete", "bound_censored"}:
        raise ValueError(f"study was incomplete: {receipt['status']}")
    if (
        receipt["protocol_sha256"] != EXPECTED_PROTOCOL_HASH
        or _hash(PROTOCOL) != EXPECTED_PROTOCOL_HASH
    ):
        raise ValueError("protocol hash mismatch")
    if receipt["case_sha256"] != case_hash():
        raise ValueError("case inventory hash mismatch")
    if receipt["case_module_sha256"] != _hash(ROOT / "experiments/prospective_cases.py"):
        raise ValueError("case module hash mismatch")
    if receipt["source_manifest_sha256"] != {path: _hash(ROOT / path) for path in SOURCE_FILES}:
        raise ValueError("source manifest mismatch")

    arms = {}
    for name in ("targeted", *(f"random_{seed}" for seed in RANDOM_ORDER_SEEDS)):
        arm = _read(directory / f"arm-{name}.json")
        if arm["requests"] != receipt["phase_ledger"][name] or arm["requests"] > 180:
            raise ValueError(f"request ledger mismatch: {name}")
        if len(arm["order"]) != len(DEV_CASES) or set(arm["order"]) != {
            case.case_id for case in DEV_CASES
        }:
            raise ValueError(f"case order mismatch: {name}")
        for row in arm["rows"]:
            if row["outcome"] != _family_outcome(row["steps"]):
                raise ValueError(f"family outcome mismatch: {row['case_id']}")
            if row["completed_at_request"] > arm["requests"]:
                raise ValueError(f"family cost exceeded arm: {row['case_id']}")
        arms[name] = arm
    comparisons = {}
    for seed in RANDOM_ORDER_SEEDS:
        random_arm = arms[f"random_{seed}"]
        cutoff = min(random_arm["requests"], arms["targeted"]["requests"])
        comparisons[str(seed)] = {
            "shared_cutoff": cutoff,
            "random": _arm_summary(random_arm, cutoff),
            "targeted": _arm_summary(arms["targeted"], cutoff),
        }
    if comparisons != receipt["discovery_comparisons"]:
        raise ValueError("discovery comparison mismatch")

    freeze = _read(directory / "pre_evaluation_freeze.json")
    if freeze["case_sha256"] != receipt["case_sha256"]:
        raise ValueError("pre-evaluation case hash mismatch")
    if freeze["arm_files"] != {name: _hash(directory / f"arm-{name}.json") for name in arms}:
        raise ValueError("pre-evaluation discovery freeze mismatch")
    if freeze["rules"] != receipt["sandbox"]["rules"]:
        raise ValueError("repair freeze mismatch")

    evaluation = _read(directory / "evaluation.json")
    if (
        evaluation["status"] != "complete"
        or evaluation["requests"] != receipt["phase_ledger"]["evaluation"]
    ):
        raise ValueError("evaluation ledger/status mismatch")
    if [row["case_id"] for row in evaluation["rows"]] != [case.case_id for case in EVAL_CASES]:
        raise ValueError("evaluation case inventory incomplete")
    for row in evaluation["rows"]:
        if row["outcome"] != _family_outcome(row["steps"]):
            raise ValueError(f"evaluation outcome mismatch: {row['case_id']}")

    policy = _read(directory / "policy-raw.json")
    if (
        policy["status"] != "complete"
        or policy["requests"] != receipt["phase_ledger"]["policy"]
        or policy["requests"] > 750
    ):
        raise ValueError("policy ledger/status mismatch")
    if len(policy["selection"]) != 12 or len(policy["evaluation"]) != 18:
        raise ValueError("policy matrix is incomplete")
    for row in (*policy["selection"], *policy["evaluation"]):
        for backend in ("simulator", "reference"):
            result = row[backend]
            if result["attempted_actions"] != len(result["steps"]):
                raise ValueError("policy attempt count mismatch")
            if result["utility"] != (100 if result["success"] else 0) - len(result["steps"]):
                raise ValueError("policy utility mismatch")
    policy_summary = summarize_policy(policy["selection"], policy["evaluation"])
    if policy_summary != receipt["policy_summary"]:
        raise ValueError("policy summary mismatch")
    if sum(receipt["phase_ledger"].values()) != receipt["total_harness_requests"]:
        raise ValueError("total request ledger mismatch")
    return {
        "status": "reproduced",
        "source_commit": receipt["source_commit"],
        "case_sha256": receipt["case_sha256"],
        "harness_requests": receipt["total_harness_requests"],
        "evaluation_outcomes": {row["case_id"]: row["outcome"] for row in evaluation["rows"]},
        "discovery_comparisons": comparisons,
        "policy_summary": policy_summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(reproduce(args.run_directory), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
