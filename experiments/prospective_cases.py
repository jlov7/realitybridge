"""Prospective 2026-09-22 cases frozen before reference outcomes were observed.

These cases instantiate the table in
``docs/research-completion-2026-09-22/PROTOCOL.md``.  Development cases are
available to discovery and repair. Evaluation cases are loaded only after
discovery and proposals are frozen.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from reality_bridge.sequences import Action


@dataclass(frozen=True, slots=True)
class ProspectiveCase:
    case_id: str
    actions: tuple[Action, ...]

    def as_dict(self) -> dict[str, object]:
        return {"case_id": self.case_id, "actions": [action.as_dict() for action in self.actions]}


def _a(op: str, *rest: str) -> Action:
    return Action(op, ("rbadmin", "spec-repo", *rest))


DEV_CASES: tuple[ProspectiveCase, ...] = (
    ProspectiveCase("D01", (_a("create_issue", "p2-dev-create"), _a("get_issue", "3"))),
    ProspectiveCase("D02", (_a("edit_issue", "2", "closed"), _a("get_issue", "2"))),
    ProspectiveCase("D03", (_a("add_label", "2", "ui"), _a("get_issue", "2"))),
    ProspectiveCase("D04", (_a("remove_label", "1", "bug"), _a("get_issue", "1"))),
    ProspectiveCase("D05", (_a("create_label", "p2-dev-bare", "112233"),)),
    ProspectiveCase("D06", (_a("create_label", "bug", "445566"),)),
    ProspectiveCase("D07", (_a("create_issue", ""),)),
    ProspectiveCase("D08", (_a("create_label", "", "123456"),)),
    ProspectiveCase("D09", (_a("get_issue", "801"),)),
    ProspectiveCase("D10", (_a("edit_issue", "802", "closed"),)),
    ProspectiveCase("D11", (_a("add_label", "1", "p2-dev-missing"),)),
    ProspectiveCase("D12", (_a("remove_label", "2", "api"),)),
    ProspectiveCase("D13", (_a("add_label", "1", "bug"), _a("get_issue", "1"))),
    ProspectiveCase(
        "D14",
        (
            _a("create_label", "p2-dev-attach", "#778899"),
            _a("add_label", "2", "p2-dev-attach"),
            _a("get_issue", "2"),
        ),
    ),
)

EVAL_CASES: tuple[ProspectiveCase, ...] = (
    ProspectiveCase(
        "E01",
        (
            _a("create_issue", "p2-eval-a"),
            _a("create_issue", "p2-eval-b"),
            _a("get_issue", "4"),
        ),
    ),
    ProspectiveCase(
        "E02",
        (
            _a("edit_issue", "2", "closed"),
            _a("edit_issue", "2", "open"),
            _a("get_issue", "2"),
        ),
    ),
    ProspectiveCase(
        "E03",
        (
            _a("add_label", "2", "bug"),
            _a("add_label", "2", "api"),
            _a("get_issue", "2"),
        ),
    ),
    ProspectiveCase(
        "E04",
        (
            _a("remove_label", "1", "bug"),
            _a("remove_label", "1", "bug"),
            _a("get_issue", "1"),
        ),
    ),
    ProspectiveCase("E05", (_a("create_label", "p2-eval-hash", "#abcdef"),)),
    ProspectiveCase(
        "E06",
        (
            _a("create_label", "p2-eval-dupe", "111111"),
            _a("create_label", "p2-eval-dupe", "222222"),
        ),
    ),
    ProspectiveCase("E07", (_a("create_issue", ""), _a("get_issue", "2"))),
    ProspectiveCase(
        "E08",
        (
            _a("edit_issue", "1", "closed"),
            _a("edit_issue", "901", "open"),
            _a("get_issue", "1"),
        ),
    ),
    ProspectiveCase(
        "E09",
        (
            _a("edit_issue", "1", "closed"),
            _a("add_label", "1", "p2-eval-missing"),
            _a("get_issue", "1"),
        ),
    ),
    ProspectiveCase("E10", (_a("remove_label", "902", "bug"),)),
    ProspectiveCase(
        "E11",
        (
            _a("create_label", "p2-eval-twice", "778899"),
            _a("add_label", "2", "p2-eval-twice"),
            _a("add_label", "2", "p2-eval-twice"),
            _a("get_issue", "2"),
        ),
    ),
    ProspectiveCase(
        "E12",
        (
            _a("edit_issue", "1", "closed"),
            _a("remove_label", "1", "bug"),
            _a("edit_issue", "1", "open"),
            _a("get_issue", "1"),
        ),
    ),
    ProspectiveCase(
        "E13",
        (
            _a("create_issue", "p2-eval-created"),
            _a("add_label", "3", "ui"),
            _a("get_issue", "3"),
        ),
    ),
    ProspectiveCase(
        "E14",
        (
            _a("create_label", "p2-eval-l1", "102030"),
            _a("create_label", "p2-eval-l2", "405060"),
            _a("add_label", "2", "p2-eval-l2"),
            _a("get_issue", "2"),
        ),
    ),
    ProspectiveCase("E15", (_a("get_issue", "903"), _a("get_issue", "1"))),
    ProspectiveCase(
        "E16",
        (
            _a("create_label", "", ""),
            _a("create_label", "p2-eval-after-invalid", "334455"),
        ),
    ),
)

TARGETED_ORDER: tuple[str, ...] = (
    "D06",
    "D12",
    "D11",
    "D08",
    "D07",
    "D10",
    "D09",
    "D13",
    "D14",
    "D04",
    "D03",
    "D02",
    "D05",
    "D01",
)
RANDOM_ORDER_SEEDS: tuple[int, ...] = (20260922, 20260923, 20260924)


def case_hash() -> str:
    payload = [case.as_dict() for case in (*DEV_CASES, *EVAL_CASES)]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def cases_by_id(cases: tuple[ProspectiveCase, ...]) -> dict[str, ProspectiveCase]:
    return {case.case_id: case for case in cases}
