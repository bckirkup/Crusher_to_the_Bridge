"""Tests for engines.infection_dynamics_bridge."""

from __future__ import annotations

import pytest

from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.sim_clock import HOURS, SimClock


def _shedding_agent(
    clock: SimClock,
    *,
    time_infected: int,
    symptomatic: bool = False,
) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=0,
        role="passenger",
        immune=False,
        home_zone="Berthing",
        dining_zone="Galley",
        work_zone="Bridge",
        free_zone="Mess",
        schedule=["Free"] * 24,
    )
    agent.clock = clock
    agent.infect_with_pathogen(
        "test_pathogen",
        dose=1e4,
        epoch=0,
        time_infected=time_infected,
    )
    if symptomatic:
        agent.infections["test_pathogen"]["illness"] = IllnessStatus.SYMPTOMATIC
    return agent


SHEDDING_PROFILE = {
    "shedding_curve_log10": [7.0, 9.0, 11.0, 11.0],
    "asymptomatic_shedding_log10": [7.0, 9.0, 11.0, 11.0],
    "dose_adjustment": 0.0,
    "presymptomatic_shedding_days": 0.5,
}


class TestInfectWithPathogen:
    def test_time_infected_from_parameter(self) -> None:
        agent = KorkinAgent(
            agent_id=0,
            role="crew",
            immune=False,
            home_zone="Berthing",
            dining_zone="Galley",
            work_zone="Bridge",
            free_zone="Mess",
            schedule=["Sleep"] * 24,
        )
        agent.infect_with_pathogen("norwalk_gi", 1e4, 0, time_infected=3)
        assert agent.infections["norwalk_gi"]["time_infected"] == 3
        assert agent.time_infected == 3

    def test_time_infected_defaults_to_zero(self) -> None:
        agent = KorkinAgent(
            agent_id=1,
            role="crew",
            immune=False,
            home_zone="Berthing",
            dining_zone="Galley",
            work_zone="Bridge",
            free_zone="Mess",
            schedule=["Sleep"] * 24,
        )
        agent.infect_with_pathogen("norwalk_gi", 100.0, 5)
        assert agent.infections["norwalk_gi"]["time_infected"] == 0


class TestOnsetAnchoredShedding:
    def test_shedding_is_zero_before_presymptomatic_window(self) -> None:
        agent = _shedding_agent(
            SimClock(epoch_duration_hours=1.0, mode=HOURS),
            time_infected=0,
        )
        infection = agent.infections["test_pathogen"]
        infection["incubation_days"] = 1.2

        assert agent.get_pathogen_shedding(
            "test_pathogen", SHEDDING_PROFILE,
        ) == 0.0

    def test_presymptomatic_shedding_uses_first_curve_value(self) -> None:
        # Rebaselined for the dose-pathway dimensional fix: the curve is a
        # per-day emission, so the host emits the clock's share of it each
        # epoch instead of a whole day's worth per epoch.
        clock = SimClock(epoch_duration_hours=1.0, mode=HOURS)
        agent = _shedding_agent(clock, time_infected=24)
        infection = agent.infections["test_pathogen"]
        infection["incubation_days"] = 1.2

        assert agent.get_pathogen_shedding(
            "test_pathogen", SHEDDING_PROFILE,
        ) == pytest.approx(clock.amount_per_epoch(10.0**7))

    def test_curve_peak_is_indexed_from_realized_onset(self) -> None:
        # Rebaselined for the dose-pathway dimensional fix: per-day curve
        # value converted through the clock.
        clock = SimClock(epoch_duration_hours=1.0, mode=HOURS)
        agent = _shedding_agent(clock, time_infected=48, symptomatic=True)
        infection = agent.infections["test_pathogen"]
        infection["onset_time_infected"] = 0

        assert agent.get_pathogen_shedding(
            "test_pathogen", SHEDDING_PROFILE,
        ) == pytest.approx(clock.amount_per_epoch(10.0**11))

    def test_curve_index_scales_with_epoch_duration(self) -> None:
        # Rebaselined for the dose-pathway dimensional fix: curve *indexing*
        # is still clock-independent, but emission is a per-day quantity, so
        # the invariant is per-day agreement rather than per-epoch equality —
        # a two-hour epoch carries twice an hourly epoch's emission.
        profile = SHEDDING_PROFILE
        one_hour_clock = SimClock(epoch_duration_hours=1.0, mode=HOURS)
        two_hour_clock = SimClock(epoch_duration_hours=2.0, mode=HOURS)
        one_hour = _shedding_agent(
            one_hour_clock, time_infected=48, symptomatic=True,
        )
        two_hours = _shedding_agent(
            two_hour_clock, time_infected=24, symptomatic=True,
        )
        one_hour.infections["test_pathogen"]["onset_time_infected"] = 0
        two_hours.infections["test_pathogen"]["onset_time_infected"] = 0

        one_hour_per_day = (
            one_hour.get_pathogen_shedding("test_pathogen", profile)
            * one_hour_clock.epochs_per_day
        )
        two_hour_per_day = (
            two_hours.get_pathogen_shedding("test_pathogen", profile)
            * two_hour_clock.epochs_per_day
        )

        assert one_hour_per_day == pytest.approx(two_hour_per_day)

    def test_virtual_onset_index_uses_elapsed_fractional_days(self) -> None:
        # Rebaselined for the dose-pathway dimensional fix: per-day curve
        # value converted through the clock.
        clock = SimClock(epoch_duration_hours=1.0, mode=HOURS)
        agent = _shedding_agent(clock, time_infected=round(2.9 * 24))
        infection = agent.infections["test_pathogen"]
        infection["incubation_days"] = 1.2

        assert agent.get_pathogen_shedding(
            "test_pathogen", SHEDDING_PROFILE,
        ) == pytest.approx(clock.amount_per_epoch(10.0**9))

    def test_absent_presymptomatic_field_means_no_shedding_before_onset(self) -> None:
        agent = _shedding_agent(
            SimClock(epoch_duration_hours=1.0, mode=HOURS),
            time_infected=24,
        )
        infection = agent.infections["test_pathogen"]
        infection["incubation_days"] = 1.2
        profile = {
            **SHEDDING_PROFILE,
            "presymptomatic_shedding_days": None,
        }
        profile.pop("presymptomatic_shedding_days")

        assert agent.get_pathogen_shedding("test_pathogen", profile) == 0.0
