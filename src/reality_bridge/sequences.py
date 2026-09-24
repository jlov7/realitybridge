"""Bounded state/action sequence generator (contracts/operations.yaml).

Generates action sequences over the six-operation grammar, up to a declared
length, from a deterministic seed.

Design constraint (Milestone B): the generator MUST NOT be able to filter or
skew sequences after seeing outcomes. Its public surface takes only
`(seed, max_len, grammar)` — no outcomes, no divergence feedback, no
post-hoc filtering. If a later repair loop wants targeted probing, that is a
SEPARATE module that consumes reference outcomes openly; it is not this one.
"""

from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass

# Bounded seeds: owner, repo, and the three seeded labels (Milestone A seed).
_OWNERS = ["rbadmin"]
_REPOS = ["spec-repo"]
_LABELS = ["bug", "ui", "api"]


@dataclass(frozen=True, slots=True)
class Action:
    op: str
    args: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {"op": self.op, "args": list(self.args)}


def _issue_number(rng: random.Random) -> int:
    return rng.randint(1, 4)


def _sample_action(rng: random.Random) -> Action:
    """Sample one action from the six-operation grammar.

    The sample space includes intentionally INVALID calls (absent title, absent
    number, wrong label) because the permission/lifecycle surface is part of
    the comparison. Skipping those would be a subtle form of filtering.
    """
    kind = rng.random()
    if kind < 0.18:
        return Action("create_issue", ("rbadmin", "spec-repo", f"issue-{rng.randint(1, 99)}"))
    if kind < 0.26:
        # intentionally invalid: no title
        return Action("create_issue", ("rbadmin", "spec-repo", ""))
    if kind < 0.42:
        return Action("get_issue", ("rbadmin", "spec-repo", str(_issue_number(rng))))
    if kind < 0.56:
        num = _issue_number(rng)
        state = "closed" if rng.random() < 0.4 else "open"
        return Action("edit_issue", ("rbadmin", "spec-repo", str(num), state))
    if kind < 0.64:
        # intentionally invalid: absent number
        return Action("edit_issue", ("rbadmin", "spec-repo", "99", "open"))
    if kind < 0.79:
        label = rng.choice(_LABELS)
        return Action("add_label", ("rbadmin", "spec-repo", str(_issue_number(rng)), label))
    if kind < 0.86:
        return Action(
            "remove_label", ("rbadmin", "spec-repo", str(_issue_number(rng)), rng.choice(_LABELS))
        )
    if kind < 0.96:
        color = rng.choice(["#d73a4a", "#0e8a16", "#6f42c1"])
        return Action(
            "create_label", ("rbadmin", "spec-repo", f"label-{rng.randint(1, 20)}", color)
        )
    return Action("create_label", ("rbadmin", "spec-repo", "", ""))  # invalid: no name


def generate(seed: int, max_len: int, count: int = 1) -> list[list[Action]]:
    """Deterministic sequence generation.

    Pure function of its arguments. `count` sequences of length 1..max_len.
    The same (seed, max_len, count) always produces the same sequences.
    """
    rng = random.Random(seed)
    sequences: list[list[Action]] = []
    for _ in range(count):
        length = rng.randint(1, max_len)
        sequences.append([_sample_action(rng) for _ in range(length)])
    return sequences


# Targeted-probing arm (brief: query selector prioritises unexplored preconditions and lifecycle boundaries).
_TARGETED_ACTIONS: list[Action] = [
    Action("create_issue", ("rbadmin", "spec-repo", "")),  # absent title
    Action("get_issue", ("rbadmin", "spec-repo", "999")),  # absent issue
    Action("edit_issue", ("rbadmin", "spec-repo", "999", "closed")),  # absent issue
    Action("create_label", ("rbadmin", "spec-repo", "", "")),  # absent name
    Action("add_label", ("rbadmin", "spec-repo", "1", "nonexistent-label")),  # absent label
    Action("remove_label", ("rbadmin", "spec-repo", "3", "api")),  # label not on issue
    Action(
        "remove_label", ("rbadmin", "spec-repo", "1", "nonexistent-label")
    ),  # absent label, absent attachment
    Action("edit_issue", ("rbadmin", "spec-repo", "1", "closed")),  # lifecycle transition
    Action("edit_issue", ("rbadmin", "spec-repo", "1", "open")),  # lifecycle re-open
]


def generate_targeted(seed: int, max_len: int, count: int = 1) -> list[list[Action]]:
    """Deterministic sequences biased toward boundary/precondition cases.

    Same contract as `generate` (pure function), but the sample space is the
    boundary surface: absent objects, absent required fields, invalid labels,
    and state transitions. Used as the 'targeted probing' arm.
    """
    rng = random.Random(seed ^ 0x5EED5)
    sequences: list[list[Action]] = []
    for _ in range(count):
        length = rng.randint(1, max_len)
        sequences.append([rng.choice(_TARGETED_ACTIONS) for _ in range(length)])
    return sequences


def all_invalid_ops() -> set[str]:
    """The intentionally-invalid actions are part of the sample space."""
    return {"create_issue:no_title", "edit_issue:absent", "create_label:no_name"}


def as_dict(sequences: Iterable[list[Action]]) -> list[list[dict[str, object]]]:
    return [[a.as_dict() for a in seq] for seq in sequences]
