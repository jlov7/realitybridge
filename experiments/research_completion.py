"""Finite, prospectively declared RealityBridge study.

Run only with REALITYBRIDGE_COMPOSE_PROJECT=rb-research-20260922 and
REALITYBRIDGE_PORT=13002. Every harness API call passes the reference meter.
The output directory is unique per attempt and is updated after each phase.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from experiments.prospective_cases import (
    DEV_CASES,
    EVAL_CASES,
    RANDOM_ORDER_SEEDS,
    TARGETED_ORDER,
    ProspectiveCase,
    case_hash,
    cases_by_id,
)
from reality_bridge import reference as ref
from reality_bridge.differential import Difference
from reality_bridge.emulator import Emulator, EmulatorError
from reality_bridge.prospective_comparison import compare_responses, project_response
from reality_bridge.repair import RepairRule, apply_rules
from reality_bridge.repair_sandbox import run_sandboxed_repair
from reality_bridge.state_oracle import (
    DeclaredState,
    LabelPairing,
    StateOracleError,
    canonicalize_declared_state,
    compare_declared_states,
)

PROTOCOL = ROOT / "docs/research-completion-2026-09-22/PROTOCOL.md"
IMAGE = "gitea/gitea@sha256:0489485c8afcb367a1c8066e081ec47d1592258dcbf729875e8bf4aa0b84a7c9"
EXPECTED_PROTOCOL_HASH = "60e5f90b4f588b304ab25453d2b96d690a8222d97183d9fb8d3d5a61b5e91e8c"
ARM_CAP = 180
POLICY_CAP = 750
SOURCE_FILES = (
    "experiments/research_completion.py",
    "experiments/reproduce_research_completion.py",
    "experiments/prospective_cases.py",
    "experiments/sandbox_repair_worker.c",
    "src/reality_bridge/reference.py",
    "src/reality_bridge/emulator.py",
    "src/reality_bridge/state_oracle.py",
    "src/reality_bridge/prospective_comparison.py",
    "src/reality_bridge/repair_sandbox.py",
)
RESPONSE_DEFECT_KINDS = {
    "action differs": "action",
    "error category differs": "error_category",
    "payload kind differs": "payload_kind",
    "issue fields differ": "issue_fields",
    "label differs": "label",
    "label set differs": "membership",
}
STATE_DEFECT_FIELDS = ("issue_count", "label_count", "issues", "labels")


class ComponentBoundExceeded(RuntimeError):
    """The frozen per-case request admission bound was too small."""


class _StoredError:
    def __init__(self, value: dict[str, Any]) -> None:
        self.status = value["status"]
        self.body = value["body"]

    def __str__(self) -> str:
        return str(self.body)


def _check_component(meter: ref.ReferenceCallMeter, before: int, maximum: int, name: str) -> None:
    actual = meter.requests - before
    if actual > maximum:
        raise ComponentBoundExceeded(
            f"{name}: {actual} requests exceeded declared maximum {maximum}"
        )


@contextmanager
def _phase_meter(
    name: str, receipt: dict[str, Any], receipt_path: Path, limit: int | None = None
) -> Iterator[ref.ReferenceCallMeter]:
    with ref.count_reference_calls(limit=limit) as meter:
        try:
            yield meter
        finally:
            receipt["phase_ledger"][name] = meter.requests
            _write(receipt_path, receipt)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")
    temporary.replace(path)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _running_reference_image() -> dict[str, str]:
    container_id = ref._compose("ps", "-q", ref.SERVICE).strip()
    if not container_id:
        raise RuntimeError("isolated reference container was not running")
    inspection = subprocess.run(
        ["docker", "inspect", "-f", "{{.Config.Image}}|{{.Image}}", container_id],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    declared, image_id = inspection.split("|", maxsplit=1)
    if declared != IMAGE:
        raise RuntimeError(f"isolated container image mismatch: {declared}")
    architecture = subprocess.run(
        ["docker", "image", "inspect", "-f", "{{.Architecture}}", image_id],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if architecture != "arm64":
        raise RuntimeError(f"reference architecture mismatch: {architecture}")
    return {"declared": declared, "image_id": image_id, "architecture": architecture}


def _new_emulator(rules: list[RepairRule]) -> Emulator:
    candidate = Emulator()
    apply_rules(candidate, rules)
    candidate.reset()
    return candidate


def _snapshot_pair(
    candidate: Emulator, token: str, pairing: LabelPairing | None = None
) -> tuple[dict[str, Any], dict[str, Any], Difference]:
    reference_raw = ref.export_declared_state(token)
    simulator_raw = candidate.export_declared_state()
    if pairing is not None and not pairing.reference_ids and not pairing.simulator_ids:
        initial = LabelPairing.from_initial(reference_raw, simulator_raw)
        pairing.reference_ids.update(initial.reference_ids)
        pairing.simulator_ids.update(initial.simulator_ids)
    left = canonicalize_declared_state(
        reference_raw, None if pairing is None else pairing.reference_ids
    )
    right = canonicalize_declared_state(
        simulator_raw, None if pairing is None else pairing.simulator_ids
    )
    return reference_raw, simulator_raw, compare_declared_states(left, right)


def _step(
    candidate: Emulator, token: str, action: dict[str, Any], meter: ref.ReferenceCallMeter,
    pairing: LabelPairing | None = None,
) -> dict[str, Any]:
    reference_raw: Any = None
    simulator_raw: Any = None
    reference_error: ref.ReferenceStepError | None = None
    simulator_error: EmulatorError | None = None
    before_action = meter.requests
    try:
        reference_raw = ref.step_reference(action, token)
    except ref.ReferenceStepError as exc:
        reference_error = exc
    try:
        simulator_raw = candidate.step(action)
    except EmulatorError as exc:
        simulator_error = exc
    _check_component(meter, before_action, 3, "action")
    response = compare_responses(
        action["op"], reference_raw, reference_error, simulator_raw, simulator_error
    )
    before_oracle = meter.requests
    if pairing is not None and action["op"] == "create_label":
        pairing.note_creation(reference_raw, simulator_raw)
    reference_state, simulator_state, state = _snapshot_pair(candidate, token, pairing)
    _check_component(meter, before_oracle, 2, "post-action oracle")
    return {
        "action_request_start": before_action,
        "action_request_end": before_oracle,
        "post_state_request_end": meter.requests,
        "action": action,
        "reference_response": reference_raw,
        "simulator_response": simulator_raw,
        "reference_error": None
        if reference_error is None
        else {
            "status": reference_error.status,
            "body": reference_error.body,
        },
        "simulator_error": None
        if simulator_error is None
        else {
            "status": simulator_error.status,
            "message": str(simulator_error),
        },
        "response": asdict(response),
        "state": asdict(state),
        "reference_state": reference_state,
        "simulator_state": simulator_state,
    }


def _family_outcome(steps: list[dict[str, Any]]) -> str:
    outcomes = [part["outcome"] for step in steps for part in (step["response"], step["state"])]
    if "undetermined" in outcomes:
        return "undetermined"
    if "unsupported" in outcomes:
        return "unsupported"
    if "diverge" in outcomes:
        return "diverge"
    return "agree"


def run_case(
    case: ProspectiveCase,
    token: str,
    rules: list[RepairRule],
    meter: ref.ReferenceCallMeter,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    start = meter.requests
    before_reset = meter.requests
    ref.soft_reset(token)
    _check_component(meter, before_reset, 8, "soft reset and seed")
    candidate = _new_emulator(rules)
    pairing = LabelPairing({}, {})
    before_initial_oracle = meter.requests
    reference_initial, simulator_initial, initial = _snapshot_pair(candidate, token, pairing)
    _check_component(meter, before_initial_oracle, 2, "initial oracle")
    row: dict[str, Any] = {
        "case_id": case.case_id,
        "actions": [action.as_dict() for action in case.actions],
        "reference_initial": reference_initial,
        "simulator_initial": simulator_initial,
        "initial_comparison": asdict(initial),
        "steps": [],
    }
    if initial.outcome != "agree":
        row["outcome"] = "setup_failure"
        row["completed_at_request"] = meter.requests
        row["request_cost"] = meter.requests - start
        return row
    if on_progress is not None:
        on_progress(row)
    for action in case.actions:
        row["steps"].append(_step(candidate, token, action.as_dict(), meter, pairing))
        if on_progress is not None:
            on_progress(row)
    row["outcome"] = _family_outcome(row["steps"])
    row["completed_at_request"] = meter.requests
    row["request_cost"] = meter.requests - start
    return row


def _arm(order: tuple[str, ...], token: str, rules: list[RepairRule], out: Path) -> dict[str, Any]:
    lookup = cases_by_id(DEV_CASES)
    rows: list[dict[str, Any]] = []
    status = "complete"
    interrupted_attempt: dict[str, Any] | None = None
    with ref.count_reference_calls(limit=ARM_CAP) as meter:
        for case_id in order:
            case = lookup[case_id]
            admission = 10 + 5 * len(case.actions)
            if ARM_CAP - meter.requests < admission:
                status = "budget_censored"
                break
            interrupted_attempt = {
                "case_id": case_id,
                "request_start": meter.requests,
                "partial_row": None,
            }

            def retain_partial(
                partial: dict[str, Any], attempt: dict[str, Any] = interrupted_attempt
            ) -> None:
                attempt["partial_row"] = partial
                _write(
                    out,
                    {
                        "status": "running",
                        "order": order,
                        "rows": rows,
                        "interrupted_attempt": attempt,
                        "requests": meter.requests,
                    },
                )

            try:
                row = run_case(case, token, rules, meter, retain_partial)
            except (ref.ReferenceBudgetExceeded, ComponentBoundExceeded) as exc:
                status = "bound_violation_censored"
                interrupted_attempt["error"] = f"{type(exc).__name__}: {exc}"
                interrupted_attempt["requests_used"] = (
                    meter.requests - interrupted_attempt["request_start"]
                )
                break
            except Exception as exc:  # noqa: BLE001 - retain machinery failure with partial evidence
                status = "machinery_failure"
                interrupted_attempt["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
                interrupted_attempt["requests_used"] = (
                    meter.requests - interrupted_attempt["request_start"]
                )
                break
            rows.append(row)
            interrupted_attempt = None
            _write(
                out, {"status": "running", "order": order, "rows": rows, "requests": meter.requests}
            )
            if row["outcome"] == "setup_failure":
                status = "setup_failure"
                break
    receipt = {
        "status": status,
        "order": order,
        "rows": rows,
        "requests": meter.requests,
        "hard_cap": ARM_CAP,
        "not_started": list(order[len(rows) :]),
        "interrupted_attempt": interrupted_attempt,
    }
    _write(out, receipt)
    return receipt


def _arm_summary(arm: dict[str, Any], cutoff: int) -> dict[str, Any]:
    rows = [row for row in arm["rows"] if row["completed_at_request"] <= cutoff]
    steps = [step for row in rows for step in row["steps"]]
    signatures = sorted({signature for step in steps for signature in defect_signatures(step)})
    return {
        "cutoff": cutoff,
        "completed_families": len(rows),
        "censored_families": 14 - len(rows),
        "divergent_families": sum(
            any(
                step[part]["outcome"] == "diverge"
                for step in row["steps"]
                for part in ("response", "state")
            )
            for row in rows
        ),
        "undetermined_families": sum(row["outcome"] == "undetermined" for row in rows),
        "unsupported_families": sum(row["outcome"] == "unsupported" for row in rows),
        "compared_actions": len(steps),
        "response_mismatch_actions": sum(
            step["response"]["outcome"] == "diverge" for step in steps
        ),
        "state_mismatch_actions": sum(step["state"]["outcome"] == "diverge" for step in steps),
        "undetermined_actions": sum(
            any(step[p]["outcome"] == "undetermined" for p in ("response", "state"))
            for step in steps
        ),
        "unsupported_actions": sum(
            any(step[p]["outcome"] == "unsupported" for p in ("response", "state"))
            for step in steps
        ),
        "signatures": signatures,
        "unique_signatures_per_request": len(signatures) / cutoff if cutoff else None,
        "first_discovery_request": next(
            (
                step["post_state_request_end"]
                for row in rows
                for step in row["steps"]
                if any(step[part]["outcome"] == "diverge" for part in ("response", "state"))
            ),
            None,
        ),
    }


def defect_signatures(step: dict[str, Any]) -> tuple[str, ...]:
    """Predeclared operation and field categories for discovered differences."""
    operation = step["action"]["op"]
    found = []
    response = step["response"]
    if response["outcome"] == "diverge":
        kind = RESPONSE_DEFECT_KINDS.get(response["reason"], "other")
        found.append(f"{operation}:response:{kind}")
    state = step["state"]
    if state["outcome"] == "diverge":
        matched = [field for field in STATE_DEFECT_FIELDS if f"{field}:" in state["evidence"]]
        found.extend(f"{operation}:state:{field}" for field in (matched or ["other"]))
    return tuple(found)


@dataclass(frozen=True)
class Goal:
    task_id: str
    kind: str
    issue: int = 0
    label: str = ""
    color: str = ""


SELECTION_TASKS = (
    Goal("S01", "closed", 2),
    Goal("S02", "label_present", 2, "ui"),
    Goal("S03", "label_exists", label="p2-policy-dev", color="556677"),
    Goal("S04", "label_absent", 1, "bug"),
)
EVALUATION_TASKS = (
    Goal("P01", "closed", 1),
    Goal("P02", "label_present", 2, "api"),
    Goal("P03", "label_exists", label="p2-policy-eval", color="8899aa"),
    Goal("P04", "label_absent", 2, "bug"),
    Goal("P05", "label_present", 1, "p2-policy-attach", "778899"),
    Goal("P06", "open_after_lifecycle", 1),
)
POLICIES = ("minimal", "inspect_first", "ensure_prerequisite")


def _action(op: str, *args: str) -> dict[str, Any]:
    return {"op": op, "args": ["rbadmin", "spec-repo", *args]}


def policy_plan(policy: str, goal: Goal) -> tuple[dict[str, Any], ...]:
    number = str(goal.issue)
    if goal.kind == "closed":
        direct = (_action("edit_issue", number, "closed"),)
        prerequisite = (_action("edit_issue", number, "open"),)
    elif goal.kind == "label_present":
        direct = (_action("add_label", number, goal.label),)
        prerequisite = (_action("create_label", goal.label, goal.color or "#0e8a16"),)
    elif goal.kind == "label_exists":
        direct = (_action("create_label", goal.label, goal.color),)
        prerequisite = (_action("get_issue", "1"),)
    elif goal.kind == "label_absent":
        direct = (_action("remove_label", number, goal.label),)
        prerequisite = (_action("get_issue", number),)
    elif goal.kind == "open_after_lifecycle":
        direct = (_action("edit_issue", number, "closed"), _action("edit_issue", number, "open"))
        prerequisite = (_action("edit_issue", number, "open"),)
    else:
        raise ValueError(f"unknown goal kind {goal.kind}")
    if policy == "minimal":
        return direct
    if policy == "inspect_first":
        return (_action("get_issue", str(goal.issue or 1)), *direct)
    if policy == "ensure_prerequisite":
        return (*prerequisite, *direct)
    raise ValueError(f"unknown policy {policy}")


def goal_succeeded(
    goal: Goal,
    state: DeclaredState,
    attempted: tuple[dict[str, Any], ...],
    steps: list[dict[str, Any]] | None = None,
) -> bool:
    issue = next((row for row in state.issues if row.number == goal.issue), None)
    if goal.kind == "label_exists":
        return (goal.label, goal.color) in state.labels
    if issue is None:
        return False
    if goal.kind == "closed":
        return issue.state == "closed" and issue.closed
    if goal.kind == "label_present":
        return any(name == goal.label for name, _ in issue.labels)
    if goal.kind == "label_absent":
        return all(name != goal.label for name, _ in issue.labels)
    if goal.kind == "open_after_lifecycle":
        return (
            issue.state == "open"
            and not issue.closed
            and any(
                step["outcome"] == "success"
                and step["action"]["op"] == "edit_issue"
                and step["action"]["args"][-1] == "closed"
                and any(
                    row["number"] == goal.issue
                    and row["state"] == "closed"
                    and row["closed_at"] is not None
                    for row in step["post_state"]["issues"]
                )
                for step in (steps or [])
            )
        )
    raise ValueError(goal.kind)


def _backend_policy(
    backend: str, candidate: Emulator, token: str, plan: tuple[dict[str, Any], ...], goal: Goal
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    stop = "plan_end"
    for action in plan:
        raw: Any = None
        error: Any = None
        try:
            raw = (
                ref.step_reference(action, token)
                if backend == "reference"
                else candidate.step(action)
            )
        except (ref.ReferenceStepError, EmulatorError) as exc:
            error = exc
        outcome = "success"
        try:
            observation = project_response(
                action["op"], raw, error, simulator=backend == "simulator"
            )
            if observation.unsupported_operation is not None:
                outcome = "unsupported"
            elif observation.error is not None:
                outcome = "undetermined" if observation.error == "transport_uncertain" else "error"
        except (StateOracleError, ValueError, TypeError, KeyError):
            outcome = "undetermined"
        post_state = (
            ref.export_declared_state(token)
            if backend == "reference"
            else candidate.export_declared_state()
        )
        canonicalize_declared_state(post_state)
        steps.append(
            {
                "action": action,
                "raw": raw,
                "error": None
                if error is None
                else {"status": error.status, "body": getattr(error, "body", str(error))},
                "outcome": outcome,
                "post_state": post_state,
            }
        )
        if outcome != "success":
            stop = outcome
            break
    state_raw = (
        ref.export_declared_state(token)
        if backend == "reference"
        else candidate.export_declared_state()
    )
    state = canonicalize_declared_state(state_raw)
    attempted = tuple(step["action"] for step in steps)
    success = goal_succeeded(goal, state, attempted, steps)
    return {
        "steps": steps,
        "stop": stop,
        "state": state_raw,
        "success": success,
        "attempted_actions": len(steps),
        "utility": (100 if success else 0) - len(steps),
    }


def _policy_trial(
    task: Goal, policy: str, token: str, rules: list[RepairRule], meter: ref.ReferenceCallMeter
) -> dict[str, Any]:
    start = meter.requests
    ref.soft_reset(token)
    candidate = _new_emulator(rules)
    reference_initial, simulator_initial, initial = _snapshot_pair(candidate, token)
    if initial.outcome != "agree":
        raise RuntimeError(f"policy setup mismatch for {task.task_id}/{policy}")
    plan = policy_plan(policy, task)
    simulator = _backend_policy("simulator", candidate, token, plan, task)
    reference = _backend_policy("reference", candidate, token, plan, task)
    diagnostics = []
    for reference_step, simulator_step in zip(reference["steps"], simulator["steps"], strict=False):
        reference_error = reference_step["error"]
        simulator_error = simulator_step["error"]
        response = compare_responses(
            reference_step["action"]["op"],
            reference_step["raw"],
            None if reference_error is None else _StoredError(reference_error),
            simulator_step["raw"],
            None if simulator_error is None else _StoredError(simulator_error),
        )
        post_state = compare_declared_states(
            canonicalize_declared_state(reference_step["post_state"]),
            canonicalize_declared_state(simulator_step["post_state"]),
        )
        diagnostics.append({"response": asdict(response), "state": asdict(post_state)})
    final_state = compare_declared_states(
        canonicalize_declared_state(reference["state"]),
        canonicalize_declared_state(simulator["state"]),
    )
    return {
        "task": asdict(task),
        "policy": policy,
        "plan": plan,
        "reference_initial": reference_initial,
        "simulator_initial": simulator_initial,
        "simulator": simulator,
        "reference": reference,
        "diagnostics": diagnostics,
        "final_state_diagnostic": asdict(final_state),
        "plan_length_difference": len(reference["steps"]) - len(simulator["steps"]),
        "request_start": start,
        "completed_at_request": meter.requests,
        "request_cost": meter.requests - start,
    }


def rank_policies(rows: list[dict[str, Any]], backend: str) -> list[str]:
    return sorted(
        POLICIES,
        key=lambda policy: (
            -sum(row[backend]["utility"] for row in rows if row["policy"] == policy)
            / len({row["task"]["task_id"] for row in rows}),
            sum(row[backend]["attempted_actions"] for row in rows if row["policy"] == policy),
            policy,
        ),
    )


def summarize_policy(
    selection: list[dict[str, Any]], evaluation: list[dict[str, Any]]
) -> dict[str, Any]:
    sim_rank = rank_policies(selection, "simulator")
    ref_rank = rank_policies(selection, "reference")
    sim_selected, ref_selected = sim_rank[0], ref_rank[0]
    by_task = {}
    for row in evaluation:
        by_task.setdefault(row["task"]["task_id"], {})[row["policy"]] = row
    per_task = []
    for task_id, task_rows in by_task.items():
        best = max(row["reference"]["utility"] for row in task_rows.values())
        sim_value = task_rows[sim_selected]["reference"]["utility"]
        ref_value = task_rows[ref_selected]["reference"]["utility"]
        per_task.append(
            {
                "task_id": task_id,
                "best_reference_utility": best,
                "simulator_selected_reference_utility": sim_value,
                "reference_selected_reference_utility": ref_value,
                "regret": best - sim_value,
                "simulation_induced_component": ref_value - sim_value,
                "task_shift_component": best - ref_value,
            }
        )
    return {
        "simulator_selection_rank": sim_rank,
        "reference_selection_rank": ref_rank,
        "rank_disagreement": sim_rank != ref_rank,
        "simulator_selected_policy": sim_selected,
        "reference_selected_policy": ref_selected,
        "simulator_false_task_pass": sum(
            row["simulator"]["success"] and not row["reference"]["success"]
            for row in (*selection, *evaluation)
        ),
        "per_task": per_task,
        "total_regret": sum(row["regret"] for row in per_task),
        "simulation_induced_regret_component": sum(
            row["simulation_induced_component"] for row in per_task
        ),
        "task_shift_regret_component": sum(row["task_shift_component"] for row in per_task),
    }


def _phase_cases(
    name: str,
    cases: tuple[ProspectiveCase, ...],
    token: str,
    rules: list[RepairRule],
    out: Path,
) -> dict[str, Any]:
    rows = []
    interrupted_attempt = None
    status = "complete"
    with ref.count_reference_calls() as meter:
        for case in cases:
            interrupted_attempt = {
                "case_id": case.case_id,
                "request_start": meter.requests,
                "partial_row": None,
            }

            def retain_partial(
                partial: dict[str, Any], attempt: dict[str, Any] = interrupted_attempt
            ) -> None:
                attempt["partial_row"] = partial
                _write(
                    out,
                    {
                        "status": "running",
                        "phase": name,
                        "rows": rows,
                        "interrupted_attempt": attempt,
                        "requests": meter.requests,
                    },
                )

            try:
                row = run_case(case, token, rules, meter, retain_partial)
            except Exception as exc:  # noqa: BLE001 - retain machinery failure with partial evidence
                status = "machinery_failure"
                interrupted_attempt["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
                interrupted_attempt["requests_used"] = (
                    meter.requests - interrupted_attempt["request_start"]
                )
                break
            rows.append(row)
            interrupted_attempt = None
            _write(
                out, {"status": "running", "phase": name, "rows": rows, "requests": meter.requests}
            )
            if row["outcome"] == "setup_failure":
                status = "setup_failure"
                break
    receipt = {
        "phase": name,
        "status": status,
        "rows": rows,
        "interrupted_attempt": interrupted_attempt,
        "requests": meter.requests,
    }
    _write(out, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root", type=Path, default=ROOT / "artifacts/research-completion-2026-09-22"
    )
    args = parser.parse_args()
    if ref.COMPOSE_PROJECT != "rb-research-20260922" or ref.REFERENCE_PORT != 13002:
        raise RuntimeError("study requires isolated project rb-research-20260922 on port 13002")
    if _hash(PROTOCOL) != EXPECTED_PROTOCOL_HASH:
        raise RuntimeError("frozen protocol hash changed")
    run_dir = (
        args.output_root / f"attempt-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{os.getpid()}"
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    if _git("status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("commit tracked source before live execution")
    untracked_required = [
        ROOT / "experiments/research_completion.py",
        ROOT / "experiments/prospective_cases.py",
        ROOT / "src/reality_bridge/prospective_comparison.py",
        ROOT / "src/reality_bridge/state_oracle.py",
    ]
    tracked = set(_git("ls-files").splitlines())
    if any(str(path.relative_to(ROOT)) not in tracked for path in untracked_required):
        raise RuntimeError(
            "study runner, cases, and oracle must be committed before live execution"
        )
    receipt: dict[str, Any] = {
        "status": "running",
        "source_commit": _git("rev-parse", "HEAD"),
        "dirty_tree_at_start": False,
        "protocol_sha256": _hash(PROTOCOL),
        "case_sha256": case_hash(),
        "case_module_sha256": _hash(ROOT / "experiments/prospective_cases.py"),
        "source_manifest_sha256": {path: _hash(ROOT / path) for path in SOURCE_FILES},
        "image": IMAGE,
        "architecture": "linux/arm64",
        "compose_project": ref.COMPOSE_PROJECT,
        "reference_port": ref.REFERENCE_PORT,
        "excluded_server_traffic": "Docker healthchecks and Compose infrastructure probes",
        "phase_ledger": {},
        "elapsed_s": None,
    }
    _write(run_dir / "receipt.json", receipt)
    started = time.monotonic()
    try:
        with _phase_meter("bootstrap", receipt, run_dir / "receipt.json"):
            bootstrap = ref.reset(with_seed=True)
            token = ref.token()
        receipt["bootstrap_timings"] = bootstrap
        receipt["running_reference_image"] = _running_reference_image()
        _write(run_dir / "receipt.json", receipt)

        # Previously exposed requalification only: seeded color mismatch.
        original = _new_emulator([])
        with _phase_meter("requalification", receipt, run_dir / "receipt.json"):
            reference_seed, simulator_seed, before = _snapshot_pair(original, token)
            exposed_color_action = _action("get_issue", "1")
            exposed_regression_action = _action("get_issue", "2")
            before_color = compare_responses(
                "get_issue",
                ref.step_reference(exposed_color_action, token),
                None,
                original.step(exposed_color_action),
                None,
            )
            before_regression = compare_responses(
                "get_issue",
                ref.step_reference(exposed_regression_action, token),
                None,
                original.step(exposed_regression_action),
                None,
            )
        receipt["requalification_before"] = asdict(before)
        receipt["exposed_requalification_before"] = {
            "color_counterexample": asdict(before_color),
            "previously_agreeing_regression": asdict(before_regression),
        }
        if (
            before.outcome != "diverge"
            or before_color.outcome != "diverge"
            or before_regression.outcome != "agree"
        ):
            raise RuntimeError(
                "known color counterexample or nonempty regression did not requalify"
            )
        # Stage only a development observation. The worker sees neither source tree nor evaluation cases.
        reference_color = next(
            label["color"] for label in reference_seed["labels"] if label["name"] == "bug"
        )
        simulator_color = next(
            label["color"] for label in simulator_seed["labels"] if label["name"] == "bug"
        )
        sandbox = run_sandboxed_repair(
            {
                "ref": {"name": "bug", "color": reference_color},
                "sim": {"name": "bug", "color": simulator_color},
            },
            ROOT / "experiments/sandbox_repair_worker.c",
            ROOT / "experiments/prospective_cases.py",
        )
        receipt["sandbox"] = asdict(sandbox)
        rules = [RepairRule(**rule) for rule in sandbox.rules]
        if not rules:
            raise RuntimeError("known color rule was not proposed")
        with _phase_meter("repair_promotion", receipt, run_dir / "receipt.json"):
            promoted = _new_emulator(rules)
            _, _, after = _snapshot_pair(promoted, token)
            after_color = compare_responses(
                "get_issue",
                ref.step_reference(exposed_color_action, token),
                None,
                promoted.step(exposed_color_action),
                None,
            )
            after_regression = compare_responses(
                "get_issue",
                ref.step_reference(exposed_regression_action, token),
                None,
                promoted.step(exposed_regression_action),
                None,
            )
        receipt["requalification_after"] = asdict(after)
        receipt["exposed_requalification_after"] = {
            "color_counterexample": asdict(after_color),
            "previously_agreeing_regression": asdict(after_regression),
        }
        if any(outcome.outcome != "agree" for outcome in (after, after_color, after_regression)):
            raise RuntimeError("bounded rule failed seed, counterexample or regression gate")
        _write(run_dir / "receipt.json", receipt)

        orders = {"targeted": TARGETED_ORDER}
        for seed in RANDOM_ORDER_SEEDS:
            shuffled = [case.case_id for case in DEV_CASES]
            random.Random(seed).shuffle(shuffled)
            orders[f"random_{seed}"] = tuple(shuffled)
        arms = {}
        for name, order in orders.items():
            arms[name] = _arm(order, token, rules, run_dir / f"arm-{name}.json")
            receipt["phase_ledger"][name] = arms[name]["requests"]
            _write(run_dir / "receipt.json", receipt)
            if arms[name]["status"] not in {
                "complete",
                "budget_censored",
                "bound_violation_censored",
            }:
                raise RuntimeError(f"discovery arm {name} failed: {arms[name]['status']}")
        receipt["discovery_comparisons"] = {}
        for seed in RANDOM_ORDER_SEEDS:
            random_arm = arms[f"random_{seed}"]
            cutoff = min(random_arm["requests"], arms["targeted"]["requests"])
            receipt["discovery_comparisons"][str(seed)] = {
                "shared_cutoff": cutoff,
                "random": _arm_summary(random_arm, cutoff),
                "targeted": _arm_summary(arms["targeted"], cutoff),
            }
        _write(run_dir / "receipt.json", receipt)

        # Discovery and the bounded rule are frozen before the new evaluation set is run.
        _write(
            run_dir / "pre_evaluation_freeze.json",
            {
                "case_sha256": case_hash(),
                "rules": [asdict(rule) for rule in rules],
                "arm_files": {name: _hash(run_dir / f"arm-{name}.json") for name in arms},
            },
        )
        evaluation = _phase_cases(
            "evaluation", EVAL_CASES, token, rules, run_dir / "evaluation.json"
        )
        receipt["phase_ledger"]["evaluation"] = evaluation["requests"]
        if evaluation["status"] != "complete":
            raise RuntimeError("evaluation setup failed")
        _write(run_dir / "receipt.json", receipt)

        selection: list[dict[str, Any]] = []
        policy_evaluation: list[dict[str, Any]] = []
        with _phase_meter(
            "policy", receipt, run_dir / "receipt.json", limit=POLICY_CAP
        ) as policy_meter:
            for destination, tasks in (
                (selection, SELECTION_TASKS),
                (policy_evaluation, EVALUATION_TASKS),
            ):
                for task in tasks:
                    for policy in POLICIES:
                        attempt_start = policy_meter.requests
                        try:
                            destination.append(
                                _policy_trial(task, policy, token, rules, policy_meter)
                            )
                        except Exception as exc:
                            _write(
                                run_dir / "policy-raw.json",
                                {
                                    "status": "interrupted",
                                    "selection": selection,
                                    "evaluation": policy_evaluation,
                                    "requests": policy_meter.requests,
                                    "interrupted_attempt": {
                                        "task": asdict(task),
                                        "policy": policy,
                                        "request_start": attempt_start,
                                        "requests_used": policy_meter.requests - attempt_start,
                                        "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                                    },
                                },
                            )
                            raise
                        _write(
                            run_dir / "policy-raw.json",
                            {
                                "status": "running",
                                "selection": selection,
                                "evaluation": policy_evaluation,
                                "requests": policy_meter.requests,
                            },
                        )
        policy_summary = summarize_policy(selection, policy_evaluation)
        _write(
            run_dir / "policy-raw.json",
            {
                "status": "complete",
                "selection": selection,
                "evaluation": policy_evaluation,
                "requests": policy_meter.requests,
                "hard_cap": POLICY_CAP,
            },
        )
        receipt["policy_summary"] = policy_summary
        receipt["status"] = (
            "bound_censored"
            if any(arm["status"] == "bound_violation_censored" for arm in arms.values())
            else "complete"
        )
    except Exception as exc:
        receipt["status"] = "infrastructure_or_machinery_failure"
        receipt["failure"] = {"type": type(exc).__name__, "message": str(exc)[:500]}
        raise
    finally:
        receipt["elapsed_s"] = round(time.monotonic() - started, 3)
        receipt["total_harness_requests"] = sum(receipt["phase_ledger"].values())
        _write(run_dir / "receipt.json", receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
