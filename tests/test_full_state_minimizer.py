"""Planted controls for signature, setup dependency, uncertainty, and metering."""

from __future__ import annotations

from reality_bridge.sequences import Action
from reality_bridge.shrink import (
    DefectSignature,
    ProbeResult,
    minimize_signature,
    signature_in_trace,
)

SETUP = Action("create_label", ("rbadmin", "spec-repo", "needed", "123456"))
IRRELEVANT = Action("get_issue", ("rbadmin", "spec-repo", "1"))
WRONG = Action("create_issue", ("rbadmin", "spec-repo", "wrong"))
TARGET = Action("add_label", ("rbadmin", "spec-repo", "1", "needed"))
SIG = DefectSignature(TARGET, "state", "declared post-state differs", "labels")


def _trace(actions: list[Action]) -> list[dict]:
    steps = []
    for action in actions:
        if action == WRONG:
            response = {
                "outcome": "diverge",
                "reason": "issue fields differ",
                "evidence": "wrong object",
            }
            state = {"outcome": "agree"}
        elif action == TARGET and SETUP in actions[: actions.index(TARGET)]:
            response = {"outcome": "agree"}
            state = {
                "outcome": "diverge",
                "reason": "declared post-state differs",
                "evidence": "labels: target membership differs",
            }
        else:
            response = {"outcome": "agree"}
            state = {"outcome": "agree"}
        steps.append({"action": action.as_dict(), "response": response, "state": state})
    return steps


def test_preserves_target_and_setup_while_deleting_wrong_defect_and_irrelevant_action() -> None:
    def probe(actions: list[Action], remaining: int) -> ProbeResult:
        return ProbeResult(signature_in_trace(_trace(actions), SIG), 1)

    result = minimize_signature([WRONG, SETUP, IRRELEVANT, TARGET], SIG, probe, request_budget=30)
    assert result.complete
    assert result.sequence == (SETUP, TARGET)
    assert result.requests == result.probes


def test_state_only_mismatch_is_visible() -> None:
    assert signature_in_trace(_trace([SETUP, TARGET]), SIG) == "reproduced"
    wrong = DefectSignature(WRONG, "state", "declared post-state differs", "labels")
    assert signature_in_trace(_trace([WRONG, SETUP, TARGET]), wrong) == "absent"


def test_unknown_cannot_certify_shorter_counterexample() -> None:
    def probe(actions: list[Action], remaining: int) -> ProbeResult:
        return ProbeResult("reproduced" if len(actions) == 3 else "unknown", 1, "transport failure")

    result = minimize_signature([SETUP, IRRELEVANT, TARGET], SIG, probe, request_budget=30)
    assert not result.complete
    assert result.sequence == (SETUP, IRRELEVANT, TARGET)
    assert "transport" in result.reason


def test_budget_exhaustion_is_incomplete() -> None:
    def probe(actions: list[Action], remaining: int) -> ProbeResult:
        return ProbeResult("reproduced", 1)

    result = minimize_signature([SETUP, TARGET], SIG, probe, request_budget=1)
    assert not result.complete
    assert result.requests == 1
    assert "budget" in result.reason


def test_probe_overrun_cannot_certify() -> None:
    def probe(actions: list[Action], remaining: int) -> ProbeResult:
        return ProbeResult("reproduced", remaining + 1)

    result = minimize_signature([SETUP, TARGET], SIG, probe, request_budget=1)
    assert not result.complete
    assert "exceeded" in result.reason


def test_same_action_reason_and_field_cannot_substitute_other_evidence() -> None:
    target = DefectSignature(
        TARGET, "state", "declared post-state differs", "labels", "target membership"
    )
    other = [
        {
            "action": TARGET.as_dict(),
            "response": {"outcome": "agree"},
            "state": {
                "outcome": "diverge",
                "reason": "declared post-state differs",
                "evidence": "labels: unrelated membership differs",
            },
        }
    ]
    assert signature_in_trace(other, target) == "absent"
    assert signature_in_trace(_trace([SETUP, TARGET]), target) == "reproduced"
