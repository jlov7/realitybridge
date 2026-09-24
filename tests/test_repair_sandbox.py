"""Enforced repair-worker boundary tests (macOS sandbox-exec)."""

from __future__ import annotations

import platform
from pathlib import Path

import pytest

from reality_bridge.repair_sandbox import run_sandboxed_repair

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "experiments" / "sandbox_repair_worker.c"
FORBIDDEN = ROOT / "experiments" / "prospective_cases.py"


def test_worker_executes_but_cannot_read_evaluation_module() -> None:
    if platform.system() != "Darwin":
        pytest.skip("sandbox-exec boundary is macOS-only; required macOS CI runs this test")
    counterexample = {
        "ref": {"name": "dev", "color": "abcdef"},
        "sim": {"name": "dev", "color": "#abcdef"},
    }
    receipt = run_sandboxed_repair(counterexample, WORKER, FORBIDDEN)
    assert receipt.allowed_execution
    assert receipt.forbidden_read_denied
    assert receipt.rules[0]["transform"] == "strip_leading_hash"
    assert len(receipt.worker_source_sha256) == 64
    assert len(receipt.worker_binary_sha256) == 64
    assert len(receipt.compiler_sha256) == 64
    assert all(len(value) == 64 for value in receipt.profile_sha256)
