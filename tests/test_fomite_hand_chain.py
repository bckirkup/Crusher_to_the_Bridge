"""Behavioral guards for the measured fomite hand-transfer chain."""

from __future__ import annotations

import numpy as np
import pytest

import engines.transmission_core as transmission_core
from engines.infection_dynamics_bridge import (
    IllnessStatus,
    KorkinAgent,
)
from engines.sim_clock import HOURS, SimClock
from engines.transmission_core import (
    ContactTracingMatrix,
    TransmissionCore,
)

PATHOGEN = "test_pathogen"
ZONE = "Public_Lounge"


def _profile(**overrides: object) -> dict:
    profile: dict[str, object] = {
        "shedding_curve_log10": [11.0] * 12,
        "asymptomatic_shedding_log10": [11.0] * 12,
        "symptom_onset_day": 0.0,
        "dose_response": {"model": "exponential", "k": 0.01},
        "hand_inactivation_rate_per_hour": 0.61,
        "hand_hygiene_rate_per_hour": 0.0,
    }
    profile.update(overrides)
    return profile


def _agent(
    agent_id: int = 1,
    *,
    schedule: list[str] | None = None,
    infected: bool = False,
) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role="passenger",
        immune=False,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=schedule or ["Free"] * 24,
    )
    agent.current_location = ZONE
    if infected:
        agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=24)
        agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
    return agent


def _core(
    *,
    zone: str = ZONE,
    zone_type: str = "Free",
    profile: dict | None = None,
    seed: int = 7,
) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={zone: 50.0},
        pathogen_profiles={PATHOGEN: profile or _profile()},
        zone_types={zone: zone_type},
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
    )
    core.initialize_zones([zone])
    return core


def test_preferred_and_legacy_release_keys_are_bitwise_equivalent() -> None:
    agent = _agent(infected=True)
    old = _profile(dose_adjustment=4.0)
    new = _profile(environmental_faecal_release_log10_g_per_epoch=4.0)
    assert agent.get_pathogen_shedding(PATHOGEN, old) == (
        agent.get_pathogen_shedding(PATHOGEN, new)
    )


def test_pickup_is_bounded_and_monotonic_in_surface_pool() -> None:
    requests = []
    for pool in (1.0, 10.0, 100.0):
        core = _core()
        requests.append(core._fomite_pickup_request(
            _agent(), ZONE, pool,
        ))
    assert requests == sorted(requests)
    assert all(0.0 <= value <= pool for value, pool in zip(
        requests, (1.0, 10.0, 100.0),
    ))


def test_pickup_is_monotonic_in_shared_surface_touch_frequency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = []
    for frequency in (2.0, 6.0, 12.0):
        monkeypatch.setattr(
            transmission_core,
            "PUBLIC_SURFACE_CONTACTS_PER_HOUR",
            frequency,
        )
        core = _core(seed=13)
        values.append(core._fomite_pickup_request(_agent(), ZONE, 10.0))
    assert values == sorted(values)


def test_zero_hand_load_delivers_zero_mouth_dose() -> None:
    core = _core()
    target = _agent()
    assert core._hand_to_mouth_dose(target, 0, 0.0) == 0.0


