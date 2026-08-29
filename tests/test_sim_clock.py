"""The one place epochs and days meet, and the progression that reads it.

Two kinds of test here: the conversion contract of ``SimClock``, and
differential tests showing that the clock actually governs natural history —
the same pathogen profile has to clear after incubation plus three symptomatic
days under each supported clock.
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


def test_a_hazard_offset_starts_at_the_threshold_not_the_next_midnight() -> None:
    """A 1.2-day incubation gets its first chance at 1.2 days, then daily."""
    crossings = [e for e in range(0, 80) if crossed_day_boundary(HOURLY, e, 1.2)]
    assert crossings == [29, 53, 77]


def test_a_hazard_offset_is_closed_before_the_threshold() -> None:
    assert not any(crossed_day_boundary(HOURLY, e, 1.2) for e in range(0, 29))


def test_the_legacy_arm_reads_a_physical_delay_on_its_day_long_epoch() -> None:
    """The control arm has to reproduce pre-clock operational timing.

    Its epoch *is* a day of natural history, so a 72-hour microbiology assay is
    three epochs there — the pre-clock ``hours_per_epoch: 24`` result — rather
    than the 72 epochs an hour-long epoch would give, which would be 72 days of
    biology in an arm whose biology still advances a day per epoch.
    """
    assert LEGACY_CLOCK.hours_per_epoch == pytest.approx(24.0)
    assert LEGACY_CLOCK.epochs_for_hours(72) == 3
    assert LEGACY_CLOCK.epochs_for_hours(24) == 1
    assert LEGACY_CLOCK.hours_elapsed(3) == pytest.approx(72.0)


def test_hours_mode_reads_a_physical_delay_on_the_voyage_grid() -> None:
    assert HOURLY.hours_per_epoch == pytest.approx(1.0)
    assert HOURLY.epochs_for_hours(72) == 72
    assert SIX_HOURLY.epochs_for_hours(72) == 12


@pytest.mark.parametrize("declared", [0, 0.0, -1])
def test_a_configured_zero_epoch_duration_is_refused(declared: float) -> None:
    """Zero is a bad declaration, not an absent one; it must not default to 1."""
    with pytest.raises(ValueError, match="must be positive"):
        SimClock.from_config({"voyage": {"epoch_duration_hours": declared}})


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


def test_hourly_clock_clears_after_incubation_plus_three_symptomatic_days() -> None:
    agent = _infected_agent(HOURLY)
    _advance(agent, 95)
    assert agent.infections["noro"]["status"] == InfectionStatus.INFECTED
    _advance(agent, 1)
    assert agent.infections["noro"]["status"] == InfectionStatus.RECOVERED


def test_legacy_clock_clears_after_incubation_plus_three_symptomatic_days() -> None:
    agent = _infected_agent(LEGACY_CLOCK)
    _advance(agent, 3)
    assert agent.infections["noro"]["status"] == InfectionStatus.INFECTED
    _advance(agent, 1)
    assert agent.infections["noro"]["status"] == InfectionStatus.RECOVERED


def test_recovery_tracks_the_configured_epoch_duration() -> None:
    """Four six-hour epochs to the day, so sixteen to a four-day course."""
    agent = _infected_agent(SIX_HOURLY)
    _advance(agent, 15)
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
    [(HOURLY, 96, 4), (LEGACY_CLOCK, 4, 4), (SIX_HOURLY, 16, 4)],
)
def test_the_illness_draw_is_per_day_not_per_epoch(
    clock: SimClock, epochs: int, expected_draws: int,
) -> None:
    """A finer grid must not hand a host more chances to present.

    The incubation day plus three symptomatic days before day-four clearance
    provide four chances at symptoms whatever the epoch length, so a host who
    declines every draw declines exactly four.
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
    profile = {"category": "enteric_viral", "symptom_onset_day": 0.0}

    agent.infections["noro"]["time_infected"] = 2
    early = _compute_infection_delta(
        "hr", agent, {"noro": profile}, responses, boundaries,
    )
    agent.infections["noro"]["time_infected"] = 48
    late = _compute_infection_delta(
        "hr", agent, {"noro": profile}, responses, boundaries,
    )
    assert (early, late) == (1.0, 9.0)


