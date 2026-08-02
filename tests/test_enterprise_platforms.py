"""Tests for Enterprise Constitution (TOS) and Galaxy (TNG) cabin-resolution platforms.

Verifies:
  - Platform JSON structure and Contam-safe zone IDs (≤15 chars)
  - Cabin-corridor topology (EC_/OC_/FC_ prefixes, Cabin_Corridor type)
  - HVAC coverage, adjacency orifice types, Contam path density
  - Contagion scenario templates resolve against layouts
  - Generator round-trip for both recipes
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

PLATFORMS = ROOT / "data" / "platforms"
TEMPLATES = ROOT / "data" / "templates"
ORIFICE_CATALOG = ROOT / "data" / "contam_hobbyist" / "orifice_catalog.json"

CONSTITUTION = "enterprise_constitution_tos"
GALAXY = "enterprise_galaxy_tng"

_CONTAM_ID_MAX = 15


def _load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_platform(platform_id: str) -> tuple[dict, dict]:
    base = PLATFORMS / platform_id
    return (
        _load(base / "spatial_layout.json"),
        _load(base / "air_flow_paths.json"),
    )


def _zone_ids(platform: dict) -> set[str]:
    return {z["id"] for z in platform["zones"]}


def _cabin_corridors(platform: dict) -> list[dict]:
    return [z for z in platform["zones"] if z.get("type") == "Cabin_Corridor"]


# ── Structure ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("platform_id", [CONSTITUTION, GALAXY])
def test_platform_json_exists_and_valid(platform_id):
    spatial, airflow = _load_platform(platform_id)
    assert spatial.get("platform") == platform_id
    assert len(spatial["zones"]) >= 20
    assert len(airflow["hvac_zones"]) >= 1
    assert len(airflow["adjacency"]) >= 1


@pytest.mark.parametrize(
    "platform_id,min_corridors,min_zones,prefixes",
    [
        (CONSTITUTION, 18, 40, ("EC_", "OC_")),
        (GALAXY, 54, 85, ("EC_", "OC_", "FC_")),
    ],
)
def test_cabin_corridor_counts(platform_id, min_corridors, min_zones, prefixes):
    spatial, _ = _load_platform(platform_id)
    corridors = _cabin_corridors(spatial)
    assert len(corridors) >= min_corridors
    assert len(spatial["zones"]) >= min_zones
    for z in corridors:
        assert z["id"].startswith(prefixes), z["id"]
        assert len(z["id"]) <= _CONTAM_ID_MAX
        assert z.get("cabin_size", 0) >= 1
        assert z.get("cabin_ventilation_type") in {
            "interior_hvac",
            "balcony_partial",
            "atrium_view",
        }


@pytest.mark.parametrize("platform_id", [CONSTITUTION, GALAXY])
def test_all_zone_ids_contam_safe(platform_id):
    spatial, _ = _load_platform(platform_id)
    for z in spatial["zones"]:
        assert len(z["id"]) <= _CONTAM_ID_MAX, z["id"]
        assert " " not in z["id"]


@pytest.mark.parametrize(
    "platform_id,expected",
    [
        (CONSTITUTION, {"Bridge", "MessHall", "Sickbay", "EngMain", "Brig", "NeckHub"}),
        (
            GALAXY,
            {
                "Bridge",
                "MessHall",
                "TenFwd",
                "Sickbay",
                "MainEng",
                "Arboretum",
                "Holodeck1",
                "ShuttleBay",
            },
        ),
    ],
)
def test_specialty_zones_present(platform_id, expected):
    ids = _zone_ids(_load_platform(platform_id)[0])
    missing = expected - ids
    assert not missing, f"{platform_id} missing specialty zones: {missing}"


@pytest.mark.parametrize("platform_id", [CONSTITUTION, GALAXY])
def test_hvac_covers_all_zones(platform_id):
    spatial, airflow = _load_platform(platform_id)
    zone_ids = _zone_ids(spatial)
    covered = {r for hz in airflow["hvac_zones"] for r in hz["rooms"]}
    assert covered == zone_ids


@pytest.mark.parametrize("platform_id", [CONSTITUTION, GALAXY])
def test_adjacency_endpoints_and_pocket_doors(platform_id):
    spatial, airflow = _load_platform(platform_id)
    zone_ids = _zone_ids(spatial)
    pocket = 0
    for link in airflow["adjacency"]:
        assert link["from"] in zone_ids, link
        assert link["to"] in zone_ids, link
        if link.get("type") == "pocket_door":
            pocket += 1
    assert pocket >= 4, f"{platform_id} expected pocket_door links, got {pocket}"
    assert any(a.get("type") == "pressure_bulkhead" for a in airflow["adjacency"])


@pytest.mark.parametrize("platform_id", [CONSTITUTION, GALAXY])
def test_cross_zone_links_reference_valid_endpoints(platform_id):
    spatial, airflow = _load_platform(platform_id)
    zone_ids = _zone_ids(spatial)
    hvac_ids = {hz["id"] for hz in airflow["hvac_zones"]}
    valid = zone_ids | hvac_ids
    for link in airflow.get("cross_zone_links", []):
        assert link["from"] in valid, link
        assert link["to"] in valid, link


def test_orifice_catalog_has_enterprise_types():
    cat = _load(ORIFICE_CATALOG)
    types = set(cat["types"])
    assert "pocket_door" in types
    assert "pressure_bulkhead" in types


@pytest.mark.parametrize(
    "platform_id,min_paths",
    [(CONSTITUTION, 300), (GALAXY, 800)],
)
def test_contam_path_density(platform_id, min_paths):
    path_map = _load(PLATFORMS / platform_id / "contam" / "path_map.json")
    assert len(path_map) >= min_paths


@pytest.mark.parametrize(
    "platform_id,expected_gw",
    [(CONSTITUTION, ["EngMain"]), (GALAXY, ["MainEng"])],
)
def test_graywater_zones(platform_id, expected_gw):
    spatial, _ = _load_platform(platform_id)
    assert spatial["graywater_zones"] == expected_gw
    ids = _zone_ids(spatial)
    for gz in expected_gw:
        assert gz in ids


# ── Templates ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "template_id,platform_id,min_agents",
    [
        ("enterprise_constitution_tos", CONSTITUTION, 400),
        ("enterprise_galaxy_tng", GALAXY, 900),
    ],
)
def test_template_homes_and_duties_resolve(template_id, platform_id, min_agents):
    tmpl = _load(TEMPLATES / f"{template_id}.json")
    spatial, _ = _load_platform(platform_id)
    zone_ids = _zone_ids(spatial)
    assert tmpl["meta"]["platform"] == platform_id
    assert tmpl["recommended_ship_graph"]["num_agents"] >= min_agents
    for cls in tmpl["agent_classes"]:
        home = cls.get("home_zone_preference")
        if home:
            assert home in zone_ids, f"{cls['class_id']} home {home}"
        duty = cls.get("duty_zone") or ""
        if duty:
            assert duty in zone_ids, f"{cls['class_id']} duty {duty}"
        free = cls.get("free_zone_preference") or ""
        if free:
            assert free in zone_ids, f"{cls['class_id']} free {free}"
    frac = sum(c["fraction"] for c in tmpl["agent_classes"])
    assert abs(frac - 1.0) < 1e-6


# ── Deck assets ────────────────────────────────────────────────────────


@pytest.mark.parametrize("platform_id", [CONSTITUTION, GALAXY])
def test_deck_manifest_present(platform_id):
    manifest_path = PLATFORMS / platform_id / "deck_manifest.json"
    assert manifest_path.exists()
    manifest = _load(manifest_path)
    assert manifest["platform_id"] == platform_id
    assert len(manifest["decks"]) >= 1
    assert (PLATFORMS / platform_id / "deck_graphics.geojson").exists()


# ── Generator round-trip ───────────────────────────────────────────────


@pytest.mark.parametrize("recipe_id", [CONSTITUTION, GALAXY])
def test_enterprise_generator_roundtrip(recipe_id):
    from enterprise_platform_recipes import RECIPES
    from generate_cruise_platform_layout import build_air_flow_paths, build_spatial_layout

    recipe = RECIPES[recipe_id]
    spatial = build_spatial_layout(recipe)
    airflow = build_air_flow_paths(recipe, {z["id"] for z in spatial["zones"]})
    committed_s, committed_a = _load_platform(recipe_id)
    assert {z["id"] for z in spatial["zones"]} == {z["id"] for z in committed_s["zones"]}
    assert {hz["id"] for hz in airflow["hvac_zones"]} == {
        hz["id"] for hz in committed_a["hvac_zones"]
    }
    assert any(z["id"].startswith("OC_") for z in spatial["zones"])
    assert any(a.get("type") == "pocket_door" for a in airflow["adjacency"])


def test_galaxy_family_corridors_and_atrium_view():
    spatial, airflow = _load_platform(GALAXY)
    family = [z for z in _cabin_corridors(spatial) if z["id"].startswith("FC_")]
    assert len(family) == 12
    assert all(z["cabin_size"] == 4 for z in family)
    atrium = [z for z in family if z["cabin_ventilation_type"] == "atrium_view"]
    assert len(atrium) >= 4
    assert any(hz["id"].startswith("AHU_FC_D") for hz in airflow["hvac_zones"])


def test_constitution_enlisted_and_officer_banks():
    spatial, airflow = _load_platform(CONSTITUTION)
    corridors = _cabin_corridors(spatial)
    enlisted = [z for z in corridors if z["id"].startswith("EC_")]
    officer = [z for z in corridors if z["id"].startswith("OC_")]
    assert len(enlisted) == 12
    assert len(officer) == 6
    assert any(hz["id"] == "AHU_Crew" for hz in airflow["hvac_zones"])
    assert {hz["id"] for hz in airflow["hvac_zones"] if hz["id"].startswith("AHU_EC_D")} == {
        "AHU_EC_D4",
        "AHU_EC_D5",
        "AHU_EC_D6",
    }
