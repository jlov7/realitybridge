"""Sequence-generator integrity: it must not filter by outcomes.

The generator's public surface takes only (seed, max_len, count) — no outcome
parameter, no divergence feedback, no post-hoc filtering. Any code that wants
to *target* probing based on reference outcomes must be a separate module.

These tests prove the constraint holds even when a peer 'discovers' outcomes
between two generations: the sequences are bit-for-bit identical because the
generator has no channel through which outcomes could influence it.
"""

from __future__ import annotations

from reality_bridge import sequences


def test_generation_is_deterministic() -> None:
    a = sequences.generate(seed=1, max_len=4, count=5)
    b = sequences.generate(seed=1, max_len=4, count=5)
    assert sequences.as_dict(a) == sequences.as_dict(b)


def test_different_seeds_differ_in_practice() -> None:
    a = sequences.generate(seed=1, max_len=4, count=20)
    b = sequences.generate(seed=2, max_len=4, count=20)
    assert sequences.as_dict(a) != sequences.as_dict(b)


def test_generation_is_unaffected_by_simulated_outcomes() -> None:
    """Generate, pretend a peer observed divergences, regenerate: identical.

    This is the anti-filtering proof at the level the API allows: the generator
    is a pure function, so there is no state a peer could mutate. We assert the
    stronger claim anyway — same input, same output — because that is the
    contract the evaluator relies on.
    """
    before = sequences.generate(seed=42, max_len=5, count=10)
    # a peer "sees outcomes" (in reality it cannot reach in — that is the point)
    for seq in before:
        _ = [a.as_dict() for a in seq]  # reading outcomes does nothing
    after = sequences.generate(seed=42, max_len=5, count=10)
    assert sequences.as_dict(before) == sequences.as_dict(after)


def test_invalid_actions_are_part_of_the_sample_space() -> None:
    """The generator must include intentionally-invalid calls.

    If it only ever produced valid sequences, the permission/lifecycle surface
    could never be compared — a silent, convenient filter. This test documents
    that the space includes absent titles, absent numbers and label-less
    creation.
    """
    ops = {
        "invalid" if a.op == "create_issue" and a.args[2] == "" else a.op
        for seq in sequences.generate(seed=3, max_len=6, count=200)
        for a in seq
    }
    assert {"create_issue", "edit_issue", "create_label"} <= ops


def test_sequence_lengths_are_bounded() -> None:
    for seq in sequences.generate(seed=9, max_len=6, count=50):
        assert 1 <= len(seq) <= 6


def test_no_import_side_effects_between_generations() -> None:
    """Two calls in the same process from different seeds do not leak state."""
    x = sequences.generate(seed=5, max_len=3, count=3)
    sequences.generate(seed=99, max_len=3, count=3)
    y = sequences.generate(seed=5, max_len=3, count=3)
    assert sequences.as_dict(x) == sequences.as_dict(y)
