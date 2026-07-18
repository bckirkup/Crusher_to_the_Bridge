"""Tests for platform graywater zone resolution and ship-wide wastewater pooling."""

from __future__ import annotations

import json
import os

import pytest

from orchestrator_epoch import (
    build_wastewater_pathogen_mass,
    build_wastewater_pathogen_mass_by_id,
    compute_zone_microflora_shifts,
)
from orchestrator_init import resolve_graywater_zones

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORMS_DIR = os.path.join(REPO_ROOT, "data", "platforms")


def _layout_path(platform_id: str) -> str:
    return os.path.join(PLATFORMS_DIR, platform_id, "spatial_layout.json")


def _cfg_for_platform(platform_id: str) -> dict:
    return {
        "ship_graph": {
            "spatial_layout": f"data/platforms/{platform_id}/spatial_layout.json",
        },
        "microflora": {},
    }


@pytest.mark.parametrize(
    "platform_id,expected",
    [
        ("destroyer_baseline", ["Engine_Room"]),
        ("mega_cruise_5000", ["Engine_Room_Aft"]),
        ("enterprise_galaxy_tng", ["MainEng"]),
    ],
)
def test_resolve_graywater_zones_from_platform(platform_id: str, expected: list[str]) -> None:
    cfg = _cfg_for_platform(platform_id)
    with open(_layout_path(platform_id), encoding="utf-8") as fh:
        layout = json.load(fh)
    zone_names = [z["id"] for z in layout["zones"]]
    assert resolve_graywater_zones(cfg, zone_names) == expected


def test_resolve_graywater_zones_config_override() -> None:
    cfg = _cfg_for_platform("mega_cruise_5000")
    cfg["microflora"]["graywater_zones"] = ["WasteTreat"]
    zone_names = ["Bridge", "WasteTreat"]
    assert resolve_graywater_zones(cfg, zone_names) == ["WasteTreat"]


def test_resolve_graywater_zones_fallback_to_all_zones() -> None:
    cfg = {"ship_graph": {}, "microflora": {}}
    zone_names = ["Bridge", "Galley"]
    assert resolve_graywater_zones(cfg, zone_names) == zone_names


def test_wastewater_pathogen_mass_pools_ship_wide() -> None:
    zone_surface = {
        "Bridge": 100.0,
        "Galley": 50.0,
        "Engine_Room_Aft": 5.0,
    }
    pooled = build_wastewater_pathogen_mass(
        list(zone_surface),
        zone_surface,
        greywater_frac=0.1,
        graywater_zones=["Engine_Room_Aft"],
    )
    assert pooled == {"Engine_Room_Aft": pytest.approx(15.5)}


def test_wastewater_pathogen_mass_by_id_pools_ship_wide() -> None:
    masses = {
        "norovirus": {"Bridge": 80.0, "Galley": 20.0},
    }
    pooled = build_wastewater_pathogen_mass_by_id(
        ["Bridge", "Galley"],
        masses,
        greywater_frac=0.1,
        graywater_zones=["Engine_Room_Aft"],
    )
    assert pooled is not None
    assert pooled["norovirus"]["Engine_Room_Aft"] == pytest.approx(10.0)


def test_microflora_propagates_to_platform_graywater_zone() -> None:
    class Agent:
        def __init__(self, loc: str, status: float) -> None:
            self.current_location = loc
            self.microflora_disruption_status = status
            self.active_pathogen_ids = ["norovirus"]

    profiles = {
        "norovirus": {
            "microflora_disruption": {
                "causes_disruption": True,
                "disruption_type": "gastrointestinal",
            },
        },
    }
    cfg = _cfg_for_platform("mega_cruise_5000")
    agents = [Agent("Main_Dining_Room", 80.0)]
    shifts = compute_zone_microflora_shifts(agents, profiles, cfg)
    assert "Engine_Room_Aft" in shifts
    assert shifts["Engine_Room_Aft"]["gastrointestinal"] > 0.0


@pytest.mark.parametrize(
    "platform_id",
    sorted(
        name
        for name in os.listdir(PLATFORMS_DIR)
        if os.path.isfile(os.path.join(PLATFORMS_DIR, name, "spatial_layout.json"))
    ),
)
def test_all_platforms_define_valid_graywater_zones(platform_id: str) -> None:
    layout_path = _layout_path(platform_id)
    with open(layout_path, encoding="utf-8") as fh:
        layout = json.load(fh)
    zone_ids = {z["id"] for z in layout["zones"]}
    graywater = layout.get("graywater_zones")
    assert graywater, f"{platform_id} missing graywater_zones"
    for gz in graywater:
        assert gz in zone_ids, f"{platform_id}: graywater zone {gz!r} not in layout"
