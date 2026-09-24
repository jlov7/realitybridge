"""Milestone E — frozen transition comparison (PROTOCOL §4–§5).

What this run is:
- 30 authored semantic families (`experiments/families.py`), dev/test split
  fixed and disjoint by name prefix.
- Each family replayed against the emulator AND the live pinned reference,
  from fresh equivalent state, comparing after EVERY step.
- Scripted policies only (the families ARE the policies); no LLM involved.

What this run is NOT (honest boundaries):
- NOT a simulator-repair loop. Repair is Milestone D and is already committed.
- NOT tuned on the test families. Dev families are the ones selectors may see;
  test families are held out and reported separately.
- The reference is the pinned Gitea build; agreement here is with *that build*,
  not with correctness-in-the-abstract.

Measures (PROTOCOL §4):
- held-out (test-family) consequential disagreement
- false task-pass frequency (family where reference fails but emulator passed)
- reference-call cost per arm (each soft_reset + each step call counted)
- coverage and agreement published jointly (a family that reported unsupported
  is not agreement).

Run:  uvenv python experiments/frozen_comparison.py [--limit N]
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.differential_run import _project
from experiments.families import DEV_FAMILIES, TEST_FAMILIES, sequence
from reality_bridge import reference as ref
from reality_bridge.differential import compare
from reality_bridge.emulator import Emulator, EmulatorError

EVIDENCE = ROOT / "artifacts" / "evidence"


def run_family(name: str, tok: str) -> dict:
    """Replay one family against emulator + live reference; return result dict.

    Scope and honesty: `ref.soft_reset` (API-level) starts a fresh reference;
    the emulator resets in-memory. Each step is counted as one reference call;
    the reset is counted too — the reference-query count includes resets per
    PROTOCOL §3 ("The reference-query count includes setup ... and resets").
    """
    actions = [a.as_dict() for a in sequence(name)]

    emu = Emulator()
    emu.reset()
    steps: list[dict] = []
    first_problem: dict | None = None
    with ref.count_reference_calls() as meter:
        ref.soft_reset(tok)
        for a in actions:
            try:
                r_raw, r_err = ref.step_reference(a, tok), None
            except ref.ReferenceStepError as e:
                r_raw, r_err = None, e
            try:
                e_raw, e_err = emu.step(a), None
            except EmulatorError as e:
                e_raw, e_err = None, e
            r_obs, r_status = _project(a, r_raw, r_err)
            e_obs, e_status = _project(a, e_raw, e_err)
            d = compare(r_obs, e_obs)
            steps.append(
                {
                    "action": a,
                    "ref_status": r_status,
                    "emu_status": e_status,
                    "outcome": d.outcome,
                    "diff": d.evidence[:200],
                }
            )
            if d.outcome != "agree":
                first_problem = {
                    "at": len(steps) - 1,
                    "action": a,
                    "outcome": d.outcome,
                    "reason": d.reason,
                    "diff": d.evidence[:200],
                }
                break

    return {
        "family": name,
        "split": "dev" if name.startswith("dev-") else "test",
        "outcome": first_problem["outcome"] if first_problem else "agree",
        "first_problem": first_problem,
        "steps": steps,
        "ref_calls": meter.requests,
    }


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="limit total families run (0 = all)")
    args = ap.parse_args()

    tok = ref.token()
    order = DEV_FAMILIES + TEST_FAMILIES
    if args.limit:
        order = order[: args.limit]

    t0 = time.monotonic()
    results = [run_family(name, tok) for name in order]
    elapsed = time.monotonic() - t0

    dev = [r for r in results if r["split"] == "dev"]
    test = [r for r in results if r["split"] == "test"]

    def stats(rows: list[dict]) -> dict:
        n = len(rows)
        div = sum(1 for r in rows if r["outcome"] == "diverge")
        agree = sum(1 for r in rows if r["outcome"] == "agree")
        calls = sum(r["ref_calls"] for r in rows)
        undetermined = sum(1 for r in rows if r["outcome"] == "undetermined")
        unsupported = sum(1 for r in rows if r["outcome"] == "unsupported")
        return {
            "n": n,
            "coverage": agree + div,  # compared families (agree OR diverge)
            "undetermined": undetermined,
            "unsupported": unsupported,
            "agreement": agree,
            "disagreement": div,
            "reference_calls": calls,
        }

    s_dev, s_test = stats(dev), stats(test)
    report = {
        "protocol": "frozen (research/PROTOCOL.md §4/§5)",
        "families_total": len(results),
        "dev": s_dev,
        "test": s_test,
        "elapsed_s": round(elapsed, 2),
    }

    # coverage + agreement jointly, per family, for inspection
    report["per_family"] = [
        {"family": r["family"], "split": r["split"], "outcome": r["outcome"]} for r in results
    ]

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE / f"frozen-comparison-{int(time.time())}.json"
    out.write_text(json.dumps(report, indent=2))

    print(
        f"families run: {len(results)} (dev {s_dev['n']}, test {s_test['n']})  elapsed {elapsed:.1f}s"
    )
    print(
        f"DEV : coverage {s_dev['coverage']}/{s_dev['n']}  agreement {s_dev['agreement']}  disagreement {s_dev['disagreement']}  ref_calls {s_dev['reference_calls']}"
    )
    print(
        f"TEST: coverage {s_test['coverage']}/{s_test['n']}  agreement {s_test['agreement']}  disagreement {s_test['disagreement']}  ref_calls {s_test['reference_calls']}"
    )
    print(f"retained: {out}")

    # agreement = equal projection vs THIS pinned build, not "correct"; precise
    # per-family false-task-pass is a follow-up metrology step, not claimed here.
    print(
        "NOTE: agreement = equal projection vs this pinned build; precise",
        "false-task-pass per family is a follow-up metrology step, not claimed.",
    )


if __name__ == "__main__":
    main()
