"""Strict response comparison for the prospective study.

Malformed declared response fields are machinery uncertainty, never agreement.
The full-state oracle independently checks effects after each action.
"""

from __future__ import annotations

from typing import Any

from reality_bridge.differential import Difference, compare, undetermined
from reality_bridge.projection import (
    Observation,
    create_issue_observation,
    error_observation,
    issue_labels_observation,
    label_observation,
    unsupported_observation,
)
from reality_bridge.state_oracle import StateOracleError, validate_issue_response


def _labels(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise StateOracleError("response.labels must be a list or null")
    result = []
    for row in value:
        if not isinstance(row, dict):
            raise StateOracleError("response.labels entry must be a mapping")
        if not isinstance(row.get("name"), str) or not isinstance(row.get("color"), str):
            raise StateOracleError("response.labels entry needs name and color strings")
        result.append({"name": row["name"], "color": row["color"]})
    return result


def project_response(
    action: str, raw: Any, error: Any | None, *, simulator: bool = False
) -> Observation:
    if error is not None:
        status = error.status
        if simulator and status == 400 and str(error).startswith("unsupported op"):
            return unsupported_observation(action)
        body = getattr(error, "body", str(error))
        return error_observation(action, status, body)
    if action == "create_label":
        if (
            not isinstance(raw, dict)
            or not isinstance(raw.get("name"), str)
            or not isinstance(raw.get("color"), str)
        ):
            raise StateOracleError("label response needs name and color strings")
        return label_observation(action, raw)
    if action == "add_label" and isinstance(raw, list):
        return issue_labels_observation(action, {"labels": _labels(raw)})
    if action in {"add_label", "remove_label"}:
        if not isinstance(raw, dict) or "labels" not in raw:
            raise StateOracleError("membership response must contain labels")
        return issue_labels_observation(action, {"labels": _labels(raw["labels"])})
    if action in {"create_issue", "get_issue", "edit_issue"}:
        if not isinstance(raw, dict):
            raise StateOracleError("issue response must be a mapping")
        return create_issue_observation(action, validate_issue_response(raw))
    raise StateOracleError(f"undeclared action {action}")


def compare_responses(
    action: str,
    reference_raw: Any,
    reference_error: Any | None,
    simulator_raw: Any,
    simulator_error: Any | None,
) -> Difference:
    try:
        reference = project_response(action, reference_raw, reference_error)
        simulator = project_response(action, simulator_raw, simulator_error, simulator=True)
    except (StateOracleError, KeyError, TypeError, ValueError) as exc:
        return undetermined(f"malformed declared response: {type(exc).__name__}: {exc}")
    return compare(reference, simulator)
