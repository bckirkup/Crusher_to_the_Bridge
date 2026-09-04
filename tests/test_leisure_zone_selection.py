"""Capacity-weighted and access-filtered leisure zone selection."""
from __future__ import annotations

import numpy as np

from crusher_labs import load_config
from engines.infection_dynamics_bridge import (
    KorkinAgent,
    KorkinShipEngine,
    weighted_zone_choice,
)
from orchestrator_init import build_engine


def test_capacity_weighting_orders_empirical_draws() -> None:
    catalog = [
        {"name": "small", "max_occupancy": 100},
        {"name": "medium", "max_occupancy": 500},
        {"name": "large", "max_occupancy": 2000},
    ]
    rng = np.random.default_rng(31)
    draws = [weighted_zone_choice(catalog, rng) for _ in range(12_000)]
    frequencies = {name: draws.count(name) / len(draws) for name in ("small", "medium", "large")}

    assert frequencies["small"] < frequencies["medium"] < frequencies["large"]
    assert frequencies["medium"] - frequencies["small"] > 0.05
    assert frequencies["large"] - frequencies["medium"] > 0.30


def test_mega_leisure_catalog_excludes_service_spaces_but_not_free_zones() -> None:
    engine = build_engine(load_config(), seed=31)
    excluded = {
        "Engine_Room_Aft", "EngControl", "WasteTreat",
        "Laundry_Main", "Central_Stores", "Bridge",
    }
    catalog_names = {entry["name"] for entry in engine._leisure_catalog}

    assert excluded.isdisjoint(catalog_names)
    assert excluded.issubset(set(engine._free_zones))
    passenger_free = {
        agent.free_zone for agent in engine.agents if agent.role == "passenger"
    }
    assert excluded.isdisjoint(passenger_free)


def test_zero_free_rotation_keeps_assigned_zone() -> None:
    agent = KorkinAgent(
        agent_id=1,
        role="passenger",
        immune=False,
        home_zone="Cabin",
        dining_zone="Dining",
        work_zone="Work",
        free_zone="Assigned",
        schedule=["Free"] * 24,
    )
    catalog = [
        {"name": "Assigned", "max_occupancy": 100},
        {"name": "Other", "max_occupancy": 2_000},
    ]

    location = agent.get_location_for_hour(
        12,
        rng=np.random.default_rng(31),
        free_catalog=catalog,
        agent_behavior={"free_zone_rotation_probability": 0.0},
    )

    assert location == "Assigned"


def test_crew_free_zone_preference_still_resolves_full_free_zone_list() -> None:
    engine = KorkinShipEngine(
        num_passengers=0,
        num_crew=4,
        initial_infected=0,
        zones=[
            {"name": "Engine_Room", "type": "Free", "max_occupancy": 100},
            {"name": "Passenger_Lounge", "type": "Free", "max_occupancy": 500},
            {"name": "Crew_Berthing", "type": "Room"},
            {"name": "Dining", "type": "Dining"},
        ],
        agent_classes=[{
            "class_id": "crew_engineering",
            "role_group": "crew",
            "fraction": 1.0,
            "home_zone_preference": "Crew",
            "duty_zone": "Engine",
            "free_zone_preference": "Engine",
        }],
        seed=31,
    )

    assert all(agent.free_zone == "Engine_Room" for agent in engine.agents)
    assert "Engine_Room" in engine._free_zones
    assert "Engine_Room" not in {entry["name"] for entry in engine._leisure_catalog}
