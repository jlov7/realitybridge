"""Canonical oracle for the complete declared issue and label domain.

This evaluator consumes raw state exported separately by the reference and a
candidate simulator. It does not import simulator transition code. Sorting
stabilizes order while tuples preserve duplicates, and explicit cardinalities
make missing or extra rows observable.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from reality_bridge.differential import Difference, agree, diverge, undetermined
from reality_bridge.projection import IssueObservation, normalize_issue


class StateOracleError(ValueError):
    """Raw state did not satisfy the declared-domain observation contract."""


@dataclass(frozen=True, slots=True)
class DeclaredState:
    issue_count: int
    label_count: int
    issues: tuple[IssueObservation, ...]
    labels: tuple[tuple[str, str], ...]
    logical_memberships: tuple[tuple[int, tuple[str, ...]], ...] | None = None


@dataclass(slots=True)
class LabelPairing:
    """Pair row IDs from seed semantics and subsequent paired create responses."""

    reference_ids: dict[int, str]
    simulator_ids: dict[int, str]
    next_created: int = 0
    seen_reference_ids: set[int] = field(default_factory=set)
    seen_simulator_ids: set[int] = field(default_factory=set)

    @classmethod
    def from_initial(cls, reference: dict[str, Any], simulator: dict[str, Any]) -> LabelPairing:
        left: dict[tuple[str, str], list[int]] = {}
        right: dict[tuple[str, str], list[int]] = {}
        for raw, target in ((reference, left), (simulator, right)):
            for row in raw.get("labels", []):
                if isinstance(row, dict) and "id" in row:
                    if not _valid_row_id(row["id"]):
                        raise StateOracleError("seed label id must be a positive integer")
                    name = row.get("name")
                    color = row.get("color")
                    if not isinstance(name, str) or not isinstance(color, str):
                        raise StateOracleError("seed label name and color must be strings")
                    target.setdefault((name, color), []).append(row["id"])
        ref_ids: dict[int, str] = {}
        sim_ids: dict[int, str] = {}
        for signature in left.keys() & right.keys():
            if len(left[signature]) == len(right[signature]) == 1:
                token = _unique_token(signature)
                ref_ids[left[signature][0]] = token
                sim_ids[right[signature][0]] = token
        all_left = [identifier for rows in left.values() for identifier in rows]
        all_right = [identifier for rows in right.values() for identifier in rows]
        if len(all_left) != len(set(all_left)) or len(all_right) != len(set(all_right)):
            raise StateOracleError("seed registry reuses a label id")
        return cls(ref_ids, sim_ids, 0, set(all_left), set(all_right))

    def note_creation(self, reference: dict[str, Any] | None, simulator: dict[str, Any] | None) -> None:
        """Bind a logical row only when both paired creations returned IDs."""
        self.next_created += 1
        if not isinstance(reference, dict) or not isinstance(simulator, dict):
            return
        left = reference.get("id")
        right = simulator.get("id")
        if left is None or right is None:
            return  # legacy source has no paired identity; duplicates stay undetermined
        if not _valid_row_id(left) or not _valid_row_id(right):
            raise StateOracleError("created label id must be a positive integer")
        if left in self.seen_reference_ids or right in self.seen_simulator_ids:
            raise StateOracleError("created label id reuses a paired row")
        self.seen_reference_ids.add(left)
        self.seen_simulator_ids.add(right)
        if reference.get("name") != simulator.get("name") or reference.get("color") != simulator.get("color"):
            return
        token = json.dumps(["create", self.next_created], separators=(",", ":"))
        self.reference_ids[left] = token
        self.simulator_ids[right] = token


def _valid_row_id(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _unique_token(signature: tuple[str, str]) -> str:
    return json.dumps(["unique", *signature], separators=(",", ":"))


def _issue_key(issue: IssueObservation) -> tuple[object, ...]:
    return (
        issue.number,
        issue.title,
        issue.body,
        issue.state,
        issue.labels,
        issue.assignees,
        issue.closed,
        issue.temporal_relation,
    )


def _required_str(row: dict[str, Any], key: str, row_kind: str) -> str:
    if key not in row or not isinstance(row[key], str):
        raise StateOracleError(f"{row_kind}.{key} must be a string")
    return row[key]


def _validate_label(row: dict[str, Any], row_kind: str) -> dict[str, str]:
    name = _required_str(row, "name", row_kind)
    color = _required_str(row, "color", row_kind)
    if not name:
        raise StateOracleError(f"{row_kind}.name must not be empty")
    return {"name": name, "color": color}


def _validate_issue(row: dict[str, Any]) -> dict[str, Any]:
    required = {
        "number",
        "title",
        "body",
        "state",
        "closed_at",
        "created_at",
        "updated_at",
        "labels",
        "assignees",
    }
    missing = sorted(required - row.keys())
    if missing:
        raise StateOracleError(f"issue is missing declared fields: {missing}")
    number = row["number"]
    if isinstance(number, bool) or not isinstance(number, int):
        raise StateOracleError("issue.number must be an integer")
    title = _required_str(row, "title", "issue")
    state = _required_str(row, "state", "issue")
    if not state:
        raise StateOracleError("issue.state must not be empty")
    body = row["body"]
    if body is not None and not isinstance(body, str):
        raise StateOracleError("issue.body must be a string or null")
    closed_at = row["closed_at"]
    if closed_at is not None:
        if not isinstance(closed_at, str) or not closed_at:
            raise StateOracleError("issue.closed_at must be a nonempty timestamp string or null")
        try:
            parsed_closed = datetime.fromisoformat(closed_at)
        except ValueError as exc:
            raise StateOracleError("issue.closed_at must be parseable") from exc
        if parsed_closed.tzinfo is None or parsed_closed.utcoffset() is None:
            raise StateOracleError("issue.closed_at must include a timezone offset")
    for key in ("created_at", "updated_at"):
        value = row[key]
        if not isinstance(value, str) or not value:
            raise StateOracleError(f"issue.{key} must be a nonempty timestamp string")
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise StateOracleError(f"issue.{key} must be parseable") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise StateOracleError(f"issue.{key} must include a timezone offset")

    labels = row["labels"]
    if labels is None:
        labels = []
    if not isinstance(labels, list):
        raise StateOracleError("issue.labels must be a list or null")
    if any(not isinstance(item, dict) for item in labels):
        raise StateOracleError("every issue.labels entry must be a mapping")
    checked_labels = [
        _validate_label(item, "issue.labels entry") for item in labels if isinstance(item, dict)
    ]

    assignees = row["assignees"]
    if assignees is None:
        assignees = []
    if not isinstance(assignees, list):
        raise StateOracleError("issue.assignees must be a list or null")
    if any(not isinstance(item, dict) for item in assignees):
        raise StateOracleError("every issue.assignees entry must be a mapping")
    checked_assignees = []
    for item in assignees:
        login = _required_str(item, "login", "issue.assignees entry")
        if not login:
            raise StateOracleError("issue.assignees entry.login must not be empty")
        checked_assignees.append({"login": login})

    return {
        "number": number,
        "title": title,
        "body": body or "",
        "state": state,
        "closed_at": closed_at,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "labels": checked_labels,
        "assignees": checked_assignees,
    }


def validate_issue_response(row: dict[str, Any]) -> dict[str, Any]:
    """Validate declared issue fields before response projection can discard any."""
    return _validate_issue(row)


def canonicalize_declared_state(
    raw: dict[str, Any], logical_ids: dict[int, str] | None = None
) -> DeclaredState:
    """Canonicalize all declared issue, label, and membership state."""
    if not isinstance(raw, dict):
        raise StateOracleError("state must be a mapping")
    raw_issues = raw.get("issues")
    raw_labels = raw.get("labels")
    if not isinstance(raw_issues, list) or not isinstance(raw_labels, list):
        raise StateOracleError("state must contain issue and label lists")
    if any(not isinstance(item, dict) for item in raw_issues):
        raise StateOracleError("every issue row must be a mapping")
    if any(not isinstance(item, dict) for item in raw_labels):
        raise StateOracleError("every label row must be a mapping")

    checked_issues = [_validate_issue(item) for item in raw_issues if isinstance(item, dict)]
    checked_labels = [
        _validate_label(item, "label") for item in raw_labels if isinstance(item, dict)
    ]
    registry_ids: dict[int, tuple[str, str]] = {}
    for row in raw_labels:
        if "id" in row:
            raw_id = row["id"]
            if not _valid_row_id(raw_id) or raw_id in registry_ids:
                raise StateOracleError("registry label id must be positive and unique")
            registry_ids[raw_id] = (row["name"], row["color"])
    try:
        issues = tuple(sorted((normalize_issue(item) for item in checked_issues), key=_issue_key))
    except (KeyError, TypeError, ValueError) as exc:
        raise StateOracleError(f"invalid declared issue value: {type(exc).__name__}") from exc
    labels = tuple(sorted((item["name"], item["color"]) for item in checked_labels))
    multiplicity: dict[tuple[str, str], int] = {}
    for label in checked_labels:
        key = (label["name"], label["color"])
        multiplicity[key] = multiplicity.get(key, 0) + 1
    memberships: list[tuple[int, tuple[str, ...]]] = []
    unresolved = False
    for raw_issue in raw_issues:
        tokens: list[str] = []
        for member in raw_issue["labels"] or []:
            key = (member["name"], member["color"])
            raw_id = member.get("id")
            if "id" in member and (not _valid_row_id(raw_id) or registry_ids.get(raw_id) != key):
                raise StateOracleError("issue membership id does not match a registry row")
            if logical_ids is not None and isinstance(raw_id, int) and raw_id in logical_ids:
                tokens.append(logical_ids[raw_id])
            elif multiplicity.get(key, 0) == 1:
                tokens.append(_unique_token(key))
            else:
                unresolved = True
        memberships.append((raw_issue["number"], tuple(sorted(tokens))))
    return DeclaredState(
        issue_count=len(raw_issues),
        label_count=len(raw_labels),
        issues=issues,
        labels=labels,
        logical_memberships=None if unresolved else tuple(sorted(memberships)),
    )


def compare_declared_states(reference: DeclaredState, simulator: DeclaredState) -> Difference:
    """Compare full canonical states with concise difference evidence."""
    differences: list[str] = []
    if reference.issue_count != simulator.issue_count:
        differences.append(f"issue_count: ref={reference.issue_count} sim={simulator.issue_count}")
    if reference.label_count != simulator.label_count:
        differences.append(f"label_count: ref={reference.label_count} sim={simulator.label_count}")
    if reference.labels != simulator.labels:
        differences.append(f"labels: ref={reference.labels!r} sim={simulator.labels!r}")
    if reference.issues != simulator.issues:
        ref_rows = [asdict(item) for item in reference.issues]
        sim_rows = [asdict(item) for item in simulator.issues]
        differences.append(f"issues: ref={ref_rows!r} sim={sim_rows!r}")
    if differences:
        return diverge("declared post-state differs", "; ".join(differences))
    if reference.logical_memberships is None or simulator.logical_memberships is None:
        return undetermined("duplicate-row membership identity has no paired creation evidence")
    if reference.logical_memberships != simulator.logical_memberships:
        return diverge(
            "paired label-row membership differs",
            f"ref={reference.logical_memberships!r} sim={simulator.logical_memberships!r}",
        )
    return agree()
