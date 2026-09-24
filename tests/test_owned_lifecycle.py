"""Owned reference startup must fail before affecting foreign resources."""

from __future__ import annotations

from pathlib import Path

import pytest

from reality_bridge import reference as ref
from reference import owned_lifecycle as owned


def _isolated_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    state = tmp_path / "owned-state"
    monkeypatch.setattr(ref, "STATE_DIR", state)
    monkeypatch.setattr(ref, "TOKEN_FILE", state / ".token")
    return state


def test_existing_project_is_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _isolated_state(monkeypatch, tmp_path)
    monkeypatch.setattr(ref, "COMPOSE_PROJECT", "rb-test-owned")
    monkeypatch.setattr(owned.platform, "machine", lambda: "arm64")
    calls: list[tuple[str, ...]] = []

    def fake_run(args: tuple[str, ...]) -> str:
        calls.append(args)
        return "foreign-container" if args[:3] == ("docker", "ps", "-aq") else "arm64"

    monkeypatch.setattr(owned, "_run", fake_run)
    with pytest.raises(ref.ReferenceError, match="already owns containers"):
        owned.preflight()
    assert not any("down" in command for command in calls)


def test_occupied_port_is_refused_before_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _isolated_state(monkeypatch, tmp_path)
    monkeypatch.setattr(ref, "COMPOSE_PROJECT", "rb-test-port")
    monkeypatch.setattr(owned.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(
        owned, "_run", lambda args: "arm64" if args[:3] == ("docker", "image", "inspect") else ""
    )

    class OccupiedSocket:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def bind(self, address):
            raise OSError("already bound")

    monkeypatch.setattr(owned.socket, "socket", lambda *args: OccupiedSocket())
    monkeypatch.setattr(ref, "REFERENCE_PORT", 13088)
    with pytest.raises(ref.ReferenceError, match="occupied"):
        owned.preflight()


def test_success_sweeps_only_started_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state = _isolated_state(monkeypatch, tmp_path)
    unrelated = tmp_path / "unrelated"
    unrelated.write_text("keep")
    monkeypatch.setattr(owned, "preflight", lambda: None)
    events: list[str] = []

    def start() -> None:
        events.append("up")
        state.mkdir()
        ref.TOKEN_FILE.write_text("synthetic")

    monkeypatch.setattr(ref, "up", start)
    monkeypatch.setattr(ref, "_compose", lambda *args: events.append(" ".join(args)))
    monkeypatch.setattr(owned.subprocess, "call", lambda *args, **kwargs: 0)
    assert owned.run_owned(("true",)) == 0
    assert events == ["up", "down -v"]
    assert not state.exists()
    assert unrelated.read_text() == "keep"


def test_failure_sweeps_only_started_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _isolated_state(monkeypatch, tmp_path)
    monkeypatch.setattr(owned, "preflight", lambda: None)
    events: list[str] = []
    monkeypatch.setattr(ref, "up", lambda: events.append("up"))
    monkeypatch.setattr(ref, "_compose", lambda *args: events.append(" ".join(args)))
    monkeypatch.setattr(owned.subprocess, "call", lambda *args, **kwargs: 7)
    assert owned.run_owned(("false",)) == 7
    assert events == ["up", "down -v"]


def test_failed_up_is_swept(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _isolated_state(monkeypatch, tmp_path)
    monkeypatch.setattr(owned, "preflight", lambda: None)
    events: list[str] = []

    def fail_up() -> None:
        events.append("up")
        raise ref.ReferenceError("injected failure")

    monkeypatch.setattr(ref, "up", fail_up)
    monkeypatch.setattr(ref, "_compose", lambda *args: events.append(" ".join(args)))
    with pytest.raises(ref.ReferenceError, match="injected failure"):
        owned.run_owned(("true",))
    assert events == ["up", "down -v"]
