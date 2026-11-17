"""Unit guards for the continuous hand-mediated contamination flow solver."""

from __future__ import annotations

import math

import pytest

from engines.contamination_flow import integrate_hand_flow
from engines.transmission_core import (
    DEFAULT_CONTAMINATION_SOLVER,
    _parse_contamination_solver,
)


def test_contamination_solver_defaults_to_continuous() -> None:
    assert DEFAULT_CONTAMINATION_SOLVER == "continuous"
    assert _parse_contamination_solver({}) == "continuous"
    assert _parse_contamination_solver({"contamination_solver": "discrete"}) == "discrete"
    with pytest.raises(ValueError, match="contamination_solver"):
        _parse_contamination_solver({"contamination_solver": "bogus"})


def test_flow_conserves_mass_without_dose() -> None:
    result = integrate_hand_flow(
        hours=1.0,
        agent_ids=[1],
        surface_units=["Zone"],
        food_zones=[],
        hand0={1: 10.0},
        surface0={"Zone": 0.0},
        food0={},
        surface_deposit={(1, "Zone"): 0.5},
        surface_pickup={},
        food_deposit={},
        mouth_rate={1: 0.0},
        food_growth_rate={},
        food_removal_rate={},
        food_dose_rate={},
        food_dose_denominator={},
        steps=24,
    )
    hand = result.hand[1]
    surface = result.surface["Zone"]
    assert hand == pytest.approx(10.0 * math.exp(-0.5), rel=1e-4)
    assert surface == pytest.approx(10.0 - hand, rel=1e-4)


def test_flow_exchange_keeps_surface_and_hand_mass_linked() -> None:
    result = integrate_hand_flow(
        hours=1.0,
        agent_ids=[1],
        surface_units=["Zone"],
        food_zones=[],
        hand0={1: 0.0},
        surface0={"Zone": 10.0},
        food0={},
        surface_deposit={(1, "Zone"): 0.5},
        surface_pickup={(1, "Zone"): 0.5},
        food_deposit={},
        mouth_rate={1: 0.0},
        food_growth_rate={},
        food_removal_rate={},
        food_dose_rate={},
        food_dose_denominator={},
        steps=24,
    )
    hand = result.hand[1]
    surface = result.surface["Zone"]
    expected_gap = 10.0 * math.exp(-1.0)
    assert surface - hand == pytest.approx(expected_gap, rel=1e-3)
    assert surface + hand == pytest.approx(10.0, rel=1e-6)


def test_flow_food_ingestion_removes_pool_and_books_dose() -> None:
    result = integrate_hand_flow(
        hours=1.0,
        agent_ids=[1],
        surface_units=[],
        food_zones=["Dining"],
        hand0={1: 0.0},
        surface0={},
        food0={"Dining": 100.0},
        surface_deposit={},
        surface_pickup={},
        food_deposit={},
        mouth_rate={1: 0.0},
        food_growth_rate={"Dining": 0.0},
        food_removal_rate={"Dining": 1.0},
        food_dose_rate={(1, "Dining"): 1.0},
        food_dose_denominator={"Dining": 1.0},
        steps=24,
    )
    eaten = 100.0 * (1.0 - math.exp(-1.0))
    assert result.food["Dining"] == pytest.approx(100.0 * math.exp(-1.0), rel=1e-3)
    assert result.food_dose[1] == pytest.approx(eaten, rel=1e-3)
    assert result.food["Dining"] + result.food_dose[1] == pytest.approx(100.0, rel=1e-3)
