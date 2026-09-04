"""Invariants for dose-pathway units, aging, and pool conservation."""

from __future__ import annotations

import math

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
    KorkinShipEngine,
)
from engines.sim_clock import SimClock
from engines.transmission_core import (
    ContactTracingMatrix,
    TransmissionCore,
)
from orchestrator_epoch import _airborne_emission_fraction, step_infection_progression

ZONE = "Test_Zone"
PATHOGEN = "test_pathogen"


def _profile(*, food: bool = False) -> dict:
    profile = {
        "shedding_curve_log10": [2.0] * 12,
        "asymptomatic_shedding_log10": [2.0] * 12,
        "symptom_onset_day": 0.0,
        "airborne_half_life_hours": 1.0,
        "surface_decay_log10_per_day": 0.301030,
        "dose_response": {
            "model": "exponential",
            "k": 0.01,
        },
    }
    if food:
        profile["food_contamination"] = {
            "enabled": True,
            "food_zones": [ZONE],
            "growth_rate_per_day": 0.0,
            "decay_rate_per_day": 0.0,
        }
    return profile


def _agent(
    agent_id: int,
    *,
    immune: bool = False,
    infected: bool = False,
    clock: SimClock | None = None,
) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role="passenger",
        immune=immune,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=["Free"] * 24,
    )
    agent.current_location = ZONE
    if clock is not None:
        agent.clock = clock
    if infected:
        agent.infection_status = InfectionStatus.INFECTED
        agent.illness_status = IllnessStatus.SYMPTOMATIC
        agent.infect_with_pathogen(
            PATHOGEN,
            1.0,
            0,
            time_infected=0,
        )
        agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
    return agent


def _core(
    *,
    clock: SimClock | None = None,
    volume: float = 50.0,
    food: bool = False,
) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(19),
        zone_volumes={ZONE: volume},
        pathogen_profiles={PATHOGEN: _profile(food=food)},
        zone_types={ZONE: "Dining"},
        clock=clock,
    )
    core.initialize_zones([ZONE])
    return core


AGING_PROFILE = {
    "shedding_curve_log10": [4.0] * 40,
    "asymptomatic_shedding_log10": [4.0] * 40,
    "dose_adjustment": 0.0,
    "presymptomatic_shedding_days": 1.0,
    "symptom_onset_day": 0.0,
    "recovery_day": 1000.0,
    "surface_deposition_fraction": 1.0,
    "airborne_half_life_hours": 1.0,
}


def _aging_engine(shedder: bool) -> KorkinShipEngine:
    """One host in one zone, so the zone's airborne mass is analytic."""
    clock = SimClock(epoch_duration_hours=1.0, mode="hours")
    engine = KorkinShipEngine(
        num_passengers=1,
        num_crew=0,
        initial_infected=0,
        immune_ratio=0.0,
        seed=11,
        clock=clock,
    )
    agent = engine.agents[0]
    agent.current_location = ZONE
    if shedder:
        agent.infection_status = InfectionStatus.INFECTED
        agent.illness_status = IllnessStatus.SYMPTOMATIC
        agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=24)
        agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
        agent.infections[PATHOGEN]["onset_time_infected"] = 0
    engine.set_pathogen_zone_mass(PATHOGEN, {ZONE: 0.0})
    return engine


def _run_aging(engine: KorkinShipEngine, epochs: int) -> list[float]:
    profiles = {PATHOGEN: AGING_PROFILE}
    trace = []
    for epoch in range(epochs):
        step_infection_progression(engine, profiles, epoch=epoch)
        trace.append(engine.get_pathogen_zone_mass(PATHOGEN)[ZONE])
    return trace


def test_airborne_mass_converges_instead_of_accumulating() -> None:
    """A constant shedder drives the zone to a bounded airborne fixed point.

    Without per-pathogen aging on the production path the reservoir is a
    running total, so it grows by the same deposit every epoch forever. Aged,
    it converges to deposit / (1 - survival).
    """
    engine = _aging_engine(shedder=True)
    clock = engine.clock
    trace = _run_aging(engine, 40)

    survival = clock.survival_from_half_life(
        AGING_PROFILE["airborne_half_life_hours"],
    )
    deposit = clock.amount_per_epoch(10.0 ** 4.0)
    assert trace[-1] == pytest.approx(deposit / (1.0 - survival), rel=1e-6)

    first_ten = trace[9] - trace[0]
    last_ten = trace[-1] - trace[-11]
    assert last_ten < first_ten
    assert all(math.isfinite(mass) for mass in trace)
    assert all(mass >= 0.0 for mass in trace)
    assert engine.zone_pathogen_mass[ZONE] == pytest.approx(trace[-1])


