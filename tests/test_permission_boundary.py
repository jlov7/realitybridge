"""Planted-defect tests: permission boundary and error taxonomy.

A simulator that blurs error categories hides exactly the mismatches this
project exists to find. A 403 where the reference produced a 404 is a
divergence, never an 'error' bucket. These are method tests validating the
instrument, not empirical claims about Gitea.
"""

from __future__ import annotations

import pytest

from reality_bridge.differential import agree, compare
from reality_bridge.projection import create_issue_observation, error_observation

ACTION = "edit_issue"


def test_permission_denied_is_distinct_from_not_found() -> None:
    """403 != 404. A simulator returning not-found for a permission failure diverges."""
    ref = error_observation(ACTION, 403, {"message": "no permission"})
    sim = error_observation(ACTION, 404, {"message": "not found"})
    result = compare(ref, sim)
    assert result.outcome == "diverge", result
    detail = result.reason + " " + result.evidence
    assert "permission_denied" in detail and "not_found" in detail


def test_validation_conflict_is_distinct_from_transport_uncertainty() -> None:
    ref = error_observation(ACTION, 422, {"message": "bad state transition"})
    sim = error_observation(ACTION, 500, {"message": "simulator crashed"})
    assert ref.error == "validation_conflict"
    assert sim.error == "transport_uncertain"
    result = compare(ref, sim)
    assert result.outcome == "undetermined", result


def test_matching_error_category_agrees() -> None:
    ref = error_observation(ACTION, 403, {"message": "denied"})
    sim = error_observation(ACTION, 403, {"message": "denied differently"})
    assert compare(ref, sim) == agree()  # category is the semantics; message text is not


def test_error_never_merges_with_success() -> None:
    """An error and a successful result can never agree."""
    ref = error_observation(ACTION, 403, {})
    sim = create_issue_observation(
        ACTION, {"number": 1, "title": "visible success", "body": "", "state": "open"}
    )
    result = compare(ref, sim)
    assert result.outcome == "diverge", result
    assert result.outcome != "agree"


@pytest.mark.parametrize(
    ("ref_status", "sim_status"),
    [(403, 404), (404, 403), (422, 403), (403, 422), (404, 422), (422, 404)],
)
def test_all_error_category_pairings_diverge(ref_status: int, sim_status: int) -> None:
    """Every distinct-category pairing must diverge; none may collapse."""
    ref = error_observation(ACTION, ref_status, {})
    sim = error_observation(ACTION, sim_status, {})
    result = compare(ref, sim)
    assert result.outcome == "diverge", f"{ref_status} vs {sim_status} collapsed"


def test_same_category_always_agrees() -> None:
    for status in (403, 404, 422):
        ref = error_observation(ACTION, status, {})
        sim = error_observation(ACTION, status, {})
        assert compare(ref, sim) == agree()
