"""Behavioral guards for the hand-borne food-contamination chain.

The food route used to deposit a fixed share of a shedder's whole emission
into a well-mixed pool, which no assay measures and which no hygiene lever
could reach (FOOD-ARCH-01). It is now composed the way the fomite route is:
contacts x per-contact transfer x what is on the hand, depleting the hand.
"""

from __future__ import annotations

import numpy as np
import pytest

import engines.transmission_core as transmission_core
from engines.infection_dynamics_bridge import IllnessStatus, KorkinAgent
from engines.sim_clock import HOURS, SimClock
from engines.transmission_core import (
    FOOD_HAND_CONTACTS_PER_DAY,
    ContactTracingMatrix,
    TransmissionCore,
)

PATHOGEN = "test_pathogen"
ZONE = "Main_Dining"


def _profile(food: dict | None = None, **overrides: object) -> dict:
    profile: dict[str, object] = {
        "shedding_curve_log10": [11.0] * 12,
        "asymptomatic_shedding_log10": [11.0] * 12,
        "symptom_onset_day": 0.0,
        "dose_adjustment": 4.0,
        "dose_response": {"model": "exponential", "k": 0.01},
        "hand_inactivation_rate_per_hour": 0.61,
        "hand_hygiene_rate_per_hour": 0.0,
        "food_contamination": {
            "enabled": True,
            "food_zones": [ZONE],
            "growth_rate_per_day": 0.0,
            "decay_rate_per_day": 0.0,
            **(food or {}),
        },
    }
    profile.update(overrides)
    return profile


def _agent(
    agent_id: int = 1,
    *,
    role: str = "passenger",
    infected: bool = True,
) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role=role,
        immune=False,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=["Meal:Lunch"] * 24,
    )
    agent.current_location = ZONE
    if infected:
        agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=24)
        agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
    return agent


def _core(
    *,
    profile: dict | None = None,
    seed: int = 7,
    hours: float = 1.0,
) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={ZONE: 50.0},
        pathogen_profiles={PATHOGEN: profile or _profile()},
        zone_types={ZONE: "Dining"},
        clock=SimClock(epoch_duration_hours=hours, mode=HOURS),
    )
    core.initialize_zones([ZONE])
    return core


def _deposit(core: TransmissionCore, agent: KorkinAgent, hand: float) -> float:
    agent.hand_load_by_pathogen[PATHOGEN] = hand
    profile = core.pathogen_profiles[PATHOGEN]
    deposits = core._food_deposits(
        ZONE, [agent], PATHOGEN, profile, profile["food_contamination"],
    )
    return sum(mass for _agent, mass in deposits)


def _mean_deposit(
    core: TransmissionCore,
    agent: KorkinAgent,
    hand: float,
    draws: int = 400,
) -> float:
    return float(np.mean([_deposit(core, agent, hand) for _ in range(draws)]))


def test_a_shedder_with_clean_hands_contaminates_no_food() -> None:
    """The structural point: the route runs on hand load, not on emission.

    This host sheds 10^11 per gram; under the retired share-of-emission form
    it deposited regardless of what was on its hands.
    """
    core = _core()
    assert _deposit(core, _agent(), 0.0) == pytest.approx(0.0)


def test_deposit_never_exceeds_the_hand_and_leaves_it_depleted() -> None:
    core = _core()
    agent = _agent()
    agent.hand_load_by_pathogen[PATHOGEN] = 1000.0
    profile = core.pathogen_profiles[PATHOGEN]
    for _ in range(50):
        before = agent.hand_load_by_pathogen[PATHOGEN]
        deposits = core._food_deposits(
            ZONE, [agent], PATHOGEN, profile, profile["food_contamination"],
        )
        mass = sum(m for _a, m in deposits)
        after = agent.hand_load_by_pathogen[PATHOGEN]
        assert 0.0 <= mass <= before
        assert after == pytest.approx(before - mass)
        assert after >= 0.0


