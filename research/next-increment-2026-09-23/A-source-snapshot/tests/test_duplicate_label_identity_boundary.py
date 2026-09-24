"""Planted identity counterexamples for the declared-state projection.

These synthetic pairs challenge the oracle. They do not claim a Gitea defect.
"""

from __future__ import annotations

from copy import deepcopy

from reality_bridge.state_oracle import canonicalize_declared_state, compare_declared_states


def _base() -> dict:
    issue = {
        "number": 1,
        "title": "synthetic",
        "body": "",
        "state": "open",
        "closed_at": None,
        "created_at": "2000-01-01T00:00:00Z",
        "updated_at": "2000-01-01T00:00:00Z",
        "assignees": [],
        "labels": [{"id": 17, "name": "same", "color": "112233"}],
    }
    return {
        "issues": [issue],
        "labels": [
            {"id": 17, "name": "same", "color": "112233"},
            {"id": 18, "name": "same", "color": "112233"},
        ],
    }


def _outcome(left: dict, right: dict) -> str:
    return compare_declared_states(
        canonicalize_declared_state(left), canonicalize_declared_state(right)
    ).outcome


def test_same_name_color_different_membership_row_is_a_documented_blind_spot() -> None:
    left = _base()
    right = deepcopy(left)
    right["issues"][0]["labels"][0]["id"] = 18
    assert _outcome(left, right) == "agree"


def test_unpaired_generated_id_drift_alone_is_not_a_divergence() -> None:
    left = _base()
    right = deepcopy(left)
    right["labels"][0]["id"] = 107
    right["labels"][1]["id"] = 108
    right["issues"][0]["labels"][0]["id"] = 107
    assert _outcome(left, right) == "agree"


def test_duplicate_membership_or_changed_color_remains_observable() -> None:
    left = _base()
    right = deepcopy(left)
    right["issues"][0]["labels"].append(deepcopy(right["issues"][0]["labels"][0]))
    assert _outcome(left, right) == "diverge"

    right = deepcopy(left)
    right["labels"][1]["color"] = "445566"
    assert _outcome(left, right) == "diverge"
