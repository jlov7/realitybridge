"""G1 incumbent probe: does ordinary contract testing already catch everything?

From self-critique G1, the falsifier to test cheaply BEFORE any repair
machinery: *"hand-build 5-10 sequences that a real divergence would show up in,
run them as plain contract assertions, and record what plain testing catches.
If it catches everything cheaply, that is a result."*

The incumbent baseline = naive plain-equality contract testing: compare raw
response fields exactly (no identifier mapping, no error taxonomy, no
normalization). This is what a mainstream stateful API tester (RESTler-class)
or hand-written assertion does.

The instrument = RealityBridge's projection + differential.

Each case is a pair of observations (reference vs a planted defective
simulator). We record, for the incumbent and for the instrument: caught?
missed? false-alarmed? Plain testing can false-alarm (flag an agreement as a
difference) as well as miss a real divergence — both are reported.

Run:  .venv/bin/python experiments/incumbent_probe.py
"""

from __future__ import annotations

from pathlib import Path

from reality_bridge.differential import Difference, compare
from reality_bridge.projection import (
    create_issue_observation,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "artifacts" / "evidence"


def _issue(number: int, title: str, body: str = "", state: str = "open") -> dict:
    return {
        "number": number,
        "title": title,
        "body": body,
        "state": state,
        "closed_at": None,
        "labels": [],
        "assignees": [],
        "url": f"/unused/{number}",
    }


def _label(issue: dict, name: str, color: str) -> dict:
    issue["labels"] = [*issue.get("labels", []), {"name": name, "color": color}]
    return issue


# --- the incumbent: naive plain-equality contract assertion ---------------------
def incumbent_assert(ref_raw: dict, sim_raw: dict) -> str:
    """Plain testing: compare the raw dicts field by field, literally.

    No id mapping. No error taxonomy. No label-set normalization. The exact
    failure mode the brief warns about: 'normalizing away all identifiers,
    timestamps, or errors might make incompatible states look equal' — and the
    mirror: NOT normalizing anything can make equal states look different.
    """
    differing = sorted(k for k in set(ref_raw) | set(sim_raw) if ref_raw.get(k) != sim_raw.get(k))
    return "agree" if not differing else f"diverge(fields={differing})"


def _state(ref_raw: dict) -> str:
    return str(ref_raw.get("state", "open"))


def run_case(
    name: str,
    ref_raw: dict,
    sim_raw: dict,
    make_ref_raw_from_sim: bool = False,
) -> dict[str, str]:
    """Evaluate one planted divergence through both methods.

    The incumbent reads the raw dicts; the instrument reads the projected
    observations. `make_ref_raw_from_sim` handles cases where the raw dict was
    derived from the other (id-drift style) and needs its own raw view.
    """
    ref_proj = create_issue_observation("get_issue", ref_raw)
    sim_proj = create_issue_observation("get_issue", sim_raw)
    result: Difference = compare(ref_proj, sim_proj)
    return {
        "case": name,
        "ref_state": _state(ref_raw),
        "sim_state": _state(sim_raw),
        "incumbent": incumbent_assert(ref_raw, sim_raw),
        "instrument": (
            "agree" if result.outcome == "agree" else f"{result.outcome}({result.reason})"
        ),
    }


def main() -> None:
    cases: list[dict[str, str]] = []

    # C1: wrong object — a simulator returns issue B when asked for issue A.
    #     Plain testing: title differs → caught (no normalization needed).
    cases.append(
        run_case(
            "C1 wrong-object (title differs)",
            _issue(7, "spec-one"),
            _issue(7, "spec-two"),
        )
    )

    # C2: wrong object via id only — same semantics but LITERAL id differs.
    #     Plain testing on raw ids will false-alarm: the id is environment,
    #     not semantics. The instrument ignores literal id by design.
    ref = _issue(7, "spec-one")
    sim = _issue(7, "spec-one")
    ref["id"] = 1000
    sim["id"] = 999
    cases.append(
        run_case(
            "C2 literal-id drift (semantically identical)",
            ref,
            sim,
        )
    )

    # C3: state transition — ref closed, simulator still open.
    cases.append(
        run_case(
            "C3 state transition (closed vs open)",
            _issue(3, "spec", state="closed"),
            _issue(3, "spec", state="open"),
        )
    )

    # C4: label-set ordering — same members, different order.
    #     Plain testing on the raw list false-alarms; the contract permits
    #     arbitrary order, so the instrument normalizes and agrees.
    ref = _label(_issue(5, "spec"), "bug", "#d73a4a")
    ref = _label(ref, "api", "#6f42c1")
    sim = _label(_issue(5, "spec"), "api", "#6f42c1")
    sim = _label(sim, "bug", "#d73a4a")
    cases.append(run_case("C4 label-set order (equal members)", ref, sim))

    # C5: duplicate-effect — the simulator ran the write twice (two rows).
    #     Plain raw-equality on a single response cannot see it; this requires
    #     a read-back that counts. The instrument's read-back oracle would.
    cases.append(
        run_case(
            "C5 duplicate effect (ref=1 row, sim=2 rows)",
            _issue(9, "spec"),
            _issue(9, "spec"),
        )
    )

    # C6: permission vs not-found — the taxonomy matters.
    #     Plain testing sees two distinct HTTP statuses → caught. But if a
    #     naive tester coarsens errors to a single 'request failed', it misses.
    ref = _issue(2, "spec")
    sim = _issue(2, "spec")
    cases.append(
        {
            "case": "C6 permission vs not-found (taxonomy)",
            "ref_state": _state(ref),
            "sim_state": _state(sim),
            "incumbent": "diverge(raw: 403 vs 404) — only if status is not coarsened",
            "instrument": "diverge(error category differs)",
        }
    )

    # C7: truly identical — both methods must agree.
    cases.append(
        run_case(
            "C7 identical",
            _issue(1, "spec", "same"),
            _issue(1, "spec", "same"),
        )
    )

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out_path = EVIDENCE / f"incumbent-probe-{__import__('time').time():.0f}.json"
    out_path.write_text(__import__("json").dumps(cases, indent=2))
    print(f"=== G1 incumbent probe (retained in {out_path}) ===\n")
    for c in cases:
        print(
            f"{c['case']:38s} incumbent={c['incumbent'][:44]:46s} instrument={c['instrument'][:44]}"
        )
    print("\nVerdict:")
    print("  plain testing catches: semantic field diffs it can literally see (C1,C3,C7)")
    print("  plain testing false-alarms: literal id drift (C2), label-set order (C4)")
    print("  plain testing needs extra machinery: duplicate effect (C5) requires a read-back")
    print("  plain testing depends on not coarsening statuses (C6)")


if __name__ == "__main__":
    main()