@pytest.mark.parametrize("hand", [1.0, 10.0, 100.0])
def test_deposit_is_proportional_to_the_hand_load(hand: float) -> None:
    core = _core(seed=13)
    unit = _mean_deposit(core, _agent(), 1.0)
    assert _mean_deposit(_core(seed=13), _agent(), hand) == pytest.approx(
        unit * hand, rel=0.05,
    )


def test_deposit_is_monotone_in_the_food_contact_rate() -> None:
    means = [
        _mean_deposit(
            _core(profile=_profile({"hand_food_contacts_per_day": rate}),
                  seed=17),
            _agent(),
            100.0,
        )
        for rate in (0.0, 0.6, 3.0, 12.0)
    ]
    assert means[0] == pytest.approx(0.0)
    assert means == sorted(means)
    assert means[2] > means[1]


def test_a_crew_food_handler_deposits_more_than_a_diner() -> None:
    """NEARS' ill-food-worker channel exists; its rate is inferred, not measured."""
    hand = 1e6  # far above what the handler multiplier can strip in one epoch
    diner = _mean_deposit(_core(seed=19), _agent(role="passenger"), hand)
    handler = _mean_deposit(_core(seed=19), _agent(role="crew"), hand)
    assert handler > diner
    assert handler == pytest.approx(
        diner * transmission_core.FOOD_HANDLER_CONTACT_MULTIPLIER, rel=0.1,
    )


def test_the_deposit_does_not_move_with_the_faecal_release_adjustment() -> None:
    """Hand load is measured against the curve peak, so the swept Grade D
    release adjustment no longer scales this route."""
    low = _core(profile=_profile(dose_adjustment=2.0), seed=23)
    high = _core(profile=_profile(dose_adjustment=6.0), seed=23)
    agent = _agent()
    assert _mean_deposit(low, agent, 100.0) == pytest.approx(
        _mean_deposit(high, agent, 100.0),
    )


def test_a_confined_shedder_deposits_no_food() -> None:
    core = _core()
    core.zone_types[ZONE] = "Cabin_Corridor"
    core._quarantined_ids = {1}
    assert _deposit(core, _agent(), 1000.0) == pytest.approx(0.0)


def test_a_days_deposit_is_the_same_on_every_clock_grid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A contact count per day, so it divides across the day's epochs."""
    monkeypatch.setattr(
        transmission_core, "HAND_TO_FOOD_TRANSFER_FRACTION_RANGE", (0.05, 0.05),
    )
    totals = []
    for hours in (1.0, 2.0, 6.0):
        core = _core(seed=29, hours=hours)
        agent = _agent()
        epochs = int(round(24.0 / hours))
        totals.append(sum(
            _deposit(core, agent, 100.0) for _ in range(epochs)
        ))
    assert totals[0] == pytest.approx(totals[1], rel=1e-9)
    assert totals[1] == pytest.approx(totals[2], rel=1e-9)


def test_hand_hygiene_reaches_the_food_route() -> None:
    """The lever the retired form could not see.

    With the fomite pathway switched off the food route maintains the hands it
    deposits from, so a hygiene event has to reduce what reaches the pool.
    """
    pools = []
    for rate in (0.0, 4.0):
        profile = _profile(hand_hygiene_rate_per_hour=rate)
        profile["environmental_contamination"] = {"person_to_person": False}
        core = _core(profile=profile, seed=31)
        agent = _agent()
        for epoch in range(24):
            core._pathway_food_contamination(
                epoch,
                {ZONE: [agent]},
                {},
                ContactTracingMatrix(epoch=epoch),
                pathogen_id=PATHOGEN,
                profile=profile,
            )
        pools.append(core.food_pools[PATHOGEN][ZONE])
    assert pools[1] < pools[0]


def test_disabled_food_contamination_stays_a_no_op() -> None:
    profile = _profile({"enabled": False})
    core = _core(profile=profile)
    agent = _agent()
    core._pathway_food_contamination(
        0,
        {ZONE: [agent]},
        {},
        ContactTracingMatrix(epoch=0),
        pathogen_id=PATHOGEN,
        profile=profile,
    )
    assert core.food_pools.get(PATHOGEN, {}).get(ZONE, 0.0) == pytest.approx(0.0)