def _wearable_phase_agent(
    clock: SimClock,
    time_infected: int,
    *,
    onset_time_infected: int | None = None,
    incubation_days: float | None = None,
) -> KorkinAgent:
    agent = _infected_agent(clock)
    infection = agent.infections["noro"]
    infection["time_infected"] = time_infected
    if onset_time_infected is not None:
        infection["onset_time_infected"] = onset_time_infected
    if incubation_days is not None:
        infection["incubation_days"] = incubation_days
    return agent


def _wearable_phase_delta(agent: KorkinAgent) -> float:
    responses = {
        "enteric_viral": {
            "hr": {"early": 1.0, "peak": 3.0, "late": 5.0, "recovery": 7.0},
        },
    }
    return _compute_infection_delta(
        "hr",
        agent,
        {"noro": {"category": "enteric_viral"}},
        responses,
        [(0, "early"), (3, "peak"), (8, "late"), (12, "recovery")],
    )


def test_wearable_pre_onset_host_uses_first_phase() -> None:
    agent = _wearable_phase_agent(HOURLY, 12, incubation_days=1.2)
    assert _wearable_phase_delta(agent) == pytest.approx(1.0)


def test_wearable_phase_follows_realized_onset_not_infection_age() -> None:
    realized = _wearable_phase_agent(HOURLY, 96, onset_time_infected=24)
    virtual = _wearable_phase_agent(HOURLY, 96, incubation_days=1.2)

    assert _wearable_phase_delta(realized) == pytest.approx(3.0)
    assert _wearable_phase_delta(virtual) == pytest.approx(1.0)


def test_wearable_phase_progresses_with_onset_age() -> None:
    phases = [
        _wearable_phase_delta(
            _wearable_phase_agent(HOURLY, onset_age * 24, onset_time_infected=0),
        )
        for onset_age in (0, 3, 8)
    ]
    assert phases == [1.0, 3.0, 5.0]


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


def test_onset_is_not_rounded_up_to_a_whole_voyage_day() -> None:
    """A drawn incubation period is realized at its own resolution.

    The illness hazard is per day, but its first opportunity is the epoch that
    crosses this host's drawn period — otherwise every onset lands on the
    24-epoch lattice and the sub-day spread the incubation distribution was
    fitted to disappears from the line list.
    """
    profile = dict(NORO, symptom_onset_day=1.2)
    agent = _infected_agent(HOURLY)
    rng = _AlwaysIllRng()
    onset_epoch = None
    for epoch in range(1, 73):
        _advance_agent_pathogen_infections(agent, {"noro": profile}, rng)
        if (
            onset_epoch is None
            and agent.infections["noro"]["illness"] == IllnessStatus.SYMPTOMATIC
        ):
            onset_epoch = epoch
    assert onset_epoch == 29


def test_late_incubation_extends_recovery_and_resets_symptom_day() -> None:
    """A late onset still gets the full symptomatic recovery duration."""
    profile = {**NORO, "symptom_onset_day": 3.0, "recovery_day": 2}
    agent = _infected_agent(HOURLY)
    rng = _AlwaysIllRng()
    for epoch in range(72):
        _advance_agent_pathogen_infections(agent, {"noro": profile}, rng, epoch=epoch)

    infection = agent.infections["noro"]
    telemetry = agent.to_schema_dict()["pathogen_infections"]["noro"]
    assert infection["status"] == InfectionStatus.INFECTED
    assert infection["illness"] == IllnessStatus.SYMPTOMATIC
    assert telemetry["days_post_infection"] == 3
    assert telemetry["days_since_symptom_onset"] == 1

    for epoch in range(72, 120):
        _advance_agent_pathogen_infections(agent, {"noro": profile}, rng, epoch=epoch)
    assert agent.infections["noro"]["status"] == InfectionStatus.RECOVERED


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
    assert hourly_seed
    assert legacy_seed
    assert set(hourly_seed) == {24}
    assert set(legacy_seed) == {1}


# ── one owner of presentation ────────────────────────────────────────────
#
# Two paths advance a host's natural history: the engine's own fallback and the
# multi-pathogen record. Both write ``agent.illness_status``, which is what the
# sentinel line list reads, so the fallback presenting on its fixed day would
# report onset before the host's drawn incubation period and put the line list
# back on the whole-day lattice.

