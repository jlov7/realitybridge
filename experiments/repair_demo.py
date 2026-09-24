"""Live repair demonstration (Milestone D).

Flow, all against the real pinned reference:
1. Differential run finds the first real divergence (with a shrunk prefix).
2. Extract the counterexample: minimal_prefix (actions) + reference observation.
3. Derive/apply the repair rule through the emulator's public seam.
4. Verify: the counterexample now AGREES, and a regression sequence (one that
   produced no divergence before) STILL agrees.

`agrees` here replays a fresh emulator+reference pair and does a real per-step
comparison — the stub from the unit tests is not used. Holdout isolation is
already proven by tests/test_repair_holdout_isolation.py; this demo is the
live end-to-end loop closure.

Run:  .venv/bin/python experiments/repair_demo.py --seed 7 --count 5
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reality_bridge import reference as ref
from reality_bridge.differential import compare
from reality_bridge.emulator import Emulator, EmulatorError
from reality_bridge.repair import repair

EVIDENCE = ROOT / "artifacts" / "evidence"


def make_evaluator(tok: str):
    """Build a real evaluator that replays a fresh pair.

    This is the live comparison: reset BOTH via API-level soft reset + emulator
    reset, step both, compare after each step.

    Returns: agrees function AND a small regression recorder (what actually
    agreed/differed, for the retained evidence).
    """

    from experiments.differential_run import _project

    def evaluate(emu: Emulator, seq: list[dict]):
        ref.soft_reset(tok)
        emu.reset()
        for a in seq:
            try:
                emu_raw, emu_err = emu.step(a), None
            except EmulatorError as e:
                emu_raw, emu_err = None, e
            try:
                ref_raw, ref_err = ref.step_reference(a, tok), None
            except ref.ReferenceStepError as e:
                ref_raw, ref_err = None, e
            ref_obs, _ = _project(a, ref_raw, ref_err)
            emu_obs, _ = _project(a, emu_raw, emu_err)
            outcome = compare(ref_obs, emu_obs).outcome
            if outcome != "agree":
                return outcome
        return "agree"

    return evaluate


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--max-len", type=int, default=5)
    ap.add_argument("--count", type=int, default=5)
    ap.add_argument("--budget", type=int, default=5)
    args = ap.parse_args()

    if Emulator.normalize_color("#aabbcc") != "#aabbcc":
        raise SystemExit(
            "The historical repair demo requires the materialized research baseline; "
            "run experiments/materialize_research_baseline.py first."
        )

    tok = ref.token()
    evaluate = make_evaluator(tok)

    # Use differential_run helpers: find the first real divergence + minimal prefix.
    from experiments.differential_run import run_differential

    t0 = time.monotonic()
    diff = run_differential(args.seed, args.max_len, args.count, args.budget)
    row = next((r for r in diff["rows"] if r.get("divergence")), None)
    if row is None:
        print("NO divergence found in this run — nothing to repair (legitimate result).")
        sys.exit(0)
    divergence = row["divergence"]
    prefix = row.get("minimal_prefix") or [
        x if isinstance(x, dict) else x.as_dict() for x in [divergence["action"]]
    ]
    counterexample = {"prefix": prefix, "ref": divergence["ref"], "sim": divergence["emu"]}

    print(f"divergence at step {divergence['at_step']}: {divergence['action']['op']}")
    print(f"  evidence: {divergence['diff'][:200]}")
    print(f"  minimal prefix: {json.dumps(prefix)}")

    # Regression = a sequence from the same run that AGREED end to end.
    regression_seq = next((r["steps"] for r in diff["rows"] if r["outcome"] == "agree"), None)
    regressions = []
    if regression_seq is not None:
        regression_actions = [s["action"] for s in regression_seq]
        regressions = [regression_actions]
        print(f"regression sequence (previously agreed): {json.dumps(regression_actions)}")

    counterexample_actions = [a for a in counterexample["prefix"]]
    print(f"\nBEFORE repair: {evaluate(Emulator(), counterexample_actions)}")

    emu = Emulator()
    emu.reset()
    # NOTE: agrees() resets internally; repair() passes emu but agrees ignores it.
    result = repair(emu, counterexample, regressions, evaluate)

    print(f"\nrules derived: {[r.transform for r in result.rules_applied]}")
    print(f"counterexample now agrees: {result.counterexample_now_agrees}")
    print(f"regressions still agree:   {result.regressions_still_agree}")

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE / f"repair-demo-{int(time.time())}.json"
    out.write_text(
        json.dumps(
            {
                "seed": args.seed,
                "counterexample": counterexample,
                "rules": [
                    {"field": r.field, "transform": r.transform, "evidence": r.evidence}
                    for r in result.rules_applied
                ],
                "counterexample_now_agrees": result.counterexample_now_agrees,
                "regressions_still_agree": result.regressions_still_agree,
                "verified": result.verified,
                "reason": result.reason,
                "elapsed_s": round(time.monotonic() - t0, 2),
            },
            indent=2,
        )
    )
    verdict = "REPAIR VERIFIED" if result.verified else "REPAIR NOT YET VERIFIED"
    print(f"\n{verdict} — evidence retained: {out}")


if __name__ == "__main__":
    main()
