"""Full declared-state oracle and silent-mutation falsifiers."""

from __future__ import annotations

import inspect

import pytest

from reality_bridge.emulator import Emulator
from reality_bridge.state_oracle import (
    StateOracleError,
    canonicalize_declared_state,
    compare_declared_states,
)


def _raw_state() -> dict:
    emu = Emulator()
    emu.reset()
    return emu.export_declared_state()


def _outcome(left: dict, right: dict) -> str:
    return compare_declared_states(
        canonicalize_declared_state(left), canonicalize_declared_state(right)
    ).outcome


def test_oracle_does_not_import_emulator_transition_code() -> None:
    import reality_bridge.state_oracle as oracle

    assert "reality_bridge.emulator" not in inspect.getsource(oracle)


def test_order_is_normalized_without_erasing_duplicates() -> None:
    left = _raw_state()
    right = {"issues": list(reversed(left["issues"])), "labels": list(reversed(left["labels"]))}
    assert _outcome(left, right) == "agree"

    right["issues"].append(dict(right["issues"][0]))
    diff = compare_declared_states(
        canonicalize_declared_state(left), canonicalize_declared_state(right)
    )
    assert diff.outcome == "diverge"
    assert "issue_count" in diff.evidence


def test_silent_extra_issue_mutation_is_detected() -> None:
    expected = _raw_state()
    silently_mutated = _raw_state()
    silently_mutated["issues"][1]["state"] = "closed"
    silently_mutated["issues"][1]["closed_at"] = "2000-01-01T00:00:02Z"
    assert _outcome(expected, silently_mutated) == "diverge"


def test_silent_unrelated_label_mutation_is_detected() -> None:
    expected = _raw_state()
    silently_mutated = _raw_state()
    silently_mutated["labels"].append({"name": "extra", "color": "abcdef"})
    assert _outcome(expected, silently_mutated) == "diverge"


def test_membership_mutation_is_detected() -> None:
    expected = _raw_state()
    silently_mutated = _raw_state()
    silently_mutated["issues"][1]["labels"] = [{"name": "api", "color": "6f42c1"}]
    assert _outcome(expected, silently_mutated) == "diverge"


def test_malformed_extra_membership_is_a_machinery_error() -> None:
    malformed = _raw_state()
    malformed["issues"][0]["labels"].append({"name": "extra"})
    with pytest.raises(StateOracleError, match="color"):
        canonicalize_declared_state(malformed)


def test_missing_declared_issue_field_is_a_machinery_error() -> None:
    malformed = _raw_state()
    del malformed["issues"][0]["title"]
    with pytest.raises(StateOracleError, match="missing declared fields"):
        canonicalize_declared_state(malformed)


def test_api_null_body_and_lists_have_explicit_empty_meaning() -> None:
    raw = _raw_state()
    raw["issues"][0]["body"] = None
    raw["issues"][0]["labels"] = None
    raw["issues"][0]["assignees"] = None
    state = canonicalize_declared_state(raw)
    assert state.issues[0].body == ""
    assert state.issues[0].labels == ()
    assert state.issues[0].assignees == ()


def test_missing_timezone_is_a_machinery_error() -> None:
    raw = _raw_state()
    raw["issues"][0]["created_at"] = "2000-01-01T00:00:00"
    with pytest.raises(StateOracleError, match="timezone"):
        canonicalize_declared_state(raw)


def test_omitted_membership_field_is_a_machinery_error() -> None:
    raw = _raw_state()
    del raw["issues"][0]["labels"]
    with pytest.raises(StateOracleError, match="missing declared fields"):
        canonicalize_declared_state(raw)


@pytest.mark.parametrize("raw", [{}, {"issues": [], "labels": {}}, {"issues": [1], "labels": []}])
def test_invalid_state_fails_closed(raw: dict) -> None:
    with pytest.raises(StateOracleError):
        canonicalize_declared_state(raw)


def test_closed_at_must_be_parseable_and_timezone_aware() -> None:
    raw = _raw_state()
    raw["issues"][0]["state"] = "closed"
    raw["issues"][0]["closed_at"] = "now"
    with pytest.raises(StateOracleError, match="closed_at must be parseable"):
        canonicalize_declared_state(raw)
    raw["issues"][0]["closed_at"] = "2000-01-01T00:00:01"
    with pytest.raises(StateOracleError, match="closed_at must include a timezone"):
        canonicalize_declared_state(raw)
