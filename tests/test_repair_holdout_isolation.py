"""Repair-input discipline and fail-closed verification.

These tests establish an interface-level boundary: the repair function receives
only a counterexample, declared regressions, and an evaluator. They do not claim
OS/process isolation from the repository or held-out files.
"""

from __future__ import annotations

import inspect
from typing import Any

from reality_bridge.differential import Outcome, compare
from reality_bridge.emulator import Emulator, EmulatorError
from reality_bridge.projection import label_observation
from reality_bridge.repair import RepairRule, repair


class UnrepairedEmulator(Emulator):
    """Explicit legacy candidate for testing the bounded color repair gate."""

    @staticmethod
    def normalize_color(color: str) -> str:
        return color


COUNTEREXAMPLE = {
    "prefix": [{"op": "create_label", "args": ["rbadmin", "spec-repo", "label-2", "#0e8a16"]}],
    "ref": {"name": "label-2", "color": "0e8a16"},
    "sim": {"name": "label-2", "color": "#0e8a16"},
}
REGRESSION = [[{"op": "get_issue", "args": ["rbadmin", "spec-repo", "1"]}]]


def _evaluate(emu: Emulator, seq: list[dict[str, Any]]) -> Outcome:
    emu.reset()
    try:
        raw: dict[str, Any] = {}
        for action in seq:
            raw = emu.step(action)
    except EmulatorError:
        return "diverge"
    if seq[-1]["op"] == "create_label":
        ref = label_observation("create_label", COUNTEREXAMPLE["ref"])
        sim = label_observation("create_label", raw)
        return compare(ref, sim).outcome
    return "agree"


def test_repair_signature_has_no_explicit_holdout_parameter() -> None:
    assert list(inspect.signature(repair).parameters) == [
        "emu",
        "counterexample",
        "regression_sequences",
        "evaluate",
    ]


def test_repair_rule_uses_paired_counterexample_values() -> None:
    emu = UnrepairedEmulator()
    result = repair(emu, COUNTEREXAMPLE, REGRESSION, _evaluate)
    assert result.verified
    assert result.rules_applied == [
        RepairRule(
            field="label.color",
            transform="strip_leading_hash",
            evidence="reference returns '0e8a16'; simulator returns '#0e8a16'",
        )
    ]
    assert emu.normalize_color("#abcdef") == "abcdef"


def test_reference_value_alone_cannot_trigger_a_rule() -> None:
    emu = UnrepairedEmulator()
    incomplete = {"prefix": COUNTEREXAMPLE["prefix"], "ref": COUNTEREXAMPLE["ref"]}
    result = repair(emu, incomplete, REGRESSION, _evaluate)
    assert result.rules_derived == []
    assert not result.verified


def test_empty_regression_set_cannot_verify_or_apply() -> None:
    emu = UnrepairedEmulator()
    result = repair(emu, COUNTEREXAMPLE, [], _evaluate)
    assert result.rules_derived
    assert result.rules_applied == []
    assert not result.regressions_still_agree
    assert not result.verified
    assert emu.normalize_color("#abcdef") == "#abcdef"


def test_unknown_counterexample_cannot_verify_or_apply() -> None:
    emu = UnrepairedEmulator()
    result = repair(emu, COUNTEREXAMPLE, REGRESSION, lambda _emu, _seq: "undetermined")
    assert result.rules_applied == []
    assert not result.verified
    assert emu.normalize_color("#abcdef") == "#abcdef"


def test_regression_must_agree_before_repair() -> None:
    def evaluate(emu: Emulator, seq: list[dict[str, Any]]) -> Outcome:
        if seq == REGRESSION[0]:
            return "diverge"
        return _evaluate(emu, seq)

    emu = UnrepairedEmulator()
    result = repair(emu, COUNTEREXAMPLE, REGRESSION, evaluate)
    assert result.regression_baseline_outcomes == ["diverge"]
    assert result.rules_applied == []
    assert not result.verified


def test_failed_post_repair_gate_does_not_mutate_candidate() -> None:
    def evaluate(emu: Emulator, seq: list[dict[str, Any]]) -> Outcome:
        if seq == REGRESSION[0] and emu.normalize_color("#aabbcc") == "aabbcc":
            return "unsupported"
        return _evaluate(emu, seq)

    emu = UnrepairedEmulator()
    result = repair(emu, COUNTEREXAMPLE, REGRESSION, evaluate)
    assert result.regression_outcomes == ["unsupported"]
    assert result.rules_applied == []
    assert not result.verified
    assert emu.normalize_color("#abcdef") == "#abcdef"
