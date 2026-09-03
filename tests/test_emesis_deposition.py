"""Focused guards for measured, localized emesis deposition."""

from __future__ import annotations

import math

import numpy as np
import pytest

from engines.infection_dynamics_bridge import IllnessStatus, KorkinAgent
from engines.sim_clock import HOURS, SimClock
from engines.transmission_core import (
    EMESIS_TOTAL_SHED_GEC_RANGE,
    ContactTracingMatrix,
    TransmissionCore,
)
from orchestrator_epoch import _advance_agent_pathogen_infections

PATHOGEN = "norwalk_gi"
ZONE = "Cabin_A"


def _profile(**overrides: object) -> dict:
    profile: dict[str, object] = {
        "symptom_onset_day": 0.0,
        "recovery_day": 5,
        "clinical_presentation": {
            "phases": [
                {
                    "name": "acute",
                    "dpi_min": 0,
                    "dpi_max": 2,
                    "features": ["vomiting"],
                },
                {
                    "name": "resolving",
                    "dpi_min": 3,
                    "dpi_max": None,
                    "features": ["watery_diarrhea"],
                },
            ],
        },
        "shedding_curve_log10": [11.0] * 12,
        "asymptomatic_shedding_log10": [11.0] * 12,
        "dose_response": {"model": "exponential", "k": 0.01},
    }
    profile.update(overrides)
    return profile


def _agent(*, symptomatic: bool = True) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=1,
        role="passenger",
        immune=False,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=["Free"] * 24,
    )
    agent.current_location = ZONE
    agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=0)
    agent.infections[PATHOGEN]["onset_time_infected"] = 0
    if symptomatic:
        agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
    return agent


def _core(
    *,
    seed: int = 11,
    clock: SimClock | None = None,
    zone: str = ZONE,
    zone_type: str = "Cabin_Corridor",
) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={zone: 50.0},
        pathogen_profiles={PATHOGEN: _profile()},
        zone_types={zone: zone_type},
        clock=clock or SimClock(epoch_duration_hours=1.0, mode=HOURS),
    )
    core.initialize_zones([zone])
    return core


def _deposit_once(
    core: TransmissionCore,
    agent: KorkinAgent,
    profile: dict,
    *,
    age_days: float = 0.0,
) -> dict:
    agent.clock = core.clock
    agent.infections[PATHOGEN]["time_infected"] = round(
        age_days * core.clock.epochs_per_day,
    )
    agent.emesis_episode_schedule_by_pathogen[PATHOGEN] = [age_days]
    core._deposit_emesis(agent, PATHOGEN, ZONE, 0, profile)
    records = agent.emesis_deposition_records_by_pathogen.get(PATHOGEN, [])
    return records[0] if records else {}


def test_emesis_partition_conserves_episode_load() -> None:
    core = _core()
    record = _deposit_once(core, _agent(), _profile())
    assert (
        record["pool_gain"]
        + record["non_touchable"]
        + record["aerosol_load"]
    ) == pytest.approx(record["episode_load"], rel=1e-12)


def test_expected_emitted_load_matches_ge_cross_check() -> None:
    """Modelled per-illness shed against Ge et al. 2023's measured totals.

    The bracket is Ge's measured per-subject cumulative shed across its dose
    groups. The engine draws the per-illness total log-uniform, so its
    expectation is (high - low) / ln(high / low), and the comparison is
    like-for-like per subject with no withdrawn intermediate in between.
    """
    low, high = EMESIS_TOTAL_SHED_GEC_RANGE
    expected_total = (high - low) / math.log(high / low)
    assert 6.4e5 <= expected_total <= 3.0e7


@pytest.mark.parametrize(
    "overrides",
    [
        {"environmental_faecal_release_log10_g_per_epoch": 0.0},
        {"environmental_faecal_release_log10_g_per_epoch": 8.0},
        {"host_shedding_multiplier": 0.01},
        {"shedding_variance_log10": 4.0},
    ],
)
def test_emesis_is_independent_of_continuous_shedding_inputs(
    overrides: dict[str, float],
) -> None:
    profile_a = _profile()
    profile_b = _profile(**overrides)
    agent_a = _agent()
    agent_b = _agent()
    agent_a.emesis_episode_schedule_by_pathogen[PATHOGEN] = [0.0]
    agent_b.emesis_episode_schedule_by_pathogen[PATHOGEN] = [0.0]
    core_a = _core(seed=17)
    core_b = _core(seed=17)
    record_a = _deposit_once(core_a, agent_a, profile_a)
    record_b = _deposit_once(core_b, agent_b, profile_b)
    assert record_a["episode_load"] == pytest.approx(record_b["episode_load"])
    assert record_a["pool_gain"] == pytest.approx(record_b["pool_gain"])


