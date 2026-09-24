"""A planted simulator defect changes selection rank and creates regret."""

from __future__ import annotations

from experiments.research_completion import (
    POLICIES,
    Goal,
    goal_succeeded,
    policy_plan,
    summarize_policy,
)
from reality_bridge.emulator import Emulator
from reality_bridge.state_oracle import canonicalize_declared_state


def _row(task: str, policy: str, simulator_utility: int, reference_utility: int) -> dict:
    return {
        "task": {"task_id": task},
        "policy": policy,
        "simulator": {
            "utility": simulator_utility,
            "attempted_actions": 1,
            "success": simulator_utility > 0,
        },
        "reference": {
            "utility": reference_utility,
            "attempted_actions": 1,
            "success": reference_utility > 0,
        },
    }


def test_planted_false_pass_changes_rank_and_regret() -> None:
    selection = [
        _row("S01", policy, 99 if policy == "minimal" else 98, 0 if policy == "minimal" else 98)
        for policy in POLICIES
    ]
    evaluation = [
        _row("P01", policy, 99 if policy == "minimal" else 98, 0 if policy == "minimal" else 98)
        for policy in POLICIES
    ]
    result = summarize_policy(selection, evaluation)
    assert result["rank_disagreement"]
    assert result["simulator_selected_policy"] == "minimal"
    assert result["reference_selected_policy"] != "minimal"
    assert result["total_regret"] == 98
    assert result["simulation_induced_regret_component"] == 98
    assert result["simulator_false_task_pass"] == 2


def test_label_creation_inspection_reads_existing_issue() -> None:
    plan = policy_plan("inspect_first", Goal("S03", "label_exists", label="new", color="123456"))
    assert plan[0]["args"][-1] == "1"


def test_lifecycle_goal_requires_observed_successful_close() -> None:
    simulator = Emulator()
    simulator.reset()
    state = canonicalize_declared_state(simulator.export_declared_state())
    close = {"op": "edit_issue", "args": ["rbadmin", "spec-repo", "1", "closed"]}
    attempted = (close,)
    goal = Goal("P06", "open_after_lifecycle", 1)
    assert not goal_succeeded(goal, state, attempted, [])
    forged = [
        {"action": close, "outcome": "error", "post_state": simulator.export_declared_state()}
    ]
    assert not goal_succeeded(goal, state, attempted, forged)