def test_the_food_route_touches_no_surface_pool() -> None:
    """One deposit per contact: the food route may not also spend the hand on
    surfaces, and the retired share-of-emission term may not be applied on top
    of the contact-level one."""
    profile = _profile()
    profile["environmental_contamination"] = {"person_to_person": False}
    core = _core(profile=profile, seed=41)
    agent = _agent()
    agent.hand_load_by_pathogen[PATHOGEN] = 1e5
    core._pathway_food_contamination(
        0,
        {ZONE: [agent]},
        {},
        ContactTracingMatrix(epoch=0),
        pathogen_id=PATHOGEN,
        profile=profile,
    )
    surface = core.surface_pools_by_pathogen.get(PATHOGEN, {})
    assert surface.get(ZONE, 0.0) == pytest.approx(0.0)
    assert core.surface_pools.get(ZONE, 0.0) == pytest.approx(0.0)
    assert core.food_pools[PATHOGEN][ZONE] > 0.0


def test_pool_and_delivered_dose_stay_finite_and_bounded() -> None:
    profile = _profile()
    profile["environmental_contamination"] = {"person_to_person": False}
    core = _core(profile=profile, seed=43)
    shedder = _agent(agent_id=1)
    eater = _agent(agent_id=2, infected=False)
    doses: dict[int, float] = {}
    for epoch in range(48):
        pool_before = core.food_pools[PATHOGEN][ZONE]
        core._pathway_food_contamination(
            epoch,
            {ZONE: [shedder, eater]},
            doses,
            ContactTracingMatrix(epoch=epoch),
            pathogen_id=PATHOGEN,
            profile=profile,
        )
        pool = core.food_pools[PATHOGEN][ZONE]
        assert np.isfinite(pool)
        assert pool >= 0.0
        # Nothing is delivered that the pool did not hold: with growth and
        # decay off, the pool can only rise by what hands put in it.
        assert pool <= pool_before + 1e5
    assert doses[eater.agent_id] > 0.0
    assert np.isfinite(doses[eater.agent_id])


def test_the_ingestion_fraction_is_a_profile_axis_on_every_grid() -> None:
    """Food-service turnover is declared, not measured, so it is sweepable —
    and a per-day fraction must remove the same share of a standing pool
    whatever the epoch length."""
    standing = []
    for hours in (1.0, 4.0):
        profile = _profile({"ingestion_fraction_per_day": 0.5})
        core = _core(profile=profile, seed=47, hours=hours)
        core.food_pools[PATHOGEN][ZONE] = 1000.0
        eater = _agent(agent_id=2, infected=False)
        for epoch in range(int(round(24.0 / hours))):
            core._pathway_food_contamination(
                epoch,
                {ZONE: [eater]},
                {},
                ContactTracingMatrix(epoch=epoch),
                pathogen_id=PATHOGEN,
                profile=profile,
            )
        standing.append(core.food_pools[PATHOGEN][ZONE])
    assert standing[0] == pytest.approx(standing[1], rel=0.02)
    assert standing[0] < 1000.0


def test_the_shipped_contact_rate_reproduces_the_retired_emission_share() -> None:
    """Change detector on the decomposition, not on a new assumption.

    ``FOOD_HAND_CONTACTS_PER_DAY`` was set so that decomposing the route does
    not move its magnitude at the shipped hand load and release adjustment:
    the mean deposit must still be ~1e-4 of the epoch's emission. If either
    the contact rate or the transfer span moves, this is the deposit level
    that moved with it.
    """
    core = _core(seed=37)
    agent = _agent()
    agent.clock = core.clock
    profile = core.pathogen_profiles[PATHOGEN]
    hand = agent.get_pathogen_hand_target(PATHOGEN, profile)
    emission = agent.get_pathogen_shedding(PATHOGEN, profile)
    assert emission == pytest.approx(1e7 / 24.0)
    retired = emission * 1e-4
    assert FOOD_HAND_CONTACTS_PER_DAY == pytest.approx(0.6)
    assert _mean_deposit(core, agent, hand, draws=2000) == pytest.approx(
        retired, rel=0.1,
    )