def test_airborne_mass_decays_without_a_shedder() -> None:
    engine = _aging_engine(shedder=False)
    engine.set_pathogen_zone_mass(PATHOGEN, {ZONE: 100.0})
    trace = _run_aging(engine, 6)

    assert trace == sorted(trace, reverse=True)
    assert trace[-1] < 100.0
    assert min(trace) >= 0.0


def test_confined_shedder_airborne_deposition_is_attenuated() -> None:
    clock = SimClock(epoch_duration_hours=1.0, mode="hours")
    profile = {
        "shedding_curve_log10": [4.0] * 40,
        "asymptomatic_shedding_log10": [4.0] * 40,
        "surface_deposition_fraction": 1.0,
        "airborne_half_life_hours": 1.0,
    }

    def deposited(quarantined: bool) -> float:
        engine = _aging_engine(shedder=True)
        core = TransmissionCore(
            rng=np.random.default_rng(19),
            zone_volumes={ZONE: 50.0},
            zone_types={ZONE: "Cabin_Corridor"},
            clock=clock,
        )
        core.initialize_zones([ZONE])
        if quarantined:
            core._quarantined_ids = {engine.agents[0].agent_id}
        step_infection_progression(
            engine,
            {PATHOGEN: profile},
            epoch=0,
            confinement_core=core,
        )
        return engine.get_pathogen_zone_mass(PATHOGEN)[ZONE]

    assert deposited(True) == pytest.approx(deposited(False) * 0.05)


@pytest.mark.parametrize(
    ("profile", "expected"),
    [
        ({"airborne_emission_mode": "emesis_conditioned"}, 0.0),
        ({"airborne_emission_fraction": 0.25}, 0.25),
        ({"surface_deposition_fraction": 0.4}, 0.4),
        ({}, 1e-4),
    ],
)
def test_airborne_emission_mode_preserves_continuous_helper_contract(
    profile: dict[str, object],
    expected: float,
) -> None:
    assert _airborne_emission_fraction(profile) == pytest.approx(expected)


def test_emesis_mode_removes_continuous_airborne_feed() -> None:
    emesis_profile = {
        **AGING_PROFILE,
        "airborne_emission_mode": "emesis_conditioned",
    }
    continuous_profile = {
        **AGING_PROFILE,
        "airborne_emission_mode": "continuous_fraction",
        "airborne_emission_fraction": 1.0,
    }
    emesis_engine = _aging_engine(shedder=True)
    continuous_engine = _aging_engine(shedder=True)

    step_infection_progression(
        emesis_engine,
        {PATHOGEN: emesis_profile},
        epoch=0,
    )
    step_infection_progression(
        continuous_engine,
        {PATHOGEN: continuous_profile},
        epoch=0,
    )

    assert emesis_engine.get_pathogen_zone_mass(PATHOGEN)[ZONE] == pytest.approx(0.0)
    assert continuous_engine.get_pathogen_zone_mass(PATHOGEN)[ZONE] > 0.0


def test_simultaneous_delivery_is_independent_of_occupant_order() -> None:
    """Everyone in a zone eats from the same pool, so order cannot matter."""
    def doses(order: list[int]) -> list[float]:
        core = _core(food=True)
        core.food_pools[PATHOGEN][ZONE] = 10.0
        occupants = [_agent(agent_id) for agent_id in order]
        agent_doses: dict[int, float] = {}
        core._pathway_food_contamination(
            0,
            {ZONE: occupants},
            agent_doses,
            ContactTracingMatrix(epoch=0),
            pathogen_id=PATHOGEN,
            profile=core.pathogen_profiles[PATHOGEN],
        )
        return [agent_doses[agent_id] for agent_id in sorted(order)]

    forward = doses([1, 2, 3])
    assert forward == pytest.approx(doses([3, 2, 1]))
    assert forward[0] == pytest.approx(forward[-1])


