"""Conventional stateful contract assertions over captured raw trial records.

This implementation deliberately does not import RealityBridge projection,
state oracle, or differential logic. It uses the same readback records but its
own checks of the six-operation contract. No HTTP calls occur here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


class MalformedTrace(ValueError):
    pass


def _labels(rows: Any) -> tuple[tuple[str, str], ...]:
    if rows is None:
        rows = []
    if not isinstance(rows, list):
        raise MalformedTrace("labels must be a list")
    pairs = []
    for row in rows:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("name"), str)
            or not isinstance(row.get("color"), str)
        ):
            raise MalformedTrace("label row needs name and color")
        pairs.append((row["name"], row["color"]))
    return tuple(sorted(pairs))  # duplicates survive sorting


def _time_relation(row: dict[str, Any]) -> tuple[bool, str]:
    values = []
    for field in ("created_at", "updated_at"):
        value = row.get(field)
        if not isinstance(value, str):
            raise MalformedTrace(f"issue.{field} is absent")
        try:
            instant = datetime.fromisoformat(value)
        except ValueError as exc:
            raise MalformedTrace(f"issue.{field} is invalid") from exc
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise MalformedTrace(f"issue.{field} needs timezone")
        values.append(instant)
    closed = row.get("closed_at")
    if closed is not None:
        if not isinstance(closed, str):
            raise MalformedTrace("issue.closed_at is invalid")
        try:
            closed_time = datetime.fromisoformat(closed)
        except ValueError as exc:
            raise MalformedTrace("issue.closed_at is invalid") from exc
        if closed_time.tzinfo is None or closed_time.utcoffset() is None:
            raise MalformedTrace("issue.closed_at needs timezone")
    return closed is not None, "ordered" if values[1] >= values[0] else "reversed"


def _issue(row: Any) -> tuple[Any, ...]:
    if not isinstance(row, dict):
        raise MalformedTrace("issue row must be a mapping")
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
        raise MalformedTrace(f"missing issue fields: {missing}")
    number = row.get("number")
    if isinstance(number, bool) or not isinstance(number, int):
        raise MalformedTrace("issue number must be integer")
    for field in ("title", "state"):
        if not isinstance(row.get(field), str):
            raise MalformedTrace(f"issue.{field} must be string")
    body = row.get("body")
    if body is not None and not isinstance(body, str):
        raise MalformedTrace("issue.body must be string or null")
    assignees = row.get("assignees")
    if assignees is None:
        assignees = []
    if not isinstance(assignees, list):
        raise MalformedTrace("assignees must be list")
    names = []
    for assignee in assignees:
        if not isinstance(assignee, dict) or not isinstance(assignee.get("login"), str):
            raise MalformedTrace("assignee needs login")
        names.append(assignee["login"])
    return (
        number,
        row["title"],
        body or "",
        row["state"],
        _labels(row.get("labels")),
        tuple(sorted(names)),
        *_time_relation(row),
    )


def _state(raw: Any) -> tuple[Any, ...]:
    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("issues"), list)
        or not isinstance(raw.get("labels"), list)
    ):
        raise MalformedTrace("state needs issue and label lists")
    issues = tuple(sorted(_issue(row) for row in raw["issues"]))
    labels = _labels(raw["labels"])
    return (len(raw["issues"]), len(raw["labels"]), issues, labels)


def _error(raw: Any) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, dict) or not isinstance(raw.get("status"), int):
        raise MalformedTrace("error needs integer status")
    status = raw["status"]
    if isinstance(status, bool):
        raise MalformedTrace("error status must not be Boolean")
    return {
        403: "permission_denied",
        404: "not_found",
        400: "validation_conflict",
        422: "validation_conflict",
    }.get(status, "undetermined")


def _response(op: str, raw: Any, error: Any) -> tuple[Any, ...]:
    category = _error(error)
    if category is not None:
        if category == "undetermined":
            raise MalformedTrace("transport or unexpected error status")
        return ("error", category)
    if op == "create_label":
        if not isinstance(raw, dict):
            raise MalformedTrace("label response must be mapping")
        return ("label", *_labels([raw]))
    if op in {"add_label", "remove_label"}:
        if isinstance(raw, list):
            return ("membership", _labels(raw))
        if not isinstance(raw, dict) or "labels" not in raw:
            raise MalformedTrace("membership response needs labels")
        return ("membership", _labels(raw["labels"]))
    if op in {"create_issue", "edit_issue", "get_issue"}:
        return ("issue", _issue(raw))
    raise MalformedTrace(f"operation outside six-operation grammar: {op}")


def compare_step(step: dict[str, Any]) -> dict[str, str]:
    """Compare response and complete post-action state, fail closed on bad traces."""
    try:
        action = step["action"]
        op = action["op"]
        response_ref = _response(op, step["reference_response"], step["reference_error"])
        response_sim = _response(op, step["simulator_response"], step["simulator_error"])
        state_ref = _state(step["reference_state"])
        state_sim = _state(step["simulator_state"])
    except (KeyError, TypeError, ValueError, MalformedTrace) as exc:
        return {
            "outcome": "undetermined",
            "reason": f"malformed trace: {type(exc).__name__}: {exc}",
        }
    if response_ref != response_sim:
        return {"outcome": "diverge", "reason": "response assertion differs"}
    if state_ref != state_sim:
        return {"outcome": "diverge", "reason": "complete state assertion differs"}
    return {"outcome": "agree", "reason": "ordinary response and state assertions passed"}


def compare_case(row: dict[str, Any]) -> dict[str, Any]:
    try:
        if _state(row["reference_initial"]) != _state(row["simulator_initial"]):
            return {"outcome": "undetermined", "reason": "initial states differ", "steps": []}
        if row.get("outcome") not in {"agree", "diverge", "undetermined", "unsupported"}:
            raise MalformedTrace("case is incomplete or has setup failure")
        actions = row["actions"]
        raw_steps = row["steps"]
        if (
            not isinstance(actions, list)
            or not isinstance(raw_steps, list)
            or len(actions) != len(raw_steps)
        ):
            raise MalformedTrace("captured steps do not match action inventory")
        if any(step.get("action") != action for action, step in zip(actions, raw_steps)):
            raise MalformedTrace("captured action order differs from inventory")
        steps = [compare_step(step) for step in raw_steps]
    except (KeyError, TypeError, ValueError, MalformedTrace) as exc:
        return {"outcome": "undetermined", "reason": f"malformed setup: {exc}", "steps": []}
    outcomes = {step["outcome"] for step in steps}
    outcome = (
        "undetermined"
        if "undetermined" in outcomes
        else "diverge"
        if "diverge" in outcomes
        else "agree"
    )
    return {"outcome": outcome, "reason": "complete captured case", "steps": steps}
