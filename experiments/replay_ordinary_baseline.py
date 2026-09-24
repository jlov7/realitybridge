"""History-free source/receipt custody and raw-row replay for the A1 study."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = ROOT / "research/ordinary-baseline-2026-09-23/snapshots"
EVIDENCE = ROOT / "artifacts/ordinary-baseline-2026-09-23"
VERSIONS = (
    (
        "initial",
        "initial-public-a8e802d.tar.gz",
        "9bc9b497b49096c38a9fd1aec94a289e7a502a4b4e04acbc77292f8e5f1311c4",
        "initial-a8e802d.tar.gz",
        "95736419681f78d82826788169dd6c21d3d68c12f6b9040d36c7fe065653606c",
        "FROZEN-MANIFEST.json",
        "2223692630f2f28c4588c50c98c5c388c15a63a1f75586678ba6d2170914967c",
    ),
    (
        "amendment1",
        "amendment1-public-d6f9280.tar.gz",
        "d5375aba1c24820ab8198afb7b25cc42d61023f55bd5b09c08d1eab0da0c1362",
        "amendment1-d6f9280.tar.gz",
        "e6e4ad1505e1cd942b0d1aed019d469dba481cc656cef885c090044ca6e87dec",
        "FROZEN-MANIFEST-A1.json",
        "78e189e1bc236fa7008021c8f8268b00f28690c39216dd921f9ef97fb8cc2b08",
    ),
)
PUBLIC_DERIVATION_SHA256 = "2f095c65b65d89bc547ccf573024ff340c444bd28195b221ca10f9af8110173a"
EXCLUDED_SNAPSHOT_PATHS = {
    "AGENTS.md",
    "CONTRIBUTING.md",
    "Planning/BUILD-PLAN.md",
    "STATUS.md",
    "artifacts/evidence/.gitkeep",
    "artifacts/evidence/repo-publication-gate.md",
    "artifacts/research-completion-2026-09-22/CLEANUP-RECEIPT.md",
    "docs/audit-2026-09-22/README.md",
}
# The historical materializer copies AGENTS.md, which was removed from the
# shipped snapshots because it contained private workflow instructions.
# This inert file exists only in the temporary extraction, after source checks.
PUBLIC_REPLAY_COMPATIBILITY = b"# Public replay compatibility file; no instructions.\n"
FIRST_SHA256 = "b7f68cff674ddf6de226ea8a2c3b2e6189c824121a1d6dd227a36cfc73f1cc30"
AMENDED_SHA256 = "a0ae0f56ff2cc8e71a557a277b4694b026c5d802564be7a0245e22338d61a8b9"
MEASURED_EMULATOR_SHA256 = "61b81d7b4f5c97a1116855fbb93c422d772d9342c5503c1f84b7bd659f3c02ac"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _extract(archive_bytes: bytes, destination: Path, retained: dict[str, str]) -> None:
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as stream:
        members = stream.getmembers()
        if len(members) != len(retained) or {m.name for m in members} != set(retained):
            raise ValueError("public snapshot member inventory mismatch")
        for member in members:
            relative = Path(member.name)
            if not member.isfile() or relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"unsafe snapshot member: {member.name}")
            if member.name in EXCLUDED_SNAPSHOT_PATHS:
                raise ValueError(f"excluded snapshot member: {member.name}")
            extracted = stream.extractfile(member)
            if extracted is None:
                raise ValueError(f"unreadable snapshot member: {member.name}")
            data = extracted.read()
            if hashlib.sha256(data).hexdigest() != retained[member.name]:
                raise ValueError(f"public snapshot retained member mismatch: {member.name}")
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)


def replay() -> dict[str, Any]:
    derivation_bytes = (SNAPSHOTS / "PUBLIC-DERIVATION.json").read_bytes()
    if hashlib.sha256(derivation_bytes).hexdigest() != PUBLIC_DERIVATION_SHA256:
        raise ValueError("public derivation manifest hash mismatch")
    derivation = json.loads(derivation_bytes)
    if (
        derivation["schema"] != "realitybridge-public-snapshot-derivation-v1"
        or set(derivation["excluded_paths"]) != EXCLUDED_SNAPSHOT_PATHS
        or set(derivation["versions"]) != {version[0] for version in VERSIONS}
    ):
        raise ValueError("public derivation manifest inventory mismatch")
    first = EVIDENCE / "setup-failure.json"
    amended = EVIDENCE / "amended-complete.json"
    first_bytes = first.read_bytes()
    amended_bytes = amended.read_bytes()
    if (
        hashlib.sha256(first_bytes).hexdigest() != FIRST_SHA256
        or hashlib.sha256(amended_bytes).hexdigest() != AMENDED_SHA256
    ):
        raise ValueError("first or amended raw receipt hash mismatch")
    with tempfile.TemporaryDirectory(prefix="rb-ordinary-replay-") as temporary:
        base = Path(temporary)
        verified_receipts = base / "verified-receipts"
        verified_receipts.mkdir()
        first_verified = verified_receipts / first.name
        amended_verified = verified_receipts / amended.name
        first_verified.write_bytes(first_bytes)
        amended_verified.write_bytes(amended_bytes)
        checked: dict[str, Any] = {}
        materialized: dict[str, Path] = {}
        source_manifests: dict[str, dict[str, str]] = {}
        for (
            name,
            archive_name,
            archive_sha,
            original_name,
            original_sha,
            manifest_name,
            manifest_sha,
        ) in VERSIONS:
            declared = derivation["versions"][name]
            if (
                declared["public_archive"] != archive_name
                or declared["public_archive_sha256"] != archive_sha
                or declared["original_archive"] != original_name
                or declared["original_archive_sha256"] != original_sha
            ):
                raise ValueError(f"{name} public derivation binding mismatch")
            archive = SNAPSHOTS / archive_name
            archive_bytes = archive.read_bytes()
            if hashlib.sha256(archive_bytes).hexdigest() != archive_sha:
                raise ValueError(f"{name} public source archive hash mismatch")
            source = base / name / "source"
            source.mkdir(parents=True)
            _extract(archive_bytes, source, declared["retained_member_sha256"])
            manifest_path = source / "research/ordinary-baseline-2026-09-23" / manifest_name
            manifest_bytes = manifest_path.read_bytes()
            if hashlib.sha256(manifest_bytes).hexdigest() != manifest_sha:
                raise ValueError(f"{name} frozen manifest hash mismatch")
            manifest = json.loads(manifest_bytes)
            source_manifests[name] = manifest["source_sha256"]
            for relative, expected in manifest["source_sha256"].items():
                if _sha(source / relative) != expected:
                    raise ValueError(f"{name} frozen source mismatch: {relative}")
            if (source / "AGENTS.md").exists():
                raise ValueError(f"{name} historical private instructions present")
            (source / "AGENTS.md").write_bytes(PUBLIC_REPLAY_COMPATIBILITY)
            target = base / name / "measured-source"
            subprocess.run(
                (
                    sys.executable,
                    str(source / "experiments/materialize_research_baseline.py"),
                    str(target),
                ),
                cwd=source,
                capture_output=True,
                text=True,
                check=True,
            )
            for relative, expected in manifest["source_sha256"].items():
                actual_expected = (
                    MEASURED_EMULATOR_SHA256
                    if relative == "src/reality_bridge/emulator.py"
                    else expected
                )
                if _sha(target / relative) != actual_expected:
                    raise ValueError(f"{name} materialized source mismatch: {relative}")
            if subprocess.run(
                ("git", "status", "--porcelain"),
                cwd=target,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip():
                raise ValueError(f"{name} materialized source is dirty")
            checked[name] = {
                "public_archive_sha256": archive_sha,
                "original_private_archive_sha256": original_sha,
                "manifest_sha256": manifest_sha,
                "source_files_verified": len(manifest["source_sha256"]),
                "measured_emulator_sha256": _sha(target / "src/reality_bridge/emulator.py"),
            }
            materialized[name] = target
        raw = json.loads(amended_bytes)
        if raw["frozen_manifest_sha256"] != checked["amendment1"]["manifest_sha256"]:
            raise ValueError("amended receipt manifest binding mismatch")
        if raw["frozen_source_sha256"] != source_manifests["amendment1"]:
            raise ValueError("amended receipt source binding mismatch")
        for relative, expected in raw["source_hashes"].items():
            if _sha(materialized["amendment1"] / relative) != expected:
                raise ValueError(f"amended receipt actual source mismatch: {relative}")
        source = materialized["amendment1"]
        env = {**os.environ, "PYTHONPATH": f"{source / 'src'}:{source}"}
        proc = subprocess.run(
            (
                sys.executable,
                str(ROOT / "experiments/replay_ordinary_baseline_worker.py"),
                str(first_verified),
                str(amended_verified),
            ),
            cwd=source,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        return {
            "status": "reproduced",
            "public_derivation_manifest_sha256": PUBLIC_DERIVATION_SHA256,
            "temporary_compatibility_file_sha256": hashlib.sha256(
                PUBLIC_REPLAY_COMPATIBILITY
            ).hexdigest(),
            "source_snapshots": checked,
            "raw_replay": json.loads(proc.stdout),
            "claim_limit": "same captured traces; no new reference calls or independent human validation",
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = replay()
    if args.output:
        if args.output.exists():
            raise FileExistsError(args.output)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
