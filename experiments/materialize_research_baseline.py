"""Make a standalone local checkout of the measured pre-fix simulator.

The retained prospective evidence was produced by the source at 19b2b47.
This helper copies tracked study files into a new directory and replaces only
the fixed emulator with its exact, byte-preserved research-baseline source.
It creates a local commit so the frozen runner's clean-source guard applies.
It creates no remote and does not start Docker or execute the study.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "experiments/research_baseline_emulator_19b2b47.py"
BASELINE_SHA256 = "61b81d7b4f5c97a1116855fbb93c422d772d9342c5503c1f84b7bd659f3c02ac"
BASELINE_ORACLE = ROOT / "experiments/research_baseline_state_oracle_5c68518.py"
BASELINE_ORACLE_SHA256 = "5c68518742ce7a8fac518b95c770b03dbe08dcc7f8d5baaff6bacfbf93634e9b"
BASELINE_STUDY = ROOT / "experiments/research_baseline_research_completion_19b2b47.py"
BASELINE_STUDY_SHA256 = "5c5c4c1d138511d6b7126d3e8d48104397db53b86b0d65526787c61583ece2d3"
COPY_DIRECTORIES = ("src", "experiments", "reference", "contracts", "docs", "research")
COPY_FILES = ("pyproject.toml", "uv.lock", ".gitignore", "README.md", "LICENSE")


def materialize(destination: Path) -> str:
    if destination.exists():
        raise FileExistsError(f"destination already exists: {destination}")
    if hashlib.sha256(BASELINE.read_bytes()).hexdigest() != BASELINE_SHA256:
        raise ValueError("research-baseline source hash mismatch")
    if hashlib.sha256(BASELINE_ORACLE.read_bytes()).hexdigest() != BASELINE_ORACLE_SHA256:
        raise ValueError("research-baseline state oracle hash mismatch")
    if hashlib.sha256(BASELINE_STUDY.read_bytes()).hexdigest() != BASELINE_STUDY_SHA256:
        raise ValueError("research-baseline study source hash mismatch")
    destination.mkdir(parents=True)
    for dirname in COPY_DIRECTORIES:
        shutil.copytree(
            ROOT / dirname,
            destination / dirname,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "state", ".pytest_cache"),
        )
    for filename in COPY_FILES:
        shutil.copy2(ROOT / filename, destination / filename)
    shutil.copy2(BASELINE, destination / "src/reality_bridge/emulator.py")
    shutil.copy2(BASELINE_ORACLE, destination / "src/reality_bridge/state_oracle.py")
    shutil.copy2(BASELINE_STUDY, destination / "experiments/research_completion.py")
    for args in (
        ("git", "init", "-q"),
        ("git", "add", "-A"),
        (
            "git",
            "-c",
            "user.name=RealityBridge local reproduction",
            "-c",
            "user.email=reproduction@example.invalid",
            "commit",
            "-q",
            "-m",
            "research baseline source",
        ),
    ):
        subprocess.run(args, cwd=destination, check=True, capture_output=True, text=True)
    return subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=destination,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    commit = materialize(args.destination.resolve())
    print(f"materialized baseline at {args.destination.resolve()} commit {commit}")
    print("Use the original project's Python environment with PYTHONPATH=src:. to run")
    print("experiments/reproduce_research_completion.py on the retained attempt directory.")
    print("For a fresh baseline study, set REALITYBRIDGE_COMPOSE_PROJECT=rb-research-20260922")
    print("and REALITYBRIDGE_PORT=13002, then run experiments/research_completion.py.")


if __name__ == "__main__":
    main()
