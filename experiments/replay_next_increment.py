"""Recompute saved next-increment summaries from a history-free source export."""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from experiments.ordinary_baseline import _response, _state, compare_case
from experiments.ordinary_baseline_cases import CASES as ORDINARY_CASES
from experiments.ordinary_baseline_study import _instrument_case
from experiments.research_completion import (
    Goal,
    _family_outcome,
    goal_succeeded,
    policy_plan,
    summarize_policy,
)
from reality_bridge.prospective_comparison import compare_responses, project_response
from reality_bridge.state_oracle import (
    LabelPairing,
    canonicalize_declared_state,
    compare_declared_states,
)

EVIDENCE = ROOT / "artifacts/next-increment-2026-09-23"
HISTORICAL = ROOT / "artifacts/ordinary-baseline-2026-09-23/amended-complete.json"
PROTOCOL = ROOT / "research/next-increment-2026-09-23/STUDY-PROTOCOL.md"
A_SNAPSHOT = ROOT / "research/next-increment-2026-09-23/A-source-snapshot"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(name: str) -> dict:
    return json.loads((EVIDENCE / name).read_text())


def _check_source(manifest: dict, phase: str) -> None:
    assert _sha(PROTOCOL) == manifest["protocol_sha256"]
    for relative, expected in manifest["source_sha256"].items():
        source = ROOT / relative
        if phase == "A" and relative in {
            "src/reality_bridge/state_oracle.py",
            "tests/test_duplicate_label_identity_boundary.py",
        }:
            source = A_SNAPSHOT / relative
        assert _sha(source) == expected, f"{phase}: source mismatch {relative}"


def _check_packet() -> dict:
    freeze = _load("B-FREEZE-A2.json")
    capsule = EVIDENCE / "B-reviewer-capsule"
    _check_source(_load("B-API-FROZEN.json"), "B-API")
    assert _sha(ROOT / "experiments/prepare_blind_oracle_packet.py") == freeze["generator_sha256"]
    assert _sha(capsule / "MANIFEST.json") == freeze["reviewer_manifest_sha256"]
    assert _sha(capsule / "observation.md") == freeze["historical_contract_sha256"]["observation"]
    assert _sha(capsule / "operations.md") == freeze["historical_contract_sha256"]["operations"]
    assert _sha(capsule / "API-SCHEMA-EXCERPT.json") == freeze["api_schema_excerpt_sha256"]
    manifest = json.loads((capsule / "MANIFEST.json").read_text())
    forbidden = {
        "outcome",
        "comparison",
        "reason",
        "evidence",
        "source_case",
        "source_study",
        "recorded_instrument_outcome",
        "case_id",
        "initial_comparison",
    }

    def keys(value: object):
        if isinstance(value, dict):
            yield from value.keys()
            for item in value.values():
                yield from keys(item)
        elif isinstance(value, list):
            for item in value:
                yield from keys(item)

    assert len(manifest["cases"]) == 28
    for row in manifest["cases"]:
        path = capsule / row["path"]
        assert _sha(path) == row["sha256"]
        assert not (set(keys(json.loads(path.read_text()))) & forbidden)
    return {
        "packet_cases": len(manifest["cases"]),
        "outside_reviews": freeze["outside_classifications_received"],
    }


class _StoredError:
    def __init__(self, value: dict) -> None:
        self.status = value["status"]
        self.body = value.get("body", value.get("message", ""))

    def __str__(self) -> str:
        return str(self.body)


def _error(value: dict | None) -> _StoredError | None:
    return None if value is None else _StoredError(value)


def _recompute_trace(row: dict) -> str:
    """Rebuild the paired response and state verdicts from retained raw fields."""
    pairing = LabelPairing.from_initial(row["reference_initial"], row["simulator_initial"])
    initial = compare_declared_states(
        canonicalize_declared_state(row["reference_initial"], pairing.reference_ids),
        canonicalize_declared_state(row["simulator_initial"], pairing.simulator_ids),
    )
    assert asdict(initial) == row["initial_comparison"]
    assert initial.outcome == "agree"
    assert [step["action"] for step in row["steps"]] == row["actions"]
    for step in row["steps"]:
        action = step["action"]
        response = compare_responses(
            action["op"],
            step["reference_response"],
            _error(step["reference_error"]),
            step["simulator_response"],
            _error(step["simulator_error"]),
        )
        assert asdict(response) == step["response"]
        if action["op"] == "create_label":
            pairing.note_creation(step["reference_response"], step["simulator_response"])
        state = compare_declared_states(
            canonicalize_declared_state(step["reference_state"], pairing.reference_ids),
            canonicalize_declared_state(step["simulator_state"], pairing.simulator_ids),
        )
        assert asdict(state) == step["state"]
    outcome = _family_outcome(row["steps"])
    assert outcome == row["outcome"]
    return outcome


