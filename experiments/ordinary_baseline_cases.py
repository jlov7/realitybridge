"""Frozen fresh cases for the ordinary-testing comparison; no live observations here."""

from __future__ import annotations

import hashlib
import json

from experiments.prospective_cases import ProspectiveCase
from reality_bridge.sequences import Action


def _a(op: str, *rest: str) -> Action:
    return Action(op, ("rbadmin", "spec-repo", *rest))


CASES: tuple[ProspectiveCase, ...] = (
    ProspectiveCase("N01", (_a("create_issue", "n01-a"), _a("get_issue", "3"))),
    ProspectiveCase(
        "N02", (_a("create_issue", "n02-a"), _a("edit_issue", "3", "closed"), _a("get_issue", "3"))
    ),
    ProspectiveCase(
        "N03",
        (
            _a("create_label", "n03-tag", "#a1b2c3"),
            _a("add_label", "1", "n03-tag"),
            _a("get_issue", "1"),
        ),
    ),
    ProspectiveCase(
        "N04",
        (
            _a("create_label", "n04-tag", "a1b2c3"),
            _a("add_label", "2", "n04-tag"),
            _a("remove_label", "2", "n04-tag"),
        ),
    ),
    ProspectiveCase(
        "N05",
        (_a("edit_issue", "2", "closed"), _a("get_issue", "2"), _a("edit_issue", "2", "open")),
    ),
    ProspectiveCase(
        "N06", (_a("remove_label", "2", "bug"), _a("add_label", "2", "bug"), _a("get_issue", "2"))
    ),
    ProspectiveCase(
        "N07", (_a("create_issue", "n07-a"), _a("create_issue", "n07-b"), _a("get_issue", "3"))
    ),
    ProspectiveCase("N08", (_a("get_issue", "917"), _a("create_issue", "n08-a"))),
    ProspectiveCase(
        "N09", (_a("create_label", "n09-tag", "334455"), _a("create_label", "n09-tag", "334455"))
    ),
    ProspectiveCase(
        "N10", (_a("add_label", "1", "ui"), _a("remove_label", "1", "ui"), _a("get_issue", "1"))
    ),
    ProspectiveCase("N11", (_a("edit_issue", "918", "open"), _a("get_issue", "2"))),
    ProspectiveCase(
        "N12",
        (
            _a("create_label", "n12-tag", "#eeeeee"),
            _a("add_label", "2", "n12-tag"),
            _a("add_label", "2", "n12-tag"),
        ),
    ),
)


def case_hash() -> str:
    payload = [case.as_dict() for case in CASES]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