def test_confinement_does_not_attenuate_emesis() -> None:
    profile = _profile()
    free_core = _core(seed=23)
    confined_core = _core(seed=23)
    free_agent = _agent()
    confined_agent = _agent()
    confined_core._quarantined_ids = {confined_agent.agent_id}
    free_record = _deposit_once(free_core, free_agent, profile)
    confined_record = _deposit_once(confined_core, confined_agent, profile)
    assert confined_record["pool_gain"] == pytest.approx(free_record["pool_gain"])


def test_emesis_total_is_invariant_to_epoch_size() -> None:
    profile = _profile()
    totals = []
    for hours_per_epoch in (1.0, 0.5):
        core = _core(
            seed=31,
            clock=SimClock(epoch_duration_hours=hours_per_epoch, mode=HOURS),
        )
        agent = _agent()
        agent.clock = core.clock
        agent.emesis_episode_schedule_by_pathogen[PATHOGEN] = [0.0, 1.0, 2.0]
        for epoch in range(1 + round(2.0 * core.clock.epochs_per_day)):
            agent.infections[PATHOGEN]["time_infected"] = epoch
            core._deposit_emesis(agent, PATHOGEN, ZONE, epoch, profile)
        totals.append(sum(
            record["episode_load"]
            for record in agent.emesis_deposition_records_by_pathogen[PATHOGEN]
        ))
    assert totals[0] == pytest.approx(totals[1], rel=1e-12)


def test_only_symptomatic_emetic_phase_can_emit() -> None:
    profile = _profile()
    asymptomatic = _agent(symptomatic=False)
    asymptomatic.emesis_episode_schedule_by_pathogen[PATHOGEN] = [0.0]
    assert _deposit_once(_core(), asymptomatic, profile) == {}

    resolving = _agent()
    resolving.emesis_episode_schedule_by_pathogen[PATHOGEN] = [3.0]
    assert _deposit_once(_core(), resolving, profile, age_days=3.0) == {}

    emetic = _agent()
    record = _deposit_once(_core(), emetic, profile)
    assert record["pool_gain"] > 0.0


def test_emesis_schedule_is_cleared_on_reinfection_and_recovery() -> None:
    profile = _profile(recovery_day=0)
    agent = _agent()
    agent.emesis_episode_schedule_by_pathogen[PATHOGEN] = [0.0]
    agent.emesis_deposition_records_by_pathogen[PATHOGEN] = [{"epoch": 0}]
    agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=0)
    assert PATHOGEN not in agent.emesis_episode_schedule_by_pathogen
    assert PATHOGEN not in agent.emesis_deposition_records_by_pathogen

    agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
    agent.infections[PATHOGEN]["onset_time_infected"] = 0
    agent.emesis_episode_schedule_by_pathogen[PATHOGEN] = [0.0]
    agent.emesis_deposition_records_by_pathogen[PATHOGEN] = [{"epoch": 0}]
    _advance_agent_pathogen_infections(
        agent,
        {PATHOGEN: profile},
        np.random.default_rng(3),
    )
    assert PATHOGEN not in agent.emesis_episode_schedule_by_pathogen
    assert PATHOGEN not in agent.emesis_deposition_records_by_pathogen


def test_fomite_route_weight_is_applied_once() -> None:
    core = _core()
    target = _agent(symptomatic=False)
    target.infections.clear()
    profile = _profile(
        transmission_route_weights={
            "direct_contact": 1.0,
            "droplet": 1.0,
            "hvac_airborne": 1.0,
            "fomite": 0.25,
            "food_contamination": 1.0,
            "environmental_source": 1.0,
        },
    )
    core.pathogen_profiles[PATHOGEN] = profile
    core.surface_pools[ZONE] = 100.0
    core.surface_pools_by_pathogen[PATHOGEN] = {ZONE: 100.0}
    core._fomite_pickup_request = lambda *_args: 10.0
    core._hand_to_mouth_dose = lambda *_args: 3.0
    agent_doses: dict[int, float] = {}
    pathway_doses: dict[int, dict[str, float]] = {}
    core._pathway_fomite(
        0,
        {ZONE: [target]},
        agent_doses,
        ContactTracingMatrix(epoch=0),
        [],
        pathway_doses,
        PATHOGEN,
        profile,
    )
    raw = float(pathway_doses[target.agent_id]["fomite"])
    core._apply_route_weights(
        core.pathogen_profiles[PATHOGEN], agent_doses, pathway_doses,
    )
    assert raw == pytest.approx(3.0)
    assert pathway_doses[target.agent_id]["fomite"] == pytest.approx(0.75)
    assert agent_doses[target.agent_id] == pytest.approx(0.75)
