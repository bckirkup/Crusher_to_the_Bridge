"""
test_transmission_infection_expanded.py – Expanded coverage for
transmission_core and infection_dynamics_bridge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Covers:
- Dose-response functions (infection_probability, illness_probability)
- Shedding value curves
- KorkinAgent lifecycle (infection, recovery, multi-pathogen)
- TransmissionCore multi-pathway execution (end-to-end)
- Contact tracing matrix structure
- SIR state transitions

Closes #94.
"""

from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from engines.infection_dynamics_bridge import (
    ALPHA,
    ASYMPTOMATIC_SHEDDING,
    BETA,
    DOSE_ADJUSTMENT,
    ETA,
    GAMMA,
    SYMPTOMATIC_SHEDDING,
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
    infection_probability,
    illness_probability,
    shedding_value,
)
from engines.transmission_core import TransmissionCore


# ── Dose-response tests ─────────────────────────────────────────────────

class TestDoseResponse:
    def test_infection_probability_zero_dose(self) -> None:
        assert infection_probability(0.0) == pytest.approx(0.0)

    def test_infection_probability_large_dose(self) -> None:
        p = infection_probability(1e6)
        assert 0.0 < p <= 1.0

    def test_infection_probability_monotonic(self) -> None:
        p1 = infection_probability(10.0)
        p2 = infection_probability(100.0)
        p3 = infection_probability(1000.0)
        assert p1 <= p2 <= p3

    def test_infection_probability_formula(self) -> None:
        dose = 50.0
        expected = 1.0 - math.pow(1.0 + dose / BETA, -ALPHA)
        assert infection_probability(dose) == pytest.approx(expected)

    def test_illness_probability_zero_dose(self) -> None:
        assert illness_probability(0.0) == pytest.approx(0.0)

    def test_illness_probability_large_dose(self) -> None:
        p = illness_probability(1e6)
        assert 0.0 < p <= 1.0

    def test_illness_probability_monotonic(self) -> None:
        p1 = illness_probability(10.0)
        p2 = illness_probability(100.0)
        p3 = illness_probability(1000.0)
        assert p1 <= p2 <= p3


# ── Shedding curve tests ────────────────────────────────────────────────

class TestSheddingCurves:
    def test_symptomatic_day_0(self) -> None:
        val = shedding_value(0, is_symptomatic=True)
        expected = max(1.0, math.pow(10, SYMPTOMATIC_SHEDDING[0] - DOSE_ADJUSTMENT))
        assert val == pytest.approx(expected)

    def test_asymptomatic_day_0(self) -> None:
        val = shedding_value(0, is_symptomatic=False)
        expected = max(1.0, math.pow(10, ASYMPTOMATIC_SHEDDING[0] - DOSE_ADJUSTMENT))
        assert val == pytest.approx(expected)

    def test_shedding_clamped_past_curve(self) -> None:
        val = shedding_value(100, is_symptomatic=True)
        last_val = shedding_value(len(SYMPTOMATIC_SHEDDING) - 1, is_symptomatic=True)
        assert val == pytest.approx(last_val)

    def test_shedding_always_positive(self) -> None:
        for day in range(20):
            assert shedding_value(day, True) >= 1.0
            assert shedding_value(day, False) >= 1.0


# ── KorkinAgent tests ────────────────────────────────────────────────────

class TestKorkinAgent:
    def _make_agent(self, agent_id: int = 0, immune: bool = False) -> KorkinAgent:
        return KorkinAgent(
            agent_id=agent_id,
            role="passenger",
            immune=immune,
            home_zone="Berthing",
            dining_zone="Galley",
            work_zone="Bridge",
            free_zone="Recreation",
            schedule=["Sleep"] * 9 + ["Meal:Breakfast"] * 2 + ["Free"] + ["Meal:Lunch"] * 2 + ["Free"] * 4 + ["Meal:Dinner"] * 2 + ["Free"] * 4,
        )

    def test_initial_susceptible(self) -> None:
        agent = self._make_agent()
        assert agent.infection_status == InfectionStatus.SUSCEPTIBLE
        assert agent.illness_status == IllnessStatus.NOT_ILL
        assert not agent.is_infected
        assert not agent.is_symptomatic
        assert agent.current_shedding == pytest.approx(0.0)

    def test_initial_immune(self) -> None:
        agent = self._make_agent(immune=True)
        assert agent.infection_status == InfectionStatus.IMMUNE
        assert agent.immune is True

    def test_get_location_for_hour(self) -> None:
        agent = self._make_agent()
        assert agent.get_location_for_hour(0) == "Berthing"   # Sleep
        assert agent.get_location_for_hour(9) == "Galley"     # Meal
        assert agent.get_location_for_hour(11) == "Recreation" # Free

    def test_infect_with_pathogen(self) -> None:
        agent = self._make_agent()
        agent.infect_with_pathogen("test_virus", dose=100.0, epoch=3)
        assert agent.is_infected
        assert "test_virus" in agent.infections
        assert agent.infections["test_virus"]["status"] == InfectionStatus.INFECTED
        assert agent.infections["test_virus"]["acquired_particles"] == pytest.approx(100.0)
        assert agent.infections["test_virus"]["infection_epoch"] == 3

    def test_infect_with_pathogen_negative_time_raises(self) -> None:
        agent = self._make_agent()
        with pytest.raises(ValueError):
            agent.infect_with_pathogen("v", dose=10.0, epoch=0, time_infected=-1)

    def test_is_infected_with(self) -> None:
        agent = self._make_agent()
        assert not agent.is_infected_with("virus_a")
        agent.infect_with_pathogen("virus_a", dose=50.0, epoch=0)
        assert agent.is_infected_with("virus_a")
        assert not agent.is_infected_with("virus_b")

    def test_init_pathogen_susceptibility(self) -> None:
        agent = self._make_agent()
        agent.init_pathogen_susceptibility("test_p", 1.5)
        assert agent.susceptibility_multiplier["test_p"] == pytest.approx(1.5)
        agent.init_pathogen_susceptibility("test_p", 2.0)
        assert agent.susceptibility_multiplier["test_p"] == pytest.approx(1.5)  # not overwritten

    def test_update_microflora_disruption(self) -> None:
        agent = self._make_agent()
        profiles = {
            "disrupting_bug": {
                "microflora_disruption": {
                    "causes_disruption": True,
                    "disruption_magnitude": 0.7,
                },
            },
        }
        agent.infect_with_pathogen("disrupting_bug", dose=50.0, epoch=0)
        agent.update_microflora_disruption(profiles)
        assert agent.microflora_disruption_status == pytest.approx(0.7)

    def test_active_pathogen_ids(self) -> None:
        agent = self._make_agent()
        agent.infect_with_pathogen("p1", dose=10.0, epoch=0)
        agent.infect_with_pathogen("p2", dose=20.0, epoch=0)
        ids = agent.active_pathogen_ids
        assert set(ids) == {"p1", "p2"}

    def test_days_post_infection(self) -> None:
        agent = self._make_agent()
        assert agent.days_post_infection == -1
        agent.infect_with_pathogen("v", dose=10.0, epoch=0, time_infected=3)
        assert agent.days_post_infection == 3


