"""Exposed 12-case engineering requalification of the current emulator.

This is separate from the frozen ordinary-baseline study. It reuses its case
inventory and both comparators, but measures a later repaired source tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from experiments.ordinary_baseline import compare_case
from experiments.ordinary_baseline_cases import CASES, case_hash
from experiments.ordinary_baseline_study import _instrument_case
from experiments.research_completion import _running_reference_image, run_case
from reality_bridge import reference as ref

CAP = 320
SOURCE_FILES = (
    "experiments/current_requalification.py",
    "experiments/ordinary_baseline.py",
    "experiments/ordinary_baseline_cases.py",
    "experiments/ordinary_baseline_study.py",
    "experiments/research_completion.py",
    "src/reality_bridge/emulator.py",
    "src/reality_bridge/state_oracle.py",
    "src/reality_bridge/prospective_comparison.py",
    "src/reality_bridge/reference.py",
    "reference/seed.py",
    "reference/compose.yaml",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _write(output: Path, receipt: dict[str, Any]) -> None:
    temp = output.with_suffix(".tmp")
    temp.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n")
    temp.replace(output)


def run(output: Path) -> dict[str, Any]:
    if os.environ.get("REALITYBRIDGE_OWNED_REFERENCE") != "1":
        raise RuntimeError("current requalification requires owned reference lifecycle")
    if output.exists():
        raise FileExistsError(output)
    if _git("status", "--porcelain"):
        raise RuntimeError("commit current source before live requalification")
    output.parent.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, Any] = {
        "status": "running",
        "classification": "exposed engineering requalification of current repaired emulator",
        "started_at_utc": datetime.now(UTC).isoformat(),
        "source_commit": _git("rev-parse", "HEAD"),
        "source_tree": _git("rev-parse", "HEAD^{tree}"),
        "clean_tree_at_start": True,
        "source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCE_FILES
        },
        "case_sha256": case_hash(),
        "image": _running_reference_image(),
        "hard_cap": CAP,
        "requests": 0,
        "rows": [],
        "interrupted_attempt": None,
    }
    _write(output, receipt)
    try:
        with ref.count_reference_calls(limit=CAP) as meter:
            ref.reset(with_seed=True)
            token = ref.token()
            receipt["requests"] = meter.requests
            _write(output, receipt)
            for case in CASES:
                if CAP - meter.requests < 10 + 5 * len(case.actions):
                    receipt["status"] = "budget_censored"
                    break
                receipt["interrupted_attempt"] = {"case_id": case.case_id, "partial_row": None}

                def retain(row: dict[str, Any], case_id: str = case.case_id) -> None:
                    receipt["interrupted_attempt"] = {"case_id": case_id, "partial_row": row}
                    receipt["requests"] = meter.requests
                    _write(output, receipt)

                row = run_case(case, token, [], meter, retain)
                receipt["rows"].append(
                    {"raw": row, "ordinary": compare_case(row), "instrument": _instrument_case(row)}
                )
                receipt["interrupted_attempt"] = None
                receipt["requests"] = meter.requests
                _write(output, receipt)
                if row["outcome"] == "setup_failure":
                    receipt["status"] = "setup_failure"
                    break
            else:
                receipt["status"] = "complete"
            receipt["requests"] = meter.requests
    except Exception as exc:  # noqa: BLE001 - preserve failed phase and partial record
        receipt["status"] = "machinery_failure"
        receipt["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
    receipt["ended_at_utc"] = datetime.now(UTC).isoformat()
    receipt["case_outcomes"] = {
        method: dict(Counter(row[method]["outcome"] for row in receipt["rows"]))
        for method in ("ordinary", "instrument")
    }
    receipt["unstarted_cases"] = [case.case_id for case in CASES[len(receipt["rows"]) :]]
    _write(output, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = run(args.output.resolve())
    print(
        json.dumps(
            {
                key: receipt[key]
                for key in (
                    "status",
                    "source_commit",
                    "requests",
                    "case_outcomes",
                    "unstarted_cases",
                )
            },
            indent=2,
        )
    )
    return 0 if receipt["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
