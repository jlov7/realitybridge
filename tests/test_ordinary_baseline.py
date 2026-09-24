"""Planted raw traces challenge the independent ordinary comparator before live data."""

from __future__ import annotations

from copy import deepcopy

from experiments.ordinary_baseline import compare_case, compare_step
from reality_bridge.emulator import Emulator


def _step() -> dict:
    candidate = Emulator()
    candidate.reset()
    state = candidate.export_declared_state()
    issue = state["issues"][0]
    return {
        "action": {"op": "get_issue", "args": ["rbadmin", "spec-repo", "1"]},
        "reference_response": deepcopy(issue),
        "simulator_response": deepcopy(issue),
        "reference_error": None,
        "simulator_error": None,
        "reference_state": deepcopy(state),
        "simulator_state": deepcopy(state),
    }


def test_benign_generated_identifier_drift_agrees() -> None:
    row = _step()
    row["simulator_response"]["id"] = 900
    row["simulator_response"]["url"] = "/different-host/issue/1"
    row["simulator_state"]["issues"][0]["id"] = 900
    assert compare_step(row)["outcome"] == "agree"


def test_wrong_logical_issue_detected() -> None:
    row = _step()
    row["simulator_response"]["number"] = 2
    assert compare_step(row)["outcome"] == "diverge"


def test_extra_row_detected_even_if_response_agrees() -> None:
    row = _step()
    row["simulator_state"]["issues"].append(deepcopy(row["simulator_state"]["issues"][0]))
    assert compare_step(row)["outcome"] == "diverge"


def test_duplicate_membership_detected() -> None:
    row = _step()
    row["simulator_state"]["issues"][0]["labels"].append(
        deepcopy(row["simulator_state"]["issues"][0]["labels"][0])
    )
    assert compare_step(row)["outcome"] == "diverge"


def test_reversed_timestamp_relation_detected() -> None:
    row = _step()
    row["simulator_state"]["issues"][0]["updated_at"] = "1999-01-01T00:00:00Z"
    assert compare_step(row)["outcome"] == "diverge"


def test_transport_uncertainty_never_agrees() -> None:
    row = _step()
    row["reference_error"] = {"status": 599, "body": {"message": "disconnect"}}
    row["reference_response"] = None
    assert compare_step(row)["outcome"] == "undetermined"


def test_missing_declared_field_is_unknown() -> None:
    row = _step()
    del row["simulator_state"]["issues"][0]["body"]
    assert compare_step(row)["outcome"] == "undetermined"


def test_boolean_error_status_is_unknown() -> None:
    row = _step()
    row["reference_error"] = {"status": True}
    row["reference_response"] = None
    assert compare_step(row)["outcome"] == "undetermined"


def test_truncated_and_extra_actions_are_unknown() -> None:
    step = _step()
    row = {
        "reference_initial": step["reference_state"],
        "simulator_initial": step["simulator_state"],
        "outcome": "agree",
        "actions": [step["action"]],
        "steps": [],
    }
    assert compare_case(row)["outcome"] == "undetermined"
    row["steps"] = [step, deepcopy(step)]
    assert compare_case(row)["outcome"] == "undetermined"
