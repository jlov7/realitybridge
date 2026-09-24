"""Hand-coded documentation-based emulator for the six issue/label ops.

Deliberately built from `contracts/operations.yaml` and `contracts/observation.yaml`
— the API documentation — NOT by matching the reference application. If this
emulator diverges from real Gitea, that divergence is a finding, not a bug in
the harness. "Matching a bug in the reference establishes fidelity to that
version — not normative correctness."

`reset(seed)` and `step(action) -> raw_observation` follow the repository
contract (proposed interface): step returns a RAW-shaped dict close enough that
the SAME projection consumed for the reference applies to the emulator. The
evaluator must never import emulator transition logic.

Deliberate simplifications (documented; each is a candidate divergence):
1. Colors stored verbatim as given (#d73a4a) — Gitea may normalize them.
2. Issue numbers start at 1 and increment per repo — mirrors a fresh seed.
3. No permission model (every call authorized) — the reference enforces this.
4. Labels are a set: adding an existing label is a documented no-op; removing a
   label not present is 404 — per contracts/operations.yaml, to be checked.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _Issue:
    number: int
    title: str
    body: str = ""
    state: str = "open"
    closed_at: str | None = None
    labels: set[str] = field(default_factory=set)
    created_at: str = "2000-01-01T00:00:00Z"
    updated_at: str = "2000-01-01T00:00:00Z"


@dataclass
class _Label:
    name: str
    color: str


class EmulatorError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


class Emulator:
    """Pure-python stand-in for the reference application."""

    def __init__(self) -> None:
        self.issues: dict[int, _Issue] = {}
        self.labels: dict[str, _Label] = {}
        self._next_number = 1

    @staticmethod
    def normalize_color(color: str) -> str:
        """Repair seam: emission normalizes, storage does not. Replaced by repair rules."""
        return color

    def reset(self, seed: str = "spec") -> None:
        """Mirror the reference seed: 3 labels, 2 issues (issue-one has bug)."""
        self.issues = {}
        self.labels = {}
        self._next_number = 1
        self.labels["bug"] = _Label("bug", "#d73a4a")
        self.labels["ui"] = _Label("ui", "#0e8a16")
        self.labels["api"] = _Label("api", "#6f42c1")
        self.create_issue("spec-repo", "issue-one", "synthetic first issue", ["bug"])
        self.create_issue("spec-repo", "issue-two", "synthetic second issue", [])

    # -- the six operations ----------------------------------------------------

    def create_issue(
        self, repo: str, title: str, body: str = "", label_names: list[str] | None = None
    ) -> dict:
        if not title:
            raise EmulatorError(422, "title is required")
        issue = _Issue(self._next_number, title, body)
        self._next_number += 1
        for name in label_names or []:
            if name in self.labels:
                issue.labels.add(name)
        self.issues[issue.number] = issue
        return self._raw_issue(issue)

    def get_issue(self, repo: str, number: str) -> dict:
        issue = self.issues.get(int(number))
        if issue is None:
            raise EmulatorError(404, "issue not found")
        return self._raw_issue(issue)

    def edit_issue(
        self,
        repo: str,
        number: str,
        state: str | None = None,
        title: str | None = None,
        body: str | None = None,
    ) -> dict:
        issue = self.issues.get(int(number))
        if issue is None:
            raise EmulatorError(404, "issue not found")
        if state in ("open", "closed"):
            issue.state = state
            issue.closed_at = None if state == "open" else "now"
            issue.updated_at = "2000-01-01T00:00:01Z"
        if title:
            issue.title = title
        if body is not None:
            issue.body = body
        return self._raw_issue(issue)

    def add_label(self, repo: str, number: str, label: str) -> dict:
        issue = self.issues.get(int(number))
        if issue is None:
            raise EmulatorError(404, "issue not found")
        if label not in self.labels:
            raise EmulatorError(404, "label not found")
        issue.labels.add(label)  # no-op if already present
        return self._raw_issue(issue)

    def remove_label(self, repo: str, number: str, label: str) -> dict:
        issue = self.issues.get(int(number))
        if issue is None:
            raise EmulatorError(404, "issue not found")
        if label not in issue.labels:
            raise EmulatorError(404, "label not found on issue")
        issue.labels.discard(label)
        return self._raw_issue(issue)

    def create_label(self, repo: str, name: str, color: str) -> dict:
        if not name:
            raise EmulatorError(422, "name is required")
        self.labels[name] = _Label(name, color)
        return {"name": name, "color": self.normalize_color(color)}

    def step(self, op: dict) -> dict:
        """Dispatch one action dict (from sequences.py `Action.as_dict()`).

        Every action carries a leading `owner` arg from the generator; the
        emulator is single-owner by construction, so it is skipped here.
        """
        kind, args = op["op"], op["args"]
        _, repo, *rest = args
        if kind == "create_issue":
            return self.create_issue(repo, rest[0])
        if kind == "get_issue":
            return self.get_issue(repo, rest[0])
        if kind == "edit_issue":
            return self.edit_issue(repo, rest[0], state=rest[1])
        if kind == "add_label":
            return self.add_label(repo, rest[0], rest[1])
        if kind == "remove_label":
            return self.remove_label(repo, rest[0], rest[1])
        if kind == "create_label":
            return self.create_label(repo, rest[0], rest[1])
        raise EmulatorError(400, f"unsupported op {kind}")

    def export_declared_state(self) -> dict[str, list[dict]]:
        """Export raw bounded state for evaluator-owned canonicalization."""
        return {
            "issues": [self._raw_issue(issue) for issue in self.issues.values()],
            "labels": [
                {"name": label.name, "color": self.normalize_color(label.color)}
                for label in self.labels.values()
            ],
        }

    # -- raw shape for the common projection ------------------------------------

    def _raw_issue(self, issue: _Issue) -> dict:
        return {
            "number": issue.number,
            "title": issue.title,
            "body": issue.body,
            "state": issue.state,
            "closed_at": issue.closed_at,
            "created_at": issue.created_at,
            "updated_at": issue.updated_at,
            "labels": [
                {"name": self.labels[n].name, "color": self.normalize_color(self.labels[n].color)}
                for n in sorted(issue.labels)
            ],
            "assignees": [],
            "url": f"/repos/spec-repo/issues/{issue.number}",
        }
