from __future__ import annotations

import math

import pytest

from engines.sim_clock import SimClock


def test_conversion_helpers_are_legacy_identities() -> None:
    clock = SimClock(mode="legacy_epoch_day")
    assert clock.day_fraction_per_epoch == pytest.approx(1.0)
    assert clock.amount_per_epoch(55.0) == pytest.approx(55.0)
    assert clock.probability_per_epoch(0.7) == pytest.approx(0.7)
    assert clock.decay_per_epoch(0.05) == pytest.approx(0.05)
    assert clock.growth_factor_per_epoch(1.2) == pytest.approx(1.2)
    assert clock.hour_of_day(100) == 12


def test_hourly_conversion_values() -> None:
    clock = SimClock(epoch_duration_hours=1.0, mode="hours")
    assert clock.decay_per_epoch(0.05) == pytest.approx(0.00213, abs=1e-5)
    assert clock.probability_per_epoch(0.70) == pytest.approx(0.0489, abs=1e-4)
    assert clock.amount_per_epoch(55.0) == pytest.approx(2.2917, abs=1e-4)
    assert clock.growth_factor_per_epoch(1.2) == pytest.approx(1.00762, abs=1e-5)
    assert clock.survival_from_half_life(5.6) == pytest.approx(0.8836, abs=1e-4)


def test_conversion_validation() -> None:
    clock = SimClock(epoch_duration_hours=1.0, mode="hours")
    with pytest.raises(ValueError):
        clock.probability_per_epoch(-0.1)
    with pytest.raises(ValueError):
        clock.decay_per_epoch(-0.1)
    with pytest.raises(ValueError):
        clock.growth_factor_per_epoch(0.0)
    assert clock.probability_per_epoch(2.0) == pytest.approx(1.0)
    assert clock.decay_per_epoch(2.0) == pytest.approx(1.0)


def test_twenty_four_hourly_epochs_match_one_legacy_epoch() -> None:
    hourly = SimClock(epoch_duration_hours=1.0, mode="hours")
    legacy = SimClock(mode="legacy_epoch_day")

    food_hourly = hourly.growth_factor_per_epoch(1.2) ** 24
    food_legacy = legacy.growth_factor_per_epoch(1.2)
    surface_hourly = (
        1.0 - hourly.decay_per_epoch(0.25)
    ) ** 24
    surface_legacy = 1.0 - legacy.decay_per_epoch(0.25)
    cost_hourly = sum(hourly.amount_per_epoch(55.0) for _ in range(24))
    cost_legacy = legacy.amount_per_epoch(55.0)
    sick_hourly = 1.0 - (
        1.0 - hourly.probability_per_epoch(0.70)
    ) ** 24
    sick_legacy = legacy.probability_per_epoch(0.70)

    assert food_hourly == pytest.approx(food_legacy)
    assert surface_hourly == pytest.approx(surface_legacy)
    assert cost_hourly == pytest.approx(cost_legacy)
    assert sick_hourly == pytest.approx(sick_legacy)
    assert math.isfinite(food_hourly)
