from __future__ import annotations

import math

import pytest
import numpy as np

from crusher_labs.cost_ledger import CostLedger
from engines.transmission_core import ContactTracingMatrix, TransmissionCore
from engines.sim_clock import SimClock
from orchestrator_epoch import step_cost_accounting
from orchestrator_types import ProtocolContext


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


def _reservoir_core(clock: SimClock) -> TransmissionCore:
    profile = {
        "food_contamination": {
            "enabled": True,
            "food_zones": ["Dining"],
            "growth_rate_per_day": 0.2,
            "decay_rate_per_day": 0.1,
        },
        "surface_decay_per_day": 0.25,
    }
    core = TransmissionCore(
        np.random.default_rng(41),
        pathogen_profiles={"test": profile},
        zone_types={"Dining": "Dining"},
        clock=clock,
    )
    core.initialize_zones(["Dining"])
    core.food_pools["test"]["Dining"] = 10.0
    core.surface_pools_by_pathogen["test"]["Dining"] = 10.0
    return core


def test_engine_reservoir_updates_match_across_clock_grids() -> None:
    hourly = _reservoir_core(SimClock(epoch_duration_hours=1.0, mode="hours"))
    legacy = _reservoir_core(SimClock(mode="legacy_epoch_day"))
    for epoch in range(24):
        hourly._pathway_food_contamination(
            epoch, {"Dining": []}, {}, ContactTracingMatrix(epoch),
            pathogen_id="test", profile=hourly.pathogen_profiles["test"],
        )
        hourly._update_surface_pools({})
    legacy._pathway_food_contamination(
        0, {"Dining": []}, {}, ContactTracingMatrix(0),
        pathogen_id="test", profile=legacy.pathogen_profiles["test"],
    )
    legacy._update_surface_pools({})
    assert hourly.food_pools["test"]["Dining"] == pytest.approx(
        legacy.food_pools["test"]["Dining"],
    )
    assert hourly.surface_pools_by_pathogen["test"]["Dining"] == pytest.approx(
        legacy.surface_pools_by_pathogen["test"]["Dining"],
    )


def _baseline_context(clock: SimClock) -> ProtocolContext:
    return ProtocolContext(
        protocol_engine=None,
        cost_ledger=CostLedger(
            starting_inventory={"swab_kits": 24, "pcr_kits": 24},
        ),
        resource_costs_cfg={
            "baseline_surveillance_costs_per_day": {
                "financial_usd": 55.0,
                "labor_person_hours": 2.0,
                "materials": {"swab_kits": 1.0, "pcr_kits": 1.0},
            },
            "per_test_costs": {},
        },
        standing_protocols=[],
        original_filter_eff=0.5,
        clock=clock,
    )


def test_engine_baseline_costs_match_across_clock_grids() -> None:
    hourly = _baseline_context(SimClock(epoch_duration_hours=1.0, mode="hours"))
    legacy = _baseline_context(SimClock(mode="legacy_epoch_day"))
    empty = ({}, {}, {}, {}, {}, {})
    for epoch in range(24):
        step_cost_accounting(epoch, hourly, *empty)
    step_cost_accounting(0, legacy, *empty)
    hourly_audit = hourly.cost_ledger.generate_financial_audit()
    legacy_audit = legacy.cost_ledger.generate_financial_audit()
    assert hourly_audit["summary"]["total_expenditure_usd"] == pytest.approx(
        legacy_audit["summary"]["total_expenditure_usd"],
    )
    assert hourly_audit["summary"]["total_labor_consumed_hours"] == pytest.approx(
        legacy_audit["summary"]["total_labor_consumed_hours"],
    )
    for item in ("swab_kits", "pcr_kits"):
        assert hourly_audit["material_inventory"][item]["consumed"] == pytest.approx(
            legacy_audit["material_inventory"][item]["consumed"],
        )


def test_engine_contacts_match_daily_mean_at_hourly_resolution() -> None:
    hourly = TransmissionCore(
        np.random.default_rng(7),
        clock=SimClock(epoch_duration_hours=1.0, mode="hours"),
        cfg={"transmission": {"contact_mode": "density_dependent"}},
    )
    legacy = TransmissionCore(
        np.random.default_rng(8),
        clock=SimClock(mode="legacy_epoch_day"),
        cfg={"transmission": {"contact_mode": "density_dependent"}},
    )
    target = type("Target", (), {"current_location": "", "role": "passenger"})()
    draws = 4000
    hourly_total = sum(
        sum(hourly._effective_contacts(50, target) for _ in range(24))
        for _ in range(draws)
    ) / draws
    legacy_mean = sum(
        legacy._effective_contacts(50, target) for _ in range(draws)
    ) / draws
    assert hourly_total == pytest.approx(legacy_mean, abs=0.35)
    assert hourly._effective_contacts(50, target) <= 2
