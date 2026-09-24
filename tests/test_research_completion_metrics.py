"""Cost cutoffs and divergence denominators follow the frozen protocol."""

from __future__ import annotations

from experiments.research_completion import _arm_summary


def _step(response: str, state: str, end: int) -> dict:
    return {
        "action": {"op": "get_issue", "args": ["rbadmin", "spec-repo", "1"]},
        "response": {
            "outcome": response,
            "reason": "issue fields differ",
            "evidence": "labels: ref=() sim=()",
        },
        "state": {
            "outcome": state,
            "reason": "declared post-state differs",
            "evidence": "issue_count: ref=2 sim=3",
        },
        "post_state_request_end": end,
    }


def test_shared_cutoff_excludes_later_outcome_and_counts_mixed_divergence() -> None:
    arm = {
        "rows": [
            {
                "case_id": "D01",
                "outcome": "undetermined",
                "steps": [_step("diverge", "undetermined", 17)],
                "completed_at_request": 17,
            },
            {
                "case_id": "D02",
                "outcome": "diverge",
                "steps": [_step("diverge", "diverge", 41)],
                "completed_at_request": 41,
            },
        ]
    }
    summary = _arm_summary(arm, 20)
    assert summary["completed_families"] == 1
    assert summary["divergent_families"] == 1
    assert summary["undetermined_families"] == 1
    assert summary["first_discovery_request"] == 17
    assert summary["signatures"] == ["get_issue:response:issue_fields"]
