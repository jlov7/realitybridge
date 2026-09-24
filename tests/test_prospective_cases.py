"""Prospective case-set freeze integrity."""

from __future__ import annotations

import random

from experiments.prospective_cases import (
    DEV_CASES,
    EVAL_CASES,
    RANDOM_ORDER_SEEDS,
    TARGETED_ORDER,
    case_hash,
)


def test_case_split_is_fixed_disjoint_and_complete() -> None:
    dev_ids = {case.case_id for case in DEV_CASES}
    eval_ids = {case.case_id for case in EVAL_CASES}
    assert len(dev_ids) == len(DEV_CASES) == 14
    assert len(eval_ids) == len(EVAL_CASES) == 16
    assert not dev_ids & eval_ids
    assert set(TARGETED_ORDER) == dev_ids
    assert len(TARGETED_ORDER) == len(set(TARGETED_ORDER))


def test_random_orders_are_deterministic_and_do_not_change_cases() -> None:
    source = [case.case_id for case in DEV_CASES]
    orders = []
    for seed in RANDOM_ORDER_SEEDS:
        order = list(source)
        random.Random(seed).shuffle(order)
        assert set(order) == set(source)
        orders.append(order)
    assert len({tuple(order) for order in orders}) == 3


def test_case_hash_is_stable_shape() -> None:
    assert len(case_hash()) == 64
    assert case_hash() == case_hash()


def test_all_cases_stay_inside_six_operation_scope() -> None:
    allowed = {
        "create_issue",
        "get_issue",
        "edit_issue",
        "add_label",
        "remove_label",
        "create_label",
    }
    for case in (*DEV_CASES, *EVAL_CASES):
        assert 1 <= len(case.actions) <= 4
        assert {action.op for action in case.actions} <= allowed
