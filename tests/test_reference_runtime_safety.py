"""Runtime guards for the reference adapter's network and cost boundary."""

from __future__ import annotations

import httpx
import pytest

from reality_bridge import reference


def test_reference_client_is_loopback_direct_and_does_not_follow_redirects() -> None:
    with reference.reference_client({}, 1.0) as client:
        assert str(client.base_url).startswith("http://127.0.0.1:")
        assert client.follow_redirects is False
        assert client.trust_env is False


def test_reference_call_meter_counts_actual_requests() -> None:
    class FakeClient:
        def request(self, method: str, url: str, **kwargs: object) -> str:
            return f"{method} {url}"

    with reference.count_reference_calls() as meter:
        assert reference.reference_request(FakeClient(), "GET", "/one") == "GET /one"  # type: ignore[arg-type]
        reference.reference_request(FakeClient(), "POST", "/two")  # type: ignore[arg-type]
    assert meter.requests == 2


def test_hard_reference_call_limit_refuses_request_before_send() -> None:
    class FakeClient:
        calls = 0

        def request(self, method: str, url: str, **kwargs: object) -> object:
            self.calls += 1
            return object()

    client = FakeClient()
    with reference.count_reference_calls(limit=1) as meter:
        reference.reference_request(client, "GET", "/first")  # type: ignore[arg-type]
        with pytest.raises(reference.ReferenceBudgetExceeded):
            reference.reference_request(client, "GET", "/blocked")  # type: ignore[arg-type]
    assert meter.requests == 1
    assert client.calls == 1


def test_transport_failure_becomes_undetermined_input(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args: object, **_kwargs: object) -> dict:
        raise httpx.ConnectError("synthetic")

    monkeypatch.setattr(reference, "_step_reference_dispatch", fail)
    with pytest.raises(reference.ReferenceStepError) as exc:
        reference.step_reference(
            {"op": "get_issue", "args": ["rbadmin", "spec-repo", "1"]}, "synthetic"
        )
    assert exc.value.status == 599
    assert exc.value.body == {"message": "ConnectError"}
