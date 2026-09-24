"""Canonical oracle for the complete declared issue and label domain.

This evaluator consumes raw state exported separately by the reference and a
candidate simulator. It does not import simulator transition code. Sorting
stabilizes order while tuples preserve duplicates, and explicit cardinalities
make missing or extra rows observable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from reality_bridge.differential import Difference, agree, diverge
from reality_bridge.projection import IssueObservation, normalize_issue


class StateOracleError(ValueError):
    """Raw state did not satisfy the declared-domain observation contract."""


@dataclass(frozen=True, slots=True)
class DeclaredState:
    issue_count: int
    label_count: int
    issues: tuple[IssueObservation, ...]
    labels: tuple[tuple[str, str], ...]


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
    if closed_at is not None and not isinstance(closed_at, str):
        raise StateOracleError("issue.closed_at must be a string or null")
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


def canonicalize_declared_state(raw: dict[str, Any]) -> DeclaredState:
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
    try:
        issues = tuple(sorted((normalize_issue(item) for item in checked_issues), key=_issue_key))
    except (KeyError, TypeError, ValueError) as exc:
        raise StateOracleError(f"invalid declared issue value: {type(exc).__name__}") from exc
    labels = tuple(sorted((item["name"], item["color"]) for item in checked_labels))
    return DeclaredState(
        issue_count=len(raw_issues),
        label_count=len(raw_labels),
        issues=issues,
        labels=labels,
    )


def compare_declared_states(reference: DeclaredState, simulator: DeclaredState) -> Difference:
    """Compare full canonical states with concise difference evidence."""
    if reference == simulator:
        return agree()
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
    return diverge("declared post-state differs", "; ".join(differences))
