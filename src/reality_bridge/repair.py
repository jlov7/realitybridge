"""Bounded repair worker (Milestone D).

Inputs (and ONLY these):
- the minimized development counterexample (the sequence that diverged, with
  the reference observations that proved it);
- the documentation (contracts/operations.yaml, observation.yaml);
- the current emulator.

The worker inspects paired counterexample observations, derives a minimal
normalization rule, tests it through the emulator's public `normalize_color`
seam, and promotes it only after the counterexample and nonempty regressions
pass strict gates. Its API has no holdout parameter. This is interface
discipline, not OS/process isolation from files in the checkout.

The first derived rule is grounded in Milestone C's real divergence: Gitea
strips the leading '#' from label colors ('d73a4a', not '#d73a4a'). The rule
language is deliberately small — per-field normalization transforms.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from reality_bridge.differential import Outcome
from reality_bridge.emulator import Emulator

# evaluate(emu, sequence_of_action_dicts) -> four-way differential outcome
EvaluateFn = Callable[[Emulator, list[dict[str, Any]]], Outcome]


@dataclass(frozen=True, slots=True)
class RepairRule:
    """One derived normalization rule, e.g. strip '#' from label colour."""

    field: str
    transform: str  # "strip_leading_hash" | "noop"
    evidence: str = ""


@dataclass(slots=True)
class RepairResult:
    rules_derived: list[RepairRule] = field(default_factory=list)
    rules_applied: list[RepairRule] = field(default_factory=list)
    counterexample_before: Outcome | None = None
    counterexample_after: Outcome | None = None
    regression_baseline_outcomes: list[Outcome] = field(default_factory=list)
    regression_outcomes: list[Outcome] = field(default_factory=list)
    reason: str = ""

    @property
    def verified(self) -> bool:
        return (
            self.counterexample_before == "diverge"
            and self.counterexample_after == "agree"
            and bool(self.regression_baseline_outcomes)
            and all(outcome == "agree" for outcome in self.regression_baseline_outcomes)
            and bool(self.regression_outcomes)
            and all(outcome == "agree" for outcome in self.regression_outcomes)
        )

    @property
    def counterexample_now_agrees(self) -> bool:
        return self.counterexample_after == "agree"

    @property
    def regressions_still_agree(self) -> bool:
        return bool(self.regression_outcomes) and all(
            outcome == "agree" for outcome in self.regression_outcomes
        )


def _derive_rules(counterexample: dict[str, Any]) -> list[RepairRule]:
    """Derive minimal rules from the counterexample's reference observations.

    Two shapes occur in the differential output:
    - an issue observation: `ref.labels` is a list of {name, color};
    - a bare label: `ref.color` directly (the create_label divergence).
    Both are handled. If a reference colour has no leading '#' while the emulator
    stored one verbatim (per the docs), that mismatch yields the strip rule.
    """
    ref = counterexample.get("ref") or {}
    sim = counterexample.get("sim") or {}
    if not isinstance(ref, dict) or not isinstance(sim, dict):
        return []
    candidates: list[tuple[dict, dict]] = []
    if isinstance(ref.get("labels"), list):
        ref_labels = {
            str(item.get("name")): item for item in ref["labels"] if isinstance(item, dict)
        }
        sim_labels = {
            str(item.get("name")): item
            for item in (sim.get("labels") or [])
            if isinstance(item, dict)
        }
        candidates = [
            (item, sim_labels[name]) for name, item in ref_labels.items() if name in sim_labels
        ]
    elif isinstance(ref.get("color"), str) and isinstance(sim.get("color"), str):
        candidates = [(ref, sim)]
    rules: list[RepairRule] = []
    for ref_item, sim_item in candidates:
        ref_color = str(ref_item.get("color", ""))
        sim_color = str(sim_item.get("color", ""))
        if sim_color.startswith("#") and ref_color == sim_color.removeprefix("#"):
            rules.append(
                RepairRule(
                    field="label.color",
                    transform="strip_leading_hash",
                    evidence=f"reference returns {ref_color!r}; simulator returns {sim_color!r}",
                )
            )
    return rules[:1]  # one minimal rule per derivation pass


def _strip_hash(color: str) -> str:
    return color.removeprefix("#")


def apply_rules(emu: Emulator, rules: list[RepairRule]) -> Emulator:
    """Install derived rules through the public seam; never private internals."""
    for rule in rules:
        if rule.transform == "strip_leading_hash" and rule.field == "label.color":
            emu.normalize_color = _strip_hash
    return emu


def repair(
    emu: Emulator,
    counterexample: dict[str, Any],
    regression_sequences: list[list[dict[str, Any]]],
    evaluate: EvaluateFn,
) -> RepairResult:
    """Derive, apply, and verify a bounded repair.

    `evaluate(emu2, seq)` runs the pair fresh and returns a four-way outcome.
    Verification requires a pre-repair divergence, post-repair agreement, and
    at least one previously agreeing regression that still agrees. Unknown,
    unsupported, and an empty regression set all fail closed.
    """
    result = RepairResult()
    rules = _derive_rules(counterexample)
    result.rules_derived = rules
    if not rules:
        result.reason = "counterexample did not support a bounded repair rule"
        return result

    result.counterexample_before = evaluate(emu, counterexample["prefix"])
    if result.counterexample_before != "diverge":
        result.reason = "counterexample was not a confirmed pre-repair divergence"
        return result
    if not regression_sequences:
        result.reason = "at least one previously agreeing regression is required"
        return result
    result.regression_baseline_outcomes = [evaluate(emu, seq) for seq in regression_sequences]
    if any(outcome != "agree" for outcome in result.regression_baseline_outcomes):
        result.reason = "every regression must agree before repair"
        return result

    candidate = apply_rules(copy.deepcopy(emu), rules)
    result.counterexample_after = evaluate(candidate, counterexample["prefix"])
    result.regression_outcomes = [evaluate(candidate, seq) for seq in regression_sequences]
    if not result.verified:
        result.reason = "repair verification did not produce strict agreement on every gate"
        return result
    apply_rules(emu, rules)
    result.rules_applied = rules
    return result
