"""One exposed current-emulator example using the existing full-state runner."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from experiments.prospective_cases import DEV_CASES
from experiments.research_completion import _running_reference_image, run_case
from reality_bridge import reference as ref


def run(output: Path, case_id: str = "D14") -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "status": "running",
        "scope": f"current repaired emulator on exposed {case_id} engineering case",
        "reference": _running_reference_image(),
        "rows": [],
        "requests": 0,
    }
    try:
        with ref.count_reference_calls(limit=40) as meter:
            ref.reset(with_seed=True)
            case = next(case for case in DEV_CASES if case.case_id == case_id)
            row = run_case(case, ref.token(), [], meter)
            result["rows"].append(row)
            result["requests"] = meter.requests
            result["status"] = "complete" if row["outcome"] == "agree" else "comparison_issue"
    except Exception as exc:  # noqa: BLE001 - retain explicit machinery failure
        result["status"] = "machinery_failure"
        result["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
    result["summary"] = {
        "status": result["status"],
        "requests": result["requests"],
        "outcomes": dict(Counter(row["outcome"] for row in result["rows"])),
        "scope": result["scope"],
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n")
    return result