# ── TransmissionCore expanded tests ──────────────────────────────────────

class TestTransmissionCoreExpanded:
    def _make_core(
        self,
        seed: int = 42,
        profiles: dict | None = None,
        zone_types: dict | None = None,
    ) -> TransmissionCore:
        return TransmissionCore(
            rng=np.random.default_rng(seed),
            zone_volumes={"Z1": 100.0, "Z2": 50.0, "Z3": 75.0},
            pathogen_profiles=profiles or {},
            zone_types=zone_types or {"Z1": "Free", "Z2": "Dining", "Z3": "Room"},
        )

    def _make_agents(self) -> list[KorkinAgent]:
        schedule = ["Sleep"] * 24
        agents = []
        for i in range(5):
            a = KorkinAgent(
                agent_id=i,
                role="crew" if i < 2 else "passenger",
                immune=(i == 4),
                home_zone="Z3",
                dining_zone="Z2",
                work_zone="Z1",
                free_zone="Z1",
                schedule=schedule,
            )
            a.current_location = ["Z1", "Z1", "Z2", "Z3", "Z1"][i]
            agents.append(a)
        return agents

    def test_pool_initialization(self) -> None:
        core = self._make_core()
        core.initialize_zones(["Z1", "Z2", "Z3"])
        assert "Z1" in core.surface_pools
        assert "Z2" in core.aerosol_pools
        assert "Z3" in core.surface_pools

    def test_execute_transmission_returns_matrix_and_events(self) -> None:
        core = self._make_core()
        core.initialize_zones(["Z1", "Z2", "Z3"])
        agents = self._make_agents()
        mass = {"Z1": 0.0, "Z2": 0.0, "Z3": 0.0}
        matrix, events = core.execute_transmission(
            epoch=0, agents=agents, zone_pathogen_mass=mass,
        )
        assert hasattr(matrix, "epoch")
        assert matrix.epoch == 0
        assert isinstance(events, list)

    def test_execute_transmission_with_infected_agent(self) -> None:
        core = self._make_core()
        core.initialize_zones(["Z1", "Z2", "Z3"])
        agents = self._make_agents()
        # Infect agent 0 so they shed
        agents[0].infection_status = InfectionStatus.INFECTED
        agents[0].illness_status = IllnessStatus.SYMPTOMATIC
        agents[0].time_infected = 3
        mass = {"Z1": 100.0, "Z2": 0.0, "Z3": 0.0}
        matrix, _events = core.execute_transmission(
            epoch=1, agents=agents, zone_pathogen_mass=mass,
        )
        assert matrix.epoch == 1

    def test_pathway_scalars_default(self) -> None:
        core = self._make_core()
        assert core.direct_contact_scalar == pytest.approx(1.0)
        assert core.droplet_scalar == pytest.approx(1.0)
        assert core.hvac_airborne_scalar == pytest.approx(1.0)

    def test_multi_pathogen_food_pool(self) -> None:
        profiles = {
            "noro": {
                "food_contamination": {
                    "enabled": True,
                    "food_zones": ["Z2"],
                },
            },
        }
        core = self._make_core(profiles=profiles, zone_types={"Z2": "Dining"})
        core.initialize_zones(["Z1", "Z2", "Z3"])
        assert "noro" in core.food_pools
        assert core.food_pools["noro"]["Z2"] == pytest.approx(0.0)

    def test_environmental_load(self) -> None:
        profiles = {
            "legionella": {
                "environmental_contamination": {
                    "enabled": True,
                    "baseline_environmental_load": 0.05,
                },
            },
        }
        core = self._make_core(profiles=profiles)
        core.initialize_zones(["Z1", "Z2", "Z3"])
        assert core.environmental_load["legionella"] == pytest.approx(0.05)
