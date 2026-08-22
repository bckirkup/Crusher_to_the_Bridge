"""Sentinel timing layer: delay pmfs, renewal, censoring, back-calculation.

Graded sensitivity checks (see docs/ci-test-design) on the properties the
attribution model actually depends on — mass conservation, monotonicity in the
parameters, the direction of the censoring bias — with a couple of labeled
golden values as change detectors.
"""

from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.analysis.sentinel.incubation import (
    DelayDistribution,
    deconvolve_onsets,
    default_pathogen,
    delays_for_pathogen,
    discrete_delay,
    expected_onsets,
    load_delay_catalog,
    lognormal_delay,
    observed_onset_fraction,
    port_resolution_adequate,
    renewal_incidence,
)


def norovirus_incubation(epoch_hours: float = 1.0) -> DelayDistribution:
    """Bundled default-pathogen incubation pmf on an epoch grid."""
    return delays_for_pathogen(epoch_hours=epoch_hours)[0]


def test_catalog_carries_the_default_and_the_documented_counter_example() -> None:
    catalog = load_delay_catalog()
    dists = catalog["distributions"]
    # Law 2: the default pathogen is named in the catalog, not in the code.
    assert default_pathogen(catalog) in dists
    assert default_pathogen() == default_pathogen(catalog)
    with pytest.raises(ValueError, match="default_pathogen"):
        default_pathogen({"distributions": dists})
    # measles is in the catalog only as the 1.8 counter-example
    assert dists["measles"]["port_resolution"] == "inadequate"
    assert dists["norovirus"]["port_resolution"] == "adequate"


def test_lognormal_pmf_is_a_normalized_distribution() -> None:
    delay = lognormal_delay(
        name="t",
        median_hours=33.0,
        sigma=0.42,
        epoch_hours=1.0,
        max_hours=120.0,
    )
    assert delay.weights.min() >= 0.0
    assert delay.weights.sum() == pytest.approx(1.0)
    assert delay.mass_within(delay.max_lag) == pytest.approx(1.0)
    assert delay.mass_within(-1) == 0.0
    assert delay.weight_at(delay.max_lag + 5) == 0.0


@pytest.mark.parametrize("median_hours", [12.0, 24.0, 48.0])
def test_median_shifts_the_delay_and_iqr_scales_with_it(median_hours: float) -> None:
    delay = lognormal_delay(
        name="t",
        median_hours=median_hours,
        sigma=0.4,
        epoch_hours=1.0,
        max_hours=400.0,
    )
    # A lognormal is a scale family in the median: mean and IQR both scale with
    # it (analytically 1.083x and 0.546x at sigma=0.4), up to 1 h binning.
    assert delay.mean_hours == pytest.approx(median_hours * 1.083, rel=0.1)
    assert delay.iqr_hours == pytest.approx(median_hours * 0.546, rel=0.2)


@pytest.mark.parametrize("sigma", [0.2, 0.4, 0.8])
def test_iqr_widens_monotonically_with_sigma(sigma: float) -> None:
    widths = [
        lognormal_delay(
            name="t",
            median_hours=33.0,
            sigma=s,
            epoch_hours=1.0,
            max_hours=600.0,
        ).iqr_hours
        for s in (0.2, 0.4, 0.8)
    ]
    assert widths == sorted(widths)
    assert widths[(0.2, 0.4, 0.8).index(sigma)] > 0.0


def test_coarser_epochs_keep_the_delay_but_lose_resolution() -> None:
    fine = norovirus_incubation(epoch_hours=1.0)
    coarse = norovirus_incubation(epoch_hours=6.0)
    assert coarse.mean_hours == pytest.approx(fine.mean_hours, rel=0.1)
    assert coarse.max_lag < fine.max_lag
    assert coarse.epoch_hours == 6.0


def test_norovirus_iqr_separates_ports_and_measles_does_not() -> None:
    noro = norovirus_incubation()
    measles = delays_for_pathogen("measles", epoch_hours=1.0)[0]
    assert noro.iqr_hours < 24.0 < measles.iqr_hours
    assert port_resolution_adequate(noro, 24.0)
    assert not port_resolution_adequate(measles, 24.0)
    # No itinerary, no resolution claim.
    assert not port_resolution_adequate(noro, 0.0)


