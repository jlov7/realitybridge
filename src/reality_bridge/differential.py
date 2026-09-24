"""Differential comparison: reference observation vs simulator observation.

The core contract from `contracts/`: `compare(reference, simulator) -> Difference`.

Four outcomes, and `undetermined` is not optional:
- agree
- diverge(reason, evidence)
- undetermined(reason)   — comparison could not decide
- unsupported(operation) — the simulator explicitly does not implement it

`undetermined` must never collapse into `agree`. This module is the guard
against erasing the signal: if a field is excluded from the projection, a
difference in it cannot be reported, so the projection's exclusions must be
deliberate (see contracts/observation.yaml).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from reality_bridge.projection import IssueObservation, Observation

Outcome = Literal["agree", "diverge", "undetermined", "unsupported"]


@dataclass(frozen=True, slots=True)
class Difference:
    outcome: Outcome
    reason: str = ""
    evidence: str = ""

    @property
    def is_issue(self) -> bool:
        return self.outcome != "agree"


def agree() -> Difference:
    return Difference("agree")


def diverge(reason: str, evidence: str) -> Difference:
    return Difference("diverge", reason=reason, evidence=evidence)


def undetermined(reason: str) -> Difference:
    return Difference("undetermined", reason=reason)


def unsupported(operation: str) -> Difference:
    return Difference("unsupported", reason=f"{operation} is not implemented by the simulator")


def _diff_issues(a: IssueObservation, b: IssueObservation) -> Difference:
    """Compare two normalized issue projections field by field."""
    diffs: list[str] = []
    if a.number != b.number:
        diffs.append(f"number: ref={a.number} sim={b.number}")
    if a.title != b.title:
        diffs.append(f"title: ref={a.title!r} sim={b.title!r}")
    if a.body != b.body:
        diffs.append(f"body: ref={a.body!r} sim={b.body!r}")
    if a.state != b.state:
        diffs.append(f"state: ref={a.state} sim={b.state}")
    if a.closed != b.closed:
        diffs.append(f"closed: ref={a.closed} sim={b.closed}")
    if a.labels != b.labels:
        diffs.append(f"labels: ref={a.labels} sim={b.labels}")
    if a.assignees != b.assignees:
        diffs.append(f"assignees: ref={a.assignees} sim={b.assignees}")
    if a.temporal_relation != b.temporal_relation:
        diffs.append(f"temporal_relation: ref={a.temporal_relation} sim={b.temporal_relation}")
    if diffs:
        return diverge("issue fields differ", "; ".join(diffs))
    return agree()


def compare(reference: Observation, simulator: Observation) -> Difference:
    """Compare two projections of the same action after the same sequence.

    Error categories are distinct: a 403 where the simulator produced a 404 is
    a divergence, never a blurred 'error' bucket.
    """
    if reference.action != simulator.action:
        return diverge("action differs", f"ref={reference.action} sim={simulator.action}")

    if simulator.unsupported_operation is not None:
        return unsupported(simulator.unsupported_operation)
    if reference.unsupported_operation is not None:
        return undetermined("reference operation was unsupported")

    # A lost response cannot establish a semantic mismatch, even when the
    # other side returned a definite result. Keep coverage uncertainty separate.
    if "transport_uncertain" in (reference.error, simulator.error):
        if reference.error == simulator.error:
            return undetermined("both exchanges were transport-uncertain")
        side = "reference" if reference.error == "transport_uncertain" else "simulator"
        return undetermined(f"{side} exchange was transport-uncertain")

    if reference.error is not None or simulator.error is not None:
        if reference.error != simulator.error:
            return diverge(
                "error category differs",
                f"ref={reference.error} sim={simulator.error} (ref detail: {reference.detail!r})",
            )
        return agree()

    payloads = {
        "issue": (reference.issue is not None, simulator.issue is not None),
        "label": (reference.label is not None, simulator.label is not None),
        "label_set": (reference.label_set is not None, simulator.label_set is not None),
    }
    ref_kinds = [name for name, (ref_present, _) in payloads.items() if ref_present]
    sim_kinds = [name for name, (_, sim_present) in payloads.items() if sim_present]
    if len(ref_kinds) != 1 or len(sim_kinds) != 1:
        return undetermined(
            f"comparison requires one payload per side (ref={ref_kinds}, sim={sim_kinds})"
        )
    if ref_kinds != sim_kinds:
        return diverge("payload kind differs", f"ref={ref_kinds[0]} sim={sim_kinds[0]}")

    if reference.issue is not None and simulator.issue is not None:
        return _diff_issues(reference.issue, simulator.issue)

    if reference.label is not None and simulator.label is not None:
        if reference.label != simulator.label:
            return diverge("label differs", f"ref={reference.label} sim={simulator.label}")
        return agree()

    if reference.label_set != simulator.label_set:
        return diverge("label set differs", f"ref={reference.label_set} sim={simulator.label_set}")
    return agree()
