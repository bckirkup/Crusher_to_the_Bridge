"""Tests for engines.infection_dynamics_bridge."""

from __future__ import annotations

from engines.infection_dynamics_bridge import InfectionStatus, KorkinAgent


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