def test_eating_context_increases_mouth_contact_dose(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core = _core()
    target = _agent(schedule=["Meal:Lunch"] * 24)
    monkeypatch.setattr(
        core, "_fomite_mouth_contacts",
        lambda _target, _epoch: 7.7,
    )
    eating = core._hand_to_mouth_dose(target, 0, 100.0)
    target.schedule = ["Free"] * 24
    monkeypatch.setattr(
        core, "_fomite_mouth_contacts",
        lambda _target, _epoch: 2.9,
    )
    non_eating = core._hand_to_mouth_dose(target, 0, 100.0)
    assert eating > non_eating


def test_mouth_dose_is_monotonic_in_mouth_contact_frequency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = []
    target = _agent()
    for frequency in (1.0, 3.0, 8.0):
        core = _core(seed=17)
        monkeypatch.setattr(
            core,
            "_fomite_mouth_contacts",
            lambda _target, _epoch, n=frequency: n,
        )
        values.append(core._hand_to_mouth_dose(target, 0, 100.0))
    assert values == sorted(values)


def test_hand_decay_uses_sim_clock_hourly_rate() -> None:
    hourly = _core(seed=23)
    half_hour = _core(
        seed=23,
    )
    hourly.clock = SimClock(epoch_duration_hours=1.0, mode=HOURS)
    half_hour.clock = SimClock(epoch_duration_hours=0.5, mode=HOURS)
    first = _agent()
    second = _agent()
    first.hand_load_by_pathogen[PATHOGEN] = 1.0
    second.hand_load_by_pathogen[PATHOGEN] = 1.0
    first.hand_inactivation_rate_by_pathogen[PATHOGEN] = 1.0
    second.hand_inactivation_rate_by_pathogen[PATHOGEN] = 1.0
    hourly._decay_hand_load(first, PATHOGEN, _profile())
    half_hour._decay_hand_load(second, PATHOGEN, _profile())
    half_hour._decay_hand_load(second, PATHOGEN, _profile())
    assert first.hand_load_by_pathogen[PATHOGEN] == pytest.approx(
        second.hand_load_by_pathogen[PATHOGEN],
    )


def test_replenishment_reaches_the_liu_hand_target() -> None:
    core = _core(seed=29)
    agent = _agent(infected=True)
    profile = _profile(hand_inactivation_rate_per_hour=1.155)
    target = agent.get_pathogen_hand_target(PATHOGEN, profile)

    for _ in range(24):
        core._replenish_hand(agent, PATHOGEN, profile)

    assert agent.hand_load_by_pathogen[PATHOGEN] == pytest.approx(
        target,
        rel=0.02,
    )


def test_replenishment_is_invariant_to_one_hour_or_half_hour_epochs() -> None:
    profile = _profile(hand_inactivation_rate_per_hour=1.155)
    hourly = _core(seed=31)
    half_hour = _core(seed=31)
    hourly.clock = SimClock(epoch_duration_hours=1.0, mode=HOURS)
    half_hour.clock = SimClock(epoch_duration_hours=0.5, mode=HOURS)
    first = _agent(infected=True)
    second = _agent(infected=True)

    for _ in range(24):
        hourly._replenish_hand(first, PATHOGEN, profile)
    for _ in range(48):
        half_hour._replenish_hand(second, PATHOGEN, profile)

    assert first.hand_load_by_pathogen[PATHOGEN] == pytest.approx(
        second.hand_load_by_pathogen[PATHOGEN],
        rel=1e-9,
    )


def test_empty_fomite_step_is_a_no_op() -> None:
    core = _core()
    before = dict(core.surface_pools)
    core._pathway_fomite(
        0,
        {ZONE: []},
        {},
        ContactTracingMatrix(epoch=0),
        [],
        pathogen_id=PATHOGEN,
        profile=core.pathogen_profiles[PATHOGEN],
    )
    assert core.surface_pools == before


def test_surface_pool_hand_pool_and_dose_do_not_create_mass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core = _core()
    target = _agent()
    core.surface_pools[ZONE] = 100.0
    core.surface_pools_by_pathogen[PATHOGEN][ZONE] = 100.0
    monkeypatch.setattr(
        core, "_fomite_pickup_request",
        lambda _target, _zone, _pool: 10.0,
    )
    before = 100.0
    doses: dict[int, float] = {}
    core._pathway_fomite(
        0,
        {ZONE: [target]},
        doses,
        ContactTracingMatrix(epoch=0),
        [],
        pathogen_id=PATHOGEN,
        profile=core.pathogen_profiles[PATHOGEN],
    )
    hand = target.hand_load_by_pathogen.get(PATHOGEN, 0.0)
    surface = core.surface_pools_by_pathogen[PATHOGEN][ZONE]
    dose = doses[target.agent_id]
    assert surface + hand + dose <= before + 1e-9
    assert surface <= before
    assert hand >= 0.0
    assert dose >= 0.0


def test_fomite_delivery_is_per_capita_invariant_to_occupancy() -> None:
    results = []
    for count in (1, 2, 4):
        core = _core(seed=11)
        targets = [_agent(i) for i in range(count)]
        core.surface_pools[ZONE] = 100.0
        core.surface_pools_by_pathogen[PATHOGEN][ZONE] = 100.0
        core._fomite_pickup_request = lambda _target, _zone, _pool: 1.0
        core._hand_to_mouth_dose = (
            lambda _target, _epoch, hand_load: hand_load * 0.01
        )
        doses: dict[int, float] = {}
        core._pathway_fomite(
            0,
            {ZONE: targets},
            doses,
            ContactTracingMatrix(epoch=0),
            [],
            pathogen_id=PATHOGEN,
            profile=core.pathogen_profiles[PATHOGEN],
        )
        results.append(sum(doses.values()) / count)
    assert results[0] == pytest.approx(results[1])
    assert results[1] == pytest.approx(results[2])
