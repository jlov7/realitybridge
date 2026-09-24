"""Post-study fixes for the three retained evaluation divergences."""

from __future__ import annotations

from reality_bridge.emulator import Emulator
from reality_bridge.state_oracle import canonicalize_declared_state


def _candidate() -> Emulator:
    simulator = Emulator()
    simulator.reset()
    return simulator


def test_current_default_includes_verified_color_rule() -> None:
    simulator = _candidate()
    state = canonicalize_declared_state(simulator.export_declared_state())
    assert ("bug", "d73a4a") in state.labels


def test_repeat_removal_of_registered_label_is_noop() -> None:
    simulator = _candidate()
    simulator.remove_label("spec-repo", "1", "bug")
    response = simulator.remove_label("spec-repo", "1", "bug")
    assert response["labels"] == []


def test_add_unknown_label_name_is_noop() -> None:
    simulator = _candidate()
    original = simulator.get_issue("spec-repo", "1")["labels"]
    response = simulator.add_label("spec-repo", "1", "unknown-name")
    assert response["labels"] == original


def test_duplicate_name_preserves_registry_rows_and_existing_membership() -> None:
    simulator = _candidate()
    simulator.create_label("spec-repo", "bug", "445566")
    state = canonicalize_declared_state(simulator.export_declared_state())
    assert state.label_count == 4
    assert ("bug", "d73a4a") in state.labels
    assert ("bug", "445566") in state.labels
    issue_one = next(issue for issue in state.issues if issue.number == 1)
    assert issue_one.labels == (("bug", "d73a4a"),)


def test_duplicate_same_name_color_adds_both_rows_and_remove_targets_first() -> None:
    simulator = _candidate()
    first = simulator.create_label("spec-repo", "same", "112233")
    second = simulator.create_label("spec-repo", "same", "112233")
    added = simulator.add_label("spec-repo", "2", "same")
    assert [row["id"] for row in added["labels"]] == [first["id"], second["id"]]
    removed = simulator.remove_label("spec-repo", "2", "same")
    assert [row["id"] for row in removed["labels"]] == [second["id"]]


def test_current_closed_issue_timestamp_is_valid() -> None:
    simulator = _candidate()
    response = simulator.edit_issue("spec-repo", "1", state="closed")
    assert response["closed_at"] == response["updated_at"]
    canonicalize_declared_state(simulator.export_declared_state())
