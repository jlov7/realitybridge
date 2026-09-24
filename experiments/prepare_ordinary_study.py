"""Export an exact reviewed commit and materialize its measured emulator baseline."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare(commit: str, destination: Path) -> Path:
    if destination.exists():
        raise FileExistsError(destination)
    manifest = json.loads(
        (ROOT / "research/ordinary-baseline-2026-09-23/FROZEN-MANIFEST-A1.json").read_text()
    )
    destination.mkdir(parents=True)
    archive = destination / "frozen.tar"
    with archive.open("wb") as handle:
        subprocess.run(
            ("git", "archive", "--format=tar", commit), cwd=ROOT, check=True, stdout=handle
        )
    source = destination / "frozen-source"
    source.mkdir()
    with tarfile.open(archive) as stream:
        for member in stream.getmembers():
            path = Path(member.name)
            if member.issym() or member.islnk() or path.is_absolute() or ".." in path.parts:
                raise ValueError("unsafe archive member")
        stream.extractall(source)
    archive.unlink()
    if (
        json.loads(
            (source / "research/ordinary-baseline-2026-09-23/FROZEN-MANIFEST-A1.json").read_text()
        )
        != manifest
    ):
        raise ValueError("exported frozen manifest differs")
    baseline = destination / "study-baseline"
    subprocess.run(
        (sys.executable, "experiments/materialize_research_baseline.py", str(baseline)),
        cwd=source,
        check=True,
    )
    shutil.rmtree(source)
    return baseline


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    baseline = prepare(args.commit, args.destination.resolve())
    print(f"Exact study tree: {baseline}")
    print("Run from that tree with REALITYBRIDGE_FROZEN_ORIGIN_COMMIT set to the reviewed commit,")
    print("a unique REALITYBRIDGE_COMPOSE_PROJECT and free REALITYBRIDGE_PORT:")
    print("python reference/owned_lifecycle.py -- python experiments/ordinary_baseline_study.py")
    print("  --live --output /absolute/path/to/new-receipt.json")


if __name__ == "__main__":
    main()