def test_food_delivery_cannot_exceed_a_depleted_pool() -> None:
    """Demand above the pool is shared out, not served first-come."""
    core = _core(food=True)
    core.food_pools[PATHOGEN][ZONE] = 1e-3
    occupants = [_agent(agent_id) for agent_id in range(1, 41)]
    agent_doses: dict[int, float] = {}
    core._pathway_food_contamination(
        0,
        {ZONE: occupants},
        agent_doses,
        ContactTracingMatrix(epoch=0),
        pathogen_id=PATHOGEN,
        profile=core.pathogen_profiles[PATHOGEN],
    )
    delivered = 1e-3 - core.food_pools[PATHOGEN][ZONE]
    assert delivered <= 1e-3 + 1e-12
    assert core.food_pools[PATHOGEN][ZONE] >= 0.0
    assert len(set(round(dose, 15) for dose in agent_doses.values())) == 1


def test_empty_reservoirs_only_decay() -> None:
    """Every persistent dose pool shrinks when no agent deposits mass."""
    core = _core(
        clock=SimClock(epoch_duration_hours=1.0, mode="hours"),
        food=True,
    )
    core.pathogen_profiles[PATHOGEN]["food_contamination"][
        "decay_rate_per_day"
    ] = 0.5
    core.aerosol_pools[ZONE] = 4.0
    core.aerosol_pools_by_pathogen[PATHOGEN][ZONE] = 4.0
    core.surface_pools[ZONE] = 4.0
    core.surface_pools_by_pathogen[PATHOGEN][ZONE] = 4.0
    core.food_pools[PATHOGEN][ZONE] = 4.0

    before = (
        core.aerosol_pools[ZONE],
        core.aerosol_pools_by_pathogen[PATHOGEN][ZONE],
        core.surface_pools[ZONE],
        core.surface_pools_by_pathogen[PATHOGEN][ZONE],
        core.food_pools[PATHOGEN][ZONE],
    )
    core._age_aerosol_pools()
    core._update_surface_pools({})
    core._pathway_food_contamination(
        0,
        {ZONE: []},
        {},
        ContactTracingMatrix(epoch=0),
        pathogen_id=PATHOGEN,
        profile=core.pathogen_profiles[PATHOGEN],
    )
    after = (
        core.aerosol_pools[ZONE],
        core.aerosol_pools_by_pathogen[PATHOGEN][ZONE],
        core.surface_pools[ZONE],
        core.surface_pools_by_pathogen[PATHOGEN][ZONE],
        core.food_pools[PATHOGEN][ZONE],
    )
    assert all(math.isfinite(value) for value in after)
    assert all(value >= 0.0 for value in after)
    assert all(new < old for old, new in zip(before, after))


def test_fomite_delivery_is_conservative_and_intensive() -> None:
    import engines.transmission_core as transmission_core

    core = _core()
    core.surface_pools[ZONE] = 10.0
    core.surface_pools_by_pathogen[PATHOGEN][ZONE] = 10.0
    target = _agent(1)
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
    delivered = 10.0 - core.surface_pools_by_pathogen[PATHOGEN][ZONE]
    expected_rng = np.random.default_rng(19)
    hand_area = expected_rng.uniform(
        *transmission_core.HAND_AREA_CM2_RANGE,
    ) / 1.0e4
    surface_fraction = expected_rng.uniform(
        *transmission_core.SURFACE_CONTACT_FRACTION_RANGE,
    )
    surface_efficiency = np.clip(
        expected_rng.lognormal(*transmission_core.SURFACE_TO_HAND_LOGNORMAL),
        0.0,
        1.0,
    )
    expected_pickup = (
        transmission_core.SURFACE_CONTACTS_PER_HOUR["dining"]
        * surface_fraction
        * hand_area
        / transmission_core.HIGH_TOUCH_AREA_M2["dining"]
        * surface_efficiency
        * 10.0
    )
    mouth_fraction = expected_rng.uniform(
        *transmission_core.MOUTH_CONTACT_FRACTION_RANGE,
    )
    mouth_efficiency = np.clip(
        expected_rng.normal(*transmission_core.HAND_TO_MOUTH_NORMAL),
        0.0,
        1.0,
    )
    mouth_contacts = max(
        0.0,
        expected_rng.normal(*transmission_core.NON_EATING_MOUTH_CONTACTS_PER_HOUR),
    )
    expected_dose = (
        mouth_contacts
        * mouth_fraction
        * mouth_efficiency
        * expected_pickup
    )
    assert delivered == pytest.approx(expected_pickup)
    assert doses[target.agent_id] == pytest.approx(expected_dose)
    assert 0.0 <= delivered <= 10.0
    assert core.surface_pools[ZONE] == pytest.approx(10.0 - delivered)


