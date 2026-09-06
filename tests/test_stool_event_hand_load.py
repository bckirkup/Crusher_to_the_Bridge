"""Behavioral guards for symptom axes and the stool-event hand channel.

Two mechanisms meet here and must stay apart: continuous RNA emission, which
every shedding host has regardless of symptoms and which the wastewater
sentinel reads, and discrete defecation events, which recontaminate a hand and
are the only channel through which symptom status reaches the fomite and food
routes.
"""

from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.sim_clock import HOURS, SimClock
from engines.transmission_core import (
    BASELINE_STOOL_EVENTS_PER_DAY,
    DIARRHOEA_AXIS,
    DIARRHOEAL_STOOL_EVENTS_PER_DAY,
    VOMITING_AXIS,
    TransmissionCore,
    draw_emesis_schedule,
    draw_symptom_axes,
    has_symptom_axis,
)

PATHOGEN = "test_pathogen"
ZONE = "Public_Lounge"

PHASES = [
    {"name": "acute", "dpi_min": 0, "dpi_max": 2,
     "features": ["vomiting", "watery_diarrhea"]},
    {"name": "resolving", "dpi_min": 3, "dpi_max": None,
     "features": ["watery_diarrhea"]},
]


def _profile(**overrides: object) -> dict:
    profile: dict[str, object] = {
        "shedding_curve_log10": [11.0] * 12,
        "asymptomatic_shedding_log10": [10.5] * 12,
        "symptom_onset_day": 0.0,
        "recovery_day": 3,
        "dose_response": {"model": "exponential", "k": 0.01},
        "hand_inactivation_rate_per_hour": 0.61,
        "hand_hygiene_rate_per_hour": 0.0,
        "clinical_presentation": {"phases": PHASES},
        "stool_events_per_day": {
            "baseline": BASELINE_STOOL_EVENTS_PER_DAY,
            "diarrhoeal": DIARRHOEAL_STOOL_EVENTS_PER_DAY,
        },
    }
    profile.update(overrides)
    return profile


def _agent(
    *,
    agent_id: int = 1,
    symptomatic: bool = True,
    time_infected: int = 24,
) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role="passenger",
        immune=False,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=["Free"] * 24,
    )
    agent.current_location = ZONE
    agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=time_infected)
    inf = agent.infections[PATHOGEN]
    if symptomatic:
        inf["illness"] = IllnessStatus.SYMPTOMATIC
        inf["presented"] = True
        inf["symptom_axes"] = {VOMITING_AXIS: True, DIARRHOEA_AXIS: True}
    else:
        inf["illness"] = IllnessStatus.NOT_ILL
        inf["presented"] = False
        inf["symptom_severity"] = "asymptomatic"
    return agent


def _core(
    *,
    profile: dict | None = None,
    seed: int = 7,
    epoch_hours: float = 1.0,
) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={ZONE: 50.0},
        pathogen_profiles={PATHOGEN: profile or _profile()},
        zone_types={ZONE: "Free"},
        clock=SimClock(epoch_duration_hours=epoch_hours, mode=HOURS),
    )
    core.initialize_zones([ZONE])
    return core


# --- symptom axes ---------------------------------------------------------


def test_axes_are_absent_and_permissive_without_a_declaration() -> None:
    inf: dict[str, object] = {}
    draw_symptom_axes(inf, {"clinical_presentation": {"phases": PHASES}},
                      np.random.default_rng(0))
    assert "symptom_axes" not in inf
    assert has_symptom_axis(inf, VOMITING_AXIS)
    assert has_symptom_axis(inf, DIARRHOEA_AXIS)


def test_declared_shares_reproduce_the_three_symptom_classes() -> None:
    shares = {
        "vomiting": 0.72,
        "diarrhoea_given_vomiting": 0.5,
        "diarrhoea_given_no_vomiting": 1.0,
    }
    profile = {"clinical_presentation": {
        "phases": PHASES, "symptom_axis_probabilities": shares,
    }}
    rng = np.random.default_rng(11)
    classes: dict[tuple[bool, bool], int] = {}
    trials = 4000
    for _ in range(trials):
        inf: dict[str, object] = {}
        draw_symptom_axes(inf, profile, rng)
        axes = inf["symptom_axes"]
        assert isinstance(axes, dict)
        key = (axes[VOMITING_AXIS], axes[DIARRHOEA_AXIS])
        classes[key] = classes.get(key, 0) + 1
    # v&d, v only, d only; and never a symptomatic host with no axis at all.
    assert (False, False) not in classes
    assert classes[(True, True)] / trials == pytest.approx(0.36, abs=0.025)
    assert classes[(True, False)] / trials == pytest.approx(0.36, abs=0.025)
    assert classes[(False, True)] / trials == pytest.approx(0.28, abs=0.025)


def test_a_non_vomiting_host_draws_no_emesis_schedule() -> None:
    profile = _profile()
    for vomits in (True, False):
        agent = _agent()
        agent.infections[PATHOGEN]["symptom_axes"] = {
            VOMITING_AXIS: vomits, DIARRHOEA_AXIS: True,
        }
        draw_emesis_schedule(
            agent, PATHOGEN, profile, np.random.default_rng(3),
        )
        schedule = agent.emesis_episode_schedule_by_pathogen[PATHOGEN]
        load = agent.emesis_episode_load_by_pathogen[PATHOGEN]
        assert bool(schedule) is vomits
        assert (load > 0.0) is vomits


# --- which arm a host defecates on ---------------------------------------


