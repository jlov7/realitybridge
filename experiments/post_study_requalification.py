"""Bounded reference check of known defects after the measured study.

This deliberately reuses exposed cases. It cannot produce new holdout evidence
or change the frozen baseline result.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from experiments.prospective_cases import DEV_CASES, EVAL_CASES
from experiments.research_completion import (
    IMAGE,
    PROTOCOL,
    SOURCE_FILES,
    Goal,
    _git,
    _hash,
    _policy_trial,
    _running_reference_image,
    _write,
    run_case,
)
from reality_bridge import reference as ref
from reality_bridge.repair import RepairRule

BASELINE = (
    ROOT / "artifacts/research-completion-2026-09-22/attempt-20260922T182622Z-59359/receipt.json"
)
CASE_IDS = tuple(case.case_id for case in (*DEV_CASES, *EVAL_CASES))
CAP = 750


def main() -> int:
    if ref.COMPOSE_PROJECT != "rb-research-20260922" or ref.REFERENCE_PORT != 13002:
        raise RuntimeError("requalification requires the isolated project and port 13002")
    if _git("status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("commit current simulator before post-study reference requalification")
    if not BASELINE.is_file():
        raise FileNotFoundError("retained baseline receipt is required")
    baseline_bytes = BASELINE.read_bytes()
    baseline_hash = hashlib.sha256(baseline_bytes).hexdigest()
    baseline_receipt = json.loads(baseline_bytes)
    lookup = {case.case_id: case for case in (*DEV_CASES, *EVAL_CASES)}
    output = (
        ROOT
        / "artifacts/research-completion-2026-09-22"
        / (
            f"post-study-requalification-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{os.getpid()}.json"
        )
    )
    receipt: dict = {
        "status": "running",
        "classification": "post-study regression requalification of exposed cases",
        "baseline_receipt_sha256": baseline_hash,
        "baseline_source_commit": baseline_receipt["source_commit"],
        "current_source_commit": _git("rev-parse", "HEAD"),
        "source_manifest_sha256": {path: _hash(ROOT / path) for path in SOURCE_FILES},
        "protocol_sha256": _hash(PROTOCOL),
        "image": IMAGE,
        "running_reference_image": _running_reference_image(),
        "case_ids": CASE_IDS,
        "rows": [],
        "policy_p05": [],
        "requests": 0,
        "hard_cap": CAP,
    }
    _write(output, receipt)
    rules: list[RepairRule] = []  # Current public emulator includes the verified color rule.
    token = ref.token()
    try:
        with ref.count_reference_calls(limit=CAP) as meter:
            try:
                for case_id in CASE_IDS:
                    row = run_case(lookup[case_id], token, rules, meter)
                    receipt["rows"].append(row)
                    receipt["requests"] = meter.requests
                    _write(output, receipt)
                goal = Goal("P05", "label_present", 1, "p2-policy-attach", "778899")
                for policy in ("minimal", "inspect_first", "ensure_prerequisite"):
                    receipt["policy_p05"].append(_policy_trial(goal, policy, token, rules, meter))
                    receipt["requests"] = meter.requests
                    _write(output, receipt)
            finally:
                receipt["requests"] = meter.requests
                _write(output, receipt)
        expected = all(row["outcome"] == "agree" for row in receipt["rows"])
        policy_states = all(
            row["final_state_diagnostic"]["outcome"] == "agree" for row in receipt["policy_p05"]
        )
        receipt["status"] = "passed" if expected and policy_states else "failed_regressions"
        receipt["case_agreements"] = sum(row["outcome"] == "agree" for row in receipt["rows"])
        receipt["policy_final_state_agreements"] = sum(
            row["final_state_diagnostic"]["outcome"] == "agree" for row in receipt["policy_p05"]
        )
    except Exception as exc:
        receipt["status"] = "infrastructure_or_machinery_failure"
        receipt["failure"] = {"type": type(exc).__name__, "message": str(exc)[:300]}
        raise
    finally:
        _write(output, receipt)
    print(
        f"{receipt['status']}: {receipt['case_agreements']}/{len(CASE_IDS)} cases, "
        f"{receipt['policy_final_state_agreements']}/3 policy states, {receipt['requests']} HTTP requests"
    )
    print(output)
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
