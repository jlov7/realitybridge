"""Disposable pinned reference (Gitea): lifecycle, admin, reset, snapshot.

The reference is a means, not the object of study. Its only job is to be
pinned, disposable, resettable, and loopback-isolated so that paired
differential trials begin from provably equivalent states.

Reset is `down -v` (named volumes removed) + fresh bring-up + admin + token.
Total reset wall time is measured and returned so the pilot can derive a hard
trial budget from it (build-plan G3) instead of assuming it.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]  # src/reality_bridge → repo root
COMPOSE_FILE = ROOT / "reference" / "compose.yaml"
_PROJECT_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")


class ReferenceError(RuntimeError):
    """The reference could not be brought to the required state."""


def _configured_project() -> str:
    project = os.environ.get("REALITYBRIDGE_COMPOSE_PROJECT", "realitybridge-reference")
    if not _PROJECT_PATTERN.fullmatch(project):
        raise ReferenceError("REALITYBRIDGE_COMPOSE_PROJECT must be a lowercase safe name")
    return project


def _configured_port() -> int:
    raw = os.environ.get("REALITYBRIDGE_PORT", "13000")
    try:
        port = int(raw)
    except ValueError as exc:
        raise ReferenceError("REALITYBRIDGE_PORT must be an integer") from exc
    if not 1024 <= port <= 65535:
        raise ReferenceError("REALITYBRIDGE_PORT must be between 1024 and 65535")
    return port


COMPOSE_PROJECT = _configured_project()
REFERENCE_PORT = _configured_port()
STATE_DIR = ROOT / "reference" / "state" / COMPOSE_PROJECT
TOKEN_FILE = STATE_DIR / ".token"

BASE_URL = f"http://127.0.0.1:{REFERENCE_PORT}/api/v1"
SERVICE = "gitea"  # compose exec targets the service name, not the container name
ADMIN_USER = "rbadmin"
ADMIN_PASS = "realitybridge-synthetic-pw-01"
ADMIN_EMAIL = "rbadmin@example.invalid"

_TTL_STEPS = 90  # healthcheck poll attempts
_TTL_STEP_S = 2.0


@dataclass(slots=True)
class ReferenceCallMeter:
    """Count actual HTTP requests made to the reference during one experiment."""

    requests: int = 0
    limit: int | None = None


class ReferenceBudgetExceeded(ReferenceError):
    """A hard request ceiling refused an exchange before it was sent."""


_CALL_METER: ContextVar[ReferenceCallMeter | None] = ContextVar(
    "reference_call_meter", default=None
)


@contextmanager
def count_reference_calls(limit: int | None = None) -> Iterator[ReferenceCallMeter]:
    if limit is not None and limit < 0:
        raise ValueError("reference-call limit must be nonnegative")
    meter = ReferenceCallMeter(limit=limit)
    reset_token = _CALL_METER.set(meter)
    try:
        yield meter
    finally:
        _CALL_METER.reset(reset_token)


def reference_request(client: httpx.Client, method: str, url: str, **kwargs: Any) -> httpx.Response:
    meter = _CALL_METER.get()
    if meter is not None:
        if meter.limit is not None and meter.requests >= meter.limit:
            raise ReferenceBudgetExceeded(
                f"reference-call limit {meter.limit} exhausted before {method} {url}"
            )
        meter.requests += 1
    return client.request(method, url, **kwargs)


def reference_client(headers: dict[str, str], timeout: float) -> httpx.Client:
    """Create a client that cannot use proxy environment variables or redirects."""
    return httpx.Client(
        base_url=BASE_URL,
        headers=headers,
        timeout=timeout,
        trust_env=False,
        follow_redirects=False,
    )


def _compose(*args: str) -> str:
    if not COMPOSE_FILE.is_file():
        raise ReferenceError(
            "live reference lifecycle requires a RealityBridge source checkout "
            "containing reference/compose.yaml"
        )
    out = subprocess.run(
        ["docker", "compose", "-p", COMPOSE_PROJECT, "-f", str(COMPOSE_FILE), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return out.stdout


def is_healthy() -> bool:
    container_id = _compose("ps", "-q", SERVICE).strip()
    if not container_id:
        return False
    out = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Health.Status}}", container_id],
        check=False,
        capture_output=True,
        text=True,
    )
    return out.returncode == 0 and out.stdout.strip() == "healthy"


def wait_healthy(timeout_s: float = 180.0) -> float:
    waited = 0.0
    while not is_healthy():
        if waited >= timeout_s:
            raise ReferenceError(f"reference not healthy after {timeout_s:.0f}s")
        time.sleep(_TTL_STEP_S)
        waited += _TTL_STEP_S
    return waited


def up() -> float:
    """Start the reference stack from its current state; return seconds to healthy."""
    _compose("up", "-d")
    return wait_healthy()


def _reset_state() -> float:
    _compose("down", "-v", "--remove-orphans")
    start = time.monotonic()
    _compose("up", "-d")
    return start  # caller computes elapsed


def create_admin_and_token() -> str:
    """Create the synthetic admin and an API token; return the token."""
    _compose(
        "exec",
        "-T",
        SERVICE,
        "gitea",
        "admin",
        "user",
        "create",
        "--username",
        ADMIN_USER,
        "--password",
        ADMIN_PASS,
        "--email",
        ADMIN_EMAIL,
        "--admin",
        "--must-change-password=false",
    )
    out = _compose(
        "exec",
        "-T",
        SERVICE,
        "gitea",
        "admin",
        "user",
        "generate-access-token",
        "--username",
        ADMIN_USER,
        "--token-name",
        "rb-synthetic",
        "--scopes",
        "all",
        "--raw",
    )
    token = out.strip().splitlines()[-1]
    if not token or " " in token:
        raise ReferenceError("token minting returned an unexpected value")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(token)
    TOKEN_FILE.chmod(0o600)
    return token


def token() -> str:
    """Current admin token, minting it if absent."""
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    return create_admin_and_token()


class ReferenceStepError(RuntimeError):
    """A step against the real reference returned a non-2xx response."""

    def __init__(self, status: int, body: object) -> None:
        super().__init__(f"reference returned {status}")
        self.status = status
        self.body = body


def step_reference(action: dict, tok: str | None = None) -> dict:
    """Drive one action dict (same contract as `emulator.step`) against the
    REAL reference application via its API. Returns a raw response dict whose
    shape the shared projection consumes.

    Raises ReferenceStepError on non-2xx so the runner can classify it into the
    error taxonomy without importing simulator transition logic.
    """
    auth_header = {"Authorization": f"token {tok or token()}"}
    op, args = action["op"], action["args"]
    owner, repo, *rest = args
    try:
        return _step_reference_dispatch(auth_header, op, owner, repo, rest)
    except httpx.HTTPStatusError as exc:
        try:
            body = exc.response.json()
        except ValueError:
            body = {"message": exc.response.text[:200]}
        raise ReferenceStepError(exc.response.status_code, body) from exc
    except httpx.TransportError as exc:
        raise ReferenceStepError(599, {"message": type(exc).__name__}) from exc


def _step_reference_dispatch(
    auth_header: dict[str, str], op: str, owner: str, repo: str, rest: list[str]
) -> dict:
    """Perform the action against the real reference; non-2xx → HTTPStatusError.

    Separated so `step_reference` can wrap the WHOLE exchange — including
    interim `raise_for_status()` calls like the label-id resolution inside
    remove_label — in one classification boundary. A 404 on an interim call is
    still a `ReferenceStepError`, never a raw exception.
    """
    with reference_client(auth_header, 30.0) as c:
        if op == "create_issue":
            resp = reference_request(
                c, "POST", f"/repos/{owner}/{repo}/issues", json={"title": rest[0]}
            )
        elif op == "get_issue":
            resp = reference_request(c, "GET", f"/repos/{owner}/{repo}/issues/{rest[0]}")
        elif op == "edit_issue":
            resp = reference_request(
                c, "PATCH", f"/repos/{owner}/{repo}/issues/{rest[0]}", json={"state": rest[1]}
            )
        elif op == "add_label":
            resp = reference_request(
                c,
                "POST",
                f"/repos/{owner}/{repo}/issues/{rest[0]}/labels",
                json={"labels": [rest[1]]},
            )
        elif op == "remove_label":
            label = (
                reference_request(c, "GET", f"/repos/{owner}/{repo}/labels")
                .raise_for_status()
                .json()
            )
            label_id = next((l["id"] for l in label if l["name"] == rest[1]), None)
            if label_id is None:
                raise ReferenceStepError(404, {"message": f"no label named {rest[1]!r}"})
            reference_request(
                c, "DELETE", f"/repos/{owner}/{repo}/issues/{rest[0]}/labels/{label_id}"
            ).raise_for_status()
            # read back: a DELETE returns 204, so fetch the post-state for comparison
            resp = reference_request(c, "GET", f"/repos/{owner}/{repo}/issues/{rest[0]}")
        elif op == "create_label":
            resp = reference_request(
                c,
                "POST",
                f"/repos/{owner}/{repo}/labels",
                json={"name": rest[0], "color": rest[1]},
            )
        else:
            raise ReferenceStepError(400, {"message": f"unsupported op {op}"})
        resp.raise_for_status()
        return resp.json()


def reset(with_seed: bool = False) -> dict[str, float]:
    """Full reset: wipe volumes, fresh bring-up, admin+token, optional seed.

    Returns timing breakdown {down_s, healthy_s, admin_s, seed_s, total_s}.
    Every number here is retained evidence for the trial-budget decision.
    """
    timings: dict[str, float] = {}
    t0 = time.monotonic()
    _compose("down", "-v", "--remove-orphans")
    timings["down_s"] = time.monotonic() - t0

    t0 = time.monotonic()
    _compose("up", "-d")
    wait_healthy()
    timings["healthy_s"] = time.monotonic() - t0

    t0 = time.monotonic()
    tok = create_admin_and_token()
    timings["admin_s"] = time.monotonic() - t0

    t0 = time.monotonic()
    if with_seed:
        from reference.seed import seed_reference

        seed_reference(tok)
    timings["seed_s"] = time.monotonic() - t0

    timings["total_s"] = sum(timings.values())
    return timings


def soft_reset(tok: str | None = None) -> dict[str, float]:
    """API-level reset: delete the spec repo and re-seed. No Docker involvement.

    The differential loop MUST use this per trial and per shrink probe; the
    full container `reset()` under repeated per-probe use wedges Docker. Deleting
    the repo removes issues+labels; `seed_reference` recreates the identical
    seeded state, so soft reset is deterministic.

    Returns {delete_s, seed_s, total_s}.
    """
    auth = {"Authorization": f"token {tok or token()}"}
    from reference.seed import ADMIN_USER, REPO, seed_reference

    timings: dict[str, float] = {}
    t0 = time.monotonic()
    with reference_client(auth, 15.0) as c:
        resp = reference_request(c, "DELETE", f"/repos/{ADMIN_USER}/{REPO}")
        if resp.status_code not in (204, 404):
            resp.raise_for_status()
        timings["delete_s"] = time.monotonic() - t0

        t0 = time.monotonic()
        seed_reference(tok or token())
        timings["seed_s"] = time.monotonic() - t0

    timings["total_s"] = sum(timings.values())
    return timings


def snapshot(tok: str | None = None) -> dict[str, list[tuple[str, ...]]]:
    """Observable state projection for determinism checks.

    Sorted tuples only, so comparison is stable. This is deliberately a tiny
    projection: repos, issues (by repo, number, title, state), labels.
    """
    auth = {"Authorization": f"token {tok or token()}"}
    with reference_client(auth, 15.0) as c:
        repos = reference_request(c, "GET", "/user/repos?limit=50").raise_for_status().json()
        repo_names = sorted((r["owner"]["login"], r["name"]) for r in repos)
        issues: list[tuple[str, ...]] = []
        labels: list[tuple[str, ...]] = []
        for owner, name in repo_names:
            iss = (
                reference_request(c, "GET", f"/repos/{owner}/{name}/issues?state=all&limit=200")
                .raise_for_status()
                .json()
            )
            for i in iss:
                issues.append((owner, name, i["number"], i["title"], i["state"]))
            lab = (
                reference_request(c, "GET", f"/repos/{owner}/{name}/labels?limit=50")
                .raise_for_status()
                .json()
            )
            for l in lab:
                labels.append((owner, name, l["name"], l["color"]))
    return {"repos": repo_names, "issues": sorted(issues), "labels": sorted(labels)}


def export_declared_state(tok: str | None = None, page_size: int = 50) -> dict[str, list[dict]]:
    """Read the complete bounded issue/label domain through paginated APIs."""
    if not 1 <= page_size <= 50:
        raise ValueError("page_size must be between 1 and 50")
    auth = {"Authorization": f"token {tok or token()}"}
    collections: dict[str, list[dict]] = {"issues": [], "labels": []}
    endpoints = {
        "issues": f"/repos/{ADMIN_USER}/spec-repo/issues?state=all",
        "labels": f"/repos/{ADMIN_USER}/spec-repo/labels",
    }
    try:
        with reference_client(auth, 15.0) as client:
            for kind, endpoint in endpoints.items():
                page = 1
                while True:
                    separator = "&" if "?" in endpoint else "?"
                    response = reference_request(
                        client,
                        "GET",
                        f"{endpoint}{separator}limit={page_size}&page={page}",
                    )
                    response.raise_for_status()
                    rows = response.json()
                    if not isinstance(rows, list):
                        raise ReferenceStepError(599, {"message": f"{kind} list was not JSON list"})
                    collections[kind].extend(rows)
                    if len(rows) < page_size:
                        break
                    page += 1
    except httpx.HTTPStatusError as exc:
        try:
            body = exc.response.json()
        except ValueError:
            body = {"message": exc.response.text[:200]}
        raise ReferenceStepError(exc.response.status_code, body) from exc
    except httpx.TransportError as exc:
        raise ReferenceStepError(599, {"message": type(exc).__name__}) from exc
    return collections
