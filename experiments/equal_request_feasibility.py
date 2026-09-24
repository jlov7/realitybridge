"""AI-authored equal-request-budget feasibility with two frozen case procedures.

Mutations live here, outside the oracle. Their known provenance is not
independent adjudication. Both comparators see the same captured trace inside
each arm, while the arms use different predeclared sequence inventories.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from experiments.ordinary_baseline import compare_case
from experiments.ordinary_baseline_study import _instrument_case
from experiments.research_completion import _snapshot_pair, _step
from reality_bridge import reference as ref
from reality_bridge.emulator import Emulator
from reality_bridge.state_oracle import LabelPairing


class WrongCreatedTitle(Emulator):
    def create_issue(
        self, repo: str, title: str, body: str = "", label_names: list[str] | None = None
    ) -> dict:
        return super().create_issue(
            repo, title + "-mutated" if title.startswith("c-") else title, body, label_names
        )


class IgnoredClose(Emulator):
    def edit_issue(
        self,
        repo: str,
        number: str,
        state: str | None = None,
        title: str | None = None,
        body: str | None = None,
    ) -> dict:
        return super().edit_issue(repo, number, "open" if state == "closed" else state, title, body)


class RemoveEveryDuplicate(Emulator):
    def remove_label(self, repo: str, number: str, label: str) -> dict:
        super().remove_label(repo, number, label)
        issue = self.issues[int(number)]
        for row in self._label_registry:
            if row.name == label:
                issue.labels.discard(row.id)
        return self._raw_issue(issue)


MUTANTS = {
    "created_title": WrongCreatedTitle,
    "ignored_close": IgnoredClose,
    "remove_every_duplicate": RemoveEveryDuplicate,
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _save(path: Path, value: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")
    temporary.replace(path)


def _run_one(case: dict, mutant: type[Emulator], token: str, meter: ref.ReferenceCallMeter) -> dict:
    start = meter.requests
    ref.soft_reset(token)
    candidate = mutant()
    candidate.reset()
    pairing = LabelPairing({}, {})
    reference_initial, simulator_initial, initial = _snapshot_pair(candidate, token, pairing)
    row = {
        "case_id": case["id"],
        "actions": case["actions"],
        "reference_initial": reference_initial,
        "simulator_initial": simulator_initial,
        "initial_comparison": asdict(initial),
        "steps": [],
    }
    if initial.outcome != "agree":
        row["outcome"] = "setup_failure"
    else:
        for action in case["actions"]:
            row["steps"].append(_step(candidate, token, action, meter, pairing))
        outcomes = {
            part["outcome"] for step in row["steps"] for part in (step["response"], step["state"])
        }
        row["outcome"] = (
            "undetermined"
            if "undetermined" in outcomes
            else "unsupported"
            if "unsupported" in outcomes
            else "diverge"
            if "diverge" in outcomes
            else "agree"
        )
    row["request_cost"] = meter.requests - start
    return row


def run(manifest_path: Path, output: Path) -> dict:
    if os.environ.get("REALITYBRIDGE_OWNED_REFERENCE") != "1":
        raise RuntimeError("owned reference lifecycle required")
    if output.exists():
        raise FileExistsError(output)
    manifest = json.loads(manifest_path.read_text())
    for name, digest in manifest["source_sha256"].items():
        if _sha(ROOT / name) != digest:
            raise RuntimeError(f"source hash mismatch: {name}")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    if commit != manifest["runtime_commit"]:
        raise RuntimeError("runtime commit mismatch")
    result = {
        "status": "running",
        "manifest_sha256": _sha(manifest_path),
        "runtime_commit": commit,
        "arms": {},
        "interrupted_trial": None,
        "author_time": "unavailable",
        "shared_setup_requests": 0,
        "adjudication": "mutation provenance and AI trace review only; no outside adjudicator",
    }
    _save(output, result)
    try:
        with ref.count_reference_calls(limit=20) as setup_meter:
            ref.reset(with_seed=True)
            token = ref.token()
            result["shared_setup_requests"] = setup_meter.requests
            _save(output, result)
        for arm in ("ordinary", "realitybridge"):
            started = time.monotonic()
            arm_result = {"status": "running", "rows": [], "requests": 0, "machine_seconds": 0}
            result["arms"][arm] = arm_result
            _save(output, result)
            with ref.count_reference_calls(limit=manifest["hard_request_cap_per_arm"]) as meter:
                for family in manifest["families"]:
                    for case in manifest["arms"][arm]:
                        # Admission keeps a partial case from being reported as a negative.
                        if manifest["hard_request_cap_per_arm"] - meter.requests < 10 + 5 * len(
                            case["actions"]
                        ):
                            arm_result["status"] = "budget_censored"
                            break
                        result["interrupted_trial"] = {
                            "arm": arm,
                            "family": family,
                            "case": case["id"],
                        }
                        _save(output, result)
                        row = _run_one(case, MUTANTS[family], token, meter)
                        arm_result["rows"].append(
                            {
                                "family": family,
                                "raw": row,
                                "ordinary": compare_case(row),
                                "instrument": _instrument_case(row),
                            }
                        )
                        arm_result["requests"] = meter.requests
                        result["interrupted_trial"] = None
                        _save(output, result)
                    if arm_result["status"] == "budget_censored":
                        break
                else:
                    arm_result["status"] = "complete"
                arm_result["requests"] = meter.requests
            arm_result["machine_seconds"] = round(time.monotonic() - started, 3)
            _save(output, result)
        result["status"] = (
            "complete"
            if all(a["status"] == "complete" for a in result["arms"].values())
            else "censored"
        )
    except Exception as exc:  # noqa: BLE001 - retain failed attempt
        result["status"] = "incomplete"
        result["error"] = f"{type(exc).__name__}: {str(exc)[:240]}"
    _save(output, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(args.manifest.resolve(), args.output.resolve())
    print(
        json.dumps(
            {
                "status": result["status"],
                "arms": {
                    k: {"status": v["status"], "requests": v["requests"], "rows": len(v["rows"])}
                    for k, v in result["arms"].items()
                },
            }
        )
    )
    raise SystemExit(0 if result["status"] == "complete" else 1)
