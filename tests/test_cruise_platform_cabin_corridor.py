"""Tests for cabin-corridor cruise platforms (expedition_cruise_450 and stacked siblings)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from orchestrator_init import assign_cabin_mates, default_cabin_size  # noqa: E402

PLATFORMS = REPO_ROOT / "data" / "platforms"


def _load_platform(platform_id: str) -> tuple[dict, dict]:
    base = PLATFORMS / platform_id
    return (
        json.loads((base / "spatial_layout.json").read_text(encoding="utf-8")),
        json.loads((base / "air_flow_paths.json").read_text(encoding="utf-8")),
    )


def test_expedition_450_corridor_topology() -> None:
    spatial, airflow = _load_platform("expedition_cruise_450")
    zones = spatial["zones"]
    corridors = [z for z in zones if z["type"] == "Cabin_Corridor"]
    pax = [z for z in corridors if z["id"].startswith("PC_")]
    crew = [z for z in corridors if z["id"].startswith("CC_")]
    assert len(pax) == 12
    assert len(crew) == 4
    assert len(zones) == 33
    vents = {z["cabin_ventilation_type"] for z in corridors}
    assert "balcony_partial" in vents
    assert "interior_hvac" in vents
    assert "atrium_view" not in vents  # expedition has no atrium

    # Contam-safe names
    assert all(len(z["id"]) <= 15 for z in zones)

    covered = {r for hz in airflow["hvac_zones"] for r in hz["rooms"]}
    assert covered == {z["id"] for z in zones}
    assert spatial["graywater_zones"] == ["Engine_Room"]
    assert spatial["deck_dimensions"] == {"length_m": 160.0, "beam_m": 21.0}


def test_expedition_450_generator_roundtrip() -> None:
    from cruise_platform_recipes import RECIPES
    from generate_cruise_platform_layout import (
        build_air_flow_paths,
        build_spatial_layout,
    )

    recipe = RECIPES["expedition_cruise_450"]
    spatial = build_spatial_layout(recipe)
    airflow = build_air_flow_paths(recipe, {z["id"] for z in spatial["zones"]})
    committed_s, committed_a = _load_platform("expedition_cruise_450")
    assert spatial["platform"] == committed_s["platform"]
    assert len(spatial["zones"]) == len(committed_s["zones"])
    assert {z["id"] for z in spatial["zones"]} == {z["id"] for z in committed_s["zones"]}
    assert {hz["id"] for hz in airflow["hvac_zones"]} == {
        hz["id"] for hz in committed_a["hvac_zones"]
    }


def test_expedition_300_archived_superseded() -> None:
    spatial, _ = _load_platform("expedition_cruise_300")
    assert spatial.get("superseded_by") == "expedition_cruise_450"
    assert "LEGACY" in spatial["description"]
    assert spatial["platform"] == "expedition_cruise_300"


def test_expedition_450_cabin_mates_pair() -> None:
    spatial, _ = _load_platform("expedition_cruise_450")

    class Agent:
        def __init__(self, agent_id: str, home_zone: str) -> None:
            self.agent_id = agent_id
            self.home_zone = home_zone
            self.cabin_mate_ids = frozenset()

    # Four agents in one corridor → two cabins of size 2
    agents = [Agent(f"a{i}", "PC_D5_P_F") for i in range(4)]
    zone_docs = [
        {
            "name": z["id"],
            "type": z["type"],
            "cabin_size": z.get("cabin_size"),
        }
        for z in spatial["zones"]
    ]
    assign_cabin_mates(agents, zone_docs)
    assert default_cabin_size("PC_D5_P_F", "Cabin_Corridor", 2) == 2
    assert agents[0].cabin_mate_ids == frozenset({"a1"})
    assert agents[1].cabin_mate_ids == frozenset({"a0"})
    assert agents[2].cabin_mate_ids == frozenset({"a3"})


def test_expedition_450_graphics_and_contam_present() -> None:
    base = PLATFORMS / "expedition_cruise_450"
    assert (base / "graphics" / "elevation.jpg").is_file()
    assert (base / "graphics" / "plan_overview.jpg").is_file()
    assert (base / "graphics" / "graphics.json").is_file()
    assert (base / "deck_graphics.geojson").is_file()
    assert (base / "deck_manifest.json").is_file()
    contam = base / "contam"
    assert (contam / "platform.prj").is_file()
    assert (contam / "path_map.json").is_file()
    assert (contam / "hobbyist_overrides.json").is_file()
    paths = json.loads((contam / "path_map.json").read_text(encoding="utf-8"))
    assert len(paths) >= 100


def test_expedition_450_architectural_loader() -> None:
    from dashboard.architectural_graphics import load_architectural_graphics

    arch = load_architectural_graphics(str(PLATFORMS / "expedition_cruise_450"))
    assert arch.has_elevation
    assert arch.has_plan
