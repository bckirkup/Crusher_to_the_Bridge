"""Behaviour of the Liu 2013 hand-rinse readout of the shipped hand process.

Sensitivity and bounds, per `.agents/skills/ci-test-design/SKILL.md`; the one
golden-shaped assertion is a labelled change detector on a wide band.
"""

import math

import pytest

from telemetry_buffer.observation_model.hand_occupancy_readout import (
    LIU_CONDITIONAL_MEAN_LOG10,
    LIU_DETECTION_LIMIT_LOG10,
    LIU_OCCUPANCY,
    hand_process_moments,
)

CEILING_LOG10 = 3.86
SHIPPED_INACTIVATION_RANGE = (0.61, 1.7)
BASELINE_EVENTS_PER_DAY = 1.0
DIARRHOEAL_EVENTS_PER_DAY = 5.63
FAST_HOURS = 40_000


def moments(**kwargs):
    defaults = {
        "inactivation_rate_per_hour": 1.0,
        "events_per_day": DIARRHOEAL_EVENTS_PER_DAY,
        "ceiling_log10": CEILING_LOG10,
        "hours": FAST_HOURS,
    }
    defaults.update(kwargs)
    return hand_process_moments(**defaults)


def test_occupancy_rises_with_event_rate():
    """More defecation events a day means more hand-epochs above the LOD."""
    rates = [0.5, 1.0, 2.5, 5.63]
    occupancies = [moments(events_per_day=r).occupancy for r in rates]

    assert occupancies == sorted(occupancies)
    assert occupancies[-1] - occupancies[0] > 0.3


def test_occupancy_falls_with_inactivation_rate():
    """Faster die-off on the hand shortens the window above the LOD."""
    rates = [0.3, 0.61, 1.15, 1.7]
    occupancies = [moments(inactivation_rate_per_hour=r).occupancy for r in rates]

    assert occupancies == sorted(occupancies, reverse=True)
    assert occupancies[0] - occupancies[-1] > 0.2


def test_mean_load_is_proportional_to_the_ceiling():
    """The amplitude is a scale factor: a decade of ceiling is a decade of mass."""
    low = moments(ceiling_log10=3.0).mean_load_log10
    high = moments(ceiling_log10=4.0).mean_load_log10

    assert high - low == pytest.approx(1.0, abs=0.02)


def test_dispersion_raises_both_the_mean_and_the_conditional_mean():
    """Lognormal dispersion at a fixed median inflates the arithmetic mean."""
    sigmas = [0.0, 0.5, 1.0, 1.4]
    means = [moments(sigma_log10=s).mean_load_log10 for s in sigmas]
    conditional = [moments(sigma_log10=s).conditional_mean_log10 for s in sigmas]

    assert means == sorted(means)
    assert conditional == sorted(conditional)
    assert means[-1] - means[0] > 1.0


def test_coupled_wash_lowers_occupancy_and_mass():
    """A removal fired with the event is the only way the event lowers a hand."""
    probabilities = [0.0, 0.5, 1.0]
    occupancies = [moments(wash_probability=p).occupancy for p in probabilities]
    masses = [moments(wash_probability=p).mean_load_log10 for p in probabilities]

    assert occupancies == sorted(occupancies, reverse=True)
    assert masses == sorted(masses, reverse=True)


def test_additive_and_reset_forms_agree_at_shipped_rates():
    """Arrivals are sparse against decay, so max() and + are the same process.

    A negative control for the sensitivity tests above: the structural change
    section 3.1 of the spec proposes is *not* what moves these moments.
    """
    reset = moments(additive=False).mean_load_log10
    additive = moments(additive=True).mean_load_log10

    assert abs(additive - reset) < 0.15


def test_conditional_mean_stays_above_the_detection_limit():
    """A mean over supra-threshold epochs cannot fall below the threshold."""
    for events in (BASELINE_EVENTS_PER_DAY, DIARRHOEAL_EVENTS_PER_DAY):
        result = moments(events_per_day=events)
        assert result.conditional_mean_log10 > LIU_DETECTION_LIMIT_LOG10
        assert result.conditional_mean_log10 <= CEILING_LOG10
        assert 0.0 <= result.occupancy <= 1.0
        assert math.isfinite(result.mean_load_log10)


def test_shipped_diarrhoeal_arm_is_over_occupied_and_under_amplitude():
    """Change detector for ledger item 25, on the shipped sourced values.

    Both statements are wide bands, not point values: across the shipped
    inactivation interval the diarrhoeal arm sits above Liu's occupancy and
    below his positive-sample mean. Ledger item 25 records the measurement.
    """
    for rate in SHIPPED_INACTIVATION_RANGE:
        result = moments(inactivation_rate_per_hour=rate)
        assert result.occupancy_ratio() > 1.5
        assert result.conditional_mean_offset_log10() < -0.3
        assert result.conditional_mean_log10 < LIU_CONDITIONAL_MEAN_LOG10


def test_baseline_arm_brackets_liu_occupancy():
    """The non-diarrhoeal arm spans Liu's 25.4% across the sourced die-off."""
    slow = moments(
        events_per_day=BASELINE_EVENTS_PER_DAY,
        inactivation_rate_per_hour=SHIPPED_INACTIVATION_RANGE[0],
    ).occupancy
    fast = moments(
        events_per_day=BASELINE_EVENTS_PER_DAY,
        inactivation_rate_per_hour=SHIPPED_INACTIVATION_RANGE[1],
    ).occupancy

    assert fast < LIU_OCCUPANCY < slow + 0.02
