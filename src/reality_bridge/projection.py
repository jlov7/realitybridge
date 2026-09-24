"""Observation projection for differential comparison.

Map a raw API exchange onto a comparison-stable `Observation` per
`contracts/observation.yaml`. The projection is where naive implementations die:
normalizing away the signal is the primary technical risk of the whole project,
so the projection is deliberately minimal and every exclusion is documented in
the contract file.

The evaluator MUST NOT import simulator transition logic. This module reads the
reference API shape only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

Category = Literal["permission_denied", "not_found", "validation_conflict", "transport_uncertain"]


@dataclass(frozen=True, slots=True)
class IssueObservation:
    number: int
    title: str
    body: str
    state: str
    labels: tuple[tuple[str, str], ...] = ()  # sorted (name, color) pairs
    assignees: tuple[str, ...] = ()
    closed: bool = False
    temporal_relation: str = "not_observed"


@dataclass(frozen=True, slots=True)
class Observation:
    """The normalized 'what happened' for one step."""

    action: str
    error: Category | None = None
    unsupported_operation: str | None = None
    issue: IssueObservation | None = None
    label: tuple[str, str] | None = None  # (name, color)
    label_set: tuple[tuple[str, str], ...] | None = None
    detail: str = ""


def _state(issue: dict[str, Any]) -> str:
    """Keep an unknown state observable instead of coercing it to ``closed``."""
    return str(issue.get("state", "missing")).lower()


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _temporal_relation(issue: dict[str, Any]) -> str:
    """Project timestamp ordering without comparing environment-specific values."""
    created_raw = issue.get("created_at")
    updated_raw = issue.get("updated_at")
    if created_raw is None and updated_raw is None:
        return "not_observed"
    created = _parse_time(created_raw)
    updated = _parse_time(updated_raw)
    if created is None or updated is None:
        return "invalid_or_incomplete"
    try:
        return "updated_not_before_created" if updated >= created else "updated_before_created"
    except TypeError:
        # Naive and timezone-aware datetimes are individually parseable but not
        # comparable. Keep the malformed relation observable and fail closed.
        return "invalid_or_incomplete"


def normalize_issue(raw: dict[str, Any]) -> IssueObservation:
    """Map a raw Issue object onto the logical projection.

    Identifiers: `id` is deliberately NOT in the projection (see contract §
    Identifier mapping). `number` is kept because it is the human-facing
    handle and is stable across trials. A wrong-object response is detected by
    semantic fields (title/number/labels), never by id.
    """
    labels = [
        (str(l["name"]), str(l.get("color", "")))
        for l in (raw.get("labels") or [])
        if isinstance(l, dict)
    ]
    labels.sort()
    assignees = sorted(
        str(a.get("login", "")) for a in (raw.get("assignees") or []) if isinstance(a, dict)
    )
    return IssueObservation(
        number=int(raw["number"]),
        title=str(raw.get("title", "")),
        body=str(raw.get("body", "")),
        state=_state(raw),
        labels=tuple(labels),
        assignees=tuple(assignees),
        closed=raw.get("closed_at") is not None,
        temporal_relation=_temporal_relation(raw),
    )


def project_error(status: int, body: Any) -> tuple[Category, str]:
    """Classify an error response into the contract's distinct taxonomy."""
    message = ""
    if isinstance(body, dict):
        message = str(body.get("message", ""))
    if status == 403:
        return "permission_denied", message
    if status == 404:
        return "not_found", message
    if status == 422 or status == 400:
        return "validation_conflict", message
    return "transport_uncertain", f"unexpected status {status}"


def create_issue_observation(action: str, raw: dict[str, Any]) -> Observation:
    return Observation(action=action, issue=normalize_issue(raw))


def issue_labels_observation(action: str, raw_issue: dict[str, Any]) -> Observation:
    """For add_label / remove_label: what matters is the resulting label set."""
    labels = [
        (str(l["name"]), str(l.get("color", "")))
        for l in raw_issue.get("labels", [])
        if isinstance(l, dict)
    ]
    labels.sort()
    return Observation(action=action, label_set=tuple(labels))


def label_observation(action: str, raw_label: dict[str, Any]) -> Observation:
    return Observation(
        action=action, label=(str(raw_label.get("name", "")), str(raw_label.get("color", "")))
    )


def error_observation(action: str, status: int, body: Any) -> Observation:
    category, message = project_error(status, body)
    return Observation(action=action, error=category, detail=message[:100])


def unsupported_observation(action: str) -> Observation:
    """Represent an explicit simulator coverage gap as its own outcome."""
    return Observation(action=action, unsupported_operation=action)
