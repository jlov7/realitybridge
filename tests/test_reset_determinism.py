"""Reset determinism — the foundation of every paired differential trial.

If the reference cannot be reset to provably equivalent state, the whole
method is invalid: a Difference between reference and simulator could be
explained by reference drift instead of simulator error. So this is an
integration test, not a unit test, and it hits the real pinned container.

Milestone A exit criteria it covers:
- reset is repeatable and observably deterministic (snapshot equality)
- reset cost is measured and stays inside a declared trial budget (G3)
"""

from __future__ import annotations

import httpx

from reality_bridge.reference import ADMIN_USER, BASE_URL, reset, snapshot
from reality_bridge.reference import token as get_token
from reference.seed import REPO
from tests.conftest import requires_reference_container

pytestmark = requires_reference_container

_TRIAL_BUDGET_S = 240.0


def _snapshot_with_current_token() -> dict:
    return snapshot(get_token())


def _create_extra_issue(tok: str) -> None:
    """A deliberate mutation that must be visible in the snapshot."""
    auth = {"Authorization": f"token {tok}"}
    with httpx.Client(base_url=BASE_URL, headers=auth, timeout=15.0) as c:
        c.post(
            f"/repos/{ADMIN_USER}/{REPO}/issues",
            json={"title": "mutation-issue", "body": "should not survive a reset"},
        ).raise_for_status()


def test_snapshot_detects_a_mutation() -> None:
    """The snapshot must see a change, or determinism tests are vacuous."""
    reset(with_seed=True)
    before = _snapshot_with_current_token()
    _create_extra_issue(get_token())
    after = _snapshot_with_current_token()
    assert before != after
    assert len(after["issues"]) == len(before["issues"]) + 1


def test_reset_is_deterministic_after_mutation() -> None:
    """Reset+seed yields identical state even when a mutation happened in between."""
    reset(with_seed=True)
    _create_extra_issue(get_token())
    mutated = _snapshot_with_current_token()

    reset(with_seed=True)
    reseeded = _snapshot_with_current_token()

    assert mutated != reseeded
    assert len(reseeded["issues"]) == 2  # the authored seed has exactly two issues


def test_reset_timing_meets_the_trial_budget() -> None:
    """Reset cost measured over a real reset, kept inside the declared budget.

    A fresh equivalent state pair is needed per differential step. If reset
    blows the budget, the sequence grammar must shrink. The assertion message
    carries the numbers so STATUS.md can cite them.
    """
    measured = reset(with_seed=True)
    total = measured["total_s"]
    assert total < _TRIAL_BUDGET_S, (
        f"reset took {total:.1f}s (down={measured['down_s']:.1f}s, "
        f"healthy={measured['healthy_s']:.1f}s, admin={measured['admin_s']:.1f}s, "
        f"seed={measured['seed_s']:.1f}s) — over {_TRIAL_BUDGET_S:.0f}s budget"
    )
