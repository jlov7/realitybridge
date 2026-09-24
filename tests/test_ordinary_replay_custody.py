"""Frozen source and raw receipts cannot be silently substituted."""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from experiments import replay_ordinary_baseline as replay


def test_changed_raw_receipt_fails_before_replay(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    for name in ("setup-failure.json", "amended-complete.json"):
        shutil.copy2(replay.EVIDENCE / name, tmp_path / name)
    amended = tmp_path / "amended-complete.json"
    amended.write_bytes(amended.read_bytes() + b"\n")
    monkeypatch.setattr(replay, "EVIDENCE", tmp_path)
    with pytest.raises(ValueError, match="raw receipt hash mismatch"):
        replay.replay()


def test_receipt_changed_after_verified_read_does_not_change_worker_input(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for name in ("setup-failure.json", "amended-complete.json"):
        shutil.copy2(replay.EVIDENCE / name, tmp_path / name)
    original_extract = replay._extract
    calls = 0

    def change_after_capture(
        archive_bytes: bytes, destination: Path, retained: dict[str, str]
    ) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            (tmp_path / "amended-complete.json").write_text("changed after verified read\n")
        original_extract(archive_bytes, destination, retained)

    monkeypatch.setattr(replay, "EVIDENCE", tmp_path)
    monkeypatch.setattr(replay, "_extract", change_after_capture)
    prior = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "artifacts/ordinary-baseline-2026-09-23/offline-replay.json"
        ).read_text()
    )
    assert replay.replay()["raw_replay"] == prior["raw_replay"]
    assert calls == 2


def test_changed_frozen_archive_fails_before_materialization(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    for name in (
        "PUBLIC-DERIVATION.json",
        "initial-public-a8e802d.tar.gz",
        "amendment1-public-d6f9280.tar.gz",
    ):
        shutil.copy2(replay.SNAPSHOTS / name, tmp_path / name)
    initial = tmp_path / "initial-public-a8e802d.tar.gz"
    initial.write_bytes(initial.read_bytes() + b"\n")
    monkeypatch.setattr(replay, "SNAPSHOTS", tmp_path)
    with pytest.raises(ValueError, match="source archive hash mismatch"):
        replay.replay()


def test_public_derivation_replays_same_raw_rows_and_excludes_internal_files() -> None:
    current = replay.replay()
    prior = json.loads((replay.EVIDENCE / "offline-replay.json").read_text())
    assert current["raw_replay"] == prior["raw_replay"]
    for version in replay.VERSIONS:
        with tarfile.open(replay.SNAPSHOTS / version[1], "r:gz") as stream:
            assert not ({member.name for member in stream} & replay.EXCLUDED_SNAPSHOT_PATHS)


def test_retained_source_tamper_fails_frozen_hash_even_with_reauthored_derivation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for version in replay.VERSIONS:
        shutil.copy2(replay.SNAPSHOTS / version[1], tmp_path / version[1])
    original = tmp_path / replay.VERSIONS[0][1]
    changed = tmp_path / "changed.tar.gz"
    source_path = "contracts/operations.yaml"
    with tarfile.open(original, "r:gz") as reader, tarfile.open(changed, "w:gz") as writer:
        for member in reader:
            extracted = reader.extractfile(member)
            assert extracted is not None
            data = extracted.read()
            if member.name == source_path:
                data += b"\n# tampered\n"
                member.size = len(data)
            writer.addfile(member, io.BytesIO(data))
    changed.replace(original)
    derivation = json.loads((replay.SNAPSHOTS / "PUBLIC-DERIVATION.json").read_text())
    derivation["versions"]["initial"]["public_archive_sha256"] = replay._sha(original)
    # Derivation was deliberately reauthored here; the original scientific manifest remains fixed.
    with tarfile.open(original, "r:gz") as stream:
        extracted = stream.extractfile(source_path)
        assert extracted is not None
        tampered = extracted.read()
    derivation["versions"]["initial"]["retained_member_sha256"][source_path] = hashlib.sha256(
        tampered
    ).hexdigest()
    derivation_path = tmp_path / "PUBLIC-DERIVATION.json"
    derivation_path.write_text(json.dumps(derivation, indent=2, sort_keys=True) + "\n")
    monkeypatch.setattr(replay, "SNAPSHOTS", tmp_path)
    monkeypatch.setattr(replay, "PUBLIC_DERIVATION_SHA256", replay._sha(derivation_path))
    changed_initial = (
        replay.VERSIONS[0][0],
        replay.VERSIONS[0][1],
        replay._sha(original),
        *replay.VERSIONS[0][3:],
    )
    monkeypatch.setattr(
        replay,
        "VERSIONS",
        (changed_initial, replay.VERSIONS[1]),
    )
    with pytest.raises(ValueError, match="frozen source mismatch: contracts/operations.yaml"):
        replay.replay()


def test_replay_validation_runs_with_optimized_python() -> None:
    result = subprocess.run(
        (
            sys.executable,
            "-O",
            "-c",
            "from experiments.replay_ordinary_baseline_worker import require; require(False, 'tampered row')",
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "ValueError: tampered row" in result.stderr
