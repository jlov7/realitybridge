"""Initial live-adapter failures retain an incomplete metered receipt."""

from __future__ import annotations

import json
import sys

from experiments import minimize_full_state as adapter
from reality_bridge import reference as ref


def test_budget_exhausted_before_target_writes_incomplete_receipt(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("REALITYBRIDGE_OWNED_REFERENCE", "1")

    def exhausted(*, with_seed: bool) -> None:
        raise ref.ReferenceBudgetExceeded("cap exhausted during initial seed")

    monkeypatch.setattr(ref, "reset", exhausted)
    output = tmp_path / "incomplete.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "minimize_full_state.py",
            "--live",
            "--case",
            "E06",
            "--step",
            "1",
            "--channel",
            "state",
            "--budget",
            "0",
            "--output",
            str(output),
        ],
    )
    assert adapter.main() == 1
    receipt = json.loads(output.read_text())
    assert receipt["status"] == "incomplete"
    assert receipt["total_reference_requests"] == 0
    assert "cap exhausted" in receipt["reason"]


def test_partial_target_trace_and_actual_request_count_survive(monkeypatch) -> None:
    monkeypatch.setenv("REALITYBRIDGE_OWNED_REFERENCE", "1")
    monkeypatch.setattr(ref, "reset", lambda *, with_seed: None)
    monkeypatch.setattr(ref, "token", lambda: "synthetic")

    def partial_then_fail(case, token, rules, meter, on_progress):
        meter.requests += 3
        on_progress({"case_id": case.case_id, "steps": [{"action": "captured"}]})
        raise ref.ReferenceBudgetExceeded("injected target failure")

    monkeypatch.setattr(adapter, "run_case", partial_then_fail)
    receipt = adapter.run("E06", 1, "state", "labels", 5)
    assert receipt["status"] == "incomplete"
    assert receipt["total_reference_requests"] == 3
    assert receipt["partial_trace"]["steps"] == [{"action": "captured"}]
