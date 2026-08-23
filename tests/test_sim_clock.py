"""The one place epochs and days meet, and the progression that reads it.

Two kinds of test here: the conversion contract of ``SimClock``, and
differential tests showing that the clock actually governs natural history —
the same pathogen profile has to clear in three days of voyage time under the
hourly clock and in three epochs under the legacy one.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from crusher_labs.clinical_presentation import annotate_agent_clinical_presentation
from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
    KorkinShipEngine,
)
from engines.sim_clock import (
    HOURS,
    LEGACY_CLOCK,
    LEGACY_EPOCH_DAY,
    SimClock,
    crossed_day_boundary,
)
from engines.wearable_monitor import _compute_infection_delta
from orchestrator_epoch import _advance_agent_pathogen_infections

HOURLY = SimClock(epoch_duration_hours=1.0, mode=HOURS)
SIX_HOURLY = SimClock(epoch_duration_hours=6.0, mode=HOURS)

NORO = {
    "recovery_day": 3,
    "symptom_onset_day": 1.0,
    "illness_probability": {"eta": 0.508, "gamma": 0.095},
}


# ── conversion contract ──────────────────────────────────────────────────

def test_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError, match="clock mode"):
        SimClock(epoch_duration_hours=1.0, mode="fortnights")


@pytest.mark.parametrize("hours", [0.0, -1.0])
def test_rejects_nonpositive_epoch_duration(hours: float) -> None:
    with pytest.raises(ValueError, match="must be positive"):
        SimClock(epoch_duration_hours=hours, mode=HOURS)


def test_legacy_clock_is_one_day_per_epoch() -> None:
    assert LEGACY_CLOCK.mode == LEGACY_EPOCH_DAY
    assert LEGACY_CLOCK.days_elapsed(3) == pytest.approx(3.0)
    assert LEGACY_CLOCK.epochs_per_day == pytest.approx(1.0)
    assert LEGACY_CLOCK.epochs_for_days(3.0) == pytest.approx(3.0)


def test_hourly_clock_is_twenty_four_epochs_per_day() -> None:
    assert HOURLY.epochs_per_day == pytest.approx(24.0)
    assert HOURLY.days_elapsed(72) == pytest.approx(3.0)
    assert HOURLY.epochs_for_days(3.0) == pytest.approx(72.0)


def test_epoch_duration_scales_the_conversion() -> None:
    assert SIX_HOURLY.epochs_per_day == pytest.approx(4.0)
    assert SIX_HOURLY.days_elapsed(4) == pytest.approx(1.0)
    assert SIX_HOURLY.hours_elapsed(4) == pytest.approx(24.0)


def test_day_index_is_held_stepwise_within_a_day() -> None:
    """A daily shedding curve is a daily observation, so it is not interpolated."""
    assert [HOURLY.day_index(e) for e in (0, 12, 23)] == [0, 0, 0]
    assert HOURLY.day_index(24) == 1
    assert HOURLY.day_index(47) == 1


def test_day_index_is_never_negative() -> None:
    assert HOURLY.day_index(-5) == 0


def test_delay_hours_round_up_to_whole_epochs() -> None:
    assert HOURLY.epochs_for_hours(24) == 24
    assert SIX_HOURLY.epochs_for_hours(5) == 1
    assert SIX_HOURLY.epochs_for_hours(7) == 2
    assert SIX_HOURLY.epochs_for_hours(-3) == 0


def test_from_config_reads_the_voyage_epoch_duration() -> None:
    clock = SimClock.from_config({"voyage": {"epoch_duration_hours": 6}})
    assert clock.epoch_duration_hours == pytest.approx(6.0)
    assert clock.mode == HOURS


def test_from_config_accepts_a_top_level_duration() -> None:
    clock = SimClock.from_config({"epoch_duration_hours": 2})
    assert clock.epoch_duration_hours == pytest.approx(2.0)


def test_from_config_defaults_to_the_physical_reading() -> None:
    assert SimClock.from_config(None).mode == HOURS
    assert SimClock.from_config({}).epoch_duration_hours == pytest.approx(1.0)


def test_legacy_arm_has_to_be_asked_for() -> None:
    clock = SimClock.from_config({"natural_history_clock": LEGACY_EPOCH_DAY})
    assert clock.mode == LEGACY_EPOCH_DAY
    assert clock.days_elapsed(3) == pytest.approx(3.0)


def test_for_run_takes_the_epoch_length_from_the_itinerary() -> None:
    clock = SimClock.for_run({"epoch_duration_hours": 3}, {"epoch_duration_hours": 3})
    assert clock.epoch_duration_hours == pytest.approx(3.0)


def test_two_declared_epoch_durations_are_refused() -> None:
    """A run with two epoch lengths has no defensible natural-history clock."""
    with pytest.raises(ValueError, match="disagrees"):
        SimClock.for_run({"epoch_duration_hours": 24}, {"epoch_duration_hours": 1})


def test_the_mode_may_be_declared_on_the_itinerary() -> None:
    """A platform itinerary is allowed to carry the arm it was written for."""
    clock = SimClock.for_run({}, {"natural_history_clock": LEGACY_EPOCH_DAY})
    assert clock.mode == LEGACY_EPOCH_DAY


def test_two_declared_clock_modes_are_refused() -> None:
    with pytest.raises(ValueError, match="natural_history_clock disagrees"):
        SimClock.for_run(
            {"natural_history_clock": HOURS},
            {"natural_history_clock": LEGACY_EPOCH_DAY},
        )


def test_agreeing_declarations_are_not_a_conflict() -> None:
    clock = SimClock.for_run(
        {"epoch_duration_hours": 6, "natural_history_clock": HOURS},
        {"epoch_duration_hours": 6, "natural_history_clock": HOURS},
    )
    assert (clock.epoch_duration_hours, clock.mode) == (6.0, HOURS)


def test_the_shipped_default_config_is_on_the_hourly_clock() -> None:
    from crusher_labs import load_config

    clock = SimClock.from_config(load_config())
    assert clock.mode == HOURS
    assert clock.epoch_duration_hours == pytest.approx(1.0)


def test_crossed_day_boundary_fires_once_per_day() -> None:
    crossings = [e for e in range(0, 49) if crossed_day_boundary(HOURLY, e)]
    assert crossings == [0, 24, 48]


def test_every_legacy_epoch_is_a_day_boundary() -> None:
    assert all(crossed_day_boundary(LEGACY_CLOCK, e) for e in range(5))


# ── progression reads the clock ──────────────────────────────────────────

ZONES = [
    {"name": "Berthing", "type": "Room"},
    {"name": "MainDining", "type": "Dining"},
    {"name": "Bridge", "type": "Work"},
    {"name": "Lounge", "type": "Free"},
]


def _infected_agent(clock: SimClock) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=0,
        role="passenger",
        immune=False,
        home_zone="Berthing",
        dining_zone="MainDining",
        work_zone="Bridge",
        free_zone="Lounge",
        schedule=["Berthing"],
    )
    agent.clock = clock
    agent.infect_with_pathogen("noro", 1e4, 0)
    return agent


def _advance(agent: KorkinAgent, epochs: int) -> None:
    rng = np.random.default_rng(7)
    for _ in range(epochs):
        _advance_agent_pathogen_infections(agent, {"noro": NORO}, rng)


def test_hourly_clock_holds_a_case_open_for_three_voyage_days() -> None:
    agent = _infected_agent(HOURLY)
    _advance(agent, 71)
    assert agent.infections["noro"]["status"] == InfectionStatus.INFECTED
    _advance(agent, 1)
    assert agent.infections["noro"]["status"] == InfectionStatus.RECOVERED


def test_legacy_clock_clears_the_same_case_in_three_epochs() -> None:
    agent = _infected_agent(LEGACY_CLOCK)
    _advance(agent, 2)
    assert agent.infections["noro"]["status"] == InfectionStatus.INFECTED
    _advance(agent, 1)
    assert agent.infections["noro"]["status"] == InfectionStatus.RECOVERED


def test_recovery_tracks_the_configured_epoch_duration() -> None:
    """Four six-hour epochs to the day, so twelve epochs to a three-day case."""
    agent = _infected_agent(SIX_HOURLY)
    _advance(agent, 11)
    assert agent.infections["noro"]["status"] == InfectionStatus.INFECTED
    _advance(agent, 1)
    assert agent.infections["noro"]["status"] == InfectionStatus.RECOVERED


def test_onset_waits_for_a_day_of_incubation_on_the_hourly_grid() -> None:
    """A host who accepts every draw still cannot present before day one."""
    agent = _infected_agent(HOURLY)
    rng = _AlwaysIllRng()
    for _ in range(23):
        _advance_agent_pathogen_infections(agent, {"noro": NORO}, rng)
    assert agent.infections["noro"]["illness"] == IllnessStatus.NOT_ILL
    _advance_agent_pathogen_infections(agent, {"noro": NORO}, rng)
    assert agent.infections["noro"]["illness"] == IllnessStatus.SYMPTOMATIC


class _AlwaysIllRng:
    """Accepts every illness draw it is offered."""

    def random(self) -> float:
        return 0.0


class _NeverIllRng:
    """Counts illness draws and refuses every one of them."""

    def __init__(self) -> None:
        self.draws = 0

    def random(self) -> float:
        self.draws += 1
        return 1.0


@pytest.mark.parametrize(
    ("clock", "epochs", "expected_draws"),
    [(HOURLY, 72, 3), (LEGACY_CLOCK, 3, 3), (SIX_HOURLY, 12, 3)],
)
def test_the_illness_draw_is_per_day_not_per_epoch(
    clock: SimClock, epochs: int, expected_draws: int,
) -> None:
    """A finer grid must not hand a host more chances to present.

    Three days of natural history is three chances at symptoms whatever the
    epoch length, so a host who declines every draw declines exactly three.
    """
    agent = _infected_agent(clock)
    rng = _NeverIllRng()
    for _ in range(epochs):
        _advance_agent_pathogen_infections(agent, {"noro": NORO}, rng)
    assert rng.draws == expected_draws
    assert agent.infections["noro"]["illness"] == IllnessStatus.RECOVERED


def test_shedding_curve_index_is_held_across_a_day() -> None:
    curve = [0.0, 9.0, 5.0, 1.0]
    profile = {"shedding_curve": curve, "shedding_adjustment": 1.0}
    agent = _infected_agent(HOURLY)
    agent.infections["noro"]["illness"] = IllnessStatus.SYMPTOMATIC
    agent.infections["noro"]["time_infected"] = 24
    first = agent.get_pathogen_shedding("noro", profile)
    agent.infections["noro"]["time_infected"] = 47
    assert agent.get_pathogen_shedding("noro", profile) == pytest.approx(first)
    agent.infections["noro"]["time_infected"] = 48
    assert agent.get_pathogen_shedding("noro", profile) != pytest.approx(first)


def test_engine_hands_its_clock_to_every_agent() -> None:
    engine = KorkinShipEngine(
        num_passengers=4,
        num_crew=1,
        initial_infected=1,
        zones=ZONES,
        seed=1,
        clock=HOURLY,
    )
    assert all(a.clock is HOURLY for a in engine.agents)


def test_downstream_consumers_are_handed_days_not_epoch_counts() -> None:
    """The payload is the boundary: everything past it reads ``days_post_infection``.

    Clinical presentation phases, the wearable phase map and the sentinel line
    list all index on that field, so the conversion has to happen once here
    rather than in each consumer.
    """
    agent = _infected_agent(HOURLY)
    agent.infections["noro"]["time_infected"] = 47
    agent.time_infected = 47
    payload = agent.to_schema_dict()
    assert payload["pathogen_infections"]["noro"]["days_post_infection"] == 1
    assert payload["days_post_infection"] == 1


def test_the_wearable_phase_advances_on_voyage_days() -> None:
    """A wearable phase boundary at day 2 must not fire two epochs in."""
    boundaries = [(0, "incubation"), (2, "symptomatic")]
    agent = _infected_agent(HOURLY)
    responses = {"enteric_viral": {"hr": {"incubation": 1.0, "symptomatic": 9.0}}}

    agent.infections["noro"]["time_infected"] = 2
    early = _compute_infection_delta(
        "hr", agent, {"noro": {"category": "enteric_viral"}}, responses, boundaries,
    )
    agent.infections["noro"]["time_infected"] = 48
    late = _compute_infection_delta(
        "hr", agent, {"noro": {"category": "enteric_viral"}}, responses, boundaries,
    )
    assert (early, late) == (1.0, 9.0)


def test_clinical_phases_resolve_on_the_converted_day() -> None:
    """A dpi-keyed presentation phase is chosen by voyage day, not epoch count."""
    presentation = {
        "phases": [
            {"dpi_min": 0, "dpi_max": 0, "syndromes": ["gastrointestinal"]},
            {"dpi_min": 2, "dpi_max": None, "syndromes": ["systemic_febrile"]},
        ],
    }
    profiles = {"noro": {"clinical_presentation": presentation}}
    agent = _infected_agent(HOURLY)
    agent.infections["noro"]["illness"] = IllnessStatus.SYMPTOMATIC

    agent.infections["noro"]["time_infected"] = 12
    day_zero = annotate_agent_clinical_presentation(agent.to_schema_dict(), profiles)
    agent.infections["noro"]["time_infected"] = 60
    day_two = annotate_agent_clinical_presentation(agent.to_schema_dict(), profiles)

    assert day_zero["observed_syndromes"] == ["gastrointestinal"]
    assert day_zero["days_since_symptom_onset"] == 1
    assert day_two["observed_syndromes"] == ["systemic_febrile"]
    assert day_two["days_since_symptom_onset"] == 2


def test_index_cases_are_seeded_one_day_in_on_either_clock() -> None:
    """An index case starts at the shedding peak, which is a day, not an epoch."""
    hourly = KorkinShipEngine(
        num_passengers=4, num_crew=1, initial_infected=1,
        zones=ZONES, seed=1, clock=HOURLY,
    )
    legacy = KorkinShipEngine(
        num_passengers=4, num_crew=1, initial_infected=1,
        zones=ZONES, seed=1, clock=LEGACY_CLOCK,
    )
    hourly_seed = [a.time_infected for a in hourly.agents if a.is_infected]
    legacy_seed = [a.time_infected for a in legacy.agents if a.is_infected]
    assert hourly_seed and legacy_seed
    assert set(hourly_seed) == {24}
    assert set(legacy_seed) == {1}
