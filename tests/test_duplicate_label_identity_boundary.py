"""Planted identity counterexamples for the declared-state projection.

These synthetic pairs challenge the oracle. They do not claim a Gitea defect.
"""

from __future__ import annotations

from copy import deepcopy

import pytest

from reality_bridge.state_oracle import (
    LabelPairing,
    StateOracleError,
    canonicalize_declared_state,
    compare_declared_states,
)


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


def test_unpaired_duplicate_membership_is_undetermined() -> None:
    left = _base()
    right = deepcopy(left)
    right["issues"][0]["labels"][0]["id"] = 18
    assert _outcome(left, right) == "undetermined"


def test_paired_creation_detects_swapped_duplicate_membership() -> None:
    left = _base()
    right = deepcopy(left)
    right["labels"][0]["id"] = 107
    right["labels"][1]["id"] = 108
    right["issues"][0]["labels"][0]["id"] = 108
    pair = LabelPairing({}, {})
    pair.note_creation(left["labels"][0], right["labels"][0])
    pair.note_creation(left["labels"][1], right["labels"][1])
    reference = canonicalize_declared_state(left, pair.reference_ids)
    simulator = canonicalize_declared_state(right, pair.simulator_ids)
    assert compare_declared_states(reference, simulator).outcome == "diverge"


def test_paired_creation_ignores_generated_id_drift_and_registry_order() -> None:
    left = _base()
    right = deepcopy(left)
    right["labels"][0]["id"] = 107
    right["labels"][1]["id"] = 108
    right["issues"][0]["labels"][0]["id"] = 107
    pair = LabelPairing({}, {})
    pair.note_creation(left["labels"][0], right["labels"][0])
    pair.note_creation(left["labels"][1], right["labels"][1])
    right["labels"].reverse()
    reference = canonicalize_declared_state(left, pair.reference_ids)
    simulator = canonicalize_declared_state(right, pair.simulator_ids)
    assert compare_declared_states(reference, simulator).outcome == "agree"


def test_unpaired_generated_id_drift_alone_is_not_a_divergence() -> None:
    left = _base()
    right = deepcopy(left)
    right["labels"][0]["id"] = 107
    right["labels"][1]["id"] = 108
    right["issues"][0]["labels"][0]["id"] = 107
    assert _outcome(left, right) == "undetermined"


def test_duplicate_membership_or_changed_color_remains_observable() -> None:
    left = _base()
    right = deepcopy(left)
    right["issues"][0]["labels"].append(deepcopy(right["issues"][0]["labels"][0]))
    assert _outcome(left, right) == "diverge"

    right = deepcopy(left)
    right["labels"][1]["color"] = "445566"
    assert _outcome(left, right) == "diverge"


def test_membership_id_cannot_alias_a_different_registry_row() -> None:
    raw = _base()
    raw["labels"][1]["color"] = "445566"
    raw["issues"][0]["labels"][0]["id"] = 18
    with pytest.raises(StateOracleError, match="does not match"):
        canonicalize_declared_state(raw)


def test_created_id_must_not_reuse_seed_or_a_prior_creation() -> None:
    raw = _base()
    pair = LabelPairing.from_initial(raw, raw)
    with pytest.raises(StateOracleError, match="reuses"):
        pair.note_creation(raw["labels"][0], raw["labels"][1])


@pytest.mark.parametrize("invalid_id", [True, False, 0, -1])
def test_initial_pairing_rejects_invalid_row_ids(invalid_id: object) -> None:
    raw = _base()
    raw["labels"][0]["id"] = invalid_id
    with pytest.raises(StateOracleError, match="positive integer"):
        LabelPairing.from_initial(raw, raw)


@pytest.mark.parametrize("invalid_id", [True, False, 0, -1])
def test_creation_pairing_rejects_invalid_row_ids(invalid_id: object) -> None:
    pair = LabelPairing({}, {})
    left = {"id": invalid_id, "name": "same", "color": "112233"}
    right = {"id": 19, "name": "same", "color": "112233"}
    with pytest.raises(StateOracleError, match="positive integer"):
        pair.note_creation(left, right)
