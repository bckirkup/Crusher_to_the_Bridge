"""DINE-SEG-01: crew dine in the crew mess, passengers in the passenger venues.

The outbreak record credits the crew attack-rate deficit to segregated crew
sleeping, dining and boarding areas. Before this change every agent's fixed
dining venue was drawn uniformly from every Dining zone, so most crew took
their meals in the passenger dining rooms and a share of passengers ate in the
crew mess or the galley. These tests hold the venue draw to the role's side of
the line on every shipped hull and on the legacy no-class path, keep crew
*work* in passenger venues untouched, and check the per-meal rotation respects
the same line. No epidemiological outcome is asserted.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from crusher_labs import load_config
from engines.infection_dynamics_bridge import (
    CREW_DINING_SERVICE_TYPES,
    PASSENGER_DINING_SERVICE_TYPES,
    KorkinShipEngine,
)
from orchestrator_init import load_spatial_layout

REPO = Path(__file__).resolve().parents[1]
HULLS = [
    "expedition_cruise_450",
    "classic_cruise_1900",
    "spirit_cruise_3000",
    "mega_cruise_5000",
]


def _hull_zones(hull: str) -> list[dict]:
    cfg = {"ship_graph": {"spatial_layout": f"data/platforms/{hull}/spatial_layout.json"}}
    zones = load_spatial_layout(cfg)
    assert zones is not None
    return zones


def _service_types(hull: str) -> dict[str, str]:
    doc = json.loads((REPO / "data" / "platforms" / hull / "spatial_layout.json").read_text())
    return {
        z["id"]: z["dining_service_type"]
        for z in doc["zones"]
        if z["type"] == "Dining"
    }


def _engine(zones: list[dict], seed: int, agent_classes: list[dict] | None) -> KorkinShipEngine:
    return KorkinShipEngine(
        num_passengers=300,
        num_crew=150,
        initial_infected=0,
        zones=zones,
        seed=seed,
        agent_classes=agent_classes,
    )


class TestTheLineOnEveryHull:
    @pytest.mark.parametrize("hull", HULLS)
    @pytest.mark.parametrize("seed", [1, 9])
    def test_crew_eat_in_a_crew_mess_and_passengers_never_do(self, hull: str, seed: int) -> None:
        graph = load_config()["ship_graph"]
        engine = _engine(_hull_zones(hull), seed, graph["agent_classes"])
        stype = _service_types(hull)
        crew_venues = {a.dining_zone for a in engine.agents if a.role == "crew"}
        pax_venues = {a.dining_zone for a in engine.agents if a.role == "passenger"}
        assert crew_venues
        assert pax_venues
        assert {stype[v] for v in crew_venues} <= CREW_DINING_SERVICE_TYPES
        assert {stype[v] for v in pax_venues} <= PASSENGER_DINING_SERVICE_TYPES
        assert not crew_venues & pax_venues

    @pytest.mark.parametrize("hull", HULLS)
    def test_every_passenger_venue_of_the_hull_is_used(self, hull: str) -> None:
        graph = load_config()["ship_graph"]
        engine = _engine(_hull_zones(hull), 4, graph["agent_classes"])
        stype = _service_types(hull)
        declared = {v for v, t in stype.items() if t in PASSENGER_DINING_SERVICE_TYPES}
        used = {a.dining_zone for a in engine.agents if a.role == "passenger"}
        assert used == declared

    def test_legacy_no_class_path_draws_the_same_line(self) -> None:
        zones = _hull_zones("expedition_cruise_450")
        engine = _engine(zones, 2, None)
        stype = _service_types("expedition_cruise_450")
        for a in engine.agents:
            allowed = (
                CREW_DINING_SERVICE_TYPES if a.role == "crew"
                else PASSENGER_DINING_SERVICE_TYPES
            )
            assert stype[a.dining_zone] in allowed


class TestWorkIsNotDining:
    def test_crew_still_work_passenger_venues(self) -> None:
        graph = load_config()["ship_graph"]
        engine = _engine(_hull_zones("expedition_cruise_450"), 6, graph["agent_classes"])
        stype = _service_types("expedition_cruise_450")
        crew = [a for a in engine.agents if a.role == "crew"]
        working_pax_venues = [
            a for a in crew
            if stype.get(a.work_zone) in PASSENGER_DINING_SERVICE_TYPES
        ]
        assert working_pax_venues, "some crew work the passenger dining rooms"
        assert all(stype[a.dining_zone] in CREW_DINING_SERVICE_TYPES for a in working_pax_venues)


class TestCapacityWeighting:
    def test_larger_venue_seats_more_of_its_side(self) -> None:
        zones = _hull_zones("expedition_cruise_450")
        counts: dict[str, int] = {}
        for seed in range(4):
            for a in _engine(zones, seed, None).agents:
                if a.role == "passenger":
                    counts[a.dining_zone] = counts.get(a.dining_zone, 0) + 1
        assert counts["MainDining"] > counts["CasualDining"]


class TestFallbacks:
    def test_a_layout_without_a_crew_mess_feeds_crew_somewhere_but_not_a_galley(self) -> None:
        zones = [
            {"name": "Berthing", "type": "Room"},
            {"name": "MDR", "type": "Dining", "dining_service_type": "mdr"},
            {"name": "Galley", "type": "Dining", "dining_service_type": "galley"},
            {"name": "Deck", "type": "Free"},
        ]
        engine = _engine(zones, 3, None)
        assert {a.dining_zone for a in engine.agents} == {"MDR"}


class TestRotationRespectsTheLine:
    def test_passenger_rotation_never_lands_in_a_crew_mess(self) -> None:
        zones = _hull_zones("classic_cruise_1900")
        engine = _engine(zones, 8, None)
        stype = _service_types("classic_cruise_1900")
        rng = np.random.default_rng(0)
        behavior = {"dining_rotation_probability": 1.0, "dining_meal_weights": {}}
        for a in engine.agents[:80]:
            for meal in ("Meal:Breakfast", "Meal:Lunch", "Meal:Dinner"):
                venue = a._resolve_dining_location(
                    activity=meal, rng=rng,
                    dining_catalog=engine._dining_catalog, agent_behavior=behavior,
                )
                allowed = (
                    CREW_DINING_SERVICE_TYPES if a.role == "crew"
                    else PASSENGER_DINING_SERVICE_TYPES
                )
                assert stype[venue] in allowed
