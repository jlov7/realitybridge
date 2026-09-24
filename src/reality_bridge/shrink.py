"""Deterministic mismatch shrinker (delta debugging for our sequences).

`shrink(sequence, reproduces)` — given a full sequence that produced a
divergence, return the smallest prefix that still reproduces a divergence.
Deterministic: same input always yields the same output, so the counterexample
is a stable, communicable artifact ("the shortest prefix where the simulator
disagrees with the reference").
"""

from __future__ import annotations

from collections.abc import Callable

from reality_bridge.sequences import Action


def shrink(sequence: list[Action], reproduces: Callable[[list[Action]], bool]) -> list[Action]:
    """Return the shortest prefix of `sequence` that still reproduces a divergence.

    `reproduces(prefix)` drives the pair fresh and returns True if any
    divergence occurs anywhere in the prefix. Binary-search the length, then
    tighten to the earliest divergent step within that length. The result is a
    prefix of the original sequence, never a reordering.
    """
    if not sequence:
        return []

    # smallest length L in [1, len(sequence)] whose prefix reproduces
    lo, hi = 1, len(sequence)
    while lo < hi:
        mid = (lo + hi) // 2
        if reproduces(sequence[:mid]):
            hi = mid
        else:
            lo = mid + 1
    return sequence[:lo]


# Full-state extension. The original shortest-prefix function remains unchanged
# for historical callers and source-bound evidence.
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class DefectSignature:
    """Target action and comparison channel; field/evidence refine broad state defects."""

    action: Action
    channel: Literal["response", "state"]
    reason: str
    field: str | None = None
    evidence_contains: str | None = None


@dataclass(frozen=True, slots=True)
class ProbeResult:
    outcome: Literal["reproduced", "absent", "unknown"]
    requests: int
    detail: str = ""


@dataclass(frozen=True, slots=True)
class MinimizeResult:
    sequence: tuple[Action, ...]
    complete: bool
    requests: int
    probes: int
    reason: str


class _IncompleteProbe(Exception):
    pass


def signature_in_trace(
    steps: list[dict], signature: DefectSignature
) -> Literal["reproduced", "absent", "unknown"]:
    """Return reproduced, absent, or unknown from full response/state step records."""
    uncertain = False
    for step in steps:
        if step.get("action") != signature.action.as_dict():
            for channel in ("response", "state"):
                uncertain |= step.get(channel, {}).get("outcome") in {"undetermined", "unsupported"}
            continue
        part = step.get(signature.channel, {})
        outcome = part.get("outcome")
        if outcome in {"undetermined", "unsupported"}:
            uncertain = True
            continue
        evidence = str(part.get("evidence", ""))
        if (
            outcome == "diverge"
            and part.get("reason") == signature.reason
            and (signature.field is None or f"{signature.field}:" in evidence)
            and (signature.evidence_contains is None or signature.evidence_contains in evidence)
        ):
            return "reproduced"
    return "unknown" if uncertain else "absent"


def minimize_signature(
    sequence: list[Action],
    signature: DefectSignature,
    probe: Callable[[list[Action], int], ProbeResult],
    *,
    request_budget: int,
) -> MinimizeResult:
    """Prefix then interior-action deletion, with fresh metered replay per probe.

    A candidate is accepted only after an explicit reproduced result. Unknown,
    including exhausted budget, returns an incomplete receipt, never success.
    """
    if request_budget < 0:
        raise ValueError("request budget must be nonnegative")
    spent = 0
    probes = 0
    best = list(sequence)

    def check(candidate: list[Action]) -> bool:
        nonlocal spent, probes
        if spent >= request_budget:
            raise _IncompleteProbe("request budget exhausted")
        result = probe(candidate, request_budget - spent)
        if result.requests < 0 or result.requests > request_budget - spent:
            raise _IncompleteProbe("probe exceeded declared request budget")
        spent += result.requests
        probes += 1
        if result.outcome == "unknown":
            raise _IncompleteProbe(result.detail or "reference outcome unknown")
        return result.outcome == "reproduced"

    try:
        if not sequence or not check(best):
            return MinimizeResult(
                tuple(best), False, spent, probes, "original target not reproduced"
            )
        best = shrink(best, check)
        index = 0
        while index < len(best) - 1:
            candidate = best[:index] + best[index + 1 :]
            if check(candidate):
                best = candidate
                index = 0
            else:
                index += 1
        if not check(best):
            return MinimizeResult(
                tuple(best), False, spent, probes, "final recheck did not reproduce"
            )
        return MinimizeResult(
            tuple(best), True, spent, probes, "signature reproduced after final recheck"
        )
    except _IncompleteProbe as exc:
        return MinimizeResult(tuple(best), False, spent, probes, str(exc))