def _engine_with_a_record(clock: SimClock, *, onset_day: float) -> KorkinShipEngine:
    """An engine whose single host carries a per-pathogen record."""
    engine = KorkinShipEngine(
        num_passengers=1, num_crew=0, initial_infected=0,
        zones=ZONES, seed=1, clock=clock,
    )
    engine.rng = _AlwaysIllRng()  # type: ignore[assignment]
    agent = engine.agents[0]
    agent.infect_with_pathogen("noro", 1e4, 0)
    agent.infections["noro"]["incubation_days"] = onset_day
    return engine


def _engine_with_a_legacy_only_host(clock: SimClock) -> KorkinShipEngine:
    """An engine whose single host was infected without a pathogen record."""
    engine = KorkinShipEngine(
        num_passengers=1, num_crew=0, initial_infected=1,
        zones=ZONES, seed=1, clock=clock,
    )
    engine.rng = _AlwaysIllRng()  # type: ignore[assignment]
    agent = engine.agents[0]
    agent.time_infected = 0
    agent.illness_status = IllnessStatus.NOT_ILL
    assert not agent.infections
    return engine


def test_the_fallback_does_not_present_a_host_that_has_a_drawn_incubation() -> None:
    """Five days of incubation is five days, not the fallback's one."""
    engine = _engine_with_a_record(HOURLY, onset_day=5.0)
    agent = engine.agents[0]
    for _ in range(96):  # four voyage days
        engine._advance_illness_and_recovery()
    assert agent.illness_status == IllnessStatus.NOT_ILL
    assert agent.time_infected == 96  # the counter is still advanced


def test_the_fallback_still_presents_a_host_with_no_pathogen_record() -> None:
    engine = _engine_with_a_legacy_only_host(HOURLY)
    agent = engine.agents[0]
    for _ in range(23):
        engine._advance_illness_and_recovery()
    assert agent.illness_status == IllnessStatus.NOT_ILL
    engine._advance_illness_and_recovery()
    assert agent.illness_status == IllnessStatus.SYMPTOMATIC


def test_the_fallback_offers_no_illness_draw_to_a_record_carrying_host() -> None:
    """Not merely a later draw: the fallback must not draw at all.

    A second Bernoulli on the same day would raise the realized symptomatic
    fraction above the profile's dose response, whatever threshold it used.
    """
    engine = _engine_with_a_record(HOURLY, onset_day=1.0)
    engine.rng = _NeverIllRng()  # type: ignore[assignment]
    for _ in range(72):
        engine._advance_illness_and_recovery()
    assert engine.rng.draws == 0  # type: ignore[attr-defined]


def test_the_fallback_does_not_clear_a_case_it_does_not_own() -> None:
    """Recovery of a record-carrying host is the record's call, not the fallback's.

    Otherwise a pathogen with a recovery day past the fallback's three would be
    cleared at the agent level while its own record is still shedding.
    """
    engine = _engine_with_a_record(HOURLY, onset_day=1.0)
    agent = engine.agents[0]
    for _ in range(96):
        engine._advance_illness_and_recovery()
    assert agent.infection_status == InfectionStatus.INFECTED
    assert agent.infections["noro"]["status"] == InfectionStatus.INFECTED


def test_the_sentinel_visible_onset_is_the_hosts_own_incubation_period() -> None:
    """The agent-level status the line list reads follows the drawn period.

    Both paths are stepped in the order ``ShipSimulation`` steps them — engine
    first, records second — so this is the epoch a sentinel line list would
    report as onset.
    """
    engine = _engine_with_a_record(HOURLY, onset_day=1.2)
    agent = engine.agents[0]
    rng = _AlwaysIllRng()
    onset_epoch = None
    for epoch in range(1, 73):
        engine._advance_illness_and_recovery()
        _advance_agent_pathogen_infections(agent, {"noro": NORO}, rng)
        if onset_epoch is None and agent.illness_status == IllnessStatus.SYMPTOMATIC:
            onset_epoch = epoch
    assert onset_epoch == 29  # 1.2 days, not the fallback's 24 epochs
