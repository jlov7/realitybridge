"""Normalization-mutation guard — the test this project must not live without.

The naive failure mode of this whole project is a projection that normalizes
the signal away. The guard is expressed as the direct contract:

    the SAFE projection must detect known divergences (title, state, wrong
    object). If a maintainer over-normalizes `normalize_issue` (drops title,
    drops state, merges everything to number), THESE TESTS FAIL — so an
    over-normalizing mutation is caught by the test suite, not by inspection.

These are method tests on the instrument, not empirical claims about Gitea.
"""

from __future__ import annotations

from pathlib import Path

from reality_bridge.differential import agree, compare
from reality_bridge.projection import create_issue_observation


def _issue(number: int, title: str, body: str = "", state: str = "open") -> dict:
    return {
        "number": number,
        "title": title,
        "body": body,
        "state": state,
        "closed_at": None,
        "labels": [],
        "assignees": [],
    }


def test_title_change_is_detected_by_safe_projection() -> None:
    """Dropping `title` from the projection would blind the instrument."""
    ref = create_issue_observation("get_issue", _issue(4, "spec-alpha"))
    sim = create_issue_observation("get_issue", _issue(4, "spec-beta"))
    result = compare(ref, sim)
    assert result.outcome == "diverge"
    assert "title" in result.reason + result.evidence


def test_state_change_is_detected_by_safe_projection() -> None:
    """Dropping `state` from the projection would blind the instrument."""
    ref = create_issue_observation("get_issue", _issue(2, "spec", state="open"))
    sim = create_issue_observation("get_issue", _issue(2, "spec", state="closed"))
    result = compare(ref, sim)
    assert result.outcome == "diverge"
    assert "state" in result.reason + result.evidence


def test_wrong_object_survives_projection() -> None:
    """Wrong-object detection must not depend on over-normalized fields."""
    ref = create_issue_observation("get_issue", _issue(11, "left-issue"))
    sim = create_issue_observation("get_issue", _issue(11, "other-issue"))
    result = compare(ref, sim)
    assert result.outcome == "diverge"
    assert "title" in result.reason + result.evidence or "number" in result.reason + result.evidence


def test_body_change_is_detected() -> None:
    ref = create_issue_observation("get_issue", _issue(12, "spec", body="v1"))
    sim = create_issue_observation("get_issue", _issue(12, "spec", body="v2"))
    result = compare(ref, sim)
    assert result.outcome == "diverge"
    assert "body" in result.reason + result.evidence


def test_identical_observations_agree() -> None:
    ref = create_issue_observation("get_issue", _issue(4, "spec-alpha", body="b"))
    sim = create_issue_observation("get_issue", _issue(4, "spec-alpha", body="b"))
    assert compare(ref, sim) == agree()


def test_exclusions_are_documented() -> None:
    """The projection's exclusions must be recorded in the contract file."""
    contract = Path(__file__).resolve().parents[1] / "contracts" / "observation.yaml"
    text = contract.read_text()
    assert "Exclusions" in text, "projection exclusions must be documented in observation.yaml"


def test_excluded_field_url_does_not_diverge() -> None:
    """The documented exclusions (url/html_url/ref) must not leak into comparison."""
    ref_issue = _issue(6, "spec", "body")
    sim_issue = _issue(6, "spec", "body")
    ref_issue["url"] = "/issues/6"
    sim_issue["url"] = "/issues/6/changed"
    ref = create_issue_observation("get_issue", ref_issue)
    sim = create_issue_observation("get_issue", sim_issue)
    assert compare(ref, sim).outcome == "agree"