def test_unknown_pathogen_names_the_known_ones() -> None:
    with pytest.raises(KeyError, match="norovirus"):
        delays_for_pathogen("influenza")


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"median_hours": 0.0, "sigma": 0.4}, "median_hours"),
        ({"median_hours": 24.0, "sigma": 0.0}, "sigma"),
    ],
)
def test_degenerate_lognormal_parameters_are_rejected(
    kwargs: dict[str, float],
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        lognormal_delay(name="t", epoch_hours=1.0, max_hours=48.0, **kwargs)


def test_forward_convolution_moves_mass_by_the_delay() -> None:
    delay = discrete_delay(name="t", weights=[0.0, 0.5, 0.5], epoch_hours=1.0)
    infections = np.zeros(10)
    infections[2] = 10.0
    onsets = expected_onsets(infections, delay)
    assert onsets[2] == 0.0
    assert onsets[3] == pytest.approx(5.0)
    assert onsets[4] == pytest.approx(5.0)
    assert onsets.sum() == pytest.approx(10.0)


def test_convolution_drops_mass_past_the_horizon_rather_than_piling_it_up() -> None:
    delay = discrete_delay(name="t", weights=[0.0, 0.0, 1.0], epoch_hours=1.0)
    infections = np.zeros(5)
    infections[4] = 8.0
    inside = expected_onsets(infections, delay, n_epochs=8)
    truncated = expected_onsets(infections, delay, n_epochs=5)
    assert inside.sum() == pytest.approx(8.0)
    assert truncated.sum() == pytest.approx(0.0)
    assert expected_onsets(infections, delay, n_epochs=0).size == 0


def test_renewal_is_strictly_lagged_and_graded_in_r_onboard() -> None:
    _, generation = delays_for_pathogen(epoch_hours=6.0)
    imported = np.zeros(40)
    imported[5] = 100.0

    totals = [
        renewal_incidence(imported, r, generation).sum() for r in (0.0, 0.5, 1.0, 1.5)
    ]
    assert totals[0] == pytest.approx(100.0)  # R=0 -> imports only
    assert totals == sorted(totals)
    assert totals[-1] > totals[0] * 2.0
    # No same-epoch self-excitation: the import epoch is untouched by R.
    for r in (0.0, 1.5):
        assert renewal_incidence(imported, r, generation)[5] == pytest.approx(100.0)


def test_renewal_rejects_a_negative_reproduction_number() -> None:
    _, generation = delays_for_pathogen(epoch_hours=6.0)
    with pytest.raises(ValueError, match="non-negative"):
        renewal_incidence(np.zeros(3), -0.1, generation)


def test_same_epoch_only_generation_interval_is_refused() -> None:
    instant = discrete_delay(name="t", weights=[1.0], epoch_hours=1.0)
    with pytest.raises(ValueError, match="no lagged mass"):
        renewal_incidence(np.zeros(3), 1.0, instant)


def test_observed_fraction_rises_with_the_epochs_left_in_the_window() -> None:
    incubation = norovirus_incubation()
    fractions = [observed_onset_fraction(k, incubation) for k in (0, 12, 24, 48, 200)]
    assert fractions == sorted(fractions)
    assert fractions[0] < 0.05  # a last-epoch infection is essentially never seen
    assert fractions[-1] == pytest.approx(1.0)
    assert observed_onset_fraction(-5, incubation) == 0.0


def test_uncorrected_counts_understate_late_exposure() -> None:
    """The 1.6 bias, made explicit: equal hazards, unequal observed counts."""
    incubation = norovirus_incubation()
    hazard, person_hours = 1e-4, 5_000.0
    early, late = 120, 24  # epochs remaining after an early vs a late port
    observed_early = observed_onset_fraction(early, incubation)
    observed_late = observed_onset_fraction(late, incubation)
    assert observed_late < observed_early

    # Same hazard at both ports; raw counts say the late port is safer.
    counts = {
        "early": hazard * person_hours * observed_early,
        "late": hazard * person_hours * observed_late,
    }
    assert counts["late"] / counts["early"] < 0.9
    # Dividing by the observed fraction restores the equality raw counts lose.
    corrected = {k: counts[k] / f for k, f in (
        ("early", observed_early),
        ("late", observed_late),
    )}
    assert corrected["late"] == pytest.approx(corrected["early"])
    assert corrected["early"] == pytest.approx(hazard * person_hours)


def test_deconvolution_recovers_a_known_infection_spike() -> None:
    incubation = norovirus_incubation()
    infections = np.zeros(120)
    infections[30] = 60.0
    onsets = expected_onsets(infections, incubation, n_epochs=120)

    recovered = deconvolve_onsets(onsets, incubation, iterations=300)
    assert int(recovered.argmax()) == 30
    assert recovered.sum() == pytest.approx(60.0, rel=0.05)


def test_deconvolution_does_not_shrink_late_infections_to_zero() -> None:
    """Censoring-aware normalizer: a late spike is recovered, not discarded."""
    incubation = norovirus_incubation()
    infections = np.zeros(90)
    infections[75] = 40.0
    onsets = expected_onsets(infections, incubation, n_epochs=90)
    assert onsets.sum() < 40.0  # most of its onsets fall outside the window

    recovered = deconvolve_onsets(onsets, incubation, iterations=300)
    assert recovered[70:].sum() > onsets.sum()
    assert recovered.sum() == pytest.approx(40.0, rel=0.3)


def test_deconvolution_edge_cases() -> None:
    incubation = norovirus_incubation()
    assert deconvolve_onsets([], incubation).size == 0
    assert deconvolve_onsets(np.zeros(10), incubation).sum() == pytest.approx(0.0)
    with pytest.raises(ValueError, match="non-negative"):
        deconvolve_onsets([1.0, -1.0], incubation)


def test_discrete_delay_validation() -> None:
    with pytest.raises(ValueError, match="empty"):
        discrete_delay(name="t", weights=[], epoch_hours=1.0)
    with pytest.raises(ValueError, match="negative"):
        discrete_delay(name="t", weights=[1.0, -0.5], epoch_hours=1.0)
    with pytest.raises(ValueError, match="sum to zero"):
        discrete_delay(name="t", weights=[0.0, 0.0], epoch_hours=1.0)


def test_norovirus_golden_summary() -> None:
    """Change detector for the bundled norovirus incubation pmf.

    Now a projection of the norwalk_gi profile (median 1.2 d, GSD 1.56, 0.1-6 d)
    rather than a separately authored entry, which is why these numbers moved
    from 33 h / 19 h / 120 h of support. tests/test_sentinel_profile_delays.py
    is what holds them to the profile; this stays a change detector.
    """
    incubation = norovirus_incubation()
    assert incubation.quantile_hours(0.5) == pytest.approx(29.0)
    assert incubation.iqr_hours == pytest.approx(17.0)
    assert incubation.max_lag == 143  # 144 h of support on a 1 h grid
    assert math.isclose(sum(incubation.pmf), 1.0, rel_tol=1e-9)
