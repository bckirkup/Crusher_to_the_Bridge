"""Tests for multi-pathogen Phase B: dining rotation, food multipliers, env zones."""
from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
    KorkinShipEngine,
)
from engines.transmission_core import TransmissionCore


def _agent(aid: int, loc: str, *, role: str = "passenger", infected: bool = False) -> KorkinAgent:
    a = KorkinAgent(
        agent_id=aid,
        role=role,
        immune=False,
        home_zone=loc,
        dining_zone="MainDining",
        work_zone=loc,
        free_zone="Lounge",
        schedule=["Meal:Lunch"] * 24 if role == "passenger" else ["Work"] * 24,
    )
    a.current_location = loc
    if infected:
        a.infection_status = InfectionStatus.INFECTED
        a.illness_status = IllnessStatus.SYMPTOMATIC
        a.time_infected = 1
    return a


class TestDiningRotation:
    def test_zero_rotation_keeps_assigned_dining(self) -> None:
        agent = _agent(1, "MainDining")
        catalog = [
            {"name": "MainDining", "service_type": "mdr", "max_occupancy": 100},
            {"name": "Windjammer", "service_type": "buffet", "max_occupancy": 500},
        ]
        loc = agent.get_location_for_hour(
            12,
            0.0,
            rng=np.random.default_rng(0),
            dining_catalog=catalog,
            agent_behavior={"dining_rotation_probability": 0.0},
        )
        assert loc == "MainDining"

    def test_rotation_visits_other_venues(self) -> None:
        agent = _agent(1, "MainDining")
        catalog = [
            {"name": "MainDining", "service_type": "mdr", "max_occupancy": 100},
            {"name": "Windjammer", "service_type": "buffet", "max_occupancy": 500},
            {"name": "SpecRest", "service_type": "specialty", "max_occupancy": 50},
        ]
        rng = np.random.default_rng(7)
        behavior = {
            "dining_rotation_probability": 1.0,
            "dining_meal_weights": {
                "lunch": {"buffet": 0.5, "mdr": 0.3, "specialty": 0.2},
            },
        }
        draws = {
            agent.get_location_for_hour(
                12, 0.0, rng=rng, dining_catalog=catalog, agent_behavior=behavior,
            )
            for _ in range(40)
        }
        assert len(draws) >= 2
        assert "Windjammer" in draws or "SpecRest" in draws

    def test_engine_builds_dining_catalog(self) -> None:
        zones = [
            {
                "name": "MainDining",
                "type": "Dining",
                "dining_service_type": "mdr",
                "max_occupancy": 200,
            },
            {
                "name": "LidoBuffet",
                "type": "Dining",
                "dining_service_type": "buffet",
                "max_occupancy": 400,
            },
            {"name": "Lounge", "type": "Free"},
            {"name": "Berthing", "type": "Room"},
        ]
        engine = KorkinShipEngine(
            num_passengers=4,
            num_crew=0,
            initial_infected=0,
            zones=zones,
            seed=1,
            immune_ratio=0.0,
            agent_behavior={"dining_rotation_probability": 0.5},
        )
        assert len(engine._dining_catalog) == 2
        types = {e["service_type"] for e in engine._dining_catalog}
        assert types == {"mdr", "buffet"}


class TestFoodZoneMultipliers:
    def test_buffet_dose_exceeds_mdr(self) -> None:
        profiles = {
            "noro": {
                "food_contamination": {
                    "enabled": True,
                    "growth_rate_per_epoch": 0.0,
                    "decay_rate_per_epoch": 0.0,
                    "food_zones": ["Buffet", "MDR"],
                },
                "dose_response": {"model": "beta_poisson", "alpha": 0.111, "beta": 32.81},
            },
        }
        core = TransmissionCore(
            rng=np.random.default_rng(0),
            zone_volumes={"Buffet": 100.0, "MDR": 100.0},
            zone_types={"Buffet": "Dining", "MDR": "Dining"},
            pathogen_profiles=profiles,
            food_zone_multipliers={"Buffet": 3.0, "MDR": 1.0},
        )
        core.initialize_zones(["Buffet", "MDR"])
        core.food_pools["noro"]["Buffet"] = 100.0
        core.food_pools["noro"]["MDR"] = 100.0

        buffet_pax = _agent(1, "Buffet")
        mdr_pax = _agent(2, "MDR")
        doses: dict[int, float] = {}
        pw: dict[int, dict[str, float]] = {}
        from engines.transmission_core import ContactTracingMatrix

        matrix = ContactTracingMatrix(epoch=1)
        core._pathway_food_contamination(
            1,
            {"Buffet": [buffet_pax], "MDR": [mdr_pax]},
            doses,
            matrix,
            pw,
            pathogen_id="noro",
            profile=profiles["noro"],
        )
        assert doses[1] == pytest.approx(3.0 * doses[2])


class TestZoneScopedEnvironmental:
    def test_legacy_env_without_source_zones(self) -> None:
        profiles = {
            "legionella": {
                "environmental_contamination": {
                    "enabled": True,
                    "colonization_rate_per_epoch": 0.0,
                    "baseline_environmental_load": 100.0,
                    "person_to_person": False,
                },
            },
        }
        core = TransmissionCore(
            rng=np.random.default_rng(0),
            zone_volumes={"A": 100.0, "B": 100.0},
            zone_types={"A": "Free", "B": "Free"},
            pathogen_profiles=profiles,
        )
        core.initialize_zones(["A", "B"])
        assert "legionella" in core.environmental_load
        assert core.env_contamination.get("legionella") in (None, {})

    def test_zone_scoped_only_exposes_matching_zones(self) -> None:
        profiles = {
            "legionella": {
                "environmental_contamination": {
                    "enabled": True,
                    "source_zones": ["Spa", "Pool_*"],
                    "base_emission_rate": 1.0,
                    "exposure_probability_per_epoch": 1.0,
                    "colonization_rate_per_epoch": 0.0,
                    "baseline_environmental_load": 10.0,
                    "person_to_person": False,
                },
                "dose_response": {"model": "beta_poisson", "alpha": 0.111, "beta": 32.81},
            },
        }
        core = TransmissionCore(
            rng=np.random.default_rng(1),
            zone_volumes={"Spa": 50.0, "Pool_Deck": 80.0, "Bridge": 40.0},
            zone_types={"Spa": "Free", "Pool_Deck": "Free", "Bridge": "Free"},
            pathogen_profiles=profiles,
        )
        core.initialize_zones(["Spa", "Pool_Deck", "Bridge"])
        assert "Spa" in core.env_contamination["legionella"]
        assert "Pool_Deck" in core.env_contamination["legionella"]
        assert "Bridge" not in core.env_contamination["legionella"]

        spa = _agent(1, "Spa")
        bridge = _agent(2, "Bridge")
        doses: dict[int, float] = {}
        pw: dict[int, dict[str, float]] = {}
        from engines.transmission_core import ContactTracingMatrix

        matrix = ContactTracingMatrix(epoch=1)
        core._pathway_environmental(
            {"Spa": [spa], "Bridge": [bridge]},
            doses,
            matrix,
            pw,
            pathogen_id="legionella",
            profile=profiles["legionella"],
        )
        assert doses.get(1, 0.0) > 0.0
        assert doses.get(2, 0.0) == 0.0

    def test_zone_match_glob(self) -> None:
        core = TransmissionCore(rng=np.random.default_rng(0))
        assert core._zone_matches("PC_D6_P_F", ["PC_*"])
        assert core._zone_matches("Pool_Deck", ["*Pool*"])
        assert not core._zone_matches("Bridge", ["Spa", "Pool_*"])
