"""Fail-closed tests for the four-way differential outcome taxonomy."""

from reality_bridge.differential import compare
from reality_bridge.projection import (
    Observation,
    error_observation,
    issue_labels_observation,
    unsupported_observation,
)


def test_equal_transport_failures_are_undetermined_not_agreement() -> None:
    ref = error_observation("get_issue", 599, {})
    sim = error_observation("get_issue", 599, {})
    assert compare(ref, sim).outcome == "undetermined"


def test_action_mismatch_precedes_matching_error_category() -> None:
    ref = error_observation("get_issue", 404, {})
    sim = error_observation("edit_issue", 404, {})
    assert compare(ref, sim).outcome == "diverge"


def test_empty_observations_are_undetermined() -> None:
    assert compare(Observation("get_issue"), Observation("get_issue")).outcome == "undetermined"


def test_explicit_unsupported_is_not_agreement() -> None:
    ref = error_observation("delete_repo", 400, {})
    sim = unsupported_observation("delete_repo")
    assert compare(ref, sim).outcome == "unsupported"


def test_empty_label_sets_are_comparable_payloads() -> None:
    ref = issue_labels_observation("remove_label", {"labels": []})
    sim = issue_labels_observation("remove_label", {"labels": []})
    assert compare(ref, sim).outcome == "agree"


def test_unknown_issue_state_is_not_coerced_to_closed() -> None:
    from reality_bridge.projection import create_issue_observation

    raw = {
        "number": 1,
        "title": "x",
        "body": "",
        "state": "future-state",
        "labels": [],
        "assignees": [],
        "closed_at": None,
    }
    ref = create_issue_observation("get_issue", {**raw, "state": "closed"})
    sim = create_issue_observation("get_issue", raw)
    assert compare(ref, sim).outcome == "diverge"


def test_timestamp_relation_is_observed_without_exact_time_equality() -> None:
    from reality_bridge.projection import create_issue_observation

    base = {
        "number": 1,
        "title": "x",
        "body": "",
        "state": "open",
        "labels": [],
        "assignees": [],
        "closed_at": None,
        "created_at": "2026-01-01T00:00:00Z",
    }
    ref = create_issue_observation("get_issue", {**base, "updated_at": "2026-01-02T00:00:00Z"})
    sim = create_issue_observation("get_issue", {**base, "updated_at": "2025-12-31T00:00:00Z"})
    assert compare(ref, sim).outcome == "diverge"