def _recompute_policy_backend(task: Goal, backend: dict, *, simulator: bool) -> None:
    assert backend["attempted_actions"] == len(backend["steps"])
    stop = "plan_end"
    for step in backend["steps"]:
        observation = project_response(
            step["action"]["op"],
            step["raw"],
            _error(step["error"]),
            simulator=simulator,
        )
        outcome = (
            "unsupported"
            if observation.unsupported_operation is not None
            else "undetermined"
            if observation.error == "transport_uncertain"
            else "error"
            if observation.error is not None
            else "success"
        )
        assert outcome == step["outcome"]
        canonicalize_declared_state(step["post_state"])
        if outcome != "success":
            stop = outcome
            assert step is backend["steps"][-1]
            break
    assert stop == backend["stop"]
    state = canonicalize_declared_state(backend["state"])
    success = goal_succeeded(
        task,
        state,
        tuple(step["action"] for step in backend["steps"]),
        backend["steps"],
    )
    assert backend["success"] == success
    assert backend["utility"] == (100 if success else 0) - len(backend["steps"])


def replay() -> dict:
    a = _load("A-RAW-A1.json")
    _check_source(_load("A-FROZEN-A1.json"), "A")
    assert a["manifest_sha256"] == _sha(EVIDENCE / "A-FROZEN-A1.json")
    assert a["status"] == "incomplete" and a["requests"] == 80  # preserved cap censoring
    first = a["cases"][0]
    added = next(issue for issue in first["steps"][2]["state"]["issues"] if issue["number"] == 2)[
        "labels"
    ]
    removed = next(issue for issue in first["steps"][3]["state"]["issues"] if issue["number"] == 2)[
        "labels"
    ]
    assert len(added) == 2 and len(removed) == 1
    assert removed[0]["id"] == added[1]["id"]
    b = _check_packet()
    c = _load("C-RAW.json")
    c_freeze = _load("C-FROZEN.json")
    _check_source(c_freeze, "C")
    assert c["manifest_sha256"] == _sha(EVIDENCE / "C-FROZEN.json")
    assert c["status"] == "complete" and c["shared_setup_requests"] == 7
    assert set(c["arms"]) == set(c_freeze["arms"])
    c_summary = {}
    for arm, payload in c["arms"].items():
        expected = [
            (family, case) for family in c_freeze["families"] for case in c_freeze["arms"][arm]
        ]
        assert len(payload["rows"]) == len(expected)
        assert payload["requests"] == sum(row["raw"]["request_cost"] for row in payload["rows"])
        assert payload["requests"] <= c_freeze["hard_request_cap_per_arm"]
        detections = {"ordinary": set(), "instrument": set()}
        for row, (family, case) in zip(payload["rows"], expected, strict=True):
            assert row["family"] == family
            assert row["raw"]["case_id"] == case["id"]
            assert row["raw"]["actions"] == case["actions"]
            assert compare_case(row["raw"]) == row["ordinary"]
            assert _instrument_case(row["raw"]) == row["instrument"]
            for method, found in detections.items():
                if row[method]["outcome"] == "diverge":
                    found.add(row["family"])
        c_summary[arm] = {
            "requests": payload["requests"],
            "trials": len(payload["rows"]),
            "planted_families_detected": {key: sorted(value) for key, value in detections.items()},
        }
    d = _load("D-RAW.json")
    d_freeze = _load("D-FROZEN.json")
    _check_source(d_freeze, "D")
    assert d["manifest_sha256"] == _sha(EVIDENCE / "D-FROZEN.json")
    assert d["status"] == "complete" and d["requests"] <= d_freeze["hard_request_cap"]
    assert d["requests"] == 7 + sum(
        row["request_cost"] for phase in ("selection", "evaluation") for row in d[phase]
    )
    for phase in ("selection", "evaluation"):
        expected = [
            (raw_task, policy) for raw_task in d_freeze[phase] for policy in d_freeze["policies"]
        ]
        assert len(d[phase]) == len(expected)
        for row, (raw_task, policy) in zip(d[phase], expected, strict=True):
            assert row["task"] == raw_task and row["policy"] == policy
            task = Goal(**raw_task)
            assert row["plan"] == list(policy_plan(policy, task))
            assert row["request_cost"] == row["completed_at_request"] - row["request_start"]
            for backend in ("reference", "simulator"):
                _recompute_policy_backend(task, row[backend], simulator=backend == "simulator")
    assert summarize_policy(d["selection"], d["evaluation"]) == d["summary"]
    e = _load("E-RAW.json")
    e_freeze = _load("E-FROZEN.json")
    _check_source(e_freeze, "E")
    assert e["manifest_sha256"] == _sha(EVIDENCE / "E-FROZEN.json")
    assert e["status"] == "complete" and e["requests"] <= e_freeze["hard_request_cap"]
    assert set(e["families"]) == set(e_freeze["families"])
    assert e["requests"] == 7 + sum(
        row["request_cost"]
        for family in e["families"].values()
        for phase in ("before", "after")
        for row in family[phase].values()
    )
    e_summary = {}
    for family, payload in e["families"].items():
        assert payload["worker"]["forbidden_read_denied"] and payload["worker"]["allowed_execution"]
        assert set(payload["before"]) == {"train", "known_regression", "unseen"}
        for phase in ("before", "after"):
            for split, row in payload[phase].items():
                case = e_freeze["families"][family][split]
                assert row["case_id"] == case["id"] and row["actions"] == case["actions"]
                _recompute_trace(row)
        e_summary[family] = {
            "status": payload["status"],
            "before": {key: row["outcome"] for key, row in payload["before"].items()},
            "after": {key: row["outcome"] for key, row in payload["after"].items()},
        }
    f = _load("F-RAW.json")
    f_freeze = _load("F-FROZEN.json")
    _check_source(f_freeze, "F")
    assert f["manifest_sha256"] == _sha(EVIDENCE / "F-FROZEN.json")
    assert f["status"] == "complete" and f["requests"] <= f_freeze["hard_request_cap"]
    assert f["image"].split("|")[0] == f_freeze["second_image"]
    assert f["image_after_reset"].split("|")[0] == f_freeze["second_image"]
    assert f["requests"] == 11 + sum(row["request_cost"] for row in f["rows"])
    assert [row["case_id"] for row in f["rows"]] == f_freeze["case_ids"]
    case_lookup = {case.case_id: case for case in ORDINARY_CASES}
    for row in f["rows"]:
        assert row["actions"] == [
            action.as_dict() for action in case_lookup[row["case_id"]].actions
        ]
        _recompute_trace(row)
    assert f["api_mapping"]["version_response"] == {"version": "1.24.6"}
    assert f["api_mapping_after_reset"]["version_response"] == {"version": "1.24.6"}
    assert not f["api_mapping"]["missing"] and not f["api_mapping_after_reset"]["missing"]
    old = {row["raw"]["case_id"]: row["raw"] for row in json.loads(HISTORICAL.read_text())["rows"]}
    deltas = {}
    for row in f["rows"]:
        prior = old[row["case_id"]]
        assert len(prior["steps"]) == len(row["steps"])
        changes = []
        for index, (left, right) in enumerate(zip(prior["steps"], row["steps"]), 1):
            op = left["action"]["op"]
            assert left["action"] == right["action"]
            if _response(op, left["reference_response"], left["reference_error"]) != _response(
                op, right["reference_response"], right["reference_error"]
            ):
                changes.append(f"{index}:response")
            if _state(left["reference_state"]) != _state(right["reference_state"]):
                changes.append(f"{index}:state")
        deltas[row["case_id"]] = changes
    return {
        "A": {"completed_cases": len(a["cases"]), "requests": a["requests"], "censored": True},
        "B": b,
        "C": c_summary,
        "D": {
            "selection_cells": len(d["selection"]),
            "evaluation_cells": len(d["evaluation"]),
            "requests": d["requests"],
            "summary": d["summary"],
        },
        "E": {"requests": e["requests"], "families": e_summary},
        "F": {
            "cases": len(f["rows"]),
            "requests": f["requests"],
            "simulator_outcomes": {row["case_id"]: row["outcome"] for row in f["rows"]},
            "normalized_reference_version_deltas": deltas,
        },
    }


if __name__ == "__main__":
    print(json.dumps(replay(), indent=2, sort_keys=True))
