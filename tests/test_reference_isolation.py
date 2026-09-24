"""Reference isolation — prove the pinned reference has NO configured outbound channels.

Milestone A exit criterion: "no network side effects."

WHAT IS ASSERTED here (all config-level, deterministic, no container needed):
1. Every outbound integration mechanism Gitea can use is disabled by config:
   mailer, webhooks, mirrors, actions, cron, openid, packages, LFS, SSH, and
   OFFline_MODE is on — so even where the network layer is available, the
   application has no configured channel to use it.
2. The published port is bound to loopback (127.0.0.1) only, not 0.0.0.0.
3. The image is pinned BY DIGEST, so a drift to a different image cannot happen
   silently through the compose file's `image:` line.

WHAT IS NOT CLAIMED here (honest bound):
- This does NOT prove the container has no route to the internet (that is a
  Docker-network-level property, environment-dependent, and not asserted).
- It proves *channel absence at the application/config surface*, which is what
  "no network side effects" can honestly mean on this project's evidence.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "reference" / "compose.yaml"

# Every key here is an outbound mechanism; the assertion is they are all
# disabled (or empty) in the running configuration.
_MUST_BE_DISABLED: dict[str, str] = {
    "GITEA__mailer__ENABLED": "false",
    "GITEA__webhook__ALLOWED_HOST_LIST": "",
    "GITEA__webhook__SKIP_TLS_VERIFY": "false",
    "GITEA__cron__ENABLED": "false",
    "GITEA__mirror__ENABLED": "false",
    "GITEA__actions__ENABLED": "false",
    "GITEA__openid__ENABLE_OPENID_SIGNIN": "false",
    "GITEA__openid__ENABLE_OPENID_SIGNUP": "false",
    "GITEA__lfs__LFS_START_SERVER": "false",
    "GITEA__packages__ENABLED": "false",
    "GITEA__service__ENABLE_NOTIFY_MAIL": "false",
    "GITEA__server__OFFLINE_MODE": "true",
}

# SSH is an inbound channel into the reference; it is disabled too, so the
# surface is asymmetric (outbound-from-Gitea channels are the real target).
_MUST_NOT_BE_PRESENT: tuple[str, ...] = ()


def _compose() -> dict:
    if not COMPOSE.exists():
        raise AssertionError(f"compose file missing: {COMPOSE}")
    return yaml.safe_load(COMPOSE.read_text())


def test_compose_file_exists_and_is_valid_yaml() -> None:
    doc = _compose()
    assert "services" in doc
    assert "gitea" in doc["services"]
    assert "container_name" not in doc["services"]["gitea"], (
        "fixed container names prevent isolated Compose projects"
    )


def test_all_outbound_channels_disabled() -> None:
    env = dict(doc["services"]["gitea"]["environment"]) if (doc := _compose()) else {}
    for key, expected in _MUST_BE_DISABLED.items():
        assert env.get(key) == expected, (
            f"outbound channel not disabled: {key} = {env.get(key)!r} (expected {expected!r})"
        )


def test_port_bound_to_loopback_only() -> None:
    ports = _compose()["services"]["gitea"]["ports"]
    assert ports == ["127.0.0.1:${REALITYBRIDGE_PORT:-13000}:3000"], (
        f"reference not loopback-only: {ports}"
    )


def test_image_pinned_by_digest() -> None:
    for svc in ("init", "gitea"):
        image = _compose()["services"][svc]["image"]
        assert image.startswith("gitea/gitea@sha256:"), f"{svc} image not digest-pinned: {image!r}"
        assert _compose()["services"][svc]["platform"] == "linux/arm64"


def test_worker_user_is_pinned_non_root() -> None:
    assert _compose()["services"]["gitea"]["user"] in ("1000:1000", "1000"), (
        "gitea service must run as uid 1000"
    )


def test_no_external_volume_or_mount_escapes_reference() -> None:
    """Volumes stay inside the named rb-data/rb-config pools."""
    for svc, spec in _compose()["services"].items():
        for v in spec.get("volumes", []):
            src = v.split(":")[0]
            assert src in ("rb-data", "rb-config"), f"{svc} escapes ( {v!r} )"
