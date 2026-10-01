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

import engines.transmission_core as transmission_core
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
    reservoir_mode: str | None = None,
) -> TransmissionCore:
    cfg = (
        {"transmission": {"hand_reservoir_mode": reservoir_mode}}
        if reservoir_mode
        else {}
    )
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={ZONE: 50.0},
        pathogen_profiles={PATHOGEN: profile or _profile()},
        zone_types={ZONE: "Free"},
        clock=SimClock(epoch_duration_hours=epoch_hours, mode=HOURS),
        cfg=cfg,
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
        load = agent.emesis_titre_gec_per_ml_by_pathogen[PATHOGEN]
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
    reservoir_mode: str | None = None,
) -> float:
    profile = _profile(stool_events_per_day={
        "baseline": events_per_day, "diarrhoeal": events_per_day,
    })
    core = _core(
        profile=profile, seed=seed, epoch_hours=epoch_hours,
        reservoir_mode=reservoir_mode,
    )
    agent = _agent()
    loads = []
    epochs = int(days * 24 / epoch_hours)
    for _ in range(epochs):
        core._replenish_hand(agent, PATHOGEN, profile)
        loads.append(agent.hand_load_by_pathogen.get(PATHOGEN, 0.0))
    return float(np.mean(loads))


def test_hand_load_rises_with_stool_frequency_and_stays_under_ceiling(
) -> None:
    # This shape guard predates the reservoir repair: the ratio band is a
    # change-detector on the spike-decay mechanism, where the per-event
    # ceiling is identical in both stool arms. The wash arm legitimately
    # steepens the ratio (post-wash residuals plus a thinned first-seen
    # floor shrink the low-frequency mean more than the high-frequency
    # one), so the guard pins the labelled baseline it was authored for.
    ceiling = _agent().get_pathogen_hand_target(PATHOGEN, _profile())
    means = [
        _mean_hand_load(rate, reservoir_mode="spike_decay")
        for rate in (0.43, 1.0, 3.0, 5.63, 8.5)
    ]
    assert all(
        low < high for low, high in zip(means, means[1:], strict=False)
    )
    assert 0.0 < means[0]
    assert means[-1] < ceiling
    # The diarrhoeal arm is worth a factor, not an order of magnitude: the
    # per-event ceiling is the same in both arms.
    assert 1.5 < means[3] / means[1] < 4.0


def test_the_wash_arm_suppresses_the_post_event_load() -> None:
    """wash_reuptake: no epoch carries more than the unsuppressed spike.

    Every stool event ends in a wash, so the modal post-visit state is a
    suppressed residual -- the ordering-flip mechanism Liu's post-bathroom
    samples show. Pinned to the labelled baseline it was authored for:
    under hygiene_cycle the post-visit wash is compliance-gated, so most
    visits carry no suppression at all (NORO-HAND-PRACTICE-01).
    """
    profile = _profile(stool_events_per_day={
        "baseline": 20.0, "diarrhoeal": 20.0,
    })
    core = _core(
        profile=profile, seed=5, reservoir_mode="wash_reuptake",
    )
    agent = _agent()
    target = agent.get_pathogen_hand_target(PATHOGEN, profile)
    suppressed = 0
    epochs = 96
    for _ in range(epochs):
        core._replenish_hand(agent, PATHOGEN, profile)
        load = agent.hand_load_by_pathogen[PATHOGEN]
        assert load <= target
        suppressed += load < target * 10 ** -0.5
    assert suppressed / epochs > 0.5


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


# --- the hygiene_cycle arm (NORO-HAND-PRACTICE-01) ------------------------


def _mean_hand_load_under_practice(
    *,
    seed: int = 11,
    days: int = 4,
    events_per_day: float = 5.63,
    routine_washes: tuple[float, float] | None = None,
    monkeypatch: pytest.MonkeyPatch | None = None,
) -> float:
    if routine_washes is not None and monkeypatch is not None:
        monkeypatch.setattr(
            transmission_core, "ROUTINE_WASHES_PER_DAY_RANGE", routine_washes,
        )
    profile = _profile(stool_events_per_day={
        "baseline": events_per_day, "diarrhoeal": events_per_day,
    })
    core = _core(profile=profile, seed=seed)
    agent = _agent()
    loads = []
    for _ in range(days * 24):
        core._replenish_hand(agent, PATHOGEN, profile)
        loads.append(agent.hand_load_by_pathogen[PATHOGEN])
    return float(np.mean(loads))


def test_hygiene_cycle_keeps_the_load_under_the_visit_ceiling() -> None:
    """Invariant: ticks and spikes can never exceed the contamination load."""
    core = _core(seed=13)
    agent = _agent()
    profile = _profile()
    target = agent.get_pathogen_hand_target(PATHOGEN, profile)
    for _ in range(96):
        core._replenish_hand(agent, PATHOGEN, profile)
        assert agent.hand_load_by_pathogen[PATHOGEN] <= target


def test_hygiene_cycle_draws_the_practice_traits_once() -> None:
    """Compliance and the two routine rates are per-infection traits."""
    core = _core(seed=5)
    agent = _agent()
    profile = _profile()
    core._replenish_hand(agent, PATHOGEN, profile)
    first = dict(agent.hand_practice_by_pathogen[PATHOGEN])
    for _ in range(24):
        core._replenish_hand(agent, PATHOGEN, profile)
    assert agent.hand_practice_by_pathogen[PATHOGEN] == first
    assert set(first) == {
        "wash_compliance", "routine_washes_per_day", "self_contacts_per_day",
    }


def test_hygiene_cycle_marks_wet_and_dry_epochs_differently() -> None:
    """The deposit-side factor sits in (0, 1] and varies by epoch."""
    core = _core(seed=7)
    agent = _agent()
    profile = _profile()
    factors = set()
    for _ in range(96):
        core._replenish_hand(agent, PATHOGEN, profile)
        factors.add(round(
            agent.hand_wet_transfer_by_pathogen[PATHOGEN], 6,
        ))
    assert all(0.0 < f <= 1.0 for f in factors)
    assert len(factors) > 1


def test_hygiene_cycle_suppresses_less_than_the_deterministic_wash() -> None:
    """Arm sensitivity: compliance-gated washes leave more mass post-visit
    than the wash_reuptake baseline's deterministic wash."""
    under_practice = _mean_hand_load_under_practice(
        seed=17, events_per_day=20.0,
    )
    profile = _profile(stool_events_per_day={
        "baseline": 20.0, "diarrhoeal": 20.0,
    })
    core = _core(profile=profile, seed=17, reservoir_mode="wash_reuptake")
    agent = _agent()
    loads = []
    for _ in range(96):
        core._replenish_hand(agent, PATHOGEN, profile)
        loads.append(agent.hand_load_by_pathogen[PATHOGEN])
    assert under_practice > float(np.mean(loads))


def test_routine_wash_frequency_moves_the_hand_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Graded sensitivity on the new term, not a golden: more routine
    washes per day -> lower mean hand load, same seeds and profile."""
    low = _mean_hand_load_under_practice(
        routine_washes=(0.5, 0.5), monkeypatch=monkeypatch,
    )
    monkeypatch.undo()
    high = _mean_hand_load_under_practice(
        routine_washes=(20.0, 20.0), monkeypatch=monkeypatch,
    )
    assert low > high
