"""Run the frozen fresh-case comparison on one owned disposable reference.

Invoke through reference/owned_lifecycle.py after parent AI protocol review.
The runner retains every completed or partial row and never modifies old evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from experiments.ordinary_baseline import compare_case
from experiments.ordinary_baseline_cases import CASES, case_hash
from experiments.research_completion import _running_reference_image, run_case
from reality_bridge import reference as ref
from reality_bridge.repair import RepairRule

MANIFEST = ROOT / "research/ordinary-baseline-2026-09-23/FROZEN-MANIFEST-A1.json"
HISTORICAL_RULE = RepairRule(
    field="label.color",
    transform="strip_leading_hash",
    evidence="paired values differ only by a simulator leading hash",
)
FIRST_ATTEMPT_SHA256 = "b7f68cff674ddf6de226ea8a2c3b2e6189c824121a1d6dd227a36cfc73f1cc30"
HISTORICAL_RECEIPT_SHA256 = "f96145b240dc2d6b759ce8b0a590843c6b39d51685188735558036a9ea0e3216"
BASELINE_HASH = "61b81d7b4f5c97a1116855fbb93c422d772d9342c5503c1f84b7bd659f3c02ac"
CAP = 320


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _save(path: Path, receipt: dict[str, Any]) -> None:
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n")
    temp.replace(path)


def _instrument_case(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("outcome") not in {"agree", "diverge", "undetermined", "unsupported"}:
        return {"outcome": "undetermined", "steps": [], "reason": "incomplete case"}
    if (
        not isinstance(row.get("actions"), list)
        or not isinstance(row.get("steps"), list)
        or len(row["actions"]) != len(row["steps"])
        or any(step.get("action") != action for action, step in zip(row["actions"], row["steps"]))
    ):
        return {"outcome": "undetermined", "steps": [], "reason": "action inventory mismatch"}
    if row["outcome"] == "setup_failure":
        return {"outcome": "undetermined", "steps": []}
    steps = []
    for step in row["steps"]:
        outcomes = {step["response"]["outcome"], step["state"]["outcome"]}
        outcome = (
            "undetermined"
            if "undetermined" in outcomes
            else "unsupported"
            if "unsupported" in outcomes
            else "diverge"
            if "diverge" in outcomes
            else "agree"
        )
        steps.append({"outcome": outcome, "response": step["response"], "state": step["state"]})
    outcomes = {step["outcome"] for step in steps}
    outcome = (
        "undetermined"
        if "undetermined" in outcomes
        else "unsupported"
        if "unsupported" in outcomes
        else "diverge"
        if "diverge" in outcomes
        else "agree"
    )
    return {"outcome": outcome, "steps": steps}


def run(output: Path) -> dict[str, Any]:
    if os.environ.get("REALITYBRIDGE_OWNED_REFERENCE") != "1":
        raise RuntimeError("live study requires reference/owned_lifecycle.py ownership")
    if output.exists():
        raise FileExistsError(output)
    origin = os.environ.get("REALITYBRIDGE_FROZEN_ORIGIN_COMMIT")
    if not origin or len(origin) != 40 or any(ch not in "0123456789abcdef" for ch in origin):
        raise RuntimeError("exact frozen origin commit required")
    manifest = json.loads(MANIFEST.read_text())
    for relative, expected in manifest["source_sha256"].items():
        if relative == "src/reality_bridge/emulator.py":
            continue  # intentional baseline materialization, checked below
        if _sha(ROOT / relative) != expected:
            raise RuntimeError(f"frozen source hash mismatch: {relative}")
    if _sha(ROOT / "src/reality_bridge/emulator.py") != BASELINE_HASH:
        raise RuntimeError(
            "exact measured pre-fix baseline emulator required; materialize it first"
        )

    def git(*args: str) -> str:
        return subprocess.run(
            ("git", *args), cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()

    if git("status", "--porcelain"):
        raise RuntimeError("materialized study tree must be clean")
    output.parent.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, Any] = {
        "status": "running",
        "started_at_utc": datetime.now(UTC).isoformat(),
        "frozen_origin_commit": origin,
        "study_commit": git("rev-parse", "HEAD"),
        "study_tree": git("rev-parse", "HEAD^{tree}"),
        "clean_tree_at_start": True,
        "frozen_manifest_sha256": _sha(MANIFEST),
        "frozen_source_sha256": manifest["source_sha256"],
        "classification": "amended AI-authored ordinary testing study after setup-only failure",
        "amendment": "research/ordinary-baseline-2026-09-23/AMENDMENT-1.md",
        "first_attempt_sha256": FIRST_ATTEMPT_SHA256,
        "historical_rule_receipt_sha256": HISTORICAL_RECEIPT_SHA256,
        "applied_rule": asdict(HISTORICAL_RULE),
        "case_hash": case_hash(),
        "source_hashes": {
            str(p.relative_to(ROOT)): _sha(p)
            for p in (
                ROOT / "src/reality_bridge/emulator.py",
                ROOT / "experiments/ordinary_baseline.py",
                ROOT / "experiments/ordinary_baseline_cases.py",
                ROOT / "experiments/ordinary_baseline_study.py",
                ROOT / "research/ordinary-baseline-2026-09-23/PROTOCOL.md",
            )
        },
        "image": _running_reference_image(),
        "hard_cap": CAP,
        "rows": [],
        "interrupted_attempt": None,
        "requests": 0,
        "adjudication": "pending independent trace review; no false-alarm or miss claim",
    }
    _save(output, receipt)
    try:
        with ref.count_reference_calls(limit=CAP) as meter:
            ref.reset(with_seed=True)
            token = ref.token()
            receipt["requests"] = meter.requests
            _save(output, receipt)
            for case in CASES:
                required = 10 + 5 * len(case.actions)
                if CAP - meter.requests < required:
                    receipt["status"] = "budget_censored"
                    break
                receipt["interrupted_attempt"] = {"case_id": case.case_id, "partial_row": None}

                def retain(row: dict[str, Any], case_id: str = case.case_id) -> None:
                    receipt["interrupted_attempt"] = {"case_id": case_id, "partial_row": row}
                    receipt["requests"] = meter.requests
                    _save(output, receipt)

                row = run_case(case, token, [HISTORICAL_RULE], meter, retain)
                receipt["rows"].append(
                    {"raw": row, "ordinary": compare_case(row), "instrument": _instrument_case(row)}
                )
                receipt["interrupted_attempt"] = None
                receipt["requests"] = meter.requests
                _save(output, receipt)
                if row["outcome"] == "setup_failure":
                    receipt["status"] = "setup_failure"
                    break
            else:
                receipt["status"] = "complete"
            receipt["requests"] = meter.requests
    except Exception as exc:  # noqa: BLE001 - evidence must survive a failed run
        receipt["status"] = "machinery_failure"
        receipt["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
    receipt["ended_at_utc"] = datetime.now(UTC).isoformat()
    receipt["comparator_effort"] = (
        "unknown; shared raw trace and HTTP workload, implementation effort not measured"
    )
    receipt["case_outcomes"] = {
        method: dict(Counter(row[method]["outcome"] for row in receipt["rows"]))
        for method in ("ordinary", "instrument")
    }
    receipt["unstarted_cases"] = [case.case_id for case in CASES[len(receipt["rows"]) :]]
    _save(output, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(args.output.resolve())
    print(
        json.dumps(
            {k: result[k] for k in ("status", "requests", "case_outcomes", "unstarted_cases")},
            indent=2,
        )
    )
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
