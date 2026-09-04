"""Contract tests for cruise exterior-zone HVAC isolation."""

from __future__ import annotations

import json
from pathlib import Path

from engines.transmission_core import build_hvac_downstream_map

PLATFORMS = Path(__file__).parents[1] / "data" / "platforms"
CRUISE_EXTERIORS = {
    "mega_cruise_5000": {
        "Main_Pool_Deck", "Sports_Court", "Waterpark", "CentralPark",
        "Aqua_Theater",
    },
    "messy_cruise_500": {
        "Main_Pool_Deck", "Sports_Court", "Waterpark",
        "Central_Park_Open_Atrium", "Aqua_Theater",
    },
    "spirit_cruise_3000": {"MainPool", "AftPool", "SportsDeck"},
    "classic_cruise_1900": {"PoolDeck"},
    "expedition_cruise_300": {"Pool_Deck"},
    "expedition_cruise_450": {"PoolDeck"},
}


def _load(platform: str, filename: str) -> dict:
    path = PLATFORMS / platform / filename
    return json.loads(path.read_text(encoding="utf-8"))


def test_cruise_exterior_descriptions_are_not_in_hvac() -> None:
    for platform, expected_exterior in CRUISE_EXTERIORS.items():
        spatial = _load(platform, "spatial_layout.json")
        airflow = _load(platform, "air_flow_paths.json")
        exterior = {
            zone["id"]
            for zone in spatial["zones"]
            if any(
                token in zone.get("description", "").lower()
                for token in ("open-air", "semi-open", "open-aft", "outdoor")
            )
        }
        covered = {
            room for group in airflow["hvac_zones"] for room in group["rooms"]
        }
        assert not expected_exterior & covered
        assert not exterior & covered


def test_cruise_exteriors_do_not_share_dining_ahu() -> None:
    for platform, exterior in CRUISE_EXTERIORS.items():
        airflow = _load(platform, "air_flow_paths.json")
        spatial = _load(platform, "spatial_layout.json")
        dining = {
            zone["id"] for zone in spatial["zones"] if zone["type"] == "Dining"
        }
        for group in airflow["hvac_zones"]:
            rooms = set(group["rooms"])
            assert not (rooms & exterior and rooms & dining)


def test_mega_hvac_downstream_has_no_exterior_to_dining_path() -> None:
    airflow = _load("mega_cruise_5000", "air_flow_paths.json")
    airflow = {**airflow, "adjacency": []}
    downstream = build_hvac_downstream_map(airflow)
    dining = {"MainDining_L", "MainDining_U", "Windjammer", "SpecRest_A", "SpecRest_B"}
    exterior = CRUISE_EXTERIORS["mega_cruise_5000"]
    assert not any(set(downstream.get(zone, [])) & dining for zone in exterior)


def test_cruise_exterior_adjacency_is_retained() -> None:
    for platform, exterior in CRUISE_EXTERIORS.items():
        airflow = _load(platform, "air_flow_paths.json")
        touching = {
            endpoint
            for link in airflow["adjacency"]
            for endpoint in (link["from"], link["to"])
            if endpoint in exterior
        }
        assert touching == exterior
