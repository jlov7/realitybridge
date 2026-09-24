"""Shared fixtures.

`requires_reference_container` skips container-backed tests cleanly when Docker
or the pinned reference is not available, so a fresh clone gives a meaningful
result instead of an opaque connection error. Everything else in the suite is
offline-deterministic.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        compose = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            timeout=10,
            check=False,
        )
        daemon = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            timeout=10,
            check=False,
        )
        return compose.returncode == 0 and daemon.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


@pytest.fixture
def _reference_container_available() -> None:
    if _docker_available():
        return
    message = "requires a running Docker engine and pinned reference (reference/compose.yaml)"
    if os.environ.get("REALITYBRIDGE_REQUIRE_REFERENCE") == "1":
        pytest.fail(message)
    pytest.skip(message)


requires_reference_container = pytest.mark.usefixtures("_reference_container_available")
