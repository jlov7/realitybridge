"""Deterministic synthetic seed for the reference.

Synthetic only: no real users, no real data, `.invalid` email. Seeding assumes
a freshly reset reference (no admin exists), which the lifecycle adapter
guarantees. Determinism here means: the same seed run on the same version
produces observably identical state.
"""

from __future__ import annotations

from reality_bridge.reference import ADMIN_USER, reference_client, reference_request

REPO = "spec-repo"
LABELS = [
    {"name": "bug", "color": "#d73a4a"},
    {"name": "ui", "color": "#0e8a16"},
    {"name": "api", "color": "#6f42c1"},
]
ISSUES = [
    {"title": "issue-one", "body": "synthetic first issue", "labels": ["bug"]},
    {"title": "issue-two", "body": "synthetic second issue", "labels": []},
]


def seed_reference(tok: str) -> None:
    """Create the synthetic repo, labels and issues via the real API."""
    auth = {"Authorization": f"token {tok}"}
    with reference_client(auth, 30.0) as c:
        reference_request(
            c,
            "POST",
            "/user/repos",
            json={"name": REPO, "auto_init": False, "private": True},
        ).raise_for_status()

        for label in LABELS:
            reference_request(
                c, "POST", f"/repos/{ADMIN_USER}/{REPO}/labels", json=label
            ).raise_for_status()

        label_by_name = {l["name"]: l for l in LABELS}
        for issue in ISSUES:
            resp = reference_request(
                c,
                "POST",
                f"/repos/{ADMIN_USER}/{REPO}/issues",
                json={"title": issue["title"], "body": issue["body"]},
            )
            resp.raise_for_status()
            index = resp.json()["number"]
            for name in issue["labels"]:
                reference_request(
                    c,
                    "POST",
                    f"/repos/{ADMIN_USER}/{REPO}/issues/{index}/labels",
                    json={"labels": [label_by_name[name]["name"]]},
                ).raise_for_status()


def seeded_state(tok: str) -> dict[str, int]:
    """Count summary used by tests to assert the seed landed.

    Not a snapshot — see reality_bridge.reference.snapshot for that.
    """
    auth = {"Authorization": f"token {tok}"}
    with reference_client(auth, 30.0) as c:
        issues = (
            reference_request(c, "GET", f"/repos/{ADMIN_USER}/{REPO}/issues?state=all&limit=200")
            .raise_for_status()
            .json()
        )
        labels = (
            reference_request(c, "GET", f"/repos/{ADMIN_USER}/{REPO}/labels?limit=50")
            .raise_for_status()
            .json()
        )
    return {"issues": len(issues), "labels": len(labels), "repo": 1}


if __name__ == "__main__":
    from reality_bridge.reference import token

    seed_reference(token())
