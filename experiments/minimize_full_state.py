"""Metered live adapter for signature-preserving full-state minimization.

Call only inside reference/owned_lifecycle.py with a source checkout. Results
are exposed engineering regressions, not new research holdouts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from typing import Literal, cast

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from experiments.prospective_cases import DEV_CASES, EVAL_CASES, ProspectiveCase
from experiments.research_completion import run_case
from reality_bridge import reference as ref
from reality_bridge.repair import RepairRule
from reality_bridge.sequences import Action
from reality_bridge.shrink import (
    DefectSignature,
    ProbeResult,
    minimize_signature,
    signature_in_trace,
)

BASELINE_HASH = "61b81d7b4f5c97a1116855fbb93c422d772d9342c5503c1f84b7bd659f3c02ac"
COLOR_RULE = RepairRule(
    "label.color", "strip_leading_hash", "paired values differ only by a simulator leading hash"
)


def run(
    case_id: str,
    step_index: int,
    channel: Literal["response", "state"],
    field: str | None,
    budget: int,
    evidence_contains: str | None = None,
) -> dict:
    if budget < 0:
        raise ValueError("request budget must be nonnegative")
    if os.environ.get("REALITYBRIDGE_OWNED_REFERENCE") != "1":
        raise RuntimeError("live minimization requires owned reference lifecycle")
    cases = {case.case_id: case for case in (*DEV_CASES, *EVAL_CASES)}
    case = cases[case_id]
    if not 0 <= step_index < len(case.actions):
        raise ValueError("target step is outside case")
    baseline = (
        hashlib.sha256((ROOT / "src/reality_bridge/emulator.py").read_bytes()).hexdigest()
        == BASELINE_HASH
    )
    rules = [COLOR_RULE] if baseline else []
    with ref.count_reference_calls(limit=budget) as meter:
        partial_trace: dict | None = None

        def retain_partial(row: dict) -> None:
            nonlocal partial_trace
            partial_trace = deepcopy(row)

        try:
            ref.reset(with_seed=True)
            token = ref.token()
            original = run_case(case, token, rules, meter, retain_partial)
        except Exception as exc:  # noqa: BLE001 - preserve initial setup and budget failure
            return {
                "status": "incomplete",
                "reason": f"initial setup or target observation failed: {type(exc).__name__}: {exc}",
                "classification": "exposed engineering counterexample",
                "case_id": case_id,
                "target_step": step_index,
                "target_channel": channel,
                "partial_trace": partial_trace,
                "sequence": [action.as_dict() for action in case.actions],
                "total_reference_requests": meter.requests,
                "hard_cap": budget,
                "baseline_color_rule_applied": baseline,
            }
        part = original["steps"][step_index][channel]
        if part["outcome"] != "diverge":
            return {
                "status": "incomplete",
                "reason": "specified target step/channel is not a divergence",
                "classification": "exposed engineering counterexample",
                "case_id": case_id,
                "target_step": step_index,
                "target_channel": channel,
                "initial_trace": original,
                "sequence": [action.as_dict() for action in case.actions],
                "total_reference_requests": meter.requests,
                "hard_cap": budget,
                "baseline_color_rule_applied": baseline,
            }
        evidence = str(part.get("evidence", ""))
        selected_evidence = evidence_contains if evidence_contains is not None else evidence
        if (
            not evidence
            or (field is not None and f"{field}:" not in evidence)
            or not selected_evidence
            or selected_evidence not in evidence
        ):
            return {
                "status": "incomplete",
                "reason": "target field or evidence selector is absent from the original divergence",
                "classification": "exposed engineering counterexample",
                "case_id": case_id,
                "target_step": step_index,
                "target_channel": channel,
                "initial_trace": original,
                "sequence": [action.as_dict() for action in case.actions],
                "total_reference_requests": meter.requests,
                "hard_cap": budget,
                "baseline_color_rule_applied": baseline,
            }
        signature = DefectSignature(
            case.actions[step_index], channel, part["reason"], field, selected_evidence
        )

        def probe(actions: list[Action], remaining: int) -> ProbeResult:
            before = meter.requests
            try:
                row = run_case(ProspectiveCase("shrink-probe", tuple(actions)), token, rules, meter)
                outcome = signature_in_trace(row["steps"], signature)
                return ProbeResult(outcome, meter.requests - before)
            except (ref.ReferenceBudgetExceeded, ref.ReferenceError) as exc:
                return ProbeResult("unknown", meter.requests - before, str(exc))
            except Exception as exc:  # noqa: BLE001 - transport/machinery uncertainty cannot certify
                return ProbeResult(
                    "unknown", meter.requests - before, f"{type(exc).__name__}: {exc}"
                )

        # The observed original and each fresh recheck are charged to the same meter.
        result = minimize_signature(
            list(case.actions), signature, probe, request_budget=budget - meter.requests
        )
        return {
            "status": "complete" if result.complete else "incomplete",
            "classification": "exposed engineering counterexample",
            "case_id": case_id,
            "target_step": step_index,
            "signature": asdict(signature),
            "sequence": [action.as_dict() for action in result.sequence],
            "initial_trace": original,
            "minimization": asdict(result),
            "total_reference_requests": meter.requests,
            "hard_cap": budget,
            "baseline_color_rule_applied": baseline,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument(
        "--case", required=True, choices=[case.case_id for case in (*DEV_CASES, *EVAL_CASES)]
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--channel", choices=["response", "state"], required=True)
    parser.add_argument("--field")
    parser.add_argument("--evidence-contains")
    parser.add_argument("--budget", type=int, default=150)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = run(
            args.case,
            args.step,
            cast(Literal["response", "state"], args.channel),
            args.field,
            args.budget,
            args.evidence_contains,
        )
    except Exception as exc:  # noqa: BLE001 - preserve preflight and other machinery failures
        result = {
            "status": "incomplete",
            "reason": f"{type(exc).__name__}: {exc}",
            "sequence": [],
            "total_reference_requests": 0,
            "hard_cap": args.budget,
        }
    output.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n")
    print(
        json.dumps(
            {k: result[k] for k in ("status", "sequence", "total_reference_requests")}, indent=2
        )
    )
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
