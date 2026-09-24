"""Transport loss is missing evidence, not a semantic simulator mismatch."""

import pytest

from reality_bridge.differential import compare
from reality_bridge.projection import Observation


@pytest.mark.parametrize(
    "observed",
    [
        Observation(action="create_label", label=("bug", "ff0000")),
        Observation(action="create_label", error="permission_denied"),
        Observation(action="create_label", error="not_found"),
        Observation(action="create_label", error="validation_conflict"),
    ],
)
@pytest.mark.parametrize("uncertain_reference", [True, False])
def test_one_sided_transport_uncertainty_remains_undetermined(
    observed: Observation, uncertain_reference: bool
) -> None:
    uncertain = Observation(action="create_label", error="transport_uncertain")
    reference, simulator = (uncertain, observed) if uncertain_reference else (observed, uncertain)
    result = compare(reference, simulator)
    assert result.outcome == "undetermined"
    assert result.is_issue


def test_both_uncertain_is_not_agreement() -> None:
    uncertain = Observation(action="create_label", error="transport_uncertain")
    assert compare(uncertain, uncertain).outcome == "undetermined"


def test_observed_error_mismatch_is_still_divergence() -> None:
    reference = Observation(action="create_label", error="permission_denied")
    simulator = Observation(action="create_label", error="not_found")
    assert compare(reference, simulator).outcome == "diverge"


def test_observed_matching_error_is_still_agreement() -> None:
    denied = Observation(action="create_label", error="permission_denied")
    assert compare(denied, denied).outcome == "agree"


def test_explicit_simulator_coverage_gap_remains_unsupported() -> None:
    reference = Observation(action="create_label", error="transport_uncertain")
    simulator = Observation(action="create_label", unsupported_operation="create_label")
    assert compare(reference, simulator).outcome == "unsupported"
