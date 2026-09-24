"""Differential runner: replay sequences against emulator AND live reference.

Milestone C deliverable: run generated sequences through both the emulator and
the real Gitea, compare projections after every step, and either find a real
minimized divergence or retain no-divergence as a legitimate result.

Executed against the LIVE reference (Milestone A's pinned container), so it is
an integration experiment, not a fixture. Every divergent step is shrunk to its
shortest reproducing prefix and written to artifacts/evidence/.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # top-level `reference` package must resolve outside pytest

from reality_bridge import reference as ref
from reality_bridge import sequences
from reality_bridge.differential import compare
from reality_bridge.emulator import Emulator, EmulatorError
from reality_bridge.projection import error_observation, unsupported_observation
from reality_bridge.shrink import shrink

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "artifacts" / "evidence"


def _project(action: dict, raw: object, err: EmulatorError | ref.ReferenceStepError | None):
    """Project a raw response or error into an Observation (shared contract)."""
    from reality_bridge.projection import (
        create_issue_observation,
        issue_labels_observation,
        label_observation,
    )

    name = action["op"]
    if err is not None:
        if (
            isinstance(err, EmulatorError)
            and err.status == 400
            and str(err).startswith("unsupported op")
        ):
            return unsupported_observation(name), err.status
        status = err.status
        body = getattr(err, "body", {}) if hasattr(err, "body") else str(err)
        return error_observation(name, status, body), status
    if isinstance(raw, list):
        # Gitea's add_label/remove_label endpoints return a label array
        labels = sorted(
            (str(l.get("name", "")), str(l.get("color", ""))) for l in raw if isinstance(l, dict)
        )
        return issue_labels_observation(
            name, {"labels": [{"name": n, "color": c} for n, c in labels]}
        ), 200
    if not isinstance(raw, dict):
        return error_observation(name, 599, {}), 599
    if "number" in raw or "labels" in raw:
        return create_issue_observation(name, raw), 200
    if "name" in raw and "color" in raw:
        return label_observation(name, raw), 200
    return error_observation(name, 599, {}), 599


def run_differential(seed: int, max_len: int, count: int, budget: int, arm: str = "random") -> dict:
    """Run `count` generated sequences through emulator and reference.

    Each sequence starts from a fresh seeded pair (reference reset + emulator
    reset) and is compared after EVERY step. The first divergence is shrunk.

    `arm` selects the probe grammar:
      - "random"   → `sequences.generate`           (uniform over the grammar)
      - "targeted" → `sequences.generate_targeted`  (boundary/preconditions-biased)
    Actual HTTP requests, including soft-reset setup, read-backs, failures, and
    shrink probes, are metered. Equal generation parameters do not by themselves
    establish equal reference-call cost.
    """
    tok = ref.token()
    emu = Emulator()
    result_rows: list[dict] = []
    generator = sequences.generate_targeted if arm == "targeted" else sequences.generate

    with ref.count_reference_calls() as meter:
        for seq_i, actions in enumerate(generator(seed=seed, max_len=max_len, count=count)):
            row_start_calls = meter.requests
            ref.soft_reset(
                tok
            )  # API-level reset; full container reset would wedge Docker per trial
            emu.reset()
            row: dict = {"sequence_index": seq_i, "steps": [], "outcome": "agree"}
            divergence: dict | None = None
            for step_i, a in enumerate(actions):
                action = a.as_dict()
                # emulator step
                try:
                    emu_raw = emu.step(action)
                    emu_err = None
                except EmulatorError as e:
                    emu_raw, emu_err = None, e
                # reference step
                try:
                    ref_raw = ref.step_reference(action, tok)
                    ref_err = None
                except ref.ReferenceStepError as e:
                    ref_raw, ref_err = None, e
                ref_obs, ref_status = _project(action, ref_raw, ref_err)
                emu_obs, emu_status = _project(action, emu_raw, emu_err)
                diff = compare(ref_obs, emu_obs)
                row["steps"].append(
                    {
                        "action": action,
                        "ref_status": ref_status,
                        "emu_status": emu_status,
                        "outcome": diff.outcome,
                        "reason": diff.reason,
                        "evidence": diff.evidence[:300],
                    }
                )
                if diff.outcome != "agree":
                    row["outcome"] = diff.outcome
                if diff.outcome == "diverge" and divergence is None:
                    divergence = {
                        "at_step": step_i,
                        "action": action,
                        "ref": ref_raw if ref_status == 200 else f"err:{ref_status}",
                        "emu": emu_raw if emu_status == 200 else f"err:{emu_status}",
                        "diff": diff.evidence[:300],
                    }
                    row["divergence"] = divergence

                    # shrink: shortest prefix of the actions SO FAR that reproduces
                    def reproduces(prefix: list) -> bool:
                        ref.soft_reset(
                            tok
                        )  # API-level reset; container reset per probe would wedge Docker
                        emu.reset()
                        for a2 in prefix:
                            a2_dict = a2.as_dict() if hasattr(a2, "as_dict") else a2
                            try:
                                r2 = emu.step(a2_dict)
                                e2 = None
                            except EmulatorError as er2:
                                r2, e2 = None, er2
                            try:
                                q2 = ref.step_reference(a2_dict, tok)
                                f2 = None
                            except ref.ReferenceStepError as fr2:
                                q2, f2 = None, fr2
                            ro2, _ = _project(a2_dict, q2, f2)
                            eo2, _ = _project(a2_dict, r2, e2)
                            if compare(ro2, eo2).outcome == "diverge":
                                return True
                        return False

                    row["minimal_prefix"] = [
                        x.as_dict() for x in shrink(actions[: step_i + 1], reproduces)
                    ]
                    break  # one divergence per sequence is enough for the pilot
                if diff.outcome in ("undetermined", "unsupported"):
                    row["inconclusive"] = {
                        "at_step": step_i,
                        "outcome": diff.outcome,
                        "reason": diff.reason,
                    }
                    break
            row["reference_calls"] = meter.requests - row_start_calls
            result_rows.append(row)
            if budget and seq_i + 1 >= budget:
                break

    return {
        "seed": seed,
        "max_len": max_len,
        "count": len(result_rows),
        "reference_calls": meter.requests,
        "rows": result_rows,
    }


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--max-len", type=int, default=5)
    ap.add_argument("--count", type=int, default=5)
    ap.add_argument("--budget", type=int, default=5)
    ap.add_argument("--arm", choices=["random", "targeted"], default="random")
    args = ap.parse_args()

    t0 = time.monotonic()
    result = run_differential(args.seed, args.max_len, args.count, args.budget, arm=args.arm)
    elapsed = time.monotonic() - t0

    n_div = sum(1 for r in result["rows"] if r.get("divergence"))
    print(
        f"arm={args.arm}: sequences run: {len(result['rows'])}  divergences: {n_div}  "
        f"reference_calls: {result['reference_calls']}  elapsed: {elapsed:.1f}s"
    )
    for r in result["rows"]:
        if r.get("divergence"):
            print(
                f"  seq#{r['sequence_index']} diverged at step {r['divergence']['at_step']}: "
                f"action={r['divergence']['action']['op']} prefix_len={len(r.get('minimal_prefix', []))}"
            )

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE / f"differential-{args.arm}-{int(time.time())}.json"
    out.write_text(
        json.dumps({**result, "arm": args.arm, "elapsed_s": round(elapsed, 2)}, indent=2)
    )
    print(f"retained: {out}")


if __name__ == "__main__":
    main()
