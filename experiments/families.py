"""Authored semantic test families (PROTOCOL §5).

30 authored families over the six-operation lifecycle grammar, sequences up to
six steps. Development and test families are FIXED and DISJOINT (rule:
dev family ids are 'dev-*', test family ids are 'test-*', so the split cannot
drift). The split itself is frozen here and recorded in the protocol.

Families capture semantic behaviour types, not paraphrases: a family is one
scripted interaction pattern with a name, an intent, and a deterministic
sequence built from real op/arg tuples. Some sequences are valid, some are
deliberately invalid (absent objects, missing required fields, boundary
transitions) — the permission/lifecycle surface is part of the comparison.

No outcomes are consulted anywhere in this module. It is a pure function of
the family definition. Everything here mirrors what the live reference seed
provides (owner rbadmin, repo spec-repo, labels bug/ui/api, issues 1-2).
"""

from __future__ import annotations

from reality_bridge.sequences import Action

# --- helpers -------------------------------------------------------------------


def _c(title: str) -> Action:
    return Action("create_issue", ("rbadmin", "spec-repo", title))


def _g(number: str) -> Action:
    return Action("get_issue", ("rbadmin", "spec-repo", number))


def _e(number: str, state: str) -> Action:
    return Action("edit_issue", ("rbadmin", "spec-repo", number, state))


def _a(number: str, label: str) -> Action:
    return Action("add_label", ("rbadmin", "spec-repo", number, label))


def _r(number: str, label: str) -> Action:
    return Action("remove_label", ("rbadmin", "spec-repo", number, label))


def _l(name: str, color: str) -> Action:
    return Action("create_label", ("rbadmin", "spec-repo", name, color))


def _n(seed: str) -> Action:
    # absent title — invalid create
    return Action("create_issue", ("rbadmin", "spec-repo", ""))


def _gone(seed: str) -> Action:
    return Action("get_issue", ("rbadmin", "spec-repo", "999"))


# --- families -------------------------------------------------------------------

FAMILIES: dict[str, list[Action]] = {
    # ---- development families (14) ----
    "dev-create-and-read": [_c("dev-a"), _g("1")],
    "dev-close-and-reopen": [_e("1", "closed"), _g("1"), _e("1", "open"), _g("1")],
    "dev-label-add-remove": [_a("1", "bug"), _r("1", "bug"), _g("1")],
    "dev-label-foreign": [_a("2", "api"), _g("2")],
    "dev-create-label-dupe": [_l("dev-label-x", "#112233"), _l("dev-label-x", "#445566")],
    "dev-absent-issue-get": [_gone("x"), _g("1")],
    "dev-absent-issue-edit": [_e("999", "closed"), _g("1")],
    "dev-absent-title": [_n("x")],
    "dev-absent-label": [_a("1", "no-such-label")],
    "dev-remove-unattached": [_r("2", "bug")],
    "dev-invalid-label-create": [_l("", "#000000")],
    "dev-multi-label": [_a("1", "bug"), _a("1", "ui"), _g("1")],
    "dev-close-then-read": [_e("1", "closed"), _g("1")],
    "dev-open-then-label": [_e("2", "open"), _a("2", "ui"), _g("2")],
    # ---- test families (16) — held out ----
    "test-create-close-reopen": [_c("test-a"), _e("1", "closed"), _e("1", "open"), _g("1")],
    "test-create-label-read": [_l("test-label", "#aabbcc"), _g("1")],
    "test-label-then-unattach": [_a("1", "bug"), _r("1", "bug"), _g("1")],
    "test-close-then-label": [_e("1", "closed"), _a("1", "ui"), _g("1")],
    "test-issue-2-read": [_g("2")],
    "test-absent-issue-remove-label": [_r("999", "bug")],
    "test-null-title": [_n("x"), _g("1")],
    "test-two-creates": [_c("test-c"), _c("test-d"), _g("1")],
    "test-add-label-twice": [_a("1", "bug"), _a("1", "bug"), _g("1")],
    "test-remove-label-twice": [_a("1", "bug"), _r("1", "bug"), _r("1", "bug"), _g("1")],
    "test-multi-label-create": [_l("tl1", "#111111"), _l("tl2", "#222222"), _g("1")],
    "test-open-label-close": [_e("2", "open"), _a("2", "ui"), _e("2", "closed"), _g("2")],
    "test-edit-close-absent": [_e("1", "closed"), _e("999", "open"), _g("1")],
    "test-foreign-label-on-closed": [_e("1", "closed"), _a("1", "api"), _g("1")],
    "test-multi-issue-edit": [_e("1", "closed"), _e("2", "closed"), _g("1")],
    "test-label-create-then-attach": [_l("tl3", "#333333"), _a("1", "tl3"), _g("1")],
}

DEV_FAMILIES: list[str] = sorted(k for k in FAMILIES if k.startswith("dev-"))
TEST_FAMILIES: list[str] = sorted(k for k in FAMILIES if k.startswith("test-"))


def sequence(family_id: str) -> list[Action]:
    """Return the (immutable-by-convention) sequence for a family."""
    fam = FAMILIES.get(family_id)
    if fam is None:
        raise KeyError(f"no family {family_id!r}")
    return list(fam)


def concurrent_denominator() -> int:
    return len(FAMILIES)