def test_food_delivery_is_conservative_and_intensive() -> None:
    core = _core(food=True)
    core.food_pools[PATHOGEN][ZONE] = 10.0
    target = _agent(1)
    doses: dict[int, float] = {}
    core._pathway_food_contamination(
        0,
        {ZONE: [target]},
        doses,
        ContactTracingMatrix(epoch=0),
        pathogen_id=PATHOGEN,
        profile=core.pathogen_profiles[PATHOGEN],
    )
    assert doses[target.agent_id] == pytest.approx(0.5)
    assert core.food_pools[PATHOGEN][ZONE] == pytest.approx(9.5)


def test_reservoir_doses_are_invariant_to_scaled_zone_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import engines.transmission_core as transmission_core

    def fomite_dose(
        occupancy: int,
        mass: float,
        high_touch_area: float = 8.0,
    ) -> float:
        monkeypatch.setitem(
            transmission_core.HIGH_TOUCH_AREA_M2,
            "dining",
            high_touch_area,
        )
        core = _core(volume=50.0)
        core.surface_pools[ZONE] = mass
        core.surface_pools_by_pathogen[PATHOGEN][ZONE] = mass
        occupants = [_agent(1)] + [
            _agent(index, immune=True) for index in range(2, occupancy + 1)
        ]
        doses: dict[int, float] = {}
        core._pathway_fomite(
            0,
            {ZONE: occupants},
            doses,
            ContactTracingMatrix(epoch=0),
            [],
            pathogen_id=PATHOGEN,
            profile=core.pathogen_profiles[PATHOGEN],
        )
        return doses[1]

    def food_dose(occupancy: int, mass: float) -> float:
        core = _core(food=True)
        core.food_pools[PATHOGEN][ZONE] = mass
        occupants = [_agent(1)] + [
            _agent(index, immune=True) for index in range(2, occupancy + 1)
        ]
        doses: dict[int, float] = {}
        core._pathway_food_contamination(
            0,
            {ZONE: occupants},
            doses,
            ContactTracingMatrix(epoch=0),
            pathogen_id=PATHOGEN,
            profile=core.pathogen_profiles[PATHOGEN],
        )
        return doses[1]

    assert fomite_dose(1, 10.0) == pytest.approx(
        fomite_dose(2, 10.0),
    )
    assert fomite_dose(1, 10.0, 8.0) == pytest.approx(
        fomite_dose(1, 20.0, 16.0),
    )
    assert food_dose(1, 10.0) == pytest.approx(food_dose(2, 20.0))


def test_emitted_and_direct_contact_dose_are_clock_invariant() -> None:
    hourly_clock = SimClock(epoch_duration_hours=1.0, mode="hours")
    legacy_clock = SimClock(mode="legacy_epoch_day")
    profile = _profile()
    hourly = _agent(1, infected=True, clock=hourly_clock)
    legacy = _agent(1, infected=True, clock=legacy_clock)
    hourly_emission = 0.0
    hourly_dose = 0.0
    hourly_core = _core(clock=hourly_clock)
    legacy_core = _core(clock=legacy_clock)
    target_hourly = _agent(2, clock=hourly_clock)
    target_legacy = _agent(2, clock=legacy_clock)
    for epoch in range(24):
        hourly.infections[PATHOGEN]["time_infected"] = epoch
        emitted = hourly.get_pathogen_shedding(PATHOGEN, profile)
        hourly_emission += emitted
        hourly_dose += hourly_core._direct_contact_dose(
            target_hourly,
            [(hourly, emitted)],
            emitted,
            1,
            1,
            False,
        )
    legacy_emission = legacy.get_pathogen_shedding(PATHOGEN, profile)
    legacy_dose = legacy_core._direct_contact_dose(
        target_legacy,
        [(legacy, legacy_emission)],
        legacy_emission,
        1,
        1,
        False,
    )
    assert hourly_emission == pytest.approx(legacy_emission)
    assert hourly_dose == pytest.approx(legacy_dose)


def test_doses_and_dose_response_are_bounded_and_monotone() -> None:
    core = _core()
    doses = [0.0, 0.1, 1.0, 10.0, 100.0]
    probabilities = [core._dose_response(PATHOGEN, dose) for dose in doses]
    assert all(0.0 <= value <= 1.0 for value in probabilities)
    assert probabilities == sorted(probabilities)
