"""Tests for per-agent shedding variance and cabin-mate transmission."""
from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
    draw_shedding_multiplier,
)
from engines.transmission_core import (
    NON_MATE_CONFINEMENT_CONTACT_FACTOR,
    TransmissionCore,
)
from orchestrator_init import assign_cabin_mates, default_cabin_size


def _agent(aid: int, loc: str, infected: bool = False) -> KorkinAgent:
    a = KorkinAgent(
        agent_id=aid,
        role="passenger",
        immune=False,
        home_zone=loc,
        dining_zone="MainDining_L",
        work_zone="Main_Pool_Deck",
        free_zone="Main_Pool_Deck",
        schedule=["home"] * 24,
    )
    if infected:
        a.infection_status = InfectionStatus.INFECTED
        a.illness_status = IllnessStatus.SYMPTOMATIC
        a.time_infected = 1
    a.current_location = loc
    return a


class TestSheddingVariance:
    def test_zero_variance_returns_one(self) -> None:
        rng = np.random.default_rng(0)
        assert draw_shedding_multiplier(rng, {}) == pytest.approx(1.0)
        assert draw_shedding_multiplier(rng, {"shedding_variance_log10": 0.0}) == pytest.approx(1.0)

    def test_multiplier_drawn_at_infection(self) -> None:
        rng = np.random.default_rng(42)
        profile = {"shedding_variance_log10": 1.5}
        agent = _agent(1, "Berthing")
        agent.infect_with_pathogen("norovirus_gii4", 100.0, 0, rng=rng, profile=profile)
        mult = agent.infections["norovirus_gii4"]["shedding_multiplier"]
        assert mult == pytest.approx(2.8646767258185335)
        assert mult > 1.0

    def test_multiplier_scales_get_pathogen_shedding(self) -> None:
        agent = _agent(1, "Berthing", infected=True)
        agent.infect_with_pathogen(
            "test_p",
            10.0,
            0,
            time_infected=1,
            rng=np.random.default_rng(0),
            profile={"shedding_variance_log10": 0.0},
        )
        profile = {
            "shedding_curve_log10": [8.0] * 15,
            "dose_adjustment": 4.0,
            "shedding_variance_log10": 0.0,
        }
        base = agent.get_pathogen_shedding("test_p", profile)
        agent.infections["test_p"]["shedding_multiplier"] = 10.0
        assert agent.get_pathogen_shedding("test_p", profile) == pytest.approx(base * 10.0)

    def test_no_rng_preserves_default_multiplier(self) -> None:
        agent = _agent(1, "Berthing")
        agent.infect_with_pathogen("v", 1.0, 0)
        assert agent.infections["v"]["shedding_multiplier"] == pytest.approx(1.0)


class TestCabinMateAssignment:
    def test_default_cabin_size_by_zone_type(self) -> None:
        assert default_cabin_size("PC_D6_P_F", "Cabin_Corridor", None) == 2
        assert default_cabin_size("CC_D2_M", "Cabin_Corridor", None) == 3
        assert default_cabin_size("Bridge", "Free", None) is None

    def test_assign_cabin_mates_pairs_agents(self) -> None:
        zone = "PC_D6_P_F"
        agents = [_agent(i, zone) for i in range(4)]
        zones = [{"name": zone, "type": "Cabin_Corridor"}]
        assign_cabin_mates(agents, zones)
        assert agents[0].cabin_mate_ids == frozenset({1})
        assert agents[1].cabin_mate_ids == frozenset({0})
        assert agents[2].cabin_mate_ids == frozenset({3})
        assert agents[3].cabin_mate_ids == frozenset({2})


class TestCabinMateTransmission:
    def test_confined_non_mate_receives_minimal_direct_contact(self) -> None:
        zone = "PC_D6_P_F"
        shedder = _agent(1, zone, infected=True)
        confined = _agent(2, zone)
        free_target = _agent(3, zone)
        confined.cabin_mate_ids = frozenset({99})
        core = TransmissionCore(
            rng=np.random.default_rng(42),
            zone_volumes={zone: 1200.0},
            zone_types={zone: "Cabin_Corridor"},
            corridor_direct_contact_factor=0.15,
        )
        core.initialize_zones([zone])
        matrix_free, _ = core.execute_transmission(
            epoch=1,
            agents=[shedder, free_target],
            zone_pathogen_mass={zone: 0.0},
            quarantined_ids=set(),
        )
        matrix_confined, _ = core.execute_transmission(
            epoch=2,
            agents=[shedder, confined],
            zone_pathogen_mass={zone: 0.0},
            quarantined_ids={2},
        )
        assert matrix_confined.shared_room_exposures[0]["dose"] < (
            matrix_free.shared_room_exposures[0]["dose"] * 0.2
        )

    def test_confined_cabin_mate_receives_full_direct_contact(self) -> None:
        zone = "PC_D6_P_F"
        shedder = _agent(1, zone, infected=True)
        confined = _agent(2, zone)
        shedder.cabin_mate_ids = frozenset({2})
        confined.cabin_mate_ids = frozenset({1})
        core = TransmissionCore(
            rng=np.random.default_rng(42),
            zone_volumes={zone: 1200.0},
            zone_types={zone: "Cabin_Corridor"},
            corridor_direct_contact_factor=0.15,
        )
        core.initialize_zones([zone])
        matrix_mate, _ = core.execute_transmission(
            epoch=1,
            agents=[shedder, confined],
            zone_pathogen_mass={zone: 0.0},
            quarantined_ids={2},
        )
        free_target = _agent(3, zone)
        matrix_free, _ = core.execute_transmission(
            epoch=2,
            agents=[shedder, free_target],
            zone_pathogen_mass={zone: 0.0},
            quarantined_ids=set(),
        )
        mate_dose = matrix_mate.shared_room_exposures[0]["dose"]
        free_dose = matrix_free.shared_room_exposures[0]["dose"]
        assert mate_dose > free_dose * NON_MATE_CONFINEMENT_CONTACT_FACTOR * 5
