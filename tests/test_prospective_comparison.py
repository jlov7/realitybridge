"""Prospective response comparisons fail closed on declared malformed fields."""

from __future__ import annotations

from reality_bridge.emulator import Emulator
from reality_bridge.prospective_comparison import compare_responses


def test_malformed_membership_row_cannot_agree_even_when_other_fields_match() -> None:
    simulator = Emulator()
    simulator.reset()
    raw = simulator.add_label("spec-repo", "1", "bug")
    malformed = [{"name": "bug"}]
    result = compare_responses("add_label", malformed, None, raw, None)
    assert result.outcome == "undetermined"


def test_omitted_issue_membership_cannot_agree() -> None:
    simulator = Emulator()
    simulator.reset()
    raw = simulator.get_issue("spec-repo", "1")
    malformed = {key: value for key, value in raw.items() if key != "labels"}
    assert compare_responses("get_issue", malformed, None, raw, None).outcome == "undetermined"


def test_shared_transport_unknown_cannot_agree() -> None:
    class Unknown(Exception):
        def __init__(self) -> None:
            self.status = 599
            self.body = {"message": "synthetic transport loss"}

    result = compare_responses("get_issue", None, Unknown(), None, Unknown())
    assert result.outcome == "undetermined"
