"""Source-checkout entry point for exact offline replay and explicit live example."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
RECEIPT = ROOT / "artifacts/research-completion-2026-09-22/attempt-20260922T182622Z-59359"


def replay(receipt: Path, output: Path | None = None) -> dict[str, Any]:
    from experiments.materialize_research_baseline import materialize

    if not (receipt / "receipt.json").is_file():
        raise FileNotFoundError(f"measured baseline receipt missing: {receipt / 'receipt.json'}")
    with tempfile.TemporaryDirectory(prefix="rb-public-replay-") as temp:
        baseline = Path(temp) / "baseline"
        materialize(baseline)
        env = {**os.environ, "PYTHONPATH": f"{baseline / 'src'}:{baseline}"}
        command = [
            sys.executable,
            str(baseline / "experiments/reproduce_research_completion.py"),
            str(receipt.resolve()),
        ]
        process = subprocess.run(
            command, cwd=baseline, env=env, capture_output=True, text=True, check=False
        )
        if process.returncode:
            raise RuntimeError(
                f"offline replay failed ({process.returncode}): {process.stderr.strip() or process.stdout.strip()}"
            )
        raw = json.loads(process.stdout)
    outcomes = Counter(raw["evaluation_outcomes"].values())
    summary: dict[str, Any] = {
        "status": "reproduced",
        "mode": "offline measured baseline replay",
        "source_commit": raw["source_commit"],
        "case_sha256": raw["case_sha256"],
        "reference_image": "gitea/gitea@sha256:0489485c8afcb367a1c8066e081ec47d1592258dcbf729875e8bf4aa0b84a7c9",
        "harness_requests": raw["harness_requests"],
        "evaluation_outcomes": dict(outcomes),
        "policy_summary": raw["policy_summary"],
        "receipt": str(receipt.resolve()),
        "scope": "2026-09-22 authored finite study; no new reference calls",
        "details": raw,
    }
    if output is not None:
        if output.exists():
            raise FileExistsError(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    offline = sub.add_parser("replay", help="validate the frozen measured result without Docker")
    offline.add_argument("--receipt", type=Path, default=RECEIPT)
    offline.add_argument("--output", type=Path)
    live = sub.add_parser("live", help="one current-emulator trial on an owned reference")
    live.add_argument("--output", type=Path, required=True)
    live.add_argument("--case", choices=["D02", "D14"], default="D14")
    args = parser.parse_args()
    if args.mode == "replay":
        result = replay(args.receipt, args.output)
        policy = result["policy_summary"]
        print(f"Offline measured replay: {result['evaluation_outcomes']}")
        print(f"Reference requests recorded: {result['harness_requests']}")
        print(
            "Policy: "
            f"rank disagreement={policy['rank_disagreement']}, "
            f"simulator-induced regret={policy['simulation_induced_regret_component']}, "
            f"task-shift regret={policy['task_shift_regret_component']}"
        )
        if args.output:
            print(f"Structured report: {args.output.resolve()}")
        return 0
    if os.environ.get("REALITYBRIDGE_OWNED_REFERENCE") != "1":
        parser.error("live mode requires reference/owned_lifecycle.py and its preflight")
    from experiments.live_example import run

    result = run(args.output.resolve(), args.case)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