def test_arm_selection_by_symptom_class_and_phase() -> None:
    core = _core()
    profile = _profile()
    rate = core._stool_event_rate_per_day

    acute = _agent()
    assert rate(acute, PATHOGEN, profile) == DIARRHOEAL_STOOL_EVENTS_PER_DAY

    vomiting_only = _agent()
    vomiting_only.infections[PATHOGEN]["symptom_axes"] = {
        VOMITING_AXIS: True, DIARRHOEA_AXIS: False,
    }
    assert rate(vomiting_only, PATHOGEN, profile) == (
        BASELINE_STOOL_EVENTS_PER_DAY
    )

    never_symptomatic = _agent(symptomatic=False)
    assert rate(never_symptomatic, PATHOGEN, profile) == (
        BASELINE_STOOL_EVENTS_PER_DAY
    )

    convalescent = _agent()
    convalescent.infections[PATHOGEN]["illness"] = IllnessStatus.RECOVERED
    assert rate(convalescent, PATHOGEN, profile) == (
        BASELINE_STOOL_EVENTS_PER_DAY
    )

    cleared = _agent()
    cleared.infections[PATHOGEN]["status"] = InfectionStatus.RECOVERED
    assert rate(cleared, PATHOGEN, profile) == BASELINE_STOOL_EVENTS_PER_DAY


def test_a_resolving_host_keeps_the_diarrhoeal_arm_without_vomiting() -> None:
    """The resolving phase declares diarrhoea and not vomiting."""
    core = _core()
    profile = _profile()
    resolving = _agent(time_infected=24 * 4)
    assert core._stool_event_rate_per_day(resolving, PATHOGEN, profile) == (
        DIARRHOEAL_STOOL_EVENTS_PER_DAY
    )
    assert core._emesis_phase(resolving, PATHOGEN, profile) is None


def test_a_profile_without_arms_keeps_the_continuous_hand_path() -> None:
    profile = _profile()
    del profile["stool_events_per_day"]
    core = _core(profile=profile)
    assert core._stool_event_rate_per_day(_agent(), PATHOGEN, profile) is None


# --- the hand channel -----------------------------------------------------


def _mean_hand_load(
    events_per_day: float,
    *,
    epoch_hours: float = 1.0,
    seed: int = 5,
    days: int = 4,
) -> float:
    profile = _profile(stool_events_per_day={
        "baseline": events_per_day, "diarrhoeal": events_per_day,
    })
    core = _core(profile=profile, seed=seed, epoch_hours=epoch_hours)
    agent = _agent()
    loads = []
    epochs = int(days * 24 / epoch_hours)
    for _ in range(epochs):
        core._replenish_hand(agent, PATHOGEN, profile)
        loads.append(agent.hand_load_by_pathogen.get(PATHOGEN, 0.0))
    return float(np.mean(loads))


def test_hand_load_rises_with_stool_frequency_and_stays_under_ceiling(
) -> None:
    ceiling = _agent().get_pathogen_hand_target(PATHOGEN, _profile())
    means = [_mean_hand_load(rate) for rate in (0.43, 1.0, 3.0, 5.63, 8.5)]
    assert all(
        low < high for low, high in zip(means, means[1:], strict=False)
    )
    assert 0.0 < means[0]
    assert means[-1] < ceiling
    # The diarrhoeal arm is worth a factor, not an order of magnitude: the
    # per-event ceiling is the same in both arms.
    assert 1.5 < means[3] / means[1] < 4.0


def test_stool_event_count_is_invariant_across_clock_grids() -> None:
    counts = {}
    for epoch_hours in (0.5, 1.0, 4.0, 12.0):
        core = _core(epoch_hours=epoch_hours, seed=19)
        epochs = int(30 * 24 / epoch_hours)
        events = sum(
            core._stool_event_occurs(DIARRHOEAL_STOOL_EVENTS_PER_DAY)
            for _ in range(epochs)
        )
        counts[epoch_hours] = events / 30.0
    # A 12 h epoch cannot resolve 5.63 events/day, so it saturates; the finer
    # grids must agree with the declared rate.
    assert counts[0.5] == pytest.approx(
        DIARRHOEAL_STOOL_EVENTS_PER_DAY, abs=0.5,
    )
    assert counts[1.0] == pytest.approx(
        DIARRHOEAL_STOOL_EVENTS_PER_DAY, abs=0.8,
    )
    assert counts[4.0] < counts[1.0] < counts[0.5] + 0.5
    assert counts[12.0] <= 2.0


# --- separation from RNA emission and the sentinel ------------------------


def test_rna_emission_is_independent_of_symptom_axes_and_arms() -> None:
    """The wastewater quantity may not move when the event channel does."""
    profile = _profile()
    armless = _profile()
    del armless["stool_events_per_day"]

    acute = _agent()
    vomiting_only = _agent()
    vomiting_only.infections[PATHOGEN]["symptom_axes"] = {
        VOMITING_AXIS: True, DIARRHOEA_AXIS: False,
    }
    baseline = acute.get_pathogen_shedding(PATHOGEN, profile)
    assert baseline > 0.0
    assert vomiting_only.get_pathogen_shedding(PATHOGEN, profile) == baseline
    assert acute.get_pathogen_shedding(PATHOGEN, armless) == baseline


def test_a_never_symptomatic_host_still_sheds_rna() -> None:
    profile = _profile()
    carrier = _agent(symptomatic=False)
    assert carrier.get_pathogen_shedding(PATHOGEN, profile) > 0.0
    core = _core()
    assert core._emesis_phase(carrier, PATHOGEN, profile) is None
