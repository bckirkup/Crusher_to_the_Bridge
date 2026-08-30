"""Regression tests for measured contact-layer rates and kernels."""

from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import KorkinAgent
from engines.sim_clock import HOURS, LEGACY_EPOCH_DAY, SimClock
from engines.transmission_core import (
    AVG_R_POOL,
    CREW_SERVICE_SURFACE_CONTACTS_PER_HOUR,
    POLYMOD_CONTACTS_PER_DAY,
    SURFACE_CONTACTS_PER_HOUR,
    TransmissionCore,
)


def _agent(agent_id: int, zone: str, role: str = "passenger") -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role=role,
        immune=False,
        home_zone=zone,
        dining_zone=zone,
        work_zone=zone,
        free_zone=zone,
        schedule=["Free"] * 24,
    )
    agent.current_location = zone
    return agent


def _core(
    zone: str,
    zone_type: str,
    *,
    hours: float = 1.0,
) -> TransmissionCore:
    return TransmissionCore(
        rng=np.random.default_rng(7),
        zone_types={zone: zone_type},
        clock=SimClock(epoch_duration_hours=hours, mode=HOURS),
    )


def test_surface_touch_rates_are_zone_and_role_aware() -> None:
    zone = "MainDining"
    core = _core(zone, "Dining")
    passenger = _agent(1, zone)
    crew = _agent(2, zone, role="crew")

    assert core._fomite_surface_contacts(zone, passenger) == pytest.approx(
        SURFACE_CONTACTS_PER_HOUR["dining"],
    )
    assert core._fomite_surface_contacts(zone, crew) == pytest.approx(
        CREW_SERVICE_SURFACE_CONTACTS_PER_HOUR,
    )


def test_crew_in_non_service_zone_uses_zone_rate() -> None:
    zone = "CrewCabin"
    core = _core(zone, "Room")
    crew = _agent(1, zone, role="crew")

    assert core._fomite_surface_contacts(zone, crew) == pytest.approx(
        SURFACE_CONTACTS_PER_HOUR["cabin"],
    )


def test_surface_touch_rates_scale_with_epoch_hours() -> None:
    zone = "Public_Lounge"
    hourly = _core(zone, "Free", hours=1.0)
    half_hour = _core(zone, "Free", hours=0.5)
    passenger = _agent(1, zone)

    assert hourly._fomite_surface_contacts(zone, passenger) == pytest.approx(
        2.0 * half_hour._fomite_surface_contacts(zone, passenger),
    )


def test_default_contact_draws_match_polymod_and_are_timestep_invariant() -> None:
    hourly = TransmissionCore(
        rng=np.random.default_rng(11),
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
    )
    daily = TransmissionCore(
        rng=np.random.default_rng(11),
        clock=SimClock(epoch_duration_hours=24.0, mode=HOURS),
    )
    target = _agent(1, "Lounge")
    samples = 4000
    hourly_means = [
        sum(hourly._draw_contact_multiplier(10, target) for _ in range(24))
        for _ in range(samples)
    ]
    daily_draws = [
        daily._draw_contact_multiplier(10, target)
        for _ in range(samples)
    ]

    assert np.mean(hourly_means) == pytest.approx(
        POLYMOD_CONTACTS_PER_DAY,
        abs=0.12,
    )
    assert np.mean(hourly_means) == pytest.approx(
        np.mean(daily_draws),
        abs=0.25,
    )


def test_legacy_contact_draws_remain_in_avg_r_pool() -> None:
    core = TransmissionCore(
        rng=np.random.default_rng(19),
        clock=SimClock(epoch_duration_hours=24.0, mode=LEGACY_EPOCH_DAY),
        cfg={"transmission": {"contact_mode": "legacy"}},
    )
    target = _agent(1, "Lounge")
    draws = [core._draw_contact_multiplier(10, target) for _ in range(1000)]

    assert set(draws) <= set(AVG_R_POOL)
