"""Recompute frozen A1 comparisons from captured raw rows in an extracted tree."""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from experiments.ordinary_baseline import compare_case
from experiments.ordinary_baseline_cases import CASES, case_hash
from experiments.ordinary_baseline_study import _instrument_case
from experiments.research_completion import _family_outcome
from reality_bridge.prospective_comparison import compare_responses
from reality_bridge.state_oracle import canonicalize_declared_state, compare_declared_states


class StoredError:
    def __init__(self, raw: dict[str, Any], simulator: bool) -> None:
        self.status = raw["status"]
        self.body = raw.get("body", raw.get("message"))
        self.message = raw.get("message", "") if simulator else ""

    def __str__(self) -> str:
        return self.message or str(self.body)


def _error(raw: dict[str, Any] | None, simulator: bool) -> StoredError | None:
    return None if raw is None else StoredError(raw, simulator)


def _state(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return asdict(
        compare_declared_states(
            canonicalize_declared_state(left), canonicalize_declared_state(right)
        )
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def check(first_path: Path, amended_path: Path) -> dict[str, Any]:
    first = json.loads(first_path.read_text())
    amended = json.loads(amended_path.read_text())
    require(
        first["status"] == "setup_failure" and first["requests"] == 17,
        "first attempt status or request count",
    )
    require(len(first["rows"]) == 1, "first attempt row count")
    failed = first["rows"][0]["raw"]
    require(failed["case_id"] == "N01" and failed["steps"] == [], "first attempt action inventory")
    require(failed["outcome"] == "setup_failure", "first attempt outcome")
    require(
        _state(failed["reference_initial"], failed["simulator_initial"])
        == failed["initial_comparison"],
        "first attempt initial state comparison",
    )
    require(
        amended["status"] == "complete" and amended["requests"] <= amended["hard_cap"] == 320,
        "amended completion or budget",
    )
    require(amended["case_hash"] == case_hash(), "amended case hash")
    require(amended["unstarted_cases"] == [], "amended unstarted cases")
    require(len(amended["rows"]) == len(CASES) == 12, "amended case count")
    initial_requests = amended["requests"] - sum(
        row["raw"]["request_cost"] for row in amended["rows"]
    )
    require(initial_requests == 7, "amended initial request count")
    cumulative = initial_requests
    outcomes = {"ordinary": Counter(), "instrument": Counter()}
    for case, entry in zip(CASES, amended["rows"], strict=True):
        raw = entry["raw"]
        require(raw["case_id"] == case.case_id, "case ID")
        require(
            raw["actions"] == [action.as_dict() for action in case.actions], "case action inventory"
        )
        require(len(raw["steps"]) == len(case.actions), "case step count")
        require(
            _state(raw["reference_initial"], raw["simulator_initial"]) == raw["initial_comparison"],
            "case initial state comparison",
        )
        require(raw["initial_comparison"]["outcome"] == "agree", "case initial state outcome")
        for action, step in zip(case.actions, raw["steps"], strict=True):
            require(step["action"] == action.as_dict(), "step action inventory")
            expected_response = asdict(
                compare_responses(
                    action.op,
                    step["reference_response"],
                    _error(step["reference_error"], False),
                    step["simulator_response"],
                    _error(step["simulator_error"], True),
                )
            )
            require(expected_response == step["response"], f"{case.case_id} {action.op} response")
            require(
                _state(step["reference_state"], step["simulator_state"]) == step["state"],
                f"{case.case_id} {action.op} state",
            )
        require(raw["outcome"] == _family_outcome(raw["steps"]), "raw case outcome")
        require(entry["ordinary"] == compare_case(raw), "ordinary case comparison")
        require(entry["instrument"] == _instrument_case(raw), "instrument case comparison")
        cumulative += raw["request_cost"]
        require(raw["completed_at_request"] == cumulative, "request ledger")
        for method, counts in outcomes.items():
            counts[entry[method]["outcome"]] += 1
    require(cumulative == amended["requests"], "amended total request ledger")
    require(
        {key: dict(counts) for key, counts in outcomes.items()} == amended["case_outcomes"],
        "amended outcome totals",
    )
    return {
        "status": "reproduced_from_raw_rows",
        "case_count": len(CASES),
        "action_count": sum(len(case.actions) for case in CASES),
        "requests": amended["requests"],
        "first_attempt": {
            "status": first["status"],
            "requests": first["requests"],
            "actions_observed": 0,
        },
        "case_outcomes": {key: dict(value) for key, value in outcomes.items()},
        "raw_response_state_recomputed": True,
        "ordinary_comparison_recomputed": True,
        "instrument_case_outcomes_recomputed": True,
    }


if __name__ == "__main__":
    print(json.dumps(check(Path(sys.argv[1]), Path(sys.argv[2])), indent=2, sort_keys=True))
