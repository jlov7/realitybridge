"""Planted-defect tests: wrong-object detection.

METHOD tests, not empirical claims. These validate the instrument: a defect is
planted in a raw response (as a buggy simulator would produce it) and the
projection + differential must detect it.

Raw response shapes mirror the pinned reference's actual `/swagger.v1.json`
Issue object (verified in Milestone A): typed issue dicts with the fields the
projection reads.
"""

from __future__ import annotations

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
        "id": number * 1000,  # literal id: deliberately ignored by the projection
        "url": f"/unused/{number}",
    }


# -- wrong object at the same position must be detected -------------------------


def test_wrong_object_with_matching_id_is_detected() -> None:
    """A simulator returning object B when asked for object A must diverge."""
    ref = create_issue_observation("get_issue", _issue(7, "spec-issue-one"))
    sim = create_issue_observation("get_issue", _issue(7, "spec-issue-two"))
    result = compare(ref, sim)
    assert result.outcome == "diverge", result


def test_wrong_object_does_not_rely_on_literal_id() -> None:
    """The id is ignored by design; semantic fields catch the wrong object."""
    ref = create_issue_observation("get_issue", _issue(9, "alpha", "a-body"))
    sim = create_issue_observation("get_issue", _issue(9, "alpha", "BODY-CHANGED"))
    result = compare(ref, sim)
    assert result.outcome == "diverge", result


def test_state_mismatch_is_detected() -> None:
    """The reference closed an issue; the simulator says it is still open."""
    ref = create_issue_observation("get_issue", _issue(3, "spec", state="closed"))
    sim = create_issue_observation("get_issue", _issue(3, "spec", state="open"))
    result = compare(ref, sim)
    assert result.outcome == "diverge", result


def test_identical_projection_agrees() -> None:
    ref = create_issue_observation("get_issue", _issue(1, "spec", "same"))
    sim = create_issue_observation("get_issue", _issue(1, "spec", "same"))
    assert compare(ref, sim) == agree()


# -- label set ordering is normalized; membership is preserved -------------------


def test_label_set_order_is_normalized_but_membership_matters() -> None:
    def labeled(body: str) -> dict:
        issue = _issue(5, "spec", body)
        issue["labels"] = [
            {"name": "bug", "color": "#d73a4a"},
            {"name": "api", "color": "#6f42c1"},
        ]
        return issue

    ref = create_issue_observation("add_label", labeled("x"))
    ref_as_returned = create_issue_observation("add_label", labeled("x"))
    assert compare(ref, ref_as_returned) == agree()

    missing = labeled("x")
    missing["labels"] = [{"name": "bug", "color": "#d73a4a"}]  # api label vanished
    result = compare(ref, create_issue_observation("add_label", missing))
    assert result.outcome == "diverge", result
