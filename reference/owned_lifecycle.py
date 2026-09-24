"""Fail-closed, source-checkout lifecycle for one disposable reference project."""

from __future__ import annotations

import argparse
import os
import platform
import socket
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reality_bridge import reference as ref

IMAGE = "gitea/gitea@sha256:0489485c8afcb367a1c8066e081ec47d1592258dcbf729875e8bf4aa0b84a7c9"


def _run(args: Sequence[str]) -> str:
    try:
        return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ref.ReferenceError(
            f"reference preflight or lifecycle command failed: {' '.join(args)}: {exc}"
        ) from exc


def preflight() -> None:
    """Refuse to borrow resources or download an uninspected reference image."""
    project = ref.COMPOSE_PROJECT
    if project == "realitybridge-reference":
        raise ref.ReferenceError("set an explicit unique REALITYBRIDGE_COMPOSE_PROJECT")
    if platform.machine().lower() not in {"arm64", "aarch64"}:
        raise ref.ReferenceError("pinned reference requires an ARM64 host")
    _run(("docker", "info", "--format", "{{.ServerVersion}}"))
    architecture = _run(("docker", "image", "inspect", IMAGE, "--format", "{{.Architecture}}"))
    if architecture != "arm64":
        raise ref.ReferenceError(
            f"pinned reference image architecture is {architecture!r}, expected arm64"
        )
    filters = ("--filter", f"label=com.docker.compose.project={project}")
    for kind, args in (
        ("containers", ("docker", "ps", "-aq", *filters)),
        ("volumes", ("docker", "volume", "ls", "-q", *filters)),
        ("networks", ("docker", "network", "ls", "-q", *filters)),
    ):
        if _run(args):
            raise ref.ReferenceError(
                f"Compose project {project!r} already owns {kind}; refusing reuse or cleanup"
            )
    if ref.STATE_DIR.exists():
        raise ref.ReferenceError(f"reference state path already exists: {ref.STATE_DIR}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", ref.REFERENCE_PORT))
        except OSError as exc:
            raise ref.ReferenceError(f"loopback port {ref.REFERENCE_PORT} is occupied") from exc


def run_owned(command: Sequence[str]) -> int:
    preflight()
    created = False
    try:
        # Mark the project owned before up: even a partial failed up is ours to sweep.
        created = True
        ref.up()
        return subprocess.call(
            command, cwd=ROOT, env={**os.environ, "REALITYBRIDGE_OWNED_REFERENCE": "1"}
        )
    finally:
        if created:
            try:
                ref._compose("down", "-v")
            finally:
                if ref.TOKEN_FILE.exists():
                    ref.TOKEN_FILE.unlink()
                if ref.STATE_DIR.exists() and not any(ref.STATE_DIR.iterdir()):
                    ref.STATE_DIR.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("provide a command after --")
    return run_owned(command)


if __name__ == "__main__":
    raise SystemExit(main())
